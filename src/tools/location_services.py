"""Location services for the Claims Handler Agent"""

import re
from typing import Dict, Optional, Tuple
import pgeocode
import pandas as pd


# Global geocoder instance for performance
_geocoder = None


def get_geocoder():
    """Get or create the geocoder instance (singleton pattern)"""
    global _geocoder
    if _geocoder is None:
        _geocoder = pgeocode.Nominatim('us')
    return _geocoder


def get_location_details(location_string: str) -> Dict[str, any]:
    """
    Enhanced location processing with validation and formatting.
    
    Args:
        location_string: Location input from user (various formats)
        
    Returns:
        Dictionary with processed location information
    """
    result = {
        "original_input": location_string,
        "formatted_location": None,
        "city": None,
        "state": None,
        "coordinates": None,
        "is_valid": False,
        "suggestions": []
    }
    
    # Clean the input
    cleaned_location = location_string.strip()
    
    # Try to parse existing "City, State" format
    city_state = parse_city_state(cleaned_location)
    if city_state:
        city, state = city_state
        result["city"] = city
        result["state"] = state
        result["formatted_location"] = f"{city}, {state}"
        result["is_valid"] = True
        
        # Try to get coordinates
        coords = get_coordinates_from_city_state(city, state)
        if coords:
            result["coordinates"] = coords
    
    # If not city/state format, try zip code
    elif is_zip_code(cleaned_location):
        zip_details = get_city_state_from_zip(cleaned_location)
        if zip_details:
            city, state = zip_details
            result["city"] = city
            result["state"] = state
            result["formatted_location"] = f"{city}, {state}"
            result["is_valid"] = True
            
            coords = get_coordinates_from_zip(cleaned_location)
            if coords:
                result["coordinates"] = coords
    
    # If still not valid, provide suggestions
    if not result["is_valid"]:
        result["suggestions"] = generate_location_suggestions(cleaned_location)
    
    return result


def parse_city_state(location_string: str) -> Optional[Tuple[str, str]]:
    """
    Parse location string in "City, State" format.
    
    Args:
        location_string: Input location string
        
    Returns:
        Tuple of (city, state) if valid format, None otherwise
    """
    # Pattern for City, State format
    city_state_pattern = r'^([A-Za-z\s]+),\s*([A-Za-z]{2})$'
    match = re.match(city_state_pattern, location_string.strip())
    
    if match:
        city = match.group(1).strip().title()
        state = match.group(2).strip().upper()
        return city, state
    
    return None


def is_zip_code(text: str) -> bool:
    """Check if text is a valid US zip code format"""
    zip_pattern = r'^\d{5}(-\d{4})?$'
    return bool(re.match(zip_pattern, text.strip()))


def get_city_state_from_zip(zip_code: str) -> Optional[Tuple[str, str]]:
    """
    Get city and state from zip code using pgeocode.
    
    Args:
        zip_code: US zip code
        
    Returns:
        Tuple of (city, state) if found, None otherwise
    """
    try:
        geocoder = get_geocoder()
        location = geocoder.query_postal_code(zip_code.strip())
        
        if pd.notnull(location.place_name) and pd.notnull(location.state_code):
            city = location.place_name
            state = location.state_code
            return city, state
    except Exception:
        pass
    
    return None


def get_coordinates_from_city_state(city: str, state: str) -> Optional[Dict[str, float]]:
    """
    Get coordinates from city and state.
    Note: This is a simplified implementation. In production, you might want
    to use a more comprehensive geocoding service.
    
    Args:
        city: City name
        state: State code
        
    Returns:
        Dictionary with lat/lon if found, None otherwise
    """
    # This is a placeholder implementation
    # In production, you'd use a proper geocoding service
    return None


def get_coordinates_from_zip(zip_code: str) -> Optional[Dict[str, float]]:
    """
    Get coordinates from zip code using pgeocode.
    
    Args:
        zip_code: US zip code
        
    Returns:
        Dictionary with lat/lon if found, None otherwise
    """
    try:
        geocoder = get_geocoder()
        location = geocoder.query_postal_code(zip_code.strip())
        
        if pd.notnull(location.latitude) and pd.notnull(location.longitude):
            return {
                "lat": float(location.latitude),
                "lon": float(location.longitude)
            }
    except Exception:
        pass
    
    return None


def generate_location_suggestions(location_input: str) -> list:
    """
    Generate helpful suggestions for invalid location inputs.
    
    Args:
        location_input: Original user input
        
    Returns:
        List of suggestion strings
    """
    suggestions = []
    
    # Common format suggestions
    suggestions.append("Try the format 'City, State' like 'Seattle, WA'")
    suggestions.append("You can also provide just a zip code like '98101'")
    
    # Check if it might be missing comma
    if " " in location_input and "," not in location_input:
        parts = location_input.split()
        if len(parts) >= 2:
            # Assume last part might be state
            potential_state = parts[-1].upper()
            if len(potential_state) == 2:
                potential_city = " ".join(parts[:-1])
                suggestions.append(f"Did you mean '{potential_city}, {potential_state}'?")
    
    return suggestions


def format_location_for_display(location_result: Dict[str, any]) -> str:
    """
    Format location result for display to user.
    
    Args:
        location_result: Result from get_location_details
        
    Returns:
        Human-readable location string
    """
    if location_result["is_valid"]:
        return location_result["formatted_location"]
    else:
        return f"Please clarify the location. {location_result['suggestions'][0] if location_result['suggestions'] else ''}"
