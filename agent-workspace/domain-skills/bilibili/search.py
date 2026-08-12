"""Bilibili video search helper for Browser Harness (视频搜索 + 列表).

Searches bilibili's public search page (search.bilibili.com/all) with a
keyword and optional ordering, then extracts the video result list with
positional order (which videos rank first/last), title, BV id, uploader,
view/danmaku counts, duration, and publish date.

Read-only; requires logged-in Agent Chrome (not strictly necessary for
search, but consistent with the rest of the bilibili skill).

UI facts (verified 2026-08-10) — search.bilibili.com/all:
- Result cards: `div.bili-video-card` (one per video, in page order).
- Title link: the `a` whose href contains `/video/BV` AND has no picture/img
  child (the cover link also matches `/video/BV` but contains an image).
- Uploader + date: `a.bili-video-card__info--owner`; the uploader name is its
  first child text node; date is `.bili-video-card__info--date`.
- Stats: `.bili-video-card__stats--item` spans — first = views, second =
  danmaku count. Duration: `.bili-video-card__stats__duration`.
- Ordering: URL param `order=` — default (综合) absent, `click` (最多播放),
  `pubdate` (最新发布), `dm` (最多弹幕), `stow` (最多收藏).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def goto_url(url: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...


ORDERS = {
    "default": "",  # 综合排序
    "click": "click",   # 最多播放
    "pubdate": "pubdate",  # 最新发布
    "dm": "dm",       # 最多弹幕
    "stow": "stow",    # 最多收藏
}


def search_videos(keyword, order="default", limit=15):
    """Search bilibili videos by keyword.

    Args:
      keyword: search term (URL-encoded by the caller or plain Chinese works
        after encoding here).
      order: one of ORDERS keys; controls the ranking of the returned list.
      limit: max results to return (page shows up to ~40).

    Returns list of dicts, in page order (first = top-ranked):
      {"title", "bvid", "url", "uploader", "view", "danmaku", "duration",
       "publish", "rank"}
    Raises RuntimeError if no results found.
    """
    from urllib.parse import quote

    url = "https://search.bilibili.com/all?keyword=" + quote(keyword)
    if ORDERS.get(order):
        url += "&order=" + ORDERS[order]
    goto_url(url)
    wait(3.5)

    data = js(
        "(() => {"
        "  const cards = Array.from(document.querySelectorAll('div.bili-video-card'));"
        "  const out = [];"
        "  let rank = 1;"
        "  for (const c of cards) {"
        "    const links = Array.from(c.querySelectorAll('a'));"
        "    const titleA = links.find(a => a.href.includes('/video/BV') && !a.querySelector('img, picture'));"
        "    const coverA = links.find(a => a.href.includes('/video/BV') && a.querySelector('img, picture'));"
        "    const owner = c.querySelector('a.bili-video-card__info--owner');"
        "    const dateEl = c.querySelector('.bili-video-card__info--date');"
        "    const stats = Array.from(c.querySelectorAll('.bili-video-card__stats--item')).map(s => s.textContent.trim());"
        "    const dur = c.querySelector('.bili-video-card__stats__duration');"
        "    if (!titleA) continue;"
        "    const bv = (titleA.href.match(/BV[0-9A-Za-z]+/) || [''])[0];"
        "    out.push({"
        "      rank: rank++,"
        "      title: titleA.textContent.trim(),"
        "      bvid: bv,"
        "      url: titleA.href,"
        "      uploader: owner ? owner.childNodes[0].textContent.trim() : '',"
        "      view: stats[0] || '',"
        "      danmaku: stats[1] || '',"
        "      duration: dur ? dur.textContent.trim() : '',"
        "      publish: dateEl ? dateEl.textContent.trim().replace(/^[·\\s]+/, '') : ''"
        "    });"
        "  }"
        "  return {posts: out};"
        "})()"
    )

    posts = data.get("posts") if isinstance(data, dict) else None
    if not posts:
        raise RuntimeError("No bilibili search results (login wall or stale selector)")
    return posts[:limit]


def run(keyword=None, order="default", limit=15):
    """CLI entry for exec(open(...).read()) under Browser Harness."""
    if not keyword:
        keyword = "白海豚"
    rows = search_videos(keyword, order=order, limit=limit)
    print("=== B站搜索: %s (排序=%s) 共%d条 ===" % (keyword, order, len(rows)))
    for e in rows:
        print("%d. %s | UP:%s | 播放:%s 弹幕:%s | %s | %s" % (
            e["rank"], e["title"][:40], e["uploader"], e["view"], e["danmaku"],
            e["duration"], e["bvid"]))
    return rows
