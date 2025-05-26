import sys
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the function to test
from xiaohongshu_mcp import search_notes

class TestSearch:
    """Test class for search functions"""
    
    @patch('xiaohongshu_mcp.ensure_browser')
    @patch('xiaohongshu_mcp.main_page')
    @patch('xiaohongshu_mcp.asyncio.sleep')
    async def test_search_notes_success(self, mock_sleep, mock_main_page, mock_ensure_browser):
        """Test search_notes with successful search"""
        # Setup mocks
        mock_ensure_browser.return_value = True
        
        # Mock post cards
        mock_card1 = AsyncMock()
        mock_card2 = AsyncMock()
        
        # Mock link elements
        mock_link1 = AsyncMock()
        mock_link1.get_attribute.return_value = "/search_result/abc123"
        mock_card1.query_selector.return_value = mock_link1
        
        mock_link2 = AsyncMock()
        mock_link2.get_attribute.return_value = "/search_result/def456"
        mock_card2.query_selector.return_value = mock_link2
        
        # Mock title elements
        mock_title1 = AsyncMock()
        mock_title1.text_content.return_value = "Test Title 1"
        mock_card1.query_selector_all.return_value = [mock_title1]
        
        mock_title2 = AsyncMock()
        mock_title2.text_content.return_value = "Test Title 2"
        mock_card2.query_selector_all.return_value = [mock_title2]
        
        # Set up main_page mock
        mock_main_page.goto = AsyncMock()
        mock_main_page.query_selector_all.return_value = [mock_card1, mock_card2]
        
        # Test
        result = await search_notes("test keywords", limit=2)
        
        # Assert
        assert "搜索结果" in result
        assert "Test Title 1" in result
        assert "Test Title 2" in result
        assert "https://www.xiaohongshu.com/explore/abc123" in result
        assert "https://www.xiaohongshu.com/explore/def456" in result
    
    @patch('xiaohongshu_mcp.ensure_browser')
    async def test_search_notes_not_logged_in(self, mock_ensure_browser):
        """Test search_notes when not logged in"""
        # Setup mock
        mock_ensure_browser.return_value = False
        
        # Test
        result = await search_notes("test keywords")
        
        # Assert
        assert result == "请先登录小红书账号"
    
    @patch('xiaohongshu_mcp.ensure_browser')
    @patch('xiaohongshu_mcp.main_page')
    @patch('xiaohongshu_mcp.asyncio.sleep')
    async def test_search_notes_no_results(self, mock_sleep, mock_main_page, mock_ensure_browser):
        """Test search_notes with no search results"""
        # Setup mocks
        mock_ensure_browser.return_value = True
        
        # Set up main_page mock
        mock_main_page.goto = AsyncMock()
        mock_main_page.query_selector_all.return_value = []
        
        # Test
        result = await search_notes("test keywords")
        
        # Assert
        assert "未找到" in result
    
    @patch('xiaohongshu_mcp.ensure_browser')
    @patch('xiaohongshu_mcp.main_page')
    async def test_search_notes_exception(self, mock_main_page, mock_ensure_browser):
        """Test search_notes when an exception occurs"""
        # Setup mocks
        mock_ensure_browser.return_value = True
        
        # Set up main_page mock to raise an exception
        mock_main_page.goto = AsyncMock(side_effect=Exception("Test exception"))
        
        # Test
        result = await search_notes("test keywords")
        
        # Assert
        assert "出错" in result