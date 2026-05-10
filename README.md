# pycamofox

**Stealth Browser Runtime Infrastructure for AI Agents**

复刻 [camofox-browser](https://github.com/redf0x1/camofox-browser) (npm) 的 Python 版本，面向 AI Agent 提供长期、稳定、低风控的真实互联网浏览能力。

## 项目定位

本项目不是：
- Playwright/Puppeteer wrapper
- 简单的浏览器自动化脚本
- "AI 自动点按钮"工具

本项目是：
- **Stealth Browser Runtime Infrastructure** — 让 AI Agent 能在真实互联网中长期、稳定、低风控地执行复杂 research/workflow 任务
- **Runtime-first** — Browser 是 Runtime Environment，不是工具
- **Skill-native** — Agent 调用语义化 Actions，不直接操作 DOM

## 核心目标

让 AI 能够：
- 长期、稳定、低风控地在真实互联网环境中执行任务
- 跨站点信息综合
- 多步骤工作流编排
- 持久化认证会话管理
- 绕过反爬检测（Stealth）

## 技术栈

- **Browser Engine**: [Camoufox](https://github.com/nite-nite/camoufox) (C++ 级别 fingerprint spoofing)
- **API Layer**: FastAPI + Uvicorn
- **Python**: 3.11+

## 当前状态

已实现：
- Camoufox browser daemon (REST API 模式)
- 多 tab 管理
- Cookie persistence (按域名存储)
- Profile 管理 (user-data-dir)
- Framework-managed input 处理 (React/Vue)
- HTTP GET (无浏览器，用于静态页面/APIs)

进行中：
- Persona system
- Semantic observation pipeline
- Event-driven architecture

## 架构演进阶段

| Phase | 内容 |
|-------|------|
| Phase 1 | Browser daemon, session manager, profile isolation |
| Phase 2 | Semantic observation, event bus, skill runtime |
| Phase 3 | Multi-agent orchestration, memory graph |
| Phase 4 | Self-evolving skills, distributed browser cluster |

## 相关项目

| 项目 | 定位 |
|------|------|
| [camofox-browser](https://github.com/redf0x1/camofox-browser) | Node.js 版本参考 |
| [Camoufox](https://github.com/nite-nite/camoufox) | Stealth browser engine |
| [browser-use](https://github.com/browser-use/browser-use) | Browser Agent SDK |
| [BrowserMCP](https://github.com/browserbase/stagehand) | MCP Browser Adapter |
| [web-access](https://github.com/anthropics/anthropic-cookbook) | Research-oriented browsing |

## 文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 系统边界与模块设计
- [PRINCIPLES.md](./PRINCIPLES.md) — 核心原则
- [AGENT_RULES.md](./AGENT_RULES.md) — Claude Code 行为约束
- [ROADMAP.md](./ROADMAP.md) — 演化路线
- [MEMORY.md](./MEMORY.md) — 当前系统状态
- [constitution/](./constitution/) — 完整宪法层

## 许可证

MIT
