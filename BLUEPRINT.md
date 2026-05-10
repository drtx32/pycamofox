# Blueprint

> 战略级项目规划，解释"为什么做"和"项目在哪个层次"。
> 相对于 [ARCHITECTURE.md](./ARCHITECTURE.md) 的"怎么做"，这里是"为什么这样做"。

---

## 你在哪个层次

当前大部分 AI Browser 项目停留在：

| 代际 | 类型 | 示例 |
|------|------|------|
| 第一代 | Playwright Wrapper | Puppeteer, Selenium |
| 第二代 | LLM Browser Agent | browser-use, BrowserMCP |
| **第三代（pycamofox 正在靠近）** | **Browser Runtime** | camofox-browser, web-access |
| 第四代（未来） | Autonomous Web OS | persona ecology, skill evolution |

**我们不在做"又一个 AI browser"。我们在做"Stealth-native Browser Infrastructure"。**

---

## 真正的问题

> 真正困难的根本不是 browser automation，而是"互联网生存系统"。

"反检测"根本不是浏览器问题，而是 **Identity Consistency Problem**：

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

全部需要一致。Geo mismatch 会直接触发 soft ban。

**未来真正强的系统不是"undetected browser"，而是"persistent digital personas"。**

---

## camofox-browser 的局限性

camofox-browser 本质做的是"Camoufox Server 化"，已经是 runtime 的雏形：

- ✓ session persistence
- ✓ REST API
- ✓ multi-session
- ✓ profile isolation
- ✓ auth vault
- ✓ CLI
- ✓ accessibility snapshot

**但它还没进入"自治 runtime"阶段**，还缺：

1. **Runtime scheduler** — 现在是 `request → browser action`，而不是 `task orchestration`
2. **Event-driven architecture** — 现在是同步 action，而不是 browser event bus
3. **Persona lifecycle** — 现在是启动时随机 fingerprint，而不是长期一致性
4. **Skill-native execution** — 现在是 `click()/type()/snapshot()`，而不是 `github.search()`
5. **Observation intelligence** — 现在是 DOM/raw HTML，而不是 semantic compressed state

---

## 你缺的不是功能，是 Runtime 层次

**Browser 不该是 SDK，而应该是 Service。**

```
传统：Agent → click/type/scroll → Browser（工具）
我们：  Agent → Semantic Skills → Research Runtime → Stealth Browser（环境）
```

---

## 架构优先级

| 优先级 | 内容 | 说明 |
|--------|------|------|
| **第一优先级** | Browser Daemon | Persistent Browser Runtime，不是每次创建 browser |
| **第二优先级** | Persona System | Camoufox 真正价值所在，长期一致性而非随机 |
| **第三优先级** | Semantic Observation | 别让 agent 看 DOM，给 JSON |
| **第四优先级** | Skill Runtime | 可复用 workflow，不是 click API |
| **第五优先级** | Event Bus | browser runtime emits events，不是 agent polling |

---

## 层级对标

| 层 | 方向 | 代表项目 |
|----|------|---------|
| Browser Infra | Stealth fingerprint | Camoufox |
| Browser Runtime | Server + sessions | camofox-browser |
| Research Runtime | Multi-agent + memory | pycamofox（本项目） |
| Agent OS | Full autonomy | OpenAI Operator（推测） |

---

## 我们在做什么

**pycamofox = Stealth Browser Runtime Infrastructure for AI Agents**

核心目标：让 AI 能够长期、稳定、低风控地在真实互联网环境中执行复杂 research/workflow 任务。

这不是"让 AI 能操作浏览器"。这是"让 AI 能在真实互联网中生存与工作"。

---

## 核心洞察

> 大多数人在卷 agent prompt，而你开始接触 browser infrastructure。这层门槛高很多。

Browser agent 的真正问题不是"怎么让 AI 点击正确按钮"，而是：
- 如何保持数字身份一致性
- 如何建立长期会话
- 如何绕过反爬检测而非被检测
- 如何让 AI 像人一样在互联网中穿梭

**这是稀缺方向。**
