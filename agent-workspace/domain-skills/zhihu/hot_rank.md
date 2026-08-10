# Zhihu Hot Rank Domain Skill (知乎热榜)

## Scope

Fetch the top-N items of Zhihu's hot-ranking list (知乎热榜) for read-only
monitoring. The hot list is category-free (single ranking page). Each entry
has a rank, question title, question URL, and heat metric.

- Allowed: reading the hot-rank list, extracting top-N entries.
- Destructive boundary: never post, answer, comment, vote, follow, or mutate
  any Zhihu data.
- Hosts: `zhihu.com` / `*.zhihu.com` (hot rank page: `zhihu.com/hot`).

## Login requirement

`www.zhihu.com/hot` renders the full list in an anonymous session, but a
logged-in session is more reliable (avoids any prompt wall). The Agent Chrome
cookie jar carries the session; do not store tokens or cookies in this skill.

## UI facts (verified 2026-08-10)

Page: `https://www.zhihu.com/hot`.

- The ranking list renders as `section.HotItem` items inside
  `div.HotList-list` (30 items visible without scrolling).
- Each item structure (verified):
  - rank: `.HotItem-rank` text (1..N). Top-3 use extra class `HotItem-hot`.
  - title: `h2.HotItem-title` text (long question text).
  - href: the wrapping `a[href*="question"]` URL
    (`https://www.zhihu.com/question/<id>`).
  - heat: `.HotItem-metrics` text like `544 万热度` (may include trailing
    UI text such as 分享; normalize whitespace).
- The page shows 30 items; take the first `limit` (default 15).
- Class names are stable CSS (HotItem/HotList), not hashed, but re-verify if
  Zhihu revamps the page.

## Functions

### `fetch_hot_rank(limit=15)`

Navigate to the hot page, wait for the list, and return up to `limit` entries.

```python
{"rank": "1", "title": "传销犯变身「国学大师」...", "heat": "544 万热度",
 "href": "https://www.zhihu.com/question/2068754726955345626"}
```

- `limit` clamps to the first N items; pass `None` for all visible (30).
- Returns a plain list; caller formats output.

### `run(limit=15)`

CLI-ish entry used when the file is loaded via `exec(open(...).read())` under
Browser Harness stdin scripts (the `__main__` guard does not fire there).
Prints each entry as `rank. title | heat | href`.

## Example

```bash
BH_DOMAIN_SKILLS=1 BU_NAME=agent BU_CDP_URL=http://127.0.0.1:9223 browser-harness <<'PY'
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/zhihu/hot_rank.py").read())
run(15)
PY
```

## Verification checklist

- [ ] `goto_url('https://www.zhihu.com/hot')` then `page_info()` stays on
      `zhihu.com/hot` with `HotItem` items present.
- [ ] `fetch_hot_rank(15)` returns 15 rows with non-empty rank/title/heat/href.
- [ ] Titles match the visible page order (rank 1 = first list item).
- [ ] `limit=None` returns all visible items (30).
- [ ] Heat text is normalized (no stray whitespace, keeps `万热度` suffix).
