from __future__ import annotations
import asyncio
import threading
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


class Tab:
    """Wrapper around a Playwright Async Page with an ID"""

    def __init__(self, id: str, page: Page):
        self.id = id
        self._page = page

    @property
    def url(self) -> str:
        return self._page.url

    async def title(self) -> str:
        return await self._page.title()

    async def goto(self, url: str, timeout: int = 30000) -> dict[str, Any]:
        await self._page.goto(url, timeout=timeout)
        return {"url": self.url, "title": await self.title()}

    async def click(self, selector: str) -> dict[str, Any]:
        await self._page.click(selector)
        return {"status": "clicked", "selector": selector}

    async def type(self, selector: str, text: str, delay: int = 0) -> dict[str, Any]:
        await self._page.type(selector, text, delay=delay)
        return {"status": "typed", "selector": selector, "text": text}

    async def fill(self, selector: str, text: str) -> dict[str, Any]:
        await self._page.fill(selector, text)
        return {"status": "filled", "selector": selector, "text": text}

    async def screenshot(self, **kwargs) -> bytes:
        return await self._page.screenshot(**kwargs)

    async def inner_text(self, selector: str = "body") -> str:
        return await self._page.inner_text(selector)

    async def content(self) -> str:
        return self._page.content()

    async def eval(self, expression: str) -> Any:
        return await self._page.eval_on_selector("body", expression)

    async def scroll(self, direction: str = "down", amount: int = 1) -> dict[str, Any]:
        import time
        for _ in range(amount):
            if direction == "down":
                await self._page.keyboard.press("End")
            else:
                await self._page.keyboard.press("Home")
            time.sleep(0.5)
        return {"status": "scrolled", "direction": direction, "amount": amount}

    async def wait_network_idle(self, timeout: int = 10000) -> dict[str, Any]:
        try:
            await self._page.wait_for_load_state("networkidle", timeout=timeout)
            return {"status": "idle"}
        except Exception as e:
            return {"status": "timeout", "error": str(e)}

    async def cookies(self) -> list[dict[str, Any]]:
        return await self._page.context.cookies()

    async def set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        await self._page.context.set_cookies(cookies)

    async def get_local_storage(self) -> dict[str, str]:
        result = await self._page.evaluate("""() => Object.fromEntries(Object.entries(localStorage))""")
        return result if isinstance(result, dict) else {}

    async def set_local_storage(self, data: dict[str, str]) -> None:
        for k, v in data.items():
            await self._page.evaluate(f"localStorage.setItem({k!r}, {v!r})")

    async def get_scroll_position(self) -> tuple[int, int]:
        pos = await self._page.evaluate("""() => ({x: window.scrollX, y: window.scrollY})""")
        return (pos.get("x", 0), pos.get("y", 0))

    async def set_scroll_position(self, x: int, y: int) -> None:
        await self._page.evaluate(f"window.scrollTo({x}, {y})")

    async def close(self) -> None:
        await self._page.close()

    async def evaluate(self, expression: str) -> Any:
        return await self._page.evaluate(expression)


class CamoufoxBrowser:
    """Manages a single Camoufox browser instance with multiple tabs.

    Uses a persistent background thread with its own event loop for all browser operations.
    Supports stealth mode with anti-detection hooks from camoufox-reverse.
    """

    def __init__(self, headless: bool = False, user_data_dir: str | None = None, stealth: str = "default"):
        """Initialize browser.

        Args:
            headless: Run in headless mode.
            user_data_dir: Optional persistent user data directory.
            stealth: Stealth mode - "none", "default", "compatible", "maximum".
        """
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.stealth = stealth
        self._host_os: str | None = None
        self._target_os: str | None = None
        self._browser: Any = None
        self._camoufox: Any = None
        self._playwright: Any = None
        self._context: Any = None
        self._tabs: dict[str, Tab] = {}
        self._tab_counter = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _get_os_type(self) -> str:
        import platform
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        return "windows"

    def _ensure_started(self) -> None:
        """Ensure the browser thread is running and browser is launched."""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_browser_loop, daemon=True)
            self._thread.start()
            # Wait for browser to be launched
            while self._browser is None:
                import time; time.sleep(0.01)

    def _run_browser_loop(self) -> None:
        """Run the browser event loop in a dedicated thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._browser_main())

    async def _inject_stealth_hooks(self, context) -> None:
        """Inject stealth JS hooks into the browser context."""
        if self.stealth == "none":
            return

        # Font fallback when OS fingerprint differs from host
        if self._target_os and self._host_os and self._target_os != self._host_os:
            from pycamofox.stealth import get_font_fallback_script
            await context.add_init_script(get_font_fallback_script())

        # Core stealth hooks
        from pycamofox.stealth import get_stealth_script
        stealth_js = get_stealth_script(self.stealth)
        if stealth_js:
            await context.add_init_script(stealth_js)

    async def _browser_main(self) -> None:
        """Main browser async task - launches browser and processes commands."""
        from camoufox.async_api import AsyncCamoufox
        from playwright.async_api import async_playwright

        self._host_os = self._get_os_type()
        self._target_os = self._host_os

        if self.user_data_dir:
            self._playwright = await async_playwright().start()
            from pathlib import Path
            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            context = await self._playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=self.headless,
            )
            self._browser = context.browser
            self._context = context
            first_page = context.pages[0] if context.pages else await context.new_page()
        else:
            self._camoufox = AsyncCamoufox(headless=self.headless, os=self._target_os)
            self._browser = await self._camoufox.__aenter__()
            # Get or create default context
            if self._browser.contexts:
                self._context = self._browser.contexts[0]
            else:
                self._context = await self._browser.new_context()
            first_page = await self._context.new_page()

        # Inject stealth hooks
        await self._inject_stealth_hooks(self._context)

        tab_id = self._create_tab(first_page)

        # Keep the loop running to handle subsequent operations
        while self._browser.is_connected():
            await asyncio.sleep(0.1)

    def _create_tab(self, page) -> str:
        self._tab_counter += 1
        tab_id = f"tab-{self._tab_counter}"
        tab = Tab(id=tab_id, page=page)
        self._tabs[tab_id] = tab
        return tab_id

    def _run_async(self, coro) -> Any:
        """Run a coroutine in the browser thread's event loop."""
        if self._loop is None:
            raise RuntimeError("Browser loop not initialized. Call launch() first.")
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def launch(self) -> dict[str, Any]:
        """Launch the Camoufox browser."""
        self._ensure_started()
        return {"status": "launched", "tab_count": len(self._tabs)}

    def new_tab(self) -> Tab:
        """Create a new tab."""
        self._ensure_started()
        return self._run_async(self._new_tab_async())

    async def _new_tab_async(self) -> Tab:
        page = await self._browser.new_page()
        tab_id = self._create_tab(page)
        return self._tabs[tab_id]

    def get_tab(self, tab_id: str) -> Tab | None:
        return self._tabs.get(tab_id)

    def close_tab(self, tab_id: str) -> None:
        if tab_id in self._tabs:
            tab = self._tabs.pop(tab_id)
            self._run_async(tab.close())

    async def _close_async(self) -> None:
        for tab in list(self._tabs.values()):
            try:
                await tab.close()
            except Exception:
                pass
        self._tabs.clear()
        if self._camoufox:
            await self._camoufox.__aexit__(None, None, None)
        elif self._playwright:
            await self._playwright.__aexit__(None, None, None)
        elif self._browser:
            await self._browser.close()

    def close(self) -> None:
        if self._loop:
            try:
                self._run_async(self._close_async())
            except Exception:
                pass

    @property
    def is_running(self) -> bool:
        return self._browser is not None and self._browser.is_connected()
