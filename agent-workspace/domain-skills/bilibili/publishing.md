# Bilibili creator publishing

This skill is loaded from the absolute path below inside Browser Harness:

```python
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py").read())
```

It is for one logged-in creator upload on the current task-owned tab. It does
not depend on SAU or biliup at runtime.

## Required order

1. Enter a managed lease. For the authorized acceptance account use:

   ```bash
   ./browser-harness agent-pool run \
     --browser "SAU-自媒体运营-2号-9226" \
     --site member.bilibili.com --account "518800384" --mode write
   ```

2. In the lease, call `new_tab(UPLOAD_URL)`, `wait_for_load()`, and
   `page_info()`. Read every returned `domain_skill_files` Markdown file before
   site-specific actions.
3. Load this file, call `require_identity(518800384, "水蜜桃英语")`, then call
   `prepare_upload(video_file, title, expected_mid, expected_name)`.
4. Set declaration, custom cover, tags, partition, description, and schedule.
   Read `submission_snapshot()` and assert every requested value.
5. Call `submit_once(...)` exactly once. After the click, confirmation is
   read-only: return to the creator manager list and reload it. Publication is
   confirmed only when the first (latest) card has the exact submitted title
   and, when scheduled, the exact schedule. Do not infer failure from a delayed
   archive API response.
6. Close only the task-owned tab after manager-list reconciliation. Never stop
   Chrome or its Profile.

## Public functions

- `account_identity() -> dict`: reads the logged-in nav API. Raises when the
  session is logged out or the API fails. No mutation.
- `archive_matches(title: str) -> list[dict]`: reads exact-title archive rows,
  including AID/BVID and state. No mutation.
- `require_identity(expected_mid: int, expected_name: str | None = None) -> dict`:
  verifies MID and optional name substring, raising on mismatch. No mutation.
- `prepare_upload(video_file: str, title: str, expected_mid: int,
  expected_name: str | None = None, timeout: int = 600) -> dict`: validates a
  non-empty video, title length, identity, and exact-title uniqueness; uploads
  the video and fills the title; raises before upload on invalid/duplicate data.
- `choose_recommended_cover() -> None`: accepts the platform recommendation
  only when the cover is empty. It never submits.
- `set_custom_cover(path: str, timeout: float = 30) -> dict`: validates a
  readable image before page interaction, uploads it through the visible image
  input, confirms the visible crop `完成` control once, and returns
  `{"custom_cover_set": True, "filename": str, "width": int, "height": int}`
  only after DOM readback. It never chooses a recommendation or submits.
- `set_tags(tags: list[str], timeout: float = 10) -> list[str]`: strips and
  de-duplicates non-empty tags in caller order, preserves platform auto-tags,
  clicks an exact visible platform recommendation when available and otherwise
  enters the target through `按回车键Enter创建标签`, and returns all selected
  tags. Raises with the missing target and observed list on rejection/quota.
- `set_declaration(label: str = "内容无需标注") -> None`: selects the visible
  declaration option and verifies the visible input. Raises on missing option or
  mismatched readback.
- `set_partition(name: str, timeout: float = 10) -> str`: rejects blank names,
  opens the visible partition selector, chooses exact visible options and a
  required second-level option, then returns the exact selected value. Body
  text alone is never accepted as proof.
- `set_description(text: str, timeout: float = 10) -> str`: replaces the
  visible Quill editor, dispatches `beforeinput`, `input`, `change`, and
  `blur`, and returns the normalized exact readback.
- `set_schedule_datetime(value: str, timeout: float = 15) -> dict`: accepts only
  `YYYY-MM-DD HH:MM`, requires a five-minute minute, and requires Asia/Shanghai
  wall time to be at least five minutes ahead and no more than fifteen days
  ahead. It enables scheduling, sets both date and time, and returns
  `{"schedule_date": str, "schedule_time": str, "schedule": str}` after strict
  readback.
- `set_schedule_time(hour: int, minute: int) -> str`: backward-compatible
  same-day wrapper around `set_schedule_datetime`; it has the same future and
  five-minute constraints.
- `submission_snapshot() -> dict`: reads title, cover readiness/custom state and
  filename, partition, description, tags, declaration, scheduling date/time,
  scheduling state, exact `立即投稿` text, button enabled state, and visible
  validation errors from the DOM. It has no fake body-text category flag.
- `submission_diagnostics() -> dict`: reads post-click URL, visible validation
  errors, toast text, confirmation/modal text, submit-button state, and a short
  relevant page-text summary. Its deterministic `reason` is one of
  `form_validation_failed`, `confirmation_required`, `platform_rejected`,
  `archive_evidence_delayed`, `click_not_accepted`, or
  `submission_unverified`. It never clicks or confirms anything.
- `manager_evidence(title: str, expected_schedule: str | None = None,
  strict: bool = True, attempts: int = 3) -> dict`: opens the manager list and
  re-navigates to that same URL for up to three total list loads. It accepts
  only the first/latest card with the exact title, then verifies optional
  `定时发布` plus the exact Chinese date/time. It returns `latest=true` and
  `list_loads`; a matching older card is not publication evidence.
- `submit_once(title: str, expected_mid: int, expected_name: str | None = None,
  expected_schedule: str | None = None, timeout: int = 600) -> dict`: rechecks
  identity, exact-title uniqueness, and two stable full snapshots, clicks
  `立即投稿` exactly once, then polls the archive API and repeatedly reloads the
  manager list under one deadline. An exact latest manager card can verify
  acceptance before the archive API catches up; the result then has
  `verification_source="manager_latest"` and may not yet contain `archive`.
  Upload/processing success notices are positive toasts, never form errors.
  A true rejection returns `status="not_accepted"`, concrete diagnostics, and
  `submit_clicks=1`.

## Exact usage example

```python
new_tab("https://member.bilibili.com/platform/upload/video/frame")
wait_for_load()
print(page_info())
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py").read())
require_identity(518800384, "水蜜桃英语")
prepare_upload(VIDEO, TITLE, 518800384, "水蜜桃英语")
set_custom_cover("/tmp/bh-bilibili-cover-20260825.png")
set_tags(["英语学习", "英语听力", "英语新闻", "足球", "彩票"])
set_partition("知识")
set_description(DESCRIPTION)
set_declaration("内容无需标注")
set_schedule_datetime("2026-08-30 22:00")
print(submission_snapshot())
result = submit_once(TITLE, 518800384, "水蜜桃英语", "2026-08-30 22:00")
print(result)
```

## Recovery contract

| Result | Required action |
| --- | --- |
| `status="verified"` | Finish when `manager.latest=true`, retain manager evidence, and retain AID/BVID too when the archive API has caught up. |
| `status="accepted_but_schedule_unverified"` | Poll only `manager_evidence(title, schedule)` read-only. Its default three list loads are the bounded refresh procedure. Never call `prepare_upload`, any `set_*`, `_click_visible`, or `submit_once` again. |
| `status="not_accepted"` | Preserve `diagnostics`, inspect the exact reason, then call only `manager_evidence(title, schedule)` for bounded read-only reconciliation. Do not click or submit again automatically. |
| multiple exact-title records or pre-existing exact-title record | Hard stop. Never submit, duplicate, delete, retract, or invent a new title. |

The submit click fact is recorded before polling, so a delayed manager page can
never cause a second click. Do not confirm delete, retract, cancel-publication,
or immediate-publication dialogs.

## Verification checklist

- [ ] Identity MID/name is exact.
- [ ] Video upload reaches `上传完成`; title is 1–80 characters.
- [ ] Custom cover readback is true with the expected filename and dimensions.
- [ ] All requested tags are present exactly once; auto-tags may remain.
- [ ] Partition readback is the requested value or its documented `知识` leaf.
- [ ] Description and declaration read back exactly.
- [ ] Scheduling is enabled and date/time match the requested value.
- [ ] Two snapshots taken two seconds apart are identical.
- [ ] `submit_once` is called once; no recovery path clicks it again.
- [ ] After bounded list reloads, the manager's first/latest card has the exact
  title, `latest=true`, and the exact Chinese schedule when scheduled.
- [ ] AID/BVID is retained when the archive API has caught up; manager-latest
  evidence remains sufficient while that API is delayed.
- [ ] Agent Pool leases and write locks are empty after cleanup.
