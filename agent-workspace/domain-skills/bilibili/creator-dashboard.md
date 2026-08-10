# Bilibili — Creator Dashboard (创作中心后台) API & Data

> **路由标准（2026-08-06 起）**：本能力已登记于 **site-capability-registry**
> 能力 ID **`bilibili.creator-analytics`**（stable）。
> 任何 agent 在浏览器任务前必须先查
> `~/.hermes/shared-skills/site-capability-registry/references/catalog.md`；
> 命中后优先用 OpenCLI 命令（见下方 Reuse），**不要手写 fetch 脚本**。
> 规范：`references/CAPABILITY-REGISTRY-SPEC.md`；本文件只保留页面/API 探索知识。

Field-tested against member.bilibili.com on 2026-08-06 (account 水蜜桃英语 UID 518800384).
Requires logged-in creator session; all member.bilibili.com API calls need cookies.

---

## Pages

| Page | URL |
|------|-----|
| Creator home (overview stats) | `member.bilibili.com/platform/home` |
| Video management (稿件管理) | `member.bilibili.com/platform/upload-manager/article` |
| Collection management (合集管理) | `member.bilibili.com/platform/upload-manager/ep` |
| Single video data page | `member.bilibili.com/platform/upload-manager/article/data/{bvid}` (iframe: `york/data-center-web/articleAnalysis?bvid=...`) |

SPA routes redirect to `/platform/home` when opened directly — always navigate from the list page or use the API layer below.

## Video management page (upload-manager/article)

- Row container: `div.article-card.v2`; title `a.name`, duration `a.cover-wrp`, time `span.date`, buttons `a.bili-btn` (编辑/数据/查询进度).
- Stats line: 7 × `span.icon-text` in order **view, like, reply, danmaku, share, fav, coin** (verified against public view API).
- Page stats header: 全部稿件/草稿/进行中/已通过/未通过; paging footer `共 N 页 / M 个`.

## Creator APIs (member.bilibili.com, cookie required)

| Purpose | Endpoint | Notes |
|---------|----------|-------|
| Video list (稿件列表) | `/x/web/archives?status=is_pubing%2Cpubed%2Cnot_pubed&pn=1&ps=10&coop=1&interactive=1` | `data.class` = 状态计数 (pubed/not_pubed/is_pubing); `data.arc_audits[].Archive` = metadata (aid/bvid/title/duration/ptime/state/tag). **No stat fields.** Sort: `order=click` (播放数). |
| Sort fields reference | `/x/web/archive/list/pre` | order=senddate/click/stow/dm_count/scores |
| Seasons list (合集列表) | `/x2/creative/web/seasons?pn=1&ps=30&order=&sort=&draft=1&source=0` | `data.seasons[]`: `.season` (id/title/ep_num), `.seasonStat` (view/danmaku/reply/fav/coin/share/like/subscription = season totals), `.sections.sections[]` (id/title/epCount), `.part_episodes[]` (**only ~4 latest**, not full list). |
| Season detail | `/x2/creative/web/season?id={seasonId}` | part_episodes usually empty here |
| **Section episodes (合集全部视频)** | `/x2/creative/web/season/section?id={sectionId}` | `data.episodes[]` — **returns ALL episodes in one call (no paging)**. Fields: id/title/aid/bvid/order/archiveState (0=passed, -40=auditing/rejected). |
| Latest stats | `/x/web/data/archive/stat/query/latest` | needs extra params; prefer public view API instead |
| **Creator overview (全站概览)** | `/x/web/data/index/stat?tmid=` | `data`: total_click/fans/like/fav/coin/reply/dm/share/elec + incr_*（今日增量）+ log_date（数据日期，每日12点更新）——已被 `opencli bilibili creator-stat` 封装 |
| **Video comments (收到的评论)** | `api.bilibili.com/x/v2/reply/up/fulllist?order=1&filter=-1&type=1&pn=1&ps=10&charge_plus_filter=false` | `data.page.total` 总评论数；`data.list[]` 每条含 title(视频标题)/bvid/cover_url/floor/ctime/like/rcount/member.uname/content.message；`oid=` 参数可按视频过滤——已被 `opencli bilibili creator-comments` 封装 |

## Public API (api.bilibili.com, no login)

| Endpoint | Returns |
|----------|---------|
| `/x/web-interface/view?bvid={bvid}` | `data.stat`: view/danmaku/reply/favorite/coin/share/like + title/pubdate |
| `/x/web-interface/nav` | current user (wbi_img keys for WBI signing) |

## Verified facts (2026-08-06)

- Season "英语新闻播客" id=8762246, section id=9765963, 18 episodes; seasonStat.view=6460 ≈ Σ per-video view (6461) — cross-check passes.
- Season "英语新闻【训练版】" id=5626003, section id=6243662, 266 episodes — section API returned all 266 in one call.
- View API `view` matches the video-management row first stat number exactly.

## Reuse

OpenCLI commands already wrap this layer (devkeeper-maintained, local checkout):
`opencli bilibili seasons` / `opencli bilibili season <id|--match> [--limit N] [--no-stats]`.
If those commands exist, prefer them over hand-rolled fetch scripts.
