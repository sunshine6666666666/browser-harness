"""Zhihu hot-rank fetch helper for Browser Harness.

Fetches the top-N items of Zhihu's hot-ranking list (知乎热榜). Read-only;
never posts or mutates data.

Page: https://www.zhihu.com/hot. Renders `section.HotItem` items inside
`div.HotList-list` (30 visible). Each item: rank `.HotItem-rank`, title
`h2.HotItem-title`, href wrapping `a[href*="question"]`, heat
`.HotItem-metrics` (e.g. `544 万热度`). Class names are stable CSS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def goto_url(url: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...
    def page_info() -> dict[str, Any]: ...

HOT_URL = "https://www.zhihu.com/hot"
_ITEM_SEL = "section.HotItem"
_TITLE_SEL = ".HotItem-title"
_METRICS_SEL = ".HotItem-metrics"
_RANK_SEL = ".HotItem-rank"


def fetch_hot_rank(limit=15):
    """Navigate to the Zhihu hot page and return up to `limit` entries.

    Each entry: {"rank": str, "title": str, "heat": str, "href": str}.

    - limit clamps to the first N rows; pass None for all visible rows (30).
    - Raises RuntimeError if the list is missing or empty.
    """
    goto_url(HOT_URL)
    wait(2.5)

    rows = js(
        "(() => {"
        "  const items = Array.from(document.querySelectorAll('%s'));"
        "  const out = items.map(it => {"
        "    const titleEl = it.querySelector('%s');"
        "    const a = it.querySelector('a[href*=\"question\"]');"
        "    const metrics = it.querySelector('%s');"
        "    const rank = it.querySelector('%s');"
        "    let heat = '';"
        "    if (metrics) {"
        "      let m = metrics.cloneNode(true);"
        "      const action = m.querySelector('.HotItem-action');"
        "      if (action) action.remove();"
        "      heat = m.textContent.replace(/\\s+/g, ' ').trim();"
        "    }"
        "    return {rank: rank ? rank.textContent.trim() : '',"
        "            title: titleEl ? titleEl.textContent.trim() : '',"
        "            href: a ? a.href : '',"
        "            heat: heat};"
        "  });"
        "  return out;"
        "})()"
        % (_ITEM_SEL, _TITLE_SEL, _METRICS_SEL, _RANK_SEL)
    )

    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            "No hot-rank items found on Zhihu hot page (selector %s may be stale)"
            % _ITEM_SEL
        )

    return rows[:limit] if limit is not None else rows


def run(limit=15):
    """CLI entry for exec(open(...).read()) under Browser Harness.

    Prints `rank. title | heat | href` per entry.
    """
    entries = fetch_hot_rank(limit)
    for e in entries:
        print("%s. %s | %s | %s" % (e["rank"], e["title"], e["heat"], e["href"]))
    return entries
