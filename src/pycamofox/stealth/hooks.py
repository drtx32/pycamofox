"""Load stealth JS hook templates from the hooks/ directory."""
from __future__ import annotations

import os


def _read_hook(filename: str) -> str:
    """Read a JS hook file from the stealth/ directory."""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _render_template(template_name: str, **kwargs) -> str:
    """Render a JS template with placeholder substitution."""
    template = _read_hook(template_name)
    js = template
    for key, value in kwargs.items():
        placeholder = "{{" + key + "}}"
        if isinstance(value, bool):
            js = js.replace(placeholder, "true" if value else "false")
        else:
            js = js.replace(placeholder, str(value))
    return js


# ====================== Individual hook loaders ======================

def get_font_fallback_script() -> str:
    """CJK font fallback for cross-OS fingerprinting."""
    return _read_hook("font_fallback.js")


def get_debugger_trap_script() -> str:
    """Bypass debugger detection."""
    return _read_hook("debugger_trap.js")


def get_runtime_probe_script() -> str:
    """Runtime probe detection."""
    return _read_hook("runtime_probe.js")


def get_property_access_hook_script() -> str:
    """DOM property access hook."""
    return _read_hook("property_access_hook.js")


def get_jsvmp_hook_script() -> str:
    """JSVMP bytecode obfuscation bypass."""
    return _read_hook("jsvmp_hook.js")


def get_jsvmp_transparent_hook_script() -> str:
    """JSVMP transparent hook."""
    return _read_hook("jsvmp_transparent_hook.js")


def get_fetch_hook_script() -> str:
    """Fetch API hook."""
    return _read_hook("fetch_hook.js")


def get_xhr_hook_script() -> str:
    """XMLHttpRequest hook."""
    return _read_hook("xhr_hook.js")


def get_websocket_hook_script() -> str:
    """WebSocket hook."""
    return _read_hook("websocket_hook.js")


def get_cookie_hook_script() -> str:
    """Cookie hook."""
    return _read_hook("cookie_hook.js")


def get_crypto_hook_script() -> str:
    """Crypto API hook."""
    return _read_hook("crypto_hook.js")


# ====================== Trace templates ======================

def render_trace_template(
    function_path: str,
    max_captures: int = 50,
    log_args: bool = True,
    log_return: bool = True,
    log_stack: bool = False,
) -> str:
    """Render the trace_template.js with the given parameters."""
    return _render_template(
        "trace_template.js",
        FUNCTION_PATH=function_path,
        MAX_CAPTURES=max_captures,
        LOG_ARGS=log_args,
        LOG_RETURN=log_return,
        LOG_STACK=log_stack,
    )


def render_persistent_trace_template(
    function_path: str,
    max_captures: int = 50,
    log_args: bool = True,
    log_return: bool = True,
    log_stack: bool = False,
) -> str:
    """Render the persistent trace template that emits data via console.log."""
    return _render_template(
        "trace_persistent_template.js",
        FUNCTION_PATH=function_path,
        MAX_CAPTURES=max_captures,
        LOG_ARGS=log_args,
        LOG_RETURN=log_return,
        LOG_STACK=log_stack,
    )


# ====================== Built-in stealth presets ======================

def get_stealth_script(mode: str = "default") -> str:
    """Get a combined stealth script preset.

    Args:
        mode: "default" (basic), "maximum" (all hooks), "compatible" (tested hooks)
    """
    if mode == "maximum":
        return "\n".join([
            get_debugger_trap_script(),
            get_runtime_probe_script(),
            get_property_access_hook_script(),
            get_fetch_hook_script(),
            get_xhr_hook_script(),
            get_websocket_hook_script(),
            get_cookie_hook_script(),
            get_crypto_hook_script(),
        ])
    elif mode == "compatible":
        # Hooks known to work reliably without breaking sites
        return "\n".join([
            get_debugger_trap_script(),
            get_property_access_hook_script(),
            get_fetch_hook_script(),
        ])
    else:
        # default - basic anti-detection
        return "\n".join([
            get_debugger_trap_script(),
            get_runtime_probe_script(),
        ])
