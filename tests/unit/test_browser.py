import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pycamofox.daemon.browser import CamoufoxBrowser, Tab

def test_tab_properties():
    """Tab wraps page with id"""
    mock_page = MagicMock()
    mock_page.url = "https://github.com"
    mock_page.title = "GitHub"
    tab = Tab(id="tab-1", page=mock_page)
    assert tab.id == "tab-1"
    assert tab.url == "https://github.com"
    assert tab.title == "GitHub"

@pytest.mark.asyncio
async def test_tab_navigate():
    mock_page = AsyncMock()
    mock_page.url = "https://github.com"
    mock_page.title = "GitHub"
    mock_page.goto = AsyncMock()
    tab = Tab(id="tab-1", page=mock_page)
    result = await tab.goto("https://github.com")
    mock_page.goto.assert_called_once_with("https://github.com", timeout=30000)
    assert result["url"] == "https://github.com"

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
    browser._tabs = {"tab-1": tab}

    # Need to run the sync wrapper for async close
    browser.close_tab("tab-1")

    # Verify close was called (via asyncio.run)
    mock_page.close.assert_called_once()
    assert "tab-1" not in browser._tabs

@pytest.mark.asyncio
async def test_browser_launch_async():
    """Test that launch_async properly launches browser"""
    browser = CamoufoxBrowser(headless=True)

    # Mock the async_playwright and Camoufox
    mock_playwright = AsyncMock()
    mock_playwright.start = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)

    mock_browser = AsyncMock()
    mock_page = MagicMock()
    mock_page.url = "about:blank"
    mock_page.title = ""
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_camoufox = AsyncMock()
    mock_camoufox.__aenter__ = AsyncMock(return_value=mock_browser)
    mock_camoufox.__aexit__ = AsyncMock(return_value=None)

    with patch("camoufox.async_api.AsyncCamoufox", return_value=mock_camoufox):
        with patch("playwright.async_api.async_playwright", return_value=mock_playwright):
            result = await browser.launch_async()

    assert result["status"] == "launched"
    assert "tab_id" in result
    assert browser.is_running is True

    # Cleanup
    await browser.aclose()
