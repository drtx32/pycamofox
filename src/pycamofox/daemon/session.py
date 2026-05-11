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
            result = await self._dispatch(command, **kwargs)
            await self._save_state_async()
            return result

    async def _dispatch(self, command: str, **kwargs) -> dict[str, Any]:
        if command == "navigate":
            return await self.tab.goto(kwargs.get("url", ""))
        elif command == "click":
            return await self.tab.click(kwargs.get("selector", ""))
        elif command == "type":
            return await self.tab.type(kwargs.get("selector", ""), kwargs.get("text", ""))
        elif command == "fill":
            return await self.tab.fill(kwargs.get("selector", ""), kwargs.get("text", ""))
        elif command == "screenshot":
            return {"data": (await self.tab.screenshot()).hex()}
        elif command == "get_text":
            return {"text": await self.tab.inner_text(kwargs.get("selector", "body"))}
        elif command == "get_html":
            return {"html": await self.tab.content()}
        elif command == "eval":
            return {"result": await self.tab.eval(kwargs.get("expression", "null"))}
        elif command == "scroll":
            return await self.tab.scroll(kwargs.get("direction", "down"), kwargs.get("amount", 1))
        elif command == "wait_network_idle":
            return await self.tab.wait_network_idle(kwargs.get("timeout", 10000))
        elif command == "get_url":
            return {"url": self.tab.url}
        elif command == "get_title":
            return {"title": await self.tab.title()}
        elif command == "cookies":
            return {"cookies": await self.tab.cookies()}
        elif command == "set_cookies":
            await self.tab.set_cookies(kwargs.get("cookies", []))
            return {"status": "ok"}
        elif command == "get_scroll":
            return dict(zip(["x", "y"], await self.tab.get_scroll_position()))
        else:
            raise ValueError(f"Unknown command: {command}")

    async def _save_state_async(self) -> None:
        """Save current state to disk (async)"""
        try:
            scroll = await self.tab.get_scroll_position()
            local_storage = await self.tab.get_local_storage()
        except Exception:
            # Some pages (e.g., about:blank) may not allow localStorage access
            scroll = (0, 0)
            local_storage = {}
        state = SessionState(
            session_id=self.id,
            url=self.tab.url,
            title=await self.tab.title(),
            cookies=await self.tab.cookies(),
            local_storage=local_storage,
            scroll_position=scroll,
            created_at=self.created_at,
            last_active=self.last_active,
        )
        self.state_store.save(state)

    def _save_state(self) -> None:
        """Save current state to disk (sync wrapper)"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._save_state_async())
        except RuntimeError:
            asyncio.run(self._save_state_async())

    async def get_state_async(self) -> SessionState:
        """Get current state without persisting (async)"""
        try:
            scroll = await self.tab.get_scroll_position()
            local_storage = await self.tab.get_local_storage()
        except Exception:
            scroll = (0, 0)
            local_storage = {}
        return SessionState(
            session_id=self.id,
            url=self.tab.url,
            title=await self.tab.title(),
            cookies=await self.tab.cookies(),
            local_storage=local_storage,
            scroll_position=scroll,
            created_at=self.created_at,
            last_active=self.last_active,
        )

    def get_state(self) -> SessionState:
        """Get current state without persisting (sync wrapper)"""
        try:
            loop = asyncio.get_running_loop()
            # Can't easily await in sync method, create a coroutine and run it
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.get_state_async())
                return future.result()
        except RuntimeError:
            return asyncio.run(self.get_state_async())


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
                asyncio.run(tab.set_cookies(existing_state.cookies))
            if existing_state.local_storage:
                asyncio.run(tab.set_local_storage(existing_state.local_storage))
            if existing_state.url:
                try:
                    asyncio.run(tab.goto(existing_state.url))
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

        # Close tab - handle both sync and async contexts
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, schedule the close
            loop.create_task(session.tab.close())
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            asyncio.run(session.tab.close())

        return {"status": "closed", "session_id": session_id}
