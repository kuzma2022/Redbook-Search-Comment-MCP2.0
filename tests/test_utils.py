import sys
import os
import pytest

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the functions to test
from utils import clean_url, is_same_url, extract_note_id, convert_url_format

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
    
    def test_is_same_url_with_same_urls(self):
        """Test is_same_url with identical URLs"""
        url1 = "https://www.xiaohongshu.com/explore/abc123"
        url2 = "https://www.xiaohongshu.com/explore/abc123"
        assert is_same_url(url1, url2) is True
    
    def test_is_same_url_with_different_urls(self):
        """Test is_same_url with different URLs"""
        url1 = "https://www.xiaohongshu.com/explore/abc123"
        url2 = "https://www.xiaohongshu.com/explore/def456"
        assert is_same_url(url1, url2) is False
    
    def test_is_same_url_with_query_params(self):
        """Test is_same_url with URLs that differ only in query parameters"""
        url1 = "https://www.xiaohongshu.com/explore/abc123?param1=value1"
        url2 = "https://www.xiaohongshu.com/explore/abc123?param2=value2"
        assert is_same_url(url1, url2) is True
    
    def test_extract_note_id_search_result(self):
        """Test extracting note ID from a search result URL"""
        url = "https://www.xiaohongshu.com/search_result/abc123?source=web"
        assert extract_note_id(url) == "abc123"
    
    def test_extract_note_id_explore(self):
        """Test extracting note ID from an explore URL"""
        url = "https://www.xiaohongshu.com/explore/def456?source=web"
        assert extract_note_id(url) == "def456"
    
    def test_extract_note_id_discovery(self):
        """Test extracting note ID from a discovery URL"""
        url = "https://www.xiaohongshu.com/discovery/ghi789?source=web"
        assert extract_note_id(url) == "ghi789"
    
    def test_extract_note_id_invalid(self):
        """Test extracting note ID from an invalid URL"""
        url = "https://www.xiaohongshu.com/page?param=value"
        assert extract_note_id(url) is None
    
    def test_convert_url_format_search_to_explore(self):
        """Test converting a search result URL to an explore URL"""
        url = "https://www.xiaohongshu.com/search_result/abc123?source=web"
        expected = "https://www.xiaohongshu.com/explore/abc123"
        assert convert_url_format(url, "explore") == expected
    
    def test_convert_url_format_explore_to_search(self):
        """Test converting an explore URL to a search result URL"""
        url = "https://www.xiaohongshu.com/explore/def456?source=web"
        expected = "https://www.xiaohongshu.com/search_result/def456"
        assert convert_url_format(url, "search_result") == expected
    
    def test_convert_url_format_invalid(self):
        """Test converting an invalid URL"""
        url = "https://www.xiaohongshu.com/page?param=value"
        assert convert_url_format(url) == url