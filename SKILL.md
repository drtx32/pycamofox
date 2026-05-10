---
name: pycamofox-skills
description: >
  pycamofox Skill System — how AI agents interact with websites
  using semantic actions instead of raw browser APIs.
  Skills encapsulate site-specific workflows, selectors, and
  observation patterns. Subagents should ONLY interact with
  the browser through skills.
version: 1.0.0
---

# pycamofox Skill System

pycamofox 是 **Stealth Browser Runtime Infrastructure for AI Agents**。
Skills 是 Agent 与网站交互的**唯一方式**。

## 核心原则

```
Agent → Skill.semantic_action() → Runtime.execute() → Browser
         ↓
    不操作 selector
    不读 raw HTML
    不直接调 Playwright
```

## Skill 结构

```
src/pycamofox/skills/
├── __init__.py       # SkillRegistry, PycamofoxRuntime, skill decorator
├── registry.py       # 运行时接口
└── baidu.py          # 百度搜索 skill
```

## PycamofoxRuntime

`PycamofoxRuntime` 是 Skill 访问浏览器的接口。每个 Skill 接收一个 runtime 实例。

```python
from pycamofox.skills import PycamofoxRuntime, SkillRegistry

# 创建 runtime
runtime = PycamofoxRuntime(session_id="abc123")

# 获取 skill
baidu = SkillRegistry.get("baidu.search")(runtime)

# 语义化操作
result = baidu.search("python")
results = baidu.get_results(max_results=10)
```

## Available Skills

### baidu.search

```python
baidu = BaiduSearchSkill(runtime)

# 搜索
baidu.search("关键词")

# 获取结构化结果
results = baidu.get_results(max_results=10)
# Returns: {"query": "", "results": [{"title": "", "url": "", "snippet": ""}], "count": N}

# 滚动加载更多
baidu.scroll_results(pages=2)

# 获取搜索建议
suggestions = baidu.get_suggestions()
```

### baidu.news

```python
baidu_news = BaiduNewsSkill(runtime)
baidu_news.navigate_news()
headlines = baidu_news.get_headlines(max_count=20)
```

## Skill 开发规则

1. **禁止** 在 Skill 内部操作 CSS selector — 使用 self.SELECTORS 常量
2. **禁止** 直接 import Playwright/Camoufox — 使用 PycamofoxRuntime
3. **必须** 返回语义化 JSON — 不返回 raw HTML
4. **必须** 使用 `wait_network_idle()` 等待页面加载
5. **必须** 捕获异常并返回错误状态

## SELECTORS 常量

每个 Skill 必须维护 SELECTORS 字典：

```python
class MySkill(Skill):
    SELECTORS = {
        "search_input": "#kw",
        "submit_button": "#su",
        "results": ".c-container",
    }
```

这样选择器集中管理，便于维护。

## 创建新 Skill

```python
from pycamofox.skills import skill, Skill, PycamofoxRuntime

@skill("mysite.action")
class MySiteSkill(Skill):
    name = "mysite.action"
    SELECTORS = {
        "input": "#search-input",
        "submit": "#submit-btn",
        "item": ".result-item",
    }

    def search(self, query: str) -> dict:
        self.runtime.fill(self.SELECTORS["input"], query)
        self.runtime.click(self.SELECTORS["submit"])
        self.runtime.wait_network_idle()
        return {"status": "ok", "url": self.runtime.get_url()["url"]}

    def get_items(self) -> dict:
        items = self.runtime.eval("""
            () => document.querySelectorAll('.result-item')
                .length
        """)
        return {"count": items}
```

## 验证

运行示例：
```bash
python scripts/run_baidu_example.py
```

输出应该显示：
- Daemon 启动成功
- Session 创建成功
- 百度搜索执行成功
- 5 条结构化结果返回
- Session 关闭成功