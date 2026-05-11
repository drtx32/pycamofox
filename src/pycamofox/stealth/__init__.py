"""Stealth hooks for pycamofox.

Integrates anti-detection hooks from camoufox-reverse:
https://github.com/drtx32/camoufox-reverse-mcp
"""
from .hooks import (
    get_font_fallback_script,
    get_debugger_trap_script,
    get_runtime_probe_script,
    get_property_access_hook_script,
    get_jsvmp_hook_script,
    get_jsvmp_transparent_hook_script,
    get_fetch_hook_script,
    get_xhr_hook_script,
    get_websocket_hook_script,
    get_cookie_hook_script,
    get_crypto_hook_script,
    render_trace_template,
    render_persistent_trace_template,
    get_stealth_script,
)

__all__ = [
    "get_font_fallback_script",
    "get_debugger_trap_script",
    "get_runtime_probe_script",
    "get_property_access_hook_script",
    "get_jsvmp_hook_script",
    "get_jsvmp_transparent_hook_script",
    "get_fetch_hook_script",
    "get_xhr_hook_script",
    "get_websocket_hook_script",
    "get_cookie_hook_script",
    "get_crypto_hook_script",
    "render_trace_template",
    "render_persistent_trace_template",
    "get_stealth_script",
]
