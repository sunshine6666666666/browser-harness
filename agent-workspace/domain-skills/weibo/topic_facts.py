"""Weibo topic-facts helper for Browser Harness (底层素材提取工具).

Opens a Weibo topic search page (from a hot-rank entry href) and extracts the
raw material needed to judge a hot topic — NOT a summary. Downstream
verification/辨证 consumes these primitives:

- topic statistics (阅读量/讨论量)
- per-post: author, blue-V/orange-V verification, official-account type,
  time, source device, full body text, image URLs, interaction counts
  (转发/评论/点赞), canonical post URL

Pagination: s.weibo.com search results paginate via `&page=N` (约 20 posts /
page). This helper keeps paging until it has covered all official/media
accounts (no new official posts for `stale_pages` consecutive pages) or until
the safety cap. It never summarizes; text/images are the material.

Read-only; never posts or mutates data. Requires logged-in Agent Chrome.

UI facts (verified 2026-08-10) — s.weibo.com search results page:
- Card unit: `div.card-wrap`; the first one is the compose box
  (`card-sender`) and MUST be skipped.
- Topic stats: `div.msg div.info div.total` text (e.g. 阅读量2818.5万 讨论量5567).
- Post: `div.card-feed` inside card-wrap:
  - author: `a.name` (nick-name attr)
  - blue V: `.woo-icon--vblue` (官方认证), orange V: `.woo-icon--vorange`
  - time: `.from a[href*="weibo.com/"]` text
  - source: `.from a[href*="app.weibo.com"]` text
  - body: `p.txt`
  - images: `[node-type="feed_list_media_prev"] img` (src or data-src)
- Interactions: `div.card-act li a` texts in the SAME card-wrap
  (space-separated numbers: 转发 评论 点赞).
- Post URL: `.from a[href*="weibo.com/"]` → https://weibo.com/<uid>/<mid>
- Pagination: `.m-page a` links `&page=N`.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def goto_url(url: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...
    def page_info() -> dict[str, Any]: ...

# Official media / government / institution account name markers (官媒判断).
# Any verified (blue-V) account whose name contains one of these is treated as
# an official media/institution source. Extend as needed.
OFFICIAL_MARKERS = [
    "人民日报", "央视", "新华社", "警方", "公安", "检察", "法院", "政府",
    "应急管理", "气象", "中国政府网", "新华视点", "半月谈", "发布",
]

MEDIA_MARKERS = [
    "新闻", "日报", "晚报", "都市报", "周刊", "时报", "电视台", "广播",
    "澎湃", "新华网", "中新网", "央广", "法治", "报业", "融媒体",
]

# Known official sources whose account names do not expose a general marker.
OFFICIAL_EXACT = {
    "平安武昌", "央视新闻", "人民日报", "新华社", "中国政府网",
    "新华视点", "北京发布", "上海发布",
}

VALID_SORTS = ("general", "hot", "time")


def _topic_url_for_sort(topic_url, sort="general", page=None):
    """Build a Weibo search URL for the requested UI sort and page.

    Weibo implements the three visible sorts as separate paths rather than by
    honoring ``xsort=hot`` on ``/weibo``. Keep unrelated query parameters,
    normalize mode-specific ones, and add ``page`` only when requested.
    """
    if sort not in VALID_SORTS:
        raise ValueError("sort must be one of: %s" % ", ".join(VALID_SORTS))

    parts = urlsplit(topic_url)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key in ("page", "xsort", "suball", "tw", "rd", "Refer"):
        params.pop(key, None)

    if sort == "hot":
        path = "/hot"
        params.update({
            "xsort": "hot", "suball": "1", "tw": "hotweibo",
            "Refer": "weibo_hot",
        })
    elif sort == "time":
        path = "/realtime"
        params.update({
            "rd": "realtime", "tw": "realtime", "Refer": "weibo_realtime",
        })
    else:
        path = "/weibo"
        params["Refer"] = "weibo_weibo"

    if page is not None:
        params["page"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(params), ""))


def _topic_from_url(url):
    """Extract and URL-decode the topic query from a s.weibo.com URL."""
    m = re.search(r"[?&]q=([^&]+)", url or "")
    if not m:
        return ""
    return unquote(m.group(1)).strip("#")


def _classify_official(author, verify_type):
    """Classify source type without equating blue-V with official media.

    Returns: 'official', 'media', 'verified_org', 'verified_person', or ''.
    """
    if not author:
        return ""
    name = author.strip()
    if name in OFFICIAL_EXACT or (
        verify_type == "blue" and any(m in name for m in OFFICIAL_MARKERS)
    ):
        return "official"
    if verify_type == "blue" and any(m in name for m in MEDIA_MARKERS):
        return "media"
    if verify_type == "blue":
        return "verified_org"
    if verify_type == "orange":
        return "verified_person"
    return ""


def _extract_posts_js():
    """Return a JS expression string that extracts posts from current page."""
    return (
        "(() => {"
        "  const wraps = Array.from(document.querySelectorAll('div.card-wrap'));"
        "  const posts = [];"
        "  for (const w of wraps) {"
        "    if (w.querySelector('.card-sender')) continue;"
        "    const f = w.querySelector('div.card-feed');"
        "    if (!f) continue;"
        "    const nameEl = f.querySelector('a.name');"
        "    const fromEl = f.querySelector('.from');"
        "    const postLink = fromEl ? fromEl.querySelector('a[href*=\"weibo.com/\"]') : null;"
        "    const srcEl = f.querySelector('.from a[href*=\"app.weibo.com\"]');"
        "    const txtEl = f.querySelector('p.txt');"
        "    const vBlue = f.querySelector('.woo-icon--vblue');"
        "    const vOrange = f.querySelector('.woo-icon--vorange');"
        "    const media = f.querySelector('[node-type=\"feed_list_media_prev\"]');"
        "    const thumbs = media ? Array.from(media.querySelectorAll('img')).map(i => i.getAttribute('src') || i.getAttribute('data-src') || '').filter(Boolean) : [];"
        "    const imgs = thumbs.map(u => u.replace('/orj360/', '/large/').replace('/thumb150/', '/large/'));"
        "    const videos = Array.from(f.querySelectorAll('a[href*=\"video.weibo.com\"], video source, video')).map(v => v.href || v.src || '').filter(Boolean);"
        "    const actEl = w.querySelector('div.card-act');"
        "    const acts = actEl ? actEl.textContent.replace(/\\s+/g,' ').trim().split(/\\s+/).slice(0,3) : [];"
        "    let time = '';"
        "    if (postLink) time = postLink.textContent.replace(/\\s+/g,' ').trim();"
        "    let source = '';"
        "    if (srcEl) source = srcEl.textContent.trim();"
        "    posts.push({"
        "      author: nameEl ? (nameEl.getAttribute('nick-name') || nameEl.textContent.trim()) : '',"
        "      verified: !!(vBlue || vOrange),"
        "      verify_type: vBlue ? 'blue' : (vOrange ? 'orange' : ''),"
        "      time: time,"
        "      source: source,"
        "      text: txtEl ? txtEl.textContent.replace(/\\s+/g,' ').trim() : '',"
        "      image_thumbnails: thumbs,"
        "      images: imgs,"
        "      videos: videos,"
        "      acts: acts,"
        "      url: postLink ? 'https:' + postLink.getAttribute('href') : ''"
        "    });"
        "  }"
        "  return {posts: posts};"
        "})()"
    )


def fetch_topic_facts(topic_url, max_pages=5, stale_pages=None, limit=None,
                      sort="general"):
    """Open a Weibo topic search URL and extract raw post material, paging.

    Args:
      topic_url: s.weibo.com search URL (from a hot-rank entry href).
      max_pages: safety cap on pages to fetch (default 5, ~100 posts).
      stale_pages: optional early-stop threshold after consecutive pages with
        no new official/media post. Default None scans all max_pages because
        later pages can still contain additional fact sources.
      limit: optional max posts in the final list; None returns all collected.
      sort: general (default), hot, or time. These map to Weibo's 综合、热门、
        实时 search tabs. Hot and time pagination use the site's live URLs.

    Returns:
    {
      "topic": str, "stats": str,
      "posts": [ {author, verified, verify_type, official, time, source,
                  text, images, image_thumbnails, videos, acts, url, page} ... ],
      "page_count": int,
    }

    `official` is one of: official / media / verified_org /
    verified_person / ''. Blue-V alone is never treated as official media.
    Posts are in page order; no reordering.
    """
    base_url = _topic_url_for_sort(topic_url, sort=sort)
    page = 1
    processed_pages = 0
    all_posts = []
    seen_urls = set()
    no_official_streak = 0
    last_stats = ""

    while page <= max_pages:
        url = base_url if page == 1 else _topic_url_for_sort(
            base_url, sort=sort, page=page
        )
        goto_url(url)
        wait(2.5)

        data = js(
            "(() => {"
            "  const statsEl = document.querySelector('div.msg div.info div.total');"
            "  const stats = statsEl ? statsEl.textContent.replace(/\\s+/g,' ').trim() : '';"
            "  const extracted = %s;"
            "  return {stats: stats, posts: extracted.posts};"
            "})()" % _extract_posts_js()
        )

        if not isinstance(data, dict) or not data.get("posts"):
            break  # no more content (end of pagination or login wall)

        processed_pages += 1
        if data.get("stats"):
            last_stats = data["stats"]

        page_fact_sources = 0
        for p in data["posts"]:
            source_type = _classify_official(
                p.get("author", ""), p.get("verify_type", "")
            )
            p["official"] = source_type  # compatibility classification string
            p["source_type"] = source_type or "ordinary"
            p["is_official"] = source_type == "official"
            p["is_media"] = source_type == "media"
            p["page"] = page
            post_key = p.get("url") or (
                p.get("author", "") + "|" + p.get("text", "")[:120]
            )
            if post_key in seen_urls:
                continue
            seen_urls.add(post_key)
            all_posts.append(p)
            if p["official"] in ("official", "media"):
                page_fact_sources += 1

        if page_fact_sources == 0:
            no_official_streak += 1
            if stale_pages is not None and no_official_streak >= stale_pages:
                break
        else:
            no_official_streak = 0

        page += 1

    if not all_posts:
        raise RuntimeError(
            "No Weibo topic posts found (login wall or stale selector)"
        )

    return {
        "topic": _topic_from_url(topic_url),
        "stats": last_stats,
        "posts": all_posts if limit is None else all_posts[:limit],
        "page_count": processed_pages,
        "sort": sort,
    }


def run(topic_url=None, max_pages=5, limit=None, sort="general"):
    """CLI entry for exec(open(...).read()) under Browser Harness.

    Prints topic stats and raw post material (page order).
    """
    if not topic_url:
        import hot_rank  # same-dir sibling for fallback topic source
        rows = hot_rank.fetch_hot_rank("social", 1)
        topic_url = rows[0]["href"]
    facts = fetch_topic_facts(
        topic_url, max_pages=max_pages, limit=limit, sort=sort
    )
    print("=== 话题: %s ===" % facts["topic"])
    print("统计: %s | 抓取页数: %d | 帖子总数: %d" % (
        facts["stats"], facts["page_count"], len(facts["posts"])))
    for i, p in enumerate(facts["posts"], 1):
        v = {"blue": "蓝V", "orange": "橙V"}.get(p["verify_type"], "无V")
        o = {
            "official": "官媒/官方", "media": "媒体",
            "verified_org": "蓝V机构", "verified_person": "认证个人",
        }.get(p["official"], "普通")
        print("%d. [%s|%s] %s | %s | %s" % (i, v, o, p["author"], p["time"], p["source"]))
        print("   正文: %s" % p["text"][:150])
        print("   图片%d张 互动:%s URL:%s" % (len(p["images"]), "/".join(p["acts"]), p["url"]))
    return facts
