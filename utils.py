"""
Utility functions for the Xiaohongshu MCP project.
"""
import re
from typing import Optional

def clean_url(url: str) -> str:
    """
    Clean a URL by removing query parameters and extracting the ID for specific Xiaohongshu URLs.
    
    Args:
        url (str): The URL to clean
        
    Returns:
        str: The cleaned URL
    """
    # First extract the base URL (without query parameters)
    base_url = url.split('?')[0]
    # If it's a Xiaohongshu search result or note page, keep the key ID
    if '/search_result/' in url or '/explore/' in url or '/discovery/' in url:
        # Extract ID
        id_match = re.search(r'/(search_result|explore|discovery)/([a-zA-Z0-9]+)', url)
        if id_match:
            return f"{base_url}_{id_match.group(2)}"
    return base_url

def is_same_url(url1: str, url2: str) -> bool:
    """
    Check if two URLs are the same after cleaning.
    
    Args:
        url1 (str): The first URL
        url2 (str): The second URL
        
    Returns:
        bool: True if the URLs are the same after cleaning, False otherwise
    """
    return clean_url(url1) == clean_url(url2)

def extract_note_id(url: str) -> Optional[str]:
    """
    Extract the note ID from a Xiaohongshu URL.
    
    Args:
        url (str): The URL to extract the note ID from
        
    Returns:
        Optional[str]: The note ID if found, None otherwise
    """
    if '/search_result/' in url or '/explore/' in url or '/discovery/' in url:
        id_match = re.search(r'/(search_result|explore|discovery)/([a-zA-Z0-9]+)', url)
        if id_match:
            return id_match.group(2)
    return None

def convert_url_format(url: str, target_format: str = 'explore') -> str:
    """
    Convert a Xiaohongshu URL from one format to another.
    
    Args:
        url (str): The URL to convert
        target_format (str): The target format, one of 'explore', 'search_result', or 'discovery'
        
    Returns:
        str: The converted URL
    """
    if '/search_result/' in url or '/explore/' in url or '/discovery/' in url:
        note_id = extract_note_id(url)
        if note_id:
            base_url = "https://www.xiaohongshu.com"
            return f"{base_url}/{target_format}/{note_id}"
    return url