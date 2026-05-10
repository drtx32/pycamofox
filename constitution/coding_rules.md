# Coding Rules

> 代码编写规范

## Python Style

### 遵循 PEP 8

- 4 空格缩进
- 行长度：88 字符（Black 默认）
- 单引号优先（除非字符串包含单引号）

### Type Hints

**必须** 为所有公开函数/方法添加 type hints：

```python
# ✓ 正确
def search_repo(query: str, language: str | None = None) -> dict[str, Any]:
    ...

# ✗ 错误
def search_repo(query, language=None):
    ...
```

### Docstrings

**必须** 为所有公开类、函数添加 docstring：

```python
class BrowserServer:
    """Browser daemon managing Camoufox instances.

    Attributes:
        port: Server port number.
        headless: Whether browser runs headless.
        user_data_dir: Browser profile directory.
    """

    def launch_browser(self) -> dict[str, Any]:
        """Launch the camoufox browser.

        Returns:
            Dict with status, tabId, headless, userDataDir.

        Raises:
            HTTPException: If browser already running.
        """
        ...
```

## Error Handling

### 异常类型

| 场景 | 异常类型 |
|------|----------|
| 预期内的错误 | `ValueError`, `KeyError` |
| 外部依赖错误 | `RuntimeError` |
| HTTP 相关 | `urllib.error.HTTPError` |
| Browser 操作失败 | `BrowserError` (自定义) |

### 异常处理原则

```python
# ✓ 正确：明确捕获、处理、重新抛出
try:
    page.goto(url, timeout=30000)
except TimeoutError as e:
    raise BrowserError(f"Navigation timeout: {url}") from e

# ✗ 错误： bare except
try:
    page.goto(url)
except:
    pass
```

## Naming

| 类型 | 规则 | 示例 |
|------|------|------|
| 类 | PascalCase | `BrowserServer`, `SkillRegistry` |
| 函数/方法 | snake_case | `launch_browser`, `get_text` |
| 常量 | UPPER_SNAKE | `DEFAULT_PORT`, `MAX_RETRIES` |
| 私有方法/属性 | `_leading_underscore` | `_export_cookies` |
| 类型变量 | PascalCase | `T`, `KT`, `VT` |

## Testing

### 测试文件位置

```
tests/
├── unit/
│   ├── test_cli.py
│   └── test_server.py
├── integration/
│   └── test_browser_flow.py
└── fixtures/
    └── mock_responses.py
```

### 测试原则

1. **单元测试**：每个函数独立可测试
2. **Mock 外部依赖**：不启动真实浏览器
3. **覆盖率**：核心模块 >80%
4. **快速**：单元测试 <100ms

### Fixture 示例

```python
@pytest.fixture
def fake_runtime():
    """提供 FakeRuntime 用于测试 Skills"""
    return FakeRuntime(
        pages={
            "default": FakePage(
                url="https://github.com",
                content={"page_type": "github_home"}
            )
        }
    )
```

## File Structure

### 模块组织

```
src/pycamofox/
├── __init__.py          # Package public API
├── __main__.py          # Entry point
├── cli.py               # CLI client
├── server.py            # Server (Phase 1)
├── browser/             # Phase 2+
│   ├── __init__.py
│   ├── daemon.py
│   ├── pool.py
│   └── ...
├── skills/              # Phase 2+
│   ├── __init__.py
│   ├── registry.py
│   ├── github/
│   └── ...
├── observation/         # Phase 2+
│   └── ...
└── api/                 # Phase 2+
    └── ...
```

### Import 顺序

```python
# 1. 标准库
import json
import os
from pathlib import Path

# 2. 第三方库
import fastapi
import uvicorn

# 3. 本项目
from pycamofox import BrowserServer
```

## Async

### 当前状态

**Phase 1**：Server 使用 async (FastAPI)，但 Browser 操作是 sync (ThreadPoolExecutor)。

### Phase 2 目标

- Browser 操作逐步迁移到 async
- 使用 `async with Camoufox()` API
- Event Bus 全面异步化

### Async 规则

```python
# ✓ 正确
async def handle_request():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, sync_function)

# ✗ 避免
async def handle_request():
    result = sync_function()  # 阻塞 event loop
    return result
```

## Logging

### 日志级别

| 级别 | 使用场景 |
|------|----------|
| DEBUG | 详细调试信息 |
| INFO | 重要操作（launch, close, navigate） |
| WARNING | 可恢复的错误 |
| ERROR | 操作失败 |

### 日志格式

```
2026-05-10 12:00:00 [INFO] pycamofox.server: Browser launched on port 9377
2026-05-10 12:00:01 [INFO] pycamofox.server: Tab opened: abc123, url=https://github.com
```

## Security

### 禁止

- 不在日志中打印 cookies、tokens、credentials
- 不在代码中硬编码 secrets
- 不将 user_data_dir 暴露给未授权方

### Cookie 处理

```python
# ✓ 正确：Cookie 存储在用户目录
cookie_file = Path.home() / ".camofox" / "cookies" / f"{domain}.json"

# ✗ 错误：Cookie 打印到日志
logger.info(f"Cookies: {cookies}")  # 禁止！
```
