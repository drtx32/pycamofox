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