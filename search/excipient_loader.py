"""
Utility module to load excipient categories from Excel file.
This is used for Vercel deployment where SQLite databases are not supported.
"""
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List

# Cache the loaded data in memory
_excipient_cache: Dict[str, List[str]] = None
_cache_file_path: str = None


def get_excel_file_path() -> Path:
    """
    Get the path to the Excel file.
    Tries multiple locations for compatibility with different deployment scenarios.
    """
    base_dir = Path(__file__).resolve().parent.parent
    
    # Try different possible locations
    possible_paths = [
        base_dir / 'Excipient Categories.xlsx',
        Path.cwd() / 'Excipient Categories.xlsx',
        Path('/tmp') / 'Excipient Categories.xlsx',  # For serverless environments
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # If not found, return the most likely location
    return base_dir / 'Excipient Categories.xlsx'


def load_excipient_categories(force_reload: bool = False) -> Dict[str, List[str]]:
    """
    Load excipient categories from Excel file.
    
    Args:
        force_reload: If True, reload from file even if cached
        
    Returns:
        Dictionary mapping category names to lists of excipient ingredient names
    """
    global _excipient_cache, _cache_file_path
    
    excel_path = get_excel_file_path()
    
    # Check if we need to reload
    if _excipient_cache is None or force_reload or _cache_file_path != str(excel_path):
        try:
            # Read the Excel file
            df = pd.read_excel(excel_path)
            
            # Verify required columns exist
            if 'INGREDIENT_NAME' not in df.columns or 'Category' not in df.columns:
                raise ValueError("Excel file missing required columns: INGREDIENT_NAME, Category")
            
            # Filter out rows without category
            df = df[df['Category'].notna()]
            
            # Group by category and collect ingredient names
            result = {}
            for category_name in df['Category'].unique():
                if pd.notna(category_name):
                    category_name = str(category_name).strip()
                    ingredients = df[df['Category'] == category_name]['INGREDIENT_NAME'].dropna().unique()
                    # Convert to list and sort
                    result[category_name] = sorted([str(ing).strip() for ing in ingredients if str(ing).strip()])
            
            # Cache the result
            _excipient_cache = result
            _cache_file_path = str(excel_path)
            
            return result
            
        except FileNotFoundError:
            # If file not found, return empty dict
            print(f"Warning: Excel file not found at {excel_path}. Returning empty categories.")
            return {}
        except Exception as e:
            print(f"Error loading excipient categories from Excel: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    return _excipient_cache


def get_excipient_categories() -> Dict[str, List[str]]:
    """
    Get excipient categories (cached version).
    This is the main function to use in views.
    """
    return load_excipient_categories()



