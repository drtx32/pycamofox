# Roadmap

> 这是 evolutionary stages，不是 TODO list。
> 每个 Phase 是前一个 Phase 的基础，不可跳跃。

---

## Phase 1: Browser Daemon Foundation

**目标**: 建立稳定的 Browser Runtime Core

### 核心组件

- [x] Camoufox Browser Daemon (REST API)
- [x] Multi-tab management
- [x] Cookie persistence (per-domain)
- [x] Profile management (user-data-dir)
- [ ] Browser pool (多浏览器实例管理)
- [ ] Session lifecycle management

### 已验证路径

```
CLI → Server → Camoufox → Tabs/Persistence
```

### 验收标准

- [ ] 可以启动 daemon，launch browser
- [ ] 可以打开多个 tab
- [ ] 可以关闭 tab
- [ ] Cookie 在重启后持久化
- [ ] 不同 profile 隔离

---

## Phase 2: Persona & Observation

**目标**: 建立 Semantic Observation 和 Persona System

### 核心组件

- [ ] **Persona System**
  - [ ] YAML persona 配置格式
  - [ ] Persona ↔ Proxy ↔ Session 绑定
  - [ ] Persona lifecycle manager
  - [ ] Hardware/Fonts/Locale/Timezone 配置

- [ ] **Semantic Observation Pipeline**
  - [ ] Accessibility Tree extractor
  - [ ] Semantic state extraction (page_type, actions, content)
  - [ ] Compression layer
  - [ ] JSON output format

- [ ] **Event Bus (MVP)**
  - [ ] network_idle event
  - [ ] navigation event
  - [ ] Basic event subscription

- [ ] **Skill Runtime (MVP)**
  - [ ] Skill registry
  - [ ] github.* skills (search_repo, get_user)
  - [ ] generic.* skills (search, scroll, click)

### 架构变化

```
Phase 1: Agent → CLI → Server → Browser
Phase 2: Agent → Skills → Runtime → Event Bus → Browser
```

### 验收标准

- [ ] Persona 配置文件可加载
- [ ] Persona 切换不破坏 session
- [ ] `runtime.observe()` 返回语义化 JSON
- [ ] Skills 可通过 registry 调用
- [ ] Event Bus 可订阅/发布

---

## Phase 3: Multi-Agent & Memory

**目标**: 支持多 Agent 协作和长期记忆

### 核心组件

- [ ] **Multi-Agent Architecture**
  - [ ] Planner / Sub-Agent 模式
  - [ ] Tab pool manager
  - [ ] Agent coordination protocol
  - [ ] Result aggregation

- [ ] **Memory Graph**
  - [ ] Query → Evidence tracking
  - [ ] Source attribution
  - [ ] Contradiction detection
  - [ ] Confidence scoring

- [ ] **Workflow Engine**
  - [ ] Workflow definition format
  - [ ] Step orchestration
  - [ ] Error recovery
  - [ ] Checkpoint/Resume

- [ ] **Advanced Event Bus**
  - [ ] anti_bot_detected event
  - [ ] captcha_risk event
  - [ ] session_degraded event
  - [ ] fingerprint_mismatch event

### 验收标准

- [ ] 可同时运行多个 Agent
- [ ] Agent 可共享 Browser tabs
- [ ] Memory 可跨会话保留
- [ ] Workflow 可中断后恢复
- [ ] Anti-bot 事件可被捕获和处理

---

## Phase 4: Self-Evolution

**目标**: 系统可自主学习和适应

### 核心组件

- [ ] **Self-Evolving Skills**
  - [ ] 自动生成新 Skill
  - [ ] 自动修复 selector
  - [ ] Site memory persistence
  - [ ] Pattern learning

- [ ] **Distributed Browser Cluster**
  - [ ] Remote browser nodes
  - [ ] Containerized browsers
  - [ ] Browser farm management
  - [ ] Load balancing

- [ ] **Advanced Stealth**
  - [ ] Mouse rhythm simulation
  - [ ] Idle behavior patterns
  - [ ] Advanced fingerprint management
  - [ ] TLS/HTTP2 fingerprint consistency

### 验收标准

- [ ] 系统可从错误中学习
- [ ] 新站点可自动适配
- [ ] 支持分布式部署
- [ ] 长期运行稳定

---

## 版本规划

| Version | Phase | 内容 |
|---------|-------|------|
| 0.1.x | Phase 1 | Basic daemon, single browser |
| 0.2.x | Phase 1 | Browser pool, session management |
| 0.3.x | Phase 2 | Persona system |
| 0.4.x | Phase 2 | Semantic observation, Skill runtime |
| 0.5.x | Phase 3 | Multi-agent, memory graph |
| 1.0.x | Phase 3-4 | Production-ready runtime |

---

## 决策记录

### 2026-05-10: 项目定位

- 确定本项目为 **Stealth Browser Runtime Infrastructure**
- 不是 Playwright wrapper，不是 browser-use clone
- 对标：camofox-browser, web-access, OpenAI Operator
- 当前处于 Phase 1 向 Phase 2 过渡阶段

---

## Non-goals (明确不做)

- 不做 LLM Provider（但兼容所有 Provider）
- 不做通用 Agent Framework
- 不做传统搜索引擎
- 不做简单 RPA
- 不追求单 Agent 万能系统
