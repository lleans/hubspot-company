from datetime import datetime, timedelta
from typing import Optional, Union
import re

def format_duration(seconds: Optional[int]) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds is None:
        return "N/A"
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"

def parse_hubspot_timestamp(timestamp: Union[str, int, None]) -> Optional[datetime]:
    """
    Parse HubSpot timestamp to datetime object
    HubSpot uses milliseconds since epoch
    
    Args:
        timestamp: HubSpot timestamp (string or int)
        
    Returns:
        Datetime object or None if parsing fails
    """
    if not timestamp:
        return None
    
    try:
        if isinstance(timestamp, str):
            if timestamp.isdigit():
                timestamp = int(timestamp)
            else:
                # Try parsing as ISO format
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        if isinstance(timestamp, int):
            # HubSpot timestamps are in milliseconds
            return datetime.fromtimestamp(timestamp / 1000)
            
    except (ValueError, TypeError, OverflowError):
        return None
    
    return None

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system usage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized or 'unnamed_file'

def chunk_list(lst: list, chunk_size: int) -> list:
    """
    Split list into chunks of specified size
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def safe_get_nested(data: dict, keys: list, default=None):
    """
    Safely get nested dictionary values
    
    Args:
        data: Dictionary to search
        keys: List of keys for nested access
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError):
        return default

def normalize_phone_number(phone: str) -> Optional[str]:
    """
    Normalize phone number format
    
    Args:
        phone: Phone number string
        
    Returns:
        Normalized phone number or None
    """
    if not phone:
        return None
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle different formats
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    return phone  # Return original if can't normalize

def validate_email(email: str) -> bool:
    """
    Basic email validation
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email appears valid
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                
    return bool(re.match(pattern, email))

def calculate_percentage(part: int, total: int) -> float:
    """
    Calculate percentage with division by zero protection
    
    Args:
        part: Part value
        total: Total value
        
    Returns:
        Percentage as float
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)