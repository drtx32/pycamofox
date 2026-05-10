# Principles

## 核心原则

### 1. Runtime-first

**Browser 是 Runtime Environment，不是工具。**

传统思维：
```
LLM → click/type/scroll → Browser (工具)
```

本项目：
```
LLM/Agents → Semantic Skills → Research Runtime → Stealth Browser Infrastructure → Real Internet
```

**意义**：Browser 不应被当作一次性工具调用，而应作为 AI 的持久化运行时环境。

### 2. Skill-native

**Agent 不直接操作 DOM，而是调用语义化 Actions。**

禁止：
```python
browser.click("#submit")
page.type("input[name=q]", "query")
```

必须：
```python
github.search_repo(query="...")
reddit.expand_thread(thread_id="...")
x.post(content="...")
```

**意义**：Skill 是可复用、可测试、可持久化的抽象单元。

### 3. Event-driven

**Runtime 推送 Events，Agent 订阅，而非持续 polling。**

Runtime 提供的事件：
- `navigation` — 页面导航完成
- `network_idle` — 网络空闲
- `mutation` — DOM 变化
- `popup` — 弹窗出现
- `captcha` — CAPTCHA 检测
- `download` — 下载触发
- `upload` — 上传触发
- `auth_required` — 需要认证
- `anti_bot_detected` — 反爬触发
- `session_degraded` — 会话质量下降
- `fingerprint_mismatch` — Fingerprint 不一致

**意义**：消除 polling 带来的资源浪费和风控问题。

### 4. Persona-consistent

**Digital Persona 不是随机 fingerprint，而是长期一致性身份。**

Persona 包含：
- Locale / Timezone
- GPU / Hardware
- Fonts (系统字体集)
- Browser history patterns
- Session age
- Proxy (ASN, geo)
- Extensions

**意义**：Geo mismatch 会直接导致 soft ban。真正的反检测靠的是一致性，而非随机性。

### 5. Semantic observation

**拒绝全 DOM 输入，采用语义化压缩状态。**

```
DOM (toxic)
  ↓
Accessibility Tree
  ↓
Semantic Extraction
  ↓
Compressed State (JSON)
  ↓
Agent Context
```

目标格式：
```json
{
  "page_type": "github_repo",
  "important_actions": ["star", "fork", "issues", "clone"],
  "main_content": {...},
  "navigation": {...}
}
```

**意义**：避免 token 爆炸、context 污染、hallucination。

### 6. Agent replaceable

**Agent 可以替换，Runtime 才是核心。**

支持的 Agent：
- Claude Code
- OpenAI Operator
- browser-use
- LangGraph
- CrewAI
- MCP clients
- Custom planners

**意义**：Runtime 的价值在于稳定、持久、不依赖特定 Agent 实现。

---

## 架构优先级

1. **Runtime stability** — 运行时稳定压倒一切
2. **Session persistence** — 会话持久化是核心价值
3. **Stealth consistency** — 反检测靠一致性而非随机
4. **Skill composability** — Skill 可组合、可复用
5. **Agent replaceability** — 不与特定 Agent 绑定

---

## 非目标

- 不追求"最快 demo"
- 不追求 benchmark 排名
- 不追求"一步完成"
- 不做单 Agent 万能系统
- 不做通用 Agent Framework
- 不做传统搜索引擎
- 不做简单 RPA

---

## 设计哲学

> **"让 AI 能长期在真实互联网中生存与工作。"**

这不是"让 AI 能操作浏览器"的另一个说法。这是完全不同的目标：
- 操作浏览器 = 一次性任务
- 互联网生存 = 长期、复杂、多站点、高风控

真正的难题不是 browser automation，而是 **Identity Consistency Problem**：
- TLS fingerprint
- HTTP/2 fingerprint
- WebRTC
- Timezone / Locale
- Proxy ASN
- Session age
- Mouse rhythm
- Browsing history
- Extension set
- Idle behavior

全部需要一致。
