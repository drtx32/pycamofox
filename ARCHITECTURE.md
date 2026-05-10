# Architecture

## 系统边界

```
┌─────────────────────────────────────────────────────────────┐
│                      Planner / Agent                        │
│              (Claude Code, OpenAI Operator, etc.)           │
└─────────────────────────┬───────────────────────────────────┘
                          │ Semantic Skills API
┌─────────────────────────▼───────────────────────────────────┐
│                    Research Runtime                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Workflow   │  │  Memory      │  │  Task             │  │
│  │  Engine     │  │  Graph       │  │  Coordination     │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ Runtime Interface
┌─────────────────────────▼───────────────────────────────────┐
│                    Browser Runtime                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Camoufox   │  │  Persona     │  │  Proxy            │  │
│  │  Pool       │  │  Manager     │  │  Manager          │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Session    │  │  Auth       │  │  CDP             │  │
│  │  Storage    │  │  Vault      │  │  Event Bus       │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ CDP
┌─────────────────────────▼───────────────────────────────────┐
│                    Real Browsers (Camoufox)                │
└─────────────────────────────────────────────────────────────┘
```

## 模块边界

### Agent 永远不能直接操作 Browser

```
Agent --→ Skill --→ Runtime --→ Browser
                 ↑
           Semantic Actions
           (不暴露 DOM)
```

**绝对禁止**：
- Agent 直接调用 Playwright/Camoufox API
- Agent 操作 CSS selector
- Agent 读取 raw HTML/DOM

**必须通过**：
- Semantic Skills (`github.search()`, `reddit.expand_thread()`)
- Runtime Event Bus
- Semantic Observation Layer

## 当前已实现模块

### src/pycamofox/

```
src/pycamofox/
├── __init__.py          # Package exports
├── __main__.py          # Entry point
├── cli.py               # CLI client (命令即服务)
└── server.py            # Browser daemon (REST API server)
```

### server.py — BrowserDaemon

- **BrowserServer** 类管理单个浏览器实例
- **REST API** 提供给 CLI 调用
- **Cookie persistence** 按域名存储到 `~/.camofox/cookies/`
- **Profile 管理** 通过 `user-data-dir` 实现多 profile

### cli.py — CLI Client

- 命令行接口，调用 server API
- 自动启动 server（如果未运行）
- 命令模式：`launch`, `open`, `click`, `type`, `eval`, `screenshot`, etc.

## 待实现模块

### Phase 2 (优先级顺序)

1. **Persona System**
   - YAML 配置 persona（locale, timezone, fonts, browsing_history）
   - Persona ↔ Proxy ↔ Session 绑定
   - 长期一致性而非随机 fingerprint

2. **Semantic Observation Pipeline**
   ```
   DOM
    ↓
   Accessibility Tree
    ↓
   Semantic Extraction
    ↓
   Compressed State (JSON)
   ```
   - 拒绝全 DOM 输入
   - 降低 token 消耗
   - 减少 hallucination

3. **Event Bus**
   - Browser Runtime emits events：
     - `network_idle`
     - `anti_bot_triggered`
     - `session_degraded`
     - `captcha_risk`
     - `fingerprint_mismatch`
   - Agent 订阅而非 polling

4. **Skill Runtime**
   - Domain Skills: `github.*`, `reddit.*`, `x.*`
   - Workflow Skills: `search → filter → summarize → cite`
   - Meta Skills: `captcha solving`, `login recovery`

### Phase 3

5. **Multi-Agent Architecture**
   - Research Planner
   - Sub Agents（独立 browser tabs）
   - 结果汇总

6. **Memory Graph**
   - Query → Evidence → Sources → Contradictions → Summaries

### Phase 4

7. **Self-Evolving Skills**
   - Agent 自动生成 skill
   - 自动修复 selector
   - 保存 site memory

8. **Distributed Browser Cluster**
   - Remote browser nodes
   - Containerized browsers
   - Browser farms

## 文件结构目标

```
pycamofox/
├── src/pycamofox/
│   ├── __init__.py
│   ├── cli.py
│   ├── server.py
│   ├── browser/              # Phase 1-2
│   │   ├── daemon/           # Browser lifecycle
│   │   ├── cdp/              # CDP integration
│   │   ├── personas/         # Persona management
│   │   ├── sessions/         # Session storage
│   │   ├── proxies/          # Proxy rotation
│   │   └── stealth/          # Stealth config
│   ├── skills/               # Phase 2
│   │   ├── github/
│   │   ├── reddit/
│   │   ├── x/
│   │   ├── generic/
│   │   └── registry/
│   ├── observation/           # Phase 2
│   │   ├── semantic/
│   │   ├── accessibility/
│   │   ├── compression/
│   │   └── extraction/
│   ├── memory/               # Phase 3
│   │   ├── graph/
│   │   ├── workflows/
│   │   ├── selectors/
│   │   └── sessions/
│   ├── orchestration/        # Phase 3
│   │   ├── agents/
│   │   ├── tabs/
│   │   ├── workflows/
│   │   └── scheduling/
│   └── api/                  # Phase 2-3
│       ├── rpc/
│       ├── websocket/
│       └── sdk/
├── constitution/             # AI-Native governance
│   ├── principles.md
│   ├── architecture.md       # (this file)
│   ├── runtime_rules.md
│   ├── coding_rules.md
│   ├── anti_patterns.md
│   └── glossary.md
└── tests/
```

## 接口契约

### Runtime Interface (目标)

```python
# 不允许
browser.click("#submit")  # ❌ 禁止直接 DOM 操作

# 允许
runtime.execute("github.search_repo", query="...")  # ✓ 语义化 action
runtime.observe()  # → {"page_type": "...", "actions": [...], "content": {...}}
```

### Event Bus (目标)

```python
# Runtime 推送
runtime.on("anti_bot_detected", handler)
runtime.on("captcha_risk", handler)
runtime.on("session_degraded", handler)

# Agent 订阅，而非 polling
```

## 部署模式

- **CLI Mode**: `pycamofox open <url>` → 自动启动 server
- **Server Mode**: `pycamofox server start --port 9377`
- **Embedded Mode**: `from pycamofox import BrowserServer; server = BrowserServer()`
