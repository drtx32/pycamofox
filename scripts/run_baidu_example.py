#!/usr/bin/env python
"""运行 GitHub 搜索示例 — 演示 pycamofox skill 系统。

这个脚本展示：
1. 如何启动 daemon
2. 如何创建 session
3. 如何使用 GitHubSearchSkill 进行语义化仓库搜索
4. 如何获取结构化结果
"""
import sys
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, "src")

from pycamofox.skills import PycamofoxRuntime, SkillRegistry
from pycamofox.skills.baidu import GitHubSearchSkill, BaiduSearchSkill
from pycamofox.skills.registry import skill


def check_server(port=9377):
    """检查 server 是否运行。"""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except:
        return False


def wait_server(port=9377, timeout=30):
    """等待 server 启动。"""
    start = time.time()
    while time.time() - start < timeout:
        if check_server(port):
            return True
        time.sleep(1)
    return False


def api_call(method, endpoint, data=None, port=9377):
    """Make API call to server."""
    url = f"http://127.0.0.1:{port}{endpoint}"
    req = urllib.request.Request(url, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"error": str(e)}


def start_daemon(port=9377, headless=True):
    """启动 daemon。"""
    import subprocess
    import sys

    if check_server(port):
        print(f"[DAEMON] Server already running on port {port}")
        return True

    cmd = [sys.executable, "-m", "pycamofox", "daemon", "--port", str(port)]
    if headless:
        cmd.append("--headless")

    print(f"[DAEMON] Starting: {' '.join(cmd)}")

    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL, creationflags=DETACHED_PROCESS)
    else:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL, start_new_session=True)

    if wait_server(port):
        print(f"[DAEMON] Started successfully on port {port}")
        return True
    else:
        print(f"[DAEMON] Failed to start")
        return False


def main():
    print("=" * 60)
    print("pycamofox GitHub Search Skill Example")
    print("=" * 60)

    # 1. 启动 daemon
    print("\n[Step 1] Starting daemon...")
    if not start_daemon(headless=True):
        print("[ERROR] Failed to start daemon")
        return

    # 2. 创建 session
    print("\n[Step 2] Creating session...")
    resp = api_call("POST", "/sessions")
    if "error" in resp:
        print(f"[ERROR] {resp}")
        return
    session_id = resp["session_id"]
    print(f"[OK] Session created: {session_id}")

    # 3. 创建 runtime
    runtime = PycamofoxRuntime(session_id=session_id)

    # 4. 注册 GitHub Skill
    github = GitHubSearchSkill(runtime)
    print(f"[OK] GitHubSearchSkill registered: {github.name}")

    # 5. 搜索仓库
    print("\n[Step 3] Searching GitHub repos...")
    print('    Query: "stealth browser", Language: python')
    result = github.search_repo("stealth browser", language="python")
    print(f"[OK] Search completed: {result['title']}")
    print(f"    URL: {result['url']}")
    print(f"    Status: {result['status']}")

    # 6. 获取结构化结果
    if result.get('status') == 'ok':
        print("\n[Step 4] Extracting repo list...")
        repos = github.get_repos(max_count=5)
        print(f"[OK] Found {repos['count']} repos")
        for i, r in enumerate(repos["repos"][:5], 1):
            print(f"\n  {i}. {r['title']}")
            print(f"     Stars: {r.get('stars', 'N/A')} | Lang: {r.get('language', 'N/A')}")
            print(f"     {r['url']}")
            if r.get('description'):
                desc = r['description'][:100] + ('...' if len(r['description']) > 100 else '')
                print(f"     {desc}")

    # 7. 关闭 session
    print("\n[Step 5] Closing session...")
    resp = api_call("DELETE", f"/sessions/{session_id}")
    print(f"[OK] Session closed: {resp}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()