import sys
import os
import pytest
import re

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Extract the clean_url function from xiaohongshu_mcp.py for testing
def clean_url(url):
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

class TestUrlUtils:
    """Test class for URL utility functions"""
    
    def test_clean_url_with_query_params(self):
        """Test cleaning a URL with query parameters"""
        url = "https://www.xiaohongshu.com/page?param1=value1&param2=value2"
        expected = "https://www.xiaohongshu.com/page"
        assert clean_url(url) == expected
    
    def test_clean_url_without_query_params(self):
        """Test cleaning a URL without query parameters"""
        url = "https://www.xiaohongshu.com/page"
        expected = "https://www.xiaohongshu.com/page"
        assert clean_url(url) == expected
    
    def test_clean_url_search_result(self):
        """Test cleaning a search result URL"""
        url = "https://www.xiaohongshu.com/search_result/abc123?source=web"
        expected = "https://www.xiaohongshu.com/search_result/abc123_abc123"
        assert clean_url(url) == expected
    
    def test_clean_url_explore(self):
        """Test cleaning an explore URL"""
        url = "https://www.xiaohongshu.com/explore/def456?source=web"
        expected = "https://www.xiaohongshu.com/explore/def456_def456"
        assert clean_url(url) == expected
    
    def test_clean_url_discovery(self):
        """Test cleaning a discovery URL"""
        url = "https://www.xiaohongshu.com/discovery/ghi789?source=web"
        expected = "https://www.xiaohongshu.com/discovery/ghi789_ghi789"
        assert clean_url(url) == expected
    
    def test_clean_url_with_complex_id(self):
        """Test cleaning a URL with a complex ID containing letters and numbers"""
        url = "https://www.xiaohongshu.com/explore/a1b2c3d4e5f6?source=web"
        expected = "https://www.xiaohongshu.com/explore/a1b2c3d4e5f6_a1b2c3d4e5f6"
        assert clean_url(url) == expected