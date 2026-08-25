# Browser Harness Bilibili Publishing Implementation Plan

> **Executor:** Low-capability autonomous agent operating under the live permission and tool contract recorded below. Follow this document literally; do not infer omitted work or widen scope.

**Goal:** Merge upstream PR #639, fix Browser Harness Issue #25, complete the Bilibili publishing Domain Skill for Issues #26–#30, prove it with unit, fleet, concurrency, and one real scheduled Bilibili submission, then merge the branch into local `main` and push the resulting `main` to `origin`.
**Done when:** All focused and full tests pass; Domain Skill verification passes; explicit 9225/9226 routing never crosses accounts; same-browser work serializes and different-browser work can overlap; exactly one real video is accepted by Bilibili account MID `518800384` and scheduled for `2026-08-30 22:00` or the deterministic fallback below; the accepted record has AID/BVID recovery evidence; local `main`, `origin/main`, and the pushed commit SHA match; no unrelated/generated files are committed.
**Workspace root:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Repository root:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Plan file:** `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-08-25-browser-harness-bilibili-publishing.md`
**Target environment:** Local development and one authorized external Bilibili acceptance submission; macOS, zsh, Python 3.14.6, uv 0.11.7, ffmpeg 8.0, Browser Harness 0.1.9 source checkout.
**Execution mode:** Unattended. The user will be away and has explicitly forbidden routine questions, permission handoffs, and requests to continue.
**Authoring runtime:** Full Access, approval policy `never`, network enabled, verified 2026-08-25 Asia/Shanghai.
**Expected executor runtime:** `workspace-write` with Auto-review. Recheck it at startup. Auto-review receives scope-specific escalation requests; it is not permission itself. Do not ask the absent user to approve. Minimize escalations and send at most one exact request per required boundary-crossing action.
**Architecture/approved approach:** Reuse the existing managed-browser Agent Pool and existing Bilibili `publishing.py/.md` pair. A registered explicit local CDP endpoint maps back to its fleet browser name and keeps its lease; an unregistered explicit endpoint remains exact and is not silently replaced. Extend the existing Bilibili helper directly, with observable DOM/API verification after every write and one-click submission idempotency. Merge upstream #639 only; do not merge #640.
**Tech stack:** Python 3.11+ source package, stdlib CDP/HTTP wrappers, pytest supplied ephemerally through uv, existing Pillow dependency, shell-driven Browser Harness, Chrome CDP, Bilibili creator web UI/API.

## Required Skills

- `openai-docs`
  - SKILL.md: `/Users/yelin/.codex/skills/.system/openai-docs/SKILL.md`
  - Lessons: none found
  - Use for: refresh official Codex sandbox, Auto-review, and Goal guidance before execution.
- `ponytail:ponytail` at full intensity
  - SKILL.md: `/Users/yelin/.codex/plugins/cache/devkeeper-ponytail-local/ponytail/4.8.4/skills/ponytail/SKILL.md`
  - Lessons: none found
  - Use for: keep the diff minimal, reuse existing helpers, add no dependency or speculative abstraction.
- `browser-fleet-manager`
  - SKILL.md: `/Users/yelin/.codex/skills/browser-fleet-manager/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/browser-fleet-manager/references/lessons.md`
  - Use for: audit and resolve the exact managed browsers 9223, 9225, and 9226 without touching personal Chrome.
- repository `browser-harness` Skill
  - SKILL.md: `/Users/yelin/Developer/agent-tools/browser-harness/SKILL.md`
  - Lessons: none found
  - Use for: current-source CLI syntax, Agent Pool invocation, Domain Skill discovery, browser interaction, and tab safety.
- Bilibili Domain documents returned by `page_info()`; read all six before any site-specific browser action:
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/creator-dashboard.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/danmaku.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/interactions.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/navigation.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/replies.md`

## Applicable Rules

- `/Users/yelin/Developer/agent-tools/browser-harness/AGENTS.md`: use `./browser-harness`, preserve unrelated work, smallest diff, no reenacted recording.
- `/Users/yelin/Developer/agent-tools/browser-harness/CLAUDE.md`: follow `AGENTS.md`; use current checkout launcher.
- User-provided scoped instructions in this task: Chinese status output, RTK for routine commands, raw output for security/audit/full diff, `apply_patch` for edits, explicit paths, no destructive Git cleanup.
- User authorization recorded in this task:
  - one real Bilibili scheduled publication from the supplied render workspace is authorized;
  - reversible pre-submit and post-submit UI exploration is authorized;
  - `git commit`, merging this branch into `main`, and `git push origin main` are authorized;
  - do not ask again for those exact actions.

## Scope

- In scope:
  - upstream PR #639 exact CDP log redaction behavior;
  - Issue #25 exact explicit endpoint routing with managed-browser leasing;
  - Issues #26–#30 in Bilibili `publishing.py/.md`;
  - focused tests plus full unit regression;
  - real 9225/9226 identity, serial, and parallel checks;
  - one real Bilibili submission on 9226;
  - explicit commits, merge to local `main`, and push to `origin/main`.
- Out of scope:
  - PR #640 and its Cloud shutdown/tab cleanup/version bump;
  - new dependencies, new framework layers, generalized publishing abstractions, SAU/Peach code changes;
  - deleting, retracting, immediately publishing, duplicating, or re-uploading an already accepted Bilibili record;
  - force push, history rewrite, reset, branch deletion, browser/Profile stop/move/retire/delete;
  - committing `.understand-anything/`, `.codegraph/`, `agent-workspace/recordings/`, `/tmp` evidence, downloaded media, cookies, tokens, or generated covers.
- Allowed side effects:
  - edit and test listed repository files;
  - create one 1280×720 PNG under `/tmp` from the authorized MP4;
  - open and close only task-owned browser tabs through Agent Pool;
  - upload the authorized MP4 and generated cover;
  - mutate the Bilibili draft form repeatedly;
  - click the final submit control exactly once;
  - retain the scheduled accepted video;
  - make scoped Git commits, merge, and push to `origin/main`.
- Forbidden side effects:
  - confirm any delete, retract, cancel-publication, immediate-publication, or duplicate-submission dialog;
  - operate personal Chrome or any unmanaged Profile;
  - print process command lines, cookies, authorization headers, CDP credentials, or daemon log secrets.

## Permission Feasibility

| Resource/action | Required capability | Expected executor path | No-user behavior |
| --- | --- | --- | --- |
| Repository edits | write `/Users/yelin/Developer/agent-tools/browser-harness` | workspace-write + `apply_patch` | proceed directly |
| Temporary cover/evidence | write `/tmp` | sandbox writable root | proceed directly |
| Managed browser audit | read processes, ports, registry | exact browser-fleet audit command; one Auto-review request only if host requires it | never ask user; do not print raw `ps` |
| Bilibili control | localhost CDP through `./browser-harness agent-pool` | already registered Chrome; network occurs inside browser session | proceed under explicit publication authorization |
| GitHub fetch/push | network and `.git` write | exact `git fetch origin`, `git push origin main`; use one scoped Auto-review request if required | never substitute force push; never ask user |
| Real external publication | logged-in 9226 session | exact one-click submission after identity/preflight gates | authorized; no extra confirmation |
| Goal persistence | live Goal tools | use only exposed schemas | no slash commands; no duplicate Goal |

## Goal Contract

- At startup, read this file from the first line, then read every Required Skill and applicable Lessons file in full.
- Refresh these official OpenAI pages and record the retrieval time in the Progress Ledger:
  - `https://learn.chatgpt.com/docs/sandboxing`
  - `https://learn.chatgpt.com/docs/sandboxing/auto-review`
  - `https://learn.chatgpt.com/docs/long-running-work`
- Inspect the live permission profile and Goal tool schemas. Official guidance says Goal preserves the current sandbox/approval boundaries and Auto-review is only a reviewer for eligible requests.
- If `create_goal`, `get_goal`, and `update_goal` are exposed with the same schemas as the authoring runtime:
  - on first execution, call `create_goal` with the exact Goal sentence at the top of this file and no token budget;
  - on resume, call `get_goal`; do not create a duplicate Goal;
  - call `update_goal(status="complete")` only after Task 9 passes.
- Do not use `/goal` as a tool call.
- Continue autonomously through safe, authorized steps. Do not ask the user to choose selectors, titles, tags, retry actions, commit messages, merge strategy, or whether to publish.
- A failed command gets at most two retries, and only after collecting new evidence or applying a specific correction. Never loop on the same output.
- If compacted or interrupted: call `get_goal`, reread this plan and Lessons, inspect `git status --short`, inspect `/tmp/bh-bilibili-acceptance.json` if present, then continue from the first unchecked task.

## Current-State Evidence

- Author verification date: 2026-08-25 Asia/Shanghai.
- Current branch: `codex/bilibili-browser-harness-publishing`.
- `HEAD`, local `main`, and `origin/main` all initially point to `d81747c`.
- Existing untracked user work that must be preserved:
  - `.understand-anything/`
  - `agent-workspace/domain-skills/bilibili/publishing.py`
  - `agent-workspace/domain-skills/bilibili/publishing.md`
  - `agent-workspace/recordings/`
- Full baseline: `217 passed in 0.64s` using `uv run --with pytest pytest -q tests/unit`.
- Domain registry baseline: `PASS registry=101 skills`.
- `uv run pytest` is invalid here because pytest is not declared. Always use `uv run --with pytest pytest`.
- CodeGraph 1.4.1 index exists at `/Users/yelin/Developer/agent-tools/browser-harness/.codegraph`.
- Browser fleet audit found four healthy managed browsers:
  - `AgentPool-共享主浏览器-9223` on 9223;
  - `热点监控-9224` on 9224;
  - `SAU-自媒体运营-9225` on 9225;
  - `SAU-自媒体运营-2号-9226` on 9226.
- Known Bilibili identities from the issue reproduction:
  - 9225: MID `526557505`, name contains `Stella英语听力磨耳朵`;
  - 9226: MID `518800384`, name contains `水蜜桃英语`.
- Real MP4:
  - `/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1782692819486-part-1/output.mp4`
  - 18,742,465 bytes; H.264/AAC; 1920×1080; 29.781333 seconds.
- Manifest:
  - `/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1782692819486-part-1/input/manifest.json`
  - publisher `水蜜桃英语`;
  - title package describes `中奖彩票反成球迷陷阱`;
  - no final 16:9 cover file exists in the render workspace.
- PR #639 commit is locally available as `11dbb41594db48855a42450997ce88c29d7273c6` and changes only `daemon.py` plus `test_daemon.py`.
- PR #640 does not fix Issue #25 because its guard runs after Agent Pool routing; it is excluded.

## Requirement Traceability

| Requirement | Implemented by | Verified by |
| --- | --- | --- |
| #639 redacts credentials/path/query without connection changes | Task 2 | focused daemon tests, raw diff audit |
| #25 exact managed CDP remains exact and leased | Task 3 | unit routing tests plus real 9225/9226 checks |
| same browser serial; different browsers parallel | Task 3 | timed concurrent real tests |
| #26 custom cover helper and readback | Task 4 | unit test plus real crop/confirm/reopen cycle |
| #27 tags work with initial auto tags | Task 4 | unit test plus real add/remove/re-add/readback cycle |
| #28 partition and description helpers | Task 4 | unit test plus real wrong-value/restore/readback cycle |
| #29 date+time scheduling and bounds | Task 4 | unit test plus real toggle/wrong-value/final-value cycle |
| #30 delayed manager evidence never causes a second submit | Task 5 | fake delayed evidence test plus real accepted record polling |
| Domain Skill has Python and Markdown | Task 4 | file readback and domain verifier |
| one real scheduled submission | Task 8 | account identity, snapshot, AID/BVID, manager schedule evidence |
| all effects reach local and remote main | Task 9 | local/remote SHA equality |

## File Map

| Action | Absolute path | Responsibility |
| --- | --- | --- |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/src/browser_harness/daemon.py` | #639 safe connection log label |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/src/browser_harness/agent_pool.py` | map explicit local CDP port to registered browser name |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/src/browser_harness/run.py` | route registered explicit endpoint through exact leased browser |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_daemon.py` | #639 security regression |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_agent_pool.py` | explicit endpoint/fleet mapping regressions |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_run.py` | legacy Hermes explicit endpoint routing regression |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py` | Bilibili publishing helpers and idempotent submit |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.md` | exact usage order, contracts, recovery, verification |
| Create | `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_bilibili_publishing.py` | focused Domain helper regressions |
| Keep | `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-08-25-browser-harness-bilibili-publishing.md` | this requested unattended execution plan and ledger |

Do not modify any other repository file unless a focused failing test proves the listed scope cannot work. A selector adjustment stays inside `publishing.py`; do not move site logic into core Browser Harness.

## Interface Contracts

### `agent_pool.browser_name_for_cdp(cdp_url: str | None) -> str | None`

- Accept HTTP or WebSocket endpoints.
- Return `None` for empty, non-loopback, or genuinely unregistered ports.
- Run the existing fleet script `audit` command and match the parsed port against `registered` entries.
- Return the unique registered browser name only when `status == "running"`, `health == "ok"`, and `problems` is empty.
- Raise `PoolError` for malformed ports, invalid audit JSON, duplicate registrations, or a matching unhealthy/conflicting browser.
- Never read the fleet registry directly and never construct or expose a Profile path.

### `set_custom_cover(path: str, timeout: float = 30) -> dict`

- Reject missing, empty, unreadable, or non-image files before touching the page.
- Use Pillow only to read width/height; Pillow is already installed.
- Use Browser Harness `upload_file()` on the visible cover image file input.
- Handle the Bilibili crop/confirm modal and click its visible `完成` control once.
- Return `{"custom_cover_set": True, "filename": str, "width": int, "height": int}` only after DOM readback proves a non-empty cover and the custom filename/input state is present.
- Never call `choose_recommended_cover()` and never submit.

### `set_tags(tags: list[str], timeout: float = 10) -> list[str]`

- Normalize surrounding whitespace, reject empty normalized entries, de-duplicate while preserving caller order.
- Preserve initial platform auto tags by default.
- Focus the real visible input with placeholder `按回车键Enter创建标签`; set one target at a time; dispatch input/change events; send Enter through Browser Harness `press_key`.
- After each target, wait until `_selected_tags()` contains it before continuing.
- Return the page's full real selected-tag list, including retained automatic tags.
- On rejection or quota limit, raise with the exact missing target and observed list.

### `set_partition(name: str, timeout: float = 10) -> str`

- Reject blank name.
- Open the visible partition selector, choose an exact visible matching option, and handle a second-level option when the UI requires it.
- Never accept body text merely containing `分区` as proof.
- Return the exact selected partition text read from the selector's selected-value element.
- Raise with requested and observed values when unavailable.

### `set_description(text: str, timeout: float = 10) -> str`

- Find the visible `.ql-editor[contenteditable=true]`.
- Replace its content, dispatch `beforeinput`, `input`, `change`, and `blur` events as accepted by the current page.
- Return normalized `innerText` only after it exactly equals the requested normalized text.

### `set_schedule_datetime(value: str, timeout: float = 15) -> dict`

- Parse exactly `YYYY-MM-DD HH:MM` with `datetime.strptime`.
- Require minute divisible by five.
- Before page interaction, require the target to be at least five minutes in the future and no more than fifteen days ahead, using local Asia/Shanghai wall time.
- Enable scheduling, set both calendar date and time, then strictly read back both fields.
- Return `{"schedule_date": "YYYY-MM-DD", "schedule_time": "HH:MM", "schedule": "YYYY-MM-DD HH:MM"}`.
- Keep `set_schedule_time(hour, minute)` only as a backward-compatible same-day wrapper calling the new function.

### `submission_snapshot() -> dict`

Return real DOM values for at least:

```python
{
    "title": str,
    "cover_ready": bool,
    "custom_cover_set": bool,
    "cover_filename": str,
    "partition": str,
    "description": str,
    "tags": list[str],
    "declaration": str,
    "scheduled": bool,
    "schedule_date": str,
    "schedule_time": str,
    "submit_text": str,
}
```

Do not keep the current fake `category = body contains 分区` boolean.

### `submit_once(...) -> dict`

- Preserve existing identity, exact-title duplicate, form snapshot, and single-click gates.
- Store a local `clicked` fact before polling; no code path may invoke the submit click twice.
- Once exactly one archive record appears, preserve its AID/BVID and poll manager evidence inside the same overall timeout.
- If exact schedule evidence appears, return `status="verified"` and the manager evidence.
- If the deadline expires after archive acceptance, return `status="accepted_but_schedule_unverified"`, the archive record, the expected schedule, and the last manager error/text. Do not throw an error that suggests retrying submission.
- If no archive ever appears, raise the existing no-evidence timeout with `do not retry blindly` language.
- Multiple exact-title records remain a hard error.

## Progress Ledger

| Task | Status | Completion evidence |
| --- | --- | --- |
| Task 1: startup and baseline | completed | Python 3.14.6, uv 0.11.7, rtk 0.43.0, CodeGraph 1.4.1, ffmpeg 8.0, gh 2.82.0; CodeGraph status complete; baseline `217 passed in 0.67s`; Domain Skill verifier `PASS registry=101 skills`; fleet audit healthy for 9223/9225/9226; official OpenAI docs refreshed 2026-08-25 19:45:14 +0800 (`sandboxing`, `sandboxing/auto-review`, `long-running-work`). |
| Task 2: merge #639 behavior | completed | Commit `fc5ea2b`; raw focused daemon suite `35 passed`; raw diff confirms endpoint construction unchanged and only topology label is logged. |
| Task 3: fix exact endpoint routing | completed | Commit `91a57a5`; focused agent-pool/run suite `52 passed`; CodeGraph impact of `should_manage_legacy` reaches only `run.py` and its main path; registered, unregistered, remote, malformed, duplicate, and unhealthy endpoint cases covered. |
| Task 4: complete publishing fields | completed | `publishing.py/.md` now expose custom cover, normalized tags, partition, description, full date/time schedule, and real snapshot readback; focused coverage passed `8` field tests; Domain Skill verifier `PASS registry=101 skills`. |
| Task 5: make submit recovery idempotent | completed | Focused Bilibili suite passed `13`; delayed manager evidence verified after two mismatches with one click; accepted-but-unverified, no-evidence, multiple-record, and pre-existing duplicate gates covered. |
| Task 6: static/full regression | pending | — |
| Task 7: real fleet and concurrency tests | pending | — |
| Task 8: high-intensity real Bilibili acceptance | pending | — |
| Task 9: commit, merge, push, final proof | pending | — |

### Task 1: Startup, protect existing work, and reproduce the baseline

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** safe/read-only, except the requested plan ledger update.

- [ ] Read all Required Skills, Lessons, `AGENTS.md`, `CLAUDE.md`, and this plan fully.
- [ ] Inspect live Goal schemas. Create or resume the Goal according to the Goal Contract.
- [ ] Keep the Mac awake for six hours without changing system settings:
  - Command: `caffeinate -dimsu -t 21600 &`
  - Expected: a background `caffeinate` process; no prompt.
- [ ] Record repository state without modifying it:
  - Command: `RTK_DISABLED=1 git status --short --branch`
  - Expected branch: `codex/bilibili-browser-harness-publishing`.
  - Preserve all four known untracked paths. Never run clean/reset/checkout restore.
- [ ] Verify tools:
  - Command: `python3 --version && uv --version && rtk --version && codegraph --version && ffmpeg -version | head -1 && gh --version | head -1`
  - Expected: all exit zero.
- [ ] Inspect CodeGraph before source edits:
  - Command: `codegraph status "/Users/yelin/Developer/agent-tools/browser-harness" --json`
  - Then query/callers for `_safe_connection_label`, `should_manage_legacy`, `run_managed`, `submission_snapshot`, and `submit_once` when indexed. Untracked `publishing.py` is authoritative if absent from the index.
- [ ] Run baseline tests:
  - Command: `rtk uv run --with pytest pytest -q "tests/unit"`
  - Pass: exactly 217 tests or a larger count if another authorized change already landed, exit zero.
  - Command: `rtk uv run python "scripts/verify_domain_skills.py"`
  - Pass: output starts with `PASS`.
- [ ] Run fleet audit with the exact Skill command:
  - Command: `python3 "/Users/yelin/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py" audit`
  - Pass: 9223, 9225, and 9226 registered, running, health `ok`, no problems/conflicts.
  - If one is stopped, use the Skill's exact `start --name` command for that registered browser, then audit once more. Starting is allowed; never stop or mutate a Profile.
- [ ] Update the Progress Ledger only after every check above passes.

### Task 2: Port upstream #639 exactly and verify security behavior

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** repository mutation; security-sensitive, raw verification mandatory.

- [ ] Inspect the local upstream commit before editing:
  - Command: `RTK_DISABLED=1 git show --format=fuller --no-ext-diff 11dbb41594db48855a42450997ce88c29d7273c6 -- "src/browser_harness/daemon.py" "tests/unit/test_daemon.py"`
  - Pass: only safe label helper, log call replacement, and four parameterized cases.
- [ ] Use `apply_patch` to add this exact helper immediately after `log()` in `daemon.py`:

```python
def _safe_connection_label(url):
    """Log only endpoint topology, never CDP credentials or provider session paths."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return "<redacted-cdp-endpoint>"
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{host}{port}"
    except (TypeError, ValueError):
        return "<redacted-cdp-endpoint>"
```

- [ ] Replace only `log(f"connecting to {url}")` with `log(f"connecting to {_safe_connection_label(url)}")`.
- [ ] Add the four upstream parameterized test cases to `tests/unit/test_daemon.py`: credentials/path/query, provider session path, IPv6, malformed input.
- [ ] Focused raw test:
  - Command: `RTK_DISABLED=1 uv run --with pytest pytest -q "tests/unit/test_daemon.py" -vv`
  - Pass: all daemon tests pass; safe-label parameterizations show four passes.
- [ ] Raw security diff:
  - Command: `RTK_DISABLED=1 git diff -- "src/browser_harness/daemon.py" "tests/unit/test_daemon.py"`
  - Pass: no credential literal is written outside test input; connection construction unchanged.
- [ ] Commit only these two files because the user authorized commits:
  - Command: `rtk git add "src/browser_harness/daemon.py" "tests/unit/test_daemon.py"`
  - Command: `git commit -m "fix: redact CDP credentials from daemon logs"`
  - Do not stage any other path.

### Task 3: Fix Issue #25 without bypassing managed-browser leases

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** core routing change; fail closed.

- [ ] Add `browser_name_for_cdp()` to `agent_pool.py` beside `_resolve_browser()`. Use exactly this decision logic:

```python
def browser_name_for_cdp(cdp_url: str | None) -> str | None:
    if not cdp_url:
        return None
    parsed = urlparse(cdp_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise PoolError("explicit CDP URL has an invalid port") from exc
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not port:
        return None
    command = [sys.executable, str(FLEET_SCRIPT), "audit"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PoolError(f"browser fleet audit failed: {exc}") from exc
    if result.returncode != 0:
        raise PoolError(f"browser fleet audit rejected the request: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PoolError("browser fleet audit returned invalid JSON") from exc
    registered = data.get("registered") if isinstance(data, dict) else None
    if not isinstance(registered, list):
        raise PoolError("browser fleet audit returned no registered browser list")
    matches = [item for item in registered if isinstance(item, dict) and item.get("port") == port]
    if not matches:
        return None
    if len(matches) != 1:
        raise PoolError(f"browser fleet has multiple registrations for CDP port {port}")
    browser = matches[0]
    if (browser.get("status") != "running" or browser.get("health") != "ok"
            or browser.get("problems")):
        raise PoolError(f"registered browser on CDP port {port} is not healthy")
    name = browser.get("name")
    if not isinstance(name, str) or not name:
        raise PoolError(f"registered browser on CDP port {port} has no name")
    return name
```

- [ ] In `run.py`, immediately before the existing legacy `run_managed` call, resolve the actual endpoint with WebSocket precedence, matching `daemon.get_ws_url()`:

```python
explicit_endpoint = os.environ.get("BU_CDP_WS") or os.environ.get("BU_CDP_URL")
browser_name = agent_pool.browser_name_for_cdp(explicit_endpoint)
if not explicit_endpoint or browser_name:
    sys.exit(agent_pool.run_managed(
        agent_pool._default_owner(),
        agent_pool.infer_site(code),
        "default",
        "write",
        code,
        browser_name=browser_name,
    ))
```

  Exact meaning:
  - no explicit endpoint: legacy behavior, fallback registered 9223;
  - registered loopback explicit endpoint: preserve legacy lease but select its exact fleet browser;
  - unregistered or remote explicit endpoint: skip legacy Agent Pool and let existing daemon code honor the explicit endpoint directly;
  - unhealthy/conflicting registered port: raise and fail closed; never fall back to 9223.
- [ ] Add unit tests to `test_agent_pool.py` for registered 9226, unregistered 9333, non-loopback remote WebSocket, malformed port, duplicate registration, and unhealthy matching registration.
- [ ] Add `test_run.py` tests proving:
  - Hermes + `BU_CDP_URL=http://127.0.0.1:9226` passes browser name `SAU-自媒体运营-2号-9226` to `run_managed`;
  - Hermes + remote `BU_CDP_WS` does not call `run_managed` and does call `ensure_daemon`;
  - no explicit endpoint continues to call `run_managed` with `browser_name=None`.
- [ ] Focused tests:
  - Command: `rtk uv run --with pytest pytest -q "tests/unit/test_agent_pool.py" "tests/unit/test_run.py"`
  - Pass: exit zero.
- [ ] Inspect impact:
  - Command: `codegraph impact "should_manage_legacy" --path "/Users/yelin/Developer/agent-tools/browser-harness" --json`
  - Verify only `run.py` legacy routing and its tests need updates.
- [ ] Commit only routing files:
  - `rtk git add "src/browser_harness/agent_pool.py" "src/browser_harness/run.py" "tests/unit/test_agent_pool.py" "tests/unit/test_run.py"`
  - `git commit -m "fix(agent-pool): honor explicit managed browser endpoints"`

### Task 4: Complete Bilibili form helpers for Issues #26–#29

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** Domain Skill code; no real submission in this task.

- [ ] Preserve the existing untracked `publishing.py/.md`; edit them in place with `apply_patch`. Do not recreate the files from scratch.
- [ ] Keep existing helpers and constants. Add only these small shared primitives where reused by at least two new functions:
  - `_wait_until(callback, timeout, message)` using `time.monotonic()` and existing `wait()`;
  - `_selected_tags()` reading `.label-item-v2-content` real text;
  - `_normalized_text(value)` for whitespace-only comparison.
  Do not add classes, adapters, configuration objects, or new dependencies.
- [ ] Implement the five interfaces exactly as defined above:
  - `set_custom_cover`;
  - corrected `set_tags`;
  - `set_partition`;
  - `set_description`;
  - `set_schedule_datetime`, with `set_schedule_time` as wrapper.
- [ ] Replace `submission_snapshot()` with real-field readback. The snapshot must not claim category success merely because the page contains the word `分区`.
- [ ] Selector rules for the current Vue page:
  - always filter candidates by positive bounding-box width/height;
  - prefer semantic placeholder/text/role and stable component structure;
  - never select a hidden duplicate input;
  - after a click, verify the specific changed field;
  - coordinate clicks are allowed for publishing because this is an authorized write flow; activate only the task-owned tab when a real page control requires focus;
  - never reuse `bilibili_click_readonly()` for publishing writes.
- [ ] Create `tests/unit/test_bilibili_publishing.py` using the same `exec(compile(...), namespace)` pattern as `test_bilibili_interactions.py`. The fake namespace must provide `js`, `wait`, `upload_file`, `fill_input`, `press_key`, `click_at_xy`, `activate_tab`, `current_tab`, `goto_url`, `page_info`.
- [ ] Required focused tests:
  1. missing and empty custom cover fail before `upload_file`;
  2. valid image returns filename and dimensions only after accepted DOM state;
  3. initial tags `原创` and `短片` remain while five targets are added;
  4. duplicate/blank caller tags normalize deterministically;
  5. one rejected target reports that target and observed tags;
  6. partition returns exact selected text and rejects a false body-text match;
  7. description dispatches and reads back exact normalized text;
  8. schedule accepts exact date/time, rejects non-five-minute values, past values, and over-fifteen-day values;
  9. snapshot includes all contract keys and real values.
- [ ] Update `publishing.md` with:
  - absolute load path;
  - required order;
  - every public function signature, input, output, errors, and side effects;
  - exact examples for custom cover, tags, partition, description, declaration, schedule, snapshot, submit, and recovery;
  - explicit Agent Pool command selecting `SAU-自媒体运营-2号-9226` for the acceptance account;
  - hard rule: submit once, reconcile on accepted-but-unverified, never click again;
  - verification checklist matching the Test Matrix.
- [ ] Focused test:
  - Command: `rtk uv run --with pytest pytest -q "tests/unit/test_bilibili_publishing.py"`
  - Pass: every required case passes.
- [ ] Domain verification:
  - Command: `rtk uv run python "scripts/verify_domain_skills.py"`
  - Pass: `PASS`; `publishing.md` is discoverable for `member.bilibili.com` through the existing Bilibili directory mapping. Do not edit `registry.json` unless verification proves it absent.

### Task 5: Fix delayed manager evidence and preserve one-click idempotency

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** high because incorrect logic can duplicate a real post; tests first, no browser submission yet.

- [ ] Update `manager_evidence` so callers can obtain observed evidence/text without losing the exact mismatch reason. Keep navigation to `MANAGER_URL` and exact-title matching.
- [ ] Update `submit_once` to implement the interface contract above. Use one `deadline = time.monotonic() + timeout` for archive and manager verification together.
- [ ] Add tests proving:
  - the submit selector is invoked exactly once when archive evidence is delayed;
  - unique archive appears, manager mismatch occurs twice, third manager read verifies schedule, result is `status="verified"`;
  - unique archive appears but manager never verifies before deadline, result is `status="accepted_but_schedule_unverified"` with AID/BVID and no exception suggesting retry;
  - zero archive until deadline still raises no-evidence timeout;
  - multiple archives fail immediately;
  - a pre-existing exact-title archive blocks before clicking.
- [ ] Run focused tests:
  - Command: `rtk uv run --with pytest pytest -q "tests/unit/test_bilibili_publishing.py" -vv`
  - Pass: all tests pass; assertions explicitly count one submit click.
- [ ] Update `publishing.md` recovery section with a literal decision table:
  - `verified`: finish and retain AID/BVID;
  - `accepted_but_schedule_unverified`: poll read-only manager evidence; never call `prepare_upload` or `submit_once` again;
  - no archive evidence: do not blindly retry; inspect archive exact-title list first;
  - duplicate exact-title: never submit.
- [ ] Commit the Domain Skill batch:
  - `rtk git add "agent-workspace/domain-skills/bilibili/publishing.py" "agent-workspace/domain-skills/bilibili/publishing.md" "tests/unit/test_bilibili_publishing.py" "docs/plans/2026-08-25-browser-harness-bilibili-publishing.md"`
  - `git commit -m "feat(bilibili): complete verified publishing workflow"`
  - Do not add recordings, media, `.understand-anything`, or `.codegraph`.

### Task 6: Static, security, and full regression gate

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** safe/read-only.

- [ ] Synchronize CodeGraph after code changes:
  - Command: `codegraph sync "/Users/yelin/Developer/agent-tools/browser-harness"`
  - Then run `codegraph affected --path "/Users/yelin/Developer/agent-tools/browser-harness" --json` if supported by installed help; otherwise run `codegraph impact` for each changed core symbol.
  - Never stage `.codegraph` output.
- [ ] Compile changed Python:
  - Command: `python3 -m py_compile "src/browser_harness/daemon.py" "src/browser_harness/agent_pool.py" "src/browser_harness/run.py" "agent-workspace/domain-skills/bilibili/publishing.py" "tests/unit/test_bilibili_publishing.py"`
  - Pass: exit zero.
- [ ] Full unit suite:
  - Command: `rtk uv run --with pytest pytest -q "tests/unit"`
  - Pass: exit zero; count is greater than 217.
- [ ] Domain verifier:
  - Command: `rtk uv run python "scripts/verify_domain_skills.py"`
  - Pass: `PASS`.
- [ ] Raw security tests and diff:
  - Command: `RTK_DISABLED=1 uv run --with pytest pytest -q "tests/unit/test_daemon.py" "tests/unit/test_agent_pool.py" "tests/unit/test_run.py" -vv`
  - Command: `RTK_DISABLED=1 git show --stat --oneline HEAD~3..HEAD`
  - Command: `RTK_DISABLED=1 git diff --check main...HEAD`
  - Pass: no failures, whitespace errors, secrets, endpoint paths, or unrelated files.
- [ ] Placeholder/debug scan:
  - Command: `rtk rg -n "TBD|TODO|FIXME|print\(|pdb|breakpoint\(" "src/browser_harness" "agent-workspace/domain-skills/bilibili/publishing.py" "tests/unit/test_bilibili_publishing.py"`
  - Interpret existing unrelated matches separately. Changed files must contain no debug residue or unresolved placeholder.

### Task 7: Real exact-port, identity, serial, and parallel tests

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** reversible browser interaction; no publishing.

- [ ] Audit fleet again. Stop if any matching port is conflicting; never use a different browser as fallback.
- [ ] Immediately before the browser-test group, read all six absolute Bilibili Domain documents listed under Required Skills and record their SHA-256 hashes. Every browser call must first `new_tab("https://member.bilibili.com/platform/home")` and print `page_info()`. Proceed only when `domain_skill_files` is exactly the already-read list and the hashes are unchanged. If a new path appears, end that read-only call, read the new Markdown file, then start a fresh call. Use only task-owned tabs.
- [ ] Exact direct legacy routing check for 9225:

```bash
env HERMES_HOME="/tmp/bh-hermes-routing" HERMES_PROFILE_NAME="routing-test" \
  BU_NAME="explicit-9225" BU_CDP_URL="http://127.0.0.1:9225" \
  ./browser-harness <<'PY'
new_tab("https://member.bilibili.com/platform/home")
wait_for_load()
print(page_info())
print(js("fetch('https://api.bilibili.com/x/web-interface/nav',{credentials:'include'}).then(r=>r.json()).then(x=>({mid:x.data&&x.data.mid,uname:x.data&&x.data.uname,isLogin:x.data&&x.data.isLogin}))"))
PY
```

  Pass: MID `526557505`; name contains `Stella英语听力磨耳朵`.
- [ ] Repeat with `BU_NAME=explicit-9226`, URL port 9226.
  Pass: MID `518800384`; name contains `水蜜桃英语`.
- [ ] After each direct call run:
  - `./browser-harness agent-pool status --browser "SAU-自媒体运营-2号-9226"`
  - Pass: `leases=[]`, `write_locks={}` after cleanup.
- [ ] Same-browser serialization test:
  - Start two background `./browser-harness agent-pool run --browser "SAU-自媒体运营-2号-9226" --site example.com --account serial-test --mode write` calls; each prints epoch start/end and runs `wait(3)`.
  - Pass: second task's browser-held interval begins only after the first ends; total elapsed is at least 5.5 seconds; no overlapping hold intervals.
- [ ] Different-browser parallel test:
  - Start one 9225 and one 9226 write lease simultaneously; each waits three seconds and prints identity.
  - Pass: wall time below 5.5 seconds; identities remain distinct; both exit zero.
- [ ] Unavailable exact-browser fail-closed test without stopping Chrome:
  - Unit coverage is authoritative. Do not stop a real managed browser.
  - Run `browser_name_for_cdp("http://127.0.0.1:65534")` in a Python snippet and verify `None`; then verify direct explicit connection exits non-zero and does not produce 9223 identity. Do not wait more than the existing bounded daemon timeout.
- [ ] Record exact timestamps, MIDs, exit codes, and final empty lease state in `/tmp/bh-browser-routing-acceptance.json` using `apply_patch` or the executor's structured artifact tool. Do not commit it.

### Task 8: High-intensity real Bilibili acceptance and exactly one scheduled submission

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** authorized external write. This exact publication was approved by the user. Do not ask again.

#### Fixed acceptance data

```text
browser name: SAU-自媒体运营-2号-9226
expected MID: 518800384
expected name substring: 水蜜桃英语
video: /Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1782692819486-part-1/output.mp4
manifest: /Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1782692819486-part-1/input/manifest.json
cover: /tmp/bh-bilibili-cover-20260825.png
title: 中奖彩票：赢得大奖反而陷入困境？数千名足球球迷的荒谬遭遇｜外刊播客｜中英+文稿
description: 以中彩票比喻，讲述数千名足球球迷因赢得大奖反而陷入困境的荒谬现象。适合英语听力、英语新闻和重点词汇学习。
tags: 英语学习, 英语听力, 英语新闻, 足球, 彩票
partition: 知识
declaration: 内容无需标注
preferred schedule: 2026-08-30 22:00 Asia/Shanghai
```

Schedule fallback is deterministic and requires no question: if the preferred schedule is no longer at least five minutes in the future or Bilibili truthfully reports it outside the allowed window, use the next calendar day at 22:00 that is within fifteen days. Record the actual schedule. Never choose immediate publication.

- [ ] Validate the MP4 with `stat` and `ffprobe`; require non-empty, 1920×1080, video+audio, duration 29–31 seconds.
- [ ] Generate the cover only in `/tmp`:
  - Command: `ffmpeg -y -ss 1 -i "/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1782692819486-part-1/output.mp4" -frames:v 1 -vf "scale=1280:720" "/tmp/bh-bilibili-cover-20260825.png"`
  - Verify with `sips -g pixelWidth -g pixelHeight`; require 1280×720 and non-zero file.
- [ ] Before opening an upload page, run a read-only exact-title archive query through 9226.
  - If zero matches: continue to the new submission flow.
  - If exactly one match: this is a partial previous execution. Do not upload or submit. Record its AID/BVID and continue only with manager schedule reconciliation.
  - If multiple matches: do not submit; record the safety failure and continue all non-external verification. Never invent a new title to bypass the duplicate gate.
- [ ] Start the write lease with exactly:

```bash
./browser-harness agent-pool run \
  --browser "SAU-自媒体运营-2号-9226" \
  --site member.bilibili.com \
  --account "518800384" \
  --mode write <<'PY'
new_tab("https://member.bilibili.com/platform/upload/video/frame")
wait_for_load()
print(page_info())
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py").read())
print(require_identity(518800384, "水蜜桃英语"))
PY
```

  Before this write call, perform one separate read-mode discovery call that only opens the same upload URL and prints `page_info()`. Read every returned Markdown path, record its SHA-256 hash, and then start the write call above. The final write script may contain the later helper calls in the same lease, but it must retain this exact browser, site, account, mode, navigation, discovery, helper load, and identity gate. If the write call returns any new Domain path or a changed hash, exit it before touching the form, read the changed document, and start one fresh write call.
- [ ] Run `prepare_upload()` and wait for `上传完成`. Do not submit.
- [ ] Perform the following high-intensity but reversible form matrix, verifying snapshot after every row:

| Control | Exercise | Required final state |
| --- | --- | --- |
| Video | upload; open replace/reselect UI; cancel it without changing file | authorized MP4 still uploaded |
| Cover | open cover modal; cancel; upload custom cover; cancel once; upload again; confirm; reopen change UI and cancel | custom 1280×720 cover accepted |
| Tags | observe auto tags; add all five targets; remove one target through its visible remove control; re-add it; attempt one duplicate | all five targets present exactly once; auto tags may remain |
| Partition | open selector and cancel; select one reversible wrong option if available; then set `知识` | readback exactly `知识` or the page's exact selected leaf under `知识`, documented in evidence |
| Description | set description; clear; set final description | exact final normalized description |
| Declaration | open and cancel; select final declaration | `内容无需标注` |
| Schedule | enable; disable; enable; set a reversible wrong future slot; restore final date/time | final actual scheduled value exact |
| Preflight | call `submission_snapshot()` twice two seconds apart | both snapshots identical for all required fields |

  Do not click unrelated navigation, monetization, collection, promotion, copyright-transfer, or immediately-publish controls.
- [ ] Before final submit, assert all hard gates in one script:
  - identity MID/name exact;
  - exact title has zero archive matches;
  - title exact and 1–80 characters;
  - cover ready and custom cover true;
  - five target tags present;
  - partition under `知识`;
  - description exact;
  - declaration exact;
  - scheduled true and date/time exact;
  - submit button text exactly `立即投稿`.
- [ ] Call `submit_once(...)` exactly once. Never call it from a retry loop.
- [ ] If result is `verified`, write `/tmp/bh-bilibili-acceptance.json` containing account MID/name, title, actual schedule, `status`, AID, BVID, manager href/text excerpt, and submit-click count `1`.
- [ ] If result is `accepted_but_schedule_unverified`, preserve AID/BVID and poll only `manager_evidence(title, actual_schedule)` every 10 seconds for up to another 10 minutes. Do not call `prepare_upload`, `set_*`, `_click_visible`, or `submit_once` again. Update the same evidence file when verified.
- [ ] Post-submit high-intensity read-only/reversible inspection on the unique manager card:
  - open `查询进度` if present, record visible status, return;
  - open `数据` if present and available, record whether data page loads, return;
  - open `编辑` only to verify the same BVID/title loads, then navigate back without saving;
  - for any delete/retract/immediate-publish control, opening a confirmation dialog is allowed only if the control is clearly identified; always click cancel/close, verify the record remains, and never confirm;
  - unknown or unlabeled controls are inventoried but not clicked.
- [ ] Final external acceptance:
  - exactly one exact-title archive record;
  - AID and BVID non-empty;
  - manager shows `定时发布` plus actual exact Chinese date/time;
  - no second submit click;
  - no duplicate record;
  - Agent Pool state empty after process exit;
  - managed Chrome remains running.

### Task 9: Final review, commits, merge to main, push, and Goal completion

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`
**Risk level:** authorized Git external write. No force operations.

- [ ] Rerun every automated Test Matrix command fresh after real acceptance.
- [ ] Read `/tmp/bh-browser-routing-acceptance.json` and `/tmp/bh-bilibili-acceptance.json`; require all final invariants.
- [ ] Inspect raw repository state:
  - `RTK_DISABLED=1 git status --short --branch`
  - `RTK_DISABLED=1 git diff --check main...HEAD`
  - `RTK_DISABLED=1 git log --oneline --decorate main..HEAD`
- [ ] If any listed core file remains uncommitted, stage it explicitly and make one final scoped commit. Never use `git add .` or `git add -A`.
- [ ] Confirm branch commits contain only:
  - `src/browser_harness/daemon.py`
  - `src/browser_harness/agent_pool.py`
  - `src/browser_harness/run.py`
  - `tests/unit/test_daemon.py`
  - `tests/unit/test_agent_pool.py`
  - `tests/unit/test_run.py`
  - `tests/unit/test_bilibili_publishing.py`
  - `agent-workspace/domain-skills/bilibili/publishing.py`
  - `agent-workspace/domain-skills/bilibili/publishing.md`
  - `docs/plans/2026-08-25-browser-harness-bilibili-publishing.md`
- [ ] Fetch the latest remote safely:
  - Command: `git fetch origin main`
  - Auto-review: if requested, submit one exact request stating the user explicitly authorized updating remote main for this Browser Harness batch.
- [ ] Switch local branch:
  - Command: `git switch main`
  - Preserve untracked `.understand-anything/` and recordings; never clean them.
- [ ] Fast-forward local main to remote before merging:
  - Command: `git merge --ff-only origin/main`
  - If this fails because local main has unique commits, inspect `git log --left-right --oneline main...origin/main`; merge non-destructively. Never reset.
- [ ] Merge the completed branch:
  - First try: `git merge --ff-only codex/bilibili-browser-harness-publishing`
  - If remote main advanced and fast-forward is impossible, use `git merge --no-edit codex/bilibili-browser-harness-publishing`, resolve only genuine overlapping lines, then rerun full tests.
- [ ] On local `main`, rerun:
  - `rtk uv run --with pytest pytest -q "tests/unit"`
  - `rtk uv run python "scripts/verify_domain_skills.py"`
  - `RTK_DISABLED=1 git diff --check origin/main...main`
- [ ] Push exactly:
  - Command: `git push origin main`
  - Never use `--force`, `--force-with-lease`, tag push, or branch deletion.
- [ ] Verify local and remote SHA equality:
  - `git rev-parse main`
  - `git rev-parse origin/main`
  - `git ls-remote origin refs/heads/main`
  - Pass: all three SHA values identical; current branch from `git branch --show-current` is `main`.
- [ ] Final status may still show the preserved unrelated untracked `.understand-anything/` and `agent-workspace/recordings/`; no tracked change may remain.
- [ ] Update all Progress Ledger rows with exact commits, test counts, MIDs, timing evidence, AID/BVID, schedule, and final SHA.
- [ ] Call `update_goal(status="complete")` only now. Report final token usage returned by the Goal tool if a budgeted Goal existed; otherwise report commits, tests, real publication evidence, final SHA, and preserved untracked paths.

## Test Matrix

| Layer | Requirement/risk | Exact command/procedure | Pass criteria |
| --- | --- | --- | --- |
| Baseline | checkout starts healthy | `uv run --with pytest pytest -q tests/unit` | 217+ passed |
| Security unit | #639 redaction | raw daemon pytest `-vv` | credentials/path/query absent from label |
| Routing unit | #25 mapping and fail-closed behavior | agent_pool + run tests | exact browser name, no 9223 fallback |
| Domain unit | #26–#30 | `test_bilibili_publishing.py -vv` | every field and one-click recovery case passes |
| Static | Python syntax | `python3 -m py_compile` listed files | exit zero |
| Domain registry | `.py + .md` discovery | `scripts/verify_domain_skills.py` | PASS |
| Full regression | all unit behavior | full `tests/unit` | count >217, zero failures |
| Fleet live | identities | direct explicit 9225/9226 scripts | correct distinct MID/name |
| Concurrency live | leasing | timed two-process tests | same browser non-overlap; different browsers overlap |
| Bilibili preflight | form behavior | reversible matrix | final snapshot exact and stable twice |
| Bilibili external | real publish | one `submit_once` | one unique AID/BVID, exact schedule, click count 1 |
| Post-submit | recovery/UI | manager polling and safe dialogs | record retained; no destructive confirmation |
| Git delivery | main synchronization | fetch/merge/push/SHA checks | local main == origin/main == ls-remote |

## Failure Recovery Rules

- Unit failure: inspect the first failure raw, patch only its root cause, rerun the focused file, then full suite. Two failed corrections maximum before returning to source/DOM evidence.
- Selector failure before submission: keep the same write lease, print only a compact inventory of visible relevant inputs/buttons/roles, update the selector in `publishing.py`, add a regression fixture, rerun focused tests, then continue. Do not click submit while any snapshot gate is false.
- Upload interruption before acceptance: exact-title archive query first. If zero, the current draft may be safely reloaded once; if one, switch to reconciliation and never re-upload.
- Connection loss after submit click: never click again. Query `archive_matches(title)` until the deadline, preserve any AID/BVID, then poll manager evidence.
- Agent Pool cleanup error: do not reap blindly. Inspect pool status and task-owned baseline evidence. Never stop Chrome or close baseline tabs.
- Bilibili login/identity mismatch: audit 9226 once and reopen a task-owned tab once. Never publish to a different MID. Continue code/Git verification; do not request credentials or MFA from the absent user.
- Auto-review denial: do not repeat the same request or route around policy. Use the already defined workspace or `/tmp` path when equivalent. For the explicitly authorized final `git push origin main`, send only one exact scoped request with the authorization quoted above; never switch to force push or credential extraction.
- Git merge conflict: preserve both sides, inspect the complete conflicting hunk, resolve only listed files, rerun full tests. Never reset, checkout-discard, or clean.
- Resume after interruption: `get_goal` → reread plan/skills/ledger → `git status` → inspect `/tmp` evidence → exact-title archive query → continue first unchecked safe step.

## Final Acceptance Checklist

- [ ] #639 behavior is present; #640 is absent.
- [ ] Issue #25 exact ports are correct and leased where registered.
- [ ] `publishing.py` and `publishing.md` are both committed.
- [ ] #26–#30 each have focused automated coverage.
- [ ] Full unit suite and Domain Skill verifier pass on local `main`.
- [ ] One and only one authorized real Bilibili record exists with AID/BVID and exact scheduled evidence.
- [ ] No delete/retract/immediate-publish action was confirmed.
- [ ] No credential, cookie, token, CDP provider path, generated cover, recording, or unrelated artifact is committed.
- [ ] Current local branch is `main`.
- [ ] Local `main`, `origin/main`, and `git ls-remote` SHA are identical.
- [ ] Goal is marked complete only after every checkbox above is true.
