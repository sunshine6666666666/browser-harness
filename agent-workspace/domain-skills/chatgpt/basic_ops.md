# ChatGPT Domain Skill — conversation lifecycle

Target: `chatgpt.com` in the managed Agent Chrome, Chinese UI (`zh-CN`).
Live audit date: 2026-09-04. Evidence: `/tmp/browser-harness-chatgpt-audit-20260904.json`.

Review follow-up: 2026-09-05. Ordinary lifecycle results below remain 2026-09-04
evidence. The new share-reader boundary algorithm has local regression coverage;
the old public URL now redirects, so it cannot provide a fresh live full-thread
read. A user-authorized minimal DR submission completed on 2026-09-05.

This skill covers the conversation lifecycle, model/reasoning controls, header
tabs, sharing, virtualized conversation reads, and the companion
`deep_research.py`. Settings, personalization, projects, workspaces, login,
credentials, and existing conversation content are out of scope.

## Invocation

Run from `/Users/yelin/orca/workspaces/browser-harness/main` through the managed
pool. The pool owns browser selection, serialization, and cleanup; do not set a
CDP URL or use a global harness binary.

```bash
./browser-harness agent-pool run \
  --browser "AgentPool-共享主浏览器-9223" \
  --site chatgpt.com --mode read --account default <<'PY'
tid = new_tab("https://chatgpt.com/")
try:
    try:
        print(page_info())
    except Exception:
        wait_for_load(timeout=20)
        print(page_info())
    exec(open("/Users/yelin/orca/workspaces/browser-harness/main/agent-workspace/domain-skills/chatgpt/basic_ops.py").read())
    print(observe_chatgpt_state())
finally:
    close_tab(tid)
PY
```

After every `new_tab()` or `goto_url()`, query `page_info()` first. If it
returns `domain_skill_files`, read every listed Markdown file before any
site-specific action. The current runtime must resolve
`agent-workspace/domain-skills/chatgpt/basic_ops.md` from this checkout.

Use `--mode write --account default` for sending, model changes, sharing,
renaming, deletion, or Deep Research. Keep one lease and one task-owned tab
sequence for a real workflow. Protect active tabs with `protect_tab`; only
unprotect and close the exact `target_id` returned by that task's `new_tab()`.

## State contract

`observe_chatgpt_state()` is the side-effect-free shared observation entry.
Every call reads the DOM afresh and returns at least:
`state`, `url`, `conversation_id`, `composer_visible`, `composer_empty`,
`generating`, `auth_required`, `paywall_or_quota`, and `dialog`.

`state` is one of:

- `ready_home`: exact `https://chatgpt.com/`, visible empty unified composer.
- `ready_conversation`: exact canonical `https://chatgpt.com/c/<id>`, visible
  empty composer, no generation signal.
- `generating`: canonical conversation with a visible generation signal,
  including the current Variant's `stop-button` / `停止回答`.
- `auth_required`: login, password, MFA, captcha, account choice, or consent.
- `paywall_or_quota`: upgrade, payment, purchase, quota, or subscription wall.
- `dialog`: a blocking visible dialog.
- `unknown`: no stronger state is proven.

Do not treat a transient `/c/WEB:<temporary-id>` route as a conversation ID.
The current Variant has a page-load race where `page_info()` can briefly fail
before `documentElement` exists; wait for load and observe again.

Stable error prefixes are: `precondition`, `not_found`, `ambiguous`,
`auth_required`, `paywall_or_quota`, `transient_rerender`, `result_unknown`,
`timeout`, `postcondition_failed`, `destructive_scope_violation`, and
`external_blocked`.

## Function contracts

| Function | Contract and verified path |
|---|---|
| `open_chatgpt(url)` | Accepts home or exact URL/path/ID, opens a task-owned tab, observes a non-unknown final state, and returns `target_id` plus state. |
| `new_chat()` | Clicks the visible new-chat link and requires exact `/` plus an empty composer. No message is sent. |
| `switch_chat(conversation)` | Accepts only an exact canonical URL, `/c/<id>` path, or ID; navigates to that exact URL and requires the same ID in the final state. Title fragments are rejected before browser access. |
| `delete_chat(conversation, confirm=False)` | Requires explicit `confirm=True`, resolves one exact sidebar pathname and its nested options button, clicks delete once, and requires that exact row to disappear. Missing/ambiguous rows never click. |
| `select_model(name)` | Opens the current model picker, selects one exact visible `menuitemradio`, reopens, and requires `aria-checked="true"`. The picker excludes `composer-plus-btn`. |
| `set_reasoning_effort(level)` | Uses the exact visible reasoning radio and reopens to verify `aria-checked="true"`. It is unavailable in the audited home Variant when no safe effort radio is exposed. |
| `send_message(text)` | Requires visible empty unified composer, accepts `send-button`, current `发送提示词`, legacy `发送提示`, or `Send prompt`, and activates at most once. Returns `definitely_sent`, pre-click `definitely_not_sent`, or non-retryable post-click `unknown`. |
| `send_and_wait(text, timeout=180)` | Snapshots assistant IDs/count before `send_message`, then requires the same conversation URL, a new assistant turn, empty composer, no visible stop control, and two stable message ID/length/tail observations. Rechecks final ID/length/tail before returning `{status, text, message_id, url}`; unknown send is never retried. |
| `conversation_text(limit)` | Reads currently rendered role nodes. For a full virtualized chat use `page_conversation` repeatedly and verify markers at both boundaries. |
| `conversation_turns(limit_per_turn=100000)` | Reads the currently rendered user/assistant turns as text with stable message identities, truncation flags, and non-text omission flags. |
| `scroll_conversation(direction, amount)` | Finds the largest visible `overflowY:auto` conversation container at action time and wheels it; returns the resulting `scrollTop`. |
| `page_conversation(direction, steps)` | Refocuses the current conversation scroller and sends bounded PageUp/PageDown keys; returns current scroll/message evidence and `moved`. |
| `full_conversation(max_pages=120)` | Reads the browser's authorized conversation responses in pages of at most 100 turns, follows `/messages?before=<start_cursor>` until `has_previous_page=false`, filters visible user/final-assistant text, and never exposes auth headers. |
| `find_conversation_by_title(title)` | Uses ChatGPT global search, waits for exact-title results to stabilize, and returns one canonical URL. Zero matches and multiple exact matches fail without opening a conversation. Newly renamed chats may not be indexed immediately. |
| `prepare_conversation_analysis(conversation, instruction)` | Validates a non-empty instruction before browser access; resolves current, exact URL/ID, or `title:` input; returns a transient complete transcript package for the calling Agent. It does not persist the transcript or invoke another model/API. |
| `read_markdown_block_summary(index)` | Reads complete visible writing-block selectors. Current audited Variant returned no block, so this capability is not verified here. |
| `toggle_user_message_expand(index)` | Re-queries the indexed user node and toggles only its `collapsible-user-message-toggle`; expanded state is read after the action. |
| `expand_all_user_messages()` | Iterates a bounded number of visible user messages, expanding only buttons that read `展开`; it never collapses an already expanded message. |
| `close_extra_tab(target_id)` | Accepts only a target in this module's task-owned set. Unknown or another owner's protected targets fail with `destructive_scope_violation`; no tab scan or URL ordering is used. |
| `export_share_link(conversation=None)` | Requires the current or supplied exact canonical conversation, clicks the conversation-level `share-chat-button` once using a fresh DOM rect, and verifies a new share URL in the clipboard or a visible copy confirmation. Results are cached: a second call returns the same URL with `created=False`; unknown results are never reactivated. |
| `read_shared_conversation(url)` | Opens its own official share target, verifies the URL, pages to a stable top boundary, then collects down to a stable bottom boundary using turn/message IDs. Missing IDs, redirects or timeout fail instead of returning a partial transcript or error-page body. Closes only its own target in `finally`. Returns `{target_id, url, text}`. |
| `rename_chat(conversation, new_title)` | Requires exact ID/URL, mutates only the exact row's native title input, blurs and verifies persistence after leaving/reopening. One bounded full transaction retry is allowed only when the exact row remains present with a different title. |
| `switch_header_tab(tab)` | Accepts only `聊天`/`chat` or `工作`/`work`, clicks the exact header radio once when needed, and verifies its checked state. |

## Parameterized conversation analysis

This is a Skill-level Agent operation, not a second model call hidden inside the
browser helper. The calling Agent supplies a non-empty analysis instruction and
uses `prepare_conversation_analysis()` once to obtain an in-memory package:

```python
package = prepare_conversation_analysis(
    "current",  # exact URL/ID, exact title, or "title:<exact title>" also work
    "逐条判断回复体现了哪些能力，并给出消息证据",
)
```

The Agent must then use every user turn as context, analyze each assistant turn
in order according to `package["instruction"]`, and return:

- `conversation_id`, `conversation_url`, `locator_path`, `acquisition_path`, `page_count`, and `completeness`;
- `user_message_count` and `assistant_message_count`;
- one analysis per assistant message with its stable message ID and evidence;
- `final_result` and the package warnings.

Do not return the preparation package as if it were the final analysis. Do not
write its `messages` to a file, database, cache, or log. Code blocks, tables, and
Markdown in the main message flow remain text. Images, audio, video, attachments,
and separate content blocks are omitted; their presence is reported in warnings.
The default operation is read-only: it must not send a prompt, start Deep
Research, create a share link, rename, or delete the target conversation.

Live verification on 2026-09-05 used one synthetic two-turn conversation. The
current-page, exact-URL, and exact-title inputs returned the same four stable
message IDs and the same transcript SHA-256; the calling Agent produced two
message-level format judgments and one combined result. No raw transcript was
saved, and the exact synthetic conversation was deleted after verification.
Global search also resolved an older indexed title to the same canonical URL
without opening or reading that conversation. A freshly renamed title returned
`conversation_unavailable` until ChatGPT indexed it, rather than falling back to
an unproven sidebar match.

### Long-conversation extraction facts

Verified on `English Review — 2026-09-01` on 2026-09-05: 242 user messages and
242 assistant text messages were returned with `completeness=complete` and no
non-text warning. The transcript was not written to disk.

- A hidden ChatGPT tab can pause virtual-list rendering; background PageUp is
  not a completeness mechanism.
- `scrollTop` jumps when older batches are prepended, and
  `conversation-turn-N` values are renumbered. Neither is a stable message ID.
- The current response shape uses `messages` plus `page_info`, not the older
  `mapping` shape.
- The initial endpoint is plural: `/backend-api/conversations/<id>`. Older
  pages use `/backend-api/conversations/<id>/messages?before=<cursor>`.
- `num_turns=100` is accepted; `num_turns=1000` returns 422. Do not probe larger
  values during normal execution.
- Calling the endpoint from page JavaScript omits the app authorization header
  and returns 401. Do not read or copy that header. `_conversation_api_page()`
  rewrites only the URL of the browser's own GET through CDP Fetch and reads its
  response body; CDP may mark that body as Base64 encoded.
- Keep `text` and `multimodal_text` from user messages and final/ordinary
  assistant messages. Exclude `thoughts`, `reasoning_recap`, hidden messages,
  non-`all` recipients, and non-final assistant channels.
- Completion requires the oldest response page to state
  `has_previous_page=false`. A scroll limit or lack of new DOM nodes is not
  sufficient evidence.

## Deep Research companion

Load `deep_research.py` after `basic_ops.py` in the same namespace.

- `arm_deep_research()` reuses the exact `data-inline-selection-pill` token with
  `data-id="plugin:connector_openai_deep_research"` and
  never adds a duplicate. Otherwise it uses `composer-plus-btn` and the exact
  `深度研究` menu leaf, then verifies the token.
- `disarm_deep_research()` removes every actual token (bounded at three) by
  clicking the token and pressing Backspace; it verifies token count reaches 0.
- `deep_research_progress()` first resolves the current page's connector DOM
  node and frame ID, then matches that exact CDP target. It never uses the first
  connector found across all browser tabs. An absent current connector is `idle`.
  A mounted connector with missing, empty, unreadable, or timed-out nested
  `iframe#root` is `unknown`, never `idle`. Planning/running/done require the
  current real completion markers.
- `run_deep_research()` requires the shared `send_message` callable before any
  UI action, arms once, calls shared `send_message` once, and never directly
  clicks the send button. Transient unknown progress is polled as the same
  submission until done or timeout; it is never resubmitted.
- `export_deep_research_markdown()` snapshots `deep-research-report*.md`
  before the click and accepts only a new or changed non-empty file. Old files
  cannot satisfy the export postcondition. Connector reads are bounded.

The 2026-09-05 live preflight confirmed that the DR token is inside the editable
composer. Empty-draft checks exclude only that exact tool token and its cursor
sentinel; ordinary text remains protected. The preflight reached the typing
boundary without typing or sending, then removed the token and verified an empty
home composer. Searching the exact prior DR run marker returned no results;
this does not establish that its unknown attempt consumed no quota.

After explicit authorization for one additional minimal run, the exact request
`BH-CHATGPT-DR-20260905-064006` was submitted once. Its connector moved through
a transient unknown state to running and done without resubmission. The report
was exported as `/Users/yelin/Downloads/deep-research-report (12).md` (11,107
bytes; SHA-256 `012eed5a06392ac23539c22980f8b54ff9bdd3d9c365419844f8b7b75b70578c`),
then the exact synthetic conversation was deleted and empty home was verified.

## Known-good states and safety

- `KGS-HOME`: task-owned target, `ready_home`, empty composer, no blocking UI.
- `KGS-CONVERSATION`: exact canonical task URL, run marker in the synthetic
  conversation, empty composer, not generating.
- `KGS-RESTORED`: original model, original effort when exposed, header `聊天`,
  no menu/dialog.
- `KGS-DR-DONE`: exact DR URL, connector done markers, non-empty report,
  stopped research signal absent. Reached on 2026-09-05.
- `KGS-CLEAN`: exact synthetic rows absent, all own targets closed, target
  9223 lease/write lock empty; other managed ports and personal Chrome untouched.

Every DOM action re-queries its target and rect immediately before acting.
Never reuse an element, backend node, or coordinate after navigation, waiting,
menu changes, or React rerender. Fixed sleeps only settle rendering; success
requires a postcondition read. All bounded loops use `time.monotonic()`.

After any non-idempotent action returns unknown, inspect only read-only state:
canonical URL, exact message IDs/turns, composer, toast/dialog, or clipboard.
If the result is still unknown, stop that mutation permanently. Never resend,
re-share, re-delete, or re-export merely because a wait timed out.

Login, MFA, captcha, account choice, authorization, payment, upgrade, and
quota purchase are hard stops. Do not type credentials or operate another
managed browser, personal browser, conversation, or profile.

## Audited capability matrix

| Capability | 2026-09-04 result | Minimum evidence |
|---|---|---|
| Open/new chat | pass | `zh-CN`, exact `/`, empty composer, current checkout domain skill discovery |
| Model selection | pass | `GPT-5.6 Sol` → `GPT-5.5` → exact `aria-checked` restoration |
| Reasoning effort | current-variant unavailable | no safe effort radio exposed by current home picker path |
| Header Chat/Work | pass | `聊天` → `工作` → `聊天`, checked state restored |
| Send/wait/read | pass | four synthetic turns, new assistant IDs, stable replies, no duplicate send |
| Long message expansion | pass | exact toggle returned `收起`; expanded messages preserved |
| Scroll/page/virtualized read | pass | scrollTop changed; PageUp/PageDown moved; line 001/080 observed |
| Markdown block | unavailable in current Variant | assistant returned unsupported; no editor selector mounted |
| Exact switch/rename | pass | canonical ID, persisted synthetic renamed title, 3 exact switches |
| Conversation share | pass | one dynamic-rect click, public URL hash stored only in Evidence, second call cached |
| Share-page read | pass | two share-only reads collected six required marker positions in order |
| Own-tab close | pass | exact share targets and an own `about:blank` target closed |
| Exact delete | pass | ordinary synthetic conversation row absent after exact delete |
| DR arm/disarm | pass | persisted duplicate token cleanup and zero-token postcondition |
| DR full run/export/delete | pass | one confirmed submission; transient unknown→running→done; fresh 11,107-byte Markdown; exact synthetic delete |
| Parameterized text analysis preparation | pass | current/URL/title inputs produced identical 2-user/2-assistant transcript identity and hash; no transcript persistence |

## Candidate paths and pruning

Scores: stable testid/exact href 5; role+aria 4; exact structural text 3;
dynamic class 1; fixed coordinate 0. Coordinates computed fresh from a stable
DOM target are acceptable; fixed coordinates are not.

| Goal | Retained path | Score/result | Pruned path and reason |
|---|---|---|---|
| Send | form send-button / exact current label, then one activation | 5; live pass | Return key; current page ignores it |
| Picker | form popup excluding plus, pointer sequence, exact radios | 5; model live pass | first global popup; it is `composer-plus-btn` |
| DR arm | plus testid + exact `深度研究` leaf | 5; live reversible pass | clicking menu row to disarm; it adds another token |
| Conversation mutation | exact canonical pathname + nested row options | 5; rename/delete live pass | title fragments and global first options |
| Share | exact header testid + fresh rect + one click + clipboard/toast | 5; live creation pass | message-level share fallback; it is not full-thread proof |
| Share read | own target + bounded top-to-bottom traversal + stable turn IDs | local regression pass; historical live path superseded | URL scan close, one bottom viewport, partial return at page limit |
| DR state | connector target + nested root via bounded read | 5; contract enforced | connector absent treated as done/idle, main-page body length |
| Download | pre/post path+mtime_ns+size comparison | 5; local regression pass | newest old file, which can be stale |

## Recovery checklist

1. Call `get_goal`, reread this file, all required Skill lessons, and the
   Evidence file.
2. Inspect raw `git status --short`, relevant target/browser state, own tabs,
   and partial exact IDs before retrying anything.
3. Treat a dead lease as stopped only after Agent Pool says runner/child dead;
   wait for automatic reclaim and never use `reap --apply`.
4. For unknown send/share/delete/DR/export, read the exact postcondition once;
   continue reading only if the result already happened, otherwise stop that
   mutation and record `result_unknown`.
5. For exact deletion, require the Evidence guard: exact ID, exact URL, the
   synthetic run marker, and the required lifecycle/share/export evidence.
6. Cleanup only task-owned targets by exact ID, then verify target 9223's
   leases/write locks are empty. Never touch 9224/9225/9226 or personal Chrome.

For this checkout launcher, run:

```bash
python3 scripts/verify_domain_skills.py --runtime-workspace "/Users/yelin/orca/workspaces/browser-harness/main/agent-workspace"
```

The launcher explicitly sets `BH_AGENT_WORKSPACE` to this checkout, verified
by live `page_info()` discovery. The user-level default symlink points to the
canonical shared skill tree in `/Users/yelin/Developer/agent-tools/browser-harness`;
it is not used by this invocation and must not be redirected into a development
checkout. Calling the verifier without the explicit argument still checks that
global link strictly; no global runtime migration is claimed here.
