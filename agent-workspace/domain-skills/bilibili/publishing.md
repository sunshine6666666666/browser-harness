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
5. Call `submit_once(...)` exactly once. Persist its archive AID/BVID evidence.
6. Close only the task-owned tab after read-only manager reconciliation. Never
   stop Chrome or its Profile.

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
  enters each target through `按回车键Enter创建标签`, and returns all selected
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
  scheduling state, and exact `立即投稿` text from the DOM. It has no fake
  body-text category flag.
- `manager_evidence(title: str, expected_schedule: str | None = None) -> dict`:
  opens the manager page, finds the unique exact-title card, and verifies the
  optional `定时发布` plus exact Chinese date/time. Raises on absence/mismatch.
- `submit_once(title: str, expected_mid: int, expected_name: str | None = None,
  expected_schedule: str | None = None, timeout: int = 600) -> dict`: rechecks
  identity, exact-title uniqueness, and the full snapshot, clicks `立即投稿`
  exactly once, then polls archive and manager evidence under one deadline.

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
| `status="verified"` | Finish and retain the returned AID/BVID and manager evidence. |
| `status="accepted_but_schedule_unverified"` | Poll only `manager_evidence(title, schedule)` read-only. Never call `prepare_upload`, any `set_*`, `_click_visible`, or `submit_once` again. |
| no archive evidence | Treat as unknown; inspect exact-title archive records first. Do not retry blindly. |
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
- [ ] `submit_once` is called once and returns one AID/BVID.
- [ ] Manager evidence shows `定时发布` and the exact Chinese schedule.
- [ ] Agent Pool leases and write locks are empty after cleanup.
