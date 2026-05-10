"""
pycamofox - CLI client for pycamofox-daemon
Session-based browser automation CLI
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

# Default profile directory
DEFAULT_PROFILE_DIR = Path.home() / ".camofox" / "profiles"

# Server process handle
_server_process = None
_pid_file = None

# Global user data dir for auto-started servers
_user_data_dir = None

# Current session ID (for commands that need a session)
_current_session_id = None


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

    # Build command - use the new daemon module path
    cmd = [python_exe, "-m", "pycamofox", "daemon", "--port", str(port)]
    if headless:
        cmd.append("--headless")
    if user_data_dir:
        cmd.extend(["--storage-dir", str(user_data_dir)])

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


def ensure_session(port: int, headless: bool = False, user_data_dir: str | None = None) -> str | None:
    """Ensure a session exists, create one if not. Returns session_id."""
    global _current_session_id

    if _current_session_id:
        # Check if session still exists
        resp = api_call("GET", f"/sessions/{_current_session_id}", port=port)
        if "session_id" in resp:
            return _current_session_id

    # Create new session
    resp = api_call("POST", "/sessions", port=port)
    if "session_id" in resp:
        _current_session_id = resp["session_id"]
        return _current_session_id
    return None


def cmd_health(port: int) -> dict:
    return api_call("GET", "/health", port=port)


def cmd_server_stop(port: int) -> dict:
    if stop_server(port):
        return {"status": "stopped", "port": port}
    return {"status": "stop_failed", "port": port}


def cmd_session_create(port: int) -> dict:
    """Create a new session"""
    return api_call("POST", "/sessions", port=port)


def cmd_session_list(port: int) -> dict:
    """List all sessions"""
    return api_call("GET", "/sessions", port=port)


def cmd_session_get(port: int, session_id: str) -> dict:
    """Get session info"""
    return api_call("GET", f"/sessions/{session_id}", port=port)


def cmd_session_close(port: int, session_id: str) -> dict:
    """Close a session"""
    return api_call("DELETE", f"/sessions/{session_id}", port=port)


def cmd_execute(port: int, session_id: str, command: str, **kwargs) -> dict:
    """Execute a command in a session"""
    resp = api_call("POST", f"/sessions/{session_id}/execute",
                   {"command": command, "args": kwargs}, port=port)
    return resp


def cmd_navigate(port: int, url: str, session_id: str | None = None) -> dict:
    """Navigate to URL"""
    sid = session_id or ensure_session(port)
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "navigate", url=url)


def cmd_get_url(port: int, session_id: str | None = None) -> dict:
    """Get current URL"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "get_url")


def cmd_get_title(port: int, session_id: str | None = None) -> dict:
    """Get page title"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "get_title")


def cmd_click(port: int, selector: str, session_id: str | None = None) -> dict:
    """Click element"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "click", selector=selector)


def cmd_type(port: int, selector: str, text: str, session_id: str | None = None) -> dict:
    """Type text"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "type", selector=selector, text=text)


def cmd_fill(port: int, selector: str, text: str, session_id: str | None = None) -> dict:
    """Fill input"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "fill", selector=selector, text=text)


def cmd_screenshot(port: int, session_id: str | None = None) -> dict:
    """Take screenshot"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "screenshot")


def cmd_get_text(port: int, selector: str = "body", session_id: str | None = None) -> dict:
    """Get text content"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "get_text", selector=selector)


def cmd_eval(port: int, expression: str, session_id: str | None = None) -> dict:
    """Evaluate JavaScript"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "eval", expression=expression)


def cmd_scroll(port: int, direction: str = "down", amount: int = 1, session_id: str | None = None) -> dict:
    """Scroll page"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "scroll", direction=direction, amount=amount)


def cmd_wait_network_idle(port: int, timeout: int = 10000, session_id: str | None = None) -> dict:
    """Wait for network idle"""
    sid = session_id or _current_session_id
    if not sid:
        return {"error": "No session available"}
    return cmd_execute(port, sid, "wait_network_idle", timeout=timeout)


def main():
    parser = argparse.ArgumentParser(prog="pycamofox", description="pycamofox browser CLI")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--user-data-dir", type=str, default=str(DEFAULT_PROFILE_DIR / "default"), help="Browser user data directory")
    parser.add_argument("--session", type=str, default=None, help="Session ID to use")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # health
    subparsers.add_parser("health", help="Health check")

    # session commands
    p_session = subparsers.add_parser("session", help="Session management")
    p_session_sub = p_session.add_subparsers(dest="session_command", help="Session commands")
    p_session_create = p_session_sub.add_parser("create", help="Create new session")
    p_session_list = p_session_sub.add_parser("list", help="List sessions")
    p_session_info = p_session_sub.add_parser("info", help="Get session info")
    p_session_info.add_argument("session_id", help="Session ID")
    p_session_close = p_session_sub.add_parser("close", help="Close session")
    p_session_close.add_argument("session_id", nargs="?", help="Session ID (current if not specified)")

    # launch (creates session implicitly)
    p_launch = subparsers.add_parser("launch", help="Launch browser (creates session)")

    # open/navigate
    p_open = subparsers.add_parser("open", help="Open URL")
    p_open.add_argument("url", help="URL to open")

    p_nav = subparsers.add_parser("navigate", help="Navigate to URL")
    p_nav.add_argument("url", help="URL to navigate to")

    # screenshot
    p_shot = subparsers.add_parser("screenshot", help="Take screenshot")

    # click
    p_click = subparsers.add_parser("click", help="Click element")
    p_click.add_argument("selector", help="CSS selector")

    # type
    p_type = subparsers.add_parser("type", help="Type text")
    p_type.add_argument("selector", help="CSS selector")
    p_type.add_argument("text", help="Text to type")

    # fill
    p_fill = subparsers.add_parser("fill", help="Fill input")
    p_fill.add_argument("selector", help="CSS selector")
    p_fill.add_argument("text", help="Text to fill")

    # wait-network-idle
    p_wni = subparsers.add_parser("wait-network-idle", help="Wait for network idle")
    p_wni.add_argument("--timeout", type=int, default=10000, help="Timeout in ms")

    # eval
    p_eval = subparsers.add_parser("eval", help="Evaluate JavaScript")
    p_eval.add_argument("expression", help="JavaScript expression")

    # scroll
    p_scroll = subparsers.add_parser("scroll", help="Scroll page")
    p_scroll.add_argument("direction", nargs="?", choices=["up", "down"], default="down")
    p_scroll.add_argument("amount", nargs="?", type=int, default=1)

    # get-text
    p_get_text = subparsers.add_parser("get-text", help="Get page text")
    p_get_text.add_argument("selector", nargs="?", default="body", help="CSS selector")

    # get-url
    subparsers.add_parser("get-url", help="Get current URL")

    # get-title
    subparsers.add_parser("get-title", help="Get page title")

    # shutdown
    subparsers.add_parser("shutdown", help="Shutdown server")

    # server
    p_server = subparsers.add_parser("server", help="Server management")
    p_server_sub = p_server.add_subparsers(dest="server_command", help="Server commands")
    p_start = p_server_sub.add_parser("start", help="Start server")
    p_start.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_start.add_argument("--headless", action="store_true")
    p_stop = p_server_sub.add_parser("stop", help="Stop server")
    p_stop.add_argument("--port", type=int, default=DEFAULT_PORT)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    port = args.port
    global _user_data_dir, _current_session_id
    _user_data_dir = args.user_data_dir
    if args.session:
        _current_session_id = args.session
    result = None

    if args.command == "server":
        if not args.server_command:
            p_server.print_help()
            return
        if args.server_command == "start":
            ensure_server_running(args.port, args.headless, _user_data_dir)
            result = {"status": "server_started_or_running", "port": args.port}
        elif args.server_command == "stop":
            result = cmd_server_stop(args.port)
    elif args.command == "health":
        result = cmd_health(port)
    elif args.command == "session":
        if not args.session_command:
            p_session.print_help()
            return
        if args.session_command == "create":
            ensure_server_running(port, False, _user_data_dir)
            result = cmd_session_create(port)
            if "session_id" in result:
                _current_session_id = result["session_id"]
        elif args.session_command == "list":
            result = cmd_session_list(port)
        elif args.session_command == "info":
            result = cmd_session_get(port, args.session_id)
        elif args.session_command == "close":
            sid = args.session_id or _current_session_id
            if sid:
                result = cmd_session_close(port, sid)
                if _current_session_id == sid:
                    _current_session_id = None
            else:
                result = {"error": "No session specified"}
    elif args.command == "launch":
        ensure_server_running(port, args.headless, _user_data_dir)
        result = cmd_session_create(port)
        if "session_id" in result:
            _current_session_id = result["session_id"]
    elif args.command == "open" or args.command == "navigate":
        ensure_server_running(port, False, _user_data_dir)
        result = cmd_navigate(port, args.url)
    elif args.command == "screenshot":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_screenshot(port, sid)
    elif args.command == "click":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_click(port, args.selector, sid)
    elif args.command == "type":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_type(port, args.selector, args.text, sid)
    elif args.command == "fill":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_fill(port, args.selector, args.text, sid)
    elif args.command == "wait-network-idle":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_wait_network_idle(port, args.timeout, sid)
    elif args.command == "eval":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_eval(port, args.expression, sid)
    elif args.command == "scroll":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_scroll(port, args.direction, args.amount, sid)
    elif args.command == "get-text":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_get_text(port, args.selector, sid)
    elif args.command == "get-url":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_get_url(port, sid)
    elif args.command == "get-title":
        ensure_server_running(port, False, _user_data_dir)
        sid = _current_session_id or ensure_session(port)
        result = cmd_get_title(port, sid)
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
