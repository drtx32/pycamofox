---
name: pycamofox-cli
description: >
  Python版camoufox浏览器CLI，复刻camofox-browser(npm)架构。
  REST API服务器 + CLI客户端，支持有头模式、扫码登录、cookies自动导入导出。
  Agent工作时会在agent-workspace/目录沉淀站点经验。
version: 1.2.0
---

# pycamofox-cli

Python版camoufox浏览器CLI，复刻camofox-browser(npm)架构。

## 架构

```
┌─────────────────────────────────────┐
│  pycamofox (CLI)                    │
│  $ pycamofox open "https://..."    │
└──────────────┬────────────────────┘
                │ HTTP (localhost:9377)
                ▼
┌─────────────────────────────────────┐
│  pycamofox-server (REST API)        │
│  - FastAPI + uvicorn                │
│  - camoufox (反检测浏览器)           │
└─────────────────────────────────────┘
```

## 特性

- **命令即服务**: 运行命令时自动后台启动server，server常驻
- **有头模式**: 支持打开真实浏览器窗口，扫码登录
- **Profile持久化**: 默认使用 `~/.camofox/profiles/default`
- **Cookies自动同步**: 自动从 `~/.camofox/cookies/` 导入/导出
- **自动重连**: 命令自动连接已运行的server
- **站点经验沉淀**: agent在`agent-workspace/domain-skills/`目录写入站点知识

## 默认路径（与camofox-browser npm版兼容）

| 用途 | 路径 |
|------|------|
| Profile目录 | `~/.camofox/profiles/default` |
| Cookies目录 | `~/.camofox/cookies/<domain>.json` |

---

# Agent 使用指南

## 浏览哲学

**像人一样思考，兼顾高效与适应性的完成任务。**

执行任务时不会过度依赖固有印象所规划的步骤，而是带着目标进入，边看边判断，遇到阻碍就解决，发现内容不够就深入——全程围绕「我要达成什么」做决策。

**① 拿到请求** — 先明确用户要做什么，定义成功标准。

**② 选择起点** — 根据任务性质、平台特征、达成条件，选一个最可能直达的方式作为第一步去验证。

**③ 过程校验** — 每一步的结果都是证据，不只是成功或失败的二元信号。

**④ 完成判断** — 对照定义的任务成功标准，确认任务完成后才停止。

## 工具选择

| 场景 | 工具 | 说明 |
|------|------|------|
| 打开URL | `pycamofox open <url>` | 自动启动server，导入cookies |
| 截图 | `pycamofox screenshot [-o path] [--full-page]` | 截图，full-page为整页 |
| 读页面文本 | `pycamofox get-text` | 获取页面body文本 |
| 读链接列表 | `pycamofox get-links` | 获取所有链接 |
| 读当前URL | `pycamofox get-url` | 获取当前页面URL |
| 读标题 | `pycamofox get-title` | 获取页面标题 |
| 导航 | `pycamofox navigate <url>` | 导航到URL（当前tab） |
| 后退/前进 | `pycamofox go-back` / `pycamofox go-forward` | 浏览器历史 |
| 点击 | `pycamofox click <selector>` | CSS选择器点击 |
| 输入文本 | `pycamofox type <selector> <text>` | 向输入框填文本 |
| 执行JS | `pycamofox eval <expression>` | 执行JS表达式 |
| 滚动 | `pycamofox scroll [up\|down] [amount]` | 滚动页面 |
| 等待元素 | 通过 eval + wait 实现 | 等DOM元素出现 |
| 关闭标签页 | `pycamofox close-tab` | 关闭当前tab |

## 截图优先原则

先用 `screenshot` 了解当前页面，快速找到可见目标，再决定下一步：
- 截图判断页面状态
- 点击用 selector 或坐标
- 读 DOM 内容用 eval

## 站点经验机制

pycamofox-cli 有**自进化能力** — agent在工作过程中把发现的站点知识写入文件，下次遇到同类任务直接复用。

### 目录结构

```
agent-workspace/
├── agent_helpers.py      # agent自定义的Python辅助函数
└── domain-skills/       # 站点经验沉淀
    ├── douyin/
    │   └── navigation.md
    ├── bilibili/
    │   └── navigation.md
    └── example/
        └── scraping.md
```

### 工作流程

```
1. agent 访问 https://example.com
2. 发现 x 平台的选择器、URL模式、操作技巧
3. 写入 agent-workspace/domain-skills/example/navigation.md
4. 下次遇到同类任务，直接读取文件，跳过探索阶段
```

### 写入规则

- 只写**经过验证的事实**，不写猜测
- 写**能复用的模式**，不写具体操作步骤
- 标注**发现日期**，当提示而非保证
- 失败时回退通用模式，更新文件

### 读取规则

**遇到已知站点时，必须读取对应文件**：
```bash
# 检查是否有该站点的经验文件
ls agent-workspace/domain-skills/<domain>/

# 读取 navigation.md 获取站点知识
cat agent-workspace/domain-skills/<domain>/navigation.md
```

---

# CLI 命令参考

## 全局选项

| 选项 | 说明 |
|------|------|
| `--port <port>` | 服务器端口（默认9377） |
| `--headless` | 无头模式运行 |
| `--user-data-dir <path>` | 浏览器profile目录 |

## 命令列表

### launch
启动浏览器。
```bash
pycamofox launch [--headless]
```

### close
关闭浏览器（并自动导出cookies）。

### open \<url\>
打开URL，自动导入cookies。
```bash
pycamofox open "https://www.douyin.com"
```

### navigate \<url\>
在当前tab导航到URL。
```bash
pycamofox navigate "https://www.baidu.com"
```

### screenshot
截图。
```bash
pycamofox screenshot                        # 输出到终端(base64)
pycamofox screenshot -o output.png          # 保存到文件
pycamofox screenshot --full-page             # 整页截图
```

### click \<selector\>
点击元素（CSS选择器）。
```bash
pycamofox click ".login-button"
```

### type \<selector\> \<text\>
向输入框填文本。
```bash
pycamofox type "input[name=keyword]" "搜索内容"
```

### eval \<expression\>
执行JavaScript表达式。
```bash
pycamofox eval "document.title"
pycamofox eval "document.querySelectorAll('a').length"
```

### scroll [up|down] [amount]
滚动页面。
```bash
pycamofox scroll down 3
```

### go-back / go-forward
浏览器后退/前进。

### get-text
获取页面文本（innerText of body）。

### get-links
获取所有链接。
```json
{
  "links": [
    {"href": "https://...", "text": "链接文字"},
    ...
  ]
}
```

### get-url
获取当前URL。

### get-title
获取页面标题。

### health
健康检查。

### close-tab
关闭当前tab。

---

# REST API 参考

服务器默认运行在 `http://127.0.0.1:9377`。

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/browser/launch` | 启动浏览器 |
| POST | `/browser/close` | 关闭浏览器 |
| POST | `/tabs/open` | 打开URL（新tab） |
| POST | `/tabs/close` | 关闭tab |
| POST | `/tabs/screenshot` | 截图 |
| GET | `/tabs/get-url` | 获取URL |
| GET | `/tabs/get-text` | 获取文本 |
| GET | `/tabs/get-links` | 获取链接 |
| GET | `/tabs/get-title` | 获取标题 |
| POST | `/tabs/click` | 点击 |
| POST | `/tabs/type` | 输入文本 |
| POST | `/tabs/eval` | 执行JS |
| POST | `/tabs/scroll` | 滚动 |
| POST | `/tabs/navigate` | 导航 |
| POST | `/tabs/go-back` | 后退 |
| POST | `/tabs/go-forward` | 前进 |
| GET | `/tabs/get-cookies` | 获取cookies |
| POST | `/tabs/set-cookies` | 设置cookies |

---

# 验证记录

| 日期 | 方式 | 结果 | 说明 |
|------|------|------|------|
| 2026-05-10 | open | ✅ | 自动启动server并打开URL |
| 2026-05-10 | screenshot | ✅ | 截图成功 |
| 2026-05-10 | health | ✅ | 服务健康检查 |
| 2026-05-10 | 有头模式 | ✅ | 支持打开浏览器窗口 |
| 2026-05-10 | user-data-dir | ✅ | Profile持久化成功 |
| 2026-05-10 | cookies自动导出 | ✅ | 关闭时保存到~/.camofox/cookies/ |
| 2026-05-10 | cookies自动导入 | ✅ | 打开URL时自动导入cookies |
