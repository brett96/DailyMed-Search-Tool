"""
Service layer for DailyMed API integration.
Wraps the DailyMed API client for use in Django views.
"""
import sys
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
    
    def _create_mock_args(self, drug_name: str, page: int = 1, pagesize: int = 25):
        """Create a mock argparse.Namespace for search_with_filters."""
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
                self.exclude_inactive = None
        
        return MockArgs()
    
    def get_drug_autocomplete(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get drug name suggestions for autocomplete using RxTerms API.
        
        Args:
            query: Search query (minimum 3 characters)
            limit: Maximum number of results to return
            
        Returns:
            List of drug name dictionaries with 'name' and 'manufacturer' keys
        """
        if len(query) < 3:
            return []
        
        try:
            # Use RxTerms API for autocomplete
            import requests
            url = "https://clinicaltables.nlm.nih.gov/api/rxterms/v3/search"
            params = {
                "terms": query,
                "maxList": min(limit, 500),
                "df": "DISPLAY_NAME",
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # RxTerms API returns: [total_count, [codes], {extra_fields}, [display_strings], [code_systems]]
            data = response.json()
            
            if not isinstance(data, list) or len(data) < 4:
                print(f"Unexpected RxTerms API response format: {data}", file=sys.stderr)
                return []
            
            display_strings = data[3] if len(data) > 3 else []
            
            if not display_strings:
                print(f"No display strings in RxTerms response for query '{query}'", file=sys.stderr)
                return []
            
            # Extract unique drug names
            seen_names = set()
            suggestions = []
            
            for display_name in display_strings:
                # Each display_name is an array with one element: [["DRUG NAME (Route)"]]
                if isinstance(display_name, list) and len(display_name) > 0:
                    full_name = display_name[0] if isinstance(display_name[0], str) else str(display_name[0])
                elif isinstance(display_name, str):
                    full_name = display_name
                else:
                    continue
                
                if not full_name or not full_name.strip():
                    continue
                
                # Extract route from name if present (format: "DRUG NAME (Route)")
                # Keep the full name for display, but extract just the drug name for matching
                drug_name = full_name.strip()
                route = ""
                if "(" in drug_name and ")" in drug_name:
                    route_start = drug_name.rfind("(")
                    route_end = drug_name.rfind(")")
                    if route_start < route_end:
                        route = drug_name[route_start + 1:route_end].strip()
                        drug_name = drug_name[:route_start].strip()
                
                # Use the drug name (without route) for uniqueness check
                if drug_name.lower() not in seen_names:
                    seen_names.add(drug_name.lower())
                    suggestions.append({
                        "name": full_name.strip(),  # Return full name with route for display
                        "manufacturer": route or "",  # Using route as secondary info
                    })
                    
                    if len(suggestions) >= limit:
                        break
            
            print(f"RxTerms autocomplete for '{query}': found {len(suggestions)} suggestions", file=sys.stderr)
            return suggestions
        except Exception as e:
            # Log error but return empty list
            print(f"Error in drug autocomplete: {e}", file=sys.stderr)
            return []
    
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

