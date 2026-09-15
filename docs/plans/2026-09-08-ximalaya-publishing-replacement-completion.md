# Ximalaya Publishing Completion and Sound Replacement Implementation Plan

> Historical execution record. Current runtime authorization is defined by
> `agent-workspace/domain-skills/ximalaya/publishing.md`: a logged-in managed
> browser is sufficient; UID and display-name comparisons are not authorization
> gates.

> **Executor:** Low-capability autonomous agent. You have no prior conversation context. Read this file from the first line, load every required Skill, reconstruct actual state, and execute literally. Do not delegate, infer omitted permissions, widen scope, or repeat an external mutation after an ambiguous result.

**Outcome:** Finish the interrupted Ximalaya publishing work, remove the still-online prior test record, add a standalone guarded sound-replacement capability to the existing Ximalaya Domain Skill, prove it by publishing one new test sound into album `7980411`, replace only that new sound's audio once, verify the same track now serves the replacement media, delete the test sound, and complete the original final audit.

**Done when:** Prior test record `1012239040` is absent; `track_evidence()` and `replace_sound_once()` are documented and unit-tested; exactly one new immediate test sound is created in album `7980411`, verified, replaced once from the fixed MP3 fixture to the fixed M4A fixture while preserving exact track ID/title/album and changing audio evidence, then deleted; focused tests, the complete suite, Domain Skill verification, syntax, diff, registry discovery, account cleanup, browser cleanup, and scope checks all pass; no historical sound or album is modified.

**Workspace root:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Repository root:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Plan file:** `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-09-08-ximalaya-publishing-replacement-completion.md`

**Previous plan:** `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-09-07-ximalaya-publishing-domain-skill.md`

**Previous evidence:** `/tmp/browser-harness-ximalaya-publishing-20260907/evidence.md`

**New evidence directory:** `/tmp/browser-harness-ximalaya-replacement-20260908`

**New evidence ledger:** `/tmp/browser-harness-ximalaya-replacement-20260908/evidence.md`

**Target environment:** Local development on macOS Darwin, `/bin/zsh`, Asia/Shanghai, repository `main`, managed Chrome `SAU-自媒体运营-2号-9226`, account `水蜜桃英语` / UID `77566037`.

**Execution mode:** `unattended`. The user has already settled the exact live publication, replacement, and cleanup batch described below. Continue autonomously through that batch; stop only for login/MFA/captcha/consent, identity mismatch, historical-record ambiguity, an external mutation outside the confirmed batch, or another explicit stop condition.

**Execution environment:** On 2026-09-08 06:52 CST the author verified Python 3.14.6, `uv 0.11.7`, Browser Harness current-checkout version 0.1.9, `playwright-cli 0.1.19`, `rtk 0.43.0`, CodeGraph 1.4.1, FFmpeg/FFprobe, network access, writable repository, and readable media fixtures. Browser 9226 was `running`, `health=ok`, with no lease or write lock. Browser Harness reported 0.1.13 available; updating Browser Harness is not authorized and must not occur in this plan.

**Architecture/approved approach:** Extend the existing Ximalaya Domain Skill in place; do not add a second module or a generalized publisher framework. Keep replacement as an independent public operation with its own exact-record lookup, confirmation guard, single-upload state machine, diagnostics, and verification. Use Browser Harness and Agent Pool for all authenticated interactions; Playwright CLI is optional and read-only for resolving DOM/network ambiguity. Live replacement must target only a new test record created by this plan, never one of album `7980411`'s historical sounds.

**Tech stack:** Python 3.11+; current Python 3.14.6; `cdp-use==1.4.5`, `fetch-use==0.4.0`, `pillow==12.3.0`, `websockets==15.0.1`; pytest through `uv run --with pytest`; Browser Harness CDP helpers; JSON registry version 1.

## Required Skills

- `writing-plans`
  - SKILL.md: `/Users/yelin/.codex/skills/writing-plans/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/writing-plans/references/lessons.md`
  - Use for: literal execution, Progress Ledger, state reconstruction, safety boundaries, and completion proof.
- `ponytail:ponytail`
  - SKILL.md: `/Users/yelin/.codex/plugins/cache/devkeeper-ponytail-local/ponytail/4.8.4/skills/ponytail/SKILL.md`
  - Lessons: `none found`
  - Use for: reuse the existing Ximalaya module, make the smallest root-cause edits, remove the duplicate test rather than preserving dead duplication, and avoid dependencies/abstractions.
- `browser-fleet-manager`
  - SKILL.md: `/Users/yelin/.codex/skills/browser-fleet-manager/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/browser-fleet-manager/references/lessons.md`
  - Use for: verify browser name, port, Profile, health, process, and CDP endpoint before every browser session.
- `playwright-cli`
  - SKILL.md: `/Users/yelin/.agents/skills/playwright-cli/SKILL.md`
  - Lessons: `none found`
  - Use for: optional read-only snapshots/request inspection after Browser Fleet `audit` and `resolve`; never for final mutation implementation.
- `browser-harness`
  - SKILL.md: `/Users/yelin/Developer/agent-tools/browser-harness/SKILL.md`
  - Lessons: `none found`
  - Use for: Agent Pool leases, `new_tab`, `page_info`, Domain Skill loading, task-owned tabs, CDP/DOM/AX inspection, file upload, and live verification.
- Browser Harness interaction references
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/uploads.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/network-requests.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/tabs.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/dialogs.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/dropdowns.md`
  - Lessons: `none found`
  - Use for: exact file input, network correlation, popover/dialog behavior, and precise task-tab cleanup.

Read every listed file in full before its first use. Also read the previous plan and previous evidence in full before changing repository or external state.

## Applicable Rules

- `/Users/yelin/Developer/agent-tools/browser-harness/AGENTS.md`: use `./browser-harness`; paths in commands are double-quoted; RTK is default and raw output is mandatory for destructive/audit ambiguity; only edit agent website code under `agent-workspace/`; preserve unrelated work; no unrequested commit, push, branch, reset, or production action.
- `/Users/yelin/Developer/agent-tools/browser-harness/CLAUDE.md`: follow `AGENTS.md`; use the checkout launcher.
- `/Users/yelin/Developer/agent-tools/browser-harness/SKILL.md`: first navigation uses `new_tab(url)`, then `wait_for_load()` and `page_info()`; read all returned `domain_skill_files` before site-specific action; publishing/replacement/deletion use Agent Pool `--mode write --account "77566037"`; close only exact task-owned tabs.
- Browser Fleet: personal/unmanaged/conflicted/stopped/unhealthy browsers are forbidden; do not start, stop, migrate, rename, retire, restore, or delete any browser/Profile; do not print command lines, cookies, tokens, passwords, or verification codes.
- File edits: use `apply_patch`; do not reset, revert, reformat, or overwrite existing Bilibili changes or completed Ximalaya work.
- CodeGraph: use the existing index before broad source reading. After code edits run `codegraph sync "/Users/yelin/Developer/agent-tools/browser-harness"` before relying on `affected` results.
- Browser selection is fixed to 9226 for this recovery because live identity was re-proven; browser name is still not authoritative, and every mutation must recheck UID/name.
- One agent only. Do not spawn sub-agents or run concurrent mutations against the account.

## Confirmed Authorization and Absolute Prohibitions

On 2026-09-08 the user explicitly confirmed this exact external batch:

1. Delete prior test record `1012239040`, exact title `BH喜马定时验收3-BHXM-20260907T155347-ba1fdb89`, only after UID/title/ID/album evidence matches.
2. Create exactly one new immediate test sound in account `77566037`, album `7980411`.
3. Replace the audio of only that newly created current-run test sound once.
4. Verify replacement, then delete only that current-run test sound.

The authorization does not include replacing, editing, hiding, or deleting any historical sound. It does not include creating/editing/deleting an album, changing metadata on an existing record, publishing a second new record, updating Browser Harness, Git commit/push, or production promotion.

Do not ask the user to reconfirm the same exact batch. If any exact target or blast-radius condition differs, stop before mutation and request new authorization using the repository's danger format.

## Fixed Identities and Fixtures

- Account UID: `77566037`
- Account name: `水蜜桃英语`
- Managed browser: `SAU-自媒体运营-2号-9226`
- CDP endpoint returned by Browser Fleet at author time: `http://127.0.0.1:9226`; resolve again at execution time and use the returned value only through Agent Pool.
- Replacement test album ID: `7980411`
- Replacement test album name: `慢速英语听力故事 | 初中每日英语听力训练`
- Album manager URL: `https://www.ximalaya.com/reform-upload/page/sound/manage/7980411`
- Studio works URL: `https://studio.ximalaya.com/opus`
- Direct upload URL: `https://www.ximalaya.com/reform-upload/page/webCenter/upload`
- Prior record ID: `1012239040`
- Prior record title: `BH喜马定时验收3-BHXM-20260907T155347-ba1fdb89`
- Prior record album ID/name: `88294964` / `雅思口语播客 | 雅思口语常考话题 | 英语磨耳朵`
- Prior verified submission record: `/tmp/browser-harness-ximalaya-publishing-20260907/scheduled_submission.json`
- Initial audio for new replacement test:
  - `/Users/yelin/Documents/english-media-materials/daily-news-podcast-selection/2026-07-10/source-profile-upload-smoke-20260710/notebooklm-robotaxi-90s-source-profile-smoke.mp3`
  - MP3, 44.1 kHz stereo, 90 seconds, 1,080,979 bytes.
- Replacement audio:
  - `/Users/yelin/Documents/english-media-materials/daily-news-podcast-selection/2026-08-28/candidate-03-death-of-the-kiss-dating/notebooklm/regenerate-20260828/audio-new.m4a`
  - AAC in M4A container, 44.1 kHz stereo, 268.329796 seconds, 8,636,680 bytes.
- Cover:
  - `/tmp/browser-harness-ximalaya-publishing-20260907/covers/square_1080.png`
  - Previously accepted as 1080×1080; revalidate existence/dimensions before reuse.

## Current-State Evidence

- Repository root: `/Users/yelin/Developer/agent-tools/browser-harness`.
- Branch/HEAD: `main` at `fd5195bcea8896a809c99240898831753e20bd99`, behind `origin/main` by one commit. Do not fetch, pull, merge, rebase, reset, switch branch, or create a worktree.
- The earlier report's phrase “git clean” meant tests/diff hygiene, not an empty working tree. Actual state is intentionally dirty/untracked:
  - modified `agent-workspace/domain-skills/bilibili/publishing.py`;
  - modified `tests/unit/test_bilibili_publishing.py`;
  - modified `agent-workspace/domain-skills/registry.json`;
  - untracked `agent-workspace/domain-skills/ximalaya/`;
  - untracked `tests/unit/test_ximalaya_publishing.py`;
  - untracked previous plan.
- Existing Ximalaya implementation: `publishing.py` 1090 lines; `publishing.md` 150 lines; unit test file 663 lines.
- Author rerun on 2026-09-08: focused Ximalaya `24 passed`; full suite `364 passed`; Domain Skill verifier `PASS registry=103 skills`; `git diff --check` clean.
- Test file currently defines `test_title_setter_dispatches_framework_events` twice. Python replaces the first function binding, so only 24 tests collect. Delete one exact duplicate; do not rename identical code and pretend it adds coverage.
- Browser 9226: running, healthy, no lease/write lock; account identity was re-proven by same-origin API and visible UI in the prior run.
- `https://studio.ximalaya.com/opus` loads as authenticated “创作中心-喜马拉雅”.
- Album manager `https://www.ximalaya.com/reform-upload/page/sound/manage/7980411` loads as authenticated “声音管理”; track-list API returned at least 50 records. The URL identifies an album, not one track.
- Historical examples in album `7980411` include track IDs `515194156`, `515192089`, `486406328`, and many others. They are evidence only and must never become replacement targets.
- Per-track menu was previously mapped to `编辑`, `替换声音`, `替换视频`, `剪辑声音`, and `删除`; current Domain Skill has deletion helpers but no replacement method.
- Prior test record `1012239040` has crossed its scheduled time. A read-only query on 2026-09-08 found it in the ordinary album-track list as mode `immediate`, album `88294964`. The stored submission originally says mode `scheduled`; current `delete_once()` branches on that stale mode and would navigate the wrong page. Fix this root cause before deletion.
- No replacement or deletion was performed by the plan author.

## Scope

### In scope

- Recover the old checkpoint without replaying prior submit attempts.
- Make `delete_once()` use exact live record state when a scheduled record has auto-published.
- Delete prior test record `1012239040` exactly once and verify absence.
- Add read-only exact-track evidence and independent guarded sound replacement to the existing Ximalaya module.
- Discover only the replacement-specific input, upload, confirmation, request, state, and verification contract missing from existing evidence.
- Publish one immediate test sound into album `7980411` with a new unique run marker.
- Replace that one new test sound from the 90-second MP3 to the 268.329796-second M4A once.
- Verify stable track ID/title/album and changed audio evidence without creating a second track.
- Delete the new test sound exactly once.
- Update documentation/tests/evidence and complete the original final audit.

### Out of scope

- Any historical sound in album `7980411` or another album.
- Title, description, cover, album, visibility, price, category, AI declaration, tags, or publish-time changes during replacement.
- Replacing video, clipping audio, editing a historical record, creating/deleting albums, or testing bulk replacement.
- More than one new live record, more than one replacement-file attachment, repeated confirm clicks, or any retry after an ambiguous mutation.
- Browser Harness core, dependencies, production snapshot, browser/Profile lifecycle, SAU, scheduler/Cron, Git branch/commit/push/PR, or upstream synchronization.

## Execution Contract

- Begin by reading this plan, previous plan, previous evidence, required Skills, current Git state, current code, current tests, Agent Pool state, and live record state.
- Initialize or resume the New Evidence Ledger. Never overwrite previous evidence.
- Generate one new replacement run marker once and persist it before upload:
  ```bash
  python3 -c 'from datetime import datetime; from uuid import uuid4; from zoneinfo import ZoneInfo; print("BHXMR-" + datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8])'
  ```
- The exact new title is `BH喜马替换验收-` followed by the persisted marker. This is 39 UTF-16 code units for the defined marker shape and stays within the verified limit of 40.
- Every mutation rechecks UID `77566037` and exact name.
- Every record mutation requires exact album ID, track ID, exact normalized title, and live unique match. Row position, newest record, fuzzy title, or prefix-only matching is forbidden.
- Treat file attachment to the `替换声音` input as the start of a potentially destructive operation. Persist `replacement_uploads=1` before waiting for the server/UI result.
- Submission, replacement, and deletion each permit one activation only. Unknown outcome means read-only reconciliation, never replay.
- Do not log request headers, cookies, tokens, authorization values, complete request bodies, phone numbers, listener data, or complete page dumps. Log only origin/path, method, status, field names/types/lengths, non-secret account/album/track IDs, timestamps, media metadata, and visible state.
- Close only task-owned tabs by exact target ID after `unprotect_tab`; never scan-close by URL.
- Do not mark complete while either test record remains or any lease/write lock is held.

## State Machine

- `resume_preflight`: no new mutation by this plan.
- `prior_delete_armed`: exact old record is uniquely live and four-way guard passes.
- `prior_delete_unknown`: delete activated once; only read-only reconciliation allowed.
- `prior_deleted`: `1012239040` absent or terminally deleted.
- `replacement_discovered`: replacement UI/network contract recorded; no historical record changed.
- `immediate_submit_armed`: new test form has two identical valid snapshots.
- `immediate_submit_unknown`: submit activated once; only read-only reconciliation.
- `immediate_verified`: exact new track ID/title/album proven.
- `replacement_armed`: exact before snapshot and replacement media metadata persisted.
- `replacement_unknown`: replacement file attached/confirmed once; only read-only reconciliation.
- `replacement_verified`: same track ID/title/album, different audio fingerprint/duration/update evidence, no duplicate.
- `new_delete_unknown`: new test record deletion activated once; only read-only reconciliation.
- `new_deleted`: new test record absent or terminally deleted.
- `complete`: all tests/audits pass and both test records are absent.

Never move from an `unknown` state back to its preceding `armed` state.

## Requirement Traceability

| Requirement | Source | Implemented by | Verified by |
| --- | --- | --- | --- |
| Finish original interrupted work | User | Tasks 1, 4, 6, 7 | Both test IDs absent; final audit passes |
| Delete auto-published old scheduled record | Prior checkpoint + confirmation | Task 1 | Exact ID/title/album absence |
| Standalone sound replacement | User | Tasks 2–3 | Public methods, tests, docs |
| Use album `7980411` without touching history | User URL + safety confirmation | Tasks 2, 4–6 | Exact new marker/track ID and historical count invariant |
| Replace once and verify real media change | User | Task 5 | Before/after evidence and one replacement upload |
| Preserve track identity/metadata | Safety requirement | Task 5 | Same track ID/title/album and unchanged non-audio fields |
| Complete immediate publication | Original plan | Task 4 | One verified immediate record |
| Delete new replacement test | Confirmation | Task 6 | Exact new track absence |
| Browser Harness is final deliverable | User | Tasks 3 and 7 | Existing module/docs/tests only; no runtime Playwright dependency |
| Protect unrelated code and external content | Repository/user | All tasks | Diff audit and historical-record invariants |

## Progress Ledger

| Task | Status | Completion evidence |
| --- | --- | --- |
| Task 0 — Resume and baseline | complete | 2026-09-08: direct-origin read-only reconciliation proved exact account and unique prior ID/title/album; marker/title persisted in `/tmp/browser-harness-ximalaya-replacement-20260908/evidence.md`; focused 24 and full 364 baseline, registry 103, fleet/pool healthy, diff check clean. |
| Task 1 — Fix cross-day deletion and remove `1012239040` | pending | `delete_once()` now uses exact live mode/album and permits only scheduled→immediate; duplicate test removed; focused 25 and full 365 pass. One menu delete activation reached a blocking confirmation/result boundary; state is `prior_delete_unknown`, exact ID still present, and no retry is permitted without new authorization. |
| Task 2 — Replacement-only live discovery | complete | Read-only manager discovery: album `7980411` baseline 62; historical menu trigger/operation structure; track list + `/revision/track/simple` detail fields; no historical file chooser activation or mutation. Evidence ledger `Task 2 replacement discovery`. |
| Task 3 — Replacement implementation, tests, and docs | complete | Added `track_evidence()`/`replace_sound_once()`, native-confirm-safe menu helper, docs, removed exact duplicate, added 8 tests; focused 33, full 373, registry 103, py_compile, CodeGraph sync and diff check pass. |
| Task 4 — One immediate test publication in album `7980411` | complete | Three disposable form-stage MP3 attachments were used while diagnosing unstable cover snapshots; only one final form was submitted. Exact account and stable final snapshots; one submit activation; new ID `1012564622` in album `7980411`; `track_evidence()` before proves 90.0s MP3, album count 63. |
| Task 5 — Replace only the new test sound once | pending | One exact M4A attachment occurred (`replacement_uploads=1`); single 900-second read-only reconciliation ended with same ID/title/album, unchanged 90.0s duration/uploadId/timestamps; state `replacement_unknown`; no retry permitted. |
| Task 6 — Delete only the replaced test sound | pending | — |
| Task 7 — Final regression and account/browser audit | pending | Safe audits pass: focused 33, full 373, registry 103, syntax, CodeGraph, diff check, secret scan, exact Domain Skill discovery, healthy fleet, and no pool lease. Completion is blocked because prior ID `1012239040` remains after one unknown delete activation and current-run ID `1012564622` remains unchanged after one replacement attachment; plan forbids retries/deletion before replacement verification. |

Update this table with `apply_patch` only after fresh evidence proves the task acceptance.

## File Map

| Action | Absolute path | Responsibility |
| --- | --- | --- |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.py` | Live-mode deletion recovery, exact track evidence, one-shot replacement, diagnostics, verification |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.md` | Replacement public contract, workflow, risks, recovery, and live acceptance |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_ximalaya_publishing.py` | Remove exact duplicate test and add cross-day deletion/replacement tests |
| Preserve | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/registry.json` | Existing Ximalaya mapping already correct; no further registry edit expected |
| Preserve | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py` | Pre-existing unrelated user change |
| Preserve | `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_bilibili_publishing.py` | Pre-existing unrelated user change |
| Create temporary | `/tmp/browser-harness-ximalaya-replacement-20260908/evidence.md` | Append-only sanitized recovery/replacement ledger |

## Interface Contracts

### Existing contract correction

- `delete_once(submission: dict[str, Any], expected_uid: int, expected_name: str | None = None, confirm: bool = False, timeout: int = 180) -> dict[str, Any]`
  - Preserve the existing signature.
  - After exact identity and submission guards, call `archive_matches(title)` and require one exact content-ID match.
  - Route deletion using the live matched record's `mode` and `album_id`, not stale `submission["mode"]` or the module default album.
  - Permit only the real transition `submission.mode == "scheduled"` to live `mode == "immediate"` after the scheduled time. Any other contradictory mode/album/ID/title state is a scope violation.
  - Return the existing result shape and add `live_mode` when useful for evidence.

### New read-only method

- `track_evidence(album_id: str, track_id: str, expected_title: str | None = None) -> dict[str, Any]`
  - Inputs are nonempty decimal-string album/track IDs and optional exact normalized title.
  - Fetch the exact album track list/detail endpoint discovered in Task 2; paginate until the ID is found or the documented bound is reached.
  - Require exactly one matching track ID and exact album ID. When `expected_title` is supplied, require exact normalized equality.
  - Return at least `track_id`, `album_id`, `title`, `duration_seconds`, `status`, `published_at`, `updated_at`, and any non-secret audio resource identifier/hash/URL path that can prove media change.
  - Return only fields actually observed; use an empty string for unavailable timestamps, but replacement acceptance still requires at least duration change plus one independent changed-audio signal.
  - Side effects: read-only.

### New independent replacement method

- `replace_sound_once(track: dict[str, Any], replacement_file: str, expected_uid: int, expected_name: str | None = None, confirm: bool = False, timeout: int = 900) -> dict[str, Any]`
  - `confirm` must be exactly `True` before page mutation.
  - Validate replacement file through the existing local audio validator and FFprobe metadata logic before browser mutation.
  - Require exact account, nonempty exact `track_id`, `album_id`, `title`, and a fresh live `track_evidence()` equal to the caller's immutable identity fields.
  - Navigate to `SOUND_MANAGE_URL + album_id`; open the exact row by track ID when the DOM exposes it, otherwise by exact title only after API proof shows one unique track. Prefix/fuzzy/row-position matching is forbidden.
  - Open only the `替换声音` menu item. Resolve its actual hidden file input and accepted formats from Task 2 evidence.
  - Attach the file once. Persist `replacement_uploads=1` before waiting. If the platform exposes a confirmation button, activate it at most once and persist `replacement_confirms=1`.
  - Do not change title, album, cover, description, visibility, price, category, AI declaration, tags, or other metadata.
  - Reconcile read-only until exact same track ID/title/album is present and new audio evidence matches the replacement fixture: duration approximately 268.329796 seconds within the platform's observed rounding tolerance, plus changed media URL/resource ID/update time/request result.
  - Verified return: `status="replaced"`, `replacement_uploads=1`, `retry=False`, exact identity fields, `before`, `after`, replacement path/metadata, and verification source.
  - Ambiguous return: `status="replacement_unverified"`, `replacement_uploads=1`, `retry=False`, diagnostics, and last before/after evidence. Never expose a retry flag.
  - A second track, changed track ID/title/album, unchanged audio evidence after deadline, or multiple matches is not success.

## Task 0: Resume the interrupted work from actual state

**Purpose:** Prevent stale-report assumptions and external replay.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** safe.

- [ ] Read this plan, all Required Skills, previous plan, previous evidence, `AGENTS.md`, `CLAUDE.md`, current Ximalaya module/docs/tests, and current Git diff.
- [ ] Run:
  ```bash
  pwd
  git branch --show-current
  git rev-parse HEAD
  RTK_DISABLED=1 git status --porcelain=v1 --branch
  codegraph status "/Users/yelin/Developer/agent-tools/browser-harness" --json
  RTK_DISABLED=1 python3 "/Users/yelin/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py" audit
  RTK_DISABLED=1 python3 "/Users/yelin/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py" resolve --name "SAU-自媒体运营-2号-9226"
  ./browser-harness agent-pool status --browser "SAU-自媒体运营-2号-9226"
  rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"
  rtk uv run --with pytest pytest -q
  rtk python3 "scripts/verify_domain_skills.py"
  RTK_DISABLED=1 git diff --check
  ```
- [ ] Expected baseline: focused 24 pass; full 364 pass; registry 103 pass; browser healthy/no conflict; dirty paths match Current-State Evidence. If counts grow because another valid user change landed, record exact all-pass counts. Do not clean/reset/update.
- [ ] Create `/tmp/browser-harness-ximalaya-replacement-20260908` with `mkdir -p`, then create/resume `evidence.md` using `apply_patch`. Persist environment, old checkpoint, exact authorization, run marker, title, mutation counters, before/after snapshots, tests, and cleanup state.
- [ ] Reconcile prior title/ID read-only. Require exactly one current record with ID `1012239040`, title exact, album `88294964`, and account exact. Record its current live mode/state. If absent, mark `prior_deleted` and skip Task 1's live delete; if ambiguous, stop.

**Task 0 acceptance:** Baseline and exact external state are recorded; no mutation occurred; new run marker/title are persisted once.

## Task 1: Fix cross-day deletion and remove the prior test record

**Purpose:** Complete the original cleanup safely after a scheduled record moved into the published track list.

**Risk level:** code edit plus pre-authorized exact deletion.

- [ ] Use `apply_patch` to change `delete_once()` so its route and album come from the one exact live match. Do not change its public signature or weaken existing guards.
- [ ] Add exact unit test `test_delete_once_uses_live_mode_after_scheduled_record_auto_publishes`. Fixture submission says scheduled; live match says immediate with album `88294964`; expected behavior opens ordinary sound manager for live album and deletes once.
- [ ] Delete one of the two byte-equivalent `test_title_setter_dispatches_framework_events` definitions. Preserve the remaining one unchanged.
- [ ] Run:
  ```bash
  uv run python -m py_compile "agent-workspace/domain-skills/ximalaya/publishing.py" "tests/unit/test_ximalaya_publishing.py"
  rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"
  rtk uv run --with pytest pytest -q
  RTK_DISABLED=1 git diff --check
  ```
- [ ] Before live deletion, recheck account, exact ID/title/album, current live mode, and unique match. Persist `prior_delete_armed`.
- [ ] Call `delete_once()` once with the persisted verified prior submission dict, UID/name, and `confirm=True`. Persist `prior_delete_unknown` immediately after activation.
- [ ] If ambiguous, use only exact-ID/title read-only reconciliation. Never click delete again.
- [ ] Mark `prior_deleted` only after both scheduled list and album track list contain no exact ID/title match.

**Task 1 acceptance:** Old test ID/title absent; delete activation count exactly one for this resumed execution; no other record changed; focused/full tests remain green.

## Task 2: Discover only the missing sound-replacement contract

**Purpose:** Obtain exact selectors/endpoints/states necessary for replacement without touching historical tracks.

**Risk level:** read-only page/menu inspection. Do not attach a file to a historical track.

- [ ] Enter an Agent Pool read lease for browser 9226/site `ximalaya.com`/account `77566037`.
- [ ] `new_tab("https://www.ximalaya.com/reform-upload/page/sound/manage/7980411")`, protect target, `wait_for_load()`, print/check `page_info()`, then read every returned Domain Skill Markdown file.
- [ ] Recheck identity. Enumerate API track IDs/titles and DOM rows only to understand exact row identity; record that historical IDs are forbidden.
- [ ] Open one historical row's “more” menu only far enough to inspect `替换声音` item structure. Do not activate its file chooser, attach a file, confirm, or call a replacement endpoint.
- [ ] Inspect frontend assets/DOM/network metadata to identify:
  - exact replacement menu/item and file-input selector;
  - whether selecting a file immediately mutates the server or only uploads a candidate;
  - upload endpoints, progress/completion/error signals;
  - confirmation dialog/control and whether it is mandatory;
  - track-list/detail endpoint fields that prove old/new duration and media identity;
  - rounding/propagation delay for duration;
  - whether replacement preserves track ID, title, album, cover, description, visibility, and URL.
- [ ] If Browser Harness evidence is ambiguous, rerun Browser Fleet audit/resolve, attach Playwright session `managed-9226`, collect only a bounded snapshot/filtered request list, then `detach`. Never use Playwright `open`, `close`, `close-all`, `kill-all`, `delete-data`, profile, persistent, extension, submit, delete, or file upload.
- [ ] Close the exact task tab. Record the replacement contract and all sanitized evidence. Do not implement selectors until this step is complete.

**Task 2 acceptance:** Every replacement interface decision has live evidence; no file was attached to any historical track; no external record changed.

## Task 3: Add standalone replacement capability and deterministic tests

**Purpose:** Implement the confirmed replacement contract in the existing module with no new abstraction layer.

**Risk level:** reversible repository edits.

- [ ] Use `apply_patch` to add `track_evidence()` and `replace_sound_once()` exactly as specified in Interface Contracts, plus only the minimal private helpers shared by those methods.
- [ ] Use exact Task 2 selectors/endpoints. Re-query row/menu/input immediately before action. Record replacement upload before waiting. Preserve one deadline through upload and verification.
- [ ] Extend `_self_check()` only with pure replacement invariants: allowed audio extensions, sound-manager host, and replacement result-state constants.
- [ ] Add these exact tests:
  - `test_track_evidence_requires_exact_album_track_and_title`
  - `test_track_evidence_rejects_missing_or_ambiguous_records`
  - `test_replace_sound_once_requires_confirm_and_exact_snapshot`
  - `test_replace_sound_once_validates_file_before_page_mutation`
  - `test_replace_sound_once_blocks_identity_or_live_record_mismatch`
  - `test_replace_sound_once_opens_exact_row_and_uploads_once`
  - `test_replace_sound_once_verifies_same_track_with_changed_audio`
  - `test_replace_sound_once_returns_nonretryable_unknown_without_second_upload`
- [ ] Update `publishing.md` public API, exact usage, replacement preconditions, before/after evidence, state/recovery table, and live-test section. State explicitly that replacing historical content requires separate exact authorization.
- [ ] Run:
  ```bash
  codegraph sync "/Users/yelin/Developer/agent-tools/browser-harness"
  uv run python -m py_compile "agent-workspace/domain-skills/ximalaya/publishing.py" "tests/unit/test_ximalaya_publishing.py"
  rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"
  rtk python3 "scripts/verify_domain_skills.py"
  rtk uv run --with pytest pytest -q
  RTK_DISABLED=1 git diff --check
  ```
- [ ] Expected minimum after exactly the listed tests: focused 33 pass and full 373 pass. If more evidence-driven tests are added, counts may be higher but none may be skipped/disabled.

**Task 3 acceptance:** New methods exist and docs/tests agree; all tests green; registry remains 103; no core/dependency/registry/Bilibili change from this task.

## Task 4: Publish one immediate test sound into album `7980411`

**Purpose:** Complete original immediate-publish acceptance and create the only safe replacement target.

**Risk level:** externally visible publication, explicitly authorized.

- [ ] Independently re-run FFprobe once per fixed audio file. Require the exact codec/container/duration/size facts in Fixed Identities and Fixtures.
- [ ] Revalidate cover through `uv run python`/Pillow. If missing, regenerate only under the new Evidence directory from the previously verified source; do not edit repository assets.
- [ ] Recheck no exact new title exists in any scheduled/album list.
- [ ] Under one Agent Pool write lease, open upload URL, page-info/read skills, exact identity, upload the fixed 90-second MP3 once, select album `7980411`, set exact new title, accepted cover, description `Browser Harness 喜马拉雅替换声音能力验收。该节目仅用于立即发布、单次替换、结果验证与安全删除。`, immediate mode, and required defaults.
- [ ] Capture two full snapshots two seconds apart. Require exact account/title/album/cover/description, upload complete, immediate mode, no schedule, submit enabled, no modal/errors.
- [ ] Persist `immediate_submit_armed`, then call `submit_once()` once. Persist `immediate_submit_unknown` and click fact before waiting.
- [ ] If unknown, reconcile read-only only. Success requires one exact new track ID/title/album `7980411`, published/accepted state, `submit_clicks=1`, and no duplicate.
- [ ] Call `track_evidence()` immediately after verification and persist immutable `before` snapshot including duration approximately 90 seconds and every available media identity field. Mark `immediate_verified`.

**Task 4 acceptance:** Exactly one current-run record exists in album `7980411`; stable track ID and before snapshot persisted; no historical count/content change other than the new +1 record.

## Task 5: Replace only the new current-run test sound once

**Purpose:** Prove the independent replacement method without risking historical content.

**Risk level:** destructive overwrite of current-run test audio, explicitly authorized.

- [ ] Recheck account, exact new track ID/title/album, current-run marker, unique live match, and before duration/media identity. Any mismatch stops before opening the menu.
- [ ] Recheck replacement M4A locally. Require AAC/M4A, 268.329796 seconds, 8,636,680 bytes.
- [ ] Persist `replacement_armed` with `replacement_uploads=0` and `replacement_confirms=0`.
- [ ] Call `replace_sound_once(before, replacement_path, 77566037, "水蜜桃英语", confirm=True)` exactly once.
- [ ] Persist `replacement_unknown` and `replacement_uploads=1` as soon as file attachment occurs. A timeout or ambiguous UI is not permission to call again.
- [ ] Reconcile with `track_evidence()` only. Require:
  - same exact track ID;
  - same exact title;
  - same exact album ID `7980411`;
  - record count remains exactly prior historical count plus one;
  - duration changes from approximately 90 seconds to approximately 268.329796 seconds within observed rounding tolerance;
  - at least one independent audio signal changes: media URL/path/resource ID, update timestamp, replacement response identifier, or player-loaded resource;
  - title, album, cover, description, visibility, category, and publish state remain unchanged.
- [ ] If the platform is still processing, poll read-only under the single method deadline. If it expires, return `replacement_unverified`, retain the record for diagnosis, and do not delete until it is clear whether replacement succeeded.
- [ ] Mark `replacement_verified` only when every identity/change invariant passes.

**Task 5 acceptance:** One replacement upload and at most one confirmation occurred; same track identity now proves M4A replacement; no second track or historical mutation.

## Task 6: Delete only the replaced current-run test sound

**Purpose:** Leave the account clean after successful replacement validation.

**Risk level:** destructive deletion, explicitly authorized only for the current-run record.

- [ ] Require state `replacement_verified`. Recheck exact account/album/track/title/run marker and unique live match.
- [ ] Build the existing verified submission dict from Task 4 evidence, retaining `created_by="ximalaya_domain_skill"`, `submit_clicks=1`, exact ID/title/album, and current-run marker.
- [ ] Call `delete_once()` once with UID/name and `confirm=True`. Persist `new_delete_unknown` immediately after activation.
- [ ] If ambiguous, use only exact-ID/title read-only reconciliation. Never repeat delete/confirm.
- [ ] Mark `new_deleted` only when scheduled and album-track APIs contain no exact ID/title; historical count returns to its Task 2 baseline.

**Task 6 acceptance:** New replacement test absent; prior test remains absent; album `7980411` historical records/count restored; no other content changed.

## Task 7: Final regression, documentation, discovery, and cleanup gate

**Purpose:** Complete original Task 8 plus replacement acceptance with fresh proof.

**Risk level:** safe local and read-only external audit.

- [ ] Update `publishing.md` with verified replacement selectors/endpoints, one-shot semantics, before/after evidence fields, live acceptance date/result, and limitations. Do not store secrets or full media URLs when a path/hash/ID proves change.
- [ ] Run every command fresh:
  ```bash
  codegraph sync "/Users/yelin/Developer/agent-tools/browser-harness"
  uv run python -m py_compile "agent-workspace/domain-skills/ximalaya/publishing.py" "tests/unit/test_ximalaya_publishing.py"
  rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"
  rtk python3 "scripts/verify_domain_skills.py"
  rtk uv run --with pytest pytest -q
  RTK_DISABLED=1 git diff --check
  RTK_DISABLED=1 git status --short
  RTK_DISABLED=1 git diff -- "agent-workspace/domain-skills/ximalaya/publishing.py" "agent-workspace/domain-skills/ximalaya/publishing.md" "tests/unit/test_ximalaya_publishing.py" "agent-workspace/domain-skills/registry.json" "docs/plans/2026-09-07-ximalaya-publishing-domain-skill.md" "docs/plans/2026-09-08-ximalaya-publishing-replacement-completion.md"
  rtk rg -n 'T.B.D|T.O.D.O|F.I.X.M.E|Bearer |Authorization:|Cookie:|sessionid|access_token|refresh_token|password' "agent-workspace/domain-skills/ximalaya" "tests/unit/test_ximalaya_publishing.py"
  ```
- [ ] Under one read lease, navigate with `new_tab()` to `https://studio.ximalaya.com/opus` and `https://www.ximalaya.com/reform-upload/page/sound/manage/7980411`; call `page_info()` after each and require the exact Ximalaya Domain Skill Markdown path in `domain_skill_files`.
- [ ] Recheck both test IDs/titles absent and album `7980411` historical count/invariants restored.
- [ ] Close exact task-owned tabs; check Agent Pool no leases/write locks; Browser Fleet audit still shows all pre-existing managed browsers running/healthy.
- [ ] Inspect full diff. Allowed plan-executor edits are only the three Ximalaya files; registry/old plan remain their already-present state; the new plan is added by the plan author. Bilibili files must remain untouched from Task 0 hashes.
- [ ] Update this Progress Ledger and both documentation acceptance sections with exact test counts, non-secret IDs/states, mutation counts, cleanup evidence, and residual risks.

**Task 7 acceptance:** Focused/full/registry/syntax/diff checks pass; both test records absent; replacement verified; no lease/tab/junk/secret/debug code; no unapproved file or external mutation.

## Test Matrix

| Layer | Risk/requirement | Exact check | Pass condition |
| --- | --- | --- | --- |
| Baseline | Resume without replay | Read previous evidence + Git + live exact ID | Actual state recorded before mutation |
| Unit | Cross-day deletion | `test_delete_once_uses_live_mode_after_scheduled_record_auto_publishes` | Live mode/album controls route; one deletion |
| Unit | Exact track lookup | Two `track_evidence` tests | ID/album/title unique; missing/ambiguous rejected |
| Unit | Replacement confirmation | `test_replace_sound_once_requires_confirm_and_exact_snapshot` | No mutation without explicit confirmed snapshot |
| Unit | Local validation | `test_replace_sound_once_validates_file_before_page_mutation` | Missing/empty/unsupported rejected before browser action |
| Unit | Identity/scope | `test_replace_sound_once_blocks_identity_or_live_record_mismatch` | Wrong account/track/title/album blocks |
| Unit | Single upload | `test_replace_sound_once_opens_exact_row_and_uploads_once` | Exact row/menu/input; one attachment |
| Unit | Replacement proof | `test_replace_sound_once_verifies_same_track_with_changed_audio` | Same identity, changed audio evidence |
| Unit | Unknown recovery | `test_replace_sound_once_returns_nonretryable_unknown_without_second_upload` | `retry=False`, no second attachment |
| Focused | Complete Ximalaya module | `rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"` | At least 33 passed, none skipped |
| Registry | Domain discovery | `rtk python3 "scripts/verify_domain_skills.py"` | PASS registry=103 |
| Regression | Repository | `rtk uv run --with pytest pytest -q` | At least 373 passed, none failed |
| Old cleanup | Prior record | Exact API/list reconciliation | ID `1012239040` absent |
| Immediate E2E | Create safe target | One `submit_once()` | One exact new track in album `7980411` |
| Replacement E2E | Replace media only | One `replace_sound_once()` | Same track identity; 90s MP3 becomes 268s M4A evidence |
| New cleanup | Remove safe target | One `delete_once()` | New exact ID/title absent; historical count restored |
| Browser safety | Shared browser | Agent Pool status + fleet audit | No task tab/lease/write lock; browser remains running |
| Scope | Preserve work | Raw diff/status | No core/dependency/Bilibili/production/Git-remote mutation |

## Failure Recovery

| Failure | Required action | Forbidden action |
| --- | --- | --- |
| Context loss | Re-read this plan, Skills, both evidence files, Progress Ledger, Git status/diff, Agent Pool, and exact live records | Restart publication/replacement |
| Login/MFA/captcha/consent | Stop for user interaction | Enter or extract credentials, bypass controls |
| Old record absent at start | Record as already cleaned; skip live old deletion | Recreate it |
| Old record identity ambiguous | Stop before delete | Pick newest/first/fuzzy row |
| Scheduled record now ordinary published | Use exact live mode/album after unit-tested root fix | Trust stale submission mode |
| Historical menu inspection uncertain | Use bounded read-only Playwright after fleet gate | Attach file or confirm on history |
| New submit unknown | Read-only exact-title/ID reconciliation | Submit again or alter title |
| Replacement attachment unknown | Read-only `track_evidence` and network/result reconciliation | Attach file again |
| Same track ID but duration unchanged | Wait read-only within deadline; then return unverified | Declare success from toast alone |
| Track ID/title/album changed | Stop, preserve evidence, do not delete automatically | Treat new identity as successful replacement |
| Duplicate new title/track | Stop and report exact IDs | Bulk delete or submit another |
| Replacement verified but delete unknown | Read-only absence polling | Repeat delete/confirm |
| Same test fails twice | Rerun exact test raw, inspect root cause, patch minimally | Continue guessing from summarized output |
| Unexpected dirty file | Preserve it and stop if overlapping | Reset, checkout, clean, stash, or overwrite |

## Final Acceptance Gate

Completion requires all conditions:

1. Previous evidence was resumed without replaying any prior submit attempt.
2. `1012239040` and its exact title are absent after one guarded deletion or were proven absent before Task 1.
3. `delete_once()` correctly follows live mode/album after scheduled-to-published transition.
4. Exact duplicate unit-test definition was removed, not renamed into fake coverage.
5. `track_evidence()` and `replace_sound_once()` match documented signatures and safety contracts.
6. One and only one new current-run immediate record was created in album `7980411`.
7. New record had an exact before snapshot proving approximately 90-second MP3 media.
8. Exactly one replacement file attachment occurred; at most one replacement confirmation occurred.
9. Replacement preserved exact track ID, title, album, cover, description, visibility, category, and publish state.
10. Replacement changed duration to approximately 268.329796 seconds and at least one independent media identity signal.
11. Replacement did not create a second track or alter any historical sound.
12. New current-run record was deleted once and exact ID/title are absent.
13. Album `7980411` historical count and sampled historical IDs/titles equal the Task 2 baseline after cleanup.
14. Focused tests are at least 33 passed; full tests at least 373 passed; registry remains 103; syntax and diff checks pass.
15. Domain discovery returns the Ximalaya Markdown path on both supplied URLs.
16. No credentials, tokens, full sensitive requests, debug dumps, disabled tests, deferred-work markers, or generated repository junk remain.
17. Existing Bilibili modifications remain unchanged; no Browser Harness core/dependency/update, Git commit/push/branch, production promotion, album mutation, or browser lifecycle operation occurred.
18. Task tabs are closed exactly; browser 9226 remains healthy; Agent Pool has no lease/write lock.
19. Every Progress Ledger row and evidence section contains fresh completion proof.

If any condition is false, the work is incomplete. Continue only through a documented safe recovery path or stop at the exact blocker. A toast, HTTP 2xx, green unit suite without live evidence, elapsed runtime, or “mostly complete” is not completion.
