---
domain: xiaohongshu.com
discovered: 2026-05-10
status: verified
---

# 小红书 — Navigation & Scraping

Field-tested against xiaohongshu.com on 2026-05-10.

## URL Patterns

| Page | URL |
|------|-----|
| 首页推荐 | `https://www.xiaohongshu.com/explore` |
| 搜索结果 | `https://www.xiaohongshu.com/search_result?keyword={kw}&source=web_explore_feed` |
| 笔记详情 | `https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={token}&xsec_source=pc_feed` |
| 用户主页 | `https://www.xiaohongshu.com/user/profile/{user_id}?xsec_token={token}` |
| 发布页 | `https://creator.xiaohongshu.com/publish/publish?source=official` |

## Login

### QR Code Login

```bash
# 有头模式打开，会显示QR码
pycamofox open "https://www.xiaohongshu.com/explore"

# 登录状态检测
pycamofox eval "document.querySelector('.main-container .user .link-wrapper .channel') ? 'logged in' : 'not logged in'"
```

### Cookie Persistence

Cookies自动保存到 `~/.camofox/cookies/xiaohongshu.com.json`。

## Key Selectors

### 登录状态
```css
.main-container .user .link-wrapper .channel  /* 登录后可见 */
.qrcode-img                              /* QR码 */
```

### 搜索
```css
div.filter              /* 筛选按钮 */
div.filter-panel        /* 筛选面板 */
```

### 笔记详情
```css
.comments-container      /* 评论容器 */
.parent-comment          /* 父评论 */
.show-more              /* 加载更多 */
.interaction-container   /* 互动区（点赞收藏） */
```

### 互动操作
```css
.interact-container .left .like-lottie          /* 点赞按钮 */
.interact-container .left .reds-icon.collect-icon  /* 收藏按钮 */
```

### 评论
```css
div.input-box div.content-edit span   /* 评论输入触发 */
div.input-box div.content-edit p.content-input  /* 评论输入框 */
div.bottom button.submit               /* 发送评论 */
```

### 发布页
```css
input[type="file"]                /* 文件上传 */
div.d-input input                  /* 标题输入 */
div.ql-editor                      /* 正文编辑器 */
.publish-page-publish-btn button.bg-red  /* 发布按钮 */
```

### 用户主页
```css
.user-name            /* 用户昵称 */
```

## Data Extraction

### 搜索结果提取

```javascript
// 笔记列表提取
pycamofox eval "
(() => {
  const notes = document.querySelectorAll('.feeds-page .note-item');
  return Array.from(notes).map(n => ({
    id: n.dataset.id || '',
    title: n.querySelector('.title')?.innerText?.trim() || '',
    author: n.querySelector('.nickname')?.innerText?.trim() || '',
    likes: n.querySelector('.liked-count')?.innerText?.trim() || '',
    url: n.querySelector('a')?.href || ''
  }));
})()
"
```

### 笔记详情提取

```javascript
// 获取笔记完整内容
pycamofox eval "
(() => {
  const title = document.querySelector('.note-content .title')?.innerText?.trim() || '';
  const author = document.querySelector('.author-wrapper .name')?.innerText?.trim() || '';
  const content = document.querySelector('.note-content .desc')?.innerText?.trim() || '';
  const images = Array.from(document.querySelectorAll('.gallery img')).map(i => i.src);
  return { title, author, content, images };
})()
"
```

### xsec_token 重要性

**xsec_token 是必须的！** 小红书所有接口都需要 xsec_token：
- 从搜索结果或首页 feed 中获取
- 用于构建详情页 URL 和 API 请求

```javascript
// 获取 xsec_token
pycamofox eval "
document.querySelector('.note-item')?.dataset.xsecToken || ''
"
```

## Anti-Detection Notes

- 小红书有严格反爬，**必须使用 camoufox**（非普通浏览器）
- 请求间隔加随机延迟：`sleep(random.uniform(1, 3))`
- 不要频繁操作，控制频率
- QR码登录后 token 有时效，关注过期

## Gotchas

- **xsec_token 必须配对使用** — 每个请求都需要从页面数据中获取最新的 token
- **图片懒加载** — 滚动后才会加载完整图片 URL
- **评论需要展开** — 子评论默认折叠，需要点击"展开更多"
- **发布需要创作者中心** — 普通账号可能没有发布权限
