import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pycamofox.daemon.browser import CamoufoxBrowser, Tab

@pytest.mark.asyncio
async def test_tab_properties():
    """Tab wraps page with id"""
    mock_page = MagicMock()
    mock_page.url = "https://github.com"
    mock_page.title = AsyncMock(return_value="GitHub")
    tab = Tab(id="tab-1", page=mock_page)
    assert tab.id == "tab-1"
    assert tab.url == "https://github.com"
    assert await tab.title() == "GitHub"

@pytest.mark.asyncio
async def test_tab_navigate():
    mock_page = AsyncMock()
    mock_page.url = "https://github.com"
    mock_page.title = AsyncMock(return_value="GitHub")
    mock_page.goto = AsyncMock()
    tab = Tab(id="tab-1", page=mock_page)
    result = await tab.goto("https://github.com")
    mock_page.goto.assert_called_once_with("https://github.com", timeout=30000)
    assert result["url"] == "https://github.com"
    assert result["title"] == "GitHub"

@pytest.mark.asyncio
async def test_tab_click():
    mock_page = AsyncMock()
    mock_page.click = AsyncMock()
    tab = Tab(id="tab-1", page=mock_page)
    result = await tab.click("#submit-btn")
    mock_page.click.assert_called_once_with("#submit-btn")
    assert result["status"] == "clicked"

@pytest.mark.asyncio
async def test_tab_inner_text():
    mock_page = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value="Hello World")
    tab = Tab(id="tab-1", page=mock_page)
    result = await tab.inner_text("body")
    assert result == "Hello World"
    mock_page.inner_text.assert_called_once_with("body")

@pytest.mark.asyncio
async def test_tab_screenshot():
    mock_page = AsyncMock()
    mock_page.screenshot = AsyncMock(return_value=b"fake-image-data")
    tab = Tab(id="tab-1", page=mock_page)
    result = await tab.screenshot()
    assert result == b"fake-image-data"

def test_browser_close_tab():
    """Test that close_tab properly closes the tab and removes it from browser"""
    mock_page = AsyncMock()
    mock_page.close = AsyncMock()
    mock_page.url = "https://example.com"

    tab = Tab(id="tab-1", page=mock_page)

    browser = CamoufoxBrowser(headless=True)
    browser._browser = MagicMock()
    browser._loop = MagicMock()
    browser._tabs = {"tab-1": tab}

    # Mock _run_async to run the coroutine synchronously
    def fake_run_async(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    browser._run_async = fake_run_async

    browser.close_tab("tab-1")

    # Verify close was called
    mock_page.close.assert_called_once()
    assert "tab-1" not in browser._tabs


def test_browser_init():
    """Test that browser initializes with correct defaults"""
    browser = CamoufoxBrowser(headless=True)
    assert browser.headless is True
    assert browser._browser is None
    assert browser._tabs == {}
    assert browser._tab_counter == 0
    assert browser.is_running is False


def test_get_tab_returns_none_when_empty():
    """Test that get_tab returns None for nonexistent tab"""
    browser = CamoufoxBrowser(headless=True)
    assert browser.get_tab("nonexistent") is None
