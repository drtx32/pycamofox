# Agent Rules

> 约束 Claude Code 行为的规则。文档即系统边界。

## 绝对禁止 (Forbidden)

### Browser Logic

- **禁止** Agent 直接操作 Playwright/Camoufox API
- **禁止** Agent 操作 CSS selector (`click("#btn")`, `type("input", "text")`)
- **禁止** Agent 读取 raw HTML/DOM (`page.content()`, `page.inner_html()`)
- **禁止** Agent 持有 browser session
- **禁止** browser logic 与 planner 耦合

### State Management

- **禁止** 新增隐式全局状态
- **禁止** 在 Skill 中存储可变状态
- **禁止** 绕过 Runtime Event Bus 进行通信

### Architecture

- **禁止** 新增直接耦合 Agent 和 Browser 的代码路径
- **禁止** 在 Skill 层直接实例化 Browser 对象
- **禁止** 绕过 Skill Runtime 执行 browser actions

## 必须遵守 (Required)

### 所有 Browser Interaction

- **必须** 通过 Runtime 接口
- **必须** 使用语义化 Actions（而非 DOM 操作）
- **必须** 通过 Event Bus 订阅 browser events

### 所有 Site Workflow

- **必须** 封装为 Skill
- **必须** 可复用、可测试
- **必须** 存储在 `src/pycamofox/skills/` 目录

### 所有 Observation

- **必须** 经过 Semantic Extraction 层
- **必须** 以 JSON 格式返回（而非 raw HTML）
- **必须** 包含 `page_type` 字段

### 所有 Session

- **必须** 绑定 Persona
- **必须** 持久化到 `~/.camofox/sessions/`
- **必须** 支持跨会话恢复

### 所有 Proxy

- **必须** 绑定到特定 Persona
- **禁止** 在运行时动态切换 Proxy（破坏一致性）

## 架构优先级 (Architectural Priorities)

```
1. Runtime stability
2. Session persistence
3. Stealth consistency
4. Skill composability
5. Agent replaceability
```

**任何时候**，如果当前 task 与上述优先级冲突，**优先保证优先级高的**。

## 决策规则

### 当不确定时

- **优先** 遵循现有架构，而非"更快的解决方案"
- **优先** 新增 Skill，而非修改 Core Runtime
- **优先** 扩展 Event，而非修改 Event Handler

### 当被要求"快速修复"时

- "快速修复" 往往是 architecture erosion 的开始
- 先问：这个修复是否违反上述禁止条款？
- 如果违反，需要先讨论架构变更

### 当发现 abstraction erosion 时

如果发现代码开始出现：
- Agent 直接调 Playwright
- Skill 持有全局状态
- Event Handler 直接操作 DOM

**立即停下来**，在 PR/Commit 中标记这个问题。

## 反模式警告 (Anti-patterns)

### ❌ BAD: Agent directly calling Playwright

```python
# 禁止
from playwright.sync_api import sync_playwright
browser = sync_playwright().start().chromium.launch()
page = browser.new_page()
page.click("#submit")
```

### ❌ BAD: Skills storing global mutable state

```python
# 禁止
_global_state = {}

class GitHubSkill:
    def __init__(self):
        self.state = _global_state  # 禁止共享可变状态
```

### ❌ BAD: Persona randomly changing mid-session

```python
# 禁止
persona = random.choice(PERSONAS)  # 运行时随机切换
```

### ❌ BAD: Passing raw HTML to LLM

```python
# 禁止
content = page.content()  # raw HTML
llm.analyze(content)
```

## 正确示例

### ✓ GOOD: Semantic Action

```python
# 正确：通过 Runtime 执行语义化 action
result = runtime.execute("github.search_repo", query="camoufox", language="python")
# result = {"repositories": [...], "count": 42}
```

### ✓ GOOD: Skill封装

```python
# src/pycamofox/skills/github/search_repo.py
class SearchRepoSkill:
    name = "github.search_repo"

    def execute(self, query: str, language: str = None) -> dict:
        # 内部使用 runtime 接口，不暴露给 Agent
        runtime.navigate("https://github.com/search?q=" + query)
        runtime.wait_for("network_idle")
        observation = runtime.observe()
        return self._extract_repos(observation)
```

### ✓ GOOD: Semantic Observation

```python
# 正确：获取压缩后的语义状态
observation = runtime.observe()
# observation = {
#   "page_type": "github_search_results",
#   "actions": ["star", "fork", "filter"],
#   "repositories": [...],
#   "pagination": {"has_next": true, "current_page": 1}
# }
```

---

**任何 Claude Code 操作前**，先检查是否违反上述规则。
