# ChatGPT domain skill — basic conversation lifecycle

Target: `chatgpt.com` (logged-in Agent Chrome, Chinese UI). Verified 2026-08-03
on ChatGPT Pro account (model picker shows `5.6 Sol 中` style).

Scope: the full "create a conversation" lifecycle — open site, new chat,
switch chat, delete chat, select model, set reasoning effort, send message,
scroll conversation, close tab. **Settings/personalization/workspace
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
| `new_chat()` | Click sidebar 新聊天; verify home/composer |
| `switch_chat(fragment)` | Click sidebar item whose visible title contains fragment; verify `/c/` URL |
| `delete_chat(fragment, confirm=True)` | Hover item → options (history-item-N-options) → 删除 → confirm dialog (`delete-conversation-confirm-button`). **Destructive — requires confirm=True** |
| `select_model(name)` | Open picker → 模型 submenu → exact radio (`GPT-5.6 Sol` / `Terra` / `Luna`); verifies composer text |
| `set_reasoning_effort(level)` | Open picker → 推理强度 submenu → 轻度/中/高/极高/最高/超高; verifies composer text |
| `send_message(text)` | Focus composer → type → click 发送提示 button (Return alone did NOT send in verified UI) |
| `scroll_conversation(direction, amount)` | Wheel on the main `overflowY:auto` container; returns scrollTop |
| `conversation_text(limit)` | Read last user/assistant turns from `[data-message-author-role]` nodes |
| `close_extra_tab(fragment=None)` | Close most recently opened content tab; option to protect tabs by URL fragment |
| `export_share_link(fragment=None)` | Export conversation as public link. Header `share-chat-button` copies conversation-level `/share/` link to clipboard directly (toast, no dialog). Fallback: message-level share → `/s/p_...` single-message link. **Link is public on the internet** |
| `read_shared_conversation(url)` | Open share link in new tab, return visible conversation text, close tab |
| `rename_chat(fragment, new_title)` | Rename conversation: options menu → 重命名 → type → save (blur+Enter) |
| `toggle_user_message_expand(i=0)` | Expand/collapse long user prompt (`collapsible-user-message-toggle`) |
| `expand_all_user_messages()` | Expand every collapsed long prompt; returns count |
| `send_and_wait(text, timeout=180)` | Send message and poll until reply finishes; returns last assistant text |
| `switch_header_tab('聊天'\|'工作')` | Toggle the top header 聊天/工作 (chat/workspace) radio tabs. Named to avoid shadowing the harness's built-in `switch_tab` (browser tab switcher) |

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
- Composer model picker: a `button` whose span text is like `5.6 Sol` + effort
  (`中`). Click at `span.x + span.width + 20` (clicking the span text alone may
  land between the two segments — verified pitfall).
- Picker panel: simple view = capability slider (5 levels); advanced view items
  are `[role="menuitem"]` with text starting 模型 / 推理强度 / 速度. Model list
  entries are `[role="menuitemradio"]`; effort list likewise (轻度/中/高/极高/最高/超高).
- Send button: `aria-label="发送提示"` (do not rely on Return).
- Main scroll container: the largest `div` with `overflowY:auto` and
  `scrollHeight > clientHeight + 50`. Note: the side "输出内容" pane is
  `overflowY:clip` (custom scroll) — not scrollable via wheel.
- Title normalization: ChatGPT may auto-rename a new chat (e.g. the sent
  message becomes the title, possibly truncated/rewritten). Match sidebar
  items by substring, not equality.
- New chats only appear in the sidebar after the first message is sent.

## Safety rules

- `delete_chat` is destructive: never call it without an explicit
  confirm=True from the caller, and prefer testing against throwaway chats.
- `select_model` / `set_reasoning_effort` change the composer state: restore
  the previous model/effort after a test (verified pattern: switch then switch
  back and re-check composer text).
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
- Rename save: pressing Return did NOT commit the rename input; blur + a
  synthetic Enter keydown/keyup event does.
- Sidebar item options button lives inside `a[href*="/c/"]`'s `li`; match by
  `history-item-N-options` testid. Never fall back to the FIRST options button
  globally — it may belong to a different conversation.
- Delete verification needs a retry: right after deletion the sidebar may
  still render the fading item; re-check after ~2.5s.
