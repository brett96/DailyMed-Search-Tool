"""
Service layer for DailyMed API integration.
Wraps the DailyMed API client for use in Django views.
"""
import sys
import re
from typing import Dict, Any, Optional, List, Generator
import requests
import json
import xml.etree.ElementTree as ET

# Import the DailyMedAPI class from the original client
import os
import importlib.util

# Load the dailymed_client module
spec = importlib.util.spec_from_file_location(
    "dailymed_client",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "dailymed_client.py")
)
dailymed_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dailymed_client)

DailyMedAPI = dailymed_client.DailyMedAPI


class DailyMedService:
    """
    Service class that wraps DailyMedAPI for Django use.
    Provides methods for autocomplete and search with excipient filtering.
    """
    
    def __init__(self):
        self.api = DailyMedAPI()
    
    def _create_mock_args(
        self, 
        drug_name: Optional[str] = None,
        rxcui: Optional[str] = None,
        page: int = 1, 
        pagesize: int = 25,
        route: Optional[str] = None,
        form: Optional[List[str]] = None,
        only_active: Optional[List[str]] = None,
        include_active: Optional[List[str]] = None,
        exclude_active: Optional[List[str]] = None,
        include_inactive: Optional[List[str]] = None,
        exclude_inactive: Optional[List[str]] = None
    ):
        """
        Create a mock argparse.Namespace for search_with_filters.
        
        Args:
            drug_name: Drug name to search for (used if rxcui not provided)
            rxcui: RxCUI to search for (takes precedence over drug_name)
            page: Page number
            pagesize: Results per page
            route: Route of administration filter
            form: List of dosage form filters
            only_active: List of active ingredients - results must ONLY contain these (and no others)
            include_active: List of active ingredients that MUST be present
            exclude_active: List of active ingredients that MUST NOT be present
            include_inactive: List of inactive ingredients that MUST be present
            exclude_inactive: List of inactive ingredients that MUST NOT be present
        """
        class MockArgs:
            def __init__(self):
                # Use rxcui if provided, otherwise use drug_name
                self.drug_name = drug_name if not rxcui else None
                self.rxcui = rxcui
                self.page = page
                self.pagesize = pagesize
                self.route = route
                self.form = form
                self.only_active = only_active
                self.include_active = include_active
                self.exclude_active = exclude_active
                self.include_inactive = include_inactive
                self.exclude_inactive = exclude_inactive
        
        return MockArgs()
    
    def get_drug_autocomplete(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get drug name suggestions using RxNorm Approximate Match API (Matches MTM Logic).
        Uses approximateTerm for 4+ character queries, and spellingsuggestions as fallback for 3-character queries.
        
        Args:
            query: Search query (minimum 3 characters)
            limit: Maximum number of results to return
            
        Returns:
            List of drug dictionaries with 'label', 'value' (RxCUI), and 'metadata' keys
        """
        if len(query) < 3:
            return []
        
        try:
            # For 3-character queries, RxNav approximateTerm doesn't return results
            # Use spellingsuggestions as fallback, then enrich with RxCUI data
            if len(query) == 3:
                return self._get_autocomplete_3chars(query, limit)
            
            # For 4+ character queries, use approximateTerm API (more accurate)
            url = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"
            params = {
                "term": query,
                "maxEntries": limit,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            suggestions = []
            
            # Navigate response structure: approximateGroup -> candidate
            group = data.get("approximateGroup", {})
            if not group:
                print(f"No approximateGroup in RxNav response for query '{query}'", file=sys.stderr)
                return []
            
            candidates = group.get("candidate", [])
            if not candidates:
                print(f"No candidates in RxNav response for query '{query}'", file=sys.stderr)
                return []
            
            # Handle both single candidate object and array
            if isinstance(candidates, dict):
                candidates = [candidates]
            elif not isinstance(candidates, list):
                candidates = []
            
            seen_rxcuis = set()
            
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                
                # MTM Logic: We prefer candidates that have a synonym (specific name)
                # In a real MTM app, we might filter by rxtty (Term Type) to ensure SBD/SCD
                # but approximateTerm primarily returns scorable candidates.
                
                rxcui_raw = candidate.get("rxcui")
                if not rxcui_raw:
                    continue
                
                rxcui = str(rxcui_raw)
                
                # Skip duplicates by RxCUI
                if rxcui in seen_rxcuis:
                    continue
                seen_rxcuis.add(rxcui)
                
                # Use synonym if available (usually contains "Lisinopril 10mg..."), else use name, else skip
                label = candidate.get("synonym") or candidate.get("name")
                
                # Skip candidates without a label (MTM logic: filter out candidates without names)
                if not label:
                    continue
                
                # Basic parsing to attempt extraction of metadata from the string
                # Example string: "Lisinopril 10 MG Oral Tablet"
                metadata = self._parse_drug_string(label)
                
                suggestions.append({
                    "label": label,        # Display Name
                    "value": rxcui,        # RxCUI (Critical for searching)
                    "metadata": metadata   # Autofill data
                })
                
                if len(suggestions) >= limit:
                    break
            
            print(f"RxNav autocomplete for '{query}': found {len(suggestions)} suggestions", file=sys.stderr)
            return suggestions
            
        except Exception as e:
            print(f"Error in RxNorm autocomplete: {e}", file=sys.stderr)
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
            return []
    
    def _get_autocomplete_3chars(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fallback method for 3-character queries using RxTerms API.
        RxNav APIs don't support 3-character queries, so we use RxTerms as a fallback.
        
        Args:
            query: 3-character search query
            limit: Maximum number of results to return
            
        Returns:
            List of drug dictionaries with 'label', 'value' (RxCUI), and 'metadata' keys
        """
        try:
            # Use RxTerms API as fallback for 3-character queries
            # RxTerms supports shorter queries better than RxNav
            url = "https://clinicaltables.nlm.nih.gov/api/rxterms/v3/search"
            params = {
                "terms": query,
                "maxList": limit,
                "ef": "STRENGTHS_AND_FORMS,SXDG_RXCUI"  # Get strengths/forms and RxCUI
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # RxTerms response format: [total_count, [codes], {extra_fields}, [display_strings], [code_systems]]
            if not isinstance(data, list) or len(data) < 4:
                print(f"Invalid RxTerms response format for query '{query}'", file=sys.stderr)
                return []
            
            total_count = data[0] if isinstance(data[0], int) else 0
            codes = data[1] if isinstance(data[1], list) else []
            extra_fields = data[2] if isinstance(data[2], dict) else {}
            display_strings = data[3] if isinstance(data[3], list) else []
            
            if not codes or not display_strings:
                print(f"No results from RxTerms for 3-char query '{query}'", file=sys.stderr)
                return []
            
            suggestions = []
            seen_rxcuis = set()
            
            # Get RxCUIs from extra_fields if available
            rxcuis_list = extra_fields.get("SXDG_RXCUI", [])
            
            for i, code in enumerate(codes):
                if i >= len(display_strings):
                    break
                
                display = display_strings[i]
                if not isinstance(display, list) or len(display) == 0:
                    continue
                
                label = display[0] if display[0] else None
                if not label:
                    continue
                
                # Try to get RxCUI from extra_fields
                rxcui = None
                if i < len(rxcuis_list) and isinstance(rxcuis_list[i], list) and len(rxcuis_list[i]) > 0:
                    rxcui = str(rxcuis_list[i][0])
                elif i < len(rxcuis_list):
                    rxcui = str(rxcuis_list[i])
                
                # If no RxCUI found, try to look it up using RxNav
                if not rxcui:
                    try:
                        rxcui_url = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
                        rxcui_params = {"name": label, "allsrc": "0"}
                        rxcui_response = requests.get(rxcui_url, params=rxcui_params, timeout=5)
                        if rxcui_response.status_code == 200:
                            rxcui_data = rxcui_response.json()
                            id_group = rxcui_data.get("idGroup", {})
                            rxcuis = id_group.get("rxnormId", [])
                            if rxcuis:
                                rxcui = str(rxcuis[0]) if isinstance(rxcuis, list) else str(rxcuis)
                    except Exception:
                        pass  # If lookup fails, skip this item
                
                if not rxcui:
                    continue  # Skip items without RxCUI
                
                # Skip duplicates by RxCUI
                if rxcui in seen_rxcuis:
                    continue
                seen_rxcuis.add(rxcui)
                
                # Parse metadata from the label string
                metadata = self._parse_drug_string(label)
                
                # Try to get strengths/forms from extra_fields if available
                strengths_forms = extra_fields.get("STRENGTHS_AND_FORMS", [])
                if i < len(strengths_forms) and isinstance(strengths_forms[i], list) and len(strengths_forms[i]) > 0:
                    # Use the first strength/form combination if available
                    first_sf = strengths_forms[i][0]
                    if first_sf and not metadata.get("strength"):
                        # Try to extract strength from the string (e.g., "10mg Tab")
                        strength_match = re.search(r'(\d+\.?\d*\s?(?:mg|ml|mcg|g|%|units?|iu))', first_sf, re.IGNORECASE)
                        if strength_match:
                            metadata["strength"] = strength_match.group(1)
                        # Try to extract form
                        for form in ["tablet", "capsule", "solution", "suspension", "cream", "ointment"]:
                            if form in first_sf.lower() and not metadata.get("form"):
                                metadata["form"] = form.title()
                                break
                
                suggestions.append({
                    "label": label,        # Display Name
                    "value": rxcui,        # RxCUI (Critical for searching)
                    "metadata": metadata   # Autofill data
                })
                
                if len(suggestions) >= limit:
                    break
            
            print(f"RxTerms fallback for 3-char query '{query}': found {len(suggestions)} suggestions", file=sys.stderr)
            return suggestions
            
        except Exception as e:
            print(f"Error in RxTerms fallback for 3-char query: {e}", file=sys.stderr)
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
            return []
    
    def _parse_drug_string(self, text: str) -> Dict[str, str]:
        """
        Helper to extract Strength, Route, and Form from a standard RxNorm string.
        Naive implementation based on standard ordering: Ingredient + Strength + Route + Form
        
        Args:
            text: Drug name string from RxNav (e.g., "Lisinopril 10 MG Oral Tablet")
            
        Returns:
            Dictionary with 'strength', 'route', and 'form' keys
        """
        metadata = {"strength": "", "route": "", "form": ""}
        
        if not text:
            return metadata
        
        # This is a heuristic parser. RxNorm strings are generally structured.
        # Real production apps often call /rxcui/{id}/allProperties for exact details,
        # but to save API calls (as per MTM doc), we parse the string.
        
        lower_text = text.lower()
        
        # Attempt to find Route (common routes)
        routes = ["oral", "topical", "intravenous", "injection", "ophthalmic", 
                  "sublingual", "intramuscular", "subcutaneous", "rectal", "vaginal",
                  "otic", "nasal", "inhalation", "transdermal", "buccal"]
        for r in routes:
            if r in lower_text:
                metadata["route"] = r.title()
                break
        
        # Attempt to find Form
        forms = ["tablet", "capsule", "solution", "suspension", "cream", "ointment", 
                "injection", "syrup", "gel", "lotion", "spray", "drops", "patch",
                "suppository", "film", "powder", "granules", "lozenge", "paste"]
        for f in forms:
            if f in lower_text:
                metadata["form"] = f.title()
                break
        
        # Attempt to find Strength (digits followed by mg, ml, %, etc)
        # Regex looks for number followed by unit
        match = re.search(r'(\d+\.?\d*\s?(?:mg|ml|mcg|g|%|units?|iu))', text, re.IGNORECASE)
        if match:
            metadata["strength"] = match.group(1)
        
        return metadata
    
    def search_with_excipients(
        self,
        drug_name: str,
        excipients: List[str],
        page: int = 1,
        pagesize: int = 25
    ) -> Dict[str, Any]:
        """
        Search for drugs and filter by excipients (inactive ingredients).
        Results are sorted: first those free from excipients, then those with excipients.
        
        Args:
            drug_name: Drug name to search for
            excipients: List of excipient names to check for (not exclude - we show all results)
            page: Page number
            pagesize: Number of results per page
            
        Returns:
            Dictionary with 'results_free', 'results_with', 'metadata', and 'excipients_highlighted'
        """
        # Create a mock argparse.Namespace for search_with_filters
        # Use exclude-inactive to filter at the API level for better performance
        class MockArgs:
            def __init__(self):
                self.drug_name = drug_name
                self.page = page
                self.pagesize = pagesize
                self.route = None
                self.form = None
                self.only_active = None
                self.include_active = None
                self.exclude_active = None
                self.include_inactive = None
                # Use exclude-inactive to filter out results with excipients at API level
                # But we'll still show all results, just sorted - so we don't exclude here
                # Instead, we'll get all results and sort them
                self.exclude_inactive = None  # Get all results, sort them client-side
        
        args = MockArgs()
        
        # Get all results using search_with_filters (which uses the "search" command logic)
        all_results = []
        try:
            for result in self.api.search_with_filters(args):
                all_results.append(result)
        except Exception as e:
            print(f"Error in search_with_excipients: {e}", file=sys.stderr)
            return {
                "results_free": [],
                "results_with": [],
                "metadata": {},
                "excipients_highlighted": excipients
            }
        
        # Separate results: free from excipients vs with excipients
        results_free = []
        results_with = []
        
        # Create a set of excipient keywords for matching (case-insensitive, partial matching)
        excipients_lower = {exc.lower() for exc in excipients} if excipients else set()
        
        for result in all_results:
            # If no excipients specified, all results go to "free" category
            if not excipients_lower:
                # Don't enrich here - skip enrichment to improve performance
                # Only add basic fields
                result["ndc"] = "N/A"
                result["packager"] = "N/A"
                result["dailymed_link"] = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={result.get('set_id', '')}"
                result["drug_type"] = result.get("form_code_display", "N/A")
                active = result.get("active", [])
                result["dosage"] = ", ".join([f"{ing.get('name', '')} {ing.get('strength', '')}" for ing in active]) if active else "N/A"
                results_free.append(result)
                continue
            
            # Check if result contains any of the excipients
            inactive_ingredients = result.get("inactive", [])
            inactive_lower = {ing.lower() for ing in inactive_ingredients}
            
            # Check for partial matches (e.g., "Aspartame" matches "aspartame")
            contains_excipient = False
            for exc_lower in excipients_lower:
                # Check if any inactive ingredient contains or is contained by the excipient
                for ing_lower in inactive_lower:
                    if exc_lower in ing_lower or ing_lower in exc_lower:
                        contains_excipient = True
                        break
                if contains_excipient:
                    break
            
            # Don't enrich here - skip enrichment to improve performance
            # Only add basic fields
            result["ndc"] = "N/A"
            result["packager"] = "N/A"
            result["dailymed_link"] = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={result.get('set_id', '')}"
            result["drug_type"] = result.get("form_code_display", "N/A")
            active = result.get("active", [])
            result["dosage"] = ", ".join([f"{ing.get('name', '')} {ing.get('strength', '')}" for ing in active]) if active else "N/A"
            
            if contains_excipient:
                results_with.append(result)
            else:
                results_free.append(result)
        
        return {
            "results_free": results_free,
            "results_with": results_with,
            "metadata": {
                "total_free": len(results_free),
                "total_with": len(results_with),
                "total": len(all_results),
            },
            "excipients_highlighted": excipients
        }
    
    def _enrich_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a search result with additional data like NDC and packager.
        
        Args:
            result: Basic result from search_with_filters
            
        Returns:
            Enriched result with NDC, packager, and DailyMed link
        """
        set_id = result.get("set_id")
        if not set_id:
            return result
        
        # Get NDCs for this SPL
        try:
            ndc_data = self.api.get_spl_ndcs(set_id)
            ndcs = ndc_data.get("data", [])
            # Get the first NDC if available
            ndc = ndcs[0].get("ndc", "N/A") if ndcs else "N/A"
            
            # Get packaging info for packager name
            packaging_data = self.api.get_spl_packaging(set_id)
            packaging = packaging_data.get("data", [])
            packager = packaging[0].get("labeler_name", "N/A") if packaging else "N/A"
        except Exception:
            ndc = "N/A"
            packager = "N/A"
        
        # Create DailyMed link
        dailymed_link = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
        
        # Determine drug type from form
        form = result.get("form_code_display", "N/A")
        drug_type = form  # Form is the drug type
        
        # Get dosage from active ingredients
        active = result.get("active", [])
        dosage = ", ".join([f"{ing.get('name', '')} {ing.get('strength', '')}" for ing in active]) if active else "N/A"
        
        result.update({
            "ndc": ndc,
            "packager": packager,
            "drug_type": drug_type,
            "dosage": dosage,
            "dailymed_link": dailymed_link,
        })
        
        return result

