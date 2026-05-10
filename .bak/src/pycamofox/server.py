"""
pycamofox-server - REST API server for camoufox browser
复刻 camofox-browser (npm) 的服务器端
"""
import asyncio
import base64
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from camoufox.sync_api import Camoufox, NewBrowser
from playwright.sync_api import sync_playwright

_executor = ThreadPoolExecutor(max_workers=1)

# Default camofox profile directory
DEFAULT_CAMOFOX_DIR = Path.home() / ".camofox"
DEFAULT_PROFILES_DIR = DEFAULT_CAMOFOX_DIR / "profiles"
DEFAULT_COOKIES_DIR = DEFAULT_CAMOFOX_DIR / "cookies"


class BrowserServer:
    def __init__(self, port: int = 9377, headless: bool = False, user_data_dir: str | None = None):
        self.port = port
        self.headless = headless
        # Default to ~/.camofox/profiles/default
        if user_data_dir:
            self.user_data_dir = user_data_dir
        else:
            self.user_data_dir = str(DEFAULT_PROFILES_DIR / "default")
        self.browser = None
        self.context = None
        self.playwright = None
        self.pages: dict[str, Any] = {}
        self.active_tab_id: str | None = None

    def _import_cookies_from_file(self, context, domain: str):
        """Import cookies from ~/.camofox/cookies/<domain>.json"""
        cookie_file = DEFAULT_COOKIES_DIR / f"{domain}.json"
        if cookie_file.exists():
            try:
                cookies = json.loads(cookie_file.read_text())
                if cookies:
                    context.add_cookies(cookies)
                    return True
            except Exception:
                pass
        return False

    def _export_cookies_to_file(self, context, domain: str):
        """Export cookies to ~/.camofox/cookies/<domain>.json"""
        try:
            cookies = context.cookies()
            if cookies:
                DEFAULT_COOKIES_DIR.mkdir(parents=True, exist_ok=True)
                cookie_file = DEFAULT_COOKIES_DIR / f"{domain}.json"
                cookie_file.write_text(json.dumps(cookies, indent=2))
                return True
        except Exception:
            pass
        return False

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove port
        if ':' in domain:
            domain = domain.split(':')[0]
        # Remove www.
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def launch_browser(self) -> dict:
        """Launch the camoufox browser (sync)"""
        if self.browser:
            return {"status": "already_running", "pages": list(self.pages.keys())}

        import platform
        system = platform.system().lower()
        if system == "darwin":
            os_type = "macos"
        elif system == "linux":
            os_type = "linux"
        else:
            os_type = "windows"

        # Ensure profile directory exists
        if self.user_data_dir:
            os.makedirs(self.user_data_dir, exist_ok=True)

        # Use persistent context if user_data_dir specified
        if self.user_data_dir:
            self.playwright = sync_playwright().__enter__()
            self.browser = NewBrowser(
                self.playwright,
                headless=self.headless,
                os=os_type,
                persistent_context=True,
                user_data_dir=self.user_data_dir
            )
            # For persistent context, the browser IS the context
            self.context = self.browser
            tab_id = "default"
            page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
            self.pages[tab_id] = page
            self.active_tab_id = tab_id
        else:
            kwargs = {"headless": self.headless, "os": os_type}
            self.browser = Camoufox(**kwargs)
            self.context = self.browser.__enter__()
            tab_id = str(uuid.uuid4())[:8]
            page = self.context.new_page()
            self.pages[tab_id] = page
            self.active_tab_id = tab_id

        return {
            "status": "launched",
            "tabId": self.active_tab_id,
            "headless": self.headless,
            "userDataDir": self.user_data_dir,
        }

    def close_browser(self) -> dict:
        """Close the browser and export cookies"""
        if self.browser:
            # Export cookies before closing
            if self.context and hasattr(self.context, 'cookies'):
                try:
                    cookies = self.context.cookies()
                    # Group cookies by domain and export
                    domains = set()
                    for c in cookies:
                        domain = c.get('domain', '')
                        # Remove leading dot
                        if domain.startswith('.'):
                            domain = domain[1:]
                        # Extract main domain
                        parts = domain.split('.')
                        if len(parts) >= 2:
                            main_domain = '.'.join(parts[-2:])
                        else:
                            main_domain = domain
                        domains.add(main_domain)

                    for domain in domains:
                        self._export_cookies_to_file(self.context, domain)
                except Exception:
                    pass

            self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.browser = None
            self.context = None
            self.playwright = None
            self.pages.clear()
            self.active_tab_id = None
        return {"status": "closed"}

    def get_page(self, tab_id: str | None = None) -> Any:
        """Get page by tab_id or return active tab"""
        if not self.browser:
            raise HTTPException(status_code=400, detail="Browser not running")
        tid = tab_id or self.active_tab_id
        if tid not in self.pages:
            raise HTTPException(status_code=404, detail=f"Tab {tid} not found")
        return self.pages[tid]

    def open_url(self, url: str, tab_id: str | None = None) -> dict:
        """Open URL in a new tab"""
        if not self.browser:
            self.launch_browser()

        # Import cookies for this domain before opening
        domain = self._get_domain_from_url(url)
        self._import_cookies_from_file(self.context, domain)

        new_tab_id = str(uuid.uuid4())[:8]
        page = self.context.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_load_state("load")
        self.pages[new_tab_id] = page
        self.active_tab_id = new_tab_id

        return {"tabId": new_tab_id, "url": page.url}

    def close_tab(self, tab_id: str | None = None) -> dict:
        """Close a tab"""
        tid = tab_id or self.active_tab_id
        if tid not in self.pages:
            raise HTTPException(status_code=404, detail=f"Tab {tid} not found")

        # For persistent context, closing last tab is not allowed
        if self.user_data_dir and len(self.pages) == 1:
            return {"error": "Cannot close last tab in persistent context"}

        self.pages[tid].close()
        del self.pages[tid]

        if self.active_tab_id == tid:
            self.active_tab_id = list(self.pages.keys())[0] if self.pages else None

        return {"status": "closed", "tabId": tid}

    def screenshot(self, tab_id: str | None = None, full_page: bool = False, path: str | None = None) -> dict:
        """Take screenshot"""
        page = self.get_page(tab_id)
        if path:
            page.screenshot(path=path, full_page=full_page)
            return {"path": path}
        else:
            data = page.screenshot(full_page=full_page)
            return {"screenshot_base64": base64.b64encode(data).decode()}

    def get_text(self, tab_id: str | None = None) -> dict:
        """Get page text content"""
        page = self.get_page(tab_id)
        return {"text": page.inner_text("body")}

    def get_links(self, tab_id: str | None = None) -> dict:
        """Get all links on page"""
        page = self.get_page(tab_id)
        try:
            links = page.eval_on_all_elements(
                "a[href]",
                "els => els.map(el => ({href: el.href, text: el.textContent.trim()}))"
            )
        except Exception:
            # Fallback for complex SPA pages where eval_on_all_elements fails
            links = page.evaluate("""
                () => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(el => {
                        const href = el.href;
                        // Filter out empty anchors and javascript links
                        if (href && !href.startsWith('javascript:') && href !== '#') {
                            links.push({
                                href: href,
                                text: (el.textContent || '').trim()
                            });
                        }
                    });
                    return links;
                }
            """)
        return {"links": links}

    def get_url(self, tab_id: str | None = None) -> dict:
        """Get current URL"""
        page = self.get_page(tab_id)
        return {"url": page.url}

    def get_title(self, tab_id: str | None = None) -> dict:
        """Get page title"""
        page = self.get_page(tab_id)
        return {"title": page.title}

    def click(self, selector: str, tab_id: str | None = None) -> dict:
        """Click element"""
        page = self.get_page(tab_id)
        page.click(selector)
        return {"status": "clicked", "selector": selector}

    def type_text(self, selector: str, text: str, tab_id: str | None = None) -> dict:
        """Type text into element"""
        page = self.get_page(tab_id)
        page.type(selector, text)
        return {"status": "typed", "selector": selector, "text": text}

    def eval_js(self, expression: str, tab_id: str | None = None) -> dict:
        """Evaluate JavaScript"""
        page = self.get_page(tab_id)
        result = page.eval_on_selector("body", expression)
        return {"result": result}

    def scroll(self, direction: str = "down", amount: int = 1, tab_id: str | None = None) -> dict:
        """Scroll page"""
        page = self.get_page(tab_id)
        import time
        for _ in range(amount):
            if direction == "down":
                page.keyboard.press("End")
            else:
                page.keyboard.press("Home")
            time.sleep(0.5)
        return {"status": "scrolled", "direction": direction, "amount": amount}

    def navigate(self, url: str, tab_id: str | None = None) -> dict:
        """Navigate to URL"""
        page = self.get_page(tab_id)
        page.goto(url, timeout=30000)
        return {"url": page.url, "title": page.title}

    def go_back(self, tab_id: str | None = None) -> dict:
        """Go back in history"""
        page = self.get_page(tab_id)
        page.go_back()
        return {"url": page.url}

    def go_forward(self, tab_id: str | None = None) -> dict:
        """Go forward in history"""
        page = self.get_page(tab_id)
        page.go_forward()
        return {"url": page.url}

    def get_tabs(self) -> dict:
        """Get list of all tabs"""
        return {
            "tabs": [{"id": tid, "url": self.pages[tid].url if hasattr(self.pages[tid], 'url') else ""} for tid in self.pages],
            "active": self.active_tab_id
        }

    def get_cookies(self, tab_id: str | None = None) -> dict:
        """Get cookies for current context"""
        page = self.get_page(tab_id)
        try:
            cookies = self.context.cookies()
            return {"cookies": cookies}
        except Exception as e:
            return {"error": str(e)}

    def set_cookies(self, cookies: list, tab_id: str | None = None) -> dict:
        """Set cookies for current context"""
        page = self.get_page(tab_id)
        try:
            self.context.add_cookies(cookies)
            return {"status": "ok", "count": len(cookies)}
        except Exception as e:
            return {"error": str(e)}

    def get_console(self, tab_id: str | None = None) -> dict:
        """Get console logs from page"""
        page = self.get_page(tab_id)
        try:
            logs = page.evaluate("""
                () => {
                    return window._pycamofox_logs || [];
                }
            """)
            return {"logs": logs}
        except Exception as e:
            return {"logs": [], "error": str(e)}

    def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 30000, tab_id: str | None = None) -> dict:
        """Wait for selector to appear or disappear"""
        page = self.get_page(tab_id)
        try:
            if state == "hidden":
                page.wait_for_selector(selector, state="hidden", timeout=timeout)
            else:
                page.wait_for_selector(selector, state="attached", timeout=timeout)
            return {"status": "found", "selector": selector}
        except Exception as e:
            return {"status": "not_found", "selector": selector, "error": str(e)}

    def wait_for_url(self, pattern: str, timeout: int = 30000, tab_id: str | None = None) -> dict:
        """Wait for URL pattern"""
        page = self.get_page(tab_id)
        try:
            page.wait_for_url(pattern, timeout=timeout)
            return {"status": "matched", "url": page.url}
        except Exception as e:
            return {"status": "timeout", "error": str(e)}

    def press_key(self, key: str, tab_id: str | None = None) -> dict:
        """Press a keyboard key"""
        page = self.get_page(tab_id)
        page.keyboard.press(key)
        return {"status": "pressed", "key": key}

    def hover(self, selector: str, tab_id: str | None = None) -> dict:
        """Hover over element"""
        page = self.get_page(tab_id)
        page.hover(selector)
        return {"status": "hovered", "selector": selector}

    def select_option(self, selector: str, value: str, tab_id: str | None = None) -> dict:
        """Select option in dropdown"""
        page = self.get_page(tab_id)
        page.select_option(selector, value)
        return {"status": "selected", "selector": selector, "value": value}

    def get_page_info(self, tab_id: str | None = None) -> dict:
        """Get detailed page info"""
        page = self.get_page(tab_id)
        return {
            "url": page.url,
            "title": page.title,
            "viewport": page.viewport_size,
            "content": page.content()[:500] if page.content() else ""
        }

    def fill_input(self, selector: str, text: str, tab_id: str | None = None) -> dict:
        """Fill a framework-managed input (React controlled, Vue v-model).

        Unlike type() which uses Input.insertText bypass, this helper:
        - Focuses the element
        - Clears it
        - Types via real key events
        - Fires synthetic input+change events so framework sees the update
        """
        page = self.get_page(tab_id)
        # Focus
        page.evaluate(f"document.querySelector({repr(selector)})?.focus()")
        # Clear
        page.evaluate(f"document.querySelector({repr(selector)}).value = ''")
        # Type with keyboard
        page.evaluate(f"""
            (el => {{
                el.focus();
                el.value = '';
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
            }})(document.querySelector({repr(selector)}))
        """)
        page.keyboard.type(text)
        # Fire change event
        page.evaluate(f"""
            document.querySelector({repr(selector)}).dispatchEvent(new Event('change', {{bubbles: true}}))
        """)
        return {"status": "filled", "selector": selector, "text": text}

    def wait_for_network_idle(self, timeout: int = 10000, tab_id: str | None = None) -> dict:
        """Wait for network to be idle"""
        page = self.get_page(tab_id)
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
            return {"status": "idle"}
        except Exception as e:
            return {"status": "timeout", "error": str(e)}

    def http_get(self, url: str, headers: dict | None = None, timeout: int = 20) -> dict:
        """Pure HTTP — no browser. Use for static pages / APIs."""
        import urllib.request
        import gzip
        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        if headers:
            h.update(headers)
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return {"status": "ok", "content": data.decode("utf-8", errors="replace")}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def health_check(self) -> dict:
        """Health check"""
        return {
            "ok": True,
            "server": {"running": True, "port": self.port},
            "browser": {
                "running": self.browser is not None,
                "tabCount": len(self.pages),
            }
        }


# Global server instance
server = BrowserServer()


# FastAPI app
app = FastAPI(title="pycamofox-server")


class OpenRequest(BaseModel):
    url: str
    tabId: str | None = None


class ClickRequest(BaseModel):
    selector: str
    tabId: str | None = None


class TypeRequest(BaseModel):
    selector: str
    text: str
    tabId: str | None = None


class EvalRequest(BaseModel):
    expression: str
    tabId: str | None = None


class ScrollRequest(BaseModel):
    direction: str = "down"
    amount: int = 1
    tabId: str | None = None


class NavigateRequest(BaseModel):
    url: str
    tabId: str | None = None


class FillRequest(BaseModel):
    selector: str
    text: str
    tabId: str | None = None


class NetworkIdleRequest(BaseModel):
    timeout: int = 10000
    tabId: str | None = None


class HttpGetRequest(BaseModel):
    url: str
    headers: dict | None = None
    timeout: int = 20


class ScreenshotRequest(BaseModel):
    path: str | None = None
    fullPage: bool = False
    tabId: str | None = None


def run_sync(func, *args):
    """Run a sync function in a thread pool"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_in_executor(_executor, func, *args)
    finally:
        pass


@app.get("/health")
async def health():
    # Run sync health_check in executor
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.health_check)


@app.post("/browser/launch")
async def launch_browser():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.launch_browser)


@app.post("/browser/close")
async def close_browser():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.close_browser)


@app.post("/tabs/open")
async def open_tab(req: OpenRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.open_url, req.url, req.tabId)


@app.post("/tabs/close")
async def close_tab(tabId: str | None = None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.close_tab, tabId)


@app.post("/tabs/screenshot")
async def screenshot(req: ScreenshotRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.screenshot, req.tabId, req.fullPage, req.path)


@app.get("/tabs/get-url")
async def get_url(tabId: str | None = None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.get_url, tabId)


@app.get("/tabs/get-text")
async def get_text(tabId: str | None = None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.get_text, tabId)


@app.get("/tabs/get-links")
async def get_links(tabId: str | None = None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.get_links, tabId)


@app.get("/tabs/get-title")
async def get_title(tabId: str | None = None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.get_title, tabId)


@app.post("/tabs/click")
async def click(req: ClickRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.click, req.selector, req.tabId)


@app.post("/tabs/type")
async def type_text(req: TypeRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.type_text, req.selector, req.text, req.tabId)


@app.post("/tabs/eval")
async def eval_js(req: EvalRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.eval_js, req.expression, req.tabId)


@app.post("/tabs/scroll")
async def scroll(req: ScrollRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.scroll, req.direction, req.amount, req.tabId)


@app.post("/tabs/navigate")
async def navigate(req: NavigateRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.navigate, req.url, req.tabId)


@app.post("/tabs/fill")
async def fill(req: FillRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.fill_input, req.selector, req.text, req.tabId)


@app.post("/tabs/wait-network-idle")
async def wait_network_idle(req: NetworkIdleRequest):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.wait_for_network_idle, req.timeout, req.tabId)


@app.get("/http/get")
async def http_get(url: str, headers: dict | None = None, timeout: int = 20):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.http_get, url, headers, timeout)


@app.post("/tabs/go-back")
async def go_back(tabId: str | None = None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.go_back, tabId)


@app.post("/tabs/go-forward")
async def go_forward(tabId: str | None = None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, server.go_forward, tabId)


@app.post("/shutdown")
async def shutdown():
    """Shutdown server and browser"""
    import os
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, server.close_browser)
    # Exit the process
    os._exit(0)
    return result


def run_server(port: int = 9377, headless: bool = False, background: bool = False, user_data_dir: str | None = None):
    """Run the server"""
    # Update global server instance
    server.port = port
    server.headless = headless
    server.user_data_dir = user_data_dir

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    _server = uvicorn.Server(config)

    if background:
        import threading
        thread = threading.Thread(target=_server.run, daemon=True)
        thread.start()
        return {"status": "started", "port": port}
    else:
        _server.run()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="pycamofox-server")
    parser.add_argument("--port", type=int, default=9377)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--user-data-dir", type=str, default=None, help="Browser user data directory")
    args = parser.parse_args()

    run_server(args.port, args.headless, args.background, args.user_data_dir)
