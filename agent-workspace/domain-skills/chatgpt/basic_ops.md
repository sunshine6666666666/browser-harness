# ChatGPT domain skill — basic conversation lifecycle

Target: `chatgpt.com` (logged-in Agent Chrome, Chinese UI). Verified 2026-08-04
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
| `new_chat()` | Click sidebar 新聊天; reject an unchanged `/c/<id>` and require a visible empty unified composer |
| `switch_chat(fragment)` | Click sidebar item whose visible title contains fragment; verify `/c/` URL |
| `delete_chat(fragment, confirm=True)` | Hover item → options (history-item-N-options) → 删除 → confirm dialog (`delete-conversation-confirm-button`). **Destructive — requires confirm=True** |
| `select_model(name)` | Open the advanced or direct model submenu, select an exact visible radio, then reopen and require `aria-checked="true"` |
| `set_reasoning_effort(level)` | Select the exact reasoning radio in either UI variant, then reopen and require `aria-checked="true"` |
| `send_message(text)` | Require an initially empty unified composer, send once, and return `definitely_sent` or non-retryable `unknown` evidence, including activation exceptions |
| `scroll_conversation(direction, amount)` | Wheel on the main `overflowY:auto` container; returns scrollTop |
| `conversation_text(limit)` | Read last user/assistant turns from `[data-message-author-role]` nodes |
| `close_extra_tab(fragment=None)` | Close most recently opened content tab; option to protect tabs by URL fragment |
| `export_share_link(fragment=None)` | Export conversation as public link. Header `share-chat-button` copies conversation-level `/share/` link to clipboard directly (toast, no dialog). Fallback: message-level share → `/s/p_...` single-message link. **Link is public on the internet** |
| `read_shared_conversation(url)` | Open share link in new tab, return visible conversation text, close tab |
| `rename_chat(url_or_id, new_title)` | Require the exact conversation URL/ID, edit only `input[aria-label="聊天标题"]`, explicitly blur the controlled input, then leave/reopen and verify that exact `/c/<id>` row persisted |
| `toggle_user_message_expand(i=0)` | Expand/collapse long user prompt (`collapsible-user-message-toggle`) |
| `expand_all_user_messages()` | Expand every collapsed long prompt; returns count |
| `send_and_wait(text, timeout=180)` | Require `definitely_sent`, then poll until reply finishes; an unknown send stops without retrying |
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
- Composer model picker: a composer-scoped `button[aria-haspopup="menu"]`. The current Radix trigger requires a full pointerdown/mousedown/pointerup/mouseup/click sequence; a bare DOM click or Escape-only cleanup may leave the menu unchanged.
- Picker panel has two live variants. The advanced variant exposes 模型 / 推理强度 / 速度 menu items. The current direct variant exposes reasoning radios at the top level and a current-model `[role="menuitem"][aria-haspopup="menu"]` that opens exact model radios. Both must be verified by reopening and reading `aria-checked`.
- Send button: `aria-label="发送提示"` (do not rely on Return).
- Main scroll container: the largest `div` with `overflowY:auto` and
  `scrollHeight > clientHeight + 50`. Note: the side "输出内容" pane is
  `overflowY:clip` (custom scroll) — not scrollable via wheel.
- ChatGPT may auto-rename a new chat. Title fragments are acceptable for read-only discovery. `rename_chat` requires an exact ChatGPT conversation URL/path/ID; `delete_chat` still accepts a title fragment but requires exactly one matching row and never falls back to another row's options button.
- New chats only appear in the sidebar after the first message is sent.

## Safety rules

- `delete_chat` is destructive: never call it without an explicit
  confirm=True from the caller; its title fragment must resolve to one row, and prefer testing against throwaway chats.
- `select_model` / `set_reasoning_effort` change the composer state: restore
  the previous model/effort after a test (verified pattern: switch then switch
  back and re-check the exact radio's `aria-checked` state).
- `send_message()` may return `status="unknown"` after a click. Never resend an unknown result; inspect the returned URL and conversation before deciding what happened.
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
