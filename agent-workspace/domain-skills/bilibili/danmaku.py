"""Bilibili danmaku fetch helper for Browser Harness (弹幕抓取).

Fetches danmaku (弹幕) for a specific bilibili video through the logged-in
Agent Chrome session. Two modes:

- mode='xml' (default): GET /x/v1/dm/list.so?oid={cid} → XML with up to
  ~1200 danmaku entries, each with progress time, mode, font size, color,
  send timestamp, user hash, and content. Fast, good for analysis/display.
- mode='seg': GET /x/v2/dm/web/seg.so?type=1&oid={cid}&segment_index={n} →
  protobuf binary; segment 1 usually contains the bulk of a short video's
  danmaku. Parsed by extracting the readable text fields (content) plus the
  binary protobuf fields via a minimal decoder fallback.

Both go through the page context fetch with credentials='include', so the
Agent Chrome login cookie applies. Read-only; never posts.

UI/API facts (verified 2026-08-10):
- Video page exposes window.__INITIAL_STATE__.videoData = {bvid, cid, stat}.
- stat.danmaku = total danmaku count on the video page.
- /x/v1/dm/list.so response caps around maxlimit 1000-1200 entries.
- /x/v2/dm/web/seg.so returns 304 for empty/missing segments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def goto_url(url: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...


def fetch_danmaku(bvid, cid=None, mode="xml", segment_index=1, limit=1200):
    """Fetch danmaku for a video.

    Args:
      bvid: video BV id (BVxxxx). Required.
      cid: optional video cid; if missing, reads it from the video page
        (requires navigating to the video page first).
      mode: 'xml' (list.so, capped ~1200) or 'seg' (seg.so protobuf).
      segment_index: seg mode segment to fetch (1-based).
      limit: max danmaku entries to return (xml mode).

    Returns:
      {"bvid", "cid", "mode", "total" (stat.danmaku or len), "count",
       "danmaku": [ {time, mode, font_size, color, send_time, user, text} ]}
    """
    if not cid:
        # navigate to the video page to read cid + stat
        goto_url("https://www.bilibili.com/video/" + bvid)
        wait(3.5)
        info = js(
            "(() => {"
            "  const st = window.__INITIAL_STATE__;"
            "  if (st && st.videoData) return {cid: st.videoData.cid, danmaku_total: st.videoData.stat ? st.videoData.stat.danmaku : 0};"
            "  return null;"
            "})()"
        )
        if not info:
            raise RuntimeError("Bilibili video page not loaded (login wall or stale selector)")
        cid = info["cid"]
        total_stat = info.get("danmaku_total", 0)
    else:
        total_stat = 0

    if mode == "xml":
        data = js(
            "(() => {"
            "  return fetch('https://api.bilibili.com/x/v1/dm/list.so?oid=' + %d + '&_=' + Date.now(), {credentials: 'include'})"
            "    .then(r => r.text())"
            "    .then(t => {"
            "      const re = /<d p=\\\"([^\\\"]*)\\\">([^<]*)<\\/d>/g;"
            "      const out = [];"
            "      let m;"
            "      while ((m = re.exec(t)) !== null) {"
            "        const p = m[1].split(',');"
            "        out.push({time: p[0] || '', mode: p[1] || '', font_size: p[2] || '', color: p[3] || '',"
            "                 send_time: p[4] || '', user: p[6] || '', text: m[2]});"
            "      }"
            "      return {count: out.length, danmaku: out.slice(0, %d)};"
            "    });"
            "})()" % (cid, limit)
        )
    else:
        # seg.so: keep the JS short (js() truncates very long expressions).
        # Top-level field 1 is a repeated nested message (DanmakuElem); inside
        # it field 7 (tag 0x3a) is the danmaku content string. Walk both
        # levels and collect readable strings.
        data = js(
            "(() => {"
            "  return fetch('https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid=' + %d + '&segment_index=' + %d + '&_=' + Date.now(), {credentials: 'include'})"
            "    .then(async r => {"
            "      if (r.status !== 200) return {status: r.status, count: 0, danmaku: []};"
            "      const buf = await r.arrayBuffer();"
            "      const bytes = new Uint8Array(buf);"
            "      const dec = new TextDecoder('utf-8');"
            "      const texts = [];"
            "      const readStr = (arr, pos) => {"
            "        let len = 0, shift = 0;"
            "        let p = pos;"
            "        while (p < arr.length && shift < 28) {"
            "          const b = arr[p++];"
            "          len |= (b & 0x7f) << shift;"
            "          if (!(b & 0x80)) break;"
            "          shift += 7;"
            "        }"
            "        if (p + len <= arr.length) {"
            "          const s = dec.decode(arr.subarray(p, p + len));"
            "          return {str: s, next: p + len};"
            "        }"
            "        return {str: '', next: arr.length};"
            "      };"
            "      let i = 0;"
            "      while (i + 2 < bytes.length) {"
            "        const tag = bytes[i++];"
            "        const wt = tag & 7;"
            "        if (wt === 2) {"
            "          const r0 = readStr(bytes, i);"
            "          const inner = bytes.subarray(i, r0.next);"
            "          i = r0.next;"
            "          let j = 0;"
            "          while (j + 2 < inner.length) {"
            "            const t2 = inner[j++];"
            "            if ((t2 & 7) === 2) {"
            "              const r1 = readStr(inner, j);"
            "              j = r1.next;"
            "              const s = r1.str;"
            "              if (t2 >> 3 === 7 && s.length > 0 && s.length < 200) texts.push(s);"
            "            } else if ((t2 & 7) === 0) {"
            "              while (j < inner.length && (inner[j] & 0x80)) j++;"
            "              if (j < inner.length) j++;"
            "            } else if ((t2 & 7) === 5) { j += 4; }"
            "            else if ((t2 & 7) === 1) { j += 8; }"
            "            else j++;"
            "          }"
            "        } else if (wt === 0) {"
            "          while (i < bytes.length && (bytes[i] & 0x80)) i++;"
            "          if (i < bytes.length) i++;"
            "        } else if (wt === 5) { i += 4; }"
            "        else if (wt === 1) { i += 8; }"
            "        else i++;"
            "      }"
            "      const danmaku = texts.map(t => ({time: '', text: t}));"
            "      return {status: 200, count: danmaku.length, danmaku: danmaku.slice(0, %d)};"
            "    });"
            "})()" % (cid, segment_index, limit)
        )

    if not isinstance(data, dict) or "count" not in data:
        raise RuntimeError("Bilibili danmaku fetch failed (login wall or stale selector)")
    if data.get("status") and data["status"] != 200:
        raise RuntimeError("Bilibili danmaku seg.so returned status %s" % data["status"])

    return {
        "bvid": bvid,
        "cid": cid,
        "mode": mode,
        "total": total_stat if total_stat else data.get("count", 0),
        "count": data["count"],
        "danmaku": data.get("danmaku", []),
    }


def run(bvid=None, mode="xml", limit=1200, segment_index=1):
    """CLI entry for exec(open(...).read()) under Browser Harness."""
    if not bvid:
        # take the first search result as a demo source (search loaded first)
        rows = search_videos("白海豚", order="dm", limit=1)
        bvid = rows[0]["bvid"]
    data = fetch_danmaku(bvid, mode=mode, limit=limit, segment_index=segment_index)
    print("=== 弹幕: %s | cid=%s | 模式=%s | 总数(页/返) %s/%d ===" % (
        data["bvid"], data["cid"], data["mode"], data["total"], data["count"]))
    for i, d in enumerate(data["danmaku"][:30], 1):
        print("%d. [%s] %s" % (i, d.get("time", ""), d["text"][:60]))
    return data
