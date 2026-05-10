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
        # Navigate to baidu.com first to set cookies
        r.navigate("https://www.baidu.com")
        r.wait_network_idle(timeout=10000)

        # Now navigate to search URL
        search_url = f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}"
        r.navigate(search_url)
        r.wait_network_idle(timeout=15000)

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