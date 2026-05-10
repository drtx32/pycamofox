# tests/conftest.py
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil


@pytest.fixture(scope="session")
def temp_camofox_dir():
    """Temporary .camofox directory for tests"""
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def session_dir(temp_camofox_dir):
    """Per-test session directory"""
    sid = "test-session-1"
    d = temp_camofox_dir / "sessions" / sid
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()