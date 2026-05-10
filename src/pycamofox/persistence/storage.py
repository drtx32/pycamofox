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