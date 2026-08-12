# Bilibili Replies Domain Skill (B站评论抓取)

## Scope

Fetch comments (评论) of a bilibili video through the logged-in Agent Chrome
session. Complements `danmaku.py` (弹幕) — together they cover the two
mass-text sources of a video (弹幕 + 评论) for downstream analysis.

- Allowed: reading comment lists (read-only).
- Destructive boundary: never post, send, delete, or mutate any bilibili data.
- Hosts: `bilibili.com` / `*.bilibili.com`.

## Login requirement

The Agent Chrome has a logged-in bilibili session. Comment API calls use page
fetch with `credentials: 'include'` so the session cookie applies. Do not
store tokens or cookies in this skill.

## API facts (verified 2026-08-10)

### Reply API

`GET https://api.bilibili.com/x/v2/reply/main?type=1&oid={aid}&mode={3|2}&next={cursor}`

- `oid` is the video **aid** (not cid).
- `mode=3`: ranked by likes (热度, 首屏即精华). `mode=2`: newest first (时间).
- `next=0` returns the first page (~20 replies); response
  `data.cursor` = `{all_count, is_end, next}` drives pagination.
- Reply entry: `member.uname` (user), `like`, `ctime` (unix ts),
  `content.message` (full text, may contain newlines).
- Video page `stat.reply` is the authoritative total comment count.

## Functions

### `fetch_replies(bvid=None, aid=None, mode='hot', max_pages=5, limit=500)`

Fetch comments. If `aid` is omitted, navigates to the video page to read
`aid` + `stat.reply` (requires bvid).

Returns:

```python
{"bvid": "BV1M7411k7eq", "aid": 85021933, "mode": "hot",
 "total": 2544,   # stat.reply from video page, or api all_count
 "count": 59,     # entries actually returned
 "is_end": False,
 "replies": [ {"user": "柠檬派奇幻漂流", "like": 6941,
               "time": 1579966129, "text": "武汉加油"} ]}
```

- `mode='hot'`: likes ranking (top comments first).
- `mode='time'`: newest first.
- `max_pages`: cursor pages to walk (~20 replies each); `limit` caps the
  final list. Raises on API failure.

### `run(bvid=None, mode='hot', max_pages=5, limit=500)`

CLI entry under Browser Harness (`exec(open(...).read())`; the `__main__`
guard does not fire). If `bvid` is omitted, searches "武汉" by `dm` order and
uses the top result — requires `search.py` loaded first.

## Example

```bash
BH_DOMAIN_SKILLS=1 BU_NAME=agent BU_CDP_URL=http://127.0.0.1:9223 browser-harness <<'PY'
exec(open(".../bilibili/replies.py").read())
data = fetch_replies(bvid="BV1M7411k7eq", mode="hot", max_pages=3, limit=100)
print(data["total"], data["count"])
for r in data["replies"][:10]:
    print(r["like"], r["user"], r["text"][:40])
PY
```

## Verification checklist

- [ ] `fetch_replies(bvid)` hot mode returns replies sorted by like count and
      `total` = video page `stat.reply`.
- [ ] `fetch_replies(bvid, mode="time")` returns newest comments first.
- [ ] `max_pages` walks the cursor; `limit` caps the result list.
- [ ] Failed API / login wall raises instead of silently returning empty data.
