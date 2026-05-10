# Memory

> 当前系统状态记录。Claude Code 长期后可能偏离架构，需要此文件锚定。

## 最新架构状态 (2026-05-10)

### 项目定位

**pycamofox** — Stealth Browser Runtime Infrastructure for AI Agents

复刻 camofox-browser (npm) 的 Python 版本，当前处于 **Phase 1 → Phase 2** 过渡阶段。

### 当前代码结构

```
src/pycamofox/
├── __init__.py          # Package exports
├── __main__.py          # Entry point
├── cli.py               # CLI client (命令即服务模式)
└── server.py            # Browser daemon (FastAPI + Camoufox)
```

**核心类**：`BrowserServer` (server.py)

### 已实现功能

- [x] REST API server (FastAPI/Uvicorn)
- [x] Camoufox browser launch/close
- [x] Multi-tab management
- [x] Cookie persistence (按域名存储到 `~/.camofox/cookies/`)
- [x] Profile 管理 (user-data-dir)
- [x] Framework-managed input (React/Vue fill)
- [x] HTTP GET (无浏览器，用于静态页面/APIs)
- [x] CLI auto-start server

### API 端点

| Method | Endpoint | 功能 |
|--------|----------|------|
| GET | /health | 健康检查 |
| POST | /browser/launch | 启动浏览器 |
| POST | /browser/close | 关闭浏览器 |
| POST | /tabs/open | 打开 URL |
| POST | /tabs/close | 关闭 tab |
| GET | /tabs/get-url | 获取当前 URL |
| GET | /tabs/get-text | 获取页面文本 |
| GET | /tabs/get-links | 获取所有链接 |
| POST | /tabs/click | 点击元素 |
| POST | /tabs/type | 输入文本 |
| POST | /tabs/fill | Framework-managed input |
| POST | /tabs/eval | 执行 JS |
| POST | /tabs/navigate | 导航 |
| POST | /tabs/scroll | 滚动 |
| POST | /tabs/wait-network-idle | 等待网络空闲 |
| GET | /http/get | HTTP GET |

### 存储路径

- **Profiles**: `~/.camofox/profiles/<profile_name>`
- **Cookies**: `~/.camofox/cookies/<domain>.json`

### 依赖

- camoufox
- playwright
- fastapi
- uvicorn
- pydantic

### 关键设计决策

#### 1. 命令即服务模式

CLI 命令自动启动 server，server 管理浏览器生命周期。
Agent/CLI 通过 REST API 与 browser 交互。

#### 2. Cookie per-domain persistence

每次打开 URL 前自动导入该域名的 cookies。
关闭浏览器时自动导出所有 cookies。

#### 3. Framework-managed input support

`fill` 命令不同于 `type`：先 focus、clear，再 type，最后 fire input/change events。
目的是让 React/Vue 等框架的 controlled inputs 能正确响应。

### Phase 2 目标（进行中）

1. **Persona System** — 未开始
2. **Semantic Observation Pipeline** — 未开始
3. **Event Bus** — 未开始
4. **Skill Runtime** — 未开始

### Phase 3 目标

5. Multi-Agent Architecture
6. Memory Graph
7. Workflow Engine

### Phase 4 目标

8. Self-Evolving Skills
9. Distributed Browser Cluster

---

## 常见问题

### Q: 为什么用 Camoufox 而非 Playwright 直接？

A: Camoufox 提供 C++ 级别的 fingerprint spoofing，能绕过反爬检测。Playwright 的 stealth 能力有限。

### Q: 为什么是 REST API 而非 WebSocket？

A: 当前 Phase 1 只需要 request-response 模式。Event Bus 在 Phase 2 实现。

### Q: 为什么 cookie 存成 per-domain？

A: 便于部分网站登录态复用。加载 URL 时自动导入对应域名的 cookies。

---

## 重要约束

- **禁止** Agent 直接调用 Playwright/Camoufox API
- **禁止** raw HTML/DOM 传入 LLM
- **禁止** 运行时随机切换 Persona
- **必须** 通过 Semantic Skills 与 Browser 交互

---

## 更新记录

| Date | Change |
|------|--------|
| 2026-05-10 | 项目初始化，建立 Constitution Layer 文档体系 |
