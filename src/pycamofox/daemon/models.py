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