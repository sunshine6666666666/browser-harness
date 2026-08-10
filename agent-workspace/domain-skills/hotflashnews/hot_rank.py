"""HotFlashNews hot-rank fetch helper for Browser Harness.

Fetches top-N items from the aggregated hot rankings on
https://hotflashnews.com/ (全网热榜). Read-only; never posts or mutates data.

Supported platforms (tab labels on the page): douyin 抖音, baidu 百度, 36kr
36Kr, it IT之家, penpai 澎湃, toutiao 头条. Weibo 微博 and Zhihu 知乎 are NOT
implemented here because devkeeper has first-party domain skills for those
sites; this skill is the fallback / cross-validation source for the others.

Data shape: rank + title only. There is NO heat value in this source.

UI facts (verified 2026-08-10): the 全网热榜 card tab bar is a sticky
container holding platform buttons; clicking swaps the ranked list below
(client-side state, no URL change). Each rank item is
`a.flex.gap-3.items-start...` with the rank in its first child div and the
title in `div.text-lg.font-medium`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def goto_url(url: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...
    def page_info() -> dict[str, Any]: ...

HOME_URL = "https://hotflashnews.com/"

# category key -> platform tab label
CATEGORY_TABS = {
    "douyin": "抖音",
    "baidu": "百度",
    "36kr": "36Kr",
    "it": "IT之家",
    "penpai": "澎湃",
    "toutiao": "头条",
}

_ITEM_SEL = "a.flex.gap-3.items-start"
_TITLE_SEL = "div.text-lg.font-medium"
_RANK_SEL = "div.w-5.h-5"


def _click_platform_tab(label):
    """Click the platform tab inside the 全网热榜 card. Returns True if clicked."""
    return js(
        "(() => {"
        "  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);"
        "  let node, anchor = null;"
        "  while (node = walker.nextNode()) {"
        "    if (node.textContent.trim() === '全网热榜') { anchor = node.parentElement; break; }"
        "  }"
        "  if (!anchor) return false;"
        "  let container = anchor;"
        "  for (let i=0; i<5 && container; i++) {"
        "    const btns = Array.from(container.querySelectorAll('button'));"
        "    const hit = btns.find(b => (b.textContent||'').trim() === %r);"
        "    if (hit) { hit.click(); return true; }"
        "    container = container.parentElement;"
        "  }"
        "  return false;"
        "})()" % label
    )


def fetch_hot_rank(category="douyin", limit=15):
    """Navigate to the homepage, switch to the platform tab, return top-N rows.

    Each entry: {"rank": str, "title": str, "href": str} (no heat field —
    this source provides rank + title only).

    - category must be a key in CATEGORY_TABS.
    - limit clamps to the first N rows; pass None for all visible.
    - Raises RuntimeError if the tab is missing or the list is empty.
    """
    if category not in CATEGORY_TABS:
        raise ValueError(
            "category must be one of %s, got %r" % (list(CATEGORY_TABS), category)
        )
    label = CATEGORY_TABS[category]

    goto_url(HOME_URL)
    wait(2.5)

    clicked = _click_platform_tab(label)
    if not clicked:
        raise RuntimeError(
            "Platform tab '%s' not found in the 全网热榜 card" % label
        )
    wait(1.5)

    rows = js(
        "(() => {"
        "  const items = Array.from(document.querySelectorAll('%s'));"
        "  const out = items.map(it => {"
        "    const titleEl = it.querySelector('%s');"
        "    const rankEl = it.querySelector('%s');"
        "    return {rank: rankEl ? rankEl.textContent.trim() : '',"
        "            title: titleEl ? titleEl.textContent.trim() : '',"
        "            href: it.href || ''};"
        "  });"
        "  return out;"
        "})()"
        % (_ITEM_SEL, _TITLE_SEL, _RANK_SEL)
    )

    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            "No hot-rank items found for platform '%s' (selector %s may be stale)"
            % (label, _ITEM_SEL)
        )

    return rows[:limit] if limit is not None else rows


def run(category="douyin", limit=15):
    """CLI entry for exec(open(...).read()) under Browser Harness.

    Prints `rank. title | href` per entry.
    """
    entries = fetch_hot_rank(category, limit)
    for e in entries:
        print("%s. %s | %s" % (e["rank"], e["title"], e["href"]))
    return entries
