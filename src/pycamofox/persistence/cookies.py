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