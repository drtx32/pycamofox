# tests/unit/test_cookies.py
from pycamofox.persistence.cookies import CookieStore
import json

def test_cookie_store_save(tmp_path):
    store = CookieStore(tmp_path)
    cookies = [{"name": "session", "value": "abc", "domain": ".github.com"}]
    store.save("github.com", cookies)

    content = (tmp_path / "cookies" / "github.com.json").read_text()
    assert json.loads(content) == cookies

def test_cookie_store_load(tmp_path):
    store = CookieStore(tmp_path)
    cookies = [{"name": "session", "value": "abc", "domain": ".github.com"}]
    store.save("github.com", cookies)

    loaded = store.load("github.com")
    assert loaded == cookies

def test_cookie_store_load_missing(tmp_path):
    store = CookieStore(tmp_path)
    assert store.load("nonexistent.com") == []