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

1. `new_tab(UPLOAD_URL)`; `protect_tab(target, owner=..., purpose=...)`.
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
| `delete_once(submission, expected_uid=None, expected_name=None, confirm=False, timeout=180)` | Login-gated deletion of only the verified record created by this module (`created_by="ximalaya_domain_skill"`, `submit_clicks=1`, run marker in exact title, live record with exact content ID). |
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
`input[type=file].webuploader-element-invisible[accept*=".M4A"]` after the
sound uploader is attached; the accepted audio domain is the same 11-format
domain used by the upload form. The historical discovery run did not activate
that file chooser or attach a file to any historical sound.

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

- Only close tabs your own `new_tab()` returned; close by exact target ID.
- `protect_tab` during work; `unprotect_tab` before closing.
- `new_tab()` must create a background Target. Keep its Browser window
  `minimized` when attaching; never call `activate_tab()`, pass
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
