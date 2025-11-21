"""
DRF API views for DailyMed search functionality.
"""
import sys
import json
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import DailyMedService


@api_view(['GET'])
def drug_autocomplete(request):
    """
    API endpoint for drug name autocomplete.
    
    Query params:
        q: Search query (minimum 3 characters)
        limit: Maximum number of results (default: 20)
    
    Returns:
        JSON array of drug name suggestions
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    
    if len(query) < 3:
        return Response([], status=status.HTTP_200_OK)
    
    try:
        service = DailyMedService()
        suggestions = service.get_drug_autocomplete(query, limit)
        return Response(suggestions, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        print(f"Error in drug_autocomplete endpoint: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return Response([], status=status.HTTP_200_OK)


def search_drugs_stream(request):
    """
    Streaming API endpoint for searching drugs with excipient filtering.
    Streams results as they are found.
    
    Query params:
        drug: Drug name to search for
        excipients: Comma-separated list of excipient names
        page: Page number (default: 1)
        pagesize: Results per page (default: 25)
    
    Returns:
        Stream of JSON objects, one per line (NDJSON format)
    """
    drug_name = request.GET.get('drug', '').strip()
    excipients_str = request.GET.get('excipients', '').strip()
    page = int(request.GET.get('page', 1))
    pagesize = int(request.GET.get('pagesize', 25))
    
    if not drug_name:
        return Response(
            {"error": "Drug name is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Parse excipients from comma-separated string
    excipients = [exc.strip() for exc in excipients_str.split(',') if exc.strip()] if excipients_str else []
    
    def generate():
        try:
            service = DailyMedService()
            
            # Send initial metadata
            yield json.dumps({
                "type": "init",
                "excipients_highlighted": excipients
            }) + "\n"
            
            # Track results as they come in
            results_free = []
            results_with = []
            excipients_lower = {exc.lower() for exc in excipients} if excipients else set()
            
            # Stream results from search_with_filters
            for result in service.api.search_with_filters(service._create_mock_args(drug_name, page, pagesize)):
                # Determine if result contains excipients
                contains_excipient = False
                if excipients_lower:
                    inactive_ingredients = result.get("inactive", [])
                    inactive_lower = {ing.lower() for ing in inactive_ingredients}
                    
                    for exc_lower in excipients_lower:
                        for ing_lower in inactive_lower:
                            if exc_lower in ing_lower or ing_lower in exc_lower:
                                contains_excipient = True
                                break
                        if contains_excipient:
                            break
                
                # Add basic fields
                result["ndc"] = "N/A"
                result["packager"] = "N/A"
                result["dailymed_link"] = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={result.get('set_id', '')}"
                result["drug_type"] = result.get("form_code_display", "N/A")
                active = result.get("active", [])
                result["dosage"] = ", ".join([f"{ing.get('name', '')} {ing.get('strength', '')}" for ing in active]) if active else "N/A"
                
                # Add to appropriate list
                if contains_excipient:
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
    API endpoint for searching drugs with excipient filtering.
    Uses streaming endpoint for better performance.
    
    Query params:
        drug: Drug name to search for
        excipients: Comma-separated list of excipient names
        page: Page number (default: 1)
        pagesize: Results per page (default: 25)
    
    Returns:
        Streaming response with results as they are found
    """
    return search_drugs_stream(request)

