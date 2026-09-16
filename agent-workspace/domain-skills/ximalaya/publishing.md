# Ximalaya Publishing Domain Skill

Site: `ximalaya.com` / `*.ximalaya.com` (registry entry `ximalaya`).
Helper module (load with `exec(open(...).read())` inside an Agent Pool task):

```
/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.py
```

Verified live on 2026-09-08 against an authenticated creator studio. A logged-in
managed browser is sufficient; account UID and display name are observational
metadata, not authorization inputs or Domain Skill constants.

## Prerequisites

- Managed Chrome selected through Browser Fleet Manager; enter through
  `browser-harness agent-pool run`. The session must be logged in to Ximalaya.
  Do not compare UID, display name, browser name, or track `account_uid`.
- Read lease for read-only probes; `--mode write --account "$TARGET_ACCOUNT_ID"`
  for upload/publication/deletion, where `TARGET_ACCOUNT_ID` is set by the
  calling task rather than this Skill.
- Attach to a tab and open the upload form URL directly:

```
https://www.ximalaya.com/reform-upload/page/webCenter/upload
```

The shell page `https://studio.ximalaya.com/upload` embeds this flow inside a
cross-origin iframe; opening the iframe URL directly is the supported path.

## Required page-info order

1. Normally `new_tab(UPLOAD_URL)`. If the attached managed window is `fullscreen`, leave it untouched: create a separate Target with `cdp("Target.createTarget", url="about:blank", newWindow=True, background=True, focus=False, windowState="minimized")`, then `switch_tab(target)` without activation and `goto_url(UPLOAD_URL)`. In either case `protect_tab(target, owner=..., purpose=...)`.
2. `wait_for_load()`; print `page_info()`.
3. If `domain_skill_files` is returned, read every listed Markdown file first.
4. Verify only that the current session is logged in (`require_identity()`).

## Public API

| Function | Purpose |
| --- | --- |
| `account_identity()` | Read-only identity from `/anchor-works-web/common/getCurrentUser` → `{"uid", "name", "logged_in"}`; raises `auth_required` when logged out. |
| `require_identity(expected_uid=None, expected_name=None)` | Login gate for compatibility with older callers. Optional account arguments are ignored; logged-out sessions raise `auth_required`. |
| `publishing_constraints()` | Copy of verified constraints (see table below). |
| `list_albums()` | Stable album IDs/titles from `/reform-upload/album/choose`; read-only. |
| `list_album_tracks(album_id, expected_uid=None, expected_name=None, limit=None)` | Read-only newest-first track list with exact album/track guards and episode metadata. Optional account arguments are compatibility-only. |
| `download_owned_track_once(track, output_dir, expected_uid=None, expected_name=None)` | Requires login, revalidates one exact track, downloads the best directly playable CDN resource to a `.part`, probes it, then atomically renames it. Optional account arguments are compatibility-only. |
| `archive_matches(title)` | Exact normalized-title matches across the scheduled list and every album's complete track list; fails closed if any album cannot be read. |
| `prepare_upload(audio_file, title, expected_uid=None, expected_name=None, timeout=900)` | Exact-upload-page + login + duplicate + local-file gates, one upload, waits for row status `上传成功`. |
| `select_album(album_id, expected_name=None, timeout=15)` | Selects one exact stable album ID; refuses ambiguous duplicate titles before the title-scoped DOM click; verifies readback on `button[aria-label="选择专辑"]`. |
| `set_title(title, timeout=15)` | Required 节目标题 setter (max 40 UTF-16 code units). |
| `set_custom_cover(path, timeout=30)` | Local validation (square, ≥500×500, ≤10M, png/jpg/jpeg/bmp), uploads, confirms the crop modal once, returns server readback. |
| `set_description(text, timeout=15)` | Writes 节目简介 through the KindEditor iframe (select-all + insertHTML + blur) and verifies the hidden textarea sync. |
| `set_publish_mode(mode)` | `immediate` or `scheduled` only; toggles `button[aria-label="定时发布"]`. |
| `set_schedule_datetime(value, timeout=20)` | `YYYY-MM-DD HH:MM` in Asia/Shanghai; enforces the 2-hour minimum lead; drives the antd calendar; readback `YYYY-MM-DD HH:MM:00`. |
| `submission_snapshot()` | Read-only full form state (identity, upload rows, title, album, category, AI flag, cover, description, mode, schedule, submit state, modal, validation errors). |
| `submission_diagnostics()` | Bounded reason enum: `form_validation_failed`, `confirmation_required`, `platform_rejected`, `auth_required`, `result_delayed`, `click_not_accepted`, `submission_unverified`. |
| `manager_evidence(title, content_id=None, expected_schedule=None, attempts=3)` | Read-only manager/API reconciliation (scheduled list + album tracks); requires exact title, and exact content ID once known. |
| `submit_once(title, expected_uid=None, expected_name=None, expected_mode="scheduled", expected_schedule=None, run_marker="", timeout=600)` | Login-gated two stable snapshots, then ONE click on `确认发布` (plus at most one platform confirmation dialog click that is part of the same activation); read-only reconciliation afterwards. |
| `prepare_successor_upload(old_track, audio_file, timeout=900)` | 保活窄路径：仅当目标专辑恰有指定旧同标题节目且旧节目明确免费、公开并可删除时，准备一次同标题上传；其他专辑同名只作观察，不比较账号身份字段。 |
| `submit_successor_once(old_track, run_marker="", timeout=600)` | 保活窄路径：提交只激活一次，按目标专辑提交前后 track ID 集合差确认唯一 successor，再用 `track_evidence` 验证；未知结果 `retry=false`。 |
| `delete_once(submission, expected_uid=None, expected_name=None, confirm=False, timeout=180)` | Login-gated deletion of only the verified record created by this module (`created_by="ximalaya_domain_skill"`, `submit_clicks=1`, run marker in exact title, live record with exact content ID). |
| `delete_published_track_once(old_track, successor, confirm=False, timeout=180)` | 保活窄路径：要求 fresh 旧证据、已验证 successor、同专辑同标题、旧音频本地备份和 `confirm=True`；只删精确旧 ID 一次并双列表确认。 |
| `track_evidence(album_id, track_id, expected_title=None)` | Read-only exact-track evidence from the album list plus `/revision/track/simple`; paginates the album list and rejects missing, cross-album, title-mismatch, or duplicate matches. |
| `replace_sound_once(track, replacement_file, expected_uid=None, expected_name=None, confirm=False, timeout=900)` | Independent login-gated one-shot replacement of one exact track: requires a readable positive duration, one `替换声音` file attachment, optional one confirmation, then read-only same-track/media-change verification. |
| `update_track_description_once(track, description, expected_uid=None, expected_name=None, confirm=False, timeout=180)` | Login-gated edit of one exact published track: saves one normalized KindEditor description, reopens the page, and verifies the text plus unchanged adjacent fields. |
| `replace_track_cover_once(track, image_file, expected_uid=None, expected_name=None, confirm=False, timeout=180)` | Login-gated edit of one exact published track: validates and uploads one replacement cover, confirms one crop and one save, then verifies the changed cover path plus unchanged adjacent fields. |

### Read and download contract

`list_album_tracks()` uses the authenticated `/reform-upload/manage/album/tracks`
API with descending management order and paginates until the complete list is
read. It validates the decimal album ID before any request, requires a logged-in
session, rejects an empty album, cross-album rows, missing titles and
duplicate track IDs, and returns normalized `track_id`, `album_id`, `title`,
`episode_number`, `album_total`, `duration_seconds`, `audio_resource_id`, and
`account_uid` fields. `account_uid` is observation only and may be absent or
different without blocking. This is API-Level Automation: it does not navigate
or activate a browser tab.

`download_owned_track_once()` accepts only one exact track evidence dictionary.
It rechecks login and the live album/track/title tuple before requesting the
normal directly playable quality endpoint. Quality is
selected in the verified order `MP3_128 → M4A_64 → MP3_64 → MP3_32 → M4A_24`;
original uploads and paid/decryption paths are not used. The destination and
its `.part` are never overwritten. A completed file is accepted only after
size and FFprobe audio decoding succeed, then the temporary file is atomically
renamed. Any download or probe failure removes only the temporary file created
by this call and never retries a platform mutation.

### Replacement contract

`track_evidence()` requires nonempty decimal-string `album_id` and `track_id`.
It returns `track_id`, `album_id`, `album_name`, exact normalized `title`,
`duration_seconds`, `status`, `published_at`, `updated_at`, cover/description/
visibility/category/publish-state evidence, and non-secret audio evidence such as
`audio_resource_id` (`uploadId`) and `audio_resource_path` when available. The
album list endpoint is `GET /reform-upload/manage/album/tracks` with pages of 50;
the detail endpoint is `GET /revision/track/simple?trackId={trackId}`. The detail
API reports `ret=200`. No full media URL, headers, cookies, or tokens are stored.
Keepalive callers must also use its positive `is_paid=false`, public
`visibility`, published `publish_state` and (when exposed) `can_delete` fields;
a missing free/public/deletable signal is not treated as permission. `is_own`,
UID, display name and `account_uid` remain observational and are not gates.

`replace_sound_once()` requires `confirm is True`, a logged-in session, an exact
track evidence dict, and a fresh `track_evidence()` whose ID, album and title
still match. Account UID is not compared. Local audio extension/size validation
and FFprobe run before page navigation or file attachment. It navigates to
`https://www.ximalaya.com/reform-upload/page/sound/manage/{albumId}`, resolves the
row by exact track ID when exposed or exact title only after the API proves one
match, and opens the menu by the verified `mouseover` trigger, falling back to
a native coordinate click when the popover is not rendered. The menu is
`.ant-popover.sound-more-popover`; the sound item is `.item-2RWRS8jo[aria-label="替换声音"]`
with a `.webuploader-pick` child. The audio input is resolved as
`input[type=file].webuploader-element-invisible[accept*=".M4A"]` inside the
visible `替换声音` menu item. Wait until exactly one such input is mounted before
CDP file attachment; menu visibility alone does not prove uploader readiness.
Do not click the item to open a native file chooser. The accepted audio domain
is the same 11-format domain used by the upload form.

The method attaches at most once (`replacement_uploads=1`), records that fact
before waiting for processing. The replacement modal keeps its confirmation
disabled until upload progress reaches 100% and a new `fileId` exists; only
then does the enabled confirmation submit `trackId`, `fileId`, and `isVideo`
through `/reform-upload/manage/album//track/changeFile`. The method clicks a
replacement confirmation at most once when the platform exposes one. Success is `status="replaced"` with
`retry=False`, the same exact track ID/title/album, replacement duration within
one platform-rounded second, and a changed independent audio signal
(`audio_resource_id`, resource path, update time, or published/update evidence).
It also requires unchanged cover, description, visibility, category, status, and
publish state. A timeout, changed target, duplicate, or unchanged audio is
`status="replacement_unverified"`, `retry=False`; reconcile read-only and never
attach the file again. Replacing historical content requires separate exact
authorization and is not covered by the live test authorization.

### Keepalive successor and deletion contract

`prepare_successor_upload()` is the only path that may prepare a same-title
successor. It requires fresh `track_evidence()` for the exact old ID, positive
`isPaid=false`, public visibility and published state, and exactly one
same-title record in the target album. `isOwn`, UID and account names are not
compared. Other albums may contain the same title; they are observations only.
The local audio is validated before the upload page is touched.

`submit_successor_once()` keeps the immediate publish form stable and clicks
`确认发布` at most once. It compares the complete target-album ID set before
and after the click; `manager_evidence(title)` or the first same-title row is
never used as the new ID. A non-unique set difference or uncertain response
returns `submission_unverified` with `retry=false`, leaving the old record.

`delete_published_track_once()` is separate from the test-record-only
`delete_once()`. Before its single `POST /reform-upload/manage/album/track/delete`
it rechecks both exact IDs, same album/title, free/public eligibility, and a
complete local backup of the old audio. After activation it only reads the
target album lists: success requires the old ID absent and the new ID still
unique. Timeout or any uncertainty returns `deletion_unverified` with
`retry=false`; never delete the new ID or issue a second POST.

### Published-track description and cover edits

Both edit capabilities require `confirm=True`, a logged-in session, and a fresh
exact `track_evidence()` result. They use
the direct edit URL
`https://www.ximalaya.com/reform-upload/page/sound/edit/{trackId}`. The page's
KindEditor iframe is updated through its editor/Form API, not by guessing a
contenteditable node. The cover flow validates a local square png/jpg/jpeg/bmp
before navigation, attaches it to the anonymous image input
`input[type=file][accept*="png"]`, waits for the crop modal, and confirms the
crop once.

The edit form's `richIntro` rule performs a debounced remote text check. After
programmatic description or cover changes, the helper first waits for one full
form validation to finish through host-side bounded polling; otherwise an
earlier field validation can consume the callback and prevent the business
update request. It then locates one visible enabled `保存` button, clicks it
once, and reopens the same edit URL.

Description and cover verification uses the authenticated creator endpoint
`/reform-upload/anchorTrack/edit?trackId={trackId}` plus the reopened edit page.
The public `/revision/track/simple` response can lag after an edit and is not
authoritative for these two fields. Success requires exact target identity and
unchanged audio, description/cover as applicable, visibility, category,
publish state and status. A post-save timeout or mismatched readback returns a non-retryable
`description_update_unverified` or `cover_replacement_unverified` result with
the counters and last evidence; it never uploads or saves again.

## Verified limits (evidence levels, verified 2026-09-07)

| Constraint | Value | Level |
| --- | --- | --- |
| Audio formats | AIFF/AIF/MP3/WMA/WAV/FLAC/OGG/MP2/AAC/AMR/M4A (11) | enforced (input accept + UI copy) |
| Audio size | min 1 MB, max 1 GB | declared_and_correlated |
| Audio bitrate | ≥64 kbps recommended; below accepted with exposure-limit warning | enforced_as_warning |
| Title | max 40 UTF-16 code units, counter N/40 | enforced |
| Cover formats | png/jpg/jpeg/bmp | enforced |
| Cover size | min edge 500, <10 MB, ≥1000×1000 recommended | declared + accepted(1080×1080) |
| Crop semantics | 1280×720 center-cropped to 1000×1000; 1080×1080 stored verbatim | accepted |
| Schedule timezone | Asia/Shanghai | accepted |
| Min lead | 2 hours, minute precision (hour/minute options disabled earlier) | enforced |
| Max horizon | none client-side (UI navigable to 2028-12); server horizon unproven | client_observed_server_unknown |
| Granularity | minute (seconds fixed 00) | enforced |
| Schedule display | `YYYY-MM-DD HH:MM:00` | accepted |
| Required fields | 节目标题, 分类 (auto from album), 节目类型 | enforced (ant-form-item-required + defaults) |
| Defaults | 免费, AI=否, 权限=公开, 知识产权承诺 checked | accepted |

## Workflow example (scheduled)

```python
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.py").read())
require_identity()
archive_matches(title)  # must be empty
prepare_upload(audio_file, title)
select_album(album_id, album_name)
set_title(title)
set_custom_cover(cover_file)
set_description(description)
set_publish_mode("scheduled")
set_schedule_datetime(schedule)
submission_snapshot(); wait(2); submission_snapshot()   # must be identical
submission = submit_once(title, expected_mode="scheduled",
                         expected_schedule=schedule, run_marker=run_marker)
delete_once(submission, confirm=True)
```

Immediate mode: same flow with `set_publish_mode("immediate")`, no schedule,
`expected_mode="immediate"`.

## Recovery tables

### Submission

| Observation | Meaning | Allowed action |
| --- | --- | --- |
| `status="verified"` | Record proven by manager/API, exact title + content ID | proceed to `delete_once` |
| `status="submission_unverified"` | Click happened; acceptance unproven | READ-ONLY reconciliation only (`manager_evidence` / manager pages). NEVER re-click, never re-upload, never change the title. |

### Deletion

| Observation | Meaning | Allowed action |
| --- | --- | --- |
| `status="deleted"` | Exact content ID absent from scheduled list + album tracks | done |
| `status="deletion_unverified"` | Delete clicked; absence unproven | READ-ONLY exact-ID polling until absence proven |

### Replacement

| Observation | Meaning | Allowed action |
| --- | --- | --- |
| `status="replaced"` | Exact track identity preserved and new audio evidence verified | Continue with exact authorized cleanup only |
| `status="replacement_unverified"` | File attachment occurred, but replacement result is not proven | READ-ONLY `track_evidence()` reconciliation; never call replacement again |
| `status="description_update_unverified"` | Description save was activated, but reopen/readback or adjacent-field verification is not proven | READ-ONLY `track_evidence()`/edit-page reconciliation; never save again |
| `status="cover_replacement_unverified"` | Cover upload/crop/save was activated, but changed cover or adjacent-field verification is not proven | READ-ONLY `track_evidence()` reconciliation; never upload, crop or save again |

Replacement counters are part of the result: `replacement_uploads` must be `1`
after attachment and `replacement_confirms` is `0` or `1`. An unknown result is
never a retry invitation.

Deletion paths (verified selectors):

- Immediate record: album track manager `https://www.ximalaya.com/reform-upload/page/sound/manage/{albumId}`
  → row `.track-1Tfey3X4` → `.manage-point-box-3qWnOYcX` → popover
  `.ant-popover.sound-more-popover` → `删除` item → custom `.xmDeleteModal`.
  The final application request is `POST /reform-upload/manage/album/track/delete`
  with JSON `{trackId}`; verify absence through the album APIs after the request.
- Scheduled record: `https://studio.ximalaya.com/timePublish`
  (iframe `https://www.ximalaya.com/reform-upload/page/time-publish`)
  → row containing exact title → the single 取消/删除/撤销 control in that row
  → confirm dialog.

## Known-good states

- Upload form after `prepare_upload`: one row with `上传成功` (`.success-FnKHWloK`).
- Cover set: 节目配图 area shows `更换图片` / `重新裁剪` + server thumbnail.
- Scheduled armed: switch `aria-checked=true`, `input.ant-calendar-picker-input`
  value = `YYYY-MM-DD HH:MM:00`, submit enabled, no modal, no validation error.
- Submit control: `button[aria-label="确认发布"]` (text 确认发布).

## Field checklist before submit

节目标题 (=requested, ≤40 units) · 选择专辑 (exact readback) · 分类 (non-empty) ·
节目类型 (免费) · 是否AI合成 (否) · 节目配图 (readback OK) · 节目简介 (synced) ·
定时发布 switch + datetime (scheduled only) · 知识产权承诺 (checked) ·
submit enabled · no modal · no validation error.

## Browser/tab cleanup

- Only close Targets returned by your own `new_tab()` or the explicit fullscreen `Target.createTarget(newWindow=True)` exception; close by exact target ID.
- `protect_tab` during work; `unprotect_tab` before closing.
- Keep the task Target's Browser window `minimized` when attaching. A fullscreen
  original window must not be restored or directly minimized; use the separate
  already-minimized window above and verify its state before any platform write.
  Never call `activate_tab()`, pass
  `activate=True`, call `Target.activateTarget` or call `Page.bringToFront`.
- Agent Pool serializes each browser; never bypass the pool with a raw CDP URL.

## Live evidence

Run-specific IDs, titles, media paths, mutation counters, failures, and cleanup
state belong in the Evidence Ledgers, not this durable Domain Skill. Before
recovering an interrupted mutation, read the relevant ledger under `/tmp` and
reconcile the exact server state; never infer retry safety from this document.

Live verification on 2026-09-08 confirmed the durable replacement contract:
one exact-track M4A attachment plus one enabled confirmation preserved the
track ID, title, and album; duration changed from 90 to 268 platform-rounded
seconds and the upload resource ID changed. The same current-run test record
was then deleted through the verified immediate-record API and exact-title/ID
reconciliation returned zero matches.
