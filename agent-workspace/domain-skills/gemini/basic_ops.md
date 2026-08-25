# Gemini domain skill — basic conversation lifecycle

Target: `gemini.google.com` (logged-in Agent Chrome, Chinese UI). Verified 2026-08-05
on Gemini Pro account (model pill shows `Pro` / `Flash`, Quill composer,
Angular/Material menus).

Scope: the full "create a conversation" lifecycle — open site, new chat,
switch chat, select model, send message, read reply, scroll conversation,
toggle Deep Research tool, start Deep Research and detect progress/completion.

Not included: a public share-link helper for ordinary chats or a guaranteed
full transcript reader for virtualized long chats. `conversation_text()` reads
the currently rendered conversation DOM. Deep Research report copy/export is
supported separately below.

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

Then run mutations under a write lease. Omit `--browser` to use the managed
default browser (9223 fallback), or select a registered Gemini browser by name:

```bash
./browser-harness agent-pool run \
  --site gemini.google.com --account default --mode write <<'PY'
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/gemini/basic_ops.py").read())
ensure_gemini_tab()
new_chat()
send_message("hello")
wait_for_reply()
PY
```

`basic_ops.py` is a library when loaded with `exec(...)`; it does not
auto-open a tab. Call the desired helper explicitly.

Smoke runner (pipe-delimited actions):

```bash
./browser-harness agent-pool run \
  --site gemini.google.com --account default --mode write <<'PY'
exec(open(".../gemini/basic_ops.py").read())
run('new_chat|send:测试|wait|conversation_text|select_model:Pro|enable_dr|dr_status')
PY
```

## Functions

| Function | Behavior |
|---|---|
| `open_gemini(url)` | New tab to gemini.google.com/app, wait for load |
| `ensure_gemini_tab(url)` | Switch to an existing gemini tab or open one — **call first in every script** |
| `new_chat()` | Click sidebar 发起新对话; require an empty Quill composer |
| `current_model()` | Read composer pill text (`Flash` / `Pro`) |
| `open_model_picker()` | Open the model menu (JS pointer sequence) |
| `model_menu_items()` | List visible `[role="menuitem"]` rows |
| `select_model(target)` | Select model by substring (e.g. `Pro`), verify pill contains target |
| `open_tools_menu()` | Open the 上传和工具 (upload-and-tools) menu |
| `open_more_tools()` | In tools menu click 更多工具 to reveal Deep Research / Canvas |
| `toggle_deep_research(enable)` | Enable/disable Deep Research; **enabling shows a confirm dialog** (`发起新对话？...`) which must be clicked |
| `deep_research_ready()` | Check composer shows Deep Research chip + Pro + 来源 button |
| `send_message(text)` | Type into Quill composer, click 发送 (JS pointer sequence), verify composer text and send |
| `wait_for_reply(timeout)` | Wait until a `Gemini 说` reply appears and stops streaming |
| `conversation_text(limit)` | Read visible conversation text around 你说 / Gemini 说 markers |
| `scroll_conversation(direction, amount)` | Wheel the main conversation scroll container |
| `start_deep_research()` | On the plan card, `scrollIntoView` then click 开始研究 |
| `deep_research_status()` | Classify: idle / plan_ready / running / completed |

## UI facts / selectors (Chinese UI, verified 2026-08-05)

- Composer editor: `div.ql-editor` (Quill), `[role="textbox"]`, placeholder
  `为 Gemini 输入提示`; when Deep Research is armed the placeholder becomes
  `你想研究什么？`.
- Send button: `button[aria-label="发送"]` (do not rely on Return).
- Sidebar new chat: element whose normalized text is exactly `发起新对话`.
- Model selector: `button[aria-label*="打开模式选择器"]`; pill text is the
  current model. Menu rows are `[role="menuitem"]`:
  `3.5 Flash-Lite 极速回答 新`, `3.6 Flash 全方位帮助`,
  `3.1 Pro 高阶数学与代码`, `扩展思考 擅长解决复杂问题`.
- Tools menu entry: `button[aria-label="上传和工具"]`. First column:
  `上传文件`, `从云端硬盘添加`, `制作图片`, `制作视频`, `制作音乐 新`,
  then `更多工具` at the bottom. Clicking `更多工具` reveals a second column:
  `Canvas`, `Deep Research`, `学习辅导` — each a
  `[role="menuitemcheckbox"]` with exact text.
- Deep Research confirm dialog: `发起新对话？选择此工具将发起新对话。` with
  buttons `不再询问` and `发起新对话`. Click the last `发起新对话` button.
- Messages: user turns under a `你说` marker (SPAN), assistant turns under a
  `Gemini 说` marker (H2).
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
- Login walls/payment UI: stop and ask Ye Lin; never type credentials.

## Pitfalls (verified 2026-08-05)

- **CDP mouse events time out on this page.** `Input.dispatchMouseEvent`
  mousePressed/mouseReleased intermittently hang (~30s IPC timeout). Prefer
  JS full pointer sequence (pointerdown/mousedown/pointerup/mouseup/click)
  via `dispatchEvent`. Keep CDP only for wheel scrolling.
- **Wrong tab between calls.** browser-harness may attach to a different tab
  (e.g. an open ChatGPT tab) between invocations. Always call
  `ensure_gemini_tab()` / enumerate + `switch_tab()` at the start of every
  script before acting.
- **Use Agent Pool for every call.** Omit `--browser` for the managed 9223
  fallback, or select a registered Gemini browser by name. Port 9226 belongs to
  the Bilibili publishing profile and must never be treated as Gemini's default.
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
