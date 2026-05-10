# Douyin — Site Navigation & Structure

Field-tested against douyin.com on 2026-05-10.
Requires login for personalized features; public pages are accessible without auth.

---

## URL Patterns

| Page | URL |
|------|-----|
| Home (recommended feed) | `https://www.douyin.com/` |
| Search | `https://www.douyin.com/search?keyword={QUERY}` |
| User profile | `https://www.douyin.com/user/{UID}` |
| Video page | `https://www.douyin.com/video/{VIDEO_ID}` |
| Watch history | `https://www.douyin.com/watchlater/` |

---

## Login

Douyin supports QR code login:
- Headful mode required: `pycamofox open "https://www.douyin.com"` (no --headless)
- QR code appears in the browser window
- Cookies auto-imported on open, auto-exported on close

### Cookie persistence

Cookies are saved to `~/.camofox/cookies/douyin.com.json` on browser close.
On next open, cookies are auto-imported — no need to re-scan QR.

---

## Detecting Login State

```python
# Logged in: user avatar element exists
pycamofox eval "document.querySelector('.header-user-info') ? 'logged in' : 'not logged in'"

# Logged out: login button visible
pycamofox eval "document.querySelector('.login-button') ? 'not logged in' : 'logged in'"
```

---

## Gotchas

- **QR login requires headful mode** — `--headless` hides the QR code
- **Cookies are domain-specific** — 抖音 uses `douyin.com`, not `bytedance.com`
- **Video IDs are numeric** — extracted from URL or page data attributes
- **wait_for_load() is not enough on SPA** — add `wait(2)` before querying selectors
