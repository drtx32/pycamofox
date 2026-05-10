"""
pycamofox - CLI client for pycamofox-server
复刻 camofox-browser (npm) 的CLI端 - 命令即服务模式
"""
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_PORT = 9377
BASE_URL = f"http://127.0.0.1:{DEFAULT_PORT}"

# Default profile directory - matches camofox-browser convention
DEFAULT_PROFILE_DIR = Path.home() / ".camofox" / "profiles"

# Server process handle
_server_process = None
_pid_file = None

# Global user data dir for auto-started servers
_user_data_dir = None


def get_pid_file(port: int) -> Path:
    """Get PID file path for a port"""
    return Path(tempfile.gettempdir()) / f"pycamofox_{port}.pid"


def is_server_running(port: int) -> bool:
    """Check if server is running on port"""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except:
        return False


def start_server_in_background(port: int, headless: bool = False, user_data_dir: str | None = None) -> bool:
    """Start server in background, return True if started"""
    global _server_process

    # Check if already running
    if is_server_running(port):
        return False  # Already running

    # Get the python executable
    python_exe = sys.executable
    server_module = "pycamofox.server"

    # Build command
    cmd = [python_exe, "-m", server_module, "--port", str(port)]
    if headless:
        cmd.append("--headless")
    if user_data_dir:
        cmd.extend(["--user-data-dir", str(user_data_dir)])

    # Use DETACHED_PROCESS to properly detach on Windows
    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        _server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED_PROCESS
        )
    else:
        # Unix-like: fork and let parent exit
        pid = os.fork()
        if pid == 0:
            os.setsid()  # Create new session
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            os._exit(0)

    # Wait for server to start (max 15 seconds)
    import time
    for _ in range(30):
        if is_server_running(port):
            return True
        time.sleep(0.5)

    return is_server_running(port)


def stop_server(port: int) -> bool:
    """Stop server on port"""
    import subprocess

    if sys.platform == "win32":
        # Windows: use netstat to find PID, then taskkill
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                if 'LISTENING' in line:
                    parts = line.split()
                    if parts:
                        pid = int(parts[-1])
                        subprocess.run(f'taskkill //F //PID {pid}',
                                     shell=True, capture_output=True)
                        return True
        except:
            pass
    else:
        # Unix: use PID file or kill by port
        pid_file = get_pid_file(port)
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                return True
            except:
                pass

    return False


def api_call(method: str, endpoint: str, data: dict | None = None, port: int = DEFAULT_PORT) -> dict:
    """Make API call to server"""
    url = f"http://127.0.0.1:{port}{endpoint}"

    req = urllib.request.Request(url, method=method)

    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e}"}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}"}


def ensure_server_running(port: int, headless: bool = False, user_data_dir: str | None = None) -> bool:
    """Ensure server is running, start if not"""
    if is_server_running(port):
        return True
    return start_server_in_background(port, headless, user_data_dir)


def cmd_launch(port: int, headless: bool = False) -> dict:
    ensure_server_running(port, headless)
    return api_call("POST", "/browser/launch", port=port)


def cmd_close(port: int) -> dict:
    return api_call("POST", "/browser/close", port=port)


def cmd_open(port: int, url: str, tab_id: str | None = None) -> dict:
    ensure_server_running(port)
    return api_call("POST", "/tabs/open", {"url": url, "tabId": tab_id}, port)


def cmd_close_tab(port: int, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/close", {"tabId": tab_id} if tab_id else {}, port)


def cmd_screenshot(port: int, path: str | None = None, full_page: bool = False, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/screenshot", {"path": path, "fullPage": full_page, "tabId": tab_id}, port)


def cmd_get_url(port: int, tab_id: str | None = None) -> dict:
    return api_call("GET", f"/tabs/get-url?tabId={tab_id}" if tab_id else "/tabs/get-url", port=port)


def cmd_get_text(port: int, tab_id: str | None = None) -> dict:
    return api_call("GET", f"/tabs/get-text?tabId={tab_id}" if tab_id else "/tabs/get-text", port=port)


def cmd_get_links(port: int, tab_id: str | None = None) -> dict:
    return api_call("GET", f"/tabs/get-links?tabId={tab_id}" if tab_id else "/tabs/get-links", port=port)


def cmd_get_title(port: int, tab_id: str | None = None) -> dict:
    return api_call("GET", f"/tabs/get-title?tabId={tab_id}" if tab_id else "/tabs/get-title", port=port)


def cmd_click(port: int, selector: str, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/click", {"selector": selector, "tabId": tab_id}, port)


def cmd_type(port: int, selector: str, text: str, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/type", {"selector": selector, "text": text, "tabId": tab_id}, port)


def cmd_eval(port: int, expression: str, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/eval", {"expression": expression, "tabId": tab_id}, port)


def cmd_scroll(port: int, direction: str = "down", amount: int = 1, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/scroll", {"direction": direction, "amount": amount, "tabId": tab_id}, port)


def cmd_navigate(port: int, url: str, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/navigate", {"url": url, "tabId": tab_id}, port)


def cmd_fill(port: int, selector: str, text: str, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/fill", {"selector": selector, "text": text, "tabId": tab_id}, port)


def cmd_wait_network_idle(port: int, timeout: int = 10000, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/wait-network-idle", {"timeout": timeout, "tabId": tab_id}, port)


def cmd_http_get(url: str, timeout: int = 20) -> dict:
    return api_call("GET", f"/http/get?url={urllib.parse.quote(url)}&timeout={timeout}", port=DEFAULT_PORT)


def cmd_go_back(port: int, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/go-back", {"tabId": tab_id} if tab_id else {}, port)


def cmd_go_forward(port: int, tab_id: str | None = None) -> dict:
    return api_call("POST", "/tabs/go-forward", {"tabId": tab_id} if tab_id else {}, port)


def cmd_health(port: int) -> dict:
    return api_call("GET", "/health", port=port)


def cmd_server_stop(port: int) -> dict:
    if stop_server(port):
        return {"status": "stopped", "port": port}
    return {"status": "stop_failed", "port": port}


def main():
    parser = argparse.ArgumentParser(prog="pycamofox", description="pycamofox browser CLI")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--user-data-dir", type=str, default=str(DEFAULT_PROFILE_DIR / "default"), help="Browser user data directory")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # launch
    p_launch = subparsers.add_parser("launch", help="Launch browser")
    p_launch.add_argument("--headless", action="store_true")

    # close
    subparsers.add_parser("close", help="Close browser")

    # open
    p_open = subparsers.add_parser("open", help="Open URL (new tab if browser running)")
    p_open.add_argument("url", help="URL to open")

    # new-tab
    p_newtab = subparsers.add_parser("new-tab", help="Open URL in new tab")
    p_newtab.add_argument("url", help="URL to open")

    # navigate
    p_nav = subparsers.add_parser("navigate", help="Navigate to URL")
    p_nav.add_argument("url", help="URL to navigate to")

    # screenshot
    p_shot = subparsers.add_parser("screenshot", help="Take screenshot")
    p_shot.add_argument("-o", "--output", help="Output file path")
    p_shot.add_argument("--full-page", action="store_true", help="Full page screenshot")

    # click
    p_click = subparsers.add_parser("click", help="Click element")
    p_click.add_argument("selector", help="CSS selector")

    # type
    p_type = subparsers.add_parser("type", help="Type text")
    p_type.add_argument("selector", help="CSS selector")
    p_type.add_argument("text", help="Text to type")

    # fill (framework-managed input)
    p_fill = subparsers.add_parser("fill", help="Fill framework-managed input (React/Vue)")
    p_fill.add_argument("selector", help="CSS selector")
    p_fill.add_argument("text", help="Text to type")

    # wait-network-idle
    p_wni = subparsers.add_parser("wait-network-idle", help="Wait for network idle")
    p_wni.add_argument("--timeout", type=int, default=10000, help="Timeout in ms")

    # http-get
    p_http = subparsers.add_parser("http-get", help="HTTP GET (no browser)")
    p_http.add_argument("url", help="URL to fetch")
    p_http.add_argument("--timeout", type=int, default=20, help="Timeout in seconds")

    # eval
    p_eval = subparsers.add_parser("eval", help="Evaluate JavaScript")
    p_eval.add_argument("expression", help="JavaScript expression")

    # scroll
    p_scroll = subparsers.add_parser("scroll", help="Scroll page")
    p_scroll.add_argument("direction", nargs="?", choices=["up", "down"], default="down")
    p_scroll.add_argument("amount", nargs="?", type=int, default=1)

    # go-back
    subparsers.add_parser("go-back", help="Go back")

    # go-forward
    subparsers.add_parser("go-forward", help="Go forward")

    # get-text
    subparsers.add_parser("get-text", help="Get page text")

    # get-links
    subparsers.add_parser("get-links", help="Get all links")

    # get-url
    subparsers.add_parser("get-url", help="Get current URL")

    # health
    subparsers.add_parser("health", help="Health check")

    # close-tab
    subparsers.add_parser("close-tab", help="Close tab")

    # shutdown
    subparsers.add_parser("shutdown", help="Shutdown server")

    # server
    p_server = subparsers.add_parser("server", help="Server management")
    p_server_sub = p_server.add_subparsers(dest="server_command", help="Server commands")
    p_start = p_server_sub.add_parser("start", help="Start server (auto-started on first command)")
    p_start.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_start.add_argument("--headless", action="store_true")
    p_stop = p_server_sub.add_parser("stop", help="Stop server")
    p_stop.add_argument("--port", type=int, default=DEFAULT_PORT)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    port = args.port
    global _user_data_dir
    _user_data_dir = args.user_data_dir
    result = None

    if args.command == "server":
        if not args.server_command:
            p_server.print_help()
            return
        if args.server_command == "start":
            from .server import run_server
            ensure_server_running(args.port, args.headless, args.user_data_dir)
            result = {"status": "server_started_or_running", "port": args.port}
        elif args.server_command == "stop":
            result = cmd_server_stop(args.port)
    elif args.command == "launch":
        ensure_server_running(port, args.headless, _user_data_dir)
        result = cmd_launch(port, args.headless)
    elif args.command == "open":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_open(port, args.url)
    elif args.command == "new-tab":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_open(port, args.url)
    elif args.command == "close-tab":
        result = cmd_close_tab(port)
    elif args.command == "close":
        result = cmd_close(port)
    elif args.command == "navigate":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_navigate(port, args.url)
    elif args.command == "screenshot":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_screenshot(port, args.output, args.full_page)
    elif args.command == "click":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_click(port, args.selector)
    elif args.command == "type":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_type(port, args.selector, args.text)
    elif args.command == "fill":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_fill(port, args.selector, args.text)
    elif args.command == "wait-network-idle":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_wait_network_idle(port, args.timeout)
    elif args.command == "http-get":
        result = cmd_http_get(args.url, args.timeout)
    elif args.command == "eval":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_eval(port, args.expression)
    elif args.command == "scroll":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_scroll(port, args.direction, args.amount)
    elif args.command == "go-back":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_go_back(port)
    elif args.command == "go-forward":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_go_forward(port)
    elif args.command == "get-text":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_get_text(port)
    elif args.command == "get-links":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_get_links(port)
    elif args.command == "get-url":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_get_url(port)
    elif args.command == "health":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_health(port)
    elif args.command == "shutdown":
        result = cmd_server_stop(port)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

    if result:
        output = json.dumps(result, indent=2, ensure_ascii=False)
        try:
            print(output)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(output.encode('utf-8') + b'\n')


if __name__ == "__main__":
    main()
