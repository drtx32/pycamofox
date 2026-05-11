"""Skill registry for pycamofox runtime.

Skills are the ONLY way Agent interacts with the browser.
Each skill provides semantic actions (e.g., baidu.search)
that internally call runtime.execute() with proper commands.
"""
import asyncio
from typing import Any, Callable
from functools import wraps

class SkillRegistry:
    """Global registry of skills."""
    _skills: dict[str, "Skill"] = {}

    @classmethod
    def register(cls, name: str, skill_instance: "Skill") -> None:
        cls._skills[name] = skill_instance

    @classmethod
    def get(cls, name: str) -> "Skill | None":
        return cls._skills.get(name)

    @classmethod
    def list_skills(cls) -> list[str]:
        return list(cls._skills.keys())


class Skill:
    """Base class for all skills."""
    name: str = ""
    description: str = ""

    def __init__(self, runtime: "PycamofoxRuntime | None = None"):
        self.runtime = runtime

    def set_runtime(self, runtime: "PycamofoxRuntime") -> None:
        self.runtime = runtime


class PycamofoxRuntime:
    """Runtime interface for skills — the ONLY way skills access the browser.

    Agent 不能直接调用这个类，而是通过 Skill 实例的方法。
    """
    def __init__(self, session_id: str, port: int = 9377):
        self.session_id = session_id
        self.port = port

    def _api(self, command: str, **kwargs) -> dict[str, Any]:
        import json, urllib.request
        url = f"http://127.0.0.1:{self.port}/sessions/{self.session_id}/execute"
        data = json.dumps({"command": command, "args": kwargs}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    def navigate(self, url: str) -> dict:
        return self._api("navigate", url=url)

    def click(self, selector: str) -> dict:
        return self._api("click", selector=selector)

    def type(self, selector: str, text: str) -> dict:
        return self._api("type", selector=selector, text=text)

    def fill(self, selector: str, text: str) -> dict:
        return self._api("fill", selector=selector, text=text)

    def get_text(self, selector: str = "body") -> dict:
        return self._api("get_text", selector=selector)

    def get_url(self) -> dict:
        return self._api("get_url")

    def get_title(self) -> dict:
        return self._api("get_title")

    def eval(self, expression: str, *args) -> dict:
        """Execute JS expression, optionally with arguments passed to the expression."""
        if args:
            import json
            args_json = json.dumps(args)
            expression = f"(function(){{ var args = {args_json}; return (function(){{ {expression} }}).apply(null, args); }})()"
        return self._api("eval", expression=expression)

    def scroll(self, direction: str = "down", amount: int = 1) -> dict:
        return self._api("scroll", direction=direction, amount=amount)

    def wait_network_idle(self, timeout: int = 10000) -> dict:
        return self._api("wait_network_idle", timeout=timeout)

    def screenshot(self) -> dict:
        return self._api("screenshot")


def skill(name: str):
    """Decorator to register a skill class."""
    def decorator(cls):
        cls.name = name
        SkillRegistry.register(name, cls)
        return cls
    return decorator