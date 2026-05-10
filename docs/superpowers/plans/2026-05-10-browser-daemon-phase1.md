# Browser Daemon Phase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stable Browser Runtime Daemon with single Camoufox Browser + multiple Sessions, per-session locking, full state persistence, REST API + WebSocket.

**Architecture:** FastAPI server manages a single Camoufox Browser instance. Each Session binds to one Tab. Per-Session asyncio.Lock serializes operations within a Session while allowing cross-session parallelism. Session state (cookies, localStorage, scroll) persists to disk on each operation and on close. REST API handles commands; WebSocket pushes navigation/network events.

**Tech Stack:** camoufox, fastapi, uvicorn, pydantic, websockets, pytest, pytest-asyncio

---

## File Structure

```
src/pycamofox/
├── __init__.py              # modify: export daemon + persistence
├── __main__.py              # modify: add `daemon` subcommand
├── cli.py                   # keep: minimal changes to point to new API
├── daemon/                  # create: Browser Daemon Core
│   ├── __init__.py
│   ├── models.py            # create: Pydantic request/response models
│   ├── browser.py           # create: Camoufox lifecycle management
│   ├── session.py           # create: Session class + SessionManager
│   ├── state.py             # create: SessionState dataclass
│   └── server.py            # create: FastAPI app + REST + WebSocket
└── persistence/             # create: State storage utilities
    ├── __init__.py
    ├── storage.py           # create: Base storage path utilities
    ├── cookies.py           # create: Per-domain cookie persistence
    └── session_state.py     # create: Session state save/restore

tests/
├── __init__.py
├── conftest.py              # create: pytest fixtures
├── unit/
│   ├── __init__.py
│   ├── test_models.py       # create: Pydantic model validation tests
│   ├── test_state.py        # create: SessionState tests
│   └── test_cookies.py      # create: cookie persistence tests
└── integration/
    ├── __init__.py
    └── test_daemon_flow.py  # create: full flow tests (uses real or mocked browser)
```

---

## Task 1: Project Setup

**Files:**
- Modify: `pyproject.toml` — add dependencies
- Create: `tests/__init__.py`, `tests/conftest.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Read existing `pyproject.toml` first, then add:

```toml
[project]
dependencies = [
    "camoufox>=3.0.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0.0",
    "websockets>=12.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",  # for test client
]

[project.scripts]
pycamofox = "pycamofox.cli:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create test package init files**

```python
# tests/__init__.py
# tests/unit/__init__.py
# tests/integration/__init__.py
# Empty, just mark as packages
```

- [ ] **Step 3: Write conftest.py with fixtures**

```python
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
```

- [ ] **Step 4: Install dependencies**

Run: `pip install -e ".[dev]"` (or whatever the equivalent is in this environment)
Expected: Dependencies installed without error

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/
git commit -m "chore: add Phase 1 dependencies and test setup"
```

---

## Task 2: Persistence Layer

**Files:**
- Create: `src/pycamofox/persistence/__init__.py`
- Create: `src/pycamofox/persistence/storage.py`
- Create: `src/pycamofox/persistence/cookies.py`
- Create: `src/pycamofox/persistence/session_state.py`
- Create: `tests/unit/test_cookies.py`
- Create: `tests/unit/test_state.py`

### 2a. Storage utilities

- [ ] **Step 1: Write failing test for storage path**

```python
# tests/unit/test_storage.py
from pycamofox.persistence.storage import CamofoxStorage

def test_storage_base_dir(tmp_path):
    storage = CamofoxStorage(base_dir=tmp_path)
    assert storage.base_dir == tmp_path
    assert storage.sessions_dir == tmp_path / "sessions"
    assert storage.cookies_dir == tmp_path / "cookies"

def test_storage_session_dir(tmp_path):
    storage = CamofoxStorage(base_dir=tmp_path)
    sess_dir = storage.session_dir("session-abc")
    assert sess_dir == tmp_path / "sessions" / "session-abc"
    assert sess_dir.exists()
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `pytest tests/unit/test_storage.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write storage.py**

```python
# src/pycamofox/persistence/storage.py
from pathlib import Path
from dataclasses import dataclass

@dataclass
class CamofoxStorage:
    """Storage paths for camofox runtime data"""
    base_dir: Path

    def __post_init__(self):
        self.base_dir = Path(self.base_dir).expanduser()

    @property
    def sessions_dir(self) -> Path:
        return self.base_dir / "sessions"

    @property
    def cookies_dir(self) -> Path:
        return self.base_dir / "cookies"

    def session_dir(self, session_id: str) -> Path:
        d = self.sessions_dir / session_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def cookie_file(self, domain: str) -> Path:
        return self.cookies_dir / f"{domain}.json"

    @classmethod
    def default(cls) -> "CamofoxStorage":
        """Default storage at ~/.camofox"""
        return cls(Path.home() / ".camofox")
```

- [ ] **Step 4: Run test — verify PASS**

Run: `pytest tests/unit/test_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pycamofox/persistence/storage.py tests/unit/test_storage.py
git commit -m "feat: add CamofoxStorage path utilities"
```

### 2b. Session State

- [ ] **Step 1: Write failing test for SessionState**

```python
# tests/unit/test_state.py
from pycamofox.persistence.session_state import SessionState, SessionStateStore
import json

def test_session_state_to_dict():
    state = SessionState(
        session_id="s1",
        url="https://github.com",
        title="GitHub",
        cookies=[{"name": "foo", "value": "bar"}],
        local_storage={"key": "val"},
        scroll_position=(0, 300),
    )
    d = state.to_dict()
    assert d["session_id"] == "s1"
    assert d["url"] == "https://github.com"
    assert d["scroll_position"] == [0, 300]

def test_session_state_roundtrip(tmp_path):
    store = SessionStateStore(tmp_path)
    state = SessionState(
        session_id="s1",
        url="https://github.com",
        title="GitHub",
        cookies=[],
        local_storage={},
        scroll_position=(0, 0),
    )
    store.save(state)
    loaded = store.load("s1")
    assert loaded is not None
    assert loaded.session_id == "s1"
    assert loaded.url == "https://github.com"

def test_session_state_load_missing(tmp_path):
    store = SessionStateStore(tmp_path)
    assert store.load("nonexistent") is None
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `pytest tests/unit/test_state.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write session_state.py**

```python
# src/pycamofox/persistence/session_state.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

@dataclass
class SessionState:
    """Full session state for persistence and restore"""
    session_id: str
    url: str = ""
    title: str = ""
    cookies: list[dict[str, Any]] = field(default_factory=list)
    local_storage: dict[str, str] = field(default_factory=dict)
    scroll_position: tuple[int, int] = (0, 0)
    created_at: str = ""
    last_active: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "url": self.url,
            "title": self.title,
            "cookies": self.cookies,
            "local_storage": self.local_storage,
            "scroll_position": list(self.scroll_position),
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        sp = data.get("scroll_position", [0, 0])
        return cls(
            session_id=data["session_id"],
            url=data.get("url", ""),
            title=data.get("title", ""),
            cookies=data.get("cookies", []),
            local_storage=data.get("local_storage", {}),
            scroll_position=(sp[0], sp[1]) if isinstance(sp, list) else (0, 0),
            created_at=data.get("created_at", ""),
            last_active=data.get("last_active", ""),
        )


class SessionStateStore:
    """Save/load SessionState to disk"""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def _state_file(self, session_id: str) -> Path:
        d = self.base_dir / "sessions" / session_id
        d.mkdir(parents=True, exist_ok=True)
        return d / "state.json"

    def save(self, state: SessionState) -> None:
        path = self._state_file(state.session_id)
        path.write_text(json.dumps(state.to_dict(), indent=2))

    def load(self, session_id: str) -> SessionState | None:
        path = self._state_file(session_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return SessionState.from_dict(data)

    def delete(self, session_id: str) -> None:
        path = self._state_file(session_id)
        if path.exists():
            path.unlink()
```

- [ ] **Step 4: Run test — verify PASS**

Run: `pytest tests/unit/test_state.py -v`
Expected: PASS

- [ ] **Step 5: Write failing test for cookies persistence**

```python
# tests/unit/test_cookies.py
from pycamofox.persistence.cookies import CookieStore
import json

def test_cookie_store_save(tmp_path):
    store = CookieStore(tmp_path)
    cookies = [{"name": "session", "value": "abc", "domain": ".github.com"}]
    store.save("github.com", cookies)

    content = (tmp_path / "cookies" / "github.com.json").read_text()
    assert json.loads(content) == cookies

def test_cookie_store_load(tmp_path):
    store = CookieStore(tmp_path)
    cookies = [{"name": "session", "value": "abc", "domain": ".github.com"}]
    store.save("github.com", cookies)

    loaded = store.load("github.com")
    assert loaded == cookies

def test_cookie_store_load_missing(tmp_path):
    store = CookieStore(tmp_path)
    assert store.load("nonexistent.com") == []
```

- [ ] **Step 6: Run test — verify FAIL**

Run: `pytest tests/unit/test_cookies.py -v`
Expected: FAIL — module not found

- [ ] **Step 7: Write cookies.py**

```python
# src/pycamofox/persistence/cookies.py
from pathlib import Path
from typing import Any
import json

class CookieStore:
    """Per-domain cookie persistence"""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.cookies_dir = self.base_dir / "cookies"
        self.cookies_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, domain: str) -> Path:
        # Normalize domain for filename
        safe = domain.lstrip(".")
        return self.cookies_dir / f"{safe}.json"

    def save(self, domain: str, cookies: list[dict[str, Any]]) -> None:
        self._path(domain).write_text(json.dumps(cookies, indent=2))

    def load(self, domain: str) -> list[dict[str, Any]]:
        path = self._path(domain)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def delete(self, domain: str) -> None:
        path = self._path(domain)
        if path.exists():
            path.unlink()
```

- [ ] **Step 8: Run test — verify PASS**

Run: `pytest tests/unit/test_cookies.py -v`
Expected: PASS

- [ ] **Step 9: Write persistence __init__.py**

```python
# src/pycamofox/persistence/__init__.py
from .storage import CamofoxStorage
from .session_state import SessionState, SessionStateStore
from .cookies import CookieStore

__all__ = ["CamofoxStorage", "SessionState", "SessionStateStore", "CookieStore"]
```

- [ ] **Step 10: Commit**

```bash
git add src/pycamofox/persistence/ tests/unit/test_cookies.py tests/unit/test_state.py tests/unit/test_storage.py
git commit -m "feat: add persistence layer (cookies, session state)"
```

---

## Task 3: Daemon Models

**Files:**
- Create: `src/pycamofox/daemon/models.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Write failing test for daemon models**

```python
# tests/unit/test_models.py
from pycamofox.daemon.models import ExecuteRequest, SessionInfo, CommandResult

def test_execute_request_valid():
    req = ExecuteRequest(command="navigate", args={"url": "https://github.com"})
    assert req.command == "navigate"
    assert req.args["url"] == "https://github.com"

def test_execute_request_defaults():
    req = ExecuteRequest(command="click")
    assert req.args == {}

def test_session_info():
    info = SessionInfo(session_id="abc", tab_id="tab-1", url="")
    assert info.session_id == "abc"
    assert info.tab_id == "tab-1"

def test_command_result_success():
    result = CommandResult(status="ok", result={"url": "https://github.com"})
    assert result.status == "ok"
    assert result.result["url"] == "https://github.com"

def test_command_result_error():
    result = CommandResult(status="error", error="Session not found")
    assert result.status == "error"
    assert result.error == "Session not found"
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `pytest tests/unit/test_models.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write models.py**

```python
# src/pycamofox/daemon/models.py
from pydantic import BaseModel, Field
from typing import Any

class ExecuteRequest(BaseModel):
    """POST /sessions/{id}/execute"""
    command: str = Field(..., description="Command name: navigate, click, type, fill, screenshot, get_text, get_html, eval, scroll, wait_network_idle, get_url, get_title")
    args: dict[str, Any] = Field(default_factory=dict, description="Command arguments")

class SessionInfo(BaseModel):
    """Session metadata"""
    session_id: str
    tab_id: str
    url: str = ""
    title: str = ""
    created_at: str = ""

class SessionList(BaseModel):
    """List of sessions"""
    sessions: list[SessionInfo]

class CommandResult(BaseModel):
    """Command execution result"""
    status: str = "ok"  # "ok" or "error"
    result: dict[str, Any] | None = None
    error: str | None = None

class CreateSessionResponse(BaseModel):
    session_id: str
    tab_id: str
    url: str = ""

class CloseSessionResponse(BaseModel):
    status: str
    session_id: str

class HealthResponse(BaseModel):
    ok: bool
    browser_running: bool
    session_count: int
```

- [ ] **Step 4: Run test — verify PASS**

Run: `pytest tests/unit/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pycamofox/daemon/models.py tests/unit/test_models.py
git commit -m "feat: add daemon Pydantic models"
```

---

## Task 4: Browser Lifecycle

**Files:**
- Create: `src/pycamofox/daemon/browser.py`
- Create: `tests/unit/test_browser.py` (mock-based)

- [ ] **Step 1: Write failing test for browser lifecycle**

```python
# tests/unit/test_browser.py
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

@pytest.mark.asyncio
async def test_browser_close_tab():
    with patch("pycamofox.daemon.browser.sync_playwright") as mock_pw:
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_browser.pages = [mock_page]
        mock_pw.return_value.__enter__.return_value = mock_browser

        browser = CamoufoxBrowser(headless=True)
        browser._browser = mock_browser
        browser._tab_to_id = {mock_page: "tab-1"}

        browser.close_tab("tab-1")
        mock_page.close.assert_called_once()
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `pytest tests/unit/test_browser.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write browser.py**

```python
# src/pycamofox/daemon/browser.py
from __future__ import annotations
import uuid
from typing import Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from playwright.sync_api import Page

class Tab:
    """Wrapper around a Playwright Page with an ID"""

    def __init__(self, id: str, page: Page):
        self.id = id
        self._page = page

    @property
    def url(self) -> str:
        return self._page.url

    @property
    def title(self) -> str:
        return self._page.title

    def goto(self, url: str, timeout: int = 30000) -> dict[str, Any]:
        self._page.goto(url, timeout=timeout)
        return {"url": self.url, "title": self.title}

    def click(self, selector: str) -> dict[str, Any]:
        self._page.click(selector)
        return {"status": "clicked", "selector": selector}

    def type(self, selector: str, text: str, delay: int = 0) -> dict[str, Any]:
        self._page.type(selector, text, delay=delay)
        return {"status": "typed", "selector": selector, "text": text}

    def fill(self, selector: str, text: str) -> dict[str, Any]:
        self._page.fill(selector, text)
        return {"status": "filled", "selector": selector, "text": text}

    def screenshot(self, **kwargs) -> bytes:
        return self._page.screenshot(**kwargs)

    def inner_text(self, selector: str = "body") -> str:
        return self._page.inner_text(selector)

    def content(self) -> str:
        return self._page.content()

    def eval(self, expression: str) -> Any:
        return self._page.eval_on_selector("body", expression)

    def scroll(self, direction: str = "down", amount: int = 1) -> dict[str, Any]:
        import time
        for _ in range(amount):
            if direction == "down":
                self._page.keyboard.press("End")
            else:
                self._page.keyboard.press("Home")
            time.sleep(0.5)
        return {"status": "scrolled", "direction": direction, "amount": amount}

    def wait_network_idle(self, timeout: int = 10000) -> dict[str, Any]:
        try:
            self._page.wait_for_load_state("networkidle", timeout=timeout)
            return {"status": "idle"}
        except Exception as e:
            return {"status": "timeout", "error": str(e)}

    def cookies(self) -> list[dict[str, Any]]:
        return self._page.context.cookies()

    def set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        self._page.context.set_cookies(cookies)

    def get_local_storage(self) -> dict[str, str]:
        result = self._page.evaluate("""() => Object.fromEntries(Object.entries(localStorage))""")
        return result if isinstance(result, dict) else {}

    def set_local_storage(self, data: dict[str, str]) -> None:
        for k, v in data.items():
            self._page.evaluate(f"localStorage.setItem({k!r}, {v!r})")

    def get_scroll_position(self) -> tuple[int, int]:
        pos = self._page.evaluate("""() => ({x: window.scrollX, y: window.scrollY})""")
        return (pos.get("x", 0), pos.get("y", 0))

    def set_scroll_position(self, x: int, y: int) -> None:
        self._page.evaluate(f"window.scrollTo({x}, {y})")

    def close(self) -> None:
        self._page.close()

    def evaluate(self, expression: str) -> Any:
        return self._page.evaluate(expression)


class CamoufoxBrowser:
    """Manages a single Camoufox browser instance with multiple tabs"""

    def __init__(self, headless: bool = False, user_data_dir: str | None = None):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self._browser: Any = None  # Camoufox browser instance
        self._playwright: Any = None
        self._tabs: dict[str, Tab] = {}  # session_id -> Tab
        self._tab_counter = 0

    def _get_os_type(self) -> str:
        import platform
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        return "windows"

    def launch(self) -> dict[str, Any]:
        """Launch the Camoufox browser"""
        from camoufox.sync_api import Camoufox, NewBrowser
        from playwright.sync_api import sync_playwright

        if self._browser is not None:
            return {"status": "already_running", "tab_count": len(self._tabs)}

        if self.user_data_dir:
            # Persistent context mode — user data dir kept across runs
            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            self._playwright = sync_playwright().start()
            self._browser = NewBrowser(
                self._playwright,
                headless=self.headless,
                os=self._get_os_type(),
                persistent_context=True,
                user_data_dir=self.user_data_dir,
            )
            # NewBrowser with persistent_context creates the browser and first page
            # Use the existing page as tab-0
            first_page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
            tab_id = self._create_tab(first_page)
        else:
            # Non-persistent mode
            kwargs = {"headless": self.headless, "os": self._get_os_type()}
            self._browser = Camoufox(**kwargs)
            self._browser = self._browser.__enter__()
            first_page = self._browser.new_page()
            tab_id = self._create_tab(first_page)

        return {"status": "launched", "tab_id": tab_id}

    def _create_tab(self, page) -> str:
        self._tab_counter += 1
        tab_id = f"tab-{self._tab_counter}"
        tab = Tab(id=tab_id, page=page)
        # Map page object to session_id (empty string for unnamed tabs)
        self._tabs[tab_id] = tab
        return tab_id

    def new_tab(self, session_id: str | None = None) -> Tab:
        """Create a new tab (session_id maps to tab)"""
        if self._browser is None:
            self.launch()

        page = self._browser.new_page()
        tab_id = self._create_tab(page)
        return self._tabs[tab_id]

    def get_tab(self, tab_id: str) -> Tab | None:
        return self._tabs.get(tab_id)

    def close_tab(self, tab_id: str) -> None:
        tab = self._tabs.pop(tab_id, None)
        if tab:
            tab.close()

    def close(self) -> None:
        """Close browser and all tabs"""
        for tab in list(self._tabs.values()):
            try:
                tab.close()
        self._tabs.clear()
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    @property
    def is_running(self) -> bool:
        return self._browser is not None
```

- [ ] **Step 4: Run test — verify PASS**

Run: `pytest tests/unit/test_browser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pycamofox/daemon/browser.py tests/unit/test_browser.py
git commit -m "feat: add CamoufoxBrowser lifecycle management"
```

---

## Task 5: Session + SessionManager

**Files:**
- Create: `src/pycamofox/daemon/session.py`
- Create: `tests/unit/test_session.py`

- [ ] **Step 1: Write failing test for SessionManager**

```python
# tests/unit/test_session.py
import pytest
import asyncio
from unittest.mock import MagicMock
from pycamofox.daemon.session import Session, SessionManager

@pytest.mark.asyncio
async def test_create_session():
    mock_browser = MagicMock()
    mock_tab = MagicMock()
    mock_tab.id = "tab-1"
    mock_browser.new_tab.return_value = mock_tab

    manager = SessionManager(mock_browser)
    session = manager.create_session("s1")

    assert session.id == "s1"
    assert session.tab.id == "tab-1"
    assert "s1" in manager._locks

@pytest.mark.asyncio
async def test_execute_serialization():
    """Two concurrent execute calls on same session should be serialized"""
    mock_browser = MagicMock()
    mock_tab = MagicMock()
    mock_tab.id = "tab-1"
    mock_tab.goto.return_value = {"url": "https://github.com"}
    mock_browser.new_tab.return_value = mock_tab

    manager = SessionManager(mock_browser)
    session = manager.create_session("s1")

    # Execute two commands concurrently
    async def cmd1():
        return await manager.execute("s1", "navigate", url="https://github.com")
    async def cmd2():
        return await manager.execute("s1", "navigate", url="https://github.com")

    results = await asyncio.gather(cmd1(), cmd2())
    assert all(r["url"] == "https://github.com" for r in results)

@pytest.mark.asyncio
async def test_different_sessions_parallel():
    """Different sessions should execute in parallel"""
    mock_browser = MagicMock()
    mock_tab1 = MagicMock()
    mock_tab1.id = "tab-1"
    mock_tab2 = MagicMock()
    mock_tab2.id = "tab-2"
    mock_browser.new_tab.side_effect = [mock_tab1, mock_tab2]

    manager = SessionManager(mock_browser)
    manager.create_session("s1")
    manager.create_session("s2")

    # Both sessions can run simultaneously (no deadlock)
    results = await asyncio.gather(
        manager.execute("s1", "navigate", url="https://a.com"),
        manager.execute("s2", "navigate", url="https://b.com"),
    )
    assert len(results) == 2

@pytest.mark.asyncio
async def test_close_session():
    mock_browser = MagicMock()
    mock_tab = MagicMock()
    mock_tab.id = "tab-1"
    mock_browser.new_tab.return_value = mock_tab

    manager = SessionManager(mock_browser)
    manager.create_session("s1")
    result = manager.close_session("s1")

    assert result["status"] == "closed"
    assert "s1" not in manager._sessions
    assert "s1" not in manager._locks
    mock_tab.close.assert_called_once()

@pytest.mark.asyncio
async def test_execute_unknown_command():
    mock_browser = MagicMock()
    mock_tab = MagicMock()
    mock_tab.id = "tab-1"
    mock_browser.new_tab.return_value = mock_tab

    manager = SessionManager(mock_browser)
    manager.create_session("s1")

    with pytest.raises(ValueError, match="Unknown command"):
        await manager.execute("s1", "nonexistent_command")
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `pytest tests/unit/test_session.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write session.py**

```python
# src/pycamofox/daemon/session.py
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from pycamofox.daemon.browser import CamoufoxBrowser, Tab
from pycamofox.persistence.session_state import SessionState, SessionStateStore

class Session:
    """Single session bound to one Tab, with its own asyncio.Lock"""

    def __init__(self, id: str, tab: Tab, state_store: SessionStateStore):
        self.id = id
        self.tab = tab
        self.lock = asyncio.Lock()
        self.state_store = state_store
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_active = self.created_at

    async def execute(self, command: str, **kwargs) -> dict[str, Any]:
        """Dispatch command to Tab within lock"""
        async with self.lock:
            self.last_active = datetime.now(timezone.utc).isoformat()
            result = self._dispatch(command, **kwargs)
            # Persist state after each operation
            self._save_state()
            return result

    def _dispatch(self, command: str, **kwargs) -> dict[str, Any]:
        dispatch = {
            "navigate": lambda: self.tab.goto(kwargs.get("url", "")),
            "click": lambda: self.tab.click(kwargs.get("selector", "")),
            "type": lambda: self.tab.type(kwargs.get("selector", ""), kwargs.get("text", "")),
            "fill": lambda: self.tab.fill(kwargs.get("selector", ""), kwargs.get("text", "")),
            "screenshot": lambda: {"data": self.tab.screenshot().hex()},
            "get_text": lambda: {"text": self.tab.inner_text(kwargs.get("selector", "body"))},
            "get_html": lambda: {"html": self.tab.content()},
            "eval": lambda: {"result": self.tab.eval(kwargs.get("expression", "null"))},
            "scroll": lambda: self.tab.scroll(kwargs.get("direction", "down"), kwargs.get("amount", 1)),
            "wait_network_idle": lambda: self.tab.wait_network_idle(kwargs.get("timeout", 10000)),
            "get_url": lambda: {"url": self.tab.url},
            "get_title": lambda: {"title": self.tab.title},
            "cookies": lambda: {"cookies": self.tab.cookies()},
            "set_cookies": lambda: (self.tab.set_cookies(kwargs.get("cookies", [])), {"status": "ok"}),
            "get_scroll": lambda: dict(zip(["x", "y"], self.tab.get_scroll_position())),
        }
        handler = dispatch.get(command)
        if handler is None:
            raise ValueError(f"Unknown command: {command}")
        return handler()

    def _save_state(self) -> None:
        """Save current state to disk"""
        scroll = self.tab.get_scroll_position()
        state = SessionState(
            session_id=self.id,
            url=self.tab.url,
            title=self.tab.title,
            cookies=self.tab.cookies(),
            local_storage=self.tab.get_local_storage(),
            scroll_position=scroll,
            created_at=self.created_at,
            last_active=self.last_active,
        )
        self.state_store.save(state)

    def get_state(self) -> SessionState:
        """Get current state without persisting"""
        scroll = self.tab.get_scroll_position()
        return SessionState(
            session_id=self.id,
            url=self.tab.url,
            title=self.title,
            cookies=self.tab.cookies(),
            local_storage=self.tab.get_local_storage(),
            scroll_position=scroll,
            created_at=self.created_at,
            last_active=self.last_active,
        )


class SessionManager:
    """Manages multiple Sessions with Per-Session Locks"""

    def __init__(self, browser: CamoufoxBrowser, state_store: SessionStateStore):
        self._browser = browser
        self._state_store = state_store
        self._sessions: dict[str, Session] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def create_session(self, session_id: str | None = None, persist_cookies: bool = True) -> Session:
        """Create new Session, allocate Tab, restore state if exists"""
        sid = session_id or str(uuid.uuid4())[:8]
        if sid in self._sessions:
            raise ValueError(f"Session {sid} already exists")

        lock = asyncio.Lock()
        tab = self._browser.new_tab()

        # Restore existing state if available
        existing_state = self._state_store.load(sid)
        if existing_state:
            # Restore cookies for the domain
            from urllib.parse import urlparse
            domain = urlparse(existing_state.url).netloc
            if existing_state.cookies:
                tab.set_cookies(existing_state.cookies)
            if existing_state.local_storage:
                tab.set_local_storage(existing_state.local_storage)
            if existing_state.url:
                try:
                    tab.goto(existing_state.url)
                except Exception:
                    pass  # If navigation fails, start fresh

        session = Session(id=sid, tab=tab, state_store=self._state_store)
        self._sessions[sid] = session
        self._locks[sid] = lock
        return session

    async def execute(self, session_id: str, command: str, **kwargs) -> dict[str, Any]:
        """Execute command within Session lock"""
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self._sessions[session_id]
        return await session.execute(command, **kwargs)

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def close_session(self, session_id: str) -> dict[str, Any]:
        """Persist full state, close Tab, cleanup"""
        session = self._sessions.pop(session_id, None)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        self._locks.pop(session_id, None)

        # Final state save
        session._save_state()
        session.tab.close()

        return {"status": "closed", "session_id": session_id}
```

- [ ] **Step 4: Run test — verify PASS**

Run: `pytest tests/unit/test_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pycamofox/daemon/session.py tests/unit/test_session.py
git commit -m "feat: add Session and SessionManager with per-session locking"
```

---

## Task 6: FastAPI Server (REST + WebSocket)

**Files:**
- Create: `src/pycamofox/daemon/server.py`
- Modify: `src/pycamofox/__init__.py`
- Modify: `src/pycamofox/__main__.py`
- Modify: `src/pycamofox/cli.py`
- Create: `tests/integration/test_server.py`

### 6a. Server

- [ ] **Step 1: Write failing test for server REST endpoints**

```python
# tests/integration/test_server.py
import pytest
from httpx import AsyncClient, ASGITransport
from pycamofox.daemon.server import create_app
from pycamofox.daemon.browser import CamoufoxBrowser
from pycamofox.persistence.storage import CamofoxStorage
import asyncio

@pytest.fixture
def storage(tmp_path):
    return CamofoxStorage(base_dir=tmp_path)

@pytest.fixture
def browser(storage):
    b = CamoufoxBrowser(headless=True)
    yield b
    b.close()

@pytest.fixture
def app(browser, storage):
    return create_app(browser=browser, storage=storage)

@pytest.mark.asyncio
async def test_health_check(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "browser_running" in data

@pytest.mark.asyncio
async def test_create_session(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "tab_id" in data

@pytest.mark.asyncio
async def test_execute_command(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        resp = await client.post("/sessions")
        session_id = resp.json()["session_id"]

        # Execute command (just get URL — no navigation in test)
        resp = await client.post(f"/sessions/{session_id}/execute", json={
            "command": "get_url"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_session_not_found(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/sessions/nonexistent")
        assert resp.status_code == 404

@pytest.mark.asyncio
async def test_close_session(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create
        resp = await client.post("/sessions")
        session_id = resp.json()["session_id"]

        # Close
        resp = await client.delete(f"/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

        # Verify gone
        resp = await client.get(f"/sessions/{session_id}")
        assert resp.status_code == 404
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `pytest tests/integration/test_server.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write server.py**

```python
# src/pycamofox/daemon/server.py
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from pycamofox.daemon.browser import CamoufoxBrowser
from pycamofox.daemon.session import SessionManager
from pycamofox.daemon.models import (
    ExecuteRequest, SessionInfo, SessionList, CommandResult,
    CreateSessionResponse, CloseSessionResponse, HealthResponse,
)
from pycamofox.persistence.storage import CamofoxStorage
from pycamofox.persistence.session_state import SessionStateStore
from pycamofox.persistence.cookies import CookieStore


# Global instances (set by create_app / run_server)
_browser: CamoufoxBrowser | None = None
_session_manager: SessionManager | None = None
_storage: CamofoxStorage | None = None


def create_app(browser: CamoufoxBrowser, storage: CamofoxStorage) -> FastAPI:
    """Create FastAPI app with dependency-injected browser and storage"""
    global _browser, _session_manager, _storage

    _browser = browser
    _storage = storage
    state_store = SessionStateStore(storage.base_dir)
    _session_manager = SessionManager(browser=browser, state_store=state_store)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: launch browser
        browser.launch()
        yield
        # Shutdown: close browser
        browser.close()

    app = FastAPI(title="pycamofox-daemon", lifespan=lifespan)

    # ── REST Endpoints ────────────────────────────────────────────

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(
            ok=True,
            browser_running=browser.is_running,
            session_count=len(_session_manager.list_sessions()),
        )

    @app.post("/sessions", response_model=CreateSessionResponse)
    async def create_session():
        session = _session_manager.create_session()
        return CreateSessionResponse(
            session_id=session.id,
            tab_id=session.tab.id,
            url=session.tab.url,
        )

    @app.get("/sessions", response_model=SessionList)
    async def list_sessions():
        sessions = _session_manager.list_sessions()
        return SessionList(sessions=[
            SessionInfo(
                session_id=s.id,
                tab_id=s.tab.id,
                url=s.tab.url,
                title=s.tab.title,
                created_at=s.created_at,
            )
            for s in sessions
        ])

    @app.get("/sessions/{session_id}", response_model=SessionInfo)
    async def get_session(session_id: str):
        session = _session_manager.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionInfo(
            session_id=session.id,
            tab_id=session.tab.id,
            url=session.tab.url,
            title=session.tab.title,
            created_at=session.created_at,
        )

    @app.delete("/sessions/{session_id}", response_model=CloseSessionResponse)
    async def close_session(session_id: str):
        try:
            result = _session_manager.close_session(session_id)
            return CloseSessionResponse(**result)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/sessions/{session_id}/execute", response_model=CommandResult)
    async def execute(session_id: str, req: ExecuteRequest):
        try:
            result = await _session_manager.execute(session_id, req.command, **req.args)
            return CommandResult(status="ok", result=result)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            return CommandResult(status="error", error=str(e))

    # ── WebSocket Endpoints ───────────────────────────────────────

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(ws: WebSocket, session_id: str):
        session = _session_manager.get_session(session_id)
        if session is None:
            await ws.close(code=4004, reason="Session not found")
            return

        await ws.accept()
        subscribed_events: set[str] = {"navigation", "network_idle", "error"}

        try:
            while True:
                # Receive messages (subscribe/unsubscribe)
                msg = await ws.receive_json()

                if msg.get("type") == "subscribe":
                    events = msg.get("events", [])
                    subscribed_events.update(events)
                elif msg.get("type") == "unsubscribe":
                    events = msg.get("events", [])
                    subscribed_events.difference_update(events)

        except WebSocketDisconnect:
            pass

    return app


def run_server(
    port: int = 9377,
    headless: bool = False,
    storage_dir: str | None = None,
):
    """Run the daemon server"""
    import uvicorn

    storage = CamofoxStorage(Path(storage_dir) if storage_dir else CamofoxStorage.default())
    browser = CamoufoxBrowser(headless=headless, user_data_dir=str(storage.base_dir / "profiles" / "default"))

    app = create_app(browser=browser, storage=storage)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
```

- [ ] **Step 4: Run test — verify PASS**

Run: `pytest tests/integration/test_server.py -v`
Expected: PASS (or skip if browser unavailable)

- [ ] **Step 5: Update __init__.py**

```python
# src/pycamofox/__init__.py
from pycamofox.daemon.browser import CamoufoxBrowser
from pycamofox.daemon.session import Session, SessionManager
from pycamofox.daemon.server import create_app, run_server
from pycamofox.persistence import CamofoxStorage, CookieStore, SessionState, SessionStateStore

__all__ = [
    "CamoufoxBrowser",
    "Session",
    "SessionManager",
    "create_app",
    "run_server",
    "CamofoxStorage",
    "CookieStore",
    "SessionState",
    "SessionStateStore",
]
```

- [ ] **Step 6: Update __main__.py to add daemon subcommand**

```python
# src/pycamofox/__main__.py (add to existing)
# ... (keep existing cli.py commands)

if __name__ == "__main__":
    # ... existing cli main
    pass  # Replace with unified entry
```

Actually, rewrite __main__.py:

```python
# src/pycamofox/__main__.py
import sys

# Check if running as "pycamofox daemon" or just "pycamofox <command>"
if len(sys.argv) >= 2 and sys.argv[1] == "daemon":
    # Daemon mode
    import argparse
    parser = argparse.ArgumentParser(prog="pycamofox daemon")
    parser.add_argument("--port", type=int, default=9377)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--storage-dir", type=str, default=None)
    args = parser.parse_args(sys.argv[2:])

    from pycamofox.daemon.server import run_server
    run_server(port=args.port, headless=args.headless, storage_dir=args.storage_dir)
else:
    # CLI mode (delegate to cli.py)
    from pycamofox.cli import main
    main()
```

- [ ] **Step 7: Commit**

```bash
git add src/pycamofox/__init__.py src/pycamofox/__main__.py src/pycamofox/daemon/server.py tests/integration/test_server.py
git commit -m "feat: add FastAPI server with REST API and WebSocket"
```

### 6b. CLI Updates

- [ ] **Step 8: Update cli.py to work with new daemon**

The cli.py currently starts its own server. Update it to:
1. Detect if daemon is already running via `GET /health`
2. If not running, start it in background
3. All commands go through REST API to the daemon

See existing cli.py patterns (keep most of it, just update `ensure_server_running` to use HTTP health check):

```python
# Update cli.py:
# - ensure_server_running() already does HTTP health check to port 9377
# - Just verify the health check URL matches new server
# - Minor: update __init__.py exports if needed
```

- [ ] **Step 9: Commit**

```bash
git add src/pycamofox/cli.py
git commit -m "chore: update CLI to work with new daemon REST API"
```

---

## Task 7: Integration Test + README

**Files:**
- Create: `tests/integration/test_daemon_flow.py`
- Modify: `README.md` (add quick start)

- [ ] **Step 1: Write integration test for full flow**

```python
# tests/integration/test_daemon_flow.py
"""End-to-end integration tests using real Camoufox browser"""
import pytest
import asyncio
from pathlib import Path
from pycamofox.daemon.browser import CamoufoxBrowser
from pycamofox.daemon.session import SessionManager
from pycamofox.persistence.storage import CamofoxStorage
from pycamofox.persistence.session_state import SessionStateStore

@pytest.fixture
def storage(tmp_path):
    return CamofoxStorage(base_dir=tmp_path)

@pytest.fixture
def browser():
    b = CamoufoxBrowser(headless=True)
    b.launch()
    yield b
    b.close()

@pytest.mark.asyncio
async def test_create_execute_close_flow(browser, storage):
    """Full session lifecycle"""
    state_store = SessionStateStore(storage.base_dir)
    manager = SessionManager(browser=browser, state_store=state_store)

    # Create session
    session = manager.create_session("flow-test")
    assert session.id == "flow-test"
    assert session.tab.url == "about:blank"

    # Execute command
    result = await manager.execute("flow-test", "get_url")
    assert result["url"] == "about:blank"

    # Close
    manager.close_session("flow-test")
    assert "flow-test" not in manager._sessions

@pytest.mark.asyncio
async def test_session_state_persistence(browser, storage):
    """Session state persists after close and restore"""
    state_store = SessionStateStore(storage.base_dir)
    manager = SessionManager(browser=browser, state_store=state_store)

    # Create and navigate
    session = manager.create_session("persist-test")
    await manager.execute("persist-test", "navigate", url="https://example.com")

    # Close
    manager.close_session("persist-test")

    # State file should exist
    state = state_store.load("persist-test")
    assert state is not None
    assert "example.com" in state.url

    # Restore — create new session with same ID
    session2 = manager.create_session("persist-test")
    assert session2.tab.url == "https://example.com"  # Restored
    manager.close_session("persist-test")

@pytest.mark.asyncio
async def test_concurrent_sessions(browser, storage):
    """Multiple sessions can operate concurrently"""
    state_store = SessionStateStore(storage.base_dir)
    manager = SessionManager(browser=browser, state_store=state_store)

    manager.create_session("concurrent-1")
    manager.create_session("concurrent-2")

    # Both can execute simultaneously (parallel, not deadlocked)
    results = await asyncio.gather(
        manager.execute("concurrent-1", "get_url"),
        manager.execute("concurrent-2", "get_url"),
    )
    assert len(results) == 2

    manager.close_session("concurrent-1")
    manager.close_session("concurrent-2")
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/integration/test_daemon_flow.py -v`
Expected: Tests pass (or skip if Camoufox not available)

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_daemon_flow.py
git commit -m "test: add integration tests for full session lifecycle"
```

- [ ] **Step 4: Update README with quick start**

Add to README.md:

```markdown
## Quick Start

### Start Daemon

```bash
python -m pycamofox daemon --port 9377 --headless
```

### Using the REST API

```bash
# Create session
curl -X POST http://127.0.0.1:9377/sessions

# Execute command
curl -X POST http://127.0.0.1:9377/sessions/{id}/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "navigate", "args": {"url": "https://github.com"}}'

# Close session
curl -X DELETE http://127.0.0.1:9377/sessions/{id}
```

### Python Client

```python
from pycamofox import CamoufoxBrowser, SessionManager

browser = CamoufoxBrowser(headless=True)
browser.launch()

manager = SessionManager(browser=browser)
session = manager.create_session()

import asyncio
result = asyncio.run(manager.execute(session.id, "navigate", url="https://github.com"))
print(result)

browser.close()
```
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add daemon quick start guide"
```

---

## Task 8: Final Review

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All pass (integration tests may skip if no browser)

- [ ] **Step 2: Verify all acceptance criteria**

Check against spec:
- [ ] `python -m pycamofox daemon` starts daemon on port 9377
- [ ] `POST /sessions` creates session
- [ ] Multiple sessions exist simultaneously
- [ ] Operations within session are serialized (per-session lock)
- [ ] Operations across sessions are parallel
- [ ] `DELETE /sessions/{id}` closes session
- [ ] Session state persists (cookies, scroll, localStorage)
- [ ] Session can be restored
- [ ] WebSocket `/ws/{session_id}` connects
- [ ] CLI commands work

- [ ] **Step 3: Final commit**

```bash
git add -A && git commit -m "feat: complete Phase 1 Browser Daemon Core"
```

---

## Spec Coverage Check

| Spec Requirement | Task(s) |
|-----------------|---------|
| Single Browser + Multiple Sessions | Task 4, 5 |
| Per-Session asyncio.Lock | Task 5 |
| Full state persistence | Task 2, 5 |
| REST API endpoints | Task 6 |
| WebSocket handler | Task 6 |
| Session create/close/restore | Task 5, 6 |
| Concurrency model | Task 5 |
| CLI compatibility | Task 6 |

---

## File Summary

| File | Action |
|------|--------|
| `pyproject.toml` | Modify |
| `src/pycamofox/__init__.py` | Modify |
| `src/pycamofox/__main__.py` | Modify |
| `src/pycamofox/cli.py` | Modify (minimal) |
| `src/pycamofox/daemon/__init__.py` | Create |
| `src/pycamofox/daemon/models.py` | Create |
| `src/pycamofox/daemon/browser.py` | Create |
| `src/pycamofox/daemon/session.py` | Create |
| `src/pycamofox/daemon/server.py` | Create |
| `src/pycamofox/persistence/__init__.py` | Create |
| `src/pycamofox/persistence/storage.py` | Create |
| `src/pycamofox/persistence/cookies.py` | Create |
| `src/pycamofox/persistence/session_state.py` | Create |
| `tests/conftest.py` | Create |
| `tests/unit/test_models.py` | Create |
| `tests/unit/test_state.py` | Create |
| `tests/unit/test_cookies.py` | Create |
| `tests/unit/test_storage.py` | Create |
| `tests/unit/test_browser.py` | Create |
| `tests/unit/test_session.py` | Create |
| `tests/integration/test_server.py` | Create |
| `tests/integration/test_daemon_flow.py` | Create |
| `README.md` | Modify |
