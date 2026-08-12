"""Bilibili replies (comments) fetch helper for Browser Harness (评论抓取).

Fetches video comments (评论) through the logged-in Agent Chrome session via
the bilibili reply API. Two modes:

- mode='hot' (default): /x/v2/reply/main?type=1&oid={aid}&mode=3 — comments
  ranked by likes (高热优先, 首屏即精华).
- mode='time': /x/v2/reply/main?type=1&oid={aid}&mode=2 — newest first.

Each reply entry: user name, like count, timestamp, full text. The API
paginates via cursor (next); `next=0` returns the first page and the cursor
tells whether more pages exist. Requires the video `aid` (not cid); if only a
bvid is given, navigates to the video page to read aid + reply stat.

Read-only; never posts. Login cookie applies via credentials:'include'.

API facts (verified 2026-08-10):
- Video page exposes window.__INITIAL_STATE__.videoData = {bvid, aid, cid,
  stat}; stat.reply = total comment count shown on the video page.
- Reply API response: {code:0, data:{cursor:{all_count, is_end, next},
  replies:[{member:{uname}, like, ctime, content:{message}}]}}.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def goto_url(url: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...


def fetch_replies(bvid=None, aid=None, mode="hot", max_pages=5, limit=500):
    """Fetch comments for a video.

    Args:
      bvid: video BV id; required if aid is missing (navigates to the video
        page to read aid + reply stat).
      aid: video aid; if provided, no navigation is needed.
      mode: 'hot' (likes ranking) or 'time' (newest first).
      max_pages: max cursor pages to fetch (~20 replies per page).
      limit: max replies to return.

    Returns:
      {"bvid", "aid", "mode", "total" (stat.reply or api all_count),
       "count", "is_end", "replies": [{user, like, time, text}]}
    """
    total_stat = 0
    if not aid:
        if not bvid:
            raise RuntimeError("fetch_replies requires bvid or aid")
        goto_url("https://www.bilibili.com/video/" + bvid)
        wait(3.5)
        info = js(
            "(() => {"
            "  const st = window.__INITIAL_STATE__;"
            "  if (st && st.videoData) return {aid: st.videoData.aid, reply_total: st.videoData.stat ? st.videoData.stat.reply : 0};"
            "  return null;"
            "})()"
        )
        if not info:
            raise RuntimeError("Bilibili video page not loaded (login wall or stale selector)")
        aid = info["aid"]
        total_stat = info.get("reply_total", 0)

    mode_val = 3 if mode == "hot" else 2

    data = js(
        "(() => {"
        "  const aid = %d;"
        "  const modeVal = %d;"
        "  const maxPages = %d;"
        "  const fetchPage = async (next) => {"
        "    const r = await fetch('https://api.bilibili.com/x/v2/reply/main?type=1&oid=' + aid + '&mode=' + modeVal + '&next=' + next + '&_=' + Date.now(), {credentials: 'include'});"
        "    return r.json();"
        "  };"
        "  return (async () => {"
        "    let all = [];"
        "    let cursorNext = 0;"
        "    let isEnd = false;"
        "    let total = 0;"
        "    for (let p = 0; p < maxPages; p++) {"
        "      const j = await fetchPage(cursorNext);"
        "      if (j.code !== 0) break;"
        "      const d = j.data || {};"
        "      total = d.cursor ? (d.cursor.all_count || 0) : total;"
        "      const replies = d.replies || [];"
        "      for (const x of replies) {"
        "        all.push({user: x.member ? x.member.uname : '', like: x.like || 0, time: x.ctime || 0, text: x.content ? x.content.message : ''});"
        "      }"
        "      if (d.cursor) {"
        "        cursorNext = d.cursor.next || 0;"
        "        isEnd = d.cursor.is_end || false;"
        "      }"
        "      if (isEnd || !cursorNext) break;"
        "    }"
        "    return {total: total, count: all.length, is_end: isEnd, replies: all.slice(0, %d)};"
        "  })();"
        "})()" % (aid, mode_val, max_pages, limit)
    )

    if not isinstance(data, dict) or "replies" not in data:
        raise RuntimeError("Bilibili replies fetch failed (login wall or stale selector)")

    return {
        "bvid": bvid or "",
        "aid": aid,
        "mode": mode,
        "total": total_stat if total_stat else data.get("total", 0),
        "count": data["count"],
        "is_end": data.get("is_end", False),
        "replies": data["replies"],
    }


def run(bvid=None, mode="hot", max_pages=5, limit=500):
    """CLI entry for exec(open(...).read()) under Browser Harness."""
    if not bvid:
        rows = search_videos("武汉", order="dm", limit=1)  # requires search loaded first
        bvid = rows[0]["bvid"]
    data = fetch_replies(bvid, mode=mode, max_pages=max_pages, limit=limit)
    print("=== 评论: %s | aid=%s | 模式=%s | 总数(页/返) %s/%d ===" % (
        data["bvid"], data["aid"], data["mode"], data["total"], data["count"]))
    for i, r in enumerate(data["replies"][:20], 1):
        print("%d. [%d赞] %s: %s" % (i, r["like"], r["user"][:15], r["text"][:50]))
    return data
