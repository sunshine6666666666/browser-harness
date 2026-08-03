"""X Browser search adapter for last30days.

Runs inside browser-harness (`browser-harness -c 'exec(open(...).read())'`).
Read-only collector: searches logged-in Agent Chrome X pages and emits raw X dicts
compatible with last30days normalize._normalize_x.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def new_tab(url: str = "about:blank") -> str: ...
    def goto_url(url: str) -> None: ...
    def wait_for_load(timeout: float = 15.0) -> bool: ...
    def wait(seconds: float = 1.0) -> None: ...


def _extract_search_articles(limit: int = 10) -> dict[str, Any]:
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const articles = [];
      const seen = new Set();
      for (const a of document.querySelectorAll('article')) {
        const text = norm(a.innerText || a.textContent || '');
        const links = Array.from(a.querySelectorAll('a[href*="/status/"]'))
          .map(x => x.href)
          .filter(Boolean);
        const href = links.find(h => /\/status\/\d+/.test(h)) || '';
        if (!text || !href || seen.has(href)) continue;
        seen.add(href);
        const authorLinks = Array.from(a.querySelectorAll('a[href]'))
          .map(x => x.href)
          .filter(h => /^https:\/\/x\.com\/[^/?#]+$/.test(h) && !/\/i\//.test(h));
        const time = a.querySelector('time');
        articles.push({
          text: text.slice(0, 2200),
          url: href,
          author_url: authorLinks[0] || '',
          datetime: time ? (time.getAttribute('datetime') || '') : '',
          visible_time: time ? norm(time.innerText) : '',
          has_like_button: !!a.querySelector('[data-testid="like"]'),
          has_reply_button: !!a.querySelector('[data-testid="reply"]'),
        });
        if (articles.length >= %d) break;
      }
      const body = (document.body && (document.body.innerText || document.body.textContent)) || '';
      return {
        url: location.href,
        title: document.title,
        items: articles,
        login_wall: /Log in|Sign in|登录|登入/.test(body) && articles.length === 0,
        body_head: body.slice(0, 400),
      };
    })()
    """ % limit)


def _extract_status() -> dict[str, Any]:
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const a = document.querySelector('article');
      if (!a) return {url: location.href, found: false};
      const links = Array.from(a.querySelectorAll('a[href]')).map(x => x.href).filter(Boolean);
      const time = a.querySelector('time');
      const authorLink = links.find(h => /^https:\/\/x\.com\/[^/?#]+$/.test(h) && !/\/i\//.test(h)) || '';
      return {
        url: location.href,
        found: true,
        text: norm(a.innerText || a.textContent || '').slice(0, 2600),
        author_url: authorLink,
        datetime: time ? (time.getAttribute('datetime') || '') : '',
        visible_time: time ? norm(time.innerText) : '',
        status_links: links.filter(h => /\/status\/\d+/.test(h)).slice(0, 8),
      };
    })()
    """)


def _handle_from_url(url: str) -> str:
    match = re.search(r"https://x\.com/([^/?#]+)", str(url or ""))
    if not match:
        return ""
    handle = match.group(1)
    if handle in {"i", "search", "home", "intent"}:
        return ""
    return handle


def _handle_from_text(text: str) -> str:
    match = re.search(r"@([A-Za-z0-9_]{1,15})", text or "")
    return match.group(1) if match else ""


def _date_from_iso(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _tweet_id(url: str) -> str:
    match = re.search(r"/status/(\d+)", str(url or ""))
    return match.group(1) if match else ""


def _clean_text(text: str, handle: str = "") -> str:
    """Best-effort cleanup of localized X article chrome without overfitting."""
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    drop_exact = {"翻译自 英语", "翻译自 日语", "显示原文", "评价此翻译：", "相关"}
    cleaned = []
    for line in lines:
        if line in drop_exact:
            continue
        if line.startswith("来自 "):
            continue
        cleaned.append(line)
    # Keep author/header too; downstream can still use it as context. Cap length.
    return "\n".join(cleaned)[:700]


def _visible_engagement(text: str) -> dict[str, Any]:
    # X's localized DOM often gives unlabeled counters. Preserve them as text
    # instead of pretending they are exact likes/reposts/replies.
    nums = re.findall(r"(?<![A-Za-z0-9_])(?:\d+(?:[.,]\d+)?\s*[万千kK]?)(?![A-Za-z0-9_])", text or "")
    return {"visible_counters": nums[-6:], "source": "x_browser_visible_text"}


def _to_last30days_x_item(item: dict[str, Any], status: dict[str, Any] | None = None, index: int = 0) -> dict[str, Any]:
    status = status or {}
    url = str(status.get("url") or item.get("url") or "")
    raw_text = str(status.get("text") or item.get("text") or "")
    author = _handle_from_url(status.get("author_url") or item.get("author_url") or "") or _handle_from_text(raw_text)
    return {
        "id": _tweet_id(url) or f"XBROWSER{index + 1}",
        "text": _clean_text(raw_text, author),
        "url": url,
        "author_handle": author,
        "date": _date_from_iso(status.get("datetime") or item.get("datetime")),
        "engagement": _visible_engagement(raw_text),
        "why_relevant": "Collected from logged-in X browser search; relevance scored downstream by last30days.",
        "relevance": 0.5,
        "metadata": {
            "adapter": "browser_x_search",
            "search_url": item.get("search_url") or "",
            "visible_time": status.get("visible_time") or item.get("visible_time") or "",
            "status_enriched": bool(status.get("found")),
        },
    }


def _build_last30days_payload(result: dict[str, Any]) -> dict[str, Any]:
    search_items = list((result.get("search") or {}).get("items") or [])
    status_by_url = result.get("status_by_url") or {}
    items = [
        _to_last30days_x_item(item, status_by_url.get(item.get("url") or ""), index=i)
        for i, item in enumerate(search_items)
    ]
    return {
        "source": "x",
        "adapter": "browser_x_search",
        "compatible_with": "last30days raw x items -> normalize._normalize_x",
        "items": items,
        "items_by_source": {"x": items},
        "notes": [
            "X search-page counters are preserved as visible text unless opened status pages expose exact labels.",
            "Status enrichment is limited to top-N to avoid excessive browser tab churn.",
        ],
    }


def run(query: str = "OpenAI Codex", limit: int = 10, enrich_limit: int = 3, close_tabs: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"query": query, "ok": False, "search": {}, "status_by_url": {}}
    search_url = f"https://x.com/search?q={quote_plus(query)}&src=typed_query"
    new_tab(search_url)
    wait_for_load()
    wait(4.0)
    for _ in range(3):
        js("window.scrollBy(0, 900)")
        wait(1.0)
    search = _extract_search_articles(limit=limit)
    for item in search.get("items") or []:
        item["search_url"] = search_url
    result["search"] = search

    for item in list(search.get("items") or [])[: max(0, enrich_limit)]:
        url = item.get("url")
        if not url:
            continue
        new_tab(url)
        wait_for_load()
        wait(3.0)
        result["status_by_url"][url] = _extract_status()

    result["ok"] = bool((search.get("items") or []))
    result["last30days"] = _build_last30days_payload(result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
