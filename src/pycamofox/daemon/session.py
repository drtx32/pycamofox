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
            "set_cookies": lambda: (self.tab.set_cookies(kwargs.get("cookies", [])), {"status": "ok"})[1],
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
            title=self.tab.title,
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

    def create_session(self, session_id: str | None = None) -> Session:
        """Create new Session, allocate Tab"""
        sid = session_id or str(uuid.uuid4())[:8]
        if sid in self._sessions:
            raise ValueError(f"Session {sid} already exists")

        lock = asyncio.Lock()
        tab = self._browser.new_tab()

        # Restore existing state if available
        existing_state = self._state_store.load(sid)
        if existing_state:
            if existing_state.cookies:
                tab.set_cookies(existing_state.cookies)
            if existing_state.local_storage:
                tab.set_local_storage(existing_state.local_storage)
            if existing_state.url:
                try:
                    tab.goto(existing_state.url)
                except Exception:
                    pass

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
        session._save_state()
        session.tab.close()

        return {"status": "closed", "session_id": session_id}