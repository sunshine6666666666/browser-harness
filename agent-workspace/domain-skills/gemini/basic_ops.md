# Gemini domain skill — basic conversation lifecycle

Target: `gemini.google.com` (logged-in managed Agent Chrome, Chinese UI). The
existing Deep Research flow was verified 2026-08-05. The core ordinary
conversation/share flow passed live E2E on 2026-08-26 before the latest local
hardening. The latest top-first paging, model-selector fallback, and exact
current-process run-ID binding have local regression evidence only; fresh live
validation is blocked by a Google CAPTCHA.
The current UI exposes hidden file inputs only after the upload-and-tools menu
has settled; setting the synthetic `.txt` fixture produced the live
“文件已上传” announcement, but no visible filename or removable preview.
Attachment attach/remove therefore remains unverified. Temporary-chat mode also
had no confirmable state, so both matrix items remain uncovered.

Scope: ordinary chat lifecycle — open a task-owned tab, create a chat, send
once with definite/unknown evidence, page and read a full transcript, expand
long user messages, switch by exact URL/ID, and create/read an ordinary public
share link. The previously verified Deep Research lifecycle remains supported.

Live safety boundary: use only a synthetic conversation for share tests. Never
read or switch to a private chat by title, and never retry a send whose result
is `unknown`.

## Invocation

First discover the website skill through the current checkout and managed
browser entry. Read every Markdown path returned by `page_info()`:

```bash
./browser-harness agent-pool run \
  --site gemini.google.com --account default --mode read <<'PY'
new_tab("https://gemini.google.com/app")
wait_for_load()
print(page_info())
PY
```

Then run mutations under a write lease. Let Agent Pool resolve the managed
default browser:

```bash
./browser-harness agent-pool run \
  --site gemini.google.com --account default --mode write <<'PY'
exec(open("agent-workspace/domain-skills/gemini/basic_ops.py").read())
tab = ensure_gemini_tab()
protect_tab(tab["target_id"], owner="gemini-task", purpose="synthetic chat")
new_chat()
result = send_message("synthetic test")
if result["status"] == "definitely_sent":
    wait_for_reply()
PY
```

`basic_ops.py` is a library when loaded with `exec(...)`; it does not
auto-open a tab. Call the desired helper explicitly.

Agent Pool closes every page target created during a lease when that lease
ends. `protect_tab()` prevents helper-level closes but does not extend the
lease lifetime. Keep a multi-step synthetic E2E in one write-lease script,
with explicit waits between actions; do not expect a target ID to survive into
the next `agent-pool run` call.

Smoke runner (pipe-delimited actions):

```bash
./browser-harness agent-pool run \
  --site gemini.google.com --account default --mode write <<'PY'
exec(open("agent-workspace/domain-skills/gemini/basic_ops.py").read())
run('new_chat|send:测试|wait|conversation_text|select_model:Pro|enable_dr|dr_status')
PY
```

## Functions

| Function | Behavior |
|---|---|
| `open_gemini(url)` | New tab to gemini.google.com/app, wait for load |
| `ensure_gemini_tab(url)` | Reuse only the current task tab when it is Gemini; otherwise open one new tab |
| `new_chat()` | Click sidebar 发起新对话; require an empty Quill composer |
| `current_model()` | Read composer pill text (`Flash` / `Pro`) |
| `open_model_picker()` | Open the model menu (JS pointer sequence) |
| `model_menu_items()` | List visible `[role="menuitem"]` rows |
| `select_model(target)` | Select model by label and verify pill; `Flash` excludes `Flash-Lite` |
| `open_tools_menu()` | Wait for and open the 上传和工具 (upload-and-tools) menu |
| `open_more_tools()` | In tools menu click 更多工具 to reveal Deep Research / Canvas |
| `toggle_deep_research(enable)` | Enable/disable Deep Research; **enabling shows a confirm dialog** (`发起新对话？...`) which must be clicked |
| `deep_research_ready()` | Check composer shows Deep Research chip + Pro + 来源 button |
| `send_message(text, evidence_timeout)` | Type once and click 发送 once; return only `definitely_sent` or `unknown` |
| `wait_for_reply(timeout)` | Wait until a `Gemini 说` reply appears and stops streaming |
| `conversation_text(limit)` | Backward-compatible text view of current structured turns |
| `conversation_turns(limit_per_turn)` | Return ordered `{role,text,id}` turns with action controls removed |
| `scroll_conversation(direction, amount)` | Wheel the main conversation scroll container |
| `page_conversation(direction, steps, wait_s)` | Focus the conversation scroller and send PageUp/PageDown |
| `expand_all_user_messages()` | Click only visible 展开/Show more controls; return count |
| `full_conversation(max_pages, wait_s)` | Read top-to-bottom with two stable boundaries and overlap/ID dedupe |
| `switch_chat(url_or_id)` | Navigate only to an exact Gemini `/app/<conversation_id>` URL or ID |
| `rename_conversation(title)` | Under a write lease, rename only the current canonical `/app/<conversation_id>` via its exact sidebar row; returns `definitely_renamed`, `unknown`, or `failed` |
| `conversation_snapshot(max_pages, wait_s)` | Read a virtualized conversation in order and return `coverage=full|partial|missing` |
| `request_conversation_summary(prompt, wait_timeout)` | Detect an existing exact user request in the full snapshot, otherwise send one in-place summary request and never retry an unknown send |
| `conversation_summary(prompt, wait_timeout)` | Compatibility alias for `request_conversation_summary` |
| `export_share_link()` | Require an exact run ID registered by this process's `send_message()` and present in the current turn, then create/copy the public share URL; idempotent per process |
| `read_shared_conversation(url, close_after)` | Validate an official share URL, read structured turns, close only its new tab |
| `start_deep_research()` | On the plan card, `scrollIntoView` then click 开始研究 |
| `deep_research_status()` | Classify: idle / plan_ready / running / completed |

`full_conversation()` is complete only after the top and bottom each report two
consecutive `moved=False` pages with no new turn. Stable message IDs are used
first; when Gemini exposes no ID, only adjacent page edge overlap is merged,
so equal text at different positions remains valid.

## UI facts / selectors (Chinese UI, ordinary chat verified 2026-08-26)

- Composer editor: `div.ql-editor` (Quill), `[role="textbox"]`, placeholder
  `为 Gemini 输入提示`; when Deep Research is armed the placeholder becomes
  `你想研究什么？`.
- For send, focus the visible editor and use page-native
  `document.execCommand('insertText', ...)`; `type_text()` can change only the
  visible DOM without committing Quill's internal state. A fresh `/app` task
  tab must be activated before this sequence; `send_message()` activates its
  current task tab once.
- Send button: `button[aria-label="发送"]` (do not rely on Return).
- Sidebar new chat: element whose normalized text is exactly `发起新对话`.
- Model selector: `button[aria-label*="打开模式选择器"]`; when that aria label is
temporarily absent during page settle, the helper falls back to a visible model
button whose text starts with `Flash` or `Pro` and excludes `Flash-Lite`. The
pill text is the current model. Menu rows are `[role="menuitem"]`:
`3.5 Flash-Lite 极速回答`, `3.7 Flash 全方位帮助`,
`3.1 Pro 高级推理`, `扩展思考 擅长解决复杂问题`.
- Tools menu entry: `button[aria-label="上传和工具"]`. The current first
  item is `添加照片和文件` (older UI used `上传文件`), followed by `从云端硬盘添加`,
  `更多上传选项`, `制作图片`, `制作视频`, `制作音乐`, then `更多工具` at
  the bottom. The menu may render after the composer; `open_tools_menu()` polls
  for the visible button before clicking. Clicking `更多工具` reveals a second column:
  `Canvas`, `Deep Research`, `学习辅导` — each a
  `[role="menuitemcheckbox"]` with exact text.
- Attachment probe: after the menu opens, hidden
  `input.hidden-file-input` nodes accept `.txt`; CDP `DOM.setFileInputFiles`
  followed by `input`/`change` produced `文件已上传` but the current build did
  not render a visible preview or a safe remove control. Do not send a file or
  claim attach/remove success unless both visible states are observed.
- Deep Research confirm dialog: `发起新对话？选择此工具将发起新对话。` with
  buttons `不再询问` and `发起新对话`. Click the last `发起新对话` button.
- Messages: current ordinary chat uses top-level `.user-query-container`
  (user) and `model-response` (assistant) nodes in alternating DOM order;
  the public share page uses `.response-container` for assistant nodes;
  hidden `screen-reader-user-query-label` nodes are not message bodies.
- Ordinary share: open the top-toolbar `打开对话操作菜单。`, then choose the
  `[role="menuitem"]` item `分享对话内容`; only then look for `复制链接`.
  Current official link forms are `https://g.co/gemini/share/<id>` and
  `https://share.gemini.google/<id>`; the final page may be
  `https://gemini.google.com/share/<id>?skid=<UUID>` and only that single
  `skid` query is allowed; reject all other query strings and fragments.
  The copy control requires one real CDP coordinate click after tab activation;
  a synthetic JS click may leave the clipboard empty.
- Current-conversation rename: `rename_conversation(title)` derives the ID only
  from the current canonical `/app/<id>` URL, opens the explicit `打开边栏` /
  `Open sidebar` control when needed, then finds exactly one visible sidebar
  anchor with that exact href, and then uses that row's observed options button
  and exact `重命名`/`Rename` menu action. It never searches by title fragment.
  The helper sets the observed editor once, submits it with one real `Enter`, and
  returns `definitely_renamed` only
  after two stable exact title reads with the editor gone. If the write started
  but persistence is ambiguous, it returns `unknown`; never retry that result.
- Ordinary summary: `conversation_snapshot()` pages to both stable boundaries,
  merges virtualized pages by message ID or adjacent edge overlap, and reports
  `full`, `partial`, or `missing` rather than silently treating a visible slice
  as a complete transcript. `request_conversation_summary()` compares the exact
  normalized prompt against the full ordered user turns before sending; an
  existing match returns `already_requested`, and an `unknown` send is never
  retried.
- Deep Research plan card: after submitting, a card shows the research title,
  numbered plan steps, `修改方案`, `开始研究`, and `不使用 Deep Research，再试一次`.
  **`开始研究` may be BELOW the viewport — scrollIntoView before clicking.**
  After clicking, Gemini replies `很好。在我进行研究时，你可以随意离开这个对话。
  研究完成后，我会立即告诉你。` then `正在开始搜索…` and a `显示思考过程` panel.
- Running markers: `正在搜索`, `Researching`, `正在开始搜索`, `筛选核心动态`,
  `评估关键差距`, `核实权威细节`, `多维深度查阅与验证`, `正在生成`, `分析结果`.
- Completion: no researching markers, body length grows (reports are several
  thousand chars), body contains `执行摘要` and `来源` plus the report title.
  **RELIABLE completion signal: the top toolbar shows `目录` + `分享和导出` +
  `创建` buttons.** `分享和导出` opens a menu with `分享` (分享报告),
  `导出到 Google 文档`, `复制内容`.

## Export / copy (verified 2026-08-05)

The finished Deep Research report is exported via the top-right toolbar:

1. `分享和导出` button (top toolbar, only present when report is done).
2. Menu items: `分享` / `导出到 Google 文档` / `复制内容`.
3. **`复制内容` is the simplest reliable route** — copies the whole report to
   the system clipboard, then read it back with
   `navigator.clipboard.readText()` (grant `clipboardReadWrite` via CDP first).
4. `导出到 Google 文档` shows `正在创建文档…` progress in the page body and
   opens a Google Docs tab when finished (not verified end-to-end here).

**Pitfall:** the `分享和导出` menu items only respond to a REAL CDP mouse
click (`Input.dispatchMouseEvent` press/release) — the JS pointer sequence
does NOT trigger copy/export. Use CDP clicks for these menu items, unlike
the rest of the page where JS pointer sequences are preferred.

## End-to-end Deep Research (the agent-facing path)

`run_deep_research(prompt, model="Pro", timeout=900)` runs the WHOLE flow and
returns the actual report text:

```python
result = run_deep_research("调研：...")
print(result["status"])   # "completed"
print(result["text"])     # the full report body
print(result["url"])      # chat URL e.g. https://gemini.google.com/app/<id>
```

It performs: fresh chat → select Pro → enable Deep Research tool → send
prompt → wait for the plan card → click 开始研究 (scrollIntoView first) →
poll until the toolbar 分享和导出 button appears → extract the report body.

- `report_is_done()` — True when the top toolbar 分享和导出 / 目录 / 创建
  buttons are present (reliable completion signal).
- `wait_for_deep_research_done(timeout, poll)` — poll until done, returns
  `{"status": "completed", "text": <report>, "url": ...}` or `"stopped"`.
- `deep_research_report_text()` — extracts the report body from the page:
  from the report title to the `报告中使用的来源` marker (sources list and
  思路 thinking transcript are excluded).

Report structure (verified 2026-08-05): title (`...研报`) → intro →
table (核心新闻 / 发生时间 / 事件概述与深度影响 / 来源链接) → conclusion,
ending right before `报告中使用的来源`.

## Safety rules

- `toggle_deep_research(True)` starts a NEW conversation (Gemini confirms this).
  Restore the model/tool state after tests when needed.
- `send_message()` requires an empty composer and verifies typed text before
  clicking send; never resend on unknown state — re-read the page first.
- `export_share_link()` requires the exact current-process run ID to be registered by
  `send_message()` and present in the current turns; it reads the official URL
  from clipboard. After an unknown share state, never click create again.
- Login walls/payment UI: stop the run and record the blocker; never type credentials.

## Pitfalls (verified 2026-08-05)

- **CDP mouse events time out on this page.** `Input.dispatchMouseEvent`
  mousePressed/mouseReleased intermittently hang (~30s IPC timeout). Prefer
  JS full pointer sequence (pointerdown/mousedown/pointerup/mouseup/click)
  via `dispatchEvent`. Keep CDP only for wheel scrolling.
- **Wrong tab between calls.** Start each script with `ensure_gemini_tab()`; it
  reuses only the current attached task tab or opens a new one. It never scans
  or switches an arbitrary existing Gemini tab.
- **Lease cleanup closes new tabs.** A task-owned tab created in one Agent Pool
  lease is cleaned up when that lease ends, even if `protect_tab()` was used.
  Keep the full synthetic flow in one slow write lease instead of splitting it
  across calls.
- **Use Agent Pool for every call** and let it resolve the managed default
  browser. Do not select a CDP endpoint or port in the Domain Skill.
- **Model rows have no `aria-checked`.** Verify selection by re-reading the
  composer pill text, not by menu radio state.
- **Deep Research entry is hidden under 更多工具.** It is NOT in the first
  tools column; you must click `更多工具` first.
- **Deep Research selection confirms a new conversation.** Expect the
  `发起新对话？` dialog and click the confirm button.
- **`开始研究` is below the plan card.** It may be off-screen; call
  `scrollIntoView({block:'center'})` before clicking, then re-locate and
  dispatch the pointer sequence.
- **Do not fuzzy-match `/开始/`.** On Gemini the plan card also has
  `不使用 Deep Research，再试一次` — never click that. Target exact `开始研究`.
- **Status check pitfall:** a report may contain the word `正在` inside
  finished body text; do not classify as running solely because the finished
  body contains such words. Use the researching marker regex plus length plus
  `执行摘要`/`来源`.
- **Long background watchdogs:** do not launch a long polling loop via
  `./browser-harness` stdin in background — it dies after the first
  sleep. Use a standalone Python script that shells out to `browser-harness`
  per check, or short foreground checks.
