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