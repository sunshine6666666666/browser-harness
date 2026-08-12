# Bilibili Search & Danmaku Domain Skill (B站搜索 + 弹幕抓取)

## Scope

Search bilibili videos by keyword (with configurable ranking) and fetch the
danmaku (弹幕) of a specific video. Intended for collecting video metadata +
danmaku content + danmaku counts for downstream analysis (素材采集).

- Allowed: search results, video metadata, danmaku content (read-only).
- Destructive boundary: never post, send, delete, or mutate any bilibili data.
- Hosts: `bilibili.com` / `*.bilibili.com` (search at
  `search.bilibili.com/all`, video at `www.bilibili.com/video/BV...`).

## Login requirement

The Agent Chrome has a logged-in bilibili session (大会员 visible). The
search page works without login; danmaku API calls use the page fetch with
`credentials: 'include'` so the session cookie applies. Do not store tokens
or cookies in this skill.

## UI facts (verified 2026-08-10)

### Search page (search.bilibili.com/all?keyword=...)

- Result cards: `div.bili-video-card`, one per video, in page order.
- Title link: `a` whose href contains `/video/BV` AND has no `img`/`picture`
  child (the cover link also matches `/video/BV` but contains an image).
- Uploader + publish date: `a.bili-video-card__info--owner` (uploader name is
  its first child text node); date is `.bili-video-card__info--date`.
- Stats: `.bili-video-card__stats--item` spans — first = views, second =
  danmaku count. Duration: `.bili-video-card__stats__duration`.
- Ordering via URL param `order=`:
  - default (综合): no param
  - `click` (最多播放), `pubdate` (最新发布), `dm` (最多弹幕), `stow` (最多收藏)

### Video page (www.bilibili.com/video/BV...)

- `window.__INITIAL_STATE__.videoData` = {bvid, cid, title, stat}.
- `stat.danmaku` = total danmaku count shown on the video page.

### Danmaku APIs

- XML (fast, capped): `GET https://api.bilibili.com/x/v1/dm/list.so?oid={cid}`
  → XML with `<d p="time,mode,fontsize,color,send_time,...,user,...">text</d>`
  entries. Single response caps around 1000-1200 entries (maxlimit).
- Segments (protobuf): `GET https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={cid}&segment_index={n}`
  → binary protobuf. Top-level field 1 is repeated `DanmakuElem`; inside it
  field 7 (tag 0x3a) is the danmaku content string. Segment 1 carries the
  bulk of short videos; further segments may return 304 (empty).

## Functions

### `search_videos(keyword, order='default', limit=15)`

Search by keyword with the given ordering. Returns list of dicts in page
order (first = top-ranked):

```python
{"rank": 1, "title": "上海今日暴雨10大名场面…", "bvid": "BV1VPu166ENW",
 "url": "https://www.bilibili.com/video/BV1VPu166ENW/",
 "uploader": "遁走的两轮_Ming", "view": "46.5万", "danmaku": "333",
 "duration": "01:21", "publish": "20小时前"}
```

- `order` must be one of: default / click / pubdate / dm / stow.
- Returns the position (rank) explicitly — which videos rank first/last.

### `fetch_danmaku(bvid, cid=None, mode='xml', segment_index=1, limit=1200)`

Fetch danmaku for a video. If `cid` is omitted, navigates to the video page
to read `cid` and the total danmaku stat.

Returns:

```python
{"bvid": "BV...", "cid": 32112314223, "mode": "xml",
 "total": 29697,   # stat.danmaku from video page, or fetched count
 "count": 360,     # entries actually returned
 "danmaku": [ {"time": "0.65300", "mode": "1", "font_size": "25",
               "color": "16777215", "send_time": "15138834", "user": "...",
               "text": "中华大海豚去1级保护动物是稀少"} ]}
```

- `mode='xml'`: fast, capped ~1000-1200 entries, full metadata per entry.
- `mode='seg'`: protobuf parse via short JS walker; returns many more entries
  (segment 1 of a short video ≈ 9k+), each `{time: '', text}` (metadata
  fields not yet decoded). Raises on non-200.
- `total` uses the video page's authoritative danmaku stat when available.

### `run(bvid=None, mode='xml', limit=1200, segment_index=1)`

CLI entry under Browser Harness (`exec(open(...).read())`; the `__main__`
guard does not fire). If `bvid` is omitted, searches "白海豚" by `dm` order
and uses the top result. Requires `search.py` to be loaded first when bvid
is omitted.

## Example

```bash
BH_DOMAIN_SKILLS=1 BU_NAME=agent BU_CDP_URL=http://127.0.0.1:9223 browser-harness <<'PY'
exec(open(".../bilibili/search.py").read())
exec(open(".../bilibili/danmaku.py").read())
rows = search_videos("白海豚", order="dm", limit=10)
for r in rows:
    print(r["rank"], r["title"], r["danmaku"], r["bvid"])
data = fetch_danmaku(rows[0]["bvid"], mode="xml", limit=500)
print(data["total"], data["count"])
PY
```

## Verification checklist

- [ ] `search_videos("白海豚")` returns ranked rows with title/bvid/uploader/
      view/danmaku/duration/publish.
- [ ] `search_videos("白海豚", order="dm")` top row has the highest danmaku
      count; counts match the video page stat when opened.
- [ ] `fetch_danmaku(bvid)` xml mode returns entries with time+text and
      `total` = video page danmaku stat.
- [ ] `fetch_danmaku(bvid, mode="seg")` returns thousands of readable text
      entries for a short popular video.
- [ ] Invalid order / failed fetch raises instead of silently returning
      empty data.
