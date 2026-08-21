# Weibo Hot Rank Domain Skill (微博热榜)

## Scope

Fetch the top-N items of Weibo's hot-search ranking by category, for read-only
monitoring. Currently implemented categories: `social` (社会) and
`entertainment` (文娱). Each category page lists rank, topic title, heat value,
and a topic search link.

- Allowed: reading hot-rank lists, extracting top-N entries.
- Destructive boundary: never post, send, delete, or mutate any Weibo data.
- Hosts: `weibo.com` / `*.weibo.com` (hot rank pages render at `weibo.com/hot/<category>`).

## Login requirement

The hot-rank category pages (`/hot/social`, `/hot/entertainment`) require a
logged-in Weibo session in the attached Chrome. Without login the page
redirects to `weibo.com/newlogin` and the list body is empty. Login state is
carried by the Agent Chrome cookie jar; do not store tokens or cookies in this
skill.

## UI facts (verified 2026-08-10)

Pages: `https://weibo.com/hot/social`, `https://weibo.com/hot/entertainment`.

- Category links in left nav once logged in: `/hot/search` (热搜),
  `/hot/entertainment` (文娱), `/hot/social` (社会), `/hot/tech` (科技),
  `/hot/life` (生活), `/hot/sports` (体育), `/hot/acg` (ACG).
- The rank list renders inside `div._item_13qc7_56` items, one per entry,
  directly under the page body (no `<ul>/<li>` wrapper).
- Each item structure (verified):
  - rank: `[class*="_ranknum"]` text (1..N). Rank 1 uses `_rank1_...` img style but `_ranknum` span still holds the number.
  - title: `a._tit_13qc7_65` text; link `a` href is the search URL
    `https://s.weibo.com/weibo?q=<urlencoded>&t=<ts>`.
  - heat: `._num_13qc7_85 span` text (integer-like heat value).
  - status badge (热/新/爆/沸/重磅): rendered in the sibling div after the
    title only on the default `/hot/search` list. The `social` and
    `entertainment` category pages currently show **no badge** (empty Vue slot).
- The page shows 17 items; take the first `limit` (default 15).
- Class names are hashed and may change on Weibo redeploys. If `_item_13qc7_56`
  no longer matches, fall back to locating `a._tit_*` anchors and walking up.

## Functions

### `fetch_hot_rank(category='social', limit=15)`

Navigate to the category page, wait for the list, and return up to `limit`
entries. Each entry:

```python
{"rank": "1", "title": "白海豚 上班", "heat": "4088597",
 "href": "https://s.weibo.com/weibo?q=...&t=769"}
```

- `category` must be one of `social`, `entertainment` (raise on others).
- `limit` clamps to the first N items; pass `None` for all available.
- Returns a plain list; caller formats output.

### `run(category='social', limit=15)`

CLI-ish entry used when the file is loaded via `exec(open(...).read())` under
Browser Harness stdin scripts (the `__main__` guard does not fire there).
Prints each entry as `rank. title | heat | href`.

## Topic facts (话题事实素材提取)

Sibling helper: `topic_facts.py` (same directory). It opens a topic search
page from a hot-rank entry href and extracts raw material for downstream
judgment/辨证 — it does NOT summarize.

### `fetch_topic_facts(topic_url, max_pages=5, stale_pages=None, limit=None, sort="general")`

Follows s.weibo.com pagination (`&page=N`) and scans five pages by default
(about 100 raw posts before deduplication). It does not stop merely because an
early page lacks official media: later pages can contain additional fact
sources. Callers can raise `max_pages` when text evidence is still incomplete,
or explicitly set `stale_pages` for an early-stop policy.

- `sort` selects the Weibo search tab: `general` (综合), `hot` (热门), or
  `time` (实时). The selected mode is reflected in the returned `sort` field.

Returns:

```python
{"topic": "武汉通报天桥打人事件", "stats": "阅读量2857.9万 讨论量5630",
 "page_count": 5, "sort": "general",
 "posts": [
   {"author": "平安武昌", "verified": True, "verify_type": "blue",
    "source_type": "official", "is_official": True, "is_media": False,
    "time": "今天09:13", "source": "微博网页版", "text": "警情通报...",
    "image_thumbnails": ["https://wx4.sinaimg.cn/orj360/..."],
    "images": ["https://wx4.sinaimg.cn/large/..."], "videos": [],
    "acts": ["358","1278","5244"],
    "url": "https://weibo.com/2524189004/RcI3Vio9M", "page": 1}
 ]}
```

Primitives for judgment: full text from multiple pages; blue-V/orange-V state;
separate source classification (`official`, `media`, `verified_org`,
`verified_person`, `ordinary`) so blue-V is never automatically called 官媒;
original image URLs for downstream vision/OCR; video URLs when exposed;
interaction counts (转发/评论/点赞); time, source device and canonical URL.
Posts stay in page order and are URL-deduplicated. The helper only extracts
material; downstream reasoning owns factual reconstruction and contradictions.

### `run(topic_url=None, limit=10, sort="general")`

CLI-ish entry; prints raw post material. If `topic_url` is omitted, it takes
the first social hot-rank entry as the topic source. `sort` is forwarded to
`fetch_topic_facts` and accepts `general`, `hot`, or `time`.

## Topic materials (图片素材库落地)

Sibling helper: `topic_materials.py` (same directory). Downloads original
images of a topic into a local material library so downstream vision/OCR/辨证
can consume them offline. Videos are NOT downloaded (out of scope; they are
too large for archival and their URLs are already exposed by
`fetch_topic_facts` for on-demand access).

**Calling convention**: because Browser Harness loads skill files via
`exec(open(...).read())`, sibling imports do not work — load `topic_facts.py`
FIRST, then `topic_materials.py`, in the same session:

```python
exec(open(".../weibo/topic_facts.py").read())
exec(open(".../weibo/topic_materials.py").read())
lib = fetch_topic_materials(topic_url, out_dir, max_pages=5, stale_pages=None,
                        limit=None, max_images_per_post=None, sort="general")
```

### `fetch_topic_materials(topic_url, out_dir, max_pages=5, stale_pages=None, limit=None, max_images_per_post=None, sort="general")`

- `out_dir`: root directory of the material library (per-topic subdirectory
  is created automatically).
- `max_pages` / `stale_pages` / `limit` / `sort`: forwarded to
  `fetch_topic_facts` (how many pages/posts to collect and which search tab to
  use — the caller decides the budget).
- `max_images_per_post`: optional cap on images downloaded per post.
- Downloads every post's original image URLs with a Weibo Referer header
  (Sina CDN may otherwise 403). Each image is verified: HTTP 200 and file
  size > 1 KB.

Output layout:

```
<out_dir>/<topic_slug>/
├── manifest.json     # every post + local image paths + meta
└── images/
    ├── 001-1.jpg     # post #001, image #1 (original resolution, for OCR)
    └── ...
```

Return:

```python
{"topic": "武汉通报天桥打人事件", "page_count": 5, "post_count": 50,
 "downloaded": 12, "failed": 0, "library_dir": "...", "manifest_path": "...",
 "manifest": [post entries with local_images]}
```

`manifest.json` keeps, per post: author, verify_type, source_type
(official/media/verified_org/verified_person/ordinary), is_official,
is_media, time, source, text (truncated to 500 chars), url, page,
images (remote URLs), local_images (absolute paths).

### `run(topic_url=None, out_dir='/tmp/weibo_materials', max_pages=5, limit=None, sort="general")`

CLI-ish entry; prints the material library summary. If `topic_url` is
omitted, it takes the first social hot-rank entry as the topic source.

## Example

```bash
/Users/yelin/Developer/agent-tools/browser-harness/browser-harness agent-pool run \
  --site weibo.com --account default --mode read <<'PY'
new_tab("https://weibo.com/hot/social")
print(page_info())
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/weibo/hot_rank.py").read())
run("social", 15)
run("entertainment", 15)
PY
```

## Verification checklist

- [ ] In the pool-assigned read session: `goto_url('https://weibo.com/hot/social')`
      then `page_info()` URL stays on `weibo.com/hot/social` (no `newlogin`
      redirect); do not select a browser instance or CDP port manually.
- [ ] `fetch_hot_rank('social', 15)` returns 15 rows with non-empty
      rank/title/heat/href.
- [ ] `fetch_hot_rank('entertainment', 15)` returns 15 rows.
- [ ] Titles match the visible page order (rank 1 = first list item).
- [ ] `limit=None` returns the full visible list (17 items).
- [ ] Invalid category raises instead of returning empty data.
