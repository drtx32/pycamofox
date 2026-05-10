"""Integration tests for the FastAPI server.

Requires --run-integration to execute (real browser needed).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from pycamofox.daemon.server import create_app
from pycamofox.daemon.browser import CamoufoxBrowser
from pycamofox.persistence.storage import CamofoxStorage


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


@pytest.fixture
def browser():
    b = CamoufoxBrowser(headless=True)
    yield b
    b.close()


@pytest.fixture
def app(browser, storage):
    return create_app(browser=browser, storage=storage)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_check(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "browser_running" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_session(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "tab_id" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_execute_command(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/sessions")
        session_id = resp.json()["session_id"]
        resp = await client.post(f"/sessions/{session_id}/execute", json={
            "command": "get_url"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_session_not_found(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/sessions/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.integration
async def test_close_session(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/sessions")
        session_id = resp.json()["session_id"]
        resp = await client.delete(f"/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"
        resp = await client.get(f"/sessions/{session_id}")
        assert resp.status_code == 404
