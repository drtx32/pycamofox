"""Baidu search skill — semantic actions for baidu.com.

使用方式:
    from pycamofox.skills import PycamofoxRuntime, SkillRegistry
    runtime = PycamofoxRuntime(session_id="xxx")
    baidu = SkillRegistry.get("baidu.search")(runtime)
    result = baidu.search("python")
"""
import json
import urllib.parse
from typing import Any
from .registry import Skill, skill, PycamofoxRuntime


@skill("baidu.search")
class BaiduSearchSkill(Skill):
    """Baidu search semantic actions.

    提供 baidu.search, baidu.get_results 等语义化接口。
    Agent 通过这些方法操作百度，而不是直接操作 CSS selector。

    注意：Baidu 对自动化请求会触发 CAPTCHA。使用 camoufox-reverse MCP
    或有更强 stealth 配置的浏览器可减少触发概率。
    """
    name = "baidu.search"
    description = "Baidu search engine semantic actions"

    # 百度搜索页面的关键选择器
    SELECTORS = {
        "search_input": "#kw",
        "search_button": "#su",
        "results_container": ".c-container",
        "result_title": ".t > a",
        "result_link": ".c-container a[href]",
        "next_page": "#page > .n",
        "result_count": ".c-containerCount",
        "suggestions": ".suggestion-item",
    }

    def search(self, query: str) -> dict[str, Any]:
        """执行百度搜索。

        Args:
            query: 搜索关键词

        Returns:
            {"status": "ok", "url": "...", "title": "..."}
            {"status": "captcha", "url": "...", "title": "..."} if redirected to CAPTCHA
        """
        r = self.runtime
        import time

        # Navigate to baidu.com
        r.navigate("https://www.baidu.com")
        time.sleep(2)

        # Type with human-like delays
        for char in query:
            r.eval(f"document.querySelector('{self.SELECTORS['search_input']}').value += '{char}'")
            time.sleep(0.05)

        time.sleep(0.3)
        # Submit via Enter
        r.eval(f"document.querySelector('{self.SELECTORS['search_input']}').closest('form').submit()")
        time.sleep(3)

        url_result = r.get_url()
        title_result = r.get_title()

        url = url_result.get("url", "")
        title = title_result.get("title", "")

        # Check if redirected to CAPTCHA
        if "wappass.baidu.com" in url or "captcha" in title.lower():
            return {
                "status": "captcha",
                "url": url,
                "title": title,
                "message": "Baidu requires CAPTCHA verification"
            }

        return {
            "status": "ok",
            "url": url,
            "title": title,
        }

    def get_results(self, max_results: int = 10) -> dict[str, Any]:
        """获取搜索结果列表。

        从页面提取语义化的结果数据，而不是 raw HTML。
        返回格式经过压缩，是给 Agent 的语义化观察结果。

        Returns:
            {
                "query": "...",
                "results": [
                    {"title": "...", "url": "...", "snippet": "..."},
                    ...
                ],
                "count": N,
                "page_url": "..."
            }
        """
        r = self.runtime

        # 提取结果
        eval_result = r.eval(f"""
            () => {{
                const containers = document.querySelectorAll('.c-container');
                return Array.from(containers).slice(0, {max_results}).map(el => {{
                    const titleEl = el.querySelector('.t > a') || el.querySelector('h3 a') || el.querySelector('a');
                    const linkEl = el.querySelector('a[href]');
                    const snippetEl = el.querySelector('.c-abstract') || el.querySelector('.content-right');
                    return {{
                        title: titleEl ? titleEl.innerText : '',
                        url: linkEl ? linkEl.href : '',
                        snippet: snippetEl ? snippetEl.innerText : ''
                    }};
                }}).filter(r => r.title || r.url);
            }}
        """)

        # Get URL safely
        url_result = r.get_url()
        page_url = url_result.get("url", "") if isinstance(url_result, dict) else ""

        # Check if CAPTCHA
        if "wappass.baidu.com" in page_url:
            return {
                "query": "",
                "results": [],
                "count": 0,
                "page_url": page_url,
                "error": "CAPTCHA page - cannot extract results"
            }

        return {
            "query": "",
            "results": eval_result if isinstance(eval_result, list) else [],
            "count": len(eval_result) if isinstance(eval_result, list) else 0,
            "page_url": page_url,
        }

    def get_suggestions(self) -> dict[str, Any]:
        """获取搜索建议/补全词。"""
        r = self.runtime
        suggestions = r.eval("""
            () => {
                const items = document.querySelectorAll('.suggestion-item');
                return Array.from(items).map(el => el.innerText);
            }
        """)
        return {"suggestions": suggestions if isinstance(suggestions, list) else []}

    def scroll_results(self, pages: int = 1) -> dict[str, Any]:
        """向下滚动加载更多结果。"""
        r = self.runtime
        for _ in range(pages):
            r.scroll("down", 3)
            r.wait_network_idle(timeout=5000)
        return {"status": "scrolled", "pages": pages}


@skill("github.search")
class GitHubSearchSkill(Skill):
    """GitHub search semantic actions — works reliably with automation.

    提供 github.search_repo, github.get_user 等语义化接口。
    GitHub 对自动化更友好，是更好的演示平台。
    """
    name = "github.search"
    description = "GitHub search semantic actions"

    SELECTORS = {
        "search_input": "[name='query']",
        "search_button": "[data-search-type='repositories']",
        "repo_item": ".repo-list-item",
    }

    def search_repo(self, query: str, language: str = None) -> dict[str, Any]:
        """搜索 GitHub 仓库。

        Args:
            query: 搜索关键词
            language: 可选，编程语言过滤（如 "python"）

        Returns:
            {"status": "ok", "url": "...", "title": "...", "count": N}
        """
        r = self.runtime
        import time

        search_query = f"{query} language:{language}" if language else query
        r.navigate(f"https://github.com/search?q={urllib.parse.quote(search_query)}&type=repositories")
        time.sleep(1)
        r.wait_network_idle(timeout=8000)
        time.sleep(2)

        url_result = r.get_url() or {}
        title_result = r.get_title() or {}
        # API response is {"status": "ok", "result": {"url": "..."}}
        result_data = (url_result.get("result") or {}) if isinstance(url_result, dict) else {}
        title_data = (title_result.get("result") or {}) if isinstance(title_result, dict) else {}

        return {
            "status": "ok",
            "url": (result_data.get("url") or "") if isinstance(result_data, dict) else "",
            "title": (title_data.get("title") or "") if isinstance(title_data, dict) else "",
        }

    def get_repos(self, max_count: int = 10) -> dict[str, Any]:
        """获取仓库列表。

        GitHub 搜索结果通过 embeddedData JSON 注入。
        返回格式经过压缩，是给 Agent 的语义化观察结果。
        """
        r = self.runtime

        repos = r.eval(f"""
            () => {{
                const script = document.querySelector('script[data-target="react-app.embeddedData"]');
                if (!script) return JSON.stringify({{error: "no embedded data", repos: []}});
                try {{
                    const data = JSON.parse(script.textContent);
                    const results = data?.payload?.results || [];
                    return JSON.stringify({{
                        repos: results.slice(0, {max_count}).map(r => ({{
                            title: r.hl_name || '',
                            url: 'https://github.com/' + (r.repo?.repository?.owner_login || '') + '/' + (r.repo?.repository?.name || ''),
                            description: r.hl_trunc_description || '',
                            language: r.language || '',
                            stars: r.followers || 0,
                        }})),
                        count: results.length,
                    }});
                }} catch(e) {{
                    return JSON.stringify({{error: e.message, repos: []}});
                }}
            }}
        """)

        import json as _json
        url_result = r.get_url()
        # API response is {"status": "ok", "result": {"result": "..."}} - extract inner result
        raw = repos.get("result", {}) if isinstance(repos, dict) else {}
        inner = raw.get("result", "") if isinstance(raw, dict) else ""
        try:
            data = _json.loads(inner) if isinstance(inner, str) else inner
        except:
            data = {"repos": [], "count": 0}
        return {
            "repos": data.get("repos", []) if isinstance(data, dict) else [],
            "count": data.get("count", 0) if isinstance(data, dict) else 0,
            "page_url": url_result.get("url", "") if isinstance(url_result, dict) else "",
            "error": data.get("error") if isinstance(data, dict) else None,
        }


@skill("baidu.news")
class BaiduNewsSkill(Skill):
    """Baidu news semantic actions."""
    name = "baidu.news"
    description = "Baidu news portal semantic actions"

    def navigate_news(self) -> dict:
        """打开百度新闻首页。"""
        r = self.runtime
        r.navigate("https://news.baidu.com")
        r.wait_network_idle(timeout=10000)
        return {"status": "ok", "url": r.get_url()["url"]}

    def get_headlines(self, max_count: int = 20) -> dict[str, Any]:
        """获取新闻标题列表。"""
        r = self.runtime
        headlines = r.eval(f"""
            () => {{
                const items = document.querySelectorAll('.news-title');
                return Array.from(items).slice(0, {max_count}).map(el => el.innerText);
            }}
        """)
        return {"headlines": headlines if isinstance(headlines, list) else [], "count": len(headlines) if isinstance(headlines, list) else 0}