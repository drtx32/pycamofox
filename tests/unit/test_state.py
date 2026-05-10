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