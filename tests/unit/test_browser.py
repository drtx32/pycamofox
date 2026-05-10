import pytest
from unittest.mock import MagicMock, patch
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

def test_tab_navigate():
    mock_page = MagicMock()
    tab = Tab(id="tab-1", page=mock_page)
    tab.goto("https://github.com")
    mock_page.goto.assert_called_once_with("https://github.com", timeout=30000)

def test_tab_click():
    mock_page = MagicMock()
    tab = Tab(id="tab-1", page=mock_page)
    tab.click("#submit-btn")
    mock_page.click.assert_called_once_with("#submit-btn")

def test_tab_inner_text():
    mock_page = MagicMock()
    mock_page.inner_text.return_value = "Hello World"
    tab = Tab(id="tab-1", page=mock_page)
    result = tab.inner_text("body")
    assert result == "Hello World"
    mock_page.inner_text.assert_called_once_with("body")

def test_tab_screenshot():
    mock_page = MagicMock()
    mock_page.screenshot.return_value = b"fake-image-data"
    tab = Tab(id="tab-1", page=mock_page)
    result = tab.screenshot()
    assert result == b"fake-image-data"

def test_browser_close_tab():
    mock_page = MagicMock()
    mock_page.url = "https://example.com"
    tab = Tab(id="tab-1", page=mock_page)

    browser = CamoufoxBrowser(headless=True)
    browser._browser = MagicMock()
    browser._tabs = {"tab-1": tab}

    browser.close_tab("tab-1")
    mock_page.close.assert_called_once()
    assert "tab-1" not in browser._tabs
