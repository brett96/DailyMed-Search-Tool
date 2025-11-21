import requests
import json
import argparse
import sys
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Union, List, Set, Generator

def print_pagination_info(args: argparse.Namespace, metadata: Dict[str, Any]):
    """
    Checks API response metadata and prints a 'next page' command if applicable.
    """
    try:
        current_page = int(metadata.get("current_page", 1))
        total_pages = int(metadata.get("total_pages", 0))

        if current_page < total_pages:
            next_page = current_page + 1
            
            # Reconstruct the command from sys.argv
            command_args = sys.argv[1:] # Get all args: ['search-spls', '--drug_name', 'ibuprofen']
            page_found = False

            for i, arg in enumerate(command_args):
                if arg == "--page":
                    if i + 1 < len(command_args):
                        command_args[i+1] = str(next_page) # Update page number
                        page_found = True
                    break
            
            if not page_found:
                # Insert --page {next_page} right after the command
                command_args.insert(3, "--page")
                command_args.insert(4, str(next_page))
            
            print("\n" + ("-" * 20))
            print(f"More results available (Page {current_page} of {total_pages}).")
            print("To get the next page, run:")
            print(f"  python {sys.argv[0]} {' '.join(command_args)}")
    except Exception as e:
        # Fail silently if metadata is malformed
        print(f"[Warning] Could not parse pagination: {e}", file=sys.stderr)


class DailyMedAPI:
    """
    A Python client for interacting with the DailyMed RESTful API (v2).
    
    This client provides methods to access various endpoints of the DailyMed API,
    handling HTTP requests and JSON/XML responses.
    """
    
    BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

    def _add_if_present(self, params: Dict[str, Any], key: str, value: Optional[Any]):
        """Helper to add a parameter to the dict if it's not None."""
        if value is not None:
            params[key] = value

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], str]:
        """
        Internal helper method to make a GET request to the DailyMed API.

        Args:
            endpoint: The API endpoint to call (e.g., "spls.json").
            params: A dictionary of query parameters for the request.

        Returns:
            A dictionary parsed from the JSON response or an XML string.
            
        Raises:
            requests.exceptions.HTTPError: If the API returns an error status code.
            requests.exceptions.RequestException: For other network or request-related issues.
            json.JSONDecodeError: If the response is not valid JSON.
        """
        
        # Clean params dictionary of None values
        clean_params = {}
        if params:
            for key, value in params.items():
                if value is not None:
                    # Special handling for bool
                    if isinstance(value, bool):
                         clean_params[key] = str(value).lower()
                    else:
                        clean_params[key] = value
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=clean_params, timeout=10)
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            
            # Handle XML endpoint specifically
            if endpoint.endswith(".xml"):
                return response.text

            # Handle JSON endpoints (default)
            # Handle potential empty responses for some endpoints
            if not response.content:
                return {"message": "Request successful, but no content returned."}
                
            return response.json()
        
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} - {response.status_code} {response.text}", file=sys.stderr)
            raise
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}", file=sys.stderr)
            raise
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}", file=sys.stderr)
            raise
        except requests.exceptions.RequestException as req_err:
            print(f"An unexpected error occurred: {req_err}", file=sys.stderr)
            raise
        except json.JSONDecodeError:
            # This can happen if the API returns XML on an error, etc.
            print(f"Failed to decode JSON response from {url}", file=sys.stderr)
            print(f"Response text: {response.text[:200]}...", file=sys.stderr)
            raise

    def search_spls(
        self, 
        page: int = 1, 
        pagesize: int = 25,
        application_number: Optional[str] = None,
        boxed_warning: Optional[bool] = None,
        dea_schedule_code: Optional[str] = None,
        doctype: Optional[str] = None,
        drug_class_code: Optional[str] = None,
        drug_class_coding_system: Optional[str] = None,
        drug_name: Optional[str] = None,
        name_type: Optional[str] = None,
        labeler: Optional[str] = None,
        manufacturer: Optional[str] = None,
        marketing_category_code: Optional[str] = None,
        ndc: Optional[str] = None,
        published_date: Optional[str] = None,
        published_date_comparison: Optional[str] = None,
        rxcui: Optional[str] = None,
        setid: Optional[str] = None,
        unii_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Searches for Structured Product Labeling (SPLs) documents with advanced filters.
        """
        print(f"\nSearching SPLs (Page {page}, Size {pagesize}) with filters...")
        
        params = {"page": page, "pagesize": pagesize}
        self._add_if_present(params, 'application_number', application_number)
        
        # This is tricky in argparse. Store it as a string.
        if boxed_warning is not None:
             self._add_if_present(params, 'boxed_warning', str(boxed_warning).lower())
        
        self._add_if_present(params, 'dea_schedule_code', dea_schedule_code)
        self._add_if_present(params, 'doctype', doctype)
        self._add_if_present(params, 'drug_class_code', drug_class_code)
        self._add_if_present(params, 'drug_class_coding_system', drug_class_coding_system)
        self._add_if_present(params, 'drug_name', drug_name)
        self._add_if_present(params, 'name_type', name_type)
        self._add_if_present(params, 'labeler', labeler)
        self._add_if_present(params, 'manufacturer', manufacturer)
        self._add_if_present(params, 'marketing_category_code', marketing_category_code)
        self._add_if_present(params, 'ndc', ndc)
        self._add_if_present(params, 'published_date', published_date)
        self._add_if_present(params, 'published_date_comparison', published_date_comparison)
        self._add_if_present(params, 'rxcui', rxcui)
        self._add_if_present(params, 'setid', setid)
        self._add_if_present(params, 'unii_code', unii_code)
        
        return self._make_request("spls.json", params=params)

    def get_spl_by_setid(self, set_id: str) -> str:
        """
        Retrieves a specific SPL document using its SET ID.
        This endpoint returns a raw XML string.
        
        Args:
            set_id: The SET ID of the SPL document.

        Returns:
            The XML response string from the API.
        """
        print(f"\nGetting SPL for SET ID: {set_id}...")
        # This endpoint returns XML, not JSON
        return self._make_request(f"spls/{set_id}.xml", params=None)

    def get_spl_history(self, set_id: str) -> Dict[str, Any]:
        """
        Retrieves the version history for a specific SPL.
        """
        print(f"\nGetting SPL history for SET ID: {set_id}...")
        return self._make_request(f"spls/{set_id}/history.json", params=None)

    def get_spl_ndcs(self, set_id: str) -> Dict[str, Any]:
        """
        Retrieves all NDCs associated with a specific SPL.
        """
        print(f"\nGetting NDCs for SET ID: {set_id}...")
        return self._make_request(f"spls/{set_id}/ndcs.json", params=None)

    def get_spl_packaging(self, set_id: str) -> Dict[str, Any]:
        """
        Retrieves product packaging information for a specific SPL.
        """
        print(f"\nGetting packaging info for SET ID: {set_id}...")
        return self._make_request(f"spls/{set_id}/packaging.json", params=None)

    def get_drug_names(
        self, 
        page: int = 1, 
        pagesize: int = 10,
        manufacturer: Optional[str] = None,
        name_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves a list of all drug names, with optional filters.
        """
        print(f"\nGetting drug names (Page {page}, Size {pagesize})...")
        params = {"page": page, "pagesize": pagesize}
        self._add_if_present(params, 'manufacturer', manufacturer)
        self._add_if_present(params, 'name_type', name_type)
        return self._make_request("drugnames.json", params=params)

    def get_ndcs(
        self, 
        page: int = 1, 
        pagesize: int = 10,
        application_number: Optional[str] = None,
        labeler: Optional[str] = None,
        marketing_category_code: Optional[str] = None,
        setid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves a list of all NDCs, with optional filters.
        """
        print(f"\nGetting NDCs (Page {page}, Size {pagesize})...")
        params = {"page": page, "pagesize": pagesize}
        self._add_if_present(params, 'application_number', application_number)
        self._add_if_present(params, 'labeler', labeler)
        self._add_if_present(params, 'marketing_category_code', marketing_category_code)
        self._add_if_present(params, 'setid', setid)
        return self._make_request("ndcs.json", params=params)

    def get_drug_classes(
        self, 
        page: int = 1, 
        pagesize: int = 10,
        drug_class_code: Optional[str] = None,
        drug_class_coding_system: Optional[str] = None,
        class_code_type: Optional[str] = None,
        class_name: Optional[str] = None,
        unii_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves a list of all drug classes, with optional filters.
        """
        print(f"\nGetting drug classes (Page {page}, Size {pagesize})...")
        params = {"page": page, "pagesize": pagesize}
        self._add_if_present(params, 'drug_class_code', drug_class_code)
        self._add_if_present(params, 'drug_class_coding_system', drug_class_coding_system)
        self._add_if_present(params, 'class_code_type', class_code_type)
        self._add_if_present(params, 'class_name', class_name)
        self._add_if_present(params, 'unii_code', unii_code)
        return self._make_request("drugclasses.json", params=params)

    def get_uniis(
        self, 
        page: int = 1, 
        pagesize: int = 10,
        active_moiety: Optional[str] = None,
        drug_class_code: Optional[str] = None,
        drug_class_coding_system: Optional[str] = None,
        rxcui: Optional[str] = None,
        unii_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves a list of all Unique Ingredient Identifiers (UNIIs), with optional filters.
        """
        print(f"\nGetting UNIIs (Page {page}, Size {pagesize})...")
        params = {"page": page, "pagesize": pagesize}
        self._add_if_present(params, 'active_moiety', active_moiety)
        self._add_if_present(params, 'drug_class_code', drug_class_code)
        self._add_if_present(params, 'drug_class_coding_system', drug_class_coding_system)
        self._add_if_present(params, 'rxcui', rxcui)
        self._add_if_present(params, 'unii_code', unii_code)
        return self._make_request("uniis.json", params=params)

    def get_rxcuis(
        self,
        page: int = 1,
        pagesize: int = 10,
        rxcui: Optional[str] = None,
        rxstring: Optional[str] = None,
        rxtty: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves a list of all RxNorm Concept Unique Identifiers (RxCUIs), with optional filters.
        """
        print(f"\nGetting RxCUIs (Page {page}, Size {pagesize})...")
        params = {"page": page, "pagesize": pagesize}
        self._add_if_present(params, 'rxcui', rxcui)
        self._add_if_present(params, 'rxstring', rxstring)
        self._add_if_present(params, 'rxtty', rxtty)
        return self._make_request("rxcuis.json", params=params)

    def _parse_spl_xml(self, xml_string: str) -> Optional[Dict[str, Any]]:
        """
        Internal helper to parse a raw SPL XML string into a structured dictionary.

        Args:
            xml_string: The raw XML content of an SPL.

        Returns:
            A dictionary with parsed data, or None if parsing fails.
        """
        try:
            # Remove default namespace (xmlns) to simplify findall
            xml_string = xml_string.replace('xmlns="urn:hl7-org:v3"', '', 1)
            root = ET.fromstring(xml_string)
            
            parsed_data = {
                "set_id": None,
                "title": "N/A",
                "form_code_display": "N/A",
                "route_code_display": "N/A",
                "active": [],
                "inactive": []
            }

            # Find Set ID
            set_id_elem = root.find(".//setId")
            if set_id_elem is not None:
                parsed_data["set_id"] = set_id_elem.get("root")

            active_ingredients = []
            inactive_ingredients_structured = set()
            inactive_ingredients_text = set()
            data_section = None
            inactive_section = None

            # Find relevant sections first (needed for title extraction)
            for section in root.findall(".//section"):
                code_elem = section.find("./code")
                if code_elem is not None:
                    code = code_elem.get("code")
                    if code == "48780-1": # "SPL product data elements section"
                        data_section = section
                    elif code == "51727-6": # "INACTIVE INGREDIENT SECTION"
                        inactive_section = section

            # Find Title - try multiple sources
            title_text = None
            
            # First, try to find the product name in the manufacturedProduct section
            if data_section is not None:
                product_name_elem = data_section.find(".//manufacturedProduct/name")
                if product_name_elem is not None:
                    title_text = " ".join(str(product_name_elem.text).split()).strip() if product_name_elem.text else None
                    if not title_text:
                        title_text = " ".join("".join(product_name_elem.itertext()).split()).strip()
            
            # Fallback to document title if product name not found
            if not title_text:
                title_elem = root.find(".//title")
                if title_elem is not None:
                    # Remove extra whitespace/newlines from title
                    title_text = " ".join(str(title_elem.text).split()).strip()
                    if not title_text:
                        # Fallback for complex titles with <sup> tags etc.
                        title_text = " ".join("".join(title_elem.itertext()).split()).strip()
                    
                    # If title is just "Drug Facts", try to find a better name
                    if title_text and title_text.lower() in ["drug facts", "drug facts label"]:
                        # Try to find product name in data_section
                        if data_section is not None:
                            product_elem = data_section.find(".//manufacturedProduct/name")
                            if product_elem is not None:
                                product_text = " ".join("".join(product_elem.itertext()).split()).strip()
                                if product_text:
                                    title_text = product_text
                            else:
                                # Try to construct from active ingredients
                                active_names = []
                                for ingredient in data_section.findall(".//ingredient[@classCode='ACTIB']"):
                                    name_elem = ingredient.find(".//ingredientSubstance/name")
                                    if name_elem is not None and name_elem.text:
                                        active_names.append(name_elem.text.strip())
                                if active_names:
                                    title_text = " / ".join(active_names)
                        else:
                            # Try to find product name anywhere in the document
                            product_elem = root.find(".//manufacturedProduct/name")
                            if product_elem is not None:
                                product_text = " ".join("".join(product_elem.itertext()).split()).strip()
                                if product_text:
                                    title_text = product_text
            
            parsed_data["title"] = title_text if title_text else "N/A"
            
            if data_section is not None:
                # Find Form Code
                form_code_elem = data_section.find(".//manufacturedProduct/formCode")
                if form_code_elem is not None:
                    parsed_data["form_code_display"] = form_code_elem.get("displayName", "N/A")

                # Find Route Code
                route_code_elem = data_section.find(".//substanceAdministration/routeCode")
                if route_code_elem is not None:
                    parsed_data["route_code_display"] = route_code_elem.get("displayName", "N/A")
                
                # Find Structured Active Ingredients (ACTIB)
                for ingredient in data_section.findall(".//ingredient[@classCode='ACTIB']"):
                    name_elem = ingredient.find(".//ingredientSubstance/name")
                    name = name_elem.text if name_elem is not None else "Unknown"
                    
                    numerator_elem = ingredient.find(".//quantity/numerator")
                    if numerator_elem is not None:
                        value = numerator_elem.get('value', 'N/A')
                        unit = numerator_elem.get('unit', '')
                        strength = f"{value} {unit}".strip()
                    else:
                        strength = "Strength not specified"
                    
                    active_ingredients.append({'name': name.title(), 'strength': strength})

                # Find Structured Inactive Ingredients (IACT)
                for ingredient in data_section.findall(".//ingredient[@classCode='IACT']"):
                    name_elem = ingredient.find(".//ingredientSubstance/name")
                    if name_elem is not None:
                        inactive_ingredients_structured.add(name_elem.text.strip().upper())
            
            # Find Human-Readable Inactive Ingredients (Fallback)
            if inactive_section is not None:
                para_texts = []
                # Find text inside all paragraphs and their children (like <content>)
                for para in inactive_section.findall(".//paragraph"):
                    text = "".join(para.itertext()).strip()
                    if text:
                        para_texts.append(text)
                
                if para_texts:
                    full_text = " ".join(para_texts).lower()
                    if full_text.startswith("inactive ingredients"):
                        full_text = full_text[len("inactive ingredients"):].strip()
                    full_text = full_text.strip(".: ")
                    
                    ingredients_list = full_text.split(',')
                    for item in ingredients_list:
                        clean_item = item.strip().upper()
                        if clean_item:
                            if " AND " in clean_item:
                                sub_items = clean_item.split(" AND ")
                                for sub in sub_items:
                                    if sub.strip():
                                        inactive_ingredients_text.add(sub.strip())
                            else:
                                inactive_ingredients_text.add(clean_item)

            # Combine and title-case ingredients
            parsed_data["active"] = active_ingredients
            combined_inactive = inactive_ingredients_structured.union(inactive_ingredients_text)
            parsed_data["inactive"] = sorted([item.title() for item in combined_inactive if item]) 

            return parsed_data

        except ET.ParseError as e:
            print(f"Failed to parse XML: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"An unexpected error occurred during XML parsing: {e}", file=sys.stderr)
            return None


    def get_ingredients_from_spl(self, set_id: str) -> Dict[str, Any]:
        """
        Fetches an SPL XML, parses it, and extracts active and inactive ingredients.
        
        Args:
            set_id: The SET ID of the SPL document.

        Returns:
            A dictionary with 'active' and 'inactive' keys.
        """
        print(f"\nFetching SPL for SET ID: {set_id} to parse ingredients...")
        
        try:
            xml_string = self._make_request(f"spls/{set_id}.xml", params=None)
            if not isinstance(xml_string, str):
                raise ValueError("Failed to fetch XML, API did not return string.")
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch SPL XML: {e}", file=sys.stderr)
            raise 

        parsed_data = self._parse_spl_xml(xml_string)
        
        if parsed_data:
            # Return only the ingredient parts for this function
            return {"active": parsed_data.get("active", []), "inactive": parsed_data.get("inactive", [])}
        else:
            raise ValueError(f"Failed to parse XML for SET ID {set_id}")

    def search_with_filters(
        self,
        args: argparse.Namespace
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Performs a basic search, then applies advanced filters by fetching each SPL.
        This is a multi-step process and may be slow.
        """
        # Extract arguments from the args object
        drug_name = args.drug_name
        pagesize = args.pagesize
        page = args.page
        route = args.route
        form = args.form # NEW
        only_active = args.only_active
        include_active = args.include_active
        exclude_active = args.exclude_active
        include_inactive = args.include_inactive
        exclude_inactive = args.exclude_inactive

        print(f"Starting advanced search for '{drug_name}' (Page {page}, processing up to {pagesize} results)...")
        print("This may take a moment as each result is fetched and parsed.")

        # 1. Initial search
        metadata = None
        try:
            initial_results = self.search_spls(drug_name=drug_name, pagesize=pagesize, page=page)
            metadata = initial_results.get("metadata") # Get metadata for pagination
        except requests.exceptions.RequestException as e:
            print(f"Initial API search failed: {e}", file=sys.stderr)
            yield # Stop generation
            return # Exit function

        data_results = initial_results.get("data")
        
        if not data_results:
            print("No initial results found.")
            yield # Stop generation
            return # Exit function

        # 2. Prepare filter keywords (convert to lowercase sets for comparison)
        route_filter = route.lower() if route else None
        form_filter = {k.lower() for k in form} if form else set() # NEW
        only_act_filts = {k.lower() for k in only_active} if only_active else set()
        inc_act = {k.lower() for k in include_active} if include_active else set()
        exc_act = {k.lower() for k in exclude_active} if exclude_active else set()
        inc_inact = {k.lower() for k in include_inactive} if include_inactive else set()
        exc_inact = {k.lower() for k in exclude_inactive} if exclude_inactive else set()

        # 3. Iterate, fetch, parse, and filter
        count = 0
        for i, item in enumerate(data_results): # Use data_results here
            
            # The API returns "setid", not "set_id" in the search-spls response
            set_id = item.get("setid") 
            
            if not set_id:
                continue
            
            try:
                xml_string = self._make_request(f"spls/{set_id}.xml", params=None)
                if not isinstance(xml_string, str):
                    continue
                
                parsed_data = self._parse_spl_xml(xml_string)
                if not parsed_data:
                    continue
                
                # --- Filtering Logic ---
                
                # Check Route
                parsed_route = parsed_data["route_code_display"].lower()
                if route_filter and route_filter not in parsed_route:
                    continue

                # Check Form (NEW)
                # We check if *any* of the filter keywords are in the form string
                parsed_form = parsed_data["form_code_display"].lower()
                if form_filter and not any(filt in parsed_form for filt in form_filter):
                    continue

                # Prepare lowercase ingredient lists from parsed data
                active_list_lower = {ing["name"].lower() for ing in parsed_data["active"]}
                inactive_list_lower = {ing.lower() for ing in parsed_data["inactive"]}
                
                # Check Include Active
                # We must match ALL keywords in the include list
                if inc_act and not all(any(filt in active for active in active_list_lower) for filt in inc_act):
                    continue
                
                # Check Exclude Active
                # We fail if ANY excluded keyword is found
                if exc_act and any(any(filt in active for active in active_list_lower) for filt in exc_act):
                    continue

                # Check Include Inactive
                if inc_inact and not all(any(filt in inactive for inactive in inactive_list_lower) for filt in inc_inact):
                    continue

                # Check Exclude Inactive
                if exc_inact and any(any(filt in inactive for inactive in inactive_list_lower) for filt in exc_inact):
                    continue
                
                # Check Only Active
                # Ensures ALL active ingredients found match at least ONE of the provided keywords
                if only_act_filts and not all(any(filt in ing for filt in only_act_filts) for ing in active_list_lower):
                    continue # Skip, as it contains an "un-approved" active ingredient

                # --- If it passes all filters, yield it ---
                count += 1
                yield parsed_data

            except Exception as e:
                print(f"    [ERROR] Failed to process SET ID {set_id}: {e}", file=sys.stderr)
                continue
        
        print(f"\nAdvanced search complete. Found {count} matching items.")
        
        # Now print pagination info if available
        if metadata:
            print_pagination_info(args, metadata)


def pretty_print_json(data: Dict[str, Any]):
    """Helper function to print JSON data in an indented, readable format."""
    print(json.dumps(data, indent=2))

def print_ingredients(data: Dict[str, Any]):
    """Helper function to print ingredients in a readable format."""
    if not data.get('active') and not data.get('inactive'):
        print("No ingredient information could be parsed.")
        return
    
    print("--- Active Ingredients ---")
    if data.get('active'):
        for item in data['active']:
            print(f"- {item['name']} ({item['strength']})")
    else:
        print("No active ingredients found or parsed.")
    
    print("\n--- Inactive Ingredients / Excipients ---")
    if data.get('inactive'):
        for item in data['inactive']:
            print(f"- {item}")
    else:
        print("No inactive ingredients found or parsed.")

def print_search_result(data: Dict[str, Any]):
    """Helper function to print the detailed search result."""
    print("\n==================================================")
    print(f"Drug: {data.get('title', 'N/A')}")
    print(f"Form: {data.get('form_code_display', 'N/A')}")
    print(f"Route: {data.get('route_code_display', 'N/A')}")
    print(f"SET ID: {data.get('set_id', 'N/A')}")
    
    # Reuse the ingredient printer
    print_ingredients(data)
    print("==================================================")

def main():
    """
    Main function to run the command-line interface for the DailyMed API client.
    """
    # Main parser
    parser = argparse.ArgumentParser(
        description="A command-line client for the DailyMed v2 API.",
        epilog="Example: python dailymed_client.py get-ingredients \"37e939c6-064b-3548-e063-6294a90a337d\""
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="The API command to run")

    # --- NEW: search command ---
    search_parser = subparsers.add_parser("search", help="Advanced search with post-filtering (slow, supports pagination).")
    search_parser.add_argument("--drug_name", type=str, required=True, help="Base drug name to search for (e.g., 'tylenol').")
    search_parser.add_argument("--page", type=int, default=1, help="Page number of results.")
    search_parser.add_argument("--pagesize", type=int, default=25, help="Number of initial results to fetch and filter (max 100).")
    search_parser.add_argument("--route", type=str, help="Filter by route of administration (e.g., 'ORAL').")
    search_parser.add_argument("--form", nargs='+', help="Filter by dosage form (e.g., 'TABLET', 'CAPSULE').")
    search_parser.add_argument("--only-active", nargs='+', help="Ensure *only* active ingredients matching these keywords are present.")
    search_parser.add_argument("--include-active", nargs='+', help="List of keywords that MUST be in active ingredients.")
    search_parser.add_argument("--exclude-active", nargs='+', help="List of keywords that MUST NOT be in active ingredients.")
    search_parser.add_argument("--include-inactive", nargs='+', help="List of keywords that MUST be in inactive ingredients.")
    search_parser.add_argument("--exclude-inactive", nargs='+', help="List of keywords that MUST NOT be in inactive ingredients.")

    # --- search-spls command ---
    spl_parser = subparsers.add_parser("search-spls", help="Search for SPLs (drug labels).")
    spl_parser.add_argument("--page", type=int, default=1, help="Page number of results.")
    spl_parser.add_argument("--pagesize", type=int, default=25, help="Results per page (max 100).")
    spl_parser.add_argument("--application_number", type=str, help="Filter by NDA number.")
    
    # Correct way to handle boolean flags in argparse
    spl_parser.add_argument("--boxed_warning", action=argparse.BooleanOptionalAction, help="Filter by boxed warning (use --boxed_warning or --no-boxed_warning).")
    
    spl_parser.add_argument("--dea_schedule_code", type=str, help="Filter by DEA schedule (e.g., 'C48676' for CIII).")
    spl_parser.add_argument("--doctype", type=str, help="Filter by document type (e.g., 'C78841' for HUMAN_PRESCRIPTION_DRUG_LABEL).")
    spl_parser.add_argument("--drug_class_code", type=str, help="Filter by drug class code.")
    spl_parser.add_argument("--drug_class_coding_system", type=str, help="Coding system for drug_class_code.")
    spl_parser.add_argument("--drug_name", type=str, help="Search by drug name (e.g., 'aspirin').")
    spl_parser.add_argument("--name_type", type=str, help="Type of name (g' for generic, 'b' for brand).")
    spl_parser.add_argument("--labeler", type=str, help="Filter by labeler name.")
    spl_parser.add_argument("--manufacturer", type=str, help="Filter by manufacturer name.")
    spl_parser.add_argument("--marketing_category_code", type=str, help="Filter by marketing category (e.g., 'C73384' for NDA).")
    spl_parser.add_argument("--ndc", type=str, help="Search by NDC code.")
    spl_parser.add_argument("--published_date", type=str, help="Filter by published date (YYYY-MM-DD).")
    spl_parser.add_argument("--published_date_comparison", type=str, help="Comparison for date (lt, lte, gt, gte, eq).")
    spl_parser.add_argument("--rxcui", type=str, help="Filter by RxNorm CUI.")
    spl_parser.add_argument("--setid", type=str, help="Filter by SPL SET ID.")
    spl_parser.add_argument("--unii_code", type=str, help="Filter by UNII code.")


    # --- get-spl command ---
    get_spl_parser = subparsers.add_parser("get-spl", help="Get a specific SPL by its SET ID (raw XML).")
    get_spl_parser.add_argument("set_id", type=str, help="The SET ID of the SPL.")

    # --- get-ingredients command ---
    ingredients_parser = subparsers.add_parser("get-ingredients", help="Parse and list ingredients for an SPL.")
    ingredients_parser.add_argument("set_id", type=str, help="The SET ID of the SPL.")

    # --- get-spl-history command ---
    history_parser = subparsers.add_parser("get-spl-history", help="Get the version history for an SPL.")
    history_parser.add_argument("set_id", type=str, help="The SET ID of the SPL.")

    # --- get-spl-ndcs command ---
    ndcs_parser = subparsers.add_parser("get-spl-ndcs", help="Get the NDCs for an SPL.")
    ndcs_parser.add_argument("set_id", type=str, help="The SET ID of the SPL.")
    
    # --- get-spl-packaging command ---
    pkg_parser = subparsers.add_parser("get-spl-packaging", help="Get the packaging information for an SPL.")
    pkg_parser.add_argument("set_id", type=str, help="The SET ID of the SPL.")

    # --- Listing commands (drugnames, ndcs, drugclasses, uniis, rxcuis) ---
    
    # get-drugnames
    drugnames_parser = subparsers.add_parser("get-drugnames", help="Get a list of all drugnames.")
    drugnames_parser.add_argument("--page", type=int, default=1, help="Page number of results.")
    drugnames_parser.add_argument("--pagesize", type=int, default=10, help="Results per page (max 100).")
    drugnames_parser.add_argument("--manufacturer", type=str, help="Filter by manufacturer name.")
    drugnames_parser.add_argument("--name_type", type=str, help="Filter by name type ('g' for generic, 'b' for brand).")

    # get-ndcs
    ndcs_list_parser = subparsers.add_parser("get-ndcs", help="Get a list of all ndcs.")
    ndcs_list_parser.add_argument("--page", type=int, default=1, help="Page number of results.")
    ndcs_list_parser.add_argument("--pagesize", type=int, default=10, help="Results per page (max 100).")
    ndcs_list_parser.add_argument("--application_number", type=str, help="Filter by NDA number.")
    ndcs_list_parser.add_argument("--labeler", type=str, help="Filter by labeler name.")
    ndcs_list_parser.add_argument("--marketing_category_code", type=str, help="Filter by marketing category.")
    ndcs_list_parser.add_argument("--setid", type=str, help="Filter by SPL SET ID.")

    # get-drugclasses
    drugclasses_parser = subparsers.add_parser("get-drugclasses", help="Get a list of all drugclasses.")
    drugclasses_parser.add_argument("--page", type=int, default=1, help="Page number of results.")
    drugclasses_parser.add_argument("--pagesize", type=int, default=10, help="Results per page (max 100).")
    drugclasses_parser.add_argument("--drug_class_code", type=str, help="Filter by drug class code.")
    drugclasses_parser.add_argument("--drug_class_coding_system", type=str, help="Coding system for drug_class_code.")
    drugclasses_parser.add_argument("--class_code_type", type=str, help="Filter by class code type (e.g., 'epc', 'moa').")
    drugclasses_parser.add_argument("--class_name", type=str, help="Filter by class name (e.g., 'opioid').")
    drugclasses_parser.add_argument("--unii_code", type=str, help="Filter by UNII code.")

    # get-uniis
    uniis_parser = subparsers.add_parser("get-uniis", help="Get a list of all uniis.")
    uniis_parser.add_argument("--page", type=int, default=1, help="Page number of results.")
    uniis_parser.add_argument("--pagesize", type=int, default=10, help="Results per page (max 100).")
    uniis_parser.add_argument("--active_moiety", type=str, help="Filter by active moiety UNII code.")
    uniis_parser.add_argument("--drug_class_code", type=str, help="Filter by drug class code.")
    uniis_parser.add_argument("--drug_class_coding_system", type=str, help="Coding system for drug_class_code.")
    uniis_parser.add_argument("--rxcui", type=str, help="Filter by RxNorm CUI.")
    uniis_parser.add_argument("--unii_code", type=str, help="Filter by UNII code.")

    # get-rxcuis
    rxcuis_parser = subparsers.add_parser("get-rxcuis", help="Get a list of all rxcuis.")
    rxcuis_parser.add_argument("--page", type=int, default=1, help="Page number of results.")
    rxcuis_parser.add_argument("--pagesize", type=int, default=10, help="Results per page (max 100).")
    rxcuis_parser.add_argument("--rxcui", type=str, help="Filter by a specific RxCUI.")
    rxcuis_parser.add_argument("--rxstring", type=str, help="Filter by a display name string (e.g., 'aspirin').")
    rxcuis_parser.add_argument("--rxtty", type=str, help="Filter by RxNorm term type (e.g., 'IN' for Ingredient).")


    args = parser.parse_args()
    api = DailyMedAPI()
    
    try:
        # Handle non-JSON, non-looping commands first
        if args.command == "get-spl":
            xml_data = api.get_spl_by_setid(args.set_id)
            print("API Response (XML):")
            print(xml_data)
        
        elif args.command == "get-ingredients":
            ingredients_data = api.get_ingredients_from_spl(args.set_id)
            print_ingredients(ingredients_data)

        # Handle new 'search' command (looping)
        elif args.command == "search":
            results_found = 0
            # search_with_filters will now print its own pagination
            for result in api.search_with_filters(args):
                results_found += 1
                print_search_result(result)
            
            if results_found == 0:
                print("\nNo results matched all of your advanced filters.")

        else:
            # Handle all other JSON-based commands
            result = None
            if args.command == "search-spls":
                result = api.search_spls(
                    page=args.page, 
                    pagesize=args.pagesize,
                    application_number=args.application_number,
                    boxed_warning=args.boxed_warning,
                    dea_schedule_code=args.dea_schedule_code,
                    doctype=args.doctype,
                    drug_class_code=args.drug_class_code,
                    drug_class_coding_system=args.drug_class_coding_system,
                    drug_name=args.drug_name,
                    name_type=args.name_type,
                    labeler=args.labeler,
                    manufacturer=args.manufacturer,
                    marketing_category_code=args.marketing_category_code,
                    ndc=args.ndc,
                    published_date=args.published_date,
                    published_date_comparison=args.published_date_comparison,
                    rxcui=args.rxcui,
                    setid=args.setid,
                    unii_code=args.unii_code
                )
            
            elif args.command == "get-spl-history":
                result = api.get_spl_history(args.set_id)
                
            elif args.command == "get-spl-ndcs":
                result = api.get_spl_ndcs(args.set_id)
                
            elif args.command == "get-spl-packaging":
                result = api.get_spl_packaging(args.set_id)
                
            elif args.command == "get-drugnames":
                result = api.get_drug_names(
                    page=args.page, 
                    pagesize=args.pagesize,
                    manufacturer=args.manufacturer,
                    name_type=args.name_type
                )
                
            elif args.command == "get-ndcs":
                result = api.get_ndcs(
                    page=args.page, 
                    pagesize=args.pagesize,
                    application_number=args.application_number,
                    labeler=args.labeler,
                    marketing_category_code=args.marketing_category_code,
                    setid=args.setid
                )
                
            elif args.command == "get-drugclasses":
                result = api.get_drug_classes(
                    page=args.page, # Corrected from copy.page
                    pagesize=args.pagesize,
                    drug_class_code=args.drug_class_code,
                    drug_class_coding_system=args.drug_class_coding_system,
                    class_code_type=args.class_code_type,
                    class_name=args.class_name,
                    unii_code=args.unii_code
                )
                
            elif args.command == "get-uniis":
                result = api.get_uniis(
                    page=args.page, 
                    pagesize=args.pagesize,
                    active_moiety=args.active_moiety,
                    drug_class_code=args.drug_class_code,
                    drug_class_coding_system=args.drug_class_coding_system,
                    rxcui=args.rxcui,
                    unii_code=args.unii_code
                )
            
            elif args.command == "get-rxcuis":
                result = api.get_rxcuis(
                    page=args.page,
                    pagesize=args.pagesize,
                    rxcui=args.rxcui,
                    rxstring=args.rxstring,
                    rxtty=args.rxtty
                )

            if result:
                print("API Response:")
                pretty_print_json(result)
                if isinstance(result, dict) and "metadata" in result:
                    print_pagination_info(args, result["metadata"])

    except (requests.exceptions.RequestException, json.JSONDecodeError, ET.ParseError) as e:
        print(f"\nAn error occurred: {e}", file=sys.stderr)
        print("Please check your connection and the API endpoint status.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()