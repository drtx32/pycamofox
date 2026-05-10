from __future__ import annotations
import uuid
from typing import Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from playwright.sync_api import Page

class Tab:
    """Wrapper around a Playwright Page with an ID"""

    def __init__(self, id: str, page: Page):
        self.id = id
        self._page = page

    @property
    def url(self) -> str:
        return self._page.url

    @property
    def title(self) -> str:
        return self._page.title

    def goto(self, url: str, timeout: int = 30000) -> dict[str, Any]:
        self._page.goto(url, timeout=timeout)
        return {"url": self.url, "title": self.title}

    def click(self, selector: str) -> dict[str, Any]:
        self._page.click(selector)
        return {"status": "clicked", "selector": selector}

    def type(self, selector: str, text: str, delay: int = 0) -> dict[str, Any]:
        self._page.type(selector, text, delay=delay)
        return {"status": "typed", "selector": selector, "text": text}

    def fill(self, selector: str, text: str) -> dict[str, Any]:
        self._page.fill(selector, text)
        return {"status": "filled", "selector": selector, "text": text}

    def screenshot(self, **kwargs) -> bytes:
        return self._page.screenshot(**kwargs)

    def inner_text(self, selector: str = "body") -> str:
        return self._page.inner_text(selector)

    def content(self) -> str:
        return self._page.content()

    def eval(self, expression: str) -> Any:
        return self._page.eval_on_selector("body", expression)

    def scroll(self, direction: str = "down", amount: int = 1) -> dict[str, Any]:
        import time
        for _ in range(amount):
            if direction == "down":
                self._page.keyboard.press("End")
            else:
                self._page.keyboard.press("Home")
            time.sleep(0.5)
        return {"status": "scrolled", "direction": direction, "amount": amount}

    def wait_network_idle(self, timeout: int = 10000) -> dict[str, Any]:
        try:
            self._page.wait_for_load_state("networkidle", timeout=timeout)
            return {"status": "idle"}
        except Exception as e:
            return {"status": "timeout", "error": str(e)}

    def cookies(self) -> list[dict[str, Any]]:
        return self._page.context.cookies()

    def set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        self._page.context.set_cookies(cookies)

    def get_local_storage(self) -> dict[str, str]:
        result = self._page.evaluate("""() => Object.fromEntries(Object.entries(localStorage))""")
        return result if isinstance(result, dict) else {}

    def set_local_storage(self, data: dict[str, str]) -> None:
        for k, v in data.items():
            self._page.evaluate(f"localStorage.setItem({k!r}, {v!r})")

    def get_scroll_position(self) -> tuple[int, int]:
        pos = self._page.evaluate("""() => ({x: window.scrollX, y: window.scrollY})""")
        return (pos.get("x", 0), pos.get("y", 0))

    def set_scroll_position(self, x: int, y: int) -> None:
        self._page.evaluate(f"window.scrollTo({x}, {y})")

    def close(self) -> None:
        self._page.close()

    def evaluate(self, expression: str) -> Any:
        return self._page.evaluate(expression)


class CamoufoxBrowser:
    """Manages a single Camoufox browser instance with multiple tabs"""

    def __init__(self, headless: bool = False, user_data_dir: str | None = None):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self._browser: Any = None
        self._playwright: Any = None
        self._tabs: dict[str, Tab] = {}
        self._tab_counter = 0

    def _get_os_type(self) -> str:
        import platform
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        return "windows"

    def launch(self) -> dict[str, Any]:
        """Launch the Camoufox browser"""
        from camoufox.sync_api import Camoufox, NewBrowser
        from playwright.sync_api import sync_playwright

        if self._browser is not None:
            return {"status": "already_running", "tab_count": len(self._tabs)}

        if self.user_data_dir:
            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            self._playwright = sync_playwright().start()
            self._browser = NewBrowser(
                self._playwright,
                headless=self.headless,
                os=self._get_os_type(),
                persistent_context=True,
                user_data_dir=self.user_data_dir,
            )
            first_page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
            tab_id = self._create_tab(first_page)
        else:
            kwargs = {"headless": self.headless, "os": self._get_os_type()}
            self._browser = Camoufox(**kwargs)
            self._browser = self._browser.__enter__()
            first_page = self._browser.new_page()
            tab_id = self._create_tab(first_page)

        return {"status": "launched", "tab_id": tab_id}

    def _create_tab(self, page) -> str:
        self._tab_counter += 1
        tab_id = f"tab-{self._tab_counter}"
        tab = Tab(id=tab_id, page=page)
        self._tabs[tab_id] = tab
        return tab_id

    def new_tab(self) -> Tab:
        """Create a new tab"""
        if self._browser is None:
            self.launch()

        page = self._browser.new_page()
        tab_id = self._create_tab(page)
        return self._tabs[tab_id]

    def get_tab(self, tab_id: str) -> Tab | None:
        return self._tabs.get(tab_id)

    def close_tab(self, tab_id: str) -> None:
        tab = self._tabs.pop(tab_id, None)
        if tab:
            tab.close()

    def close(self) -> None:
        """Close browser and all tabs"""
        for tab in list(self._tabs.values()):
            try:
                tab.close()
            except Exception:
                pass
        self._tabs.clear()
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    @property
    def is_running(self) -> bool:
        return self._browser is not None
