# ChatGPT domain skill — basic conversation lifecycle

> **路由标准（2026-08-06 起）**：ChatGPT 会话管理已登记为共享能力
> `chatgpt.conversation-ops`（experimental）与 `chatgpt.deep-research`（experimental），
> 详见 `~/.hermes/shared-skills/site-capability-registry/references/catalog.md` 与规范
> `CAPABILITY-REGISTRY-SPEC.md`。已固化为 OpenCLI 命令（`opencli chatgpt rename/share/delete/deep-research`），
> 命中后优先用 OpenCLI；本文件保留页面交互知识与 BrowserHarness 手动路径。

Target: `chatgpt.com` (logged-in Agent Chrome, Chinese UI). Verified 2026-08-04
on ChatGPT Pro account (model picker shows `5.6 Sol 中` style).

Scope: the full "create a conversation" lifecycle — open site, new chat,
switch chat, delete chat, select model, set reasoning effort, send message,
scroll conversation, close tab, plus Deep Research (深度研究) via the
companion `deep_research.py` module. **Settings/personalization/workspace
management are intentionally out of scope** (per Ye Lin).

## Invocation

Run inside browser-harness against Agent Chrome:

```bash
BU_NAME=agent BU_CDP_URL=http://127.0.0.1:9223 browser-harness <<'PY'
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/chatgpt/basic_ops.py").read())
new_chat()
send_message("hello")
PY
```

`basic_ops.py` is a library when loaded with `exec(...)`; it does not
auto-open a tab. Call the desired helper explicitly. This prevents a smoke
script from opening an extra ChatGPT home tab before its own setup.

Smoke runner (pipe-delimited actions):

```bash
BU_NAME=agent BU_CDP_URL=http://127.0.0.1:9223 browser-harness <<'PY'
exec(open(".../basic_ops.py").read())
run('switch_chat:English|scroll_conversation:down:800|conversation_text')
PY
```

## Functions

| Function | Behavior |
|---|---|
| `open_chatgpt(url)` | New tab to chatgpt.com, wait for load |
| `new_chat()` | Click sidebar 新聊天; require the exact fresh-home path `/` and a visible empty unified composer; any `/c/<id>` is rejected |
| `switch_chat(fragment)` | Click sidebar item whose visible title contains fragment; verify `/c/` URL |
| `delete_chat(fragment, confirm=True)` | Hover item → options (history-item-N-options) → 删除 → confirm dialog (`delete-conversation-confirm-button`). **Destructive — requires confirm=True** |
| `select_model(name)` | Open the advanced or direct model submenu, select an exact visible radio, then reopen and require `aria-checked="true"` |
| `set_reasoning_effort(level)` | Select the exact reasoning radio in either UI variant, then reopen and require `aria-checked="true"` |
- `send_message(text)` | Require an initially empty unified composer, send once, and return `definitely_sent`, `definitely_not_sent` (no click was issued), or non-retryable `unknown` evidence. The live send button accepts `发送提示词`, legacy `发送提示`, and `Send prompt`. Long collapsed prompts can be proven by the rendered prefix, an unseen `data-message-id`, an increasing `conversation-turn-N`, and an emptied composer; transient `/c/WEB:...` routes are rejected until the canonical URL appears |
| `scroll_conversation(direction, amount)` | Wheel on the main `overflowY:auto` container; returns scrollTop. Use only for ordinary viewport movement |
| `page_conversation(direction, steps)` | Focus the main conversation scroller and send real PageUp/PageDown keys so ChatGPT's virtualizer renders the next page; returns scroll/message evidence |
| `conversation_text(limit)` | Read last user/assistant turns from `[data-message-author-role]` nodes |
| `read_markdown_block_summary(index=-1)` | Return the full text of a ChatGPT writing/Markdown editor block when a summary is rendered outside ordinary message text |
| `close_extra_tab(fragment=None)` | Close most recently opened content tab; option to protect tabs by URL fragment |
| `export_share_link(fragment=None)` | Export conversation as public link. Header `share-chat-button` copies conversation-level `/share/` link to clipboard directly (toast, no dialog). Fallback: message-level share → `/s/p_...` single-message link. **Link is public on the internet** |
| `read_shared_conversation(url)` | Open share link in new tab, return visible conversation text, close tab |
| `rename_chat(url_or_id, new_title)` | Require the exact conversation URL/ID, edit only `input[aria-label="聊天标题"]`, explicitly blur the controlled input, then leave/reopen and verify that exact `/c/<id>` row persisted; if that read still shows the old title, retry the exact transaction once |
| `toggle_user_message_expand(i=0)` | Expand/collapse long user prompt (`collapsible-user-message-toggle`) |
| `expand_all_user_messages()` | Expand every collapsed long prompt; returns count |
| `send_and_wait(text, timeout=180)` | Require `definitely_sent`, then poll until reply finishes; an unknown send stops without retrying |
| `switch_header_tab('聊天'\|'工作')` | Toggle the top header 聊天/工作 (chat/workspace) radio tabs. Named to avoid shadowing the harness's built-in `switch_tab` (browser tab switcher) |

## Deep Research (深度研究) — companion `deep_research.py`

Verified 2026-08-05 with a real minimal DR run on the Chinese UI (Pro account).
Load the companion module alongside `basic_ops.py`:

```python
exec(open(".../domain-skills/chatgpt/basic_ops.py").read())
exec(open(".../domain-skills/chatgpt/deep_research.py").read())
```

| Function | Behavior |
|---|---|
| `arm_deep_research()` | Open composer `+` menu (`composer-plus-btn`, aria 添加文件等), click the 深度研究 text-leaf row (plain DIV, not `menuitemradio`), verify the composer shows the 深度研究 pill. Does NOT send anything |
| `disarm_deep_research()` | Remove the pill by clicking the composer token then Backspace; verify it is gone. Clicking the `+` row again would ADD a second token — never use that to toggle off |
| `deep_research_progress()` | Resolve `iframe_target('connector-openai-deep-research')`, read the NESTED `iframe#root` body (the outer connector body is empty). Returns `state`: `idle` (no connector yet) / `planning` / `running` / `done` / `unknown`, plus `text` |
| `export_deep_research_markdown(timeout=30)` | Inside the connector iframe click the 导出 icon (`aria-label=导出`), then 导出到 Markdown; waits for the newest non-empty `~/Downloads/deep-research-report (N).md` and returns its absolute path |
| `run_deep_research(question, poll_interval=8, timeout=900, export=True)` | Arm + type question + send + poll until `done`; optionally export. **Consumes a real Pro Deep Research quota run** |

DR UI facts:

- Menu rows under `+` are plain DIVs; the 深度研究 row is a text-leaf whose
  normalized text is exactly 深度研究 inside an ancestor whose normalized
  text is exactly `深度研究 获取详细报告`.
- After arming, the composer shows a blue 深度研究 pill as a span/token inside
  `form[data-type="unified-composer"]` (not a button). Verify via form innerText.
- Progress runs in a sandbox iframe
  `https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/...`
  (hyphenated name). Real progress/report text is inside nested
  `iframe#root`; the outer connector body is empty. Never judge completion by
  main-page text length — the main page can stay prompt-only the whole run.
- Running state: plan title + step checklist + `正在研究…` / `停止研究`.
  Completion: `研究完成情况：<time> · N 次引用 · N 个搜索` plus the report
  body and `停止研究` gone.
- Export control is inside the connector iframe, NOT the main-page top bar:
  icon `aria-label=导出` → menu 复制内容 / 导出到 Markdown / 导出到 Word /
  导出到 PDF. Markdown download lands in `~/Downloads/deep-research-report (N).md`.
- All clicks use the full pointer sequence (`pointerdown → mousedown → pointerup
  → mouseup → click`); the small composer `+` control may ignore a bare DOM
  click, and CDP mouse events time out on this SPA.

## UI facts / selectors (Chinese UI)

- Composer picker has TWO styles on the same account:
  1. model+effort (e.g. `5.6 Sol 中`) — older/new conversations;
  2. capability slider (e.g. `极高`) — some conversations show only the
     capability level. `open_model_picker` expands the panel and clicks the
     `高级` item to reach the advanced view (模型/推理强度/速度) when needed.
- Sidebar new chat: `<a>` whose text matches 新聊天.
- Sidebar items: `a[href*="/c/"]`; hover reveals two buttons — 置顶 and
  options (`aria-label` contains 对话选项, `data-testid="history-item-N-options"`).
- Options menu: 分享 / 重命名 / 移至项目 / 置顶聊天 / 归档 / 删除.
- Delete confirm: `[data-testid="delete-conversation-confirm-button"]`.
- Composer model picker: a composer-scoped `button[aria-haspopup="menu"]`. The current Radix trigger requires a full pointerdown/mousedown/pointerup/mouseup/click sequence; a bare DOM click or Escape-only cleanup may leave the menu unchanged.
- Picker panel has two live variants. The advanced variant exposes 模型 / 推理强度 / 速度 menu items. The current direct variant exposes reasoning radios at the top level and a current-model `[role="menuitem"][aria-haspopup="menu"]` that opens exact model radios. Both must be verified by reopening and reading `aria-checked`.
- Send button: current `aria-label="发送提示词"`, with legacy `发送提示` and `Send prompt` compatibility (do not rely on Return).
- Main scroll container: the largest `div` with `overflowY:auto` and
  `scrollHeight > clientHeight + 50`. Note: the side "输出内容" pane is
  `overflowY:clip` (custom scroll) — not scrollable via wheel.
- Long chats are virtualized: the DOM contains only the currently rendered page of `[data-message-author-role]` nodes. For full collection, call `page_conversation(..., steps=1)` repeatedly and collect after every call until `moved` stays false; assigning `scrollTop` alone is not proof of full coverage.
- Markdown/document summaries can render in `.writing-block-editor`, `.mt4SwW_editor`, or `[data-writing-block-fullscreen-editor]` instead of ordinary message text. Use `read_markdown_block_summary()` before concluding the summary is missing or truncated.
- ChatGPT may auto-rename a new chat. Title fragments are acceptable for read-only discovery. `rename_chat` requires an exact ChatGPT conversation URL/path/ID; `delete_chat` still accepts a title fragment but requires exactly one matching row and never falls back to another row's options button.
- New chats only appear in the sidebar after the first message is sent.

## Safety rules

- `delete_chat` is destructive: never call it without an explicit
  confirm=True from the caller; its title fragment must resolve to one row, and prefer testing against throwaway chats.
- `select_model` / `set_reasoning_effort` change the composer state: restore
  the previous model/effort after a test (verified pattern: switch then switch
  back and re-check the exact radio's `aria-checked` state).
- `send_message()` may return `status="unknown"` after a click. Never resend an unknown result; inspect the returned URL and conversation before deciding what happened. Route/context-transition exceptions during post-click evidence polling are retried until the evidence timeout, then converted to non-retryable `unknown`.
- ChatGPT can expose a transient `/c/WEB:<temporary-id>` route immediately after send. It is not an exact conversation identity and must never be passed to rename/delete helpers; wait for the canonical `/c/<id>` URL.
- Sidebar mutation helpers must never fall back to another row's options button. An absent or ambiguous exact target is a hard failure.
- Login walls/payment UI: stop and ask Ye Lin; never type credentials.

## Pitfalls (verified 2026-08-03)

- Opening the picker twice in a row can fail (closing-animation overlay
  swallows the click). `open_model_picker` retries with Escape to clear.
- `_composer_state` prefers the visible model pill inside
  `form[data-type="unified-composer"]`; only the legacy fallback uses the
  lower viewport zone. A bare `GPT-5\.|5\.\d` regex matches price text like
  `US$25.99` inside messages.
- Effort/model radios also appear in the capability slider with the same
  text (e.g. `中`, `高`, `极高`); always pick the rightmost submenu radio.
- `press_key("Return")` does not send; use the `发送提示` button.
- Header share button (`share-chat-button`) does NOT open a dialog — it copies
  the conversation-level public link to the clipboard directly (toast 公开链接
  已复制到剪贴板). Check the clipboard via `pbpaste`; do not wait for a modal.
  Same conversation re-share returns the SAME link.
- A leftover share dialog/backdrop renders a full-screen `z-50` overlay that
  swallows clicks (elementFromPoint shows a grid overlay instead of the button).
  Press Escape to clear before further clicks.
- Message-level share yields `/s/p_...` links that only contain the single
  prompt message; conversation-level `/share/` links contain the full thread.
- Long user prompts are collapsed by default; toggle button
  `collapsible-user-message-toggle` (text 展开/收起). `expand_all_user_messages`
  checks the BEFORE state (展开=will expand), never re-collapses expanded ones.
- **CDP Input.dispatchMouseEvent (mouseMoved/click) times out intermittently on
  this page (~30s ipc timeout). Prefer JS `el.click()` + synthetic
  mouseover/mouseenter for hover-dependent buttons (sidebar options, menu
  items, confirm dialogs).** Keep CDP events only for wheel scrolling.
- Rename uses the controlled native value setter plus bubbling `input`/`change`, then a real click outside the title field; synthetic Enter is not proof of persistence.
- Sidebar item options button lives inside `a[href*="/c/"]`'s `li`; match by
  `history-item-N-options` testid. Never fall back to the FIRST options button
  globally — it may belong to a different conversation.
- Delete verification needs a retry: right after deletion the sidebar may
  still render the fading item; re-check after ~2.5s.
