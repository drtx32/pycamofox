# Anti Patterns

> Claude Code 看到这些会显著减少"发散"。

## Browser 操作

### ❌ Agent directly calling Playwright

```python
# 禁止：Agent 直接导入并调用 Playwright
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://github.com")
    page.click("#submit-btn")
```

**为什么错误**：破坏 Browser Runtime 抽象，Agent 不应知道底层是 Playwright/Camoufox。

**正确方式**：
```python
runtime.execute("github.navigate", url="https://github.com")
runtime.execute("generic.click", selector="#submit-btn")
```

---

### ❌ Agent reading raw HTML/DOM

```python
# 禁止：读取原始 HTML
html = page.content()
dom = page.inner_html()
```

**为什么错误**：Token 爆炸、context 污染、hallucination。

**正确方式**：
```python
observation = runtime.observe()
# {"page_type": "github_home", "actions": [...], "content": {...}}
```

---

### ❌ Agent constructing URLs manually

```python
# 禁止：手动拼接 URL（缺少必要参数）
url = "https://github.com/search?q=camo"  # 缺少必要参数
page.goto(url)
```

**为什么错误**：网站 URL 包含隐式参数，手动构造可能触发反爬。

**正确方式**：
```python
runtime.execute("github.search", query="camo")
# Skill 内部处理 URL 构造
```

---

## State Management

### ❌ Skills storing global mutable state

```python
# 禁止：Skill 存储全局可变状态
_global_cache = {}

class GitHubSkill:
    def __init__(self):
        self.state = _global_cache  # 禁止！
```

**为什么错误**：多实例/并发时状态污染，难以测试。

**正确方式**：
```python
class GitHubSkill:
    def __init__(self, runtime):
        self.runtime = runtime  # 依赖注入
```

---

### ❌ Singleton pattern for Skills

```python
# 禁止：Skill 单例
class GitHubSkill:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

**为什么错误**：状态不可预测，难以重置。

**正确方式**：
```python
# Skill 由 SkillRegistry 管理生命周期
registry = SkillRegistry()
skill = registry.get("github.search_repo")
```

---

## Persona System

### ❌ Persona randomly changing mid-session

```python
# 禁止：运行时随机切换 Persona
persona = random.choice(PERSONAS)  # ❌
browser.update_fingerprint(persona)
```

**为什么错误**：Geo mismatch 会触发 soft ban。Persona 必须长期一致。

**正确方式**：
```python
# Persona 在 Session 创建时绑定，之后不变
session = runtime.create_session(persona_id="us-dev-1")
# session 生命周期内 persona_id 保持不变
```

---

### ❌ Separate proxy from Persona

```python
# 禁止：Proxy 独立于 Persona
browser.set_proxy("10.0.0.1:8080")
persona = {"locale": "en-US", "timezone": "America/New_York"}  # 与 proxy 不匹配
```

**为什么错误**：Proxy geo 与 Persona timezone/locale 不一致会触发检测。

**正确方式**：
```yaml
# persona.yaml
persona:
  id: us-east-1
  proxy:
    url: "http://proxy-us-east.example.com:8080"
    geo: "New York"
  locale: "en-US"
  timezone: "America/New_York"
```

---

## Event Bus

### ❌ Agent polling in a loop

```python
# 禁止：轮询等待状态变化
while True:
    if page.url == "https://example.com/done":
        break
    time.sleep(1)
```

**为什么错误**：浪费资源，可能触发反爬。

**正确方式**：
```python
# 订阅事件
@runtime.on("navigation")
def on_navigate(event):
    if event.url == "https://example.com/done":
        # 处理完成
        runtime.emit("task_complete", data={...})

# Agent 等待事件，而非轮询
runtime.wait_for("task_complete")
```

---

### ❌ Bypassing Event Bus for communication

```python
# 禁止：直接修改共享状态通信
shared_state["result"] = compute()

# 另一个 Agent 轮询 shared_state
while "result" not in shared_state:
    time.sleep(1)
```

**为什么错误**：破坏事件驱动架构，引入隐式依赖。

**正确方式**：
```python
# 通过 Event Bus
runtime.emit("result_ready", data={"result": compute()})

# 订阅者处理
@runtime.on("result_ready")
def handle_result(event):
    process(event.data["result"])
```

---

## Architecture

### ❌ Browser logic leaking into Planner

```python
# 禁止：Planner 直接调用 browser API
class Planner:
    def execute_task(self):
        page = self.browser.new_page()  # ❌
        page.goto(self.task.url)
        page.click(self.task.selector)
```

**为什么错误**：Planner 应专注于决策，不应知道 Browser 细节。

**正确方式**：
```python
class Planner:
    def execute_task(self):
        skill = self.registry.get(self.task.skill_name)
        result = skill.execute(**self.task.params)
```

---

### ❌ Creating abstractions prematurely

```python
# 禁止：为了"未来扩展"添加复杂抽象
class AbstractBrowserInterface:
    class BrowserImpl:
        class ChromiumStrategy:
            class LinuxStrategy:
                # 过度设计
```

**为什么错误**：YAGNI。Phase 1 不需要 Phase 3 的抽象。

**正确方式**：
```python
# 只为当前需求创建必要抽象
class BrowserRuntime:
    def __init__(self, browser: Camoufox):
        self.browser = browser
```

---

### ❌ Ignoring Non-goals

```python
# 禁止：试图做"万能系统"
class SuperSkill:
    def execute(self, task):
        # 试图处理所有类型的任务
        if "github" in task:
            ...
        elif "reddit" in task:
            ...
        elif "twitter" in task:
            ...
        # 这不是 Skill，这是 Agent
```

**为什么错误**：违反单一职责原则，破坏 Skill 可复用性。

**正确方式**：
```python
# 每个 Skill 专注一件事
class GitHubSearchSkill:
    name = "github.search"

class RedditExpandSkill:
    name = "reddit.expand"
```

---

## Testing

### ❌ Testing Skills with real Browser

```python
# 禁止：每个 test 都启动真实浏览器
def test_github_search():
    browser = launch_browser()  # 慢，不稳定
    page = browser.new_page()
    page.goto("https://github.com")
    # ...
```

**为什么错误**：测试变慢，不稳定，无法 CI。

**正确方式**：
```python
# Mock Runtime，使用 Fake Runtime
def test_github_search():
    fake_runtime = FakeRuntime()
    skill = GitHubSearchSkill(fake_runtime)
    result = skill.execute(query="test")
    assert "repositories" in result
```

---

### ❌ No test for Skill

```python
# 禁止：Skill 没有测试
class GitHubSearchSkill:
    def execute(self):
        # 手动测试后就交付
        pass
```

**为什么错误**：Skill 是核心抽象，必须有测试覆盖。

**正确方式**：
```python
# tests/test_skills/test_github.py
def test_search_repo_returns_repositories():
    runtime = FakeRuntime()
    skill = GitHubSearchSkill(runtime)
    result = skill.execute(query="camoufox", language="python")
    assert "repositories" in result
    assert len(result["repositories"]) > 0
```
