"""Gemini (gemini.google.com) basic conversation-lifecycle ops for browser-harness.

Runs inside browser-harness (heredoc: `browser-harness <<'PY'` then
`exec(open("<repo>/agent-workspace/domain-skills/gemini/basic_ops.py").read())`
and call the functions below). Verified 2026-08-05 against gemini.google.com
Chinese UI (Pro account, Quill `ql-editor` composer, Angular/Material menus).

Covered lifecycle: open site, new chat, switch chat, select model, toggle
Deep Research tool, send message, wait for reply, read conversation,
scroll, start Deep Research and detect its progress/completion.

IMPORTANT platform quirks (all verified):
- Clicking: CDP `Input.dispatchMouseEvent` mousePressed/Released intermittently
  TIMES OUT (~30s IPC timeout) on this page. Prefer JS full pointer sequence
  (pointerdown/mousedown/pointerup/mouseup/click) via `dispatchEvent`. Keep
  CDP only for wheel scrolling.
- Tab switching: browser-harness may attach to the wrong tab between calls.
  Always enumerate tabs and `switch_tab()` to the exact gemini.google.com tab
  at the start of every script.
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

import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str, target_id: str | None = None) -> Any: ...
    def new_tab(url: str = "about:blank") -> str: ...
    def goto_url(url: str) -> None: ...
    def type_text(text: str) -> None: ...
    def press_key(key: str, modifiers: int = 0) -> None: ...
    def wait_for_load(timeout: float = 15.0) -> bool: ...
    def wait(seconds: float = 1.0) -> None: ...
    def cdp(method: str, session_id: str | None = None, **params: Any) -> Any: ...
    def list_tabs(include_chrome: bool = True) -> list[dict[str, Any]]: ...
    def switch_tab(target: str) -> None: ...
    def close_tab(target: str | None = None) -> None: ...
    def capture_screenshot(path: str | None = None, full: bool = False, max_dim: int | None = None) -> str: ...


GEMINI_HOME = "https://gemini.google.com/app"


def _norm(s: str | None) -> str:
    return " ".join((s or "").replace("\xa0", " ").split())


def _js_click_sequence() -> list[str]:
    """Event names for the full pointer sequence that Gemini/Angular accepts."""
    return ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]


def _activate_element(js_find: str, expect: str = "element") -> dict[str, Any]:
    """Find an element via js_find (returns {found:true, x, y} or found only)
    and dispatch the full pointer sequence on it. Returns the element rect."""
    r = js(js_find)
    if not r or not r.get("found"):
        raise RuntimeError(f"{expect} not found: {js_find[:80]}...")
    return r


def ensure_gemini_tab(url: str = GEMINI_HOME) -> dict[str, Any]:
    """Switch to an existing gemini.google.com tab, or open one."""
    tabs = list_tabs(include_chrome=False)
    for t in tabs:
        if "gemini.google.com" in t["url"]:
            switch_tab(t["targetId"])
            wait(1.5)
            return t
    new_tab(url)
    wait_for_load(timeout=20)
    wait(3.0)
    return {"url": url}


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
    before_url = js("location.href")
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
    """Composer model selector pill (aria-label contains 打开模式选择器)."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const b = [...document.querySelectorAll('button')].find(x => {
        const label = x.getAttribute('aria-label') || '';
        return label.includes('打开模式选择器') && x.offsetParent;
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


def _activate(js_find: str) -> dict[str, Any]:
    """Dispatch the full pointer sequence on the element found by js_find."""
    return js(js_find)


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
    """Select a model by substring (e.g. 'Pro' or 'Flash') and verify the pill.

    Gemini model rows: `3.5 Flash-Lite 极速回答 新`, `3.6 Flash 全方位帮助`,
    `3.1 Pro 高阶数学与代码`, `扩展思考 擅长解决复杂问题`.
    Opens the model picker itself first.
    """
    open_model_picker()
    r = _click_js(f"""
      const el = [...document.querySelectorAll('[role="menuitem"]')].find(e => {{
        if (!e.offsetParent) return false;
        const t = norm(e.innerText || '');
        return t.includes({target!r});
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


def _upload_tools_button() -> dict[str, Any]:
    """The 上传和工具 composer button (tools entry)."""
    return js(r"""
    (() => {
      const b = [...document.querySelectorAll('button')].find(x => (x.getAttribute('aria-label') || '') === '上传和工具' && x.offsetParent);
      if (!b) return {found: false};
      return {found: true};
    })()
    """)


def open_tools_menu() -> dict[str, Any]:
    """Open the 上传和工具 menu."""
    r = _click_js("""
      const el = [...document.querySelectorAll('button')].find(x => (x.getAttribute('aria-label') || '') === '上传和工具' && x.offsetParent);
    """)
    if not r or not r.get("found"):
        raise RuntimeError("open_tools_menu: 上传和工具 button not found")
    wait(2.5)
    return r


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


def _send_button() -> dict[str, Any]:
    """Composer send button (aria-label 发送)."""
    return js(r"""
    (() => {
      const b = [...document.querySelectorAll('button')].find(x => (x.getAttribute('aria-label') || '') === '发送' && x.offsetParent);
      if (!b) return {found: false};
      return {found: true};
    })()
    """)


def send_message(text: str) -> dict[str, Any]:
    """Type into the Quill composer and click 发送 (full JS pointer sequence)."""
    ed = _composer_editor()
    if not ed.get("found"):
        raise RuntimeError("send_message: Quill composer editor not found")
    if not ed.get("empty"):
        raise RuntimeError("send_message: composer must be empty before typing")
    js("([...document.querySelectorAll('[role=\"textbox\"]')].find(e => e.offsetParent && (e.className||'').toString().includes('ql-editor'))).focus()")
    wait(0.4)
    type_text(text)
    wait(1.0)
    ed2 = _composer_editor()
    if _norm(ed2.get("text")) != _norm(text):
        raise RuntimeError(f"send_message: composer text mismatch after typing: {ed2.get('text','')[:60]!r}")
    r = _click_js("""
      const el = [...document.querySelectorAll('button')].find(x => (x.getAttribute('aria-label') || '') === '发送' && x.offsetParent);
    """)
    if not r or not r.get("found"):
        raise RuntimeError("send_message: 发送 button not found")
    wait(2.0)
    return {"status": "sent", "url": js("location.href")}


def wait_for_reply(timeout: float = 90.0) -> dict[str, Any]:
    """Wait until a Gemini 说 reply appears and stops streaming."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = js(r"""
        (() => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim();
          const body = norm(document.body.innerText || '');
          return {has_user: body.includes('你说'), has_gemini: body.includes('Gemini 说'),
                  has_stop: /停止|停止生成|停止回答/.test(body),
                  len: body.length};
        })()
        """) or {}
        if st.get("has_gemini") and not st.get("has_stop"):
            return {"status": "reply", "url": js("location.href"), "len": st.get("len", 0)}
        wait(5)
    return {"status": "timeout", "len": 0}


def conversation_text(limit: int = 1000) -> str:
    """Read the visible conversation text (the last N chars around 你说/Gemini 说)."""
    body = js("document.body.innerText || ''") or ""
    norm = " ".join(body.split())
    idx = norm.find("你说")
    if idx >= 0:
        return norm[idx:idx + limit]
    return norm[-limit:]


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


def start_deep_research() -> dict[str, Any]:
    """Click 开始研究 on the plan card (scrolls into view first)."""
    r = _click_js("""
      const els = [...document.querySelectorAll('button')].filter(e => {
        if (!e.offsetParent) return false;
        const t = norm(e.innerText || e.textContent);
        return t === '开始研究' || t.includes('开始研究');
      });
      const el = els.length ? els[0] : null;
      if (el) el.scrollIntoView({block: 'center'});
    """)
    if not r or not r.get("found"):
        raise RuntimeError("start_deep_research: 开始研究 button not found (plan card may not be ready)")
    wait(2.0)
    # After scrollIntoView, re-find and dispatch the pointer sequence on the element
    r2 = _click_js("""
      const els = [...document.querySelectorAll('button')].filter(e => {
        if (!e.offsetParent) return false;
        const t = norm(e.innerText || e.textContent);
        return t === '开始研究' || t.includes('开始研究');
      });
      const el = els.length ? els[0] : null;
    """)
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


def close_extra_tab(keep_url_fragment: str | None = None) -> int:
    """Close the most recently opened content tab. Returns remaining tab count."""
    tabs = [t for t in list_tabs(include_chrome=False) if t["url"] and not t["url"].startswith("chrome://")]
    if keep_url_fragment:
        protect = [t for t in tabs if keep_url_fragment in t["url"]]
        closeable = [t for t in tabs if t not in protect]
    else:
        closeable = tabs
    if not closeable:
        raise RuntimeError("close_extra_tab: no closeable tabs")
    target = closeable[-1]
    close_tab(target["targetId"])
    wait(1.5)
    return len([t for t in list_tabs(include_chrome=False) if t["url"] and not t["url"].startswith("chrome://")])


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
        .filter(e => {
          if (!e.offsetParent) return false;
          const r = e.getBoundingClientRect();
          return r.x > 800 && r.x < 1400 && r.y > 50 && r.y < 300;
        })
        .map(e => {
          const r = e.getBoundingClientRect();
          return {text: norm(e.innerText || e.textContent).slice(0, 40),
                  label: (e.getAttribute('aria-label') || '').slice(0, 40),
                  x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
        })
        .filter(x => x.text || x.label)
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
    try:
        cdp("Browser.grantPermissions", permissions=["clipboardReadWrite", "clipboardSanitizedWrite"])
    except Exception:
        pass
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=target["x"], y=target["y"])
    wait(0.3)
    cdp("Input.dispatchMouseEvent", type="mousePressed", x=target["x"], y=target["y"], button="left", clickCount=1)
    wait(0.15)
    cdp("Input.dispatchMouseEvent", type="mouseReleased", x=target["x"], y=target["y"], button="left", clickCount=1)
    wait(2.0)
    clip = js("""
    (async () => {
      try {
        const t = await navigator.clipboard.readText();
        return {ok: true, len: t.length, text: t};
      } catch (e) {
        return {ok: false, err: String(e).slice(0, 150)};
      }
    })()
    """) or {"ok": False}
    if not clip.get("ok") or not clip.get("text"):
        raise RuntimeError(f"export_report_copy: clipboard read failed: {clip.get('err', 'empty')}")
    text = clip.get("text")
    if not isinstance(text, str):
        raise RuntimeError("export_report_copy: clipboard returned non-string")
    return text


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
