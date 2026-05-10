from __future__ import annotations
import asyncio
import uuid
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

    @property
    def title(self) -> str:
        return self._page.title

    async def goto(self, url: str, timeout: int = 30000) -> dict[str, Any]:
        await self._page.goto(url, timeout=timeout)
        return {"url": self.url, "title": self.title}

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
        return await self._page.content()

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

    def cookies(self) -> list[dict[str, Any]]:
        # sync — no await needed for context.cookies()
        return self._page.context.cookies()

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

    async def launch_async(self) -> dict[str, Any]:
        """Launch the Camoufox browser (async)"""
        from camoufox.async_api import AsyncCamoufox
        from playwright.async_api import async_playwright

        if self._browser is not None:
            return {"status": "already_running", "tab_count": len(self._tabs)}

        self._playwright = await async_playwright().start()

        if self.user_data_dir:
            # Persistent context mode
            from pathlib import Path
            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            # Use standard Chromium with persistent context
            context = await self._playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=self.headless,
            )
            self._browser = context.browser
            first_page = context.pages[0] if context.pages else await context.new_page()
        else:
            # Use Camoufox async API
            self._browser = await AsyncCamoufox(headless=self.headless, os=self._get_os_type()).__aenter__()
            first_page = await self._browser.new_page()

        tab_id = self._create_tab(first_page)
        return {"status": "launched", "tab_id": tab_id}

    def launch(self) -> dict[str, Any]:
        """Launch the Camoufox browser (sync wrapper)"""
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.launch_async())
                return future.result()
        except RuntimeError:
            # No running event loop, safe to use asyncio.run
            return asyncio.run(self.launch_async())

    def _create_tab(self, page) -> str:
        self._tab_counter += 1
        tab_id = f"tab-{self._tab_counter}"
        tab = Tab(id=tab_id, page=page)
        self._tabs[tab_id] = tab
        return tab_id

    async def new_tab_async(self) -> Tab:
        """Create a new tab (async)"""
        if self._browser is None:
            await self.launch_async()

        page = await self._browser.new_page()
        tab_id = self._create_tab(page)
        return self._tabs[tab_id]

    def new_tab(self) -> Tab:
        """Create a new tab (sync wrapper)"""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.new_tab_async())
                return future.result()
        except RuntimeError:
            return asyncio.run(self.new_tab_async())

    def get_tab(self, tab_id: str) -> Tab | None:
        return self._tabs.get(tab_id)

    def close_tab(self, tab_id: str) -> None:
        tab = self._tabs.pop(tab_id, None)
        if tab:
            asyncio.run(tab.close())

    async def aclose(self) -> None:
        """Close browser and all tabs (async)"""
        for tab in list(self._tabs.values()):
            try:
                await tab.close()
            except Exception:
                pass
        self._tabs.clear()
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.__aexit__(None, None, None)
            self._playwright = None

    def close(self) -> None:
        """Close browser and all tabs (sync wrapper)"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.aclose())
        except RuntimeError:
            asyncio.run(self.aclose())

    @property
    def is_running(self) -> bool:
        return self._browser is not None
