import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the function to test
from xiaohongshu_mcp import is_same_page

class TestPageUtils:
    """Test class for page utility functions"""
    
    @patch('xiaohongshu_mcp.main_page')
    async def test_is_same_page_with_same_urls(self, mock_main_page):
        """Test is_same_page with identical URLs"""
        # Setup mock
        mock_main_page.url = "https://www.xiaohongshu.com/explore/abc123"
        
        # Test
        result = await is_same_page("https://www.xiaohongshu.com/explore/abc123")
        
        # Assert
        assert result is True
    
    @patch('xiaohongshu_mcp.main_page')
    async def test_is_same_page_with_different_urls(self, mock_main_page):
        """Test is_same_page with different URLs"""
        # Setup mock
        mock_main_page.url = "https://www.xiaohongshu.com/explore/abc123"
        
        # Test
        result = await is_same_page("https://www.xiaohongshu.com/explore/def456")
        
        # Assert
        assert result is False
    
    @patch('xiaohongshu_mcp.main_page')
    async def test_is_same_page_with_query_params(self, mock_main_page):
        """Test is_same_page with URLs that differ only in query parameters"""
        # Setup mock
        mock_main_page.url = "https://www.xiaohongshu.com/explore/abc123?param1=value1"
        
        # Test
        result = await is_same_page("https://www.xiaohongshu.com/explore/abc123?param2=value2")
        
        # Assert
        assert result is True
    
    @patch('xiaohongshu_mcp.main_page')
    async def test_is_same_page_with_no_main_page(self, mock_main_page):
        """Test is_same_page when main_page is None"""
        # Setup mock
        mock_main_page = None
        
        # Test
        result = await is_same_page("https://www.xiaohongshu.com/explore/abc123")
        
        # Assert
        assert result is False
    
    @patch('xiaohongshu_mcp.main_page')
    async def test_is_same_page_with_exception(self, mock_main_page):
        """Test is_same_page when an exception occurs"""
        # Setup mock to raise an exception
        mock_main_page.url = MagicMock(side_effect=Exception("Test exception"))
        
        # Test
        result = await is_same_page("https://www.xiaohongshu.com/explore/abc123")
        
        # Assert
        assert result is False