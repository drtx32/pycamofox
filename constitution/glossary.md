# Glossary

> 术语定义，避免歧义

---

## Core Concepts

### Browser Runtime

**定义**：一种基础设施，让 AI Agent 能在真实浏览器环境中执行长期任务。

**不是**：简单的浏览器自动化脚本或 Playwright wrapper。

**核心特征**：
- Persistent sessions
- Event-driven architecture
- Persona consistency
- Semantic observation

---

### Stealth

**定义**：绕过反爬检测的能力，包括 fingerprint spoofing、behavior simulation 等。

**实现层级**：
1. **Level 1**: 基本 fingerprint 随机化（随机 UA）
2. **Level 2**: 指纹一致性（geo/locale/timezone 匹配）
3. **Level 3**: 行为仿真（mouse rhythm、typing speed、idle behavior）
4. **Level 4**: 高级指纹管理（TLS、HTTP/2、Canvas、WebGL）

**Camoufox 提供**：Level 1-2 的内置支持

---

### Persona

**定义**：数字身份，包含硬件配置、地理位置、浏览器行为模式等，用于模拟真实用户。

**组成部分**：
- Hardware (GPU, memory, CPU)
- Locale / Timezone
- Fonts
- Proxy (ASN, geo)
- Browsing patterns
- Session age
- Extension set

**核心原则**：一致性 > 随机性。Geo mismatch 会触发 soft ban。

---

### Skill

**定义**：封装好的网站工作流，以语义化方式暴露给 Agent。

**类型**：

| 类型 | 说明 | 示例 |
|------|------|------|
| **Domain Skill** | 网站特化 | `github.search_repo`, `reddit.expand_thread` |
| **Workflow Skill** | 组合流程 | `search → filter → summarize → cite` |
| **Meta Skill** | Runtime 能力 | `captcha.solve`, `login.recover` |

**格式**：YAML 配置 + Python 实现

---

### Observation

**定义**：从 Browser 获取的语义化页面状态，而非 raw HTML/DOM。

**Pipeline**：
```
DOM → Accessibility Tree → Semantic Extraction → Compression → JSON
```

**目标格式**：
```json
{
  "page_type": "github_repo",
  "actions": ["star", "fork"],
  "content": {...}
}
```

---

### Event Bus

**定义**：Browser Runtime 与 Agent 之间的异步通信机制。

**Events**：
- `navigation` — 页面导航完成
- `network_idle` — 网络空闲
- `anti_bot_detected` — 反爬触发
- `captcha` — CAPTCHA 检测
- `session_degraded` — 会话质量下降

**对比**：
- **Polling**：Agent 循环检查状态（浪费资源，可能触发反爬）
- **Event Bus**：Runtime 推送事件（高效、低风控）

---

### Session

**定义**：Browser Instance + Persona + Proxy + State 的组合，代表一个独立的浏览上下文。

**生命周期**：
1. 创建：分配 Browser Instance，绑定 Persona
2. 活跃：执行操作，状态变化
3. 持久化：导出 cookies，保存 state
4. 关闭：释放 Browser Instance

**隔离**：每个 Session 独立的 cookies、localStorage、profile。

---

## Architecture

### Runtime-first

**定义**：Browser 是 Runtime Environment 而非工具。Agent 不直接操作 Browser，而是通过 Runtime 接口。

**对比**：
- **传统**：LLM → click/type/scroll → Browser（工具）
- **Runtime-first**：LLM → Skill → Runtime → Browser（环境）

---

### Agent Replaceable

**定义**：Runtime 不依赖特定 Agent 实现，可以对接任意 Agent。

**支持的 Agent**：
- Claude Code
- OpenAI Operator
- browser-use
- LangGraph
- CrewAI
- MCP clients

---

### Abstraction Erosion

**定义**：架构层次随着时间推移逐渐被破坏的过程。

**典型表现**：
- Agent 开始直接调用 Playwright
- Skill 持有全局状态
- Event Handler 直接操作 DOM

**预防**：通过 AGENT_RULES.md 强约束。

---

## Components

### BrowserServer (当前 Phase 1)

**定义**：管理单个 Camoufox 浏览器实例的类，提供 REST API。

**核心方法**：
- `launch_browser()`
- `close_browser()`
- `open_url()`
- `close_tab()`

**存储**：
- Cookies → `~/.camofox/cookies/`
- Profiles → `~/.camofox/profiles/`

---

### Browser Pool (Phase 2)

**定义**：管理多个 Browser Instance 的池化系统。

**功能**：
- Instance 分配/回收
- 负载均衡
- 健康检查
- 自动重启

---

### CDP (Chrome DevTools Protocol)

**定义**：Chrome 内置的调试协议，用于与浏览器通信。

**用途**：
- DOM 操作
- Network 拦截
- Console 捕获
- Performance 分析

---

## Project Terms

### Phase 1: Browser Daemon Foundation

**目标**：建立稳定的 Browser Runtime Core
- [x] Camoufox Browser Daemon (REST API)
- [x] Multi-tab management
- [x] Cookie persistence
- [ ] Browser pool
- [ ] Session lifecycle

---

### Phase 2: Persona & Observation

**目标**：Semantic Observation 和 Persona System
- [ ] Persona System
- [ ] Semantic Observation Pipeline
- [ ] Event Bus (MVP)
- [ ] Skill Runtime (MVP)

---

### Phase 3: Multi-Agent & Memory

**目标**：多 Agent 协作和长期记忆
- [ ] Multi-Agent Architecture
- [ ] Memory Graph
- [ ] Workflow Engine
- [ ] Advanced Event Bus

---

### Phase 4: Self-Evolution

**目标**：系统可自主学习和适应
- [ ] Self-Evolving Skills
- [ ] Distributed Browser Cluster
- [ ] Advanced Stealth

---

## External References

### Camoufox

**定义**：C++ 级别的 stealth browser 引擎，基于 Firefox。

**特点**：
- Fingerprint spoofing (hardware, canvas, WebGL, audio)
- Human-like behavior
- Anti-detection

**链接**：https://github.com/nite-nite/camoufox

### camofox-browser

**定义**：Node.js 版本的 camofox browser runtime。

**链接**：https://github.com/redf0x1/camofox-browser

---

## Acronyms

| Acronym | Full Form |
|---------|-----------|
| API | Application Programming Interface |
| CDP | Chrome DevTools Protocol |
| CLI | Command Line Interface |
| DOM | Document Object Model |
| LLM | Large Language Model |
| MCP | Model Context Protocol |
| REST | Representational State Transfer |
| RPA | Robotic Process Automation |
| YAML | YAML Ain't Markup Language |
