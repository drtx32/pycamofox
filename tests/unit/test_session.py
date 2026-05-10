import pytest
import asyncio
from unittest.mock import MagicMock
from pycamofox.daemon.session import Session, SessionManager

@pytest.mark.asyncio
async def test_create_session(tmp_path):
    mock_browser = MagicMock()
    mock_tab = MagicMock()
    mock_tab.id = "tab-1"
    mock_browser.new_tab.return_value = mock_tab

    from pycamofox.persistence.session_state import SessionStateStore
    store = SessionStateStore(tmp_path)

    manager = SessionManager(mock_browser, store)
    session = manager.create_session("s1")

    assert session.id == "s1"
    assert session.tab.id == "tab-1"
    assert "s1" in manager._locks

@pytest.mark.asyncio
async def test_execute_serialization(tmp_path):
    """Two concurrent execute calls on same session should be serialized"""
    mock_browser = MagicMock()
    mock_tab = MagicMock()
    mock_tab.id = "tab-1"
    mock_tab.url = "https://github.com"
    mock_tab.title = "GitHub"
    mock_tab.goto.return_value = {"url": "https://github.com"}
    mock_tab.cookies.return_value = []
    mock_tab.get_local_storage.return_value = {}
    mock_tab.get_scroll_position.return_value = (0, 0)
    mock_browser.new_tab.return_value = mock_tab

    from pycamofox.persistence.session_state import SessionStateStore
    store = SessionStateStore(tmp_path)

    manager = SessionManager(mock_browser, store)
    session = manager.create_session("s1")

    # Execute two commands concurrently
    async def cmd1():
        return await manager.execute("s1", "navigate", url="https://github.com")
    async def cmd2():
        return await manager.execute("s1", "navigate", url="https://github.com")

    results = await asyncio.gather(cmd1(), cmd2())
    assert all(r["url"] == "https://github.com" for r in results)

@pytest.mark.asyncio
async def test_different_sessions_parallel(tmp_path):
    """Different sessions should execute in parallel"""
    mock_browser = MagicMock()
    mock_tab1 = MagicMock()
    mock_tab1.id = "tab-1"
    mock_tab1.url = "https://a.com"
    mock_tab1.title = "Site A"
    mock_tab1.goto.return_value = {"url": "https://a.com"}
    mock_tab1.cookies.return_value = []
    mock_tab1.get_local_storage.return_value = {}
    mock_tab1.get_scroll_position.return_value = (0, 0)
    mock_tab2 = MagicMock()
    mock_tab2.id = "tab-2"
    mock_tab2.url = "https://b.com"
    mock_tab2.title = "Site B"
    mock_tab2.goto.return_value = {"url": "https://b.com"}
    mock_tab2.cookies.return_value = []
    mock_tab2.get_local_storage.return_value = {}
    mock_tab2.get_scroll_position.return_value = (0, 0)
    mock_browser.new_tab.side_effect = [mock_tab1, mock_tab2]

    from pycamofox.persistence.session_state import SessionStateStore
    store = SessionStateStore(tmp_path)

    manager = SessionManager(mock_browser, store)
    manager.create_session("s1")
    manager.create_session("s2")

    # Both sessions can run simultaneously (no deadlock)
    results = await asyncio.gather(
        manager.execute("s1", "navigate", url="https://a.com"),
        manager.execute("s2", "navigate", url="https://b.com"),
    )
    assert len(results) == 2

@pytest.mark.asyncio
async def test_close_session(tmp_path):
    mock_browser = MagicMock()
    mock_tab = MagicMock()
    mock_tab.id = "tab-1"
    mock_tab.url = "https://example.com"
    mock_tab.title = "Example"
    mock_tab.cookies.return_value = []
    mock_tab.get_local_storage.return_value = {}
    mock_tab.get_scroll_position.return_value = (0, 0)
    mock_browser.new_tab.return_value = mock_tab

    from pycamofox.persistence.session_state import SessionStateStore
    store = SessionStateStore(tmp_path)

    manager = SessionManager(mock_browser, store)
    manager.create_session("s1")
    result = manager.close_session("s1")

    assert result["status"] == "closed"
    assert "s1" not in manager._sessions
    assert "s1" not in manager._locks
    mock_tab.close.assert_called_once()

@pytest.mark.asyncio
async def test_execute_unknown_command(tmp_path):
    mock_browser = MagicMock()
    mock_tab = MagicMock()
    mock_tab.id = "tab-1"
    mock_browser.new_tab.return_value = mock_tab

    from pycamofox.persistence.session_state import SessionStateStore
    store = SessionStateStore(tmp_path)

    manager = SessionManager(mock_browser, store)
    manager.create_session("s1")

    with pytest.raises(ValueError, match="Unknown command"):
        await manager.execute("s1", "nonexistent_command")