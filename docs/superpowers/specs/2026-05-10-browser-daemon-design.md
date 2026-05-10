# Browser Daemon Core — Design Spec

> Phase 1: Browser Daemon with Per-Session Locking and Full State Persistence
> Date: 2026-05-10

---

## 1. Overview

**Goal**: Build a stable Browser Runtime Daemon that manages a single Camoufox Browser instance supporting multiple concurrent Sessions.

**Key Characteristics**:
- Single Camoufox Browser + Multiple Tabs (one Tab per Session)
- Per-Session asyncio.Lock for concurrency control (operations within a Session are serialized)
- Different Sessions can execute in parallel (different Locks)
- Full Session state persistence (cookies, localStorage, scroll_position) on close
- REST API + WebSocket on unified port

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                           │
│                   (localhost:9377)                          │
│  ┌─────────────────┐       ┌───────────────────────────┐   │
│  │   REST API      │       │   WebSocket Handler       │   │
│  │   /sessions/*  │       │   /ws/{session_id}        │   │
│  └────────┬────────┘       └───────────┬───────────────┘   │
│           │                            │                    │
│  ┌────────▼────────────────────────────▼───────────────┐   │
│  │              Session Manager                          │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │   │
│  │  │Session-1│  │Session-2│  │Session-N│             │   │
│  │  │ Lock-S1 │  │ Lock-S2 │  │ Lock-SN │             │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘             │   │
│  └───────┼────────────┼────────────┼──────────────────┘   │
│          │            │            │                        │
│  ┌───────▼────────────▼────────────▼──────────────────┐   │
│  │              Camoufox Browser                        │   │
│  │  ┌──────────┐  ┌──────────┐                        │   │
│  │  │  Tab-1   │  │  Tab-2   │  ...                  │   │
│  │  │(Session-1)│ │(Session-2)│                        │   │
│  │  └──────────┘  └──────────┘                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                 │
│  ┌───────────────────────▼───────────────────────────────┐ │
│  │              Persistence Layer                          │ │
│  │   ~/.camofox/sessions/{session_id}/state.json         │ │
│  │   ~/.camofox/cookies/{domain}.json                     │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
src/pycamofox/
├── __init__.py
├── __main__.py
├── cli.py                     # CLI client (kept, minimal changes)
├── daemon/                    # NEW: Browser Daemon Core
│   ├── __init__.py
│   ├── server.py              # FastAPI app + REST routes + WebSocket
│   ├── browser.py             # Camoufox lifecycle management
│   ├── session.py             # Session class + Per-Session Lock
│   ├── state.py               # SessionState persistence model
│   └── models.py              # Pydantic request/response models
└── persistence/               # State storage utilities
    ├── __init__.py
    ├── cookies.py             # Per-domain cookie persistence
    ├── session_state.py       # Session state save/restore
    └── storage.py             # File storage utilities
```

---

## 4. Components

### 4.1 SessionManager

```python
class SessionManager:
    """Manages multiple Sessions with Per-Session Locks"""

    def __init__(self, browser: CamoufoxBrowser):
        self._sessions: dict[str, Session] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._browser = browser
        self._tab_to_session: dict[str, str] = {}  # tab_id -> session_id

    def create_session(self, session_id: str | None = None) -> Session:
        """Create new Session, allocate Tab, save initial state"""
        sid = session_id or str(uuid.uuid4())[:8]
        lock = asyncio.Lock()
        tab = self._browser.new_tab()
        session = Session(id=sid, tab=tab, lock=lock)
        self._sessions[sid] = session
        self._locks[sid] = lock
        self._tab_to_session[tab.id] = sid
        self._persist_state(session)
        return session

    async def execute(self, session_id: str, command: str, **kwargs) -> dict:
        """Execute command within Session lock"""
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")

        async with self._locks[session_id]:
            session = self._sessions[session_id]
            result = await session.execute(command, **kwargs)
            self._persist_state(session)
            return result

    def close_session(self, session_id: str) -> dict:
        """Persist full state, close Tab, cleanup"""
        session = self._sessions.pop(session_id)
        self._locks.pop(session_id)
        tab_id = session.tab.id
        self._tab_to_session.pop(tab_id, None)
        self._persist_state(session)  # Final state save
        session.tab.close()
        return {"status": "closed", "session_id": session_id}
```

### 4.2 Session

```python
class Session:
    """Single session bound to one Tab, with its own Lock"""

    def __init__(self, id: str, tab: Tab, lock: asyncio.Lock):
        self.id = id
        self.tab = tab
        self.lock = lock
        self.created_at = datetime.now()
        self.last_active = datetime.now()

    async def execute(self, command: str, **kwargs) -> dict:
        """Dispatch command to Tab"""
        self.last_active = datetime.now()
        dispatch = {
            "navigate": self.tab.goto,
            "click": self.tab.click,
            "type": self.tab.type,
            "fill": self.tab.fill,
            "screenshot": self.tab.screenshot,
            "get_text": self.tab.inner_text,
            "get_html": self.tab.content,
            "eval": self.tab.eval,
            "scroll": self.tab.scroll,
            "wait_network_idle": self.tab.wait_network_idle,
            "get_url": lambda: {"url": self.tab.url},
            "get_title": lambda: {"title": self.tab.title},
        }
        handler = dispatch.get(command)
        if not handler:
            raise ValueError(f"Unknown command: {command}")
        return handler(**kwargs)
```

### 4.3 SessionState

```python
@dataclass
class SessionState:
    """Full session state for persistence and restore"""
    session_id: str
    url: str
    title: str
    cookies: list[dict]
    local_storage: dict[str, str]
    scroll_position: tuple[int, int]
    created_at: str
    last_active: str

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> SessionState: ...

    def save(self, path: Path):
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, session_dir: Path) -> SessionState | None:
        state_file = session_dir / "state.json"
        if state_file.exists():
            return cls.from_dict(json.loads(state_file.read_text()))
        return None
```

### 4.4 Persistence Layout

```
~/.camofox/
├── sessions/
│   └── {session_id}/
│       ├── state.json        # SessionState (cookies, localStorage, scroll)
│       └── screenshot.png    # Optional: last screenshot
└── cookies/
    └── {domain}.json         # Per-domain cookies
```

---

## 5. REST API

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions` | Create new session |
| GET | `/sessions` | List all sessions |
| GET | `/sessions/{session_id}` | Get session info |
| DELETE | `/sessions/{session_id}` | Close session |
| POST | `/sessions/{session_id}/execute` | Execute command |
| WS | `/ws/{session_id}` | WebSocket for events |

### Request/Response Models

```python
# POST /sessions
# Request: {}
# Response: {"session_id": "abc123", "tab_id": "tab-1", "url": ""}

# POST /sessions/{id}/execute
class ExecuteRequest(BaseModel):
    command: str              # "navigate", "click", "type", etc.
    args: dict[str, Any] = {} # command arguments

# Response: {"status": "ok", "result": {...}}

# DELETE /sessions/{id}
# Response: {"status": "closed", "session_id": "abc123"}
```

---

## 6. WebSocket Protocol

### Client → Server

```json
{"type": "subscribe", "events": ["navigation", "network_idle"]}
{"type": "unsubscribe", "events": ["navigation"]}
```

### Server → Client

```json
{"type": "navigation", "session_id": "abc", "url": "https://github.com", "tab_id": "tab-1"}
{"type": "network_idle", "session_id": "abc", "tab_id": "tab-1"}
{"type": "error", "session_id": "abc", "reason": "click_failed", "selector": "#btn"}
```

---

## 7. Concurrency Model

```
Agent A: POST /sessions/s1/execute (click)  ─┐
Agent B: POST /sessions/s1/execute (type)  ─┼─→ Lock-S1 (serialized)
Agent C: POST /sessions/s2/execute (nav)   ─┼─→ Lock-S2 (parallel)
Agent D: POST /sessions/s2/execute (shot)  ─┘
```

**Rules**:
1. All operations within a Session are serialized via its Lock
2. Operations across different Sessions are parallel
3. Lock is held only during actual browser operation
4. State is persisted after each operation (before releasing lock)

---

## 8. Session Lifecycle

### Create
1. Generate session_id
2. Allocate new Tab from Browser
3. Create asyncio.Lock for session
4. Save initial state (empty)

### Active
1. Each execute() acquires lock
2. Run command on Tab
3. Update state (url, cookies, scroll)
4. Persist state to disk
5. Release lock

### Close
1. Final state save (cookies, localStorage, scroll_position)
2. Close Tab
3. Remove from session registry
4. Delete lock

### Restore
1. Load state from disk
2. Create new Tab
3. Navigate to saved URL
4. Restore cookies (per-domain)
5. Restore localStorage
6. Restore scroll position
7. Resume operations

---

## 9. Error Handling

| Error | Response |
|-------|----------|
| Session not found | 404 `{"error": "Session not found"}` |
| Unknown command | 400 `{"error": "Unknown command: foo"}` |
| Browser crashed | 500 `{"error": "Browser crashed", "detail": "..."}` |
| Lock acquisition timeout | 408 `{"error": "Session busy, try again"}` |

---

## 10. Phase 1 Scope (Out of Scope)

- Persona System (Phase 2)
- Semantic Observation Pipeline (Phase 2)
- Event Bus (Phase 2)
- Skill Runtime (Phase 2)
- Multi-Agent Architecture (Phase 3)

---

## 11. Acceptance Criteria

- [ ] `python -m pycamofox daemon` starts daemon on port 9377
- [ ] `POST /sessions` creates session and returns session_id
- [ ] Multiple sessions can exist simultaneously
- [ ] Operations within a session are serialized
- [ ] Operations across sessions are parallel
- [ ] `DELETE /sessions/{id}` closes session and persists state
- [ ] Session can be recreated with state restored
- [ ] WebSocket `/ws/{session_id}` connects successfully
- [ ] Events are pushed to WebSocket clients
- [ ] CLI commands work against new daemon

---

## 12. Dependencies

- `camoufox` — stealth browser engine
- `fastapi` — REST API framework
- `uvicorn` — ASGI server
- `pydantic` — data validation
- `websockets` — WebSocket support (or use fastapi.websockets)
