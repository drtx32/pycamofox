# tests/integration/test_daemon_flow.py
"""End-to-end integration tests using real Camoufox browser.

These tests require a real Camoufox browser to be installed and accessible.
They are skipped by default; run with --run-integration to execute them.
"""
import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
from pycamofox.daemon.browser import CamoufoxBrowser
from pycamofox.daemon.session import SessionManager
from pycamofox.persistence.storage import CamofoxStorage
from pycamofox.persistence.session_state import SessionStateStore


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", default=False,
                     help="run integration tests that require real browser")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture
def storage(tmp_path):
    return CamofoxStorage(base_dir=tmp_path)


@pytest_asyncio.fixture
async def browser():
    b = CamoufoxBrowser(headless=True)
    await b.launch_async()
    yield b
    await b.aclose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_execute_close_flow(browser, storage):
    """Full session lifecycle"""
    state_store = SessionStateStore(storage.base_dir)
    manager = SessionManager(browser=browser, state_store=state_store)

    session = manager.create_session("flow-test")
    assert session.id == "flow-test"
    assert session.tab.url == "about:blank"

    result = await manager.execute("flow-test", "get_url")
    assert result["url"] == "about:blank"

    manager.close_session("flow-test")
    assert "flow-test" not in manager._sessions


@pytest.mark.asyncio
@pytest.mark.integration
async def test_session_state_persistence(browser, storage):
    """Session state persists after close and restore"""
    state_store = SessionStateStore(storage.base_dir)
    manager = SessionManager(browser=browser, state_store=state_store)

    session = manager.create_session("persist-test")
    await manager.execute("persist-test", "navigate", url="https://example.com")

    manager.close_session("persist-test")

    state = state_store.load("persist-test")
    assert state is not None
    assert "example.com" in state.url

    session2 = manager.create_session("persist-test")
    assert session2.tab.url == "https://example.com"
    manager.close_session("persist-test")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_sessions(browser, storage):
    """Multiple sessions can operate concurrently"""
    state_store = SessionStateStore(storage.base_dir)
    manager = SessionManager(browser=browser, state_store=state_store)

    manager.create_session("concurrent-1")
    manager.create_session("concurrent-2")

    results = await asyncio.gather(
        manager.execute("concurrent-1", "get_url"),
        manager.execute("concurrent-2", "get_url"),
    )
    assert len(results) == 2

    manager.close_session("concurrent-1")
    manager.close_session("concurrent-2")
