"""Reddit Browser Tier-1 smoke for last30days integration experiments.

Runs inside browser-harness (`browser-harness -c 'exec(open(...).read())'`).
Non-core helper: does not modify last30days upstream code. It validates whether
Agent Chrome logged-in Reddit can provide normalized Reddit items for a query.
"""

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def new_tab(url: str = "about:blank") -> str: ...
    def wait_for_load(timeout: float = 15.0) -> bool: ...
    def wait(seconds: float = 1.0) -> None: ...
    def scroll(x: int, y: int, dy: int = -300, dx: int = 0) -> None: ...
    def cdp(method: str, session_id: str | None = None, **params: Any) -> dict: ...


def _extract_search_posts(limit=8):
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const abs = href => href ? new URL(href, location.origin).href : '';
      const out = [];
      const seen = new Set();
      const toNum = s => {
        s = String(s || '').replace(/,/g,'').trim().toLowerCase();
        if(!s) return null;
        if(s.includes('万')) return Math.round(parseFloat(s) * 10000);
        if(s.includes('千')) return Math.round(parseFloat(s) * 1000);
        if(s.endsWith('k')) return Math.round(parseFloat(s) * 1000);
        const n = parseFloat(s); return Number.isFinite(n) ? Math.round(n) : null;
      };
      const pushItem = (item) => {
        if(!item.title || !item.url || seen.has(item.url)) return;
        seen.add(item.url); out.push(item);
      };
      for (const p of document.querySelectorAll('shreddit-post')) {
        const title = norm(p.getAttribute('post-title')) || norm((p.querySelector('[slot="title"], h1, h2, h3') || {}).innerText);
        const permalink = p.getAttribute('permalink') || (p.querySelector('a[href*="/comments/"]') || {}).getAttribute?.('href') || '';
        if (!title || !permalink || !permalink.includes('/comments/')) continue;
        const postId = p.getAttribute('post-id') || (permalink.match(/\/comments\/([^/]+)/) || [])[1] || '';
        const subreddit = p.getAttribute('subreddit-name') || (permalink.match(/\/r\/([^/]+)/) || [])[1] || '';
        const author = p.getAttribute('author') || norm((p.querySelector('[slot="authorName"] a, a[data-testid="post_author_link"]') || {}).innerText);
        const scoreAttr = p.getAttribute('score');
        const commentsAttr = p.getAttribute('comment-count');
        const created = p.getAttribute('created-timestamp') || '';
        pushItem({id: postId, title, url: abs(permalink), subreddit, author,
          score: scoreAttr === null ? null : Number(scoreAttr),
          num_comments: commentsAttr === null ? null : Number(commentsAttr),
          created_at: created, source_layer: 'browser_reddit_search_shreddit'});
        if (out.length >= %d) break;
      }
      // Search results page currently does not render <shreddit-post>; it exposes
      // stable /comments/ links and localized visible text. Fall back to anchors.
      if (out.length < %d) {
        for (const a of document.querySelectorAll('a[href*="/comments/"]')) {
          const href = abs(a.getAttribute('href'));
          if(!href || seen.has(href)) continue;
          const title = norm(a.innerText || a.textContent);
          if(!title || title.length < 4) continue;
          let box = a;
          for(let i=0; i<8 && box && box.parentElement; i++){
            box = box.parentElement;
            const t = norm(box.innerText);
            if((/r\//.test(t) || /票|comments?|条评论/i.test(t)) && t.length > title.length) break;
          }
          const txt = norm(box && box.innerText);
          const sub = (href.match(/\/r\/([^/]+)/) || [])[1] || '';
          const postId = (href.match(/\/comments\/([^/]+)/) || [])[1] || '';
          const scoreM = txt.match(/([\d.,]+\s*[万千kK]?)\s*(?:票|upvotes?)/i);
          const commM = txt.match(/([\d.,]+\s*[万千kK]?)\s*(?:条评论|comments?)/i);
          pushItem({id: postId, title, url: href, subreddit: sub, author: '',
            score: scoreM ? toNum(scoreM[1]) : null,
            num_comments: commM ? toNum(commM[1]) : null,
            created_at: '', source_layer: 'browser_reddit_search_anchor'});
          if(out.length >= %d) break;
        }
      }
      const loginWall = !!document.querySelector('a[href*="/login"], [data-testid="login-button"]');
      const ageGate = !!document.querySelector('[data-testid="nsfw-gate"], shreddit-interstitial');
      return {items: out, loginWall, ageGate, url: location.href, title: document.title};
    })()
    """ % (limit, limit, limit))


def _extract_thread(limit=8):
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const p = document.querySelector('shreddit-post');
      const comments = [];
      for (const c of document.querySelectorAll('shreddit-comment[depth="0"], shreddit-comment')) {
        const bodyEl = c.querySelector('[slot="comment"] .md, [slot="comment"]');
        const body = norm(bodyEl && bodyEl.innerText);
        if (!body) continue;
        comments.push({
          author: c.getAttribute('author') || '',
          score: c.getAttribute('score') === null ? null : Number(c.getAttribute('score')),
          created_at: c.getAttribute('created-timestamp') || '',
          excerpt: body.slice(0, 280),
          url: c.getAttribute('permalink') ? new URL(c.getAttribute('permalink'), location.origin).href : '',
        });
        if (comments.length >= %d) break;
      }
      return {
        url: location.href,
        title: p ? (norm(p.getAttribute('post-title')) || norm((p.querySelector('h1, [slot="title"]') || {}).innerText)) : document.title,
        body: p ? norm(((p.querySelector('[slot="text-body"] .md, [slot="text-body"]') || {}).innerText)) : '',
        comments,
        comment_count_dom: document.querySelectorAll('shreddit-comment').length,
      };
    })()
    """ % limit)


def _date_from_created(value: Any) -> str | None:
    """Convert Reddit DOM timestamp variants to last30days YYYY-MM-DD or None."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).date().isoformat()
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return datetime.fromtimestamp(float(text), tz=timezone.utc).date().isoformat()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _comment_insights(comments: list[dict[str, Any]], limit: int = 7) -> list[str]:
    insights: list[str] = []
    for comment in comments[:limit]:
        excerpt = str(comment.get("excerpt") or comment.get("body") or "").strip()
        if excerpt:
            insights.append(excerpt[:240])
    return insights


def _to_last30days_reddit_item(
    item: dict[str, Any],
    thread: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map Browser Reddit extraction to last30days raw Reddit item shape.

    This intentionally matches the dict shape consumed by
    last30days `normalize._normalize_reddit`: id/title/url/subreddit/date,
    engagement/selftext/top_comments/comment_insights/relevance/why_relevant.
    Browser-only fields are preserved under metadata.browser_raw so the adapter
    does not silently lose data while still remaining last30days-compatible.
    """
    comments = list((thread or {}).get("comments") or [])
    top_comments = [
        {
            "score": c.get("score") if c.get("score") is not None else 0,
            "date": _date_from_created(c.get("created_at")),
            "excerpt": str(c.get("excerpt") or c.get("body") or "").strip(),
            "url": str(c.get("url") or ""),
            "author": str(c.get("author") or ""),
        }
        for c in comments
        if str(c.get("excerpt") or c.get("body") or "").strip()
    ]
    score = item.get("score")
    num_comments = item.get("num_comments")
    engagement = {
        key: value
        for key, value in {
            "score": score,
            "num_comments": num_comments,
        }.items()
        if value is not None
    }
    browser_raw = {
        key: item.get(key)
        for key in ["created_at", "source_layer", "author", "score", "num_comments"]
        if item.get(key) not in (None, "")
    }
    return {
        "id": str(item.get("id") or ""),
        "title": str(item.get("title") or ""),
        "url": str(item.get("url") or ""),
        "subreddit": str(item.get("subreddit") or ""),
        "author": str(item.get("author") or ""),
        "date": _date_from_created(item.get("created_at")),
        "engagement": engagement,
        "selftext": str((thread or {}).get("body") or ""),
        "top_comments": top_comments,
        "comment_insights": _comment_insights(top_comments),
        "relevance": 0.5,
        "why_relevant": "Collected from logged-in Reddit browser search; relevance scored downstream by last30days.",
        "metadata": {
            "adapter": "browser_reddit_tier1",
            "source_layer": item.get("source_layer") or "browser_reddit_search",
            "browser_raw": browser_raw,
            "thread_url": (thread or {}).get("url") or "",
            "thread_comment_count_dom": (thread or {}).get("comment_count_dom"),
        },
    }


def _build_last30days_payload(result: dict[str, Any]) -> dict[str, Any]:
    search_items = list((result.get("search") or {}).get("items") or [])
    thread = result.get("thread") or {}
    thread_url = str(thread.get("url") or "")
    items: list[dict[str, Any]] = []
    for item in search_items:
        matched_thread = thread if thread_url and str(item.get("url") or "") == thread_url else None
        items.append(_to_last30days_reddit_item(item, matched_thread))
    required = ["id", "title", "url", "subreddit", "engagement", "top_comments", "comment_insights"]
    missing_by_index = {
        idx: [field for field in required if normalized.get(field) in (None, "", {})]
        for idx, normalized in enumerate(items)
    }
    return {
        "source": "reddit",
        "adapter": "browser_reddit_tier1",
        "compatible_with": "last30days raw reddit items -> normalize._normalize_reddit",
        "items": items,
        "items_by_source": {"reddit": items},
        "missing_required_by_index": {idx: fields for idx, fields in missing_by_index.items() if fields},
        "notes": [
            "`date` may be null on Reddit search-anchor results; last30days treats this as low date confidence.",
            "Only the opened top thread is comment-enriched in this smoke; later production adapter should enrich top-N survivors.",
        ],
    }


def run(query="OpenAI", limit=8, close_tabs=True):
    search_tid = None
    thread_tid = None
    result = {"query": query, "ok": False, "search": {}, "thread": {}, "closed_tabs": []}
    try:
        search_url = f"https://www.reddit.com/search/?q={quote_plus(query)}&sort=relevance&t=month"
        search_tid = new_tab(search_url)
        wait_for_load()
        wait(4.0)
        # Hydrate / lazy load cards.
        for _ in range(3):
            scroll(500, 700, dy=1200)
            wait(0.8)
        search = _extract_search_posts(limit=limit)
        result["search"] = search
        items = search.get("items") or []
        if items:
            thread_tid = new_tab(items[0]["url"])
            wait_for_load()
            wait(3.0)
            for _ in range(4):
                scroll(500, 700, dy=1600)
                wait(0.9)
            result["thread"] = _extract_thread(limit=limit)
        result["ok"] = bool(items)
        result["last30days"] = _build_last30days_payload(result)
        return result
    finally:
        if close_tabs:
            # Close newest/owned tabs. Best effort; do not throw from cleanup.
            for tid in [thread_tid, search_tid]:
                if tid:
                    try:
                        cdp("Target.closeTarget", targetId=tid)
                        result["closed_tabs"].append(tid)
                    except Exception as exc:
                        result.setdefault("cleanup_errors", []).append(str(exc))


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
elif "new_tab" in globals():
    print(json.dumps(run(), ensure_ascii=False, indent=2))
