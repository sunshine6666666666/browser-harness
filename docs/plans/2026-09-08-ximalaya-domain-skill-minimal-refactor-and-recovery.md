# Ximalaya Domain Skill Minimal Refactor and Recovery Plan

> Historical execution record. Current runtime authorization is defined by
> `agent-workspace/domain-skills/ximalaya/publishing.md`: a logged-in managed
> browser is sufficient; UID and display-name comparisons are not authorization
> gates.

> **Executor:** Low-capability autonomous agent. Read this plan from the beginning and follow it literally. You inherit no conversation context. Do not restart discovery, recreate test records, broaden the refactor, or repeat an external mutation beyond the exact renewed authorization recorded here.

**Outcome:** Preserve all verified Ximalaya knowledge and working capabilities, align subsequent work with `DOMAIN_SKILL_DESIGN.md`, make only evidence-required root-cause corrections, safely resolve two current test records, verify sound replacement if the renewed single retry succeeds, clean up exact test data, and finish with a smaller-or-equal conceptual surface rather than a broader site SDK.

**Done when:** Existing publishing, scheduled publishing, immediate publishing, exact-track lookup, replacement, and deletion contracts remain available; no verified selector/API/constraint/safety guard is lost; prior record `1012239040` is deleted after at most one renewed deletion attempt; current replacement-test record `1012564622` receives at most one renewed M4A replacement attachment and is proven replaced before deletion; focused/full/registry/syntax/diff tests pass; no historical content, existing evidence, previous plan, Browser Harness core, dependency, Git history, or browser/Profile is modified.

**Workspace root:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Repository root:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Plan file:** `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-09-08-ximalaya-domain-skill-minimal-refactor-and-recovery.md`

**Design standard:** `/Users/yelin/Developer/agent-tools/browser-harness/DOMAIN_SKILL_DESIGN.md`

**Previous plans, immutable:**

- `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-09-07-ximalaya-publishing-domain-skill.md`
- `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-09-08-ximalaya-publishing-replacement-completion.md`

**Previous evidence, immutable:**

- `/tmp/browser-harness-ximalaya-publishing-20260907/evidence.md`
- `/tmp/browser-harness-ximalaya-publishing-20260907/scheduled_submission.json`
- `/tmp/browser-harness-ximalaya-replacement-20260908/evidence.md`

**New evidence ledger:** `/tmp/browser-harness-ximalaya-minimal-recovery-20260908/evidence.md`

**Target environment:** Local development, macOS Darwin, `/bin/zsh`, Asia/Shanghai, repository `main`, managed browser `SAU-自媒体运营-2号-9226`, Ximalaya account `水蜜桃英语` / UID `77566037`.

**Execution mode:** `unattended`. The user has explicitly renewed exactly one deletion attempt for `1012239040`, exactly one replacement attachment attempt for `1012564622`, and deletion of the successfully replaced current-run record. Routine inspection, minimal code edits, tests, read-only reconciliation, and those exact mutations proceed without reconfirmation. Any changed target or additional mutation requires a new confirmation.

**Execution environment:** Verified by the author on 2026-09-08 at 08:30 CST: filesystem/network available; Browser Harness checkout version 0.1.9; Python 3.14.6; `uv 0.11.7`; `playwright-cli 0.1.19`; CodeGraph 1.4.1; FFmpeg/FFprobe available; 9226 running and healthy with no Agent Pool lease/write lock. Browser Harness advertises 0.1.13, but updates are out of scope.

**Architecture/approved approach:** Do not rewrite the current 1395-line module merely to reduce line count. Its 19 public functions currently map to L2 domain reads, field setters, snapshots, or guarded non-idempotent commands; keep their signatures and behavior unless direct evidence proves a defect. Do not split files, add layers, introduce a generic publisher, or merge the workflow into one macro. Apply the smallest patch at the failed shared boundary, add the smallest regression test, and leave validated code alone.

**Tech stack:** Python 3.11+ project; current Python 3.14.6; `cdp-use==1.4.5`, `fetch-use==0.4.0`, `pillow==12.3.0`, `websockets==15.0.1`; pytest via `uv run --with pytest`; Browser Harness/CDP; no new dependency.

## Required Skills and Rules

- `writing-plans`
  - SKILL.md: `/Users/yelin/.codex/skills/writing-plans/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/writing-plans/references/lessons.md`
  - Use for: execution ledger, exact commands, interruption recovery, and completion proof.
- `ponytail:ponytail`
  - SKILL.md: `/Users/yelin/.codex/plugins/cache/devkeeper-ponytail-local/ponytail/4.8.4/skills/ponytail/SKILL.md`
  - Lessons: `none found`
  - Use for: preserve working code, delete only proven duplication, avoid speculative refactors, and patch root causes only.
- `browser-fleet-manager`
  - SKILL.md: `/Users/yelin/.codex/skills/browser-fleet-manager/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/browser-fleet-manager/references/lessons.md`
  - Use for: audit and resolve 9226 before browser access.
- `playwright-cli`
  - SKILL.md: `/Users/yelin/.agents/skills/playwright-cli/SKILL.md`
  - Lessons: `none found`
  - Use for: optional read-only diagnostics only after Browser Fleet audit/resolve.
- `browser-harness`
  - SKILL.md: `/Users/yelin/Developer/agent-tools/browser-harness/SKILL.md`
  - Lessons: `none found`
  - Use for: Agent Pool, page discovery, task-owned tabs, CDP/DOM/AX, upload, dialog, and readback.
- Repository rules:
  - `/Users/yelin/Developer/agent-tools/browser-harness/AGENTS.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/CLAUDE.md`
- Interaction references:
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/uploads.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/network-requests.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/dialogs.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/tabs.md`

Read all paths in full before their first use. If instructions conflict, repository rules and the current tool schema win.

## Immutable Knowledge and Artifact Contract

The user explicitly said already-produced work cost substantial effort and must not be casually rewritten.

Never modify:

- the two previous plans;
- the two previous Evidence Ledgers or any prior JSON/PNG/script artifact;
- `DOMAIN_SKILL_DESIGN.md` during execution;
- `/Users/yelin/Developer/agent-tools/browser-harness/AGENTS.md`, including its existing required reference to `DOMAIN_SKILL_DESIGN.md`;
- existing Bilibili files or their current local changes;
- Browser Harness core, registry, dependencies, versions, or production snapshot.

The executor may minimally modify only:

- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.py`
- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/ximalaya/publishing.md`
- `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_ximalaya_publishing.py`
- this plan's Progress Ledger
- the new Evidence Ledger outside the repository

Existing facts that must be preserved verbatim in substance:

- direct upload URL and cross-origin iframe discovery;
- account identity API and UID/name gate;
- album list, exact IDs, selected album facts;
- title 40 UTF-16-unit limit;
- 11 audio formats, size/bitrate observations;
- cover types/dimensions/crop behavior;
- scheduling timezone, two-hour lead, minute precision;
- submit via DOM `click()` and one-shot reconciliation;
- exact-track API/list evidence;
- replacement/deletion menus and native/DOM dialog distinction;
- every non-idempotent unknown-result rule.

## Renewed Authorization

On 2026-09-08 the user confirmed the following exact retry batch after being told both previous outcomes were unknown:

1. At most one additional delete attempt against exact record `1012239040`, title `BH喜马定时验收3-BHXM-20260907T155347-ba1fdb89`, album `88294964`.
2. At most one additional replacement-file attachment against exact record `1012564622`, title `BH喜马替换验收-BHXMR-20260908T070531-e7aa532b`, album `7980411`.
3. If and only if replacement is verified, delete exact record `1012564622` once.

No additional publish is authorized. No historical record is authorized. If an exact ID/title/album/account differs, stop before mutation.

## Current Verified State

- Git: `main`, HEAD `fd5195bcea8896a809c99240898831753e20bd99`, behind `origin/main` by one. Do not pull/fetch/merge/rebase/reset/switch.
- Intentional working tree: modified `AGENTS.md`, Bilibili files, and registry; untracked Ximalaya module/docs/tests, design standard, and prior plans. `AGENTS.md` already requires Domain Skill authors to read `DOMAIN_SKILL_DESIGN.md`; preserve that user change exactly. Do not clean, stash, commit, or normalize its missing final newline.
- Ximalaya module: 1395 lines at author inspection; 59 top-level functions; 19 public and 40 private.
- AST inspection found no private top-level function with zero internal references.
- All 19 public functions correspond to a domain query, field operation, snapshot/diagnostic, or guarded submit/replace/delete command. Public count alone is not a refactor trigger.
- Tests at stopped checkpoint: focused 33 passed; full 373 passed; registry 103 passed; syntax and diff check passed.
- Prior exact record `1012239040`: still present, live mode `immediate`, album `88294964`; one earlier delete menu activation occurred, result unknown.
- Current replacement target `1012564622`: still present in album `7980411`; duration 90.0 seconds; `audio_resource_id=u_37664936300`; updated time `2026-09-08 07:27:31`; one earlier M4A attachment occurred but no media change was observed after 900 seconds.
- Both read-only facts were rechecked by the plan author after the weak executor stopped.
- Browser 9226 was healthy, running, and idle after author cleanup.

## Scope

### In scope

- Reconcile actual state before mutation.
- Audit current public functions against `DOMAIN_SKILL_DESIGN.md` without changing them merely for aesthetics.
- Diagnose the exact delete-confirmation and replacement-attachment boundaries using read-only DOM/network/source evidence.
- Make the smallest root-cause patch only if current code cannot safely perform the renewed attempt.
- Add a focused regression test for each actual code defect fixed.
- Execute the exact renewed deletion/replacement/cleanup batch.
- Update permanent Markdown only with stable, verified replacement/deletion facts; keep run-specific details in the new Evidence Ledger.
- Run final tests and scope audits.

### Out of scope

- New features, additional public functions, generic interfaces, classes, Page Objects, adapters, factories, config systems, plugin systems, multiple modules, or dependencies.
- Renaming or moving functions solely to reduce API count.
- Reformatting/reordering the complete module.
- Replacing 19 public functions with one end-to-end workflow macro.
- Reopening completed field/limit/album/schedule discovery.
- New publication, another test record, another replacement after the renewed retry, or another delete attempt after an unknown renewed result.
- Editing previous plans/evidence, design standard, registry, core, Bilibili, Git history/remotes, production version, browser/Profile, or historical Ximalaya content.

## Execution Contract

- Start from actual repository and external state, not prior prose.
- Use `./browser-harness agent-pool run --browser "SAU-自媒体运营-2号-9226" --site "ximalaya.com" --account "77566037"` with read/write mode matching the action.
- After every `new_tab()` or `goto_url()`, call `wait_for_load()` and inspect `page_info()`; read every returned `domain_skill_files` Markdown before site-specific action.
- Recheck UID `77566037`, exact name, album ID, record ID, and exact title before every write.
- Every renewed mutation has a counter initialized from previous evidence, not zero:
  - prior delete activations begin at 1 and may reach at most 2;
  - replacement attachments begin at 1 and may reach at most 2;
  - current-record delete begins at 0 and may reach at most 1 after replacement verification.
- Persist the new activation fact before waiting for a dialog, request, or API state.
- Timeout or interruption after activation permits read-only reconciliation only.
- Do not treat unchanged state as permission for a third attempt.
- Close only task-owned tabs by exact ID; leave Chrome running.
- Never log credentials, cookies, authorization headers, full request bodies, full media URLs, or unrelated content.

## Minimality Gate

Before any refactor, classify each proposed change:

1. **Required root fix:** current live evidence proves behavior is incorrect or unsafe. Implement and test.
2. **Deletion of exact duplication/dead code:** CodeGraph plus direct source proves no consumer and tests cover removal. Delete.
3. **Naming/layout/style preference:** skip.
4. **Speculative future flexibility:** skip.
5. **Line-count reduction that moves complexity elsewhere:** skip.
6. **Safety guard, input validation, exact identity, one-shot behavior, or unknown-result protection:** preserve even if verbose.

There is no target line count. A no-refactor result is valid when the audit finds no safe simplification beyond root fixes.

## Required Public Surface

Preserve these existing L2 capabilities unless a direct test proves the signature itself unusable:

- Observation: `account_identity`, `publishing_constraints`, `list_albums`, `archive_matches`, `submission_snapshot`, `submission_diagnostics`, `track_evidence`, `manager_evidence`.
- Form preparation: `prepare_upload`, `select_album`, `set_title`, `set_custom_cover`, `set_description`, `set_publish_mode`, `set_schedule_datetime`.
- Guarded mutations: `submit_once`, `replace_sound_once`, `delete_once`.
- Guard: `require_identity`.

Do not add `publish_all`, `replace_and_delete`, `workflow_runner`, a service class, or another public helper.

## Progress Ledger

| Task | Status | Completion evidence |
| --- | --- | --- |
| Task 0 — Resume/freeze baseline | complete | Baseline, immutable hashes, exact live reconciliation, browser/pool state persisted in the new Evidence Ledger. |
| Task 1 — Minimal abstraction audit | complete | `no_structural_refactor`; CodeGraph/source audit retained the L2 surface and patched only proven menu/dialog/disabled-confirmation/API boundaries; focused/full tests pass. |
| Task 2 — Renewed exact deletion recovery | complete | After explicit renewed user authorization, the source-backed direct delete API returned HTTP 200/`ret=0`; final read-only reconciliation proves exact `1012239040` absent. |
| Task 3 — Renewed replacement recovery | incomplete | One renewed M4A attachment and one ineffective disabled-button confirmation completed (`replacement_unverified`); source diagnosis and local fix are recorded, but `1012564622` remains at 90s with the original resource and no third attachment is allowed. |
| Task 4 — Exact current-record cleanup | skipped | Replacement was not verified, so deleting `1012564622` would violate the plan gate. |
| Task 5 — Durable documentation and final gate | incomplete | Durable replacement/delete API facts documented; focused/full tests now `36/376`, registry `103`; old record is absent but current replacement record remains and Task 4 is gated. |

Update only this table with `apply_patch`; put detailed run evidence in the new Evidence Ledger.

## Task 0: Resume and freeze the baseline

**Risk:** safe/read-only.

- [ ] Read all Required Skills/rules, design standard, immutable previous plans/evidence, current Ximalaya files, and complete current diff.
- [ ] Run from `/Users/yelin/Developer/agent-tools/browser-harness`:
  ```bash
  pwd
  git branch --show-current
  git rev-parse HEAD
  RTK_DISABLED=1 git status --porcelain=v1 --branch
  RTK_DISABLED=1 git diff --check
  codegraph status "/Users/yelin/Developer/agent-tools/browser-harness" --json
  RTK_DISABLED=1 python3 "/Users/yelin/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py" audit
  RTK_DISABLED=1 python3 "/Users/yelin/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py" resolve --name "SAU-自媒体运营-2号-9226"
  ./browser-harness agent-pool status --browser "SAU-自媒体运营-2号-9226"
  rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"
  rtk uv run --with pytest pytest -q
  rtk python3 "scripts/verify_domain_skills.py"
  ```
- [ ] Expected baseline: focused 33, full 373, registry 103, diff check clean, browser healthy/no conflict/no lease. If another user changed the checkout, record actual all-pass counts and stop only if changes overlap the three allowed Ximalaya files.
- [ ] Create `/tmp/browser-harness-ximalaya-minimal-recovery-20260908` with `mkdir -p`; create/resume `evidence.md` with `apply_patch`. Record hashes of all immutable artifacts and allowed implementation files. Author-observed immutable hashes are `AGENTS.md=28d36bff2835cb38c811a75216227cefe0a767f856e4e6e90d535a9a0dfd61fe`, `DOMAIN_SKILL_DESIGN.md=85a699c59b4b3d24af43953eb200e838eadebe6b2f07f73b6a85a7837bfdb61c`, previous 0907 plan `f3cb9e71752de63292719ab0de31665159209f3f1029d6ed99ae91a00d151394`, and previous 0908 plan `a586c328cb4ecdcbc94ed5ca5a553bc5e7a732ba9d061034a8d583e898e3fc74`; execution-time hashes may differ only if another user action changed them before Task 0, in which case record the new baseline and do not overwrite it.
- [ ] Read-only reconcile both exact IDs/titles. Record duration/resource ID for `1012564622` and live mode/album for `1012239040`.

**Acceptance:** Baseline, hashes, existing counters, exact records, browser state, and first safe action are persisted; no write occurred.

## Task 1: Apply the Domain Skill minimality audit

**Risk:** read-only unless an exact deletion candidate is proven.

- [ ] Use CodeGraph query/callers/callees plus direct AST/source reading to classify all 19 public functions as L1/L2/L3 and every proposed edit through the Minimality Gate.
- [ ] Verify current private functions have internal consumers. Do not delete based only on an underscore/name or line count.
- [ ] Search exact duplicate code/tests. Delete only byte-equivalent duplication whose removal changes no behavior.
- [ ] Record one of two conclusions:
  - `no_structural_refactor`: current public surface is already L2; only root fixes continue;
  - `minimal_deletion`: list exact symbol/duplicate, consumer proof, and test proving removal.
- [ ] Do not modify code during classification. If minimal deletion is proven, apply one patch and immediately run focused tests.

**Acceptance:** No speculative abstraction or API redesign is planned; every retained verbose block is tied to a safety/website constraint or active consumer.

## Task 2: Resolve the prior record with one renewed delete attempt

**Risk:** destructive external action, exact renewed authorization exists.

- [ ] Reconcile `1012239040` first. If absent, record `prior_deleted` and skip mutation. If present, require exact account/title/album and one unique match.
- [ ] Diagnose the prior blocking boundary before mutation:
  - verify whether delete opens a native JavaScript dialog, DOM modal, or both;
  - verify `page_info()` pending-dialog handling and `Page.handleJavaScriptDialog` path;
  - verify `_confirm_dialog_accept()` does not synchronously call page JS while a native dialog freezes Runtime;
  - verify the exact menu item and confirmation are each scoped to `1012239040`.
- [ ] If current code already covers the observed dialog path, do not edit it. If not, patch only `_confirm_dialog_accept()` or its single caller and add one exact regression test reproducing the observed pending-dialog state.
- [ ] Run focused tests and syntax before live mutation.
- [ ] Persist `prior_delete_activations=2` immediately before/at the renewed menu activation; invoke exact deletion once.
- [ ] If result is unknown, never attempt a third activation. Reconcile exact ID/title read-only and stop this branch if it remains.
- [ ] Success requires absence from scheduled and album-track APIs and unchanged neighboring record sample/count.

**Acceptance:** `1012239040` absent with renewed activation count at most 2 total; or branch explicitly remains unknown with no third attempt.

## Task 3: Resolve sound replacement with one renewed attachment

**Risk:** destructive overwrite of exact current-run test audio, renewed authorization exists.

- [ ] Reconcile `1012564622`. If duration/resource evidence already changed to the M4A, mark replacement verified and skip attachment. If absent or identity differs, stop. If still exact 90-second/original resource, continue.
- [ ] Before attachment, identify the previous no-op root cause using read-only evidence:
  - inspect the exact current row/menu and the dynamically created replacement uploader;
  - prove the selected `input[type=file]` belongs to the exact `替换声音` uploader, not upload-page or another row input;
  - inspect replacement-specific upload initialization/block/merge requests and the final apply/confirm request path from frontend code or non-mutating setup;
  - determine whether file attachment alone applies replacement or merely stages media;
  - determine the exact completion/confirmation state.
- [ ] Playwright CLI may assist only with a bounded read-only snapshot/request list after Browser Fleet audit/resolve. It must detach and must not upload/click the mutation.
- [ ] Patch only the proven shared root cause inside existing private replacement helpers or `replace_sound_once()`. Do not create another public method, class, or workflow layer.
- [ ] Add one focused unit test that fails for the proven previous no-op and passes after the patch. Existing eight replacement tests remain.
- [ ] Run syntax, focused tests, and full tests before renewed attachment.
- [ ] Persist `replacement_uploads_total=2` at the renewed attachment boundary. Attach the fixed M4A once. Trigger at most the one exact required apply/confirmation action proven by preflight.
- [ ] After attachment, only read-only reconciliation is allowed. Never make a third attachment.
- [ ] Success requires same ID/title/album/account; duration approximately 268.329796 seconds; changed independent media signal; unchanged cover/description/visibility/category/status; no second track.
- [ ] If still unchanged/unknown after the bounded deadline, record the exact requests/UI state and stop this branch. Do not claim success or delete under Task 4.

**Acceptance:** Replacement is proven with exactly two lifetime attachments at most, or remains honestly unknown with no third attempt and complete diagnostics.

## Task 4: Delete the exact replacement-test record after verified replacement

**Risk:** destructive external action, authorized only after Task 3 verified replacement.

- [ ] Require `replacement_verified`. If not true, skip this task and leave the plan incomplete.
- [ ] Recheck account, album `7980411`, track `1012564622`, exact title/run marker, and unique match.
- [ ] Call existing `delete_once()` once with exact verified submission evidence and `confirm=True`; persist `current_delete_activations=1` at activation.
- [ ] If unknown, read-only reconcile only; never activate delete again.
- [ ] Success requires exact ID/title absent and album historical count/sample restored to pre-test baseline.

**Acceptance:** `1012564622` absent after at most one delete; no historical record changed.

## Task 5: Preserve durable knowledge and run the final gate

**Risk:** local documentation/tests and read-only audit.

- [ ] Update `publishing.md` only when Tasks 2–4 establish a stable new website fact or correct an inaccurate contract. Do not rewrite existing verified sections or paste run logs into permanent documentation.
- [ ] Keep exact IDs, counters, timestamps, failures, request traces, and temporary media results in the new Evidence Ledger, not permanent Skill Markdown.
- [ ] Ensure the public API table remains at the existing capability level; no full-workflow macro or click-level public helper.
- [ ] Run from repository root:
  ```bash
  codegraph sync "/Users/yelin/Developer/agent-tools/browser-harness"
  uv run python -m py_compile "agent-workspace/domain-skills/ximalaya/publishing.py" "tests/unit/test_ximalaya_publishing.py"
  rtk uv run --with pytest pytest -q "tests/unit/test_ximalaya_publishing.py"
  rtk python3 "scripts/verify_domain_skills.py"
  rtk uv run --with pytest pytest -q
  RTK_DISABLED=1 git diff --check
  RTK_DISABLED=1 git status --short
  RTK_DISABLED=1 git diff -- "agent-workspace/domain-skills/ximalaya/publishing.py" "agent-workspace/domain-skills/ximalaya/publishing.md" "tests/unit/test_ximalaya_publishing.py" "docs/plans/2026-09-08-ximalaya-domain-skill-minimal-refactor-and-recovery.md"
  rtk rg -n 'T.B.D|T.O.D.O|F.I.X.M.E|Bearer |Authorization:|Cookie:|sessionid|access_token|refresh_token|password' "agent-workspace/domain-skills/ximalaya" "tests/unit/test_ximalaya_publishing.py"
  ```
- [ ] Reconcile both test IDs read-only. Completion requires both absent.
- [ ] Close task-owned tabs exactly, verify no Agent Pool lease/write lock, and rerun Browser Fleet audit without stopping any browser.
- [ ] Compare immutable artifact hashes and Bilibili hashes with Task 0. Any difference caused by this plan is failure.

**Acceptance:** All tests pass, registry remains 103, both exact records absent, durable docs accurate, no secret/junk, and changes are limited to proven Ximalaya root fixes/tests plus this new plan.

## Test Matrix

| Layer | Requirement | Check | Pass condition |
| --- | --- | --- | --- |
| Baseline | Preserve existing work | Focused/full/registry/diff before edit | 33/373/103 baseline or documented higher all-pass count |
| Architecture | Match design standard | Classify 19 public functions | All are L2/guard; no new public API or macro |
| Minimality | No speculative refactor | CodeGraph/AST/direct diff | Only proven root fixes or exact duplication deletion |
| Delete dialog | Avoid Runtime freeze | Focused native/DOM dialog test | Pending native dialog accepted without page-JS deadlock |
| Replacement selector | Exact dynamic uploader | Focused prior-no-op regression | Exact track's replacement input and apply boundary used |
| Replacement safety | One renewed attachment | Counter/evidence | Lifetime replacement attachments at most 2 |
| Replacement result | Real media changed | `track_evidence()` before/after | Same identity, 90s→268s, independent media signal changed |
| Old cleanup | Prior test removed | Exact API reconciliation | `1012239040` absent |
| New cleanup | Current test removed | Exact API reconciliation | `1012564622` absent after verified replacement |
| Regression | Repository behavior | Full pytest | At least 373 tests plus new tests pass; none skipped/failed |
| Registry | Discovery | `scripts/verify_domain_skills.py` | PASS registry=103 |
| Safety | Shared browser/account | Pool/fleet/tab checks | Exact account, no lease/tab, Chrome remains healthy |
| Preservation | Expensive artifacts | Hash comparison | Previous plans/evidence/design/Bilibili unchanged |

## Failure Recovery

| Situation | Required action | Forbidden action |
| --- | --- | --- |
| Context loss | Re-read this plan, immutable prior evidence, new ledger, Git state, exact live records, counters | Restart discovery or reset counters |
| Record already absent | Record success by read-only proof and skip mutation | Recreate record |
| Account/ID/title/album mismatch | Stop before action | Use row position, prefix, newest item, or fuzzy title |
| Prior delete renewed attempt unknown | Read-only reconcile; stop if still present | Third delete activation |
| Replacement already completed asynchronously | Verify and skip renewed attachment | Replace again |
| Replacement renewed attempt unknown | Read-only reconcile and retain record | Third attachment or false success |
| Replacement remains unverified | Leave Task 4 blocked | Delete and claim end-to-end replacement passed |
| Test failure twice | Rerun exact test raw and fix root cause only | Broad rewrite or disabled test |
| No safe simplification found | Record `no_structural_refactor` | Force line-count reduction |
| Unexpected overlapping user edit | Preserve and stop | Reset, checkout, clean, stash, overwrite |

## Final Acceptance Gate

Mark complete only if every condition is true:

1. Previous plans, previous evidence, `DOMAIN_SKILL_DESIGN.md`, registry, core, dependencies, Bilibili work, Git branch/history/remotes, production version, and browser/Profile are unchanged.
2. No new public function, class, framework, workflow runner, dependency, or file split was introduced.
3. Every code change is tied to a reproduced delete/replacement defect or proven exact duplication.
4. All verified Ximalaya facts, capabilities, identity guards, one-shot boundaries, and unknown-result protections remain.
5. `1012239040` is absent with no more than one renewed deletion attempt.
6. `1012564622` is proven replaced after no more than one renewed attachment: same identity, approximately 268.329796 seconds, and changed media evidence.
7. `1012564622` is then absent after at most one delete.
8. No historical sound or album property changed; album `7980411` returns to its pre-test count/sample.
9. Focused tests, full tests, registry verification, syntax, CodeGraph sync, `git diff --check`, secret scan, and scope audit all pass.
10. Browser 9226 remains running/healthy; no task tab, lease, or write lock remains.
11. Permanent Skill Markdown contains durable knowledge only; new run details live only in the new Evidence Ledger.
12. Progress Ledger contains fresh evidence for every task.

If renewed deletion or replacement remains unknown, the plan is not complete. Record the checkpoint and stop without a third attempt. Safety boundaries are not removable complexity.
