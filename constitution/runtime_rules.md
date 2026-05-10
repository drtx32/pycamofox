# Runtime Rules

> Browser Runtime 的核心约束

## Browser Lifecycle

### 启动

1. Runtime 启动 → 创建 Browser Pool
2. Browser Pool 初始化指定数量的 Browser Instances
3. 每个 Instance 绑定一个 Persona
4. Proxy 绑定到 Persona（Phase 2 实现）

### Session 创建

1. Agent 请求 Session
2. Runtime 分配空闲 Browser Instance
3. Session 绑定 Persona（从 Instance 继承）
4. Session 记录创建时间、Browser Instance ID

### Session 关闭

1. 导出 cookies（per-domain）
2. 保存 session state（scroll position, tab state）
3. 释放 Browser Instance（归还 Pool）
4. Browser Instance 不关闭（保持 warm）

### 异常处理

| 异常 | 处理方式 |
|------|----------|
| Browser Crash | 重启 Instance，重新创建 Session |
| Anti-bot Detected | 触发 event，Agent 决定是否切换 Persona |
| Captcha | 触发 event，Agent 决定是否处理 |
| Network Timeout | 重试 3 次，超时则 Session 失败 |

## Event Bus

### 必须支持的 Events

```python
# Navigation
navigation = {
    "type": "navigation",
    "url": "https://...",
    "tab_id": "...",
    "timestamp": 1234567890
}

# Network
network_idle = {
    "type": "network_idle",
    "tab_id": "...",
    "timestamp": 1234567890
}

# Anti-bot
anti_bot_detected = {
    "type": "anti_bot_detected",
    "tab_id": "...",
    "reason": "fingerprint_mismatch | human_check | captcha",
    "timestamp": 1234567890
}

# Session
session_degraded = {
    "type": "session_degraded",
    "tab_id": "...",
    "reason": "cookie_expired | proxy_dead",
    "timestamp": 1234567890
}
```

### Event 订阅规则

- Agent 可以订阅任意 Event
- Event 触发时调用 Handler
- Handler 执行期间，Session 状态冻结
- Handler 执行时间过长（>60s）则超时取消

## Persona System

### Persona 配置格式

```yaml
# persona/us-east-dev.yaml
persona:
  id: us-east-dev-1
  locale: en-US
  timezone: America/New_York
  hardware:
    gpu: intel_uhd_620
    memory: 16GB
    cpu: intel_core_i7_10th
  fonts:
    - Segoe UI
    - Arial
    - Helvetica
  browser:
    version: 120
    platform: windows
  proxy:
    url: "http://proxy-us-east.example.com:8080"
    geo: "New York"
    asn: 12345
  browsing_patterns:
    scroll_speed: normal
    typing_speed: normal
    click_interval: 1-3s
  session_age: "30d"
  extensions: []
```

### Persona 绑定规则

1. Session 创建时绑定 Persona
2. Session 生命周期内 Persona 不变
3. Proxy 必须与 Persona timezone/locale 一致
4. Session 关闭时保存 Persona state

### Persona 切换

1. 关闭旧 Session（导出 cookies，保存 state）
2. 创建新 Session（绑定新 Persona）
3. 新 Session 从旧 Session 继承部分 cookies（如 GitHub）

## Observation Pipeline

### 语义状态格式

```json
{
  "page_type": "github_search_results",
  "url": "https://github.com/search?q=camo",
  "timestamp": 1234567890,
  "actions": [
    {"type": "link", "text": "nite-nite/camoufox", "href": "/nite-nite/camoufox"},
    {"type": "filter", "name": "Language", "value": "Python"}
  ],
  "content": {
    "title": "Search results for camo",
    "repository_count": 42,
    "repositories": [
      {
        "name": "nite-nite/camoufox",
        "description": "A stealth browser...",
        "stars": 1234,
        "language": "Python"
      }
    ]
  },
  "pagination": {
    "has_next": true,
    "current_page": 1
  },
  "metadata": {
    "loaded_resources": 23,
    "render_time_ms": 1200
  }
}
```

### Pipeline 步骤

1. **DOM Access**: 获取完整 DOM
2. **Accessibility Tree**: 提取 a11y tree
3. **Semantic Extraction**: 识别 page_type, actions, content
4. **Compression**: 移除冗余，保留关键信息
5. **JSON Output**: 输出结构化状态

### 禁止行为

- raw HTML 传入 LLM
- 全 DOM 作为 context
- 每次 observation 返回 >10KB 数据

## Storage

### Session Storage

```
~/.camofox/
├── profiles/           # Browser profiles
│   └── <profile_id>/
├── cookies/            # Per-domain cookies
│   └── <domain>.json
├── sessions/           # Session states (Phase 2)
│   └── <session_id>.json
└── personas/          # Persona configs (Phase 2)
    └── <persona_id>.yaml
```

### Cookie 格式

```json
[
  {
    "name": "session",
    "value": "abc123",
    "domain": ".github.com",
    "path": "/",
    "expires": 1234567890,
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  }
]
```

## Error Recovery

### Retry Policy

| 操作 | 重试次数 | 间隔 |
|------|----------|------|
| Network Request | 3 | 1s, 2s, 4s (exponential) |
| Browser Launch | 2 | 5s, 10s |
| Click/Type | 2 | 0.5s, 1s |

### Circuit Breaker

- 连续 5 次操作失败 → 标记 Session degraded
- 连续 3 次 anti_bot_detected → 建议切换 Persona
- Session degraded 超过 10 分钟 → 自动关闭

### Checkpoint

- 每个 Workflow step 完成后保存 checkpoint
- Checkpoint 包含：Session ID, Tab state, Step index
- 支持从 checkpoint 恢复（Phase 3 实现）
