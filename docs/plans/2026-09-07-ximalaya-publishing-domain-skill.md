# Ximalaya Publishing Domain Skill Implementation Plan

> Historical execution record. Current runtime authorization is defined by
> `agent-workspace/domain-skills/ximalaya/publishing.md`: a logged-in managed
> browser is sufficient; UID and display-name comparisons are not authorization
> gates.

> **Executor:** Low-capability autonomous agent operating in the execution environment recorded below. Follow this document literally; do not infer omitted work, widen scope, delegate to sub-agents, or continue past a stated stop condition.

**Outcome:** Discover Ximalaya Studio's real audio-publishing contract and add a reusable Browser Harness Domain Skill that safely uploads audio, fills every required publishing field, supports scheduled and immediate publication, verifies the server-visible result, records verified platform limits, and deletes only the two test records created by this run.

**Done when:** The new Ximalaya Domain Skill is auto-discovered for `ximalaya.com`; its documented public methods and unit tests cover identity, albums, audio, cover, text limits, scheduled/immediate modes, one-click submission, read-only reconciliation, and guarded deletion; one scheduled and one immediate live publication on account `77566037` are each verified and then deleted; all focused tests, all 340 baseline tests plus the new tests, Domain Skill registry verification, syntax checks, diff checks, and safety audits pass; no existing Ximalaya content, album, browser/Profile, Bilibili work, Git branch, commit, remote, or production release is changed.

**Workspace root:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Repository root:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Plan file:** `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-09-07-ximalaya-publishing-domain-skill.md`

**Evidence directory:** `/tmp/browser-harness-ximalaya-publishing-20260907`

**Evidence ledger:** `/tmp/browser-harness-ximalaya-publishing-20260907/evidence.md`

**Target environment:** Local development environment on macOS Darwin, `/bin/zsh`, Asia/Shanghai timezone, authenticated managed Chrome selected deterministically from ports 9225 then 9226.

**Execution mode:** `unattended`. Routine discovery, code edits, local tests, two explicitly authorized live publications, and deletion of exactly those two newly created records must proceed without asking the user to choose implementation details. Stop only for login/MFA/consent, an identity mismatch, an unconfirmed expansion of destructive scope, or another explicit stop condition in this plan.

**Execution environment:** The author verified on 2026-09-07 that the filesystem is unrestricted, network access is enabled, the repository is writable, `/Users/yelin/Documents/english-media-materials` is readable, and both managed browsers are running and healthy. Available tools are Python 3.14.6, `uv 0.11.7`, Browser Harness 0.1.9 from the current checkout, Browser Harness production snapshot v3 at commit `fd5195bcea8896a809c99240898831753e20bd99`, `playwright-cli 0.1.19`, `rtk 0.43.0`, CodeGraph 1.4.1, FFmpeg/FFprobe under `/opt/homebrew/bin`, and Pillow 12.3.0 through `uv run python`. Authentication availability must be rechecked in the selected browser at execution time; credentials, cookies, tokens, passwords, and verification codes must never be read or printed.

**Architecture/approved approach:** Keep Browser Harness core unchanged. Follow the existing Bilibili shape: one site-specific Markdown contract, one directly executable Python helper module, one focused unit-test module, and one registry entry. Browser Harness and its Agent Pool own all final browser interactions; Playwright CLI is an optional, read-only diagnostic aid only when Browser Harness DOM/AX/network evidence is ambiguous. Implement only behavior observed on the live Ximalaya variant; do not add a generic publishing framework or dependency.

**Tech stack:** Python 3.11+ project, currently Python 3.14.6; `cdp-use==1.4.5`, `fetch-use==0.4.0`, `pillow==12.3.0`, `websockets==15.0.1`; pytest supplied by `uv run --with pytest`; Chrome DevTools Protocol through Browser Harness; JSON registry version 1.

## Required Skills and References

- `writing-plans`
  - SKILL.md: `/Users/yelin/.codex/skills/writing-plans/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/writing-plans/references/lessons.md`
  - Use for: literal execution, Progress Ledger maintenance, interruption recovery, safety gates, and final proof.
- `ponytail:ponytail`
  - SKILL.md: `/Users/yelin/.codex/plugins/cache/devkeeper-ponytail-local/ponytail/4.8.4/skills/ponytail/SKILL.md`
  - Lessons: `none found`
  - Use for: understand before writing, reuse existing repository patterns, avoid new dependencies and speculative abstractions, and make the smallest root-cause change.
- `browser-fleet-manager`
  - SKILL.md: `/Users/yelin/.codex/skills/browser-fleet-manager/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/browser-fleet-manager/references/lessons.md`
  - Use for: real-time audit and resolution of managed browser identity, port, Profile, process, and CDP health.
- `playwright-cli`
  - SKILL.md: `/Users/yelin/.agents/skills/playwright-cli/SKILL.md`
  - Lessons: `none found`
  - Use for: optional read-only snapshots or request inspection after the Browser Fleet gate; never use it as the final implementation or to create an unmanaged browser.
- `browser-harness`
  - SKILL.md: `/Users/yelin/Developer/agent-tools/browser-harness/SKILL.md`
  - Lessons: `none found`
  - Use for: Agent Pool leases, task-owned tabs, CDP/DOM/AX interaction, file upload, page discovery, and Domain Skill loading.
- Browser Harness interaction references
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/uploads.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/network-requests.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/tabs.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/dialogs.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/dropdowns.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/scrolling.md`
  - Lessons: `none found`
  - Use for: exact task-tab cleanup, upload inputs, submit evidence, confirmation dialogs, dropdowns, calendars, and virtualized controls.

Read every listed file in full before the first related action. If a file is absent, record the exact missing path in the Evidence Ledger and continue only when the missing file is not required for a safety boundary. `uploads.md` and `network-requests.md` are currently nearly empty; read them anyway and rely on current source plus live evidence rather than inventing undocumented behavior.

## Applicable Rules

- `/Users/yelin/Developer/agent-tools/browser-harness/AGENTS.md`: use the current checkout's `./browser-harness`; edit site-specific agent code only inside `agent-workspace/`; use double-quoted paths; use RTK normally and raw output when security, destructive actions, completeness, or ambiguity matters; preserve unrelated changes; do not commit, push, create branches, or run destructive Git commands.
- `/Users/yelin/Developer/agent-tools/browser-harness/CLAUDE.md`: follow `AGENTS.md`; use the current source wrapper for browser work.
- `/Users/yelin/Developer/agent-tools/browser-harness/SKILL.md`: first navigation is `new_tab(url)`; call `wait_for_load()` and then print/check `page_info()`; if `domain_skill_files` appears, read every returned Markdown file before site-specific actions; enter managed browser work through Agent Pool; use `--mode write --account "77566037"` for upload, publication, and deletion; only close tabs returned by this run's `new_tab()`.
- Browser Fleet rules: never operate the personal Chrome; never use a raw Profile path; never start, stop, migrate, rename, retire, restore, or delete a browser/Profile; do not read cookies or tokens; abort on `conflict`, `unmanaged`, `personal`, `unhealthy`, or stopped results.
- File changes: use `apply_patch`; do not overwrite or revert the existing user modifications in `agent-workspace/domain-skills/bilibili/publishing.py` and `tests/unit/test_bilibili_publishing.py`.
- CodeGraph: use the existing index for narrow structure discovery before broad source reading; do not initialize it. After repository edits, run `codegraph sync .` before using `affected` or further graph conclusions.
- Comments and docs: match the repository's existing English code-comment and Domain Skill documentation language. The plan and Evidence Ledger may remain Chinese/English mixed where clarity benefits.
- No sub-agents: execute serially in one agent. A second agent must not share the account, browser, lease, or external mutation state.

## Scope

### In scope

- Discover the current authenticated Ximalaya Studio audio-upload and content-management flows at `https://studio.ximalaya.com/`.
- Verify account name `水蜜桃英语` and account ID `77566037` before every publication and deletion.
- Select one existing active album deterministically; record its exact name and stable ID; never create, rename, edit, or delete an album.
- Discover and document every visible or request-backed publishing field, its required/optional state, default, accepted value domain, character-count semantics, and validation behavior.
- Discover and document audio extension/container/codec, size, duration, channel/sample-rate, and upload-processing constraints with evidence levels.
- Discover and document custom-cover format, dimensions, aspect ratio, byte-size, crop, and validation constraints with evidence levels.
- Discover the scheduling timezone, minimum lead, maximum horizon, minute granularity, calendar boundary behavior, and readback format.
- Add `ximalaya/publishing.py`, `ximalaya/publishing.md`, focused unit tests, and registry mapping.
- Complete exactly one scheduled and one immediate real publication, with a unique run marker and at most one submit activation per title.
- Verify both records by exact ID/title and observable manager/API evidence.
- Delete exactly those two records after verification and prove they are gone or terminally deleted.

### Out of scope

- Creating or changing albums, paid-content settings, channel settings, account profile, organization details, monetization, advertisements, comments, followers, or historical content.
- Publishing more than two live records, retrying a submit with the same exact title, or keeping test content online after successful deletion verification.
- Browser Harness core changes under `src/browser_harness/`, new dependencies, Page Objects, generalized publisher frameworks, SAU integration, schedulers, Cron jobs, production-version promotion, package release, Git commit, push, PR, branch, worktree, or remote repository mutation.
- Password entry, MFA, captcha solving, consent acceptance, account switching, authentication bypass, automation evasion, fingerprint spoofing, or reading raw Cookie/Storage/token values.
- Treating Playwright CLI scripts, snapshots, or generated locators as the final deliverable.

### Allowed side effects

- Read Ximalaya Studio pages and sanitized request metadata in the selected managed browser.
- Upload local test audio and generated temporary cover candidates without submitting while probing form validation.
- Create exactly two Ximalaya test records on account `77566037`: one scheduled record and one immediate record.
- Delete exactly those two newly created records after their identities and publication results are verified.
- Create code and documentation only at the four planned repository paths and temporary evidence/cover artifacts under `/tmp/browser-harness-ximalaya-publishing-20260907`.

### Confirmed dangerous side effects

The user explicitly confirmed in this conversation on 2026-09-07:

- real scheduled publication of one test audio on account `77566037`;
- real immediate publication of one test audio on account `77566037`;
- deletion of only those two records created by this execution after account ID, record ID, exact title, and run marker all match.

This authorization does not cover any pre-existing record. Do not ask again for the same exact batch. Ask again only if the target account, number of records, record origin, deletion mechanism, blast radius, or recovery conditions change.

## Execution Contract

- Read this plan from the beginning before changing state.
- Initialize or resume the Progress Ledger from actual repository, Evidence Ledger, browser, and Ximalaya manager state; never assume an unchecked step is complete.
- Continue autonomously through all in-scope work and settled routine decisions.
- Use 9225 first. If and only if its live account identity is not `77566037`, close only the probe tab and try 9226. Use the first browser that proves the exact account. If neither proves the account, stop and ask the user to log in; do not enter credentials or use 9223 as an unplanned fallback.
- Hold one Agent Pool write lease for each cohesive mutation phase. Never attach directly with a manually supplied CDP URL outside the pool.
- Every non-idempotent action follows: observe exact precondition, perform one activation, persist the click fact, then use only read-only reconciliation until success or terminal uncertainty.
- A timeout, navigation error, missing response, renderer detachment, or ambiguous toast after submit/delete is not permission to repeat the action.
- Store only sanitized evidence: URL origin/path, request method, status, field names, value lengths, non-secret IDs, account name/ID, album name/ID, content name/ID, timestamps, state, and validation copy. Never store request headers, cookies, tokens, authorization values, personal listener data, or full page dumps.
- Stop only at a genuine blocker or an unconfirmed dangerous-operation boundary. Preserve the exact checkpoint and all known IDs before stopping.
- After interruption, reconstruct external state before any retry. Query manager/API by exact run marker and record ID first.
- Mark the plan complete only after every acceptance check passes with fresh evidence and no required cleanup remains.

## Safety State Machine

Use these states verbatim in the Evidence Ledger and public results:

- `preflight`: no Ximalaya mutation has occurred.
- `form_discovery`: form may contain temporary input/upload state, but no submit activation occurred.
- `scheduled_submit_armed`: scheduled form has two identical stable snapshots and exact account/album/target time.
- `scheduled_submit_unknown`: scheduled submit was activated once but acceptance is not yet proven; only read-only reconciliation is allowed.
- `scheduled_verified`: exact scheduled record ID/title/time are proven.
- `scheduled_delete_unknown`: delete was activated once but disappearance is not yet proven; only read-only reconciliation is allowed.
- `scheduled_deleted`: exact scheduled record is absent or explicitly terminal-deleted.
- `immediate_submit_armed`: immediate form has two identical stable snapshots and exact account/album.
- `immediate_submit_unknown`: immediate submit was activated once but acceptance is not yet proven; only read-only reconciliation is allowed.
- `immediate_verified`: exact immediate record ID/title/state are proven.
- `immediate_delete_unknown`: delete was activated once but disappearance is not yet proven; only read-only reconciliation is allowed.
- `immediate_deleted`: exact immediate record is absent or explicitly terminal-deleted.
- `complete`: both records were verified and deleted; tests and audits pass.

Transitions may advance only in the listed direction. Never move from an `unknown` state back to an `armed` state for the same title.

## Current-State Evidence

- Verified repository root: `/Users/yelin/Developer/agent-tools/browser-harness`.
- Current branch: `main`, tracking `origin/main`.
- Current HEAD: `fd5195bcea8896a809c99240898831753e20bd99`.
- Existing dirty files that belong to the user and must be preserved:
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py`
  - `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_bilibili_publishing.py`
- CodeGraph status: initialized, version 1.4.1, complete index, 62 indexed files, two pending modified files matching the dirty Bilibili paths.
- Baseline focused Bilibili suite: `26 passed in 0.15s`.
- Baseline full suite: `340 passed in 1.14s`.
- Baseline Domain Skill verification: `PASS registry=102 skills; runtime_root=/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills`.
- Browser `SAU-自媒体运营-9225`: port 9225, `health=ok`, `status=running`, no lease, no write lock.
- Browser `SAU-自媒体运营-2号-9226`: port 9226, `health=ok`, `status=running`, no lease, no write lock.
- User-provided account evidence: display name `水蜜桃英语`, Ximalaya ID `77566037`, verified-account badge visible.
- Existing mature reference:
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py`
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_bilibili_publishing.py`
- Existing public Bilibili shape includes identity checks, exact-title duplicate prevention, upload preparation, cover/metadata/schedule setters, stable snapshots, `submit_once`, read-only manager reconciliation, bounded errors, and a module self-check. Reuse the safety pattern, not Bilibili selectors or URLs.
- Verified scheduled-test audio candidate:
  - `/Users/yelin/Documents/english-media-materials/daily-news-podcast-selection/2026-08-28/candidate-03-death-of-the-kiss-dating/notebooklm/regenerate-20260828/audio-new.m4a`
  - AAC, M4A container, 44.1 kHz stereo, 268.329796 seconds, 8,636,680 bytes.
- Verified immediate-test audio candidate:
  - `/Users/yelin/Documents/english-media-materials/daily-news-podcast-selection/2026-07-10/source-profile-upload-smoke-20260710/notebooklm-robotaxi-90s-source-profile-smoke.mp3`
  - MP3 codec/container, 44.1 kHz stereo, 90 seconds, 1,080,979 bytes.
- Verified cover source:
  - `/Users/yelin/Documents/english-media-materials/peach-publish-jobs/2026-08-04/three-platform-test/job-54/current.png`
  - PNG, 1280×720, 793,118 bytes.
- Ximalaya site layout, endpoints, field limits, album inventory, and current login state have intentionally not been explored by the plan author. They are required outputs of Task 2, not assumptions.

## Requirement Traceability

| Requirement | Source | Implemented by | Verified by |
| --- | --- | --- | --- |
| Browser-independent execution on 9225 or 9226 | User decision | Tasks 1 and 4 | Identity probe and live runs on first matching browser |
| Exact account `77566037` / `水蜜桃英语` | User screenshot and confirmation | Tasks 1, 3, 5–7 | Identity unit tests plus pre-submit/pre-delete live evidence |
| Scheduled publication is primary | User decision | Tasks 2, 3, 5 | Exact schedule snapshot and manager/API evidence |
| Immediate publication is supported | User decision | Tasks 2, 3, 7 | Exact immediate record evidence |
| Audio upload and existing album selection | User decision | Tasks 2, 3, 5, 7 | Two formats uploaded; exact album ID/name readback |
| Discover all fields and limits | User decision | Tasks 2 and 3 | Constraints table, boundary evidence, runtime constants, unit tests |
| Custom cover constraints | User decision | Tasks 2, 3, 5, 7 | Generated candidate matrix, accepted final cover, exact dimensions/readback |
| One-click, no blind retry | Approved safety model | Tasks 3, 5, 7 | Unit tests and `submit_clicks == 1` for each live record |
| Delete test records after verification | User-confirmed destructive batch | Tasks 6 and 7 | Exact record disappearance/terminal deletion evidence |
| Browser Harness is final deliverable | User decision | Tasks 3, 4, 8 | Four scoped repository files, registry discovery, no core/Playwright artifact dependency |
| Playwright CLI is auxiliary | User decision | Task 2 | Evidence ledger says `not_needed` or records a bounded read-only use |
| Preserve unrelated work | Repository rule | Tasks 0, 4, 8 | Final diff/status contains existing Bilibili edits unchanged plus planned files only |

## Progress Ledger

| Task | Status | Completion evidence |
| --- | --- | --- |
| Task 0 — Execution preflight and recovery ledger | complete | env: repo main@fd5195b, python3.14.6/uv0.11.7/rtk0.43.0/playwright-cli0.1.19/BH0.1.9 all present; run marker `BHXM-20260907T155347-ba1fdb89` persisted in /tmp/browser-harness-ximalaya-publishing-20260907/evidence.md; baseline: bilibili 26 passed, full 340 passed in 1.11s, registry PASS 102 skills; dirty hashes recorded (951e6f87…, b7080be4…); no Ximalaya mutation |
| Task 1 — Managed-browser and account selection | complete | 9225 login-wall (probe tab closed); 9226 selected: audit health=ok running, pool no lease; identity proved by GET /api/home/userInfo uid=77566037 nickName=水蜜桃英语 verifyStatus=3 + matching AX UI; evidence.md Browser/Account sections |
| Task 2 — Live workflow and constraint discovery | complete | form/limits discovered on www.ximalaya.com/reform-upload/page/webCenter/upload (upload→发布音频), offsets/fields/limits in evidence.md; M4A+MP3 both accepted (上传成功) with only bitrate warnings; album 88294964 (雅思口语播客) selected+readback; cover square_1080 accepted (server 1080×1080); schedule min-lead 2h enforced in UI (hour/minute disabled), seconds fixed 00, format YYYY-MM-DD HH:MM:00; title UTF-16 max 40 → derived-run titles recorded in evidence.md；timelist/timePublish 0 rows; managers /opus + sound/manage/{albumId}; per-track delete popover mapped; playwright bounded use recorded (Step 2.8); no submit/delete activated |
| Task 3 — Domain Skill implementation and unit contract | complete | created agent-workspace/domain-skills/ximalaya/publishing.py (+set_title, discovered required field), publishing.md, tests/unit/test_ximalaya_publishing.py (24 tests, all 22 mandatory names), registry entry ximalaya; py_compile OK; focused 24 passed; registry PASS 103 skills; full 364 passed; git diff --check clean; only 4 planned paths + preserved Bilibili dirty files changed; codegraph synced |
| Task 4 — Local verification before live submit | complete | py_compile OK; focused 24 passed; registry 103; full 364 passed; diff --check clean; live dry run DRYRUN_OK (dryrun.json): identity ok, 7 albums, M4A 上传成功, album readback ok, cover square_1080 crop-confirmed, description synced, mode scheduled, schedule target **2026-09-07 20:22** (persisted, Asia/Shanghai, now+2h10m rounded), readback 2026-09-07 20:22:00, two snapshots 2s apart EQUAL, preflight_ok=true; MP3 local preflight verified; NO submit activated; row deleted after dry run |
| Task 5 — Scheduled publication acceptance | complete | attempts 1-2 coordinate-click produced NO record (proven absent; titles burned, evidence.md); attempt 3 with js-click: POST /reform-upload/upload/create fired, record verified: content_id **1012239040**, title BH喜马定时验收3-BHXM-20260907T155347-ba1fdb89, schedule 2026-09-07 20:37:00+08 exact (epoch 1788784620000), album 88294964, state 专享特权审核中, list totalSize 1, submit_clicks=1; no duplicate exact title (2 burned titles have zero records); module manager_evidence/epoch parse fixed + 24 tests pass |
| Task 6 — Scheduled-record deletion acceptance | pending | — |
| Task 7 — Immediate publication and deletion acceptance | pending | — |
| Task 8 — Final documentation, regression, and audit gate | pending | — |

Update this table with `apply_patch` after each task. Completion evidence must name commands, exit codes, exact non-secret IDs/states, and Evidence Ledger anchors. Do not replace `pending` with `complete` based on memory.

## File Map

| Action | Absolute path | Repository-relative path | Responsibility | Depends on / consumed by |
| --- | --- | --- | --- | --- |
| Create | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.py` | `agent-workspace/domain-skills/ximalaya/publishing.py` | Ximalaya identity, constraints, upload, album, metadata, schedule, submission, reconciliation, and guarded deletion helpers | Loaded by `publishing.md` and unit tests |
| Create | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.md` | `agent-workspace/domain-skills/ximalaya/publishing.md` | Exact live workflow, public API, verified limits, recovery table, and acceptance evidence | Auto-discovered by Browser Harness registry |
| Create | `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_ximalaya_publishing.py` | `tests/unit/test_ximalaya_publishing.py` | Deterministic fake-page tests for every safety-critical branch | Run by pytest |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/registry.json` | `agent-workspace/domain-skills/registry.json` | Map `ximalaya.com` and `*.ximalaya.com` to directory `ximalaya` | Read by `_domain_skill_context`; verified by `scripts/verify_domain_skills.py` |
| Create temporary | `/tmp/browser-harness-ximalaya-publishing-20260907/evidence.md` | outside repository | Append-only sanitized discovery and live-action ledger | Required for resume and final proof |
| Create temporary | `/tmp/browser-harness-ximalaya-publishing-20260907/covers/` | outside repository | Generated cover boundary candidates and accepted covers | Uploaded only during Task 2/5/7 |
| Preserve | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py` | existing dirty file | User-owned unrelated work | Must remain byte-for-byte untouched by this plan |
| Preserve | `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_bilibili_publishing.py` | existing dirty file | User-owned unrelated work | Must remain byte-for-byte untouched by this plan |

## Interface Contracts

The following public interfaces are mandatory. Selectors, URLs, response paths, limits, and additional required-field setters must be derived from Task 2 evidence. Do not rename these interfaces after live testing begins.

- `account_identity() -> dict[str, Any]`
  - Inputs: none; uses current authenticated page/session.
  - Output: at least `{"uid": int, "name": str, "logged_in": bool}` plus non-secret organization/verification status when reliably observable.
  - Errors: `auth_required` when logged out; `identity_unreadable` when neither a sanctioned same-origin request nor exact UI state proves identity.
  - Side effects: read-only.
- `require_identity(expected_uid: int, expected_name: str | None = None) -> dict[str, Any]`
  - Validates integer UID equality and optional exact normalized display name.
  - Mismatch error starts with `blocked publish identity:` and reports expected/observed non-secret identity.
  - Side effects: read-only.
- `publishing_constraints() -> dict[str, Any]`
  - Returns the exact live-verified constraints recorded in `publishing.md`: accepted audio extensions/containers, byte and duration limits, title/description counting and bounds, cover types/dimensions/aspect/bytes, scheduling timezone/lead/horizon/granularity, and verification date.
  - Every critical constraint includes evidence level `enforced`, `accepted`, or `declared_and_correlated`; `unknown` is forbidden at final acceptance.
  - Side effects: read-only and returns a copy, not the mutable module constant.
- `list_albums() -> list[dict[str, Any]]`
  - Returns stable album ID, exact name, current status, and whether audio can be added.
  - Must not create or modify albums.
- `archive_matches(title: str) -> list[dict[str, Any]]`
  - Returns exact normalized-title matches with stable content ID, album ID/name, state, mode, and scheduled/published time when observable.
  - Must use exact equality after documented normalization; substring matches are not evidence.
- `prepare_upload(audio_file: str, title: str, expected_uid: int, expected_name: str | None = None, timeout: int = 900) -> dict[str, Any]`
  - Rejects missing, empty, unsupported, or locally provably out-of-range files before upload.
  - Verifies identity and exact-title absence before upload.
  - Uploads at most once and waits for an explicit upload/processing completion signal under one deadline.
  - Returns identity, canonical path, probed audio metadata, title, and upload completion evidence.
- `select_album(album_id: str, expected_name: str | None = None, timeout: float = 15) -> dict[str, Any]`
  - Selects one exact stable album ID; optional name must match readback.
  - Rejects ambiguous name-only selection and inactive/non-writable albums.
  - Returns exact selected album ID/name after DOM or request-backed readback.
- `set_custom_cover(path: str, timeout: float = 30) -> dict[str, Any]`
  - Validates readable local image, format, dimensions, ratio, and bytes before page mutation where possible.
  - Completes any visible crop/confirm step exactly once and returns filename, width, height, format, bytes, crop state, and accepted readback.
- `set_description(text: str, timeout: float = 15) -> str`
  - Replaces the actual editor value through events recognized by the current frontend and returns exact normalized readback.
  - Enforces the discovered counting semantics and maximum.
- `set_publish_mode(mode: str) -> dict[str, Any]`
  - Accepts only `"immediate"` or `"scheduled"`.
  - Returns exact mode and observable control state; does not submit.
- `set_schedule_datetime(value: str, timeout: float = 20) -> dict[str, Any]`
  - Accepts only `YYYY-MM-DD HH:MM` interpreted in Asia/Shanghai.
  - Enforces discovered lead, horizon, and minute granularity before changing UI.
  - Returns exact date, time, timezone, mode, and readback.
- `submission_snapshot() -> dict[str, Any]`
  - Returns identity, audio readiness/name, title, album ID/name, cover state/metadata, description, every other discovered required field/value, publish mode, schedule, submit control text/enabled state, visible validation errors, and modal state.
  - Side effects: read-only.
- `submission_diagnostics() -> dict[str, Any]`
  - Returns URL, toast/modal/validation text in minimal form, submit state, upload state, and deterministic reason.
  - Reasons are limited to `form_validation_failed`, `confirmation_required`, `platform_rejected`, `auth_required`, `result_delayed`, `click_not_accepted`, and `submission_unverified`.
  - Side effects: read-only.
- `manager_evidence(title: str, content_id: str | None = None, expected_schedule: str | None = None, attempts: int = 3) -> dict[str, Any]`
  - Performs at most three read-only manager/API refreshes per call.
  - Accepts only an exact title and, once known, exact content ID. For scheduled records, verifies exact time or a documented terminal accepted state that temporarily hides it.
  - Returns content ID, exact title, album, state, mode, schedule, latest/match flags, source, and load count.
- `submit_once(title: str, expected_uid: int, expected_name: str | None = None, expected_mode: str = "scheduled", expected_schedule: str | None = None, run_marker: str = "", timeout: int = 600) -> dict[str, Any]`
  - Requires nonempty unique run marker, exact identity, exact-title absence, upload complete, all required fields valid, two identical snapshots two seconds apart, expected mode/schedule readback, enabled submit control, and no modal/errors.
  - Activates the final submit control once. It records the click fact before waiting.
  - Never clicks submit again. It reconciles through manager/API evidence until verified or timeout.
  - Verified output contains `status="verified"`, `submitted=True`, `submit_clicks=1`, `content_id`, `title`, `run_marker`, `mode`, schedule, account, album, and `created_by="ximalaya_domain_skill"`.
  - Unknown output contains `status="submission_unverified"`, `submitted=True`, `submit_clicks=1`, diagnostics, and no retry signal.
- `delete_once(submission: dict[str, Any], expected_uid: int, expected_name: str | None = None, confirm: bool = False, timeout: int = 180) -> dict[str, Any]`
  - Requires `confirm is True`, exact identity, `submission.status == "verified"`, `submit_clicks == 1`, `created_by == "ximalaya_domain_skill"`, nonempty current-run marker, exact content ID/title, and a matching live manager record.
  - Refuses arbitrary IDs, historical entries, ambiguous matches, account mismatch, title mismatch, or records absent from the Evidence Ledger.
  - Activates one exact record's delete/cancel control and one required confirmation at most once each; records the delete fact before waiting.
  - Never repeats deletion after an unknown result. Read-only reconciliation proves absence or terminal deletion.
  - Returns `status="deleted"`, exact content ID/title/run marker, `delete_clicks=1`, and verification source; otherwise returns `status="deletion_unverified"` with diagnostics and no retry signal.

If Task 2 proves another field is required to submit, first append that field's literal public setter name, exact signature, inputs, output, errors, and side effects to this Interface Contracts section with `apply_patch`; then implement that recorded contract, document it in `publishing.md`, include it in `submission_snapshot()`, and add at least one focused unit test. Do not add setters for optional fields that are neither requested nor needed for the two acceptance publications.

## Task 0: Establish a recoverable, non-destructive execution baseline

**Purpose:** Ensure the weak executor starts from real state, preserves unrelated work, and can resume without replaying external actions.

**Prerequisites:** None.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** safe.

**Required Skills:** Read every path in “Required Skills and References,” plus `/Users/yelin/Developer/agent-tools/browser-harness/AGENTS.md` and `/Users/yelin/Developer/agent-tools/browser-harness/CLAUDE.md`, before continuing.

**Files:** Create only the temporary Evidence directory/ledger and update this plan's Progress Ledger. Preserve every existing file.

- [ ] **Step 0.1: Re-read environment and repository state**
  - Run from: `/Users/yelin/Developer/agent-tools/browser-harness`
  - Commands:
    ```bash
    pwd
    uname -s
    printf '%s\n' "$SHELL"
    python3 --version
    uv --version
    rtk --version
    playwright-cli --version
    ./browser-harness --version
    git branch --show-current
    git rev-parse HEAD
    RTK_DISABLED=1 git status --porcelain=v1 --branch
    codegraph status "/Users/yelin/Developer/agent-tools/browser-harness" --json
    ```
  - Expected: repository root and `main`; tools execute; the two known Bilibili modifications may remain.
  - Stop if: repository root differs, branch is detached/not `main`, required commands are missing, or new dirty paths overlap the four planned implementation files.
  - Do not fix by switching branches, resetting, cleaning, stashing, or creating a worktree.

- [ ] **Step 0.2: Create or resume the Evidence Ledger**
  - Command: `mkdir -p "/tmp/browser-harness-ximalaya-publishing-20260907/covers"`
  - If `evidence.md` exists, read it fully and reconcile every external action with the manager before continuing.
  - If absent, create it with `apply_patch` containing headings for environment, browser selection, account, run marker, field matrix, constraints, request map, album, scheduled record, immediate record, deletion, tests, and residual risks.
  - Generate the run marker once with:
    ```bash
    python3 -c 'from datetime import datetime; from uuid import uuid4; from zoneinfo import ZoneInfo; print("BHXM-" + datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8])'
    ```
  - Persist that exact marker before any upload. Never regenerate it on resume.
  - Define titles as exact deterministic strings:
    - scheduled: `BH喜马拉雅定时发布验收-` followed by the persisted run marker;
    - immediate: `BH喜马拉雅立即发布验收-` followed by the persisted run marker.

- [ ] **Step 0.3: Re-run baseline checks**
  - Commands:
    ```bash
    rtk uv run --with pytest pytest -q "tests/unit/test_bilibili_publishing.py"
    rtk uv run --with pytest pytest -q
    rtk python3 "scripts/verify_domain_skills.py"
    ```
  - Expected: 26 focused Bilibili tests pass, 340 total tests pass, registry verifier reports 102 skills.
  - If count differs but all tests pass, record the new count and continue. If any test fails, rerun the failing command once with `rtk proxy` for complete output. Do not edit unrelated code; stop if failure predates this plan and blocks a trustworthy baseline.

- [ ] **Task 0 acceptance**
  - Pass criteria: exact environment, run marker, current HEAD/status, baseline results, and known dirty-file hashes are recorded; no Ximalaya mutation has occurred.
  - Update Progress Ledger using `apply_patch`.

## Task 1: Select a healthy managed browser and prove the exact account

**Purpose:** Avoid binding the Domain Skill to a browser name while ensuring live mutations target only account `77566037`.

**Prerequisites:** Task 0 complete.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** safe, read-only external access.

- [ ] **Step 1.1: Audit and resolve both allowed browsers**
  - Commands:
    ```bash
    RTK_DISABLED=1 python3 "/Users/yelin/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py" audit
    RTK_DISABLED=1 python3 "/Users/yelin/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py" resolve --name "SAU-自媒体运营-9225"
    RTK_DISABLED=1 python3 "/Users/yelin/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py" resolve --name "SAU-自媒体运营-2号-9226"
    ./browser-harness agent-pool status --browser "SAU-自媒体运营-9225"
    ./browser-harness agent-pool status --browser "SAU-自媒体运营-2号-9226"
    ```
  - Expected: both are managed, running, `health=ok`, with no conflict. Waiting on an existing lease is allowed; bypassing it is forbidden.

- [ ] **Step 1.2: Probe 9225 first, then 9226 only if necessary**
  - For each candidate, use an Agent Pool read lease with `--site "studio.ximalaya.com" --account "77566037" --mode read`.
  - The Browser Harness stdin script must:
    1. call `new_tab("https://studio.ximalaya.com/")` and save its target ID;
    2. call `protect_tab(target, owner="ximalaya-domain-skill", purpose="identity-probe")`;
    3. call `wait_for_load()`;
    4. print `page_info()` immediately;
    5. inspect only minimal DOM/AX identity evidence;
    6. print a redacted dict containing URL, login-wall boolean, observed display name, and observed numeric ID;
    7. call `unprotect_tab(target)` and `close_tab(target)` in `finally`.
  - If `page_info()` returns `domain_skill_files`, stop site-specific inspection and read every returned Markdown path first.
  - Select the first candidate proving `name == "水蜜桃英语"` and `uid == 77566037`. Record its exact managed name and port.
  - If a login wall, MFA, captcha, consent, or account chooser appears, stop and ask the user to complete it manually in that managed browser. Do not click through or read credentials.
  - If both browsers show a different logged-in account, stop with both observed non-secret identities; do not use 9223.

- [ ] **Task 1 acceptance**
  - Pass criteria: one selected browser is healthy, exact account identity is proved by at least one same-origin/API or exact profile-page source plus matching visible UI, and all probe tabs are closed by exact target ID.

## Task 2: Discover the live workflow, fields, limits, states, and recovery evidence

**Purpose:** Replace assumptions with a complete evidence-backed contract before writing selectors or constants.

**Prerequisites:** Task 1 complete; selected browser/account persisted.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** reversible external form state; no final submit or delete allowed.

### Required discovery matrix

Record one row per field/control with: page URL; label; semantic role; stable selector candidates; input type; required/default state; accepted value domain; DOM attributes; visible validation; request field name; response field/state; readback source; retry safety; and evidence level. Cover at least:

- account identity;
- upload input and upload-processing state;
- title;
- album selector and album stable ID;
- description/introduction;
- cover upload/crop;
- original/reposted/content declaration when present;
- categories, tags, episode number, free/paid state, or other required controls when present;
- immediate/scheduled mode;
- date/time/timezone;
- save draft, preview, submit, confirmation dialog;
- manager/list/detail states;
- delete/cancel-schedule control and confirmation dialog.

- [ ] **Step 2.1: Map navigation and page states with Browser Harness**
  - Enter one Agent Pool write lease for the selected browser, site `studio.ximalaya.com`, account `77566037`.
  - Open exactly one task tab; protect it; call `page_info()` after every navigation; read all newly returned Domain Skill Markdown files before further site actions.
  - Prefer AX semantic roles/names; use targeted DOM reads only when AX is insufficient; use screenshots only when layout/crop geometry matters.
  - Enumerate the creator home, audio-create/upload form, content manager/list, item detail, and deletion confirmation path without activating final submit/delete.
  - Re-query elements after every navigation, modal, dropdown, calendar change, or upload state change. Never reuse stale node IDs or coordinates.

- [ ] **Step 2.2: Correlate network and business actions without secrets**
  - Enable CDP Network observation before each meaningful action.
  - Record only method, origin/path, status, request field names, value types/lengths, non-secret stable IDs, and response state/error codes.
  - Never print headers, cookies, query tokens, authorization values, complete request bodies, or complete page HTML.
  - Establish request/response correlation for identity, album list, upload initialization/chunks/completion, form validation, submit, manager list/detail, and delete.
  - A 2xx response alone is not publication/deletion success; pair it with manager/API final state.

- [ ] **Step 2.3: Discover text limits and counting semantics without submitting**
  - For title and every text editor, inspect `maxlength`, counters, validation copy, and request-side schema/config.
  - Test empty value, one ASCII character, one Chinese character, one emoji, exact declared maximum, and maximum plus one. Restore a valid value afterward.
  - Record whether counting uses Unicode code points, UTF-16 code units, UTF-8 bytes, or platform-specific normalized length. Use observed counters and accepted/rejected readback, not Python `len()` alone.
  - Never activate final submit during boundary probing.

- [ ] **Step 2.4: Discover audio constraints without creating extra records**
  - Re-verify both candidate files independently with the exact `ffprobe` commands below. One `ffprobe` invocation accepts one input only.
    ```bash
    RTK_DISABLED=1 /opt/homebrew/bin/ffprobe -v error -show_entries format=filename,format_name,duration,size -show_entries stream=codec_name,codec_type,sample_rate,channels -of json "/Users/yelin/Documents/english-media-materials/daily-news-podcast-selection/2026-08-28/candidate-03-death-of-the-kiss-dating/notebooklm/regenerate-20260828/audio-new.m4a"
    RTK_DISABLED=1 /opt/homebrew/bin/ffprobe -v error -show_entries format=filename,format_name,duration,size -show_entries stream=codec_name,codec_type,sample_rate,channels -of json "/Users/yelin/Documents/english-media-materials/daily-news-podcast-selection/2026-07-10/source-profile-upload-smoke-20260710/notebooklm-robotaxi-90s-source-profile-smoke.mp3"
    ```
  - Inspect file input `accept`, visible help, frontend validation/config, and upload API errors.
  - Prove M4A and true MP3 acceptance using the two real files, reusing them later for the two submissions. Do not upload a third valid production-sized audio unless one candidate is rejected.
  - For unsupported/empty input behavior, use only small temporary fixtures under the Evidence directory and stop before server-side submission.
  - For maximum byte/duration limits, require two independent sources: visible official validation/help plus correlated client/request schema or a bounded rejection response. Do not generate or upload multi-gigabyte files merely to prove a displayed maximum. Mark the evidence `declared_and_correlated`; final docs must distinguish it from `accepted` and `enforced`.

- [ ] **Step 2.5: Discover cover constraints with generated local candidates**
  - Use Pillow through `uv run python`; do not rely on global `python3`, where Pillow is absent.
  - Generate from the verified 1280×720 PNG: square 800×800, 1000×1000, 1080×1080, 1280×1280; landscape 1280×720; portrait 1080×1920; PNG and JPEG variants. Store only under `/tmp/browser-harness-ximalaya-publishing-20260907/covers/`.
  - Inspect visible guidance, input `accept`, cropper viewport, request metadata, and validation errors.
  - Identify one final accepted format/dimension/ratio without submitting. Record whether the platform crops, rejects, or accepts each candidate.
  - If a byte maximum is declared, validate an over-limit candidate only when it can be generated below 25 MB. Otherwise use `declared_and_correlated` evidence and do not allocate a huge artifact.

- [ ] **Step 2.6: Discover scheduling constraints**
  - Determine exact timezone, minimum lead time, maximum horizon, minute granularity, disabled dates/times, month transition, midnight behavior, and displayed/readback format.
  - Test invalid past, too-soon, invalid minute, exact earliest accepted slot, and first slot beyond the maximum horizon without submitting.
  - Return the form to immediate mode or a valid future slot after every negative test.
  - Compute the later live scheduled target from the discovered rules: begin with current Asia/Shanghai time plus the larger of two hours or minimum lead plus ten minutes; round upward to the next accepted minute increment; if that exceeds the maximum horizon, choose the last accepted slot minus one increment. Persist the exact value before Task 5.

- [ ] **Step 2.7: Select one existing album deterministically**
  - Enumerate exact stable IDs and names of albums that are active and accept a new audio item.
  - Choose the first album in the platform's displayed ordering that is active, writable, and already contains at least one audio item. Record exact ID/name and ordering evidence.
  - Do not choose by fuzzy title; do not create or modify an album.

- [ ] **Step 2.8: Use Playwright CLI only if a precise ambiguity remains**
  - Trigger: Browser Harness AX, targeted DOM, and sanitized network evidence cannot distinguish a required control, accessibility name, or request correlation.
  - Before any Playwright browser command, rerun Browser Fleet `audit` and `resolve` for the selected browser.
  - Attach only to the exact resolved CDP endpoint, use a session named `ximalaya-discovery-9225` or `ximalaya-discovery-9226`, capture only a bounded snapshot or filtered request list, then run `detach`. Do not run `open`, `close`, `close-all`, `kill-all`, `delete-data`, `--persistent`, `--profile`, or `--extension`.
  - Playwright must not click submit/delete or become a runtime dependency. Record either the exact ambiguity it resolved or `not_needed`.

- [ ] **Task 2 acceptance**
  - Pass criteria: all required discovery-matrix rows and critical constraints are populated with observed evidence; no final submit/delete occurred; two audio formats were accepted by upload processing; one existing album and one valid cover are selected; the scheduled target is persisted; optional Playwright use is accounted for.
  - Stop if: a critical limit remains unsupported by two evidence sources, the account changes, paid/monetized settings are mandatory, or the flow requires modifying an album/account setting. Report the exact blocker instead of inventing a default.

## Task 3: Implement the minimal Ximalaya Domain Skill and deterministic unit contract

**Purpose:** Convert verified live facts into reusable Browser Harness code without coupling to one browser or adding a framework.

**Prerequisites:** Task 2 complete; discovery matrix and exact URLs/selectors/limits available.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** reversible repository mutation.

**Files:** Create the three Ximalaya files and modify only the registry. Preserve all other files, especially the dirty Bilibili paths.

- [ ] **Step 3.1: Re-read the mature reference and inspect impact**
  - Commands:
    ```bash
    codegraph status "/Users/yelin/Developer/agent-tools/browser-harness" --json
    codegraph query "publishing submit_once manager_evidence" --path "/Users/yelin/Developer/agent-tools/browser-harness" --json --limit 20
    RTK_DISABLED=1 rg -n '^def ' "agent-workspace/domain-skills/bilibili/publishing.py"
    RTK_DISABLED=1 rg -n '^def test_' "tests/unit/test_bilibili_publishing.py"
    ```
  - Read `publishing.py`, `publishing.md`, and the focused test loader relevant sections. Do not copy Bilibili selectors, URLs, field limits, MID terminology, or manager states.

- [ ] **Step 3.2: Add the registry entry**
  - Use `apply_patch` to add exactly:
    ```json
    "ximalaya": [
      "ximalaya.com",
      "*.ximalaya.com"
    ]
    ```
  - Preserve valid JSON, version 1, and existing entries.

- [ ] **Step 3.3: Create `publishing.py`**
  - Use `apply_patch`.
  - Match the Bilibili module's direct `exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.py").read())` loading pattern and `TYPE_CHECKING` declarations for Browser Harness injected helpers.
  - Use only standard library plus already-installed Pillow.
  - Implement every mandatory Interface Contract with exact Task 2 constants and selectors.
  - Keep private helpers local and minimal: visible-element resolution, normalized text, bounded wait, and one exact click helper only when reused.
  - Re-resolve visible elements immediately before coordinate clicks.
  - Put identity, duplicate prevention, local file validation, stable snapshots, one-click facts, exact record identity, and delete guards in shared functions so every caller receives the same protection.
  - Add `_self_check()` for pure constants, URL host, constraint consistency, allowed modes, and schedule timezone.

- [ ] **Step 3.4: Create focused unit tests**
  - Use `apply_patch` to create a fake page/runtime loader like the current Bilibili test; execute the Domain Skill module in a namespace of fake injected helpers.
  - Mandatory tests, using these exact names:
    - `test_account_identity_rejects_logged_out_session`
    - `test_require_identity_matches_uid_and_exact_name`
    - `test_require_identity_blocks_uid_or_name_mismatch`
    - `test_constraints_have_no_unknown_critical_values`
    - `test_prepare_upload_rejects_missing_empty_and_unsupported_files`
    - `test_prepare_upload_blocks_exact_title_duplicate_before_upload`
    - `test_prepare_upload_waits_for_explicit_processing_completion`
    - `test_select_album_requires_exact_stable_id_and_readback`
    - `test_custom_cover_validates_file_and_returns_exact_metadata`
    - `test_text_limits_follow_discovered_counting_semantics`
    - `test_publish_mode_accepts_only_immediate_or_scheduled`
    - `test_schedule_datetime_enforces_timezone_lead_horizon_and_granularity`
    - `test_submission_snapshot_contains_every_required_field`
    - `test_submit_once_requires_two_stable_valid_snapshots`
    - `test_submit_once_clicks_exactly_once_then_reconciles_read_only`
    - `test_submit_once_returns_nonretryable_unknown_after_ambiguous_click`
    - `test_manager_evidence_requires_exact_title_and_content_id`
    - `test_delete_once_requires_confirm_and_verified_submission`
    - `test_delete_once_rejects_nonledger_or_identity_mismatch`
    - `test_delete_once_clicks_exact_record_once_then_reconciles_read_only`
    - `test_delete_once_returns_nonretryable_unknown_after_ambiguous_click`
    - `test_module_self_check_runs_on_import`
  - Additional discovered required fields each receive one exact readback/error test.

- [ ] **Step 3.5: Create `publishing.md`**
  - Use `apply_patch`.
  - Include absolute load path, prerequisites, exact Agent Pool invocation, required page-info discovery order, public API, verified limits table with evidence levels and date, scheduled and immediate examples, submit/delete recovery tables, exact known-good states, field checklist, browser/tab cleanup rules, and live acceptance results section.
  - State that account ID is authoritative and browser name is not.
  - State that unknown submission/deletion results are read-only recovery states, never retry invitations.
  - Do not include cookies, tokens, raw headers, complete request bodies, fragile full-page dumps, or Playwright artifacts.

- [ ] **Step 3.6: Sync graph after edits and inspect affected tests**
  - Commands:
    ```bash
    codegraph sync "/Users/yelin/Developer/agent-tools/browser-harness"
    codegraph affected --path "/Users/yelin/Developer/agent-tools/browser-harness" --json "agent-workspace/domain-skills/ximalaya/publishing.py" "agent-workspace/domain-skills/registry.json"
    ```
  - Treat direct source/tests as authoritative if new files are not yet fully represented.

- [ ] **Task 3 acceptance**
  - Pass criteria: only four planned repository paths changed/created by this task; every mandatory interface exists; every mandatory test name exists; comments/docs match repository language; no dependency or core change.

## Task 4: Prove local correctness before any live submit

**Purpose:** Prevent avoidable live side effects caused by syntax, contract, or state-machine defects.

**Prerequisites:** Task 3 complete.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** safe local verification.

- [ ] **Step 4.1: Run syntax and focused tests**
  - Commands:
    ```bash
    uv run python -m py_compile "agent-workspace/domain-skills/ximalaya/publishing.py" "tests/unit/test_ximalaya_publishing.py"
    rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"
    rtk python3 "scripts/verify_domain_skills.py"
    ```
  - Expected: syntax success, all mandatory tests pass, registry count increases from 102 to 103 and resolves to the canonical workspace.
  - After one failure, inspect exact failing assertion/source and make the smallest evidence-backed correction. If the same failure remains after two attempts, rerun raw with `rtk proxy` before another edit.

- [ ] **Step 4.2: Run full regression and diff hygiene**
  - Commands:
    ```bash
    rtk uv run --with pytest pytest -q
    RTK_DISABLED=1 git diff --check
    RTK_DISABLED=1 git status --short
    ```
  - Expected: all baseline plus new tests pass; no whitespace error; status contains the two preserved Bilibili modifications, this plan, and only the four planned Ximalaya/registry paths.

- [ ] **Step 4.3: Perform a live pre-submit dry run**
  - Load the new Domain Skill through its absolute path under one write lease.
  - Verify identity, constraints, albums, both audio preflight paths, cover, metadata, schedule, and snapshots.
  - Do not call `submit_once` yet.
  - Compare two snapshots two seconds apart; every requested field must match and no validation/modal error may remain.

- [ ] **Task 4 acceptance**
  - Pass criteria: local suite is green and both live forms can reach stable submit-ready states without any submit activation.

## Task 5: Complete one scheduled publication with one submit activation

**Purpose:** Prove the primary scheduled workflow end to end.

**Prerequisites:** Task 4 complete; state is `form_discovery`; no existing exact scheduled title match.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** externally visible write, explicitly authorized.

**Fixed inputs:** scheduled title derived in Task 0; M4A path recorded in Current-State Evidence; selected album ID/name from Task 2; accepted cover from Task 2; description `Browser Harness 喜马拉雅定时发布能力验收。该内容仅用于验证上传、参数回读、定时发布、结果确认与安全删除。`; exact persisted scheduled target from Task 2; account ID `77566037`; account name `水蜜桃英语`.

- [ ] **Step 5.1: Reconcile before preparing**
  - Call `require_identity`, then `archive_matches` with the exact scheduled title.
  - If zero matches, continue. If one match with the current run marker exists, treat it as a resumed partial run and reconcile instead of uploading. If any pre-existing/ambiguous match exists, stop; never alter the title and blindly continue.

- [ ] **Step 5.2: Prepare and arm the scheduled submission**
  - Call `prepare_upload`, `select_album`, `set_custom_cover`, `set_description`, any Task 2-proven required setters, `set_publish_mode("scheduled")`, and `set_schedule_datetime`.
  - Capture two `submission_snapshot()` values two seconds apart.
  - Require exact identity, filename, title, album ID/name, cover metadata, description, required fields, scheduled mode/time/timezone, enabled submit, no validation errors, and no blocking modal.
  - Persist state `scheduled_submit_armed` and both snapshots before submit.

- [ ] **Step 5.3: Submit once and reconcile**
  - Call `submit_once` exactly once.
  - Persist state `scheduled_submit_unknown` and `submit_clicks=1` immediately after activation.
  - If the call times out or returns unknown, do not call it again. Use only `manager_evidence` and exact-title/content-ID readback under bounded retries.
  - Success requires one exact record, nonempty stable content ID, exact title/run marker, exact album, scheduled mode, exact target time or a documented accepted/review state that temporarily hides it, and `submit_clicks=1`.
  - Persist the full sanitized submission dict and state `scheduled_verified`.

- [ ] **Task 5 acceptance**
  - Pass criteria: scheduled record is verified by exact ID/title/account/album and schedule evidence; no duplicate exact title exists; one submit activation total.

## Task 6: Delete only the verified scheduled test record

**Purpose:** Test cleanup of a scheduled record before it becomes public.

**Prerequisites:** Task 5 state is `scheduled_verified`; exact submission dict is in the Evidence Ledger.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** destructive external operation, pre-authorized only for this exact current-run record.

- [ ] **Step 6.1: Enforce four-way destructive scope check**
  - Verify live account ID `77566037` and exact name.
  - Verify live manager record content ID equals the persisted scheduled content ID.
  - Verify exact title contains the persisted run marker and equals the persisted scheduled title.
  - Verify submission dict says `status="verified"`, `created_by="ximalaya_domain_skill"`, and `submit_clicks=1`.
  - Any mismatch is `destructive_scope_violation`; stop without opening the delete menu.

- [ ] **Step 6.2: Delete once and reconcile**
  - Call `delete_once(submission, 77566037, "水蜜桃英语", confirm=True)` exactly once.
  - Persist state `scheduled_delete_unknown` immediately after activation.
  - If unknown, never call delete again. Refresh/query only by exact content ID/title until absence or terminal deletion is proven under the existing deadline.
  - Persist state `scheduled_deleted`, `delete_clicks=1`, and verification source only after proof.

- [ ] **Task 6 acceptance**
  - Pass criteria: scheduled content ID is absent or terminally deleted, exact-title match count is zero, no other manager record changed, and one delete activation total.

## Task 7: Complete one immediate publication and delete only that record

**Purpose:** Prove the secondary immediate workflow and cleanup without reusing scheduled state.

**Prerequisites:** Task 6 complete; no exact immediate title match.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** externally visible write followed by destructive cleanup, both explicitly authorized for this exact current-run record.

**Fixed inputs:** immediate title derived in Task 0; true MP3 path recorded in Current-State Evidence; same selected album; accepted cover; description `Browser Harness 喜马拉雅立即发布能力验收。该内容仅用于验证上传、参数回读、立即发布、结果确认与安全删除。`; account ID/name as above.

- [ ] **Step 7.1: Prepare a fresh immediate form**
  - Open a fresh task-owned upload tab or reset through a proven new-upload navigation. Never reuse a submitted form.
  - Call identity/duplicate guards, upload MP3, select exact album, set cover/description/required fields, and call `set_publish_mode("immediate")`.
  - Two stable snapshots must prove immediate mode and absence of schedule values.
  - Persist `immediate_submit_armed`.

- [ ] **Step 7.2: Submit once and reconcile**
  - Call `submit_once` exactly once with expected mode `immediate` and no schedule.
  - Persist `immediate_submit_unknown` and click fact before waiting.
  - Success requires one exact record ID/title/run marker/account/album, an immediate published/accepted state, and one submit activation.
  - Persist `immediate_verified`.

- [ ] **Step 7.3: Delete the exact immediate record once**
  - Repeat the four-way destructive scope check from Task 6 using the immediate submission dict.
  - Call `delete_once(immediate_submission, 77566037, "水蜜桃英语", confirm=True)` once; persist `immediate_delete_unknown` immediately after activation.
  - Use only read-only reconciliation afterward. Persist `immediate_deleted` only after exact absence/terminal deletion.

- [ ] **Task 7 acceptance**
  - Pass criteria: immediate record was verified then deleted; no exact-title match remains; one submit and one delete activation total; scheduled record remains deleted; no historical record changed.

## Task 8: Final documentation, regression, cleanup proof, and completion gate

**Purpose:** Make the Domain Skill reusable by a future agent and prove the repository/external account are clean.

**Prerequisites:** Tasks 0–7 complete.

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** safe local verification and read-only external audit.

- [ ] **Step 8.1: Update live evidence in `publishing.md`**
  - Record verification date, account ID/name, selected album ID/name, exact constraints/evidence levels, scheduled/immediate result-state semantics, deletion semantics, and known limitations.
  - Do not include temporary titles' full public URLs if they expose private account data; stable non-secret content IDs are allowed in the temporary Evidence Ledger and may be summarized in docs only when necessary.
  - Ensure every code method and result field matches the document exactly.

- [ ] **Step 8.2: Run the complete Test Matrix fresh**
  - Execute every command listed below, even if it passed earlier.
  - If any test fails, do not mark completion. Diagnose with raw output after the second repeated failure and fix only Ximalaya-scoped causes.

- [ ] **Step 8.3: Audit external cleanup and browser state**
  - Under one read lease, prove both exact titles and content IDs are absent/terminal-deleted.
  - Confirm the selected album still exists unchanged.
  - Close only task-owned tabs after `unprotect_tab`; never close by URL scan.
  - Run Agent Pool status for the selected browser and require no lease/write lock after the command exits.
  - Rerun Browser Fleet audit and require all pre-existing managed browsers still healthy; never stop them.

- [ ] **Step 8.4: Audit diff, scope, placeholders, secrets, and junk**
  - Commands:
    ```bash
    RTK_DISABLED=1 git diff --check
    RTK_DISABLED=1 git status --short
    RTK_DISABLED=1 git diff -- "agent-workspace/domain-skills/ximalaya/publishing.py" "agent-workspace/domain-skills/ximalaya/publishing.md" "agent-workspace/domain-skills/registry.json" "tests/unit/test_ximalaya_publishing.py" "docs/plans/2026-09-07-ximalaya-publishing-domain-skill.md"
    rtk rg -n 'T.B.D|T.O.D.O|F.I.X.M.E|Bearer |Authorization:|Cookie:|sessionid|access_token|refresh_token|password' "agent-workspace/domain-skills/ximalaya" "tests/unit/test_ximalaya_publishing.py"
    ```
  - Expected: no whitespace errors, no unresolved implementation placeholders, no secret-bearing strings, and no changes outside the planned paths plus the two preserved pre-existing Bilibili modifications.
  - No deferred-work marker or unresolved implementation placeholder may appear in implementation artifacts.

- [ ] **Step 8.5: Complete the Progress Ledger**
  - Map every Requirement Traceability row to fresh evidence.
  - Record final test counts, registry count, account cleanup state, selected browser lease state, changed files, preserved dirty files, and residual non-blocking risks.
  - Mark `complete` only when no required external record or browser lease remains.

- [ ] **Task 8 acceptance**
  - Pass criteria: every final acceptance item and Test Matrix row passes; state is `complete`; no dangerous operation remains pending; no commit, push, branch, production promotion, or browser lifecycle mutation occurred.

## Test Matrix

| Layer | Requirement/risk | Preconditions/fixtures | Exact command or procedure | Expected result | Failure evidence |
| --- | --- | --- | --- | --- | --- |
| Baseline | Preserve current repository behavior | Current checkout before Ximalaya edits | `rtk uv run --with pytest pytest -q` | 340 tests pass at author baseline; execution-time all-pass count recorded | Raw pytest output after repeat failure |
| Syntax | New Python files import/compile | Task 3 files exist | `uv run python -m py_compile "agent-workspace/domain-skills/ximalaya/publishing.py" "tests/unit/test_ximalaya_publishing.py"` | Exit 0 | Exact traceback |
| Unit | Identity, limits, upload, album, cover, schedule, snapshot, submit, delete | Fake runtime in focused test file | `rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"` | Every mandatory named test passes | Failing test and assertion |
| Registry | Domain discovery wiring | Registry and Markdown exist | `rtk python3 "scripts/verify_domain_skills.py"` | `PASS registry=103 skills` and canonical runtime root | Verifier error |
| Regression | Neighboring behavior | Focused suite green | `rtk uv run --with pytest pytest -q` | Baseline plus all new tests pass; no skipped/disabled Ximalaya tests | Full raw failure output |
| Static hygiene | Patch validity | All edits made | `RTK_DISABLED=1 git diff --check` | Exit 0, no whitespace errors | Exact file/line |
| Browser identity | Wrong-account safety | Healthy 9225/9226 and login | Probe exact UID/name before each mutation | UID 77566037 and exact name | Redacted observed identity |
| Form discovery | All parameters/limits | Logged-in selected browser | Task 2 matrix and negative boundary checks without submit | Every critical constraint has allowed evidence level, none unknown | Evidence row and validation copy |
| Audio integration | M4A and true MP3 | Two fixed candidate files | Upload/process each once under dry-run/live flow | Explicit processing complete and exact metadata | Upload state, status, sanitized request path |
| Cover integration | Format/dimension/crop | Generated candidate matrix | Upload candidates without submit, then accepted cover in live runs | Exact accepted metadata and crop/readback | Candidate result matrix |
| Scheduled E2E | Primary publish | Stable scheduled snapshot | Task 5, one `submit_once` | Exact verified ID/title/album/time, `submit_clicks=1` | Submission dict and manager/API evidence |
| Scheduled delete | Destructive guard | Verified current-run scheduled dict | Task 6, one `delete_once` | Exact record absent/terminal-deleted, `delete_clicks=1` | Deletion dict and read-only reconciliation |
| Immediate E2E | Immediate publish | Stable immediate snapshot | Task 7, one `submit_once` | Exact verified ID/title/album/state, `submit_clicks=1` | Submission dict and manager/API evidence |
| Immediate delete | Destructive guard | Verified current-run immediate dict | Task 7, one `delete_once` | Exact record absent/terminal-deleted, `delete_clicks=1` | Deletion dict and read-only reconciliation |
| Tab/lease cleanup | Shared-browser safety | Both E2E paths finished | Exact task-tab close, Agent Pool status, Browser Fleet audit | No task-owned tabs/leases/write locks; browsers remain running/healthy | Status/audit JSON |
| Scope | Preserve unrelated work | Final checkout | Raw status and scoped/full diff review | Only planned paths plus unchanged pre-existing Bilibili edits | Unexpected path/diff |

## Failure Recovery Table

| Failure or interruption | Required response | Forbidden response |
| --- | --- | --- |
| Login/MFA/captcha/consent/account chooser | Preserve task tab and checkpoint when safe; stop for user interaction | Enter credentials, bypass, switch account, or scrape secrets |
| 9225 wrong account | Close exact probe tab and try 9226 | Mutate 9225 or use 9223 automatically |
| Both allowed browsers wrong/logged out | Stop with redacted identities/login states | Start/stop browsers or copy Profiles |
| Upload timeout before explicit completion | Inspect upload state and sanitized request/error; retry only if evidence proves no accepted upload and the form supports safe replacement | Assume failure and upload repeatedly |
| Form rerender/stale node | Re-query AX/DOM and current rect under same deadline | Reuse stored backend node/coordinate |
| Submit result unknown | Persist click fact; call only read-only manager/API reconciliation | Call submit again, change title, or re-upload |
| Multiple exact-title records | Hard stop and report IDs/states | Delete all, choose one heuristically, or submit another |
| Scheduled time becomes invalid before submit | Recompute one valid slot using persisted discovered rules before arming; update snapshots/evidence | Fall back to immediate mode |
| Delete result unknown | Persist delete fact; use read-only exact-ID reconciliation | Click delete/confirm again |
| Record identity mismatch before delete | `destructive_scope_violation`; stop | Delete by row position, fuzzy title, or latest-item assumption |
| Network/DOM disagreement | Treat external result as unknown; preserve both evidence sources | Prefer whichever result allows progress |
| Same local test fails twice | Rerun exact test raw, inspect root cause, then patch minimally | Continue blind edits based on RTK summary |
| Unrelated baseline test fails | Record full evidence and stop if it blocks trust; do not edit unrelated subsystem | Mark suite acceptable or disable test |
| Context loss | Re-read plan, skills, lessons, Progress Ledger, Evidence Ledger, Git status/diff, Agent Pool status, and exact manager records; resume first incomplete safe step | Restart live submissions from Task 5 |

## Final Acceptance Gate

The executor may report completion only after all statements below are freshly proven:

1. Account ID `77566037` and exact name were verified before every submit and delete.
2. Exactly two live submit activations occurred: one scheduled title and one immediate title, both containing the one persisted run marker.
3. Each submission produced one exact stable content ID and passed manager/API reconciliation; no duplicate exact title exists.
4. Scheduled mode, timezone, target time, lead/horizon/granularity, and visible readback are documented and tested.
5. Immediate mode has no residual scheduled value and reaches an accepted/published state.
6. Both exact current-run records were deleted once and are absent or terminally deleted; no historical content changed.
7. Every critical title, description, audio, cover, album, and scheduling constraint has a value, counting/unit semantics, evidence level, and verification date; none is labeled unknown.
8. `publishing.py`, `publishing.md`, `test_ximalaya_publishing.py`, and the registry entry agree on interfaces, constants, states, and recovery rules.
9. Syntax, focused unit tests, registry verification, full regression tests, and `git diff --check` all pass.
10. Registry discovery returns the Ximalaya Markdown file after navigation once the entry exists.
11. No secret, raw Cookie/header/token, debug dump, disabled test, implementation placeholder, generated repository junk, or live test content remains.
12. All task-owned tabs are closed exactly; selected browser remains running; Agent Pool leases/write locks are empty.
13. The two pre-existing Bilibili modifications remain untouched.
14. No Browser Harness core file, dependency, Git branch/commit/remote, production snapshot, browser Profile, or existing album was changed.
15. Every Progress Ledger row is complete with evidence and the final state is `complete`.

If any item is false, the work is incomplete. Record the exact checkpoint and continue through safe recovery, or stop at the applicable explicit blocker. “Most steps passed,” runtime limits, an unknown submit/delete result, or a green unit suite without live evidence is not completion.
