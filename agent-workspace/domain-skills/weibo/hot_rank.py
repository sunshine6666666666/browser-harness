"""Weibo hot-rank fetch helper for Browser Harness.

Fetches the top-N items of Weibo's hot-search ranking for a category
(social 社会 / entertainment 文娱). Read-only; never posts or mutates data.

Requires a logged-in Weibo session in the attached Chrome, otherwise the
category pages redirect to /newlogin and the list body is empty.

UI facts (verified 2026-08-10): rank list renders in `div._item_13qc7_56`
items; each has rank `[class*="_ranknum"]`, title `a._tit_13qc7_65` (href is
the s.weibo.com search link), heat `._num_13qc7_85 span`. Class names are
hashed and may change; see hot_rank.md for fallbacks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def goto_url(url: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...
    def page_info() -> dict[str, Any]: ...

VALID_CATEGORIES = ("social", "entertainment")
_CATEGORY_URLS = {
    "social": "https://weibo.com/hot/social",
    "entertainment": "https://weibo.com/hot/entertainment",
}
_ITEM_SEL = "div._item_13qc7_56"
_RANK_SEL = '[class*="_ranknum"]'
_TITLE_SEL = "a._tit_13qc7_65"
_HEAT_SEL = "._num_13qc7_85 span"


def _page_text():
    """Return current page body text (for redirect/login detection)."""
    try:
        return js("document.body ? document.body.innerText.slice(0, 300) : ''")
    except Exception:
        return ""


def _is_login_wall(url, text):
    """Detect the unauthenticated redirect (newlogin) or empty list."""
    return "newlogin" in url or "登录/注册" in text and "_item_13qc7_56" not in js("document.body.innerHTML")


def fetch_hot_rank(category="social", limit=15):
    """Navigate to the category hot-rank page and return up to `limit` entries.

    Each entry: {"rank": str, "title": str, "heat": str, "href": str}.

    - category must be 'social' or 'entertainment'.
    - limit clamps to the first N rows; pass None for all visible rows.
    - Raises RuntimeError if the page is a login wall or the list is missing.
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(
            "category must be one of %s, got %r" % (VALID_CATEGORIES, category)
        )
    url = _CATEGORY_URLS[category]
    goto_url(url)

    # Wait briefly for the Vue list to hydrate. The page is client-rendered;
    # a short fixed wait is cheaper than polling for a hashed selector we
    # already know, and the heat values can settle slightly after mount.
    wait(2.5)

    info = page_info()
    text = _page_text()
    if "newlogin" in info["url"] or (text and "登录/注册" in text and _ITEM_SEL not in js("document.body.innerHTML")):
        raise RuntimeError(
            "Weibo hot rank needs a logged-in session: redirected to %s"
            % info["url"]
        )

    rows = js(
        "(() => {"
        "  const items = Array.from(document.querySelectorAll('%s'));"
        "  const out = items.map(it => {"
        "    const tit = it.querySelector('%s');"
        "    const num = it.querySelector('%s');"
        "    const rank = it.querySelector('%s');"
        "    return {rank: rank ? rank.textContent.trim() : '',"
        "            title: tit ? tit.textContent.trim() : '',"
        "            href: tit ? tit.href : '',"
        "            heat: num ? num.textContent.trim() : ''};"
        "  });"
        "  return out;"
        "})()"
        % (_ITEM_SEL, _TITLE_SEL, _HEAT_SEL, _RANK_SEL)
    )

    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            "No hot-rank items found for category '%s' (selector %s may be stale)"
            % (category, _ITEM_SEL)
        )

    return rows[:limit] if limit is not None else rows


def run(category="social", limit=15):
    """CLI entry for exec(open(...).read()) under Browser Harness.

    Prints `rank. title | heat | href` per entry.
    """
    entries = fetch_hot_rank(category, limit)
    for e in entries:
        print("%s. %s | %s | %s" % (e["rank"], e["title"], e["heat"], e["href"]))
    return entries
