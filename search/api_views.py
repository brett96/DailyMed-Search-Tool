"""
DRF API views for DailyMed search functionality.
"""
import sys
import json
import re
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import DailyMedService, search_rxnorm_logic
from .excipient_loader import get_excipient_categories
# Try to import models for local development (database mode)
try:
    from .models import ExcipientCategory, Excipient
    USE_DATABASE = True
except (ImportError, Exception):
    # Models not available (e.g., in Vercel deployment without database)
    USE_DATABASE = False


def extract_base_drug_name(drug_name: str) -> str:
    """
    Extract the base drug name from various formats, removing route, form, and strength information.
    Handles formats like:
    - "ADVIL (Oral Pill)" -> "ADVIL"
    - "TYLENOL (Oral Pill)" -> "TYLENOL"
    - "Duloxetine Hydrochloride 20 MG Oral Tablet" -> "Duloxetine Hydrochloride"
    - "Duloxetine Hydrochloride Pill" -> "Duloxetine Hydrochloride"
    
    Args:
        drug_name: The full drug name string from autocomplete
        
    Returns:
        The base drug name without route, form, or strength
    """
    if not drug_name:
        return ""
    
    base_drug_name = drug_name.strip()
    
    # Remove content in parentheses (e.g., "(Oral Pill)", "(Injectable)")
    # This handles autocomplete formats like "ADVIL (Oral Pill)"
    base_drug_name = re.sub(r'\s*\([^)]*\)\s*$', '', base_drug_name).strip()
    
    # Remove strength patterns (numbers with units) and everything after
    # This handles cases like "Duloxetine Hydrochloride 20 MG Oral Tablet"
    strength_pattern = r'\s+\d+\.?\d*\s*(?:mg|ml|mcg|g|%|units?|iu)\s*.*$'
    base_drug_name = re.sub(strength_pattern, '', base_drug_name, flags=re.IGNORECASE).strip()
    
    # Remove route suffixes (with or without parentheses)
    route_suffixes = [' Oral', ' Injectable', ' Topical', ' Intravenous', ' Ophthalmic', 
             ' Sublingual', ' Intramuscular', ' Subcutaneous', ' Rectal', ' Vaginal',
             ' Otic', ' Nasal', ' Inhalation', ' Transdermal', ' Buccal']
    for route_suffix in route_suffixes:
        # Handle both " Drug Oral" and " Drug (Oral)" formats
        base_drug_name = re.sub(rf'{re.escape(route_suffix)}\s*(?:\(.*?\))?\s*(?:Pill|Tablet|Capsule|.*)?$', '', base_drug_name, flags=re.IGNORECASE).strip()
        # Also handle route in parentheses at the end
        base_drug_name = re.sub(rf'\s*\({re.escape(route_suffix.strip())}.*?\)\s*$', '', base_drug_name, flags=re.IGNORECASE).strip()
    
    # Remove form suffixes (must be at the end, with or without parentheses)
    form_suffixes = [' Pill', ' Tablet', ' Capsule', ' Solution', ' Suspension', ' Cream', 
            ' Ointment', ' Injection', ' Syrup', ' Gel', ' Lotion', ' Spray', 
            ' Drops', ' Patch', ' Suppository', ' Film', ' Powder', ' Granules', 
            ' Lozenge', ' Paste', ' Delayed Release', ' Extended Release', 
            ' ER', ' DR', ' SR', ' XR', ' pellets', ' Pellets']
    for form_suffix in form_suffixes:
        # Handle both " Drug Pill" and " Drug (Pill)" formats
        if base_drug_name.lower().endswith(form_suffix.lower()):
            base_drug_name = base_drug_name[:-len(form_suffix)].strip()
        # Also handle form in parentheses at the end
        base_drug_name = re.sub(rf'\s*\({re.escape(form_suffix.strip())}.*?\)\s*$', '', base_drug_name, flags=re.IGNORECASE).strip()
    
    # Remove any remaining parentheses and their content at the end
    base_drug_name = re.sub(r'\s*\([^)]*\)\s*$', '', base_drug_name).strip()
    
    # Remove trailing punctuation, commas, and extra spaces
    base_drug_name = re.sub(r'[,\s]+$', '', base_drug_name).strip()
    
    # If we've removed everything, fall back to original (but try to extract just the first word)
    if not base_drug_name:
        # Try to get just the first word as fallback
        first_word_match = re.match(r'^([A-Za-z0-9]+)', drug_name.strip())
        if first_word_match:
            base_drug_name = first_word_match.group(1)
        else:
            base_drug_name = drug_name.strip()
    
    return base_drug_name


@api_view(['GET'])
def drug_autocomplete(request):
    """
    API endpoint for drug name autocomplete using RxNorm database.
    
    Query params:
        q: Search query (drug name or NDC)
        limit: Maximum number of results (default: 20, max: 250)
    
    Returns:
        JSON array of drug name suggestions with format:
        {
            'label': Display name,
            'value': RxCUI,
            'metadata': {strength, form, route}
        }
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    
    if not query:
        return Response([], status=status.HTTP_200_OK)
    
    try:
        # Use RxNorm database search logic
        results = search_rxnorm_logic(query)
        
        # Limit results if needed
        if limit > 0 and len(results) > limit:
            results = results[:limit]
        
        # Format results for frontend compatibility
        suggestions = []
        for result in results:
            suggestions.append({
                'label': result.get('label', result.get('display', '')),
                'value': result.get('value', result.get('id', '')),
                'metadata': result.get('metadata', {})
            })
        
        return Response(suggestions, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        print(f"Error in drug_autocomplete endpoint: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return Response([], status=status.HTTP_200_OK)


def search_drugs_stream(request):
    """
    Streaming API endpoint for searching drugs with advanced ingredient filtering.
    Streams results as they are found.
    
    Query params:
        drug: Drug name to search for (required)
        excipients: Comma-separated list of excipient names (for highlighting only, legacy)
        page: Page number (default: 1)
        pagesize: Results per page (default: 25)
        route: Route of administration filter
        form: Comma-separated list of dosage forms
        only-active: Comma-separated list of active ingredients (results must ONLY contain these)
        include-active: Comma-separated list of active ingredients that MUST be present
        exclude-active: Comma-separated list of active ingredients that MUST NOT be present
        include-inactive: Comma-separated list of inactive ingredients that MUST be present
        exclude-inactive: Comma-separated list of inactive ingredients that MUST NOT be present
    
    Returns:
        Stream of JSON objects, one per line (NDJSON format)
    """
    drug_name = request.GET.get('drug', '').strip()
    rxcui = request.GET.get('rxcui', '').strip() or None
    excipients_str = request.GET.get('excipients', '').strip()
    page = int(request.GET.get('page', 1))
    pagesize = int(request.GET.get('pagesize', 25))
    
    # Validate that either drug_name or rxcui is provided
    if not drug_name and not rxcui:
        return Response(
            {"error": "Either drug name or rxcui is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # If both are provided, prefer rxcui but keep drug_name as fallback
    # If only rxcui is provided, we'll try to extract drug name from it if search fails
    
    # Parse filter parameters
    route = request.GET.get('route', '').strip() or None
    form_str = request.GET.get('form', '').strip()
    form = [f.strip() for f in form_str.split(',') if f.strip()] if form_str else None
    
    only_active_str = request.GET.get('only-active', '').strip()
    only_active = [ing.strip() for ing in only_active_str.split(',') if ing.strip()] if only_active_str else None
    
    include_active_str = request.GET.get('include-active', '').strip()
    include_active = [ing.strip() for ing in include_active_str.split(',') if ing.strip()] if include_active_str else None
    
    exclude_active_str = request.GET.get('exclude-active', '').strip()
    exclude_active = [ing.strip() for ing in exclude_active_str.split(',') if ing.strip()] if exclude_active_str else None
    
    include_inactive_str = request.GET.get('include-inactive', '').strip()
    include_inactive = [ing.strip() for ing in include_inactive_str.split(',') if ing.strip()] if include_inactive_str else None
    
    exclude_inactive_str = request.GET.get('exclude-inactive', '').strip()
    exclude_inactive = [ing.strip() for ing in exclude_inactive_str.split(',') if ing.strip()] if exclude_inactive_str else None
    
    # Parse excipients from comma-separated string (for highlighting only)
    excipients = [exc.strip() for exc in excipients_str.split(',') if exc.strip()] if excipients_str else []
    
    def generate():
        try:
            service = DailyMedService()
            
            # Combine exclude-inactive and legacy excipients for highlighting
            all_excipients_for_highlight = list(set(exclude_inactive + excipients)) if exclude_inactive else excipients
            
            # Send initial metadata
            yield json.dumps({
                "type": "init",
                "excipients_highlighted": all_excipients_for_highlight
            }) + "\n"
            
            # Track results as they come in
            results_free = []
            results_with = []
            # Combine exclude-inactive and legacy excipients for categorization/highlighting
            all_excipients_for_categorization = list(set(exclude_inactive + excipients)) if exclude_inactive else excipients
            excipients_lower = {exc.lower() for exc in all_excipients_for_categorization} if all_excipients_for_categorization else set()
            
            # Try RxCUI search first if available, then fall back to drug_name if no results
            mock_args = None
            
            # First attempt: Try RxCUI if available
            if rxcui:
                # Check if RxCUI search returns any results
                # We'll do a quick test search to see if there are results
                test_results = service.api.search_spls(rxcui=rxcui, pagesize=1, page=1)
                if test_results.get("data") and len(test_results.get("data", [])) > 0:
                    # RxCUI search has results, use it
                    # But also extract drug_name for potential fallback if no filtered results
                    base_drug_name = None
                    if drug_name:
                        base_drug_name = extract_base_drug_name(drug_name)
                    
                    mock_args = service._create_mock_args(
                        drug_name=base_drug_name,  # Pass extracted name for fallback
                        rxcui=rxcui,
                        page=page,
                        pagesize=pagesize,
                        route=route,
                        form=form,
                        only_active=only_active,
                        include_active=include_active,
                        exclude_active=exclude_active,
                        include_inactive=include_inactive,
                        exclude_inactive=exclude_inactive
                    )
                    print(f"Using RxCUI {rxcui} for search (found {len(test_results.get('data', []))} initial results)", file=sys.stderr)
                    if base_drug_name:
                        print(f"  Drug name '{base_drug_name}' available as fallback if needed", file=sys.stderr)
                else:
                    # RxCUI search returned no results, fall back to drug_name
                    print(f"RxCUI {rxcui} returned no results, falling back to drug_name search", file=sys.stderr)
                    if drug_name:
                        base_drug_name = extract_base_drug_name(drug_name)
                        
                        mock_args = service._create_mock_args(
                            drug_name=base_drug_name,
                            rxcui=None,
                            page=page,
                            pagesize=pagesize,
                            route=route,
                            form=form,
                            only_active=only_active,
                            include_active=include_active,
                            exclude_active=exclude_active,
                            include_inactive=include_inactive,
                            exclude_inactive=exclude_inactive
                        )
                        print(f"Falling back to drug_name '{base_drug_name}' (extracted from '{drug_name}') for search", file=sys.stderr)
                    else:
                        # No drug_name available
                        print(f"No drug_name available and RxCUI {rxcui} has no results", file=sys.stderr)
                        yield json.dumps({
                            "type": "error",
                            "error": f"No results found for RxCUI {rxcui}. Please try searching by drug name instead."
                        }) + "\n"
                        return
            else:
                # No RxCUI, use drug_name
                if not drug_name:
                    yield json.dumps({
                        "type": "error",
                        "error": "Either drug name or rxcui is required"
                    }) + "\n"
                    return
                
                # Extract base drug name using helper function
                base_drug_name = extract_base_drug_name(drug_name)
                
                mock_args = service._create_mock_args(
                    drug_name=base_drug_name,
                    rxcui=None,
                    page=page,
                    pagesize=pagesize,
                    route=route,
                    form=form,
                    only_active=only_active,
                    include_active=include_active,
                    exclude_active=exclude_active,
                    include_inactive=include_inactive,
                    exclude_inactive=exclude_inactive
                )
                print(f"Using drug_name '{base_drug_name}' (extracted from '{drug_name}') for search", file=sys.stderr)
            
            if not mock_args:
                yield json.dumps({
                    "type": "error",
                    "error": "Unable to create search parameters"
                }) + "\n"
                return
            
            # Stream results from search_with_filters
            # All results at this point have already passed the filters
            result_count = 0
            for result in service.api.search_with_filters(mock_args):
                # Skip None results (generator may yield None when no results found)
                if result is None:
                    continue
                
                # Ensure result is a dictionary
                if not isinstance(result, dict):
                    continue
                
                result_count += 1
                
                # Determine if result contains excluded excipients (for categorization/highlighting)
                contains_excluded_excipient = False
                if excipients_lower:
                    inactive_ingredients = result.get("inactive", [])
                    inactive_lower = {ing.lower() for ing in inactive_ingredients}
                    
                    for exc_lower in excipients_lower:
                        for ing_lower in inactive_lower:
                            if exc_lower in ing_lower or ing_lower in exc_lower:
                                contains_excluded_excipient = True
                                break
                        if contains_excluded_excipient:
                            break
                
                # Use NDC and packager info from parsed XML (extracted in _parse_spl_xml)
                set_id = result.get('set_id', '')
                
                # Map 'labeler' (from XML) to 'packager' (expected by frontend)
                result["packager"] = result.get("labeler", "N/A")
                
                # Ensure NDC is set (it should come from XML now)
                if "ndc" not in result or result["ndc"] is None:
                    result["ndc"] = "N/A"
                result["dailymed_link"] = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
                result["drug_type"] = result.get("form_code_display", "N/A")
                
                # Ensure active is always a list
                active = result.get("active", [])
                if not isinstance(active, list):
                    active = []
                
                # Filter and ensure each active ingredient has the expected structure
                # Remove any non-dict items and ensure all dicts have name and strength
                valid_active = []
                for ing in active:
                    if not isinstance(ing, dict):
                        continue  # Skip non-dict items
                    # Ensure required fields exist and are not empty
                    name = ing.get("name", "").strip() if ing.get("name") else ""
                    if not name:
                        name = "Unknown"
                    ing["name"] = name
                    
                    strength = ing.get("strength", "").strip() if ing.get("strength") else ""
                    if not strength:
                        strength = "N/A"
                    ing["strength"] = strength
                    
                    valid_active.append(ing)
                
                # Set active back to result with only valid ingredients
                result["active"] = valid_active
                # Only use the first (main) active ingredient for dosage
                if valid_active and len(valid_active) > 0:
                    main_ing = valid_active[0]
                    result["dosage"] = f"{main_ing.get('name', '')} {main_ing.get('strength', '')}".strip()
                else:
                    result["dosage"] = "N/A"
                
                # Add to appropriate list
                # If we have excluded excipients, categorize for highlighting
                # Otherwise, all results go to "free" category
                if excipients_lower and contains_excluded_excipient:
                    results_with.append(result)
                    category = "with"
                else:
                    results_free.append(result)
                    category = "free"
                
                # Stream the result
                yield json.dumps({
                    "type": "result",
                    "category": category,
                    "result": result,
                    "metadata": {
                        "total_free": len(results_free),
                        "total_with": len(results_with),
                        "total": len(results_free) + len(results_with)
                    }
                }) + "\n"
            
            # If RxCUI search returned no results and we have a drug_name, try drug_name search as fallback
            if result_count == 0 and rxcui and drug_name and mock_args.drug_name:
                print(f"RxCUI {rxcui} search returned no filtered results, trying drug_name '{mock_args.drug_name}' as fallback", file=sys.stderr)
                # Create new mock_args with drug_name instead of RxCUI
                fallback_mock_args = service._create_mock_args(
                    drug_name=mock_args.drug_name,
                    rxcui=None,
                    page=page,
                    pagesize=pagesize,
                    route=route,
                    form=form,
                    only_active=only_active,
                    include_active=include_active,
                    exclude_active=exclude_active,
                    include_inactive=include_inactive,
                    exclude_inactive=exclude_inactive
                )
                
                # Try drug_name search
                for result in service.api.search_with_filters(fallback_mock_args):
                    if result is None or not isinstance(result, dict):
                        continue
                    
                    result_count += 1
                    
                    # Determine if result contains excluded excipients
                    contains_excluded_excipient = False
                    if excipients_lower:
                        inactive_ingredients = result.get("inactive", [])
                        inactive_lower = {ing.lower() for ing in inactive_ingredients}
                        
                        for exc_lower in excipients_lower:
                            for ing_lower in inactive_lower:
                                if exc_lower in ing_lower or ing_lower in exc_lower:
                                    contains_excluded_excipient = True
                                    break
                            if contains_excluded_excipient:
                                break
                    
                    # Use NDC and packager info from parsed XML (extracted in _parse_spl_xml)
                    set_id = result.get('set_id', '')
                    
                    # Map 'labeler' (from XML) to 'packager' (expected by frontend)
                    result["packager"] = result.get("labeler", "N/A")
                    
                    # Ensure NDC is set (it should come from XML now)
                    if "ndc" not in result or result["ndc"] is None:
                        result["ndc"] = "N/A"
                    result["dailymed_link"] = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
                    result["drug_type"] = result.get("form_code_display", "N/A")
                    
                    # Ensure active is always a list and filter out invalid items
                    active = result.get("active", [])
                    if not isinstance(active, list):
                        active = []
                    
                    # Filter and ensure each active ingredient has the expected structure
                    valid_active = []
                    for ing in active:
                        if not isinstance(ing, dict):
                            continue  # Skip non-dict items
                        # Ensure required fields exist and are not empty
                        name = ing.get("name", "").strip() if ing.get("name") else ""
                        if not name:
                            name = "Unknown"
                        ing["name"] = name
                        
                        strength = ing.get("strength", "").strip() if ing.get("strength") else ""
                        if not strength:
                            strength = "N/A"
                        ing["strength"] = strength
                        
                        valid_active.append(ing)
                    
                    # Set active back to result with only valid ingredients
                    result["active"] = valid_active
                    result["dosage"] = ", ".join([f"{ing.get('name', '')} {ing.get('strength', '')}" for ing in valid_active]) if valid_active else "N/A"
                    
                    # Add to appropriate list
                    if excipients_lower and contains_excluded_excipient:
                        results_with.append(result)
                        category = "with"
                    else:
                        results_free.append(result)
                        category = "free"
                    
                    # Stream the result
                    yield json.dumps({
                        "type": "result",
                        "category": category,
                        "result": result,
                        "metadata": {
                            "total_free": len(results_free),
                            "total_with": len(results_with),
                            "total": len(results_free) + len(results_with)
                        }
                    }) + "\n"
            
            # Send completion message
            yield json.dumps({
                "type": "complete",
                "metadata": {
                    "total_free": len(results_free),
                    "total_with": len(results_with),
                    "total": len(results_free) + len(results_with)
                }
            }) + "\n"
            
        except Exception as e:
            import traceback
            print(f"Error in search_drugs_stream: {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            yield json.dumps({
                "type": "error",
                "error": str(e)
            }) + "\n"
    
    response = StreamingHttpResponse(generate(), content_type='application/x-ndjson')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def search_drugs(request):
    """
    API endpoint for searching drugs with advanced ingredient filtering.
    Uses streaming endpoint for better performance.
    
    Query params:
        drug: Drug name to search for (required)
        excipients: Comma-separated list of excipient names (for highlighting only, legacy)
        page: Page number (default: 1)
        pagesize: Results per page (default: 25)
        route: Route of administration filter
        form: Comma-separated list of dosage forms
        only-active: Comma-separated list of active ingredients (results must ONLY contain these)
        include-active: Comma-separated list of active ingredients that MUST be present
        exclude-active: Comma-separated list of active ingredients that MUST NOT be present
        include-inactive: Comma-separated list of inactive ingredients that MUST be present
        exclude-inactive: Comma-separated list of inactive ingredients that MUST NOT be present
    
    Returns:
        Streaming response with results as they are found
    """
    return search_drugs_stream(request)


@api_view(['GET'])
def excipient_categories(request):
    """
    API endpoint to retrieve all excipient categories with their excipients.
    
    Returns:
        JSON object with categories as keys and lists of excipient names as values:
        {
            "Category Name": ["excipient1", "excipient2", ...],
            ...
        }
    """
    try:
        # Try database first (for local development), fall back to Excel file (for Vercel)
        if USE_DATABASE:
            try:
                categories = ExcipientCategory.objects.all().prefetch_related('excipients')
                result = {}
                
                for category in categories:
                    excipients = list(category.excipients.values_list('ingredient_name', flat=True))
                    result[category.name] = sorted(excipients)
                
                return Response(result, status=status.HTTP_200_OK)
            except Exception as db_error:
                # Database query failed, fall back to Excel file
                print(f"Database query failed, falling back to Excel file: {db_error}", file=sys.stderr)
                result = get_excipient_categories()
                return Response(result, status=status.HTTP_200_OK)
        else:
            # Use Excel file directly (Vercel deployment)
            result = get_excipient_categories()
            return Response(result, status=status.HTTP_200_OK)
            
    except Exception as e:
        import traceback
        print(f"Error in excipient_categories endpoint: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return Response(
            {"error": "Failed to retrieve excipient categories"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

