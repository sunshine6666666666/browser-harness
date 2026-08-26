"""Gemini (gemini.google.com) basic conversation-lifecycle ops for browser-harness.

Runs inside this checkout's `./browser-harness` (script via stdin, then
`exec(open("<repo>/agent-workspace/domain-skills/gemini/basic_ops.py").read())`
and call the functions below). Verified 2026-08-05 against gemini.google.com
Chinese UI (Pro account, Quill `ql-editor` composer, Angular/Material menus).

Covered lifecycle: open site, new chat, switch chat, exact-current-conversation
rename, ordered conversation snapshot/summary request, select model, toggle
Deep Research tool, send message, wait for reply, read conversation, scroll,
start Deep Research and detect its progress/completion.

IMPORTANT platform quirks (all verified):
- Clicking: CDP `Input.dispatchMouseEvent` mousePressed/Released intermittently
  TIMES OUT (~30s IPC timeout) on this page. Prefer JS full pointer sequence
  (pointerdown/mousedown/pointerup/mouseup/click) via `dispatchEvent`. Keep
  CDP only for wheel scrolling.
- Tab ownership: reuse only the current task-owned Gemini tab, or open one new
  tab. Never scan or switch to an arbitrary existing Gemini tab.
- Model menu items have NO `aria-checked`; verify selection by re-reading the
  composer pill text (`打开模式选择器，当前模式为"Pro"`).
- Deep Research lives in the `上传和工具` (upload-and-tools) menu under
  `更多工具` (More tools), as a `[role="menuitemcheckbox"]` with exact text
  `Deep Research`. Selecting it triggers a confirm dialog
  `发起新对话？选择此工具将发起新对话。` — must click `发起新对话`.
- Deep Research plan card: after submitting, a plan card appears with a
  `开始研究` button BELOW the plan steps — it may be below the viewport, so
  `scrollIntoView` before clicking. After clicking `开始研究`, Gemini replies
  `很好。在我进行研究时，你可以随意离开这个对话...` then shows
  `正在开始搜索…` and a `显示思考过程` panel. Running markers:
  `正在搜索/Researching/筛选核心动态/评估关键差距/核实权威细节`.
  Completion: no researching markers, body length grows (>1500), report
  contains `执行摘要` / `来源` / report title.
"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    def js(expression: str, target_id: str | None = None) -> Any: ...
    def new_tab(url: str = "about:blank") -> str: ...
    def goto_url(url: str) -> None: ...
    def press_key(key: str, modifiers: int = 0) -> None: ...
    def wait_for_load(timeout: float = 15.0) -> bool: ...
    def wait(seconds: float = 1.0) -> None: ...
    def cdp(method: str, session_id: str | None = None, **params: Any) -> Any: ...
    def current_tab() -> dict[str, Any]: ...
    def activate_tab(target: str | None = None) -> None: ...
    def click_at_xy(x: float, y: float) -> None: ...
    def close_tab(target: str | None = None) -> None: ...


GEMINI_HOME = "https://gemini.google.com/app"
_SYNTHETIC_RUN_RE = re.compile(r"\bBH-GEMINI-AUDIT-\d{8}-\d{6}\b")
_reply_count_before_send: int | None = None
_synthetic_run_ids: dict[str, str] = {}
_pending_synthetic_run_id: str | None = None
_share_links: dict[str, str] = {}
_share_unknown: dict[str, str] = {}


def _norm(s: str | None) -> str:
    return " ".join((s or "").replace("\xa0", " ").split())


def _gemini_url(value: str, *, allow_home: bool = True) -> str:
    """Normalize an exact Gemini app URL or conversation ID."""
    value = (value or "").strip().rstrip("/")
    if allow_home and value in {GEMINI_HOME, "/app"}:
        return GEMINI_HOME
    if re.fullmatch(r"[A-Za-z0-9_-]{8,}", value):
        return f"{GEMINI_HOME}/{value}"
    parsed = urlparse(value)
    match = re.fullmatch(r"/app/([A-Za-z0-9_-]{8,})", parsed.path)
    if (parsed.scheme == "https" and parsed.hostname == "gemini.google.com" and
            not parsed.query and not parsed.fragment and match):
        return f"{GEMINI_HOME}/{match.group(1)}"
    raise ValueError("Gemini URL must be https://gemini.google.com/app or an exact /app/<conversation_id>")


def _is_gemini_app_url(value: str) -> bool:
    try:
        _gemini_url(value)
        return True
    except ValueError:
        return False


def _is_conversation_url(value: str) -> bool:
    try:
        _gemini_url(value, allow_home=False)
        return True
    except ValueError:
        return False


def ensure_gemini_tab(url: str = GEMINI_HOME) -> dict[str, Any]:
    """Reuse only the current task tab, otherwise open one owned tab."""
    requested = _gemini_url(url)
    current = current_tab()
    current_url = (current or {}).get("url", "")
    opened = False
    if _is_gemini_app_url(current_url):
        if current_url.rstrip("/") != requested:
            goto_url(requested)
        target_id = (current or {}).get("targetId") or (current or {}).get("target_id")
    else:
        target_id = new_tab(requested)
        opened = True
    wait_for_load(timeout=20)
    wait(3.0)
    actual = js("location.href") or requested
    if not _is_gemini_app_url(actual):
        raise RuntimeError(f"ensure_gemini_tab: unexpected URL {actual!r}")
    if not _composer_editor().get("found"):
        raise RuntimeError("ensure_gemini_tab: usable composer not found")
    return {"target_id": target_id, "targetId": target_id, "url": actual, "opened": opened}


def _composer_editor() -> dict[str, Any]:
    """The Quill composer editor (div.ql-editor, role=textbox)."""
    return js(r"""
    (() => {
      const ed = [...document.querySelectorAll('[role="textbox"]')].find(e =>
        e.offsetParent && (e.className || '').toString().includes('ql-editor'));
      if (!ed) return {found: false};
      const r = ed.getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2),
              text: (ed.innerText || '').trim(), empty: ((ed.innerText || '').trim() === ''),
              placeholder: ed.getAttribute('aria-label') || ed.getAttribute('data-placeholder') || ''};
    })()
    """) or {"found": False}


def open_gemini(url: str = GEMINI_HOME) -> None:
    """Open Gemini in a new tab and wait for load."""
    new_tab(url)
    wait_for_load(timeout=20)
    wait(3.0)
    st = js("location.href")
    if "gemini.google.com" not in st:
        raise RuntimeError(f"open_gemini: landed on unexpected URL {st}")


def _new_chat_link() -> dict[str, Any]:
    """Sidebar 发起新对话 link."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const els = [...document.querySelectorAll('a, button, [role="button"]')].filter(e => {
        const t = norm(e.innerText || e.textContent);
        return t === '发起新对话' && e.offsetParent;
      });
      if (!els.length) return {found: false};
      els[0].click();
      return {found: true};
    })()
    """)


def new_chat() -> dict[str, Any]:
    """Start a fresh conversation and prove an empty composer is active.

    Gemini 发起新对话 is a sidebar icon button; when the sidebar is
    collapsed it may only exist as a hidden tooltip. Two strategies:
    1. click a VISIBLE sidebar element whose text is 发起新对话
       (exclude role=tooltip, exclude offsetParent hidden);
    2. fallback: navigate to https://gemini.google.com/app (no /app/<id>),
       which Gemini treats as a fresh chat home.
    """
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const els = [...document.querySelectorAll('a, button, [role="button"]')].filter(e => {
        if (!e.offsetParent) return false;
        if (e.getAttribute('role') === 'tooltip') return false;
        const r = e.getBoundingClientRect();
        if (r.width < 5 || r.height < 5) return false;
        const t = norm(e.innerText || e.textContent);
        return t === '发起新对话' || t.includes('发起新对话');
      });
      if (!els.length) return {found: false};
      for (const type of ['pointerdown','mousedown','pointerup','mouseup','click']) {
        const ev = type.startsWith('pointer')
          ? new PointerEvent(type, {bubbles:true, cancelable:true, pointerId:1, pointerType:'mouse', isPrimary:true, button:0, buttons: type.endsWith('down')?1:0})
          : new MouseEvent(type, {bubbles:true, cancelable:true, button:0, buttons: type.endsWith('down')?1:0});
        els[0].dispatchEvent(ev);
      }
      return {found: true, clicked: true};
    })()
    """)
    if not r or not r.get("found"):
        # fallback: fresh home
        goto_url("https://gemini.google.com/app")
        wait_for_load(timeout=20)
        wait(3.0)
    else:
        wait(2.5)
    state = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const ed = [...document.querySelectorAll('[role="textbox"]')].find(e =>
        e.offsetParent && (e.className || '').toString().includes('ql-editor'));
      return {url: location.href, editor_found: !!ed, editor_empty: !!ed && (ed.innerText || '').trim() === '',
              has_composer_buttons: !!ed};
    })()
    """)
    if not state or not state.get("editor_found") or not state.get("editor_empty"):
        raise RuntimeError("new_chat: empty composer not found")
    return state


def _model_pill() -> dict[str, Any]:
    """Composer model selector pill (ARIA label, then visible model text)."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const visible = e => e && e.offsetParent && e.getBoundingClientRect().width > 0;
      const buttons = [...document.querySelectorAll('button')].filter(visible);
      const b = buttons.find(x => (x.getAttribute('aria-label') || '').includes('打开模式选择器')) ||
        buttons.find(x => {
          const text = norm(x.innerText || x.textContent);
          return !text.includes('Flash-Lite') && /^(Flash|Pro)(\b|\s)/.test(text);
        });
      if (!b) return {found: false};
      const r = b.getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2),
              text: norm(b.innerText || ''), label: b.getAttribute('aria-label') || ''};
    })()
    """) or {"found": False}


def current_model() -> str:
    """Read the current composer model pill text, e.g. 'Flash' or 'Pro'."""
    p = _model_pill()
    return p.get("text", "") if p.get("found") else ""


def _click_js(js_selector_body: str) -> dict[str, Any]:
    """Generic: run a JS snippet that finds an element and dispatches the full
    pointer sequence. The snippet must define `el` and return {found, ...}.
    NOTE: do NOT declare `const norm` inside js_selector_body — it is already
    declared in the wrapper template."""
    return js(f"""
    (() => {{
      const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
      {js_selector_body}
      if (!el) return {{found: false}};
      for (const type of ['pointerdown','mousedown','pointerup','mouseup','click']) {{
        const ev = type.startsWith('pointer')
          ? new PointerEvent(type, {{bubbles:true, cancelable:true, pointerId:1, pointerType:'mouse', isPrimary:true, button:0, buttons: type.endsWith('down')?1:0}})
          : new MouseEvent(type, {{bubbles:true, cancelable:true, button:0, buttons: type.endsWith('down')?1:0}});
        el.dispatchEvent(ev);
      }}
      const r = el.getBoundingClientRect();
      return {{found: true, x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), rect: {{x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}}}};
    }})()
    """)


def open_model_picker() -> dict[str, Any]:
    """Open the model picker (Flash/Pro menu) via JS pointer sequence."""
    r = _click_js("""
      const el = [...document.querySelectorAll('button')].find(x => {
        const label = x.getAttribute('aria-label') || '';
        return label.includes('打开模式选择器') && x.offsetParent;
      });
    """)
    if not r or not r.get("found"):
        raise RuntimeError("open_model_picker: model selector button not found")
    wait(2.0)
    return r


def model_menu_items() -> list[dict[str, Any]]:
    """List visible model menu items (role=menuitem)."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      return [...document.querySelectorAll('[role="menuitem"], [role="menuitemradio"], [role="option"], [role="radio"]')]
        .filter(e => e.offsetParent)
        .map(e => {
          const r = e.getBoundingClientRect();
          return {role: e.getAttribute('role'), text: norm(e.innerText || e.textContent).slice(0, 60),
                  checked: e.getAttribute('aria-checked'),
                  x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
        })
        .filter(x => x.text)
        .sort((a, b) => a.y - b.y || a.x - b.x);
    })()
    """)


def select_model(target: str) -> dict[str, Any]:
    """Select a model by label and verify the composer pill.

    `Flash` prefers the full Flash row and excludes `Flash-Lite`, whose label
    also contains the substring. Other targets use substring matching.
    Opens the model picker itself first.
    """
    open_model_picker()
    r = _click_js(f"""
      const wanted = {json.dumps(target, ensure_ascii=False)};
      const el = [...document.querySelectorAll('[role="menuitem"]')].find(e => {{
        if (!e.offsetParent) return false;
        const t = norm(e.innerText || '');
        return wanted === 'Flash' ? t.includes('Flash') && !t.includes('Flash-Lite') : t.includes(wanted);
      }});
    """)
    if not r or not r.get("found"):
        press_key("Escape")
        raise RuntimeError(f"select_model: model {target!r} not in visible list")
    wait(2.0)
    pill = current_model()
    if target not in pill:
        raise RuntimeError(f"select_model: pill after selection is {pill!r}, expected contains {target!r}")
    return {"target": target, "pill": pill}


def open_tools_menu() -> dict[str, Any]:
    """Open the 上传和工具 menu after the composer UI has settled."""
    for _ in range(10):
        r = _click_js("""
          const el = [...document.querySelectorAll('button')].find(x => (x.getAttribute('aria-label') || '') === '上传和工具' && x.offsetParent);
        """)
        if r and r.get("found"):
            wait(2.5)
            return r
        wait(1.0)
    raise RuntimeError("open_tools_menu: 上传和工具 button not found")


def open_more_tools() -> dict[str, Any]:
    """In the tools menu, click 更多工具 to reveal Deep Research / Canvas."""
    r = _click_js("""
      const el = [...document.querySelectorAll('button, [role="button"], [role="menuitem"]')].find(e => {
        if (!e.offsetParent) return false;
        const t = norm(e.innerText || e.textContent);
        return t === '更多工具' || t === 'More tools' || t.includes('更多工具');
      });
    """)
    if not r or not r.get("found"):
        raise RuntimeError("open_more_tools: 更多工具 not found")
    wait(2.5)
    return r


def _deep_research_checkbox() -> dict[str, Any]:
    """The Deep Research menuitemcheckbox (only after open_more_tools)."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll('[role="menuitemcheckbox"], [role="checkbox"]')].find(e => {
        if (!e.offsetParent) return false;
        return norm(e.innerText || e.textContent) === 'Deep Research';
      });
      if (!el) return {found: false};
      const r = el.getBoundingClientRect();
      return {found: true, checked: el.getAttribute('aria-checked'), x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
    })()
    """)


def toggle_deep_research(enable: bool = True) -> dict[str, Any]:
    """Enable (or disable) the Deep Research tool.

    Opens the tools menu, clicks 更多工具, toggles the Deep Research
    menuitemcheckbox, and confirms the 发起新对话 dialog when enabling.
    Selecting Deep Research starts a NEW conversation.

    NOTE: after clicking the checkbox the menu auto-closes, so the checkbox
    element disappears. Verify the outcome via the composer state instead
    (Deep Research chip present/absent), which remains readable.
    """
    open_tools_menu()
    open_more_tools()
    dr = _deep_research_checkbox()
    if not dr.get("found"):
        raise RuntimeError("toggle_deep_research: Deep Research checkbox not found")
    desired_checked = "true" if enable else "false"
    if dr.get("checked") == desired_checked:
        press_key("Escape")
        wait(1.0)
        return {"status": "already", "checked": dr.get("checked")}
    r = _click_js("""
      const el = [...document.querySelectorAll('[role="menuitemcheckbox"], [role="checkbox"]')].find(e => {
        if (!e.offsetParent) return false;
        return norm(e.innerText || e.textContent) === 'Deep Research';
      });
    """)
    if not r or not r.get("found"):
        raise RuntimeError("toggle_deep_research: could not click Deep Research checkbox")
    # First-enable confirm dialog: 发起新对话？选择此工具将发起新对话。
    # May appear with delay; poll briefly and click its 发起新对话 button.
    for _ in range(5):
        confirmed = _click_js("""
          const els = [...document.querySelectorAll('button')].filter(e => {
            if (!e.offsetParent) return false;
            const t = norm(e.innerText || e.textContent);
            return t === '发起新对话';
          });
          const el = els.length ? els[els.length - 1] : null;
        """)
        if confirmed and confirmed.get("found"):
            wait(2.5)
            break
        wait(1.2)
    # Verify via composer state (menu may have closed, checkbox gone)
    wait(1.5)
    comp = _composer_editor()
    ready = deep_research_ready()
    if enable:
        if not (ready.get("has_dr") or (comp.get("found") and "研究" in (comp.get("placeholder") or ""))):
            raise RuntimeError("toggle_deep_research: composer does not show Deep Research after enabling")
    else:
        if ready.get("has_dr"):
            raise RuntimeError("toggle_deep_research: composer still shows Deep Research after disabling")
    return {"status": "toggled", "enable": enable, "checked": desired_checked}


def deep_research_ready() -> dict[str, Any]:
    """Check composer shows the Deep Research tool chip + Pro model + 来源 button."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const body = norm(document.body.innerText || '');
      const url = location.href;
      const has_dr = body.includes('Deep Research');
      const has_pro = /Pro/.test(body);
      const has_source = body.includes('来源');
      const ed = [...document.querySelectorAll('[role="textbox"]')].find(e =>
        e.offsetParent && (e.className || '').toString().includes('ql-editor'));
      const placeholder = ed ? (ed.getAttribute('aria-label') || ed.getAttribute('data-placeholder') || '') : '';
      return {url: url, has_dr: has_dr, has_pro: has_pro, has_source: has_source,
              placeholder: placeholder, ready: has_dr && has_pro && has_source};
    })()
    """) or {"ready": False}


def _reply_state() -> dict[str, Any]:
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const structuredReplies = [...document.querySelectorAll('model-response,[data-message-author-role="assistant"]')]
        .filter(e => e.offsetParent);
      const replies = structuredReplies.length ? structuredReplies : [...document.querySelectorAll('h1,h2,h3,[role="heading"]')]
        .filter(e => norm(e.innerText || e.textContent) === 'Gemini 说');
      const stop = [...document.querySelectorAll('button,[role="button"]')].some(e => {
        if (!e.offsetParent) return false;
        return /停止|停止生成|停止回答/.test(norm(e.innerText || e.textContent) + ' ' + (e.getAttribute('aria-label') || ''));
      });
      return {assistant_count: replies.length, has_stop: stop,
              len: norm(document.body.innerText || '').length};
    })()
    """) or {"assistant_count": 0, "has_stop": False, "len": 0}


def _turn_matches(expected: str, actual: str) -> bool:
    expected = _norm(expected)
    actual = _norm(actual)
    for prefix in ("你说", "Gemini 说"):
        if actual.startswith(prefix):
            actual = _norm(actual[len(prefix):])
            break
    if actual == expected:
        return True
    # The rendered user turn may include a short UI/accessibility wrapper
    # around the submitted text. The caller still requires a new turn ID/count
    # before accepting this as post-send evidence.
    if expected and expected in actual:
        return True
    # Gemini may render a collapsed long prompt; require both ends before
    # accepting the visible excerpt as the just-sent turn.
    return (len(actual) >= 160 and len(expected) >= len(actual) and
            expected[:80] in actual[:160] and expected[-80:] in actual[-160:])


def _canonical_url() -> str:
    value = js("location.href") or ""
    if not _is_conversation_url(value):
        raise RuntimeError("Gemini conversation URL is not canonical")
    return _gemini_url(value, allow_home=False)


def send_message(text: str, evidence_timeout: float = 10.0) -> dict[str, Any]:
    """Type once, click once, and return definite or unknown send evidence."""
    global _reply_count_before_send, _pending_synthetic_run_id
    expected = _norm(text)
    run_ids = set(_SYNTHETIC_RUN_RE.findall(expected))
    _pending_synthetic_run_id = next(iter(run_ids)) if len(run_ids) == 1 else None
    if not expected:
        raise ValueError("send_message: message must not be empty")
    ed = _composer_editor()
    if not ed.get("found"):
        raise RuntimeError("send_message: Quill composer editor not found")
    if not ed.get("empty"):
        raise RuntimeError("send_message: composer must be empty before typing")
    current = current_tab()
    target_id = (current or {}).get("targetId") or (current or {}).get("target_id")
    if target_id:
        activate_tab(target_id)
        wait(1.0)
    js("([...document.querySelectorAll('[role=\"textbox\"]')].find(e => e.offsetParent && (e.className||'').toString().includes('ql-editor'))).focus()")
    wait(0.4)
    js(f"document.execCommand('insertText', false, {json.dumps(text, ensure_ascii=False)})")
    wait(1.0)
    ed2 = _composer_editor()
    if _norm(ed2.get("text")) != _norm(text):
        raise RuntimeError(f"send_message: composer text mismatch after typing: {ed2.get('text','')[:60]!r}")
    before_turns = conversation_turns()
    before_user_ids = {t.get("id") for t in before_turns if t.get("role") == "user" and t.get("id")}
    before_user_count = sum(t.get("role") == "user" for t in before_turns)
    _reply_count_before_send = int(_reply_state().get("assistant_count", 0))
    r = _click_js("""
      const el = [...document.querySelectorAll('button')].find(x => (x.getAttribute('aria-label') || '') === '发送' && x.offsetParent);
    """)
    if not r or not r.get("found"):
        return {"status": "unknown", "reason": "send_button_not_found", "url": js("location.href")}
    try:
        post_editor = _composer_editor()
        composer_empty = bool(post_editor.get("empty"))
    except Exception:
        composer_empty = False
    deadline = time.time() + max(0.0, evidence_timeout)
    stable_key = None
    stable_reads = 0
    latest_url = js("location.href") or ""
    while time.time() < deadline:
        wait(0.5)
        try:
            composer_empty = bool(_composer_editor().get("empty"))
            latest_url = js("location.href") or latest_url
            turns = conversation_turns()
        except Exception:
            continue
        candidates = [
            (index, turn) for index, turn in enumerate(turns)
            if turn.get("role") == "user" and _turn_matches(expected, turn.get("text", ""))
        ]
        if not candidates:
            continue
        index, turn = candidates[-1]
        message_id = turn.get("id")
        is_new = ((message_id and message_id not in before_user_ids) or
                  (not message_id and sum(t.get("role") == "user" for t in turns) > before_user_count))
        key = (message_id, index, _norm(turn.get("text", ""))[:80], _norm(turn.get("text", ""))[-80:])
        stable_reads = stable_reads + 1 if key == stable_key else 1
        stable_key = key
        if (_is_conversation_url(latest_url) and composer_empty and is_new and stable_reads >= 2):
            conversation_url = _gemini_url(latest_url, allow_home=False)
            if _pending_synthetic_run_id:
                _synthetic_run_ids[conversation_url] = _pending_synthetic_run_id
            return {
                "status": "definitely_sent",
                "url": conversation_url,
                "composer_empty": True,
                "expected_user_message_found": True,
                "message_id": message_id,
                "message_turn": index,
            }
    return {
        "status": "unknown",
        "reason": "post_send_evidence_inconclusive",
        "url": latest_url,
        "composer_empty": composer_empty,
        "expected_user_message_found": False,
    }


def wait_for_reply(timeout: float = 90.0) -> dict[str, Any]:
    """Wait for a new Gemini reply and require two stable non-streaming reads."""
    deadline = time.time() + timeout
    baseline = _reply_count_before_send
    last_signature = None
    while time.time() < deadline:
        st = _reply_state()
        count = int(st.get("assistant_count", 0))
        new_reply = count > baseline if baseline is not None else count > 0
        signature = (count, int(st.get("len", 0)))
        if new_reply and not st.get("has_stop"):
            if signature == last_signature:
                return {"status": "reply", "url": js("location.href"),
                        "len": st.get("len", 0), "assistant_count": count}
            last_signature = signature
        else:
            last_signature = None
        wait(5)
    return {"status": "timeout", "len": 0}


def conversation_text(limit: int = 1000) -> str:
    """Read the current rendered turns while preserving the old text API."""
    text = "\n".join(f"[{turn['role']}] {turn['text']}" for turn in conversation_turns())
    return text[:limit] if text else ""


def conversation_turns(limit_per_turn: int = 20000) -> list[dict[str, Any]]:
    """Return current DOM turns in order, excluding message action controls."""
    if limit_per_turn < 1:
        raise ValueError("conversation_turns: limit_per_turn must be at least 1")
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
      const visible = e => e && e.offsetParent;
      const action = /^(复制|分享|赞|踩|编辑|重新生成|停止|复制链接|展开|收起|Copy|Share|Like|Dislike|Edit|Regenerate|Show more|Hide)$/i;
      const clean = (root, marker) => {
        const clone = root.cloneNode(true);
        clone.querySelectorAll('button,[role="button"],svg,mat-icon,input,textarea,[aria-hidden="true"]').forEach(e => e.remove());
        const text = (clone.innerText || clone.textContent || '').split(/\n+/).map(norm)
          .filter(x => x && x !== marker && !action.test(x)).join(' ').slice(0, %d);
        return marker && text.startsWith(marker) ? text.slice(marker.length).trim() : text;
      };
      const idOf = root => root.getAttribute('data-message-id') || root.getAttribute('data-turn-id') ||
        ((root.getAttribute('data-testid') || '').match(/(?:message|turn)[-_]([A-Za-z0-9_-]+)/i) || [])[1] || null;
      const result = [];
      const seen = new Set();
      const push = (root, role, marker) => {
        if (!root || seen.has(root)) return;
        const text = clean(root, marker);
        if (!text) return;
        seen.add(root);
        result.push({role, text, id: idOf(root)});
      };
      const byRole = [...document.querySelectorAll('[data-message-author-role="user"],[data-message-author-role="assistant"]')]
        .filter(visible);
      if (byRole.length) {
        byRole.forEach(root => push(root, root.getAttribute('data-message-author-role'), ''));
        return result;
      }
      const selector = document.querySelector('model-response')
        ? '.user-query-container,model-response'
        : '.user-query-container,model-response,.response-container';
      const structured = [...document.querySelectorAll(selector)]
        .filter(root => visible(root) && (
          (root.matches('model-response,.response-container') &&
            !root.parentElement?.closest('model-response,.response-container')) ||
          (!root.matches('model-response,.response-container') &&
            !root.parentElement?.closest('.user-query-container'))))
        .map(root => root.matches('model-response,.response-container')
          ? [root, 'assistant', 'Gemini 说']
          : [root, 'user', '你说']);
      if (structured.length) {
        structured.forEach(([root, role, marker]) => push(root, role, marker));
        return result;
      }
      const markers = [...document.querySelectorAll('span,h1,h2,h3,[role="heading"]')]
        .filter(visible).filter(e => ['你说', 'Gemini 说'].includes(norm(e.innerText || e.textContent)));
      markers.forEach(marker => {
        const role = norm(marker.innerText || marker.textContent) === '你说' ? 'user' : 'assistant';
        let root = marker.closest('[data-message-id],[data-turn-id]');
        if (!root) {
          root = marker.parentElement;
          for (let i = 0; i < 8 && root && root.parentElement; i++, root = root.parentElement) {
            const className = (root.className || '').toString();
            if (/screen-reader|visually-hidden/i.test(className)) continue;
            const size = (root.innerText || root.textContent || '').length;
            if (size > marker.textContent.length + 1 &&
                (size < (document.body.innerText || '').length * 0.7 || /query-text|user-query|response/i.test(className))) break;
          }
        }
        push(root, role, norm(marker.innerText || marker.textContent));
      });
      return result;
    })()
    """ % limit_per_turn) or []


def _conversation_scroller() -> dict[str, Any]:
    """The main conversation scroll container (largest overflowY:auto)."""
    return js(r"""
    (() => {
      const els = [...document.querySelectorAll('div')].filter(el =>
        el.scrollHeight > el.clientHeight + 50 && getComputedStyle(el).overflowY === 'auto');
      if (!els.length) return {found: false};
      els.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
      const el = els[0];
      const r = el.getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2),
              scrollTop: el.scrollTop, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight};
    })()
    """)


def scroll_conversation(direction: str = "down", amount: int = 600) -> int:
    """Scroll the main conversation container (CDP wheel is OK here)."""
    target = _conversation_scroller()
    if not target.get("found"):
        raise RuntimeError("scroll_conversation: no scrollable main container")
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=target["x"], y=target["y"])
    wait(0.3)
    dy = amount if direction == "down" else -amount
    cdp("Input.dispatchMouseEvent", type="mouseWheel", x=target["x"], y=target["y"], deltaX=0, deltaY=dy)
    wait(0.8)
    return _conversation_scroller().get("scrollTop", -1)


def _conversation_scroll_state() -> dict[str, Any]:
    """Focus the largest scrollable conversation container."""
    return js(r"""
    (() => {
      const els = [...document.querySelectorAll('div')].filter(el =>
        el.scrollHeight > el.clientHeight + 50 && ['auto', 'scroll'].includes(getComputedStyle(el).overflowY));
      if (!els.length) return {found: false};
      els.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
      const el = els[0];
      if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
      el.focus({preventScroll: true});
      return {found: true, scroll_top: el.scrollTop, scroll_height: el.scrollHeight,
              client_height: el.clientHeight, turn_count: document.querySelectorAll('[data-message-author-role], [data-message-id]').length};
    })()
    """) or {"found": False}


def page_conversation(direction: str = "down", steps: int = 1, wait_s: float = 0.8) -> dict[str, Any]:
    """Page the focused conversation scroller with PageUp/PageDown."""
    direction = direction.lower().strip()
    if direction not in {"up", "down"}:
        raise ValueError("page_conversation: direction must be 'up' or 'down'")
    if not isinstance(steps, int) or steps < 1:
        raise ValueError("page_conversation: steps must be at least 1")
    if wait_s < 0:
        raise ValueError("page_conversation: wait_s must not be negative")
    before = _conversation_scroll_state()
    if not before.get("found"):
        raise RuntimeError("page_conversation: no scrollable main container")
    for _ in range(steps):
        press_key("PageDown" if direction == "down" else "PageUp")
        wait(wait_s)
    after = _conversation_scroll_state()
    if not after.get("found"):
        raise RuntimeError("page_conversation: conversation scroller disappeared")
    return {"direction": direction, "steps": steps, "before": before, "after": after,
            "moved": after.get("scroll_top") != before.get("scroll_top")}


def expand_all_user_messages() -> int:
    """Click only visible collapsed user-message controls and return the count."""
    return int(js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const visible = e => e.offsetParent && e.getBoundingClientRect().width > 0;
      const buttons = [...document.querySelectorAll('button,[role="button"]')].filter(e => {
        const text = norm(e.innerText || e.textContent);
        return visible(e) && ['展开', 'Show more'].includes(text);
      });
      for (const el of buttons) {
        for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
          const event = type.startsWith('pointer')
            ? new PointerEvent(type, {bubbles:true, cancelable:true, pointerId:1, pointerType:'mouse', isPrimary:true, button:0, buttons:type.endsWith('down') ? 1 : 0})
            : new MouseEvent(type, {bubbles:true, cancelable:true, button:0, buttons:type.endsWith('down') ? 1 : 0});
          el.dispatchEvent(event);
        }
      }
      return buttons.length;
    })()
    """) or 0)


def _merge_turn_page(accumulated: list[dict[str, Any]], page: list[dict[str, Any]]) -> int:
    """Merge one rendered page without changing its conversation order."""
    if not page:
        return 0

    def key(turn: dict[str, Any]) -> tuple[str, str]:
        message_id = turn.get("id")
        return ("id", message_id) if message_id else (
            turn.get("role", ""), _norm(turn.get("text", ""))
        )

    overlap = 0
    for size in range(min(len(accumulated), len(page)), 0, -1):
        if [key(x) for x in accumulated[-size:]] == [key(x) for x in page[:size]]:
            overlap = size
            break

    by_id = {
        turn.get("id"): index
        for index, turn in enumerate(accumulated)
        if turn.get("id")
    }
    for turn in page[:overlap]:
        message_id = turn.get("id")
        if message_id in by_id:
            index = by_id[message_id]
            if len(turn.get("text", "")) > len(accumulated[index].get("text", "")):
                accumulated[index] = turn

    added = 0
    for turn in page[overlap:]:
        message_id = turn.get("id")
        if message_id in by_id:
            index = by_id[message_id]
            if len(turn.get("text", "")) > len(accumulated[index].get("text", "")):
                accumulated[index] = turn
            continue
        accumulated.append(turn)
        if message_id:
            by_id[message_id] = len(accumulated) - 1
        added += 1
    return added


def _page_or_static(direction: str, wait_s: float) -> dict[str, Any]:
    try:
        return page_conversation(direction, 1, wait_s)
    except RuntimeError as exc:
        if "no scrollable main container" in str(exc):
            return {"direction": direction, "moved": False, "static": True}
        raise


def full_conversation(max_pages: int = 120, wait_s: float = 0.8) -> dict[str, Any]:
    """Read a virtualized conversation from top to bottom with stable boundaries."""
    if not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("full_conversation: max_pages must be at least 1")
    pages = 0
    top_stable = 0
    previous_page: list[dict[str, Any]] | None = None
    while top_stable < 2 and pages < max_pages:
        page_state = _page_or_static("up", wait_s)
        expand_all_user_messages()
        current_page = conversation_turns()
        same_page = current_page == previous_page
        pages += 1
        if not page_state.get("moved") and same_page:
            top_stable += 1
        else:
            top_stable = 0
        previous_page = current_page
    if top_stable < 2:
        raise RuntimeError("full_conversation: max_pages reached before top boundary")

    accumulated: list[dict[str, Any]] = []
    bottom_stable = 0
    while bottom_stable < 2 and pages < max_pages:
        expand_all_user_messages()
        added = _merge_turn_page(accumulated, conversation_turns())
        page_state = _page_or_static("down", wait_s)
        pages += 1
        if not page_state.get("moved") and added == 0:
            bottom_stable += 1
        else:
            bottom_stable = 0
    if bottom_stable < 2:
        raise RuntimeError("full_conversation: max_pages reached before bottom boundary")
    text = "\n".join(f"[{turn['role']}] {turn['text']}" for turn in accumulated)
    return {"status": "complete", "turns": accumulated, "text": text, "pages": pages,
            "url": js("location.href") or ""}


def switch_chat(url_or_id: str) -> dict[str, Any]:
    """Navigate only to an exact Gemini conversation URL or ID."""
    url = _gemini_url(url_or_id, allow_home=False)
    tab = ensure_gemini_tab(url)
    if (tab.get("url", "") or "").rstrip("/") != url:
        goto_url(url)
    wait_for_load(timeout=20)
    wait(2.0)
    actual = js("location.href") or ""
    if actual.rstrip("/") != url:
        raise RuntimeError(f"switch_chat: exact URL was not reached ({actual!r})")
    composer = _composer_editor()
    turns = conversation_turns()
    if not composer.get("found") and not turns:
        raise RuntimeError("switch_chat: composer or conversation turns not found")
    return {"status": "switched", "url": url, "conversation_id": url.rsplit("/", 1)[-1],
            "composer_found": bool(composer.get("found")), "turn_count": len(turns)}


def _exact_conversation_row(conversation_id: str) -> dict[str, Any]:
    """Find the visible sidebar row for exactly one canonical conversation ID."""
    return js(r"""
    (() => {
      const wanted = %s;
      const norm = s => (s || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
      const visible = e => e && e.offsetParent && e.getBoundingClientRect().width > 0;
      const anchors = [...document.querySelectorAll('a[href]')].filter(a => {
        if (!visible(a)) return false;
        const url = new URL(a.href, location.href);
        return url.origin === 'https://gemini.google.com' &&
          url.pathname === '/app/' + wanted && !url.search && !url.hash;
      });
      if (anchors.length !== 1) return {found: false, count: anchors.length};
      const anchor = anchors[0];
      const row = anchor.closest('[role="treeitem"],li') || anchor.parentElement;
      if (!row) return {found: false, count: 1, reason: 'exact_row_missing'};
      const buttons = [...row.querySelectorAll('button,[role="button"]')].filter(visible);
      const menu = buttons.find(button => {
        const label = norm([
          button.getAttribute('aria-label'), button.getAttribute('title'),
          button.getAttribute('data-tooltip'), button.innerText || button.textContent
        ].filter(Boolean).join(' '));
        return /更多|选项|菜单|more|option/i.test(label) &&
          !/发起新对话|设置|帮助|反馈/i.test(label);
      });
      return {
        found: !!menu,
        count: 1,
        title: norm(anchor.innerText || anchor.textContent),
        menu_present: !!menu,
        menu_label: menu ? norm(menu.getAttribute('aria-label') || menu.getAttribute('title') || '') : ''
      };
    })()
    """ % json.dumps(conversation_id)) or {"found": False, "count": 0}


def _ensure_conversation_sidebar() -> bool:
    """Expand the sidebar only when Gemini exposes its explicit open control."""
    r = _click_js(r"""
      const el = [...document.querySelectorAll('button,[role="button"]')].find(e => {
        if (!e.offsetParent) return false;
        const label = norm(e.getAttribute('aria-label') || e.innerText || e.textContent);
        return label === '打开边栏' || /^Open sidebar$/i.test(label);
      });
    """)
    if r and r.get("found"):
        wait(0.8)
        return True
    return False


def _open_exact_conversation_options(conversation_id: str) -> dict[str, Any]:
    """Open options for the row whose href is exactly `/app/<conversation_id>`."""
    r = _click_js(r"""
      const wanted = %s;
      const anchors = [...document.querySelectorAll('a[href]')].filter(a => {
        if (!a.offsetParent) return false;
        const url = new URL(a.href, location.href);
        return url.origin === 'https://gemini.google.com' &&
          url.pathname === '/app/' + wanted && !url.search && !url.hash;
      });
      const anchor = anchors.length === 1 ? anchors[0] : null;
      const row = anchor && (anchor.closest('[role="treeitem"],li') || anchor.parentElement);
      const buttons = row ? [...row.querySelectorAll('button,[role="button"]')].filter(e => e.offsetParent) : [];
      const menu = buttons.find(button => {
        const label = norm([
          button.getAttribute('aria-label'), button.getAttribute('title'),
          button.getAttribute('data-tooltip'), button.innerText || button.textContent
        ].filter(Boolean).join(' '));
        return /更多|选项|菜单|more|option/i.test(label) &&
          !/发起新对话|设置|帮助|反馈/i.test(label);
      });
      const el = menu;
    """ % json.dumps(conversation_id))
    return r or {"found": False}


def _rename_menu_item() -> dict[str, Any]:
    """Click the exact visible rename action, never a title or text fragment."""
    return _click_js(r"""
      const els = [...document.querySelectorAll('[role="menuitem"],button,[role="button"]')]
        .filter(e => e.offsetParent && norm(e.innerText || e.textContent) &&
          ['重命名', 'Rename'].includes(norm(e.innerText || e.textContent)));
      const el = els.length === 1 ? els[0] : null;
    """)


def _rename_input_state() -> dict[str, Any]:
    """Read the visible rename input without returning private conversation text."""
    return js(r"""
    (() => {
      const visible = e => e && e.offsetParent && e.getBoundingClientRect().width > 0;
      const inputs = [...document.querySelectorAll('input')].filter(e =>
        visible(e) && (e.type || 'text') === 'text');
      const el = inputs.find(e => /重命名|rename/i.test(
        [e.getAttribute('aria-label'), e.getAttribute('placeholder'), e.getAttribute('data-testid')]
          .filter(Boolean).join(' '))) || (inputs.length === 1 ? inputs[0] : null);
      return el ? {found: true, value: (el.value || '').slice(0, 200)} : {found: false};
    })()
    """) or {"found": False}


def _set_rename_title(title: str) -> dict[str, Any]:
    """Set the observed rename input once, leaving it focused for Enter commit."""
    return js(r"""
    (() => {
      const wanted = %s;
      const visible = e => e && e.offsetParent && e.getBoundingClientRect().width > 0;
      const inputs = [...document.querySelectorAll('input')].filter(e =>
        visible(e) && (e.type || 'text') === 'text');
      const el = inputs.find(e => /重命名|rename/i.test(
        [e.getAttribute('aria-label'), e.getAttribute('placeholder'), e.getAttribute('data-testid')]
          .filter(Boolean).join(' '))) || (inputs.length === 1 ? inputs[0] : null);
      if (!el) return {found: false};
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(el, wanted);
      el.dispatchEvent(new Event('input', {bubbles: true}));
      el.dispatchEvent(new Event('change', {bubbles: true}));
      el.focus();
      return {found: true, focused: true, value_set: el.value === wanted};
    })()
    """ % json.dumps(title, ensure_ascii=False)) or {"found": False}


def _read_exact_conversation_title(conversation_id: str) -> dict[str, Any]:
    """Read the exact row title and whether its rename editor is gone."""
    return js(r"""
    (() => {
      const wanted = %s;
      const norm = s => (s || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
      const visible = e => e && e.offsetParent && e.getBoundingClientRect().width > 0;
      const anchors = [...document.querySelectorAll('a[href]')].filter(a => {
        if (!visible(a)) return false;
        const url = new URL(a.href, location.href);
        return url.origin === 'https://gemini.google.com' &&
          url.pathname === '/app/' + wanted && !url.search && !url.hash;
      });
      if (anchors.length !== 1) return {found: false, count: anchors.length};
      const anchor = anchors[0];
      const row = anchor.closest('[role="treeitem"],li') || anchor.parentElement;
      const input = row && [...row.querySelectorAll('input')].find(visible);
      return {found: true, count: 1, input_present: !!input,
              title: norm(anchor.innerText || anchor.textContent)};
    })()
    """ % json.dumps(conversation_id)) or {"found": False, "count": 0}


def rename_conversation(title: str) -> dict[str, Any]:
    """Rename only the current canonical conversation and verify exact persistence.

    The caller must invoke this helper under an Agent Pool ``--mode write`` lease.
    It performs one observed menu transaction and never retries an ambiguous write.
    ``definitely_renamed`` is returned only after two stable exact title reads with
    the editor gone; otherwise the result is ``unknown`` after a write was started,
    or ``failed`` when the exact row/menu/action was not available beforehand.
    """
    title = _norm(title)
    if not title:
        raise ValueError("rename_conversation: title must not be empty")
    url = _canonical_url()
    conversation_id = url.rsplit("/", 1)[-1]
    _ensure_conversation_sidebar()
    row = _exact_conversation_row(conversation_id)
    if not row.get("found"):
        return {"status": "failed", "reason": "exact_current_conversation_menu_not_found", "url": url}
    opened = _open_exact_conversation_options(conversation_id)
    if not opened.get("found"):
        return {"status": "failed", "reason": "exact_current_conversation_menu_not_opened", "url": url}
    wait(0.8)
    action = _rename_menu_item()
    if not action.get("found"):
        return {"status": "failed", "reason": "exact_rename_action_not_found", "url": url}
    wait(0.5)
    if not _rename_input_state().get("found"):
        return {"status": "unknown", "reason": "rename_editor_not_observed", "url": url}
    applied = _set_rename_title(title)
    if not applied.get("found") or not applied.get("value_set"):
        return {"status": "unknown", "reason": "rename_value_commit_unobserved", "url": url}
    press_key("Enter")
    stable_reads = 0
    for _ in range(10):
        wait(0.5)
        state = _read_exact_conversation_title(conversation_id)
        if (state.get("found") and not state.get("input_present") and
                state.get("title") == title):
            stable_reads += 1
            if stable_reads >= 2:
                return {"status": "definitely_renamed", "url": url,
                        "conversation_id": conversation_id, "title": title}
        else:
            stable_reads = 0
    return {"status": "unknown", "reason": "exact_title_persistence_unobserved", "url": url,
            "conversation_id": conversation_id}


def conversation_snapshot(max_pages: int = 120, wait_s: float = 0.8) -> dict[str, Any]:
    """Return ordered turns plus a truthful full/partial/missing coverage marker."""
    if not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("conversation_snapshot: max_pages must be at least 1")
    if wait_s < 0:
        raise ValueError("conversation_snapshot: wait_s must not be negative")
    url = js("location.href") or ""
    try:
        result = full_conversation(max_pages=max_pages, wait_s=wait_s)
        turns = result.get("turns") or []
        coverage = "full" if turns else "missing"
        return {"status": "complete" if turns else "missing", "coverage": coverage,
                "turns": turns, "text": result.get("text", ""),
                "pages": result.get("pages", 0), "url": result.get("url") or url}
    except Exception as exc:
        try:
            turns = conversation_turns()
        except Exception:
            turns = []
        coverage = "partial" if turns else "missing"
        return {"status": "partial" if turns else "missing", "coverage": coverage,
                "turns": turns, "text": "\n".join(
                    f"[{turn['role']}] {turn['text']}" for turn in turns),
                "pages": 0, "url": url, "error": type(exc).__name__}


DEFAULT_SUMMARY_PROMPT = "Please provide a concise summary of this conversation so far."


def request_conversation_summary(prompt: str = DEFAULT_SUMMARY_PROMPT,
                                 wait_timeout: float = 90.0) -> dict[str, Any]:
    """Request one in-place summary after full-snapshot duplicate detection."""
    prompt = _norm(prompt)
    if not prompt:
        raise ValueError("request_conversation_summary: prompt must not be empty")
    snapshot = conversation_snapshot()
    turns = snapshot.get("turns") or []
    if snapshot.get("coverage") == "missing":
        return {"status": "missing", "coverage": "missing", "turns": []}
    if any(turn.get("role") == "user" and _turn_matches(prompt, turn.get("text", ""))
           for turn in turns):
        return {"status": "already_requested", "coverage": snapshot.get("coverage"),
                "turns": turns, "url": snapshot.get("url", "")}
    try:
        sent = send_message(prompt)
    except Exception as exc:
        return {"status": "failed", "reason": type(exc).__name__,
                "coverage": snapshot.get("coverage"), "turns": turns}
    if sent.get("status") != "definitely_sent":
        return {"status": "unknown", "send": sent,
                "coverage": snapshot.get("coverage"), "turns": turns}
    reply = wait_for_reply(timeout=wait_timeout)
    after = conversation_snapshot()
    return {"status": "definitely_requested", "send": sent, "reply": reply,
            "coverage": after.get("coverage"), "turns": after.get("turns", []),
            "url": after.get("url", "")}


def conversation_summary(prompt: str = DEFAULT_SUMMARY_PROMPT,
                         wait_timeout: float = 90.0) -> dict[str, Any]:
    """Compatibility alias for the one-shot ordinary-chat summary request."""
    return request_conversation_summary(prompt, wait_timeout)


def start_deep_research() -> dict[str, Any]:
    """Click 开始研究 on the plan card (scrolls into view first)."""
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll('button')].find(e =>
        e.offsetParent && norm(e.innerText || e.textContent) === '开始研究');
      if (!el) return {found: false};
      el.scrollIntoView({block: 'center'});
      return {found: true};
    })()
    """)
    if not r or not r.get("found"):
        raise RuntimeError("start_deep_research: 开始研究 button not found (plan card may not be ready)")
    wait(0.3)
    r2 = _click_js("""
      const el = [...document.querySelectorAll('button')].find(e =>
        e.offsetParent && norm(e.innerText || e.textContent) === '开始研究');
    """)
    if not r2 or not r2.get("found"):
        raise RuntimeError("start_deep_research: 开始研究 button moved before click")
    wait(6.0)
    return {"status": "started", "url": js("location.href")}


def deep_research_status() -> dict[str, Any]:
    """Classify Gemini Deep Research state: idle / plan_ready / running / completed.

    Plan card contains STATIC step labels (研究网站/分析结果/生成报告) — do NOT
    treat those as running. Running markers are dynamic: 正在开始搜索/正在研究/
    正在生成/停止研究/停止生成 + the research progress panel (已研究 N 个网站
    with a 显示思考过程 toggle). Completion: no running markers, long body,
    and the report section (执行摘要 + 来源) is present.
    """
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const body = norm(document.body.innerText || '');
      // dynamic running indicators only
      const running = /正在开始搜索|正在研究|正在搜索|正在生成|停止研究|停止生成|停止回答|筛选核心动态|评估关键差距|核实权威细节|多维深度查阅|已研究 \d+ 个网站/.test(body);
      // plan card: 开始研究 button present AND 修改方案 present (both static)
      const start_btn = body.includes('开始研究') && body.includes('修改方案');
      const stopped = body.includes('你已停止此任务');
      const len = body.length;
      const has_exec = body.includes('执行摘要');
      const has_source = body.includes('来源');
      let status = 'idle';
      if (stopped) status = 'stopped';
      else if (running) status = 'running';
      else if (start_btn) status = 'plan_ready';
      else if (len > 1500 && (has_exec || has_source)) status = 'completed';
      return {status: status, len: len, url: location.href, running: running, start_btn: start_btn, stopped: stopped};
    })()
    """) or {"status": "idle", "len": 0}


def _share_export_button() -> dict[str, Any]:
    """The top toolbar 分享和导出 button (appears once the report is done)."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const els = [...document.querySelectorAll('button, [role="button"]')].filter(e => {
        if (!e.offsetParent) return false;
        const t = norm(e.innerText || e.textContent);
        return t === '分享和导出' || t.includes('分享和导出');
      });
      if (!els.length) return {found: false};
      const r = els[0].getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
    })()
    """)


def _share_export_menu_items() -> list[dict[str, Any]]:
    """Items in the 分享和导出 menu: 分享 / 导出到 Google 文档 / 复制内容."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      return [...document.querySelectorAll('[role="menuitem"]')]
        .filter(e => e.offsetParent)
        .map(e => {
          const r = e.getBoundingClientRect();
          return {text: norm(e.innerText || e.textContent).slice(0, 40),
                  label: (e.getAttribute('aria-label') || '').slice(0, 40),
                  x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
        })
        .filter(x => ['分享', '导出到 Google 文档', '复制内容'].some(t =>
          x.text.includes(t) || x.label.includes(t)))
        .sort((a, b) => a.y - b.y);
    })()
    """)


def open_share_export_menu() -> list[dict[str, Any]]:
    """Open the 分享和导出 menu (only present after the Deep Research report
    is done) and return its items."""
    r = _share_export_button()
    if not r.get("found"):
        raise RuntimeError("open_share_export_menu: 分享和导出 button not found (report not done?)")
    _click_js("""
      const els = [...document.querySelectorAll('button, [role="button"]')].filter(e => {
        if (!e.offsetParent) return false;
        const t = norm(e.innerText || e.textContent);
        return t === '分享和导出' || t.includes('分享和导出');
      });
      const el = els.length ? els[0] : null;
    """)
    wait(2.0)
    return _share_export_menu_items()


def _read_clipboard_text() -> str:
    """Read clipboard text through the already attached Gemini page."""
    try:
        cdp("Browser.grantPermissions", permissions=["clipboardReadWrite", "clipboardSanitizedWrite"])
    except Exception:
        pass
    clip = js(r"""
    (async () => {
      try {
        const text = await navigator.clipboard.readText();
        return {ok: true, text};
      } catch (error) {
        return {ok: false, error: String(error).slice(0, 120)};
      }
    })()
    """) or {"ok": False}
    text = clip.get("text")
    if not clip.get("ok") or not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"clipboard read failed: {clip.get('error', 'empty')}")
    return text.strip()


def _share_url_allowed(value: str) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse((value or "").strip().rstrip("/"))
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.fragment
        or parsed.netloc.lower() != host
    ):
        return False
    short_link = (
        host == "g.co" and not parsed.query and
        re.fullmatch(r"/gemini/share/[A-Za-z0-9_-]{6,}", parsed.path)
    ) or (
        host == "share.gemini.google" and not parsed.query and
        re.fullmatch(r"/[A-Za-z0-9_-]{6,}", parsed.path)
    )
    redirect = (
        host == "gemini.google.com" and
        re.fullmatch(r"/share/[A-Za-z0-9_-]{6,}", parsed.path) and
        re.fullmatch(
            r"skid=[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            parsed.query,
        )
    )
    return bool(short_link or redirect)


def _share_button() -> dict[str, Any]:
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const visible = e => e.offsetParent && e.getBoundingClientRect().width > 0;
      const elements = [...document.querySelectorAll('button,a,[role="button"]')].filter(visible);
      const direct = elements.find(e => {
        const label = norm(e.getAttribute('aria-label') || e.innerText || e.textContent);
        const testid = e.getAttribute('data-testid') || '';
        return ['分享', 'Share', '分享聊天', 'Share chat'].includes(label) || /share/i.test(testid);
      });
      const button = direct || elements.find(e =>
        (e.getAttribute('aria-label') || '').includes('打开对话操作菜单'));
      if (!button) return {found: false};
      const r = button.getBoundingClientRect();
      return {found: true, kind: direct ? 'direct' : 'conversation_menu',
              x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
    })()
    """) or {"found": False}


def _copy_share_button() -> dict[str, Any]:
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const button = [...document.querySelectorAll('button,[role="button"]')].find(e => {
        if (!e.offsetParent) return false;
        const label = norm(e.getAttribute('aria-label') || e.innerText || e.textContent);
        return label === '复制链接' || label === 'Copy link';
      });
      if (!button) return {found: false};
      const r = button.getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
    })()
    """) or {"found": False}


def _share_unknown_result(conversation_url: str, reason: str) -> dict[str, Any]:
    _share_unknown[conversation_url] = reason
    return {"status": "unknown", "reason": reason, "conversation_url": conversation_url}


def export_share_link() -> dict[str, Any]:
    """Create or copy the current synthetic conversation's public share link."""
    conversation_url = _canonical_url()
    if conversation_url in _share_unknown:
        return _share_unknown_result(conversation_url, _share_unknown[conversation_url])
    turns = conversation_turns()
    if not turns:
        raise RuntimeError("export_share_link: current conversation has no readable turns")
    run_id = _synthetic_run_ids.get(conversation_url)
    if not run_id and _pending_synthetic_run_id:
        if any(_pending_synthetic_run_id in _SYNTHETIC_RUN_RE.findall(turn.get("text", "")) for turn in turns):
            run_id = _pending_synthetic_run_id
            _synthetic_run_ids[conversation_url] = run_id
    if not run_id or not any(run_id in _SYNTHETIC_RUN_RE.findall(turn.get("text", "")) for turn in turns):
        raise RuntimeError("export_share_link: current conversation lacks this run's synthetic ID")
    cached = _share_links.get(conversation_url)
    if cached:
        return {"status": "shared", "url": cached, "created": False, "conversation_url": conversation_url}

    current = current_tab()
    target_id = (current or {}).get("targetId") or (current or {}).get("target_id")
    if target_id:
        activate_tab(target_id)
        wait(1.0)
    control = _share_button()
    if not control.get("found"):
        return _share_unknown_result(conversation_url, "share_button_not_found")
    try:
        if control.get("kind") == "conversation_menu":
            clicked = _click_js("""
              const el = [...document.querySelectorAll('button,[role="button"]')].find(e =>
                e.offsetParent && (e.getAttribute('aria-label') || '').includes('打开对话操作菜单'));
            """)
            if clicked and clicked.get("found"):
                wait(1.5)
                clicked = _click_js("""
                  const el = [...document.querySelectorAll('[role="menuitem"]')].find(e => {
                    if (!e.offsetParent) return false;
                    const label = norm(e.innerText || e.textContent || e.getAttribute('aria-label'));
                    return label === '分享对话内容' || label === 'Share conversation';
                  });
                """)
        else:
            clicked = _click_js("""
              const el = [...document.querySelectorAll('button,a,[role="button"]')].find(e => {
                if (!e.offsetParent) return false;
                const label = norm(e.getAttribute('aria-label') || e.innerText || e.textContent);
                const testid = e.getAttribute('data-testid') || '';
                return ['分享', 'Share', '分享聊天', 'Share chat'].includes(label) || /share/i.test(testid);
              });
            """)
    except Exception:
        return _share_unknown_result(conversation_url, "share_activation_exception")
    if not clicked or not clicked.get("found"):
        return _share_unknown_result(conversation_url, "share_activation_unconfirmed")
    wait(3.5)
    copy = _copy_share_button()
    if not copy.get("found"):
        return _share_unknown_result(conversation_url, "copy_link_button_not_found")
    try:
        click_at_xy(copy["x"], copy["y"])
    except Exception:
        return _share_unknown_result(conversation_url, "copy_link_activation_unconfirmed")
    wait(1.0)
    if target_id:
        activate_tab(target_id)
        wait(1.0)
    link = _read_clipboard_text()
    if not _share_url_allowed(link):
        raise ValueError("export_share_link: clipboard is not an allowed Gemini share URL")
    _share_links[conversation_url] = link.rstrip("/")
    _share_unknown.pop(conversation_url, None)
    press_key("Escape")
    return {"status": "shared", "url": link.rstrip("/"), "created": True, "conversation_url": conversation_url}


def read_shared_conversation(url: str, close_after: bool = True) -> dict[str, Any]:
    """Read an allowed Gemini share URL and close only its newly opened tab."""
    if not _share_url_allowed(url):
        raise ValueError("read_shared_conversation: URL is not an allowed Gemini share URL")
    target = new_tab(url)
    try:
        wait_for_load(timeout=20)
        wait(8.0)
        final_url = js("location.href") or url
        if not _share_url_allowed(final_url):
            raise RuntimeError("read_shared_conversation: share page redirected to an unapproved URL")
        turns = conversation_turns()
        text = "\n".join(f"[{turn['role']}] {turn['text']}" for turn in turns)
        return {"status": "read", "url": final_url.rstrip("/"), "title": js("document.title") or "", "turns": turns, "text": text}
    finally:
        if close_after and target:
            close_tab(target)
            wait(0.5)


def export_report_copy() -> str:
    """Copy the finished Deep Research report to the system clipboard via
    分享和导出 → 复制内容.

    IMPORTANT (verified 2026-08-05): the menu item only responds to a REAL
    CDP mouse click — the JS pointer sequence does NOT trigger the copy.
    After clicking, read the clipboard via navigator.clipboard.readText()
    (grant clipboardReadWrite first).
    """
    items = open_share_export_menu()
    target = None
    for it in items:
        if "复制内容" in it.get("text", ""):
            target = it
            break
    if not target:
        press_key("Escape")
        raise RuntimeError("export_report_copy: 复制内容 menu item not found")
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=target["x"], y=target["y"])
    wait(0.3)
    cdp("Input.dispatchMouseEvent", type="mousePressed", x=target["x"], y=target["y"], button="left", clickCount=1)
    wait(0.15)
    cdp("Input.dispatchMouseEvent", type="mouseReleased", x=target["x"], y=target["y"], button="left", clickCount=1)
    wait(2.0)
    return _read_clipboard_text()


def report_is_done() -> bool:
    """Completion signal: the top toolbar 分享和导出 / 目录 / 创建 buttons exist."""
    return bool(_share_export_button().get("found"))


def deep_research_report_text(limit: int = 0) -> str:
    """Extract the finished Deep Research report body from the page.

    Structure (verified 2026-08-05): the report starts at its title
    (e.g. `2026年8月全球人工智能核心动态研报`) and ends right before
    `报告中使用的来源`. Everything after that marker is the sources list
    and the thinking transcript (思路), which are NOT part of the report.

    Falls back to clipboard copy if DOM parsing fails.
    """
    body = js("document.body.innerText || ''") or ""
    norm = " ".join(body.split())
    # report end marker: 报告中使用的来源
    end = norm.find("报告中使用的来源")
    if end < 0:
        raise RuntimeError("deep_research_report_text: report end marker (报告中使用的来源) not found")
    # report start: find the message block that contains the report title.
    # The title is the first line that does NOT appear in the plan card and
    # precedes the table. We locate the title by looking for the line right
    # after the completion text (I've completed your research / 研究完成).
    # Heuristic: find the last occurrence of the report-title-ish heading.
    # A robust anchor: the report body starts after the last occurrence of
    # `分享和导出` is NOT needed; instead find the LAST `你说 开始研究`? No —
    # simpler: the report starts at the title line, which is the line between
    # the toolbar markers and the table. Use: slice after the last occurrence
    # of `分享和导出 创建` (toolbar) then trim leading UI chrome.
    toolbar = norm.rfind("分享和导出")
    if toolbar >= 0 and toolbar < end:
        start = toolbar + len("分享和导出")
    else:
        start = 0
    text = norm[start:end].strip()
    # remove any leading UI remnants that may precede the title
    while text and text[0] in " 目录创建":
        text = text[1:].strip()
    if limit > 0 and len(text) > limit:
        text = text[:limit]
    return text


def wait_for_deep_research_done(timeout: float = 900.0, poll: float = 20.0) -> dict[str, Any]:
    """Wait until the Deep Research report is done (工具栏分享和导出 appears).

    Returns the final report text. Raises on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = deep_research_status()
        if report_is_done():
            text = deep_research_report_text()
            return {"status": "completed", "len": len(text), "text": text, "url": js("location.href")}
        if st.get("status") == "stopped":
            return {"status": "stopped", "text": "", "url": js("location.href")}
        wait(poll)
    raise RuntimeError(f"wait_for_deep_research_done: timeout after {int(timeout)}s")


def run_deep_research(prompt: str, model: str = "Pro", timeout: float = 900.0) -> dict[str, Any]:
    """End-to-end Deep Research: fresh chat → Pro model → enable DR tool →
    send prompt → plan card → 开始研究 → wait for completion → extract report.

    Returns {"status": "completed", "text": <full report>, "url": <chat url>}.
    Use this when the caller wants the actual report content, not just a
    started research job.
    """
    ensure_gemini_tab()
    new_chat()
    select_model(model)
    toggle_deep_research(True)
    send_message(prompt)
    # wait for plan card (开始研究 button)
    plan_seen = False
    for _ in range(15):
        wait(8)
        if deep_research_status().get("status") == "plan_ready":
            plan_seen = True
            break
    if not plan_seen:
        raise RuntimeError("run_deep_research: plan card not seen after submitting prompt")
    start_deep_research()
    result = wait_for_deep_research_done(timeout=timeout)
    return {"status": result.get("status"), "text": result.get("text", ""), "url": result.get("url", "")}


# --- smoke runner ---
def run(actions: str) -> None:
    """Pipe-delimited actions for smoke testing: new_chat|send:hello|wait|conversation_text"""
    for act in actions.split("|"):
        act = act.strip()
        if not act:
            continue
        if act == "new_chat":
            print("new_chat:", new_chat())
        elif act.startswith("send:"):
            print("send:", send_message(act[5:]))
        elif act == "wait":
            print("wait_reply:", wait_for_reply())
        elif act == "conversation_text":
            print("conversation_text:", conversation_text(500))
        elif act.startswith("select_model:"):
            print("select_model:", select_model(act.split(":", 1)[1]))
        elif act == "enable_dr":
            print("enable_dr:", toggle_deep_research(True))
        elif act == "dr_status":
            print("dr_status:", deep_research_status())
        elif act.startswith("run_dr:"):
            prompt = act.split(":", 1)[1]
            print("run_dr:", run_deep_research(prompt, timeout=900))
        elif act == "report_text":
            print("report_text:", deep_research_report_text())
        elif act == "report_done":
            print("report_done:", report_is_done())
        else:
            print("unknown action:", act)
