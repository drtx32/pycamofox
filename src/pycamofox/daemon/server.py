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


# Global instances
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
        browser.launch()
        yield
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