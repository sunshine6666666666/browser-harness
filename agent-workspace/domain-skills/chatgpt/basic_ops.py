"""ChatGPT basic conversation-lifecycle ops for browser-harness.

Runs inside browser-harness (heredoc: `browser-harness <<'PY'` then
`exec(open("<repo>/agent-workspace/domain-skills/chatgpt/basic_ops.py").read())`
and call the functions below). Verified 2026-08-04 against chatgpt.com
Chinese UI (direct capability radios + current-model submenu, sidebar history items).

Covered lifecycle: open site, new chat, switch chat, delete chat,
select model, set reasoning effort, send message, scroll conversation,
close tab. Deep Research (深度研究) lives in the companion
deep_research.py (arm / progress / export).
Settings/personalization are intentionally out of scope.

All element targeting is DOM/aria/testid based; coordinates are computed
at runtime via getBoundingClientRect, never hardcoded.
"""

from __future__ import annotations

import base64
import json
import re
import time
from urllib.parse import urlparse
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str) -> Any: ...
    def new_tab(url: str = "about:blank") -> str: ...
    def goto_url(url: str) -> None: ...
    def click_at_xy(x: float, y: float, button: str = "left", clicks: int = 1) -> None: ...
    def type_text(text: str) -> None: ...
    def press_key(key: str, modifiers: int = 0) -> None: ...
    def wait_for_load(timeout: float = 15.0) -> bool: ...
    def wait(seconds: float = 1.0) -> None: ...
    def cdp(method: str, session_id: str | None = None, **params: Any) -> Any: ...
    def drain_events() -> list[dict[str, Any]]: ...
    def list_tabs(include_chrome: bool = True) -> list[dict[str, Any]]: ...
    def current_tab() -> dict[str, Any]: ...
    def activate_tab(target: str | None = None) -> None: ...
    def switch_tab(target: str) -> None: ...
    def close_tab(target: str | None = None) -> None: ...
    def capture_screenshot(path: str | None = None, full: bool = False, max_dim: int | None = None) -> str: ...


_TASK_OWNED_TABS: set[str] = set()
_SHARE_RESULTS: dict[str, dict[str, Any]] = {}


def _norm(s: str | None) -> str:
    return " ".join((s or "").replace("\xa0", " ").split())


def _sent_message_match(expected: str, rendered: str) -> str | None:
    """Classify full or safely collapsed evidence for the newly added user turn."""
    rendered = _norm(rendered)
    if expected and expected in rendered:
        return "full"
    if len(expected) > 240 and rendered.startswith(expected[:160]):
        return "collapsed_prefix"
    return None


def _is_canonical_conversation_url(url: str) -> bool:
    """Reject transient ChatGPT routes such as `/c/WEB:<temporary-id>`."""
    parsed = urlparse(url or "")
    return bool(
        parsed.scheme == "https" and
        parsed.hostname == "chatgpt.com" and
        re.fullmatch(r"/c/[A-Za-z0-9-]{8,}", parsed.path) and
        not parsed.query and not parsed.fragment
    )


def observe_chatgpt_state() -> dict[str, Any]:
    """Read the current page state without changing the page."""
    raw = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const visible = el => {
        if (!el || !el.offsetParent) return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.x >= 0 && r.y >= 0 &&
               r.right <= innerWidth && r.bottom <= innerHeight;
      };
      const visibleText = el => visible(el) && norm(el.innerText || el.textContent || el.getAttribute('aria-label'));
      const form = document.querySelector('form[data-type="unified-composer"]');
      const editor = form && (form.querySelector('[contenteditable="true"]') ||
                              form.querySelector('textarea, [role="textbox"]'));
      const draft = editor && editor.cloneNode(true);
      if (draft) draft.querySelectorAll('[data-inline-selection-pill][data-id="plugin:connector_openai_deep_research"], [data-inline-selection-pill-cursor-target]').forEach(el => el.remove());
      const controls = [...document.querySelectorAll('button, [role="button"], [role="status"]')]
        .filter(visible).map(visibleText).filter(Boolean);
      const body = norm(document.body && (document.body.innerText || document.body.textContent));
      const auth_required = [...document.querySelectorAll('button, a, h1, h2, input')]
        .some(el => /登录|log in|sign in|password|验证码|MFA|账号选择|choose account/i.test(visibleText(el) || ''));
      const paywall_or_quota = [...document.querySelectorAll('button, a, h1, h2, [role="dialog"]')]
        .some(el => /升级|付款|购买|quota|upgrade|subscribe|payment/i.test(visibleText(el) || ''));
      const dialog = [...document.querySelectorAll('[role="dialog"]')].some(visible);
      const generating = [...document.querySelectorAll('[data-testid="stop-button"]')].some(visible) ||
        controls.some(t => /停止回答|停止生成|停止研究|正在生成|正在研究|stop generating|stop streaming/i.test(t));
      const url = location.href;
      const match = url.match(/^https:\/\/chatgpt\.com\/c\/([A-Za-z0-9-]{8,})$/);
      const composer_visible = !!(editor && visible(editor));
      return {
        url,
        conversation_id: match ? match[1] : null,
        composer_visible,
        composer_empty: composer_visible && !norm(draft.textContent || draft.value),
        generating,
        auth_required,
        paywall_or_quota,
        dialog,
        body_nonempty: !!body
      };
    })()
    """) or {}
    url = str(raw.get("url", ""))
    canonical = _is_canonical_conversation_url(url)
    if raw.get("auth_required"):
        state = "auth_required"
    elif raw.get("paywall_or_quota"):
        state = "paywall_or_quota"
    elif raw.get("dialog"):
        state = "dialog"
    elif canonical and raw.get("generating"):
        state = "generating"
    elif url == "https://chatgpt.com/" and raw.get("composer_visible") and raw.get("composer_empty"):
        state = "ready_home"
    elif canonical and raw.get("composer_visible") and raw.get("composer_empty"):
        state = "ready_conversation"
    else:
        state = "unknown"
    return {**raw, "state": state, "conversation_id": raw.get("conversation_id") if canonical else None}


def _click_element_center(js_find: str, expect: str = "element") -> dict[str, Any]:
    """Run a JS snippet that returns {found, x, y} (center of target)."""
    r = js(js_find)
    if not r or not r.get("found"):
        raise RuntimeError(f"{expect} not found: {js_find[:80]}...")
    click_at_xy(r["x"], r["y"])
    return r


def _composer_state() -> str:
    """Current model+effort shown in the composer picker, e.g. '5.6 Sol 中' or '极高'."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll('button')].find(b => {
        const t = norm(b.innerText || b.textContent);
        if (!b.offsetParent) return false;
        const r = b.getBoundingClientRect();
        if (r.width < 20) return false;
        const inComposer = !!b.closest('form[data-type="unified-composer"]');
        const isPicker = (b.matches('[aria-haspopup="menu"]') || b.classList.contains('__composer-pill')) &&
                         b.getAttribute('data-testid') !== 'composer-plus-btn';
        if (inComposer && isPicker) return true;
        if (r.y < innerHeight * 0.8) return false; // legacy fallback outside composer form
        return /^5\.\d\s+\S+/.test(t) || /^GPT-5\./.test(t) ||
               ['极速', '轻度', '中', '高', '极高', '最高', '超高', 'Pro'].includes(t);
      });
      return el ? norm(el.innerText || el.textContent).slice(0, 30) : '';
    })()
    """)


def _find_composer_picker() -> dict[str, Any]:
    """Center of the composer model/effort picker button (model+effort or capability style)."""
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const scoped = [...document.querySelectorAll('form[data-type="unified-composer"] button')].filter(b =>
        b.offsetParent && b.getAttribute('data-testid') !== 'composer-plus-btn' &&
        (b.matches('[aria-haspopup="menu"]') || b.classList.contains('__composer-pill'))
      );
      const btns = scoped.length ? scoped : [...document.querySelectorAll('button')].filter(b => {
        const t = norm(b.innerText || b.textContent);
        if (!b.offsetParent) return false;
        const r = b.getBoundingClientRect();
        if (r.width < 20 || r.y < innerHeight * 0.8) return false;
        return /^5\.\d\s+\S+/.test(t) || /^GPT-5\./.test(t) ||
               ['极速', '轻度', '中', '高', '极高', '最高', '超高', 'Pro'].includes(t);
      });
      if (!btns.length) return {found: false};
      const b = btns[0].getBoundingClientRect();
      return {found: true, x: Math.round(b.x + b.width * 0.7), y: Math.round(b.y + b.height / 2)};
    })()
    """)
    return r


def open_chatgpt(url: str = "https://chatgpt.com/") -> dict[str, Any]:
    """Open the home page or one exact conversation in a task-owned tab."""
    if url == "https://chatgpt.com/":
        target_url = url
    else:
        conversation_id = _conversation_id(url)
        target_url = f"https://chatgpt.com/c/{conversation_id}"
    target_id = new_tab(target_url)
    _TASK_OWNED_TABS.add(target_id)
    try:
        wait_for_load(timeout=20)
        deadline = time.monotonic() + 20
        state: dict[str, Any] = {}
        while time.monotonic() < deadline:
            state = observe_chatgpt_state()
            if state.get("state") != "unknown":
                break
            wait(0.5)
        if state.get("state") == "unknown":
            raise RuntimeError("unknown: ChatGPT page state did not stabilize")
        return {"target_id": target_id, **state}
    except Exception:
        _TASK_OWNED_TABS.discard(target_id)
        close_tab(target_id)
        raise


def new_chat() -> dict[str, Any]:
    """Click sidebar '新聊天' and prove a fresh, empty composer is active."""
    before_url = js("location.href")
    clicked = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const links = [...document.querySelectorAll('a')].filter(a =>
        /新聊天|New chat/i.test(norm(a.innerText || a.textContent)) && a.offsetParent);
      if (!links.length) return {found: false};
      links[0].click();
      return {found: true, clicked: true};
    })()
    """)
    if not clicked or not clicked.get("found"):
        raise RuntimeError("new_chat: new-chat link not found")
    wait(2.0)
    state = js(r"""
    (() => {
      const form = document.querySelector('form[data-type="unified-composer"]');
      const editor = form && (form.querySelector('[contenteditable="true"]') ||
                              form.querySelector('textarea, [role="textbox"]'));
      const visible = !!(editor && editor.offsetParent);
      const text = editor ? ((editor.innerText || editor.value || '').trim()) : '';
      return {
        url: location.href,
        path: location.pathname,
        composer_found: visible,
        composer_empty: visible && text === ''
      };
    })()
    """)
    if not state or not state.get("composer_found") or not state.get("composer_empty"):
        raise RuntimeError("new_chat: fresh chat composer is missing or non-empty")
    after_url = state.get("url", "")
    if "/c/" in before_url and after_url == before_url:
        raise RuntimeError("new_chat: unchanged existing conversation is not a fresh chat")
    path = state.get("path") or ""
    if path != "/":
        raise RuntimeError(f"new_chat: fresh home path required after click ({after_url})")
    return state


def switch_chat(conversation: str) -> dict[str, Any]:
    """Switch to one exact conversation URL, path, or ID."""
    conversation_id = _conversation_id(conversation)
    target_url = f"https://chatgpt.com/c/{conversation_id}"
    current = observe_chatgpt_state()
    if (current.get("url") == target_url and
            current.get("state") in {"ready_conversation", "generating"}):
        return current
    goto_url(target_url)
    wait_for_load(timeout=25)
    deadline = time.monotonic() + 25
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = observe_chatgpt_state()
        if state.get("url") == target_url and state.get("state") in {"ready_conversation", "generating"}:
            return state
        wait(0.5)
    raise RuntimeError(f"postcondition_failed: exact conversation {target_url} did not become readable")


def delete_chat(conversation: str, confirm: bool = False) -> dict[str, Any]:
    """Delete one exact conversation after explicit confirmation."""
    if not confirm:
        raise RuntimeError("precondition: delete_chat requires confirm=True")
    conversation_id = _conversation_id(conversation)
    _open_exact_conversation_options(conversation_id)
    dl = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll('[role="menuitem"]')].find(i =>
        norm(i.innerText || i.textContent) === '删除' || norm(i.innerText || i.textContent) === 'Delete');
      if (!el) return {found: false};
      el.click();
      return {found: true};
    })()
    """)
    if not dl or not dl.get("found"):
        raise RuntimeError("not_found: delete menu item")
    wait(1.5)
    conf = js(r"""
    (() => {
      const el = document.querySelector('[data-testid="delete-conversation-confirm-button"]');
      if (!el) return {found: false};
      el.click();
      return {found: true};
    })()
    """)
    if not conf or not conf.get("found"):
        raise RuntimeError("dialog: delete confirmation did not appear")
    wait(3.0)
    gone = js(r"""
    (() => {
      const suffix = '/c/' + %r;
      return ![...document.querySelectorAll('a[href*="/c/"]')].some(x =>
        x.offsetParent && new URL(x.href, location.href).pathname === suffix);
    })()
    """ % conversation_id)
    if not gone:
        # sidebar may still be animating; retry once after a longer wait
        wait(2.5)
        gone = js(r"""
        (() => {
          const suffix = '/c/' + %r;
          return ![...document.querySelectorAll('a[href*="/c/"]')].some(x =>
            x.offsetParent && new URL(x.href, location.href).pathname === suffix);
        })()
        """ % conversation_id)
    if not gone:
        raise RuntimeError(f"postcondition_failed: exact conversation /c/{conversation_id} still present after delete")
    return {"deleted": True, "conversation_id": conversation_id}


def _visible_menu_count() -> int:
    """Count only rendered menu layers; hidden Radix mounts do not count."""
    return int(js(r"""
    (() => {
      const visibleMenus = [...document.querySelectorAll('[role="menu"]')].filter(el => {
        if (!el.offsetParent) return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.x < innerWidth && r.y < innerHeight &&
               r.right > 0 && r.bottom > 0;
      });
      return visibleMenus.length;
    })()
    """) or 0)


def _activate_composer_picker() -> dict[str, Any]:
    """Use the full pointer sequence required by the current Radix trigger."""
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const form = document.querySelector('form[data-type="unified-composer"]');
      const buttons = form ? [...form.querySelectorAll('button')] : [];
      const visible = buttons.filter(b => {
        if (!b.offsetParent || b.disabled) return false;
        const r = b.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.x >= 0 && r.y >= 0 &&
               r.right <= innerWidth && r.bottom <= innerHeight;
      });
      const el = visible.find(b => b.getAttribute('data-testid') !== 'composer-plus-btn' &&
        b.getAttribute('aria-haspopup') === 'menu' &&
        !/添加文件|attach|语音|voice|听写|dictation/i.test(norm((b.innerText || '') + ' ' + (b.getAttribute('aria-label') || '')))) ||
        visible.find(b => /GPT|推理|Reasoning|快速|Fast|极高|High|中|Medium|低|Low/i.test(
          norm((b.innerText || '') + ' ' + (b.getAttribute('aria-label') || ''))));
      if (!el) return {found: false};
      for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
        const event = type.startsWith('pointer')
          ? new PointerEvent(type, {bubbles: true, cancelable: true, pointerId: 1,
              pointerType: 'mouse', isPrimary: true, button: 0,
              buttons: type.endsWith('down') ? 1 : 0})
          : new MouseEvent(type, {bubbles: true, cancelable: true, button: 0,
              buttons: type.endsWith('down') ? 1 : 0});
        el.dispatchEvent(event);
      }
      return {found: true, text: norm(el.innerText || el.getAttribute('aria-label'))};
    })()
    """) or {"found": False}


def _usable_picker_panel() -> bool:
    """True when a visible menu is an already-open usable model/effort panel.

    Issue #12 (2026-08-08): the current ChatGPT UI renders the model/effort
    panel as a Radix popper that stays 'open' even after trigger toggle and
    Escape presses, while remaining fully usable (radios clickable, aria-checked
    verifiable). Treat that as a successfully open panel instead of a cleanup
    failure. Unrelated menus (e.g. 下载 ChatGPT 桌面版) never match.
    """
    return bool(js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      return [...document.querySelectorAll('[role="menu"]')].some(el => {
        if (!el.offsetParent) return false;
        const r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) return false;
        const t = norm(el.innerText || '');
        return /模型|思考强度|推理强度|GPT-|高级|更快|更智能|极高/.test(t);
      });
    })()
    """) or False)


def _close_visible_menus(max_layers: int = 4, *, tolerate_usable: bool = False) -> None:
    """Close all visible picker layers, preferring the Radix trigger toggle.

    When tolerate_usable=True, a still-visible model/effort panel that is open
    and usable is accepted (Issue #12 cleanup false-failure) instead of raising.
    """
    if _visible_menu_count() == 0:
        return
    toggled = _activate_composer_picker()
    if toggled.get("found"):
        wait(0.5)
        if _visible_menu_count() == 0:
            return
    for _ in range(max_layers):
        press_key("Escape")
        wait(0.35)
        if _visible_menu_count() == 0:
            return
    if tolerate_usable and _usable_picker_panel():
        return
    raise RuntimeError("picker menus remained visible after trigger/Escape cleanup")


def open_model_picker() -> None:
    """Click the composer model/effort picker button to open the model panel.

    Handles both UI styles: model+effort (e.g. '5.6 Sol 中') and capability
    slider (e.g. '极高'). Then ensures the advanced view is expanded.

    Issue #12 (2026-08-08): if the model/effort panel is already open and
    usable (trigger toggle and Escape cannot dismiss this Radix popper), reuse
    it instead of a close→reopen cycle that raises a false cleanup failure.
    """
    if _usable_picker_panel():
        return
    _close_visible_menus()
    r = _find_composer_picker()
    if not r or not r.get("found"):
        raise RuntimeError("open_model_picker: composer model button not found")
    for attempt in range(2):
        clicked = _activate_composer_picker()
        if not clicked or not clicked.get("found"):
            raise RuntimeError("open_model_picker: composer model button disappeared")
        wait(1.4)
        if _visible_menu_count() > 0:
            break
        # panel did not open — likely a leftover closing overlay; clear and retry
        press_key("Escape")
        wait(0.8)
    if _visible_menu_count() == 0:
        raise RuntimeError("open_model_picker: model panel did not open")
    # If the panel is in simple/capability view, expand advanced view first.
    has_advanced = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      return [...document.querySelectorAll('[role="menuitem"]')].some(i =>
        norm(i.innerText || i.textContent).startsWith('模型'));
    })()
    """)
    if not has_advanced:
        if not _click_advanced_item("高级", required=False):
            _click_advanced_item("Advanced", required=False)


def _click_advanced_item(prefix: str, required: bool = True) -> bool:
    """Click an advanced-view menu item when that UI variant is present.

    UI label drift (2026-08-08): the reasoning group's submenu entry is currently
    rendered as 思考强度 (older label: 推理强度). Callers that need the reasoning
    radios should pass a candidate list via _click_advanced_item_any() or try both
    labels explicitly; never rely on a single stale label.
    """
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const pre = %r;
      const el = [...document.querySelectorAll('[role="menuitem"], button')].find(i => {
        if (!i.offsetParent || !norm(i.innerText || i.textContent).startsWith(pre)) return false;
        const b = i.getBoundingClientRect();
        return b.width > 0 && b.height > 0 && b.x >= 0 && b.y >= 0 &&
               b.right <= innerWidth && b.bottom <= innerHeight;
      });
      if (!el) return {found: false};
      for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
        const event = type.startsWith('pointer')
          ? new PointerEvent(type, {bubbles: true, cancelable: true, pointerId: 1,
              pointerType: 'mouse', isPrimary: true, button: 0,
              buttons: type.endsWith('down') ? 1 : 0})
          : new MouseEvent(type, {bubbles: true, cancelable: true, button: 0,
              buttons: type.endsWith('down') ? 1 : 0});
        el.dispatchEvent(event);
      }
      return {found: true, clicked: true};
    })()
    """ % prefix)
    if not r or not r.get("found"):
        if required:
            raise RuntimeError(f"advanced item {prefix!r} not found in model panel")
        return False
    if not r.get("clicked"):
        raise RuntimeError(f"advanced item {prefix!r} was not activated")
    wait(1.0)
    return True


def _open_model_choices() -> None:
    """Open model radios in either the advanced or current direct-submenu UI."""
    if _click_advanced_item("模型", required=False):
        return
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll('[role="menuitem"][aria-haspopup="menu"], [role="menuitem"][data-has-submenu], [role="menuitem"]')]
        .find(i => {
          if (!i.offsetParent) return false;
          const t = norm(i.innerText || i.textContent);
          const aria = norm(i.getAttribute('aria-label') || '');
          const b = i.getBoundingClientRect();
          return (/^GPT-|^o\d|模型|Model|选择模型|Select model/i.test(t + ' ' + aria)) && b.width > 0 && b.height > 0 &&
                 b.x >= 0 && b.y >= 0 && b.right <= innerWidth && b.bottom <= innerHeight;
        });
      if (!el) return {found: false};
      for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
        const event = type.startsWith('pointer')
          ? new PointerEvent(type, {bubbles: true, cancelable: true, pointerId: 1,
              pointerType: 'mouse', isPrimary: true, button: 0,
              buttons: type.endsWith('down') ? 1 : 0})
          : new MouseEvent(type, {bubbles: true, cancelable: true, button: 0,
              buttons: type.endsWith('down') ? 1 : 0});
        el.dispatchEvent(event);
      }
      return {found: true, clicked: true};
    })()
    """)
    if not r or not r.get("found") or not r.get("clicked"):
        raise RuntimeError("select_model: model submenu not found")
    wait(1.0)


def _radio_target(name: str, first_token: bool = False, activate: bool = False) -> dict[str, Any]:
    """Find an exact hit-test-safe radio and optionally activate it once."""
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const expected = %r;
      const firstToken = %s;
      const activate = %s;
      const els = [...document.querySelectorAll('[role="menuitemradio"]')].filter(e => {
        if (!e.offsetParent) return false;
        const text = norm(e.innerText || e.textContent);
        const matches = firstToken ? text.split(/\s+/)[0] === expected : text === expected;
        if (!matches) return false;
        const b = e.getBoundingClientRect();
        if (b.width <= 0 || b.height <= 0 || b.x < 0 || b.y < 0 ||
            b.right > innerWidth || b.bottom > innerHeight) return false;
        const hit = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2);
        return !!hit && (hit === e || e.contains(hit));
      });
      if (!els.length) return {found: false};
      els.sort((a, b) => b.getBoundingClientRect().x - a.getBoundingClientRect().x);
      const el = els[0];
      const b = el.getBoundingClientRect();
      const checked = el.getAttribute('aria-checked') === 'true';
      let activated = false;
      if (activate && !checked) {
        for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
          const event = type.startsWith('pointer')
            ? new PointerEvent(type, {bubbles: true, cancelable: true, pointerId: 1,
                pointerType: 'mouse', isPrimary: true, button: 0,
                buttons: type.endsWith('down') ? 1 : 0})
            : new MouseEvent(type, {bubbles: true, cancelable: true, button: 0,
                buttons: type.endsWith('down') ? 1 : 0});
          el.dispatchEvent(event);
        }
        activated = true;
      }
      return {
        found: true,
        x: Math.round(b.x + b.width / 2),
        y: Math.round(b.y + b.height / 2),
        checked: checked,
        activated: activated
      };
    })()
    """ % (name, "true" if first_token else "false", "true" if activate else "false"))
    return r or {"found": False}


def _verify_radio_after_reopen(name: str, *, model: bool, first_token: bool = False) -> dict[str, Any]:
    open_model_picker()
    if model:
        _open_model_choices()
    elif not _click_advanced_item("推理强度", required=False):
        _click_advanced_item("思考强度", required=False)
    check = _radio_target(name, first_token=first_token)
    _close_visible_menus(tolerate_usable=True)
    if not check.get("found") or not check.get("checked"):
        raise RuntimeError(f"picker radio {name!r} is not aria-checked after selection")
    return {"name": name, "checked": True}


def select_model(model_name: str) -> dict[str, Any]:
    """Select an exact model radio and re-open the picker to prove aria-checked."""
    open_model_picker()
    _open_model_choices()
    target = _radio_target(model_name)
    if not target.get("found"):
        press_key("Escape")
        raise RuntimeError(f"select_model: model {model_name!r} not in visible list")
    if not target.get("checked"):
        activated = _radio_target(model_name, activate=True)
        if not activated.get("found") or not activated.get("activated"):
            raise RuntimeError(f"select_model: could not activate model {model_name!r}")
        wait(1.2)
    return _verify_radio_after_reopen(model_name, model=True)


def set_reasoning_effort(level: str) -> dict[str, Any]:
    """Set reasoning effort and re-open the picker to prove exact aria-checked."""
    open_model_picker()
    if not _click_advanced_item("推理强度", required=False):
        _click_advanced_item("思考强度", required=False)
    target = _radio_target(level, first_token=True)
    if not target.get("found"):
        press_key("Escape")
        raise RuntimeError(f"set_reasoning_effort: level {level!r} not in visible list")
    if not target.get("checked"):
        activated = _radio_target(level, first_token=True, activate=True)
        if not activated.get("found") or not activated.get("activated"):
            raise RuntimeError(f"set_reasoning_effort: could not activate level {level!r}")
        wait(1.0)
    return _verify_radio_after_reopen(level, model=False, first_token=True)


def send_message(text: str, evidence_timeout: float = 8.0) -> dict[str, Any]:
    """Send once from the unified composer and return non-retryable evidence.

    Preflight failures raise before any click. After the send click, callers get
    ``definitely_sent`` or ``unknown`` and must never resend an ``unknown`` result.
    """
    expected = _norm(text)
    if not expected:
        raise RuntimeError("send_message: message must not be empty")
    before = js(r"""
    (() => {
      const form = document.querySelector('form[data-type="unified-composer"]');
      const editor = form && (form.querySelector('[contenteditable="true"]') ||
                              form.querySelector('textarea, [role="textbox"]'));
      const users = [...document.querySelectorAll('[data-message-author-role="user"]')];
      const existing_user_messages = users.length;
      const last_user = users.length ? users[users.length - 1] : null;
      const last_turn_testid = last_user?.closest('[data-testid^="conversation-turn-"]')?.getAttribute('data-testid') || '';
      const last_turn_match = last_turn_testid.match(/conversation-turn-(\d+)/);
      if (!form || !editor || !editor.offsetParent) return {found: false};
      const r = editor.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0 || r.x < 0 || r.y < 0 ||
          r.right > innerWidth || r.bottom > innerHeight) return {found: false};
      const draft = editor.cloneNode(true);
      draft.querySelectorAll('[data-inline-selection-pill][data-id="plugin:connector_openai_deep_research"], [data-inline-selection-pill-cursor-target]').forEach(el => el.remove());
      const content = (draft.textContent || draft.value || '').trim();
      editor.focus();
      return {
        found: true,
        empty: content === '',
        url: location.href,
        user_count: existing_user_messages,
        user_message_ids: users.map(el => el.getAttribute('data-message-id')).filter(Boolean),
        last_user_message_id: last_user?.getAttribute('data-message-id') || null,
        last_user_turn: last_turn_match ? Number(last_turn_match[1]) : -1
      };
    })()
    """)
    if not before or not before.get("found"):
        raise RuntimeError("send_message: visible unified composer not found")
    if not before.get("empty"):
        raise RuntimeError("send_message: unified composer must be empty before typing")
    wait(0.4)
    type_text(text)
    wait(0.5)
    btn = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const form = document.querySelector('form[data-type="unified-composer"]');
      const send_button = form && [...form.querySelectorAll('button')].find(el => {
        const label = norm(el.getAttribute('aria-label') || '');
        const testid = el.getAttribute('data-testid') || '';
        return (testid === 'send-button' || label === '发送提示词' ||
                label === '发送提示' || label === 'Send prompt') && el.offsetParent &&
               !el.disabled && el.getAttribute('aria-disabled') !== 'true';
      });
      if (!send_button) return {found: false};
      const r = send_button.getBoundingClientRect();
      const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      if (r.width <= 0 || r.height <= 0 || r.x < 0 || r.y < 0 ||
          r.right > innerWidth || r.bottom > innerHeight ||
          !hit || !(hit === send_button || send_button.contains(hit))) return {found: false};
      return {found: true};
    })()
    """)
    if not btn or not btn.get("found"):
        raise RuntimeError("send_message: enabled unified-composer send button not found")
    try:
        activated = js(r"""
        (() => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim();
          const form = document.querySelector('form[data-type="unified-composer"]');
          const activate_send_button = form && [...form.querySelectorAll('button')].find(el => {
            const label = norm(el.getAttribute('aria-label') || '');
            const testid = el.getAttribute('data-testid') || '';
            return (testid === 'send-button' || label === '发送提示词' ||
                    label === '发送提示' || label === 'Send prompt') && el.offsetParent &&
                   !el.disabled && el.getAttribute('aria-disabled') !== 'true';
          });
          if (!activate_send_button) return {found: false, clicked: false};
          for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
            const event = type.startsWith('pointer')
              ? new PointerEvent(type, {bubbles: true, cancelable: true, pointerId: 1,
                  pointerType: 'mouse', isPrimary: true, button: 0,
                  buttons: type.endsWith('down') ? 1 : 0})
              : new MouseEvent(type, {bubbles: true, cancelable: true, button: 0,
                  buttons: type.endsWith('down') ? 1 : 0});
            activate_send_button.dispatchEvent(event);
          }
          return {found: true, clicked: true};
        })()
        """) or {}
    except Exception:
        return {
            "status": "unknown",
            "reason": "send_activation_exception",
            "url": before.get("url"),
            "composer_empty": False,
            "expected_user_message_found": False,
        }
    if not activated.get("found") or not activated.get("clicked"):
        return {
            "status": "unknown",
            "reason": "send_activation_unconfirmed",
            "url": before.get("url"),
            "composer_empty": False,
            "expected_user_message_found": False,
        }

    deadline = time.monotonic() + evidence_timeout
    latest: dict[str, Any] = {}
    evidence_read_failed = False
    while time.monotonic() < deadline:
        wait(0.5)
        try:
            latest = js(r"""
            (() => {
              const norm = s => (s || '').replace(/\s+/g, ' ').trim();
              const form = document.querySelector('form[data-type="unified-composer"]');
              const editor = form && (form.querySelector('[contenteditable="true"]') ||
                                      form.querySelector('textarea, [role="textbox"]'));
              const draft = editor && editor.cloneNode(true);
              if (draft) draft.querySelectorAll('[data-inline-selection-pill][data-id="plugin:connector_openai_deep_research"], [data-inline-selection-pill-cursor-target]').forEach(el => el.remove());
              const users = [...document.querySelectorAll('[data-message-author-role="user"]')];
              const last_user = users.length ? users[users.length - 1] : null;
              const last_user_message = last_user ? norm(last_user.innerText || last_user.textContent) : '';
              const last_turn_testid = last_user?.closest('[data-testid^="conversation-turn-"]')?.getAttribute('data-testid') || '';
              const last_turn_match = last_turn_testid.match(/conversation-turn-(\d+)/);
              return {
                url: location.href,
                composer_empty: !!draft && norm(draft.textContent || draft.value) === '',
                user_count: users.length,
                last_user_message_id: last_user?.getAttribute('data-message-id') || null,
                last_user_turn: last_turn_match ? Number(last_turn_match[1]) : -1,
                last_user_message: last_user_message
              };
            })()
            """) or {}
        except Exception:
            evidence_read_failed = True
            continue
        message_match = _sent_message_match(expected, latest.get("last_user_message", ""))
        before_ids = set(before.get("user_message_ids") or [])
        message_id = latest.get("last_user_message_id")
        new_turn = (
            message_id and message_id not in before_ids and
            latest.get("last_user_turn", -1) > before.get("last_user_turn", -1)
        )
        if (_is_canonical_conversation_url(latest.get("url", "")) and
                latest.get("composer_empty") and new_turn and message_match):
            return {
                "status": "definitely_sent",
                "url": latest.get("url"),
                "composer_empty": bool(latest.get("composer_empty")),
                "expected_user_message_found": True,
                "message_match": message_match,
                "message_id": message_id,
                "message_turn": latest.get("last_user_turn"),
            }
    return {
        "status": "unknown",
        "reason": "post_send_evidence_unavailable" if evidence_read_failed else "post_send_evidence_inconclusive",
        "url": latest.get("url", before.get("url")),
        "composer_empty": bool(latest.get("composer_empty")),
        "expected_user_message_found": False,
    }


def scroll_conversation(direction: str = "down", amount: int = 600, wait_s: float = 0.8) -> int:
    """Scroll the main conversation container (overflowY:auto) via wheel.

    Returns the resulting scrollTop. Direction: 'down' or 'up'.
    """
    target = js(r"""
    (() => {
      const els = [...document.querySelectorAll('div')].filter(el =>
        el.scrollHeight > el.clientHeight + 50 && getComputedStyle(el).overflowY === 'auto');
      if (!els.length) return {found: false};
      els.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
      const el = els[0];
      const b = el.getBoundingClientRect();
      return {found: true, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2)};
    })()
    """)
    if not target or not target.get("found"):
        raise RuntimeError("scroll_conversation: no scrollable main container")
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=target["x"], y=target["y"])
    wait(0.3)
    dy = amount if direction == "down" else -amount
    cdp("Input.dispatchMouseEvent", type="mouseWheel", x=target["x"], y=target["y"],
        deltaX=0, deltaY=dy)
    wait(wait_s)
    return js(r"""
    (() => {
      const els = [...document.querySelectorAll('div')].filter(el =>
        el.scrollHeight > el.clientHeight + 50 && getComputedStyle(el).overflowY === 'auto');
      els.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
      return els.length ? els[0].scrollTop : -1;
    })()
    """)


def close_extra_tab(target_id: str) -> int:
    """Close one exact task-owned tab, never a tab selected by URL order."""
    if target_id not in _TASK_OWNED_TABS:
        raise RuntimeError("destructive_scope_violation: tab is not task-owned")
    try:
        owner = tab_owner(target_id)
    except (NameError, RuntimeError):
        owner = None
    owner_name = owner.get("owner") if isinstance(owner, dict) else None
    if owner_name and owner_name not in {"chatgpt-domain-skill", "chatgpt-domain-skill-live-audit"}:
        raise RuntimeError("destructive_scope_violation: tab is protected by another owner")
    close_tab(target_id)
    _TASK_OWNED_TABS.discard(target_id)
    wait(1.5)
    return len(_TASK_OWNED_TABS)


def export_share_link(conversation: str | None = None) -> dict[str, Any]:
    """Create or read one conversation-level public share link."""
    import subprocess
    if conversation is None:
        current = observe_chatgpt_state()
        if current.get("state") not in {"ready_conversation", "generating"}:
            raise RuntimeError("precondition: current exact conversation is required")
        conversation_id = current["conversation_id"]
    else:
        conversation_id = _conversation_id(conversation)
        current = switch_chat(conversation_id)
    target_url = f"https://chatgpt.com/c/{conversation_id}"
    if current.get("url") != target_url:
        raise RuntimeError("postcondition_failed: share target conversation is not exact")
    cached = _SHARE_RESULTS.get(conversation_id)
    if cached:
        return {**cached, "created": False}
    wait(0.5)
    previous_clipboard = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
    r = js(r"""
    (() => {
      const b = [...document.querySelectorAll('button[data-testid="share-chat-button"]')]
        .find(x => x.offsetParent && !x.disabled);
      if (!b) return {found: false};
      const r = b.getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
    })()
    """)
    if not r or not r.get("found"):
        raise RuntimeError("not_found: conversation-level share button")
    # Persist uncertainty before activation: even a failed evidence read must not replay it.
    _SHARE_RESULTS[conversation_id] = {
        "status": "unknown", "reason": "share_result_unknown", "url": None,
        "created": False, "conversation_id": conversation_id,
    }
    try:
        click_at_xy(r["x"], r["y"])
    except Exception:
        result = {"status": "unknown", "reason": "share_activation_exception", "url": None,
                  "created": False, "conversation_id": conversation_id}
        _SHARE_RESULTS[conversation_id] = result
        return result
    deadline = time.monotonic() + 8
    link = ""
    confirmed = False
    while time.monotonic() < deadline:
        wait(0.5)
        confirmed = bool(js(r"""
        (() => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim();
          return [...document.querySelectorAll('[role="status"], [role="alert"]')].some(el =>
            el.offsetParent && /公开链接.*复制|链接已复制|link copied/i.test(norm(el.innerText || el.textContent)));
        })()
        """) or False)
        link = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
        if link.startswith("https://chatgpt.com/share/") and (confirmed or link != previous_clipboard):
            break
    if not link.startswith("https://chatgpt.com/share/") or not (confirmed or link != previous_clipboard):
        result = {"status": "unknown", "reason": "share_result_unknown", "url": None,
                  "created": False, "conversation_id": conversation_id}
        _SHARE_RESULTS[conversation_id] = result
        return result
    result = {"status": "success", "url": link, "created": True, "conversation_id": conversation_id}
    _SHARE_RESULTS[conversation_id] = result
    return result


def read_shared_conversation(url: str, close_after: bool = True) -> dict[str, Any]:
    """Open a chatgpt.com/share/... or chatgpt.com/s/... link in a new tab and
    return the visible conversation text. Closes the tab when close_after.

    Note: /share/ links render the full conversation inline; /s/p_... links
    (message-level) may render a broken UI (Failed to fetch template) with the
    data embedded in a React Router stream — see
    agent-browser-operations references/chatgpt-shared-extraction.md for the
    extraction fallback.
    """
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != "chatgpt.com" or
            not (parsed.path.startswith("/share/") or parsed.path.startswith("/s/"))):
        raise RuntimeError("precondition: official ChatGPT share URL is required")
    target_id = new_tab(url)
    _TASK_OWNED_TABS.add(target_id)
    try:
        try:
            page_info()
        except Exception:
            pass
        wait_for_load(timeout=20)
        deadline = time.monotonic() + 20
        records: dict[str, dict[str, Any]] = {}
        body: dict[str, Any] = {}
        direction = "up"
        boundary_reads = 0
        previous_signature = None
        while time.monotonic() < deadline:
            body = js(r"""
            (() => {
              const norm = s => (s || '').replace(/\s+/g, ' ').trim();
              const visible = el => !!(el.offsetParent && el.getBoundingClientRect().width > 0);
              const toggles = [...document.querySelectorAll('button[data-testid="collapsible-user-message-toggle"]')]
                .filter(el => visible(el) && norm(el.innerText || el.textContent) === '展开');
              toggles.forEach(el => el.click());
              const turns = [...document.querySelectorAll('[data-message-author-role]')].filter(visible).map(el => ({
                role: el.getAttribute('data-message-author-role'),
                id: el.getAttribute('data-message-id'),
                turn: el.closest('[data-testid^="conversation-turn-"]')?.getAttribute('data-testid') || '',
                text: norm(el.innerText || el.textContent)
              })).filter(x => x.text);
              const candidates = [document.scrollingElement, ...document.querySelectorAll('div')].filter(el =>
                el && el.scrollHeight > el.clientHeight + 50 &&
                ['auto', 'scroll'].includes(getComputedStyle(el).overflowY));
              candidates.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
              const scroller = candidates[0];
              if (scroller && !scroller.hasAttribute('tabindex')) scroller.setAttribute('tabindex', '-1');
              if (scroller) scroller.focus({preventScroll: true});
              const t = norm(document.body && (document.body.innerText || document.body.textContent));
              return {url: location.href, body: t, turns,
                      message_count: turns.length,
                      scroll: scroller ? {found: true, top: scroller.scrollTop,
                        height: scroller.scrollHeight, client: scroller.clientHeight} : {found: false}};
            })()
            """) or {}
            if body.get("url") != url:
                raise RuntimeError("postcondition_failed: share page changed URL")
            turns = body.get("turns") or []
            if direction == "down":
                for turn in turns:
                    key = turn.get("turn") or turn.get("id")
                    if not key:
                        raise RuntimeError("postcondition_failed: share turn has no stable identity")
                    if len(turn.get("text", "")) >= len(records.get(key, {}).get("text", "")):
                        records[key] = turn
            if body.get("message_count", 0) > 0:
                scroll = body.get("scroll") or {}
                at_boundary = not scroll.get("found") or (
                    scroll.get("top", 0) <= 1 if direction == "up" else
                    scroll.get("top", 0) + scroll.get("client", 0) >= scroll.get("height", 0) - 1
                )
                signature = [(t.get("turn"), t.get("id"), t.get("text")) for t in turns]
                boundary_reads = boundary_reads + 1 if at_boundary and signature == previous_signature else 0
                previous_signature = signature
                if boundary_reads >= 2:
                    if direction == "down":
                        break
                    direction = "down"
                    boundary_reads = 0
                    previous_signature = None
                    continue
                if not at_boundary:
                    press_key("PageUp" if direction == "up" else "PageDown")
                wait(0.6)
            else:
                wait(0.5)
        else:
            raise RuntimeError("timeout: share conversation boundaries not verified")
        if not records:
            raise RuntimeError("postcondition_failed: share page has no readable turns")
        text = "\n".join(f"[{turn.get('role')}] {turn.get('text')}" for turn in records.values())
        return {"target_id": target_id, "url": body.get("url", ""), "text": text}
    finally:
        if close_after:
            close_tab(target_id)
            _TASK_OWNED_TABS.discard(target_id)
            wait(1.0)


def conversation_text(limit: int = 4000) -> str:
    """Read the visible conversation text (assistant + user turns)."""
    wait(0.5)
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const parts = [];
      document.querySelectorAll('[data-message-author-role]').forEach(el => {
        const t = norm(el.innerText || el.textContent);
        if (t) parts.push('[' + el.getAttribute('data-message-author-role') + '] ' + t.slice(0, %d));
      });
      return parts.slice(-20).join('\n').slice(-%d);
    })()
    """ % (limit, limit))


def conversation_turns(limit_per_turn: int = 100_000) -> list[dict[str, Any]]:
    """Read the currently rendered text turns with stable identities."""
    if limit_per_turn < 1:
        raise ValueError("conversation_turns: limit_per_turn must be at least 1")
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
      return [...document.querySelectorAll(
        '[data-message-author-role="user"], [data-message-author-role="assistant"]'
      )].filter(el => el.offsetParent).map(el => {
        const clone = el.cloneNode(true);
        const omitted = !!clone.querySelector(
          'img, video, audio, [data-testid*="file"], [data-writing-block-fullscreen-editor], .writing-block-editor'
        );
        clone.querySelectorAll(
          'button, [role="button"], svg, input, textarea, [aria-hidden="true"], [data-inline-selection-pill]'
        ).forEach(node => node.remove());
        const text = norm(clone.textContent);
        const turn = el.closest('[data-testid^="conversation-turn-"]')?.getAttribute('data-testid') || '';
        const id = el.getAttribute('data-message-id') || turn || null;
        return {
          role: el.getAttribute('data-message-author-role'),
          id,
          turn,
          text: text.slice(0, %d),
          truncated: text.length > %d,
          non_text_omitted: omitted
        };
      }).filter(turn => turn.text);
    })()
    """ % (limit_per_turn, limit_per_turn)) or []


def _conversation_api_page(
    conversation_id: str,
    before: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Read one authorized conversation page without exposing auth headers."""
    target_id = new_tab("about:blank")
    _TASK_OWNED_TABS.add(target_id)
    payload = None
    status = None
    try:
        cdp("Fetch.enable", patterns=[
            {"urlPattern": "*backend-api/conversations/*", "requestStage": "Request"},
            {"urlPattern": "*backend-api/conversations/*", "requestStage": "Response"},
        ])
        goto_url(f"https://chatgpt.com/c/{conversation_id}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and payload is None:
            for event in drain_events():
                if event.get("method") != "Fetch.requestPaused":
                    continue
                params = event["params"]
                request_id = params["requestId"]
                request_url = params["request"]["url"]
                target_request = f"/backend-api/conversations/{conversation_id}" in request_url
                if params.get("responseStatusCode") is None:
                    if target_request:
                        endpoint = f"https://chatgpt.com/backend-api/conversations/{conversation_id}"
                        request_url = (
                            f"{endpoint}/messages?before={before}&include_has_versions=true&num_turns=100"
                            if before else f"{endpoint}?include_has_versions=true&num_turns=100"
                        )
                    cdp("Fetch.continueRequest", requestId=request_id, url=request_url)
                    continue
                if target_request:
                    response = cdp("Fetch.getResponseBody", requestId=request_id)
                    body = response["body"]
                    if response.get("base64Encoded"):
                        body = base64.b64decode(body).decode("utf-8")
                    payload = json.loads(body)
                    status = params["responseStatusCode"]
                cdp("Fetch.continueRequest", requestId=request_id)
            wait(0.1)
        if status != 200 or not isinstance(payload, dict):
            raise RuntimeError(f"incomplete_extraction: conversation page request failed ({status})")
        if not isinstance(payload.get("messages"), list) or not isinstance(payload.get("page_info"), dict):
            raise RuntimeError("incomplete_extraction: unexpected conversation page response")
        return payload
    finally:
        try:
            cdp("Fetch.disable")
        except Exception:
            pass
        close_tab(target_id)
        _TASK_OWNED_TABS.discard(target_id)


def _api_message_turns(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only visible user and final-assistant text from an API page."""
    turns = []
    for message in messages:
        role = (message.get("author") or {}).get("role")
        content = message.get("content") or {}
        metadata = message.get("metadata") or {}
        if (role not in {"user", "assistant"} or
                content.get("content_type") not in {"text", "multimodal_text"} or
                metadata.get("is_visually_hidden_from_conversation") is True or
                message.get("recipient") not in {None, "all"} or
                (role == "assistant" and message.get("channel") not in {None, "final"})):
            continue
        text_parts = []
        omitted = False
        for part in content.get("parts") or []:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
            else:
                omitted = True
        text = "\n".join(text_parts).strip()
        if text:
            turns.append({
                "id": message.get("id"),
                "role": role,
                "text": text,
                "non_text_omitted": omitted,
            })
    return turns


def full_conversation(max_pages: int = 120, wait_s: float = 0.8) -> dict[str, Any]:
    """Read all authorized text pages until the server proves history start."""
    if not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("full_conversation: max_pages must be at least 1")
    state = observe_chatgpt_state()
    if state.get("state") != "ready_conversation":
        raise RuntimeError("precondition: a complete, idle canonical conversation is required")
    original_tab = current_tab()
    original_target = original_tab.get("targetId") or original_tab.get("target_id")
    conversation_id = state["conversation_id"]
    before = None
    accumulated: list[dict[str, Any]] = []
    seen_cursors = set()
    complete = False
    pages = 0
    try:
        while pages < max_pages:
            payload = _conversation_api_page(conversation_id, before)
            page = _api_message_turns(payload["messages"])
            page_ids = {turn["id"] for turn in page}
            accumulated = page + [turn for turn in accumulated if turn["id"] not in page_ids]
            pages += 1
            page_info = payload["page_info"]
            if not page_info.get("has_previous_page"):
                complete = True
                break
            before = page_info.get("start_cursor")
            if not before or before in seen_cursors:
                break
            seen_cursors.add(before)
    finally:
        if original_target:
            switch_tab(original_target)
    if not complete or not accumulated:
        raise RuntimeError("incomplete_extraction: server history boundary was not verified")

    final_state = observe_chatgpt_state()
    if (final_state.get("state") != "ready_conversation" or
            final_state.get("conversation_id") != state.get("conversation_id")):
        raise RuntimeError("incomplete_extraction: conversation identity changed while reading")
    return {
        "status": "complete",
        "url": final_state["url"],
        "conversation_id": final_state["conversation_id"],
        "pages": pages,
        "turns": accumulated,
        "source": "authorized_browser_response_pages",
    }


def find_conversation_by_title(title: str, timeout: float = 12.0) -> str:
    """Return the canonical URL for one exact visible or searched title."""
    title = _norm(title)
    if not title:
        raise ValueError("find_conversation_by_title: title must not be empty")

    def matches() -> list[str]:
        return js(r"""
        (() => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim();
          const title = %r;
          const scope = document.querySelector('[role="dialog"]');
          if (!scope) return [];
          return [...scope.querySelectorAll('a[href*="/c/"]')].filter(a => {
            if (!a.offsetParent) return false;
            const firstLine = (a.innerText || a.textContent || '').split('\n').map(norm).find(Boolean) || '';
            return firstLine === title;
          }).map(a => new URL(a.href, location.href).pathname);
        })()
        """ % title) or []

    opened = js(r"""
    (() => {
      const input = [...document.querySelectorAll('input')].find(el =>
        el.offsetParent && /搜索|search/i.test(el.getAttribute('placeholder') || el.getAttribute('aria-label') || ''));
      if (input) return true;
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const button = [...document.querySelectorAll('button')].find(el => {
        const label = norm((el.innerText || '') + ' ' + (el.getAttribute('aria-label') || ''));
        return el.offsetParent && /^(搜索|Search|Search chats)$/.test(label);
      });
      if (!button) return false;
      button.click();
      return true;
    })()
    """)
    if not opened:
        raise RuntimeError("not_found: conversation search control")
    deadline = time.monotonic() + timeout
    typed = False
    found: list[str] = []
    previous_found: list[str] | None = None
    stable_reads = 0
    settled = False
    while time.monotonic() < deadline:
        if not typed:
            typed = bool(js(r"""
            (() => {
              const title = %r;
              const input = [...document.querySelectorAll('input')].find(el =>
                el.offsetParent && /搜索|search/i.test(el.getAttribute('placeholder') || el.getAttribute('aria-label') || ''));
              if (!input) return false;
              const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              setter.call(input, title);
              input.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: title}));
              return true;
            })()
            """ % title))
        if typed:
            found = matches()
            if found:
                stable_reads = stable_reads + 1 if found == previous_found else 1
                previous_found = found
                if stable_reads >= 3:
                    settled = True
                    break
        wait(0.4)

    unique = list(dict.fromkeys(found))
    if not unique:
        raise RuntimeError(f"conversation_unavailable: no exact title {title!r}")
    if not settled:
        raise RuntimeError(f"conversation_unavailable: title results did not stabilize for {title!r}")
    if len(unique) != 1:
        raise RuntimeError(f"ambiguous_conversation: {len(unique)} exact title matches for {title!r}")
    conversation_id = _conversation_id(unique[0])
    return f"https://chatgpt.com/c/{conversation_id}"


def prepare_conversation_analysis(
    conversation: str | None,
    instruction: str,
    max_pages: int = 120,
) -> dict[str, Any]:
    """Return a transient, complete transcript package for the calling Agent."""
    instruction = _norm(instruction)
    if not instruction:
        raise ValueError("prepare_conversation_analysis: instruction must not be empty")

    locator = _norm(conversation) if conversation is not None else "current"
    if locator.lower() == "current":
        state = observe_chatgpt_state()
        if state.get("state") != "ready_conversation":
            raise RuntimeError("conversation_unavailable: current page is not an idle canonical conversation")
        acquisition_path = "current_conversation"
    elif locator.lower().startswith("title:"):
        switch_chat(find_conversation_by_title(locator.split(":", 1)[1]))
        acquisition_path = "exact_title_search"
    else:
        try:
            switch_chat(locator)
            acquisition_path = "exact_url_or_id"
        except RuntimeError as exc:
            if "exact conversation URL or ID" not in str(exc):
                raise
            switch_chat(find_conversation_by_title(locator))
            acquisition_path = "exact_title_search"

    transcript = full_conversation(max_pages=max_pages)
    turns = transcript["turns"]
    warnings = []
    omitted = sum(bool(turn.get("non_text_omitted")) for turn in turns)
    if omitted:
        warnings.append(f"{omitted} message(s) contained non-text content omitted from text extraction")
    return {
        "status": "ready_for_agent_analysis",
        "instruction": instruction,
        "conversation_id": transcript["conversation_id"],
        "conversation_url": transcript["url"],
        "locator_path": acquisition_path,
        "acquisition_path": transcript.get("source", "rendered_conversation"),
        "completeness": "complete",
        "page_count": transcript["pages"],
        "user_message_count": sum(turn["role"] == "user" for turn in turns),
        "assistant_message_count": sum(turn["role"] == "assistant" for turn in turns),
        "messages": turns,
        "warnings": warnings,
    }


def _conversation_scroll_state() -> dict[str, Any]:
    """Focus the main virtualized conversation scroller and return live evidence."""
    return js(r"""
    (() => {
      const els = [...document.querySelectorAll('div')].filter(el =>
        el.scrollHeight > el.clientHeight + 50 &&
        ['auto', 'scroll'].includes(getComputedStyle(el).overflowY));
      if (!els.length) return {found: false};
      els.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
      const el = els[0];
      if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
      el.focus({preventScroll: true});
      return {
        found: true,
        scroll_top: el.scrollTop,
        scroll_height: el.scrollHeight,
        client_height: el.clientHeight,
        message_count: document.querySelectorAll('[data-message-author-role]').length
      };
    })()
    """) or {"found": False}


def page_conversation(direction: str = "down", steps: int = 1, wait_s: float = 0.8) -> dict[str, Any]:
    """Page a virtualized long chat with real PageUp/PageDown key events."""
    direction = direction.lower().strip()
    if direction not in {"up", "down"}:
        raise ValueError("page_conversation: direction must be 'up' or 'down'")
    if steps < 1:
        raise ValueError("page_conversation: steps must be at least 1")
    before = _conversation_scroll_state()
    if not before.get("found"):
        raise RuntimeError("page_conversation: no scrollable main container")
    key = "PageDown" if direction == "down" else "PageUp"
    for _ in range(steps):
        press_key(key)
        wait(wait_s)
    after = _conversation_scroll_state()
    if not after.get("found"):
        raise RuntimeError("page_conversation: conversation scroller disappeared")
    after["moved"] = after.get("scroll_top") != before.get("scroll_top")
    return after


def read_markdown_block_summary(index: int = -1) -> str:
    """Return the full text of a ChatGPT writing/Markdown editor block."""
    blocks = js(r"""
    (() => [...document.querySelectorAll(
      '[data-writing-block-fullscreen-editor], .writing-block-editor, .mt4SwW_editor'
    )].filter((el, i, all) => !all.some((other, j) => j !== i && other.contains(el)))
      .map(el => {
        const text = (el.innerText || el.textContent || '').trim();
        return {text: text, chars: text.length};
      }).filter(item => item.chars > 0))()
    """) or []
    if not blocks:
        raise RuntimeError("read_markdown_block_summary: no Markdown editor block found")
    try:
        return blocks[index]["text"]
    except IndexError as exc:
        raise RuntimeError(f"read_markdown_block_summary: block index {index} is out of range") from exc


def _conversation_id(conversation: str) -> str:
    """Normalize an exact ChatGPT conversation URL/path/ID; reject title fragments."""
    value = (conversation or "").strip().rstrip("/")
    if re.fullmatch(r"[A-Za-z0-9-]{8,}", value):
        return value
    path_match = re.fullmatch(r"/c/([A-Za-z0-9-]{8,})", value)
    if path_match:
        return path_match.group(1)
    parsed = urlparse(value)
    url_match = re.fullmatch(r"/c/([A-Za-z0-9-]{8,})", parsed.path)
    if (parsed.scheme == "https" and parsed.hostname == "chatgpt.com" and
            not parsed.query and not parsed.fragment and url_match):
        return url_match.group(1)
    raise RuntimeError("precondition: exact conversation URL or ID is required; title fragments are unsafe")


def _open_exact_conversation_options(conversation_id: str) -> None:
    """Open only the options button inside the exact `/c/<id>` sidebar row.

    A brand-new conversation's row may not have hydrated into the sidebar
    immediately after send_message (React list lag). Before raising, perform
    a bounded reload-and-retry: navigate to the exact conversation URL, wait
    for hydration, and re-query the row (max 2 reloads).
    """
    def _query() -> dict[str, Any]:
        return js(r"""
    (() => {
      const suffix = '/c/' + %r;
      const matches = [...document.querySelectorAll('a[href*="/c/"]')].filter(a =>
        a.offsetParent && new URL(a.href, location.href).pathname === suffix);
      if (matches.length !== 1) return {found: false, count: matches.length};
      const a = matches[0];
      for (const type of ['mouseover', 'mouseenter', 'mousemove', 'pointerover']) {
        a.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true}));
      }
      const item = a.closest('li') || a.parentElement;
      const btn = [...item.querySelectorAll('button')].find(b =>
        /history-item-\d+-options/i.test(b.getAttribute('data-testid') || ''));
      if (!btn) return {found: false, count: 1};
      btn.click();
      return {found: true};
    })()
    """ % conversation_id) or {"found": False}

    r = _query()
    reloads = 0
    while (not r or not r.get("found")) and reloads < 2:
        reloads += 1
        goto_url(f"https://chatgpt.com/c/{conversation_id}")
        wait_for_load(timeout=25)
        wait(2.5)
        r = _query()
    if not r or not r.get("found"):
        raise RuntimeError(
            f"not_found: exact sidebar row /c/{conversation_id} or its options button "
            f"was not found (after {reloads} reload{'' if reloads == 1 else 's'})"
        )
    wait(1.2)


def _read_exact_conversation_row(conversation_id: str) -> dict[str, Any]:
    return js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const suffix = '/c/' + %r;
      const a = [...document.querySelectorAll('a[href*="/c/"]')].find(x =>
        x.offsetParent && new URL(x.href, location.href).pathname === suffix);
      const inputGone = ![...document.querySelectorAll('input[aria-label="聊天标题"], input[aria-label="Chat title"]')]
        .some(x => x.offsetParent);
      const title = a ? norm(a.innerText || a.textContent).split('\n')[0] : null;
      return {found: !!a, input_gone: inputGone, title: title};
    })()
    """ % conversation_id) or {}


def _rename_chat_once(conversation_id: str, new_title: str) -> dict[str, Any]:
    """Perform one exact-URL rename transaction and return its final row read."""
    _open_exact_conversation_options(conversation_id)
    ren = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll('[role="menuitem"]')].find(i => {
        const t = norm(i.innerText || i.textContent);
        return (t === '重命名' || t === 'Rename') && i.offsetParent;
      });
      if (!el) return {found: false};
      el.click();
      return {found: true};
    })()
    """)
    if not ren or not ren.get("found"):
        raise RuntimeError("rename_chat: rename menu item not found")
    wait(1.2)
    edited = js(r"""
    (() => {
      const title = %r;
      const el = [...document.querySelectorAll('input[aria-label="聊天标题"], input[aria-label="Chat title"]')]
        .find(x => x.offsetParent);
      if (!el) return {found: false};
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(el, title);
      el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: title}));
      el.dispatchEvent(new Event('change', {bubbles: true}));
      el.blur();
      const form = document.querySelector('form[data-type="unified-composer"]');
      if (!form || !form.offsetParent) return {found: false, blurred: document.activeElement !== el};
      for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
        const event = type.startsWith('pointer')
          ? new PointerEvent(type, {bubbles: true, cancelable: true, pointerId: 1,
              pointerType: 'mouse', isPrimary: true, button: 0,
              buttons: type.endsWith('down') ? 1 : 0})
          : new MouseEvent(type, {bubbles: true, cancelable: true, button: 0,
              buttons: type.endsWith('down') ? 1 : 0});
        form.dispatchEvent(event);
      }
      return {found: true, blurred: document.activeElement !== el, commit_dispatched: true};
    })()
    """ % new_title)
    if (not edited or not edited.get("found") or not edited.get("blurred") or
            not edited.get("commit_dispatched")):
        raise RuntimeError("rename_chat: title input commit sequence could not be dispatched")

    wait(1.5)
    check = _read_exact_conversation_row(conversation_id)
    if not check.get("found") or not check.get("input_gone") or check.get("title") != new_title:
        raise RuntimeError(f"rename_chat: exact /c/{conversation_id} row did not save title {new_title!r}")

    target_url = f"https://chatgpt.com/c/{conversation_id}"
    goto_url("https://chatgpt.com/")
    wait_for_load(timeout=20)
    wait(1.5)
    goto_url(target_url)
    wait_for_load(timeout=20)
    wait(2.0)
    return _read_exact_conversation_row(conversation_id)


def rename_chat(conversation: str, new_title: str) -> str:
    """Rename one exact conversation, retrying one stale persistence read only."""
    conversation_id = _conversation_id(conversation)
    new_title = _norm(new_title)
    if not new_title:
        raise RuntimeError("rename_chat: new title must not be empty")

    def _persisted(row: dict[str, Any]) -> bool:
        return bool(row.get("found") and row.get("input_gone") and
                    row.get("title") == new_title)

    persisted = _rename_chat_once(conversation_id, new_title)
    if _persisted(persisted):
        return persisted["title"]

    # A newly-created row can transiently accept the edit while the first
    # leave/reopen read still exposes its generated title. Retry the complete
    # exact-URL transaction once, and only when that read proves the row is
    # still present with a different title. Never retry a missing/ambiguous row.
    retry_attempted = False
    if (persisted.get("found") and persisted.get("title") and
            persisted.get("title") != new_title):
        retry_attempted = True
        persisted = _rename_chat_once(conversation_id, new_title)
        if _persisted(persisted):
            return persisted["title"]

    suffix = "after bounded retry" if retry_attempted else "after reload"
    raise RuntimeError(
        f"rename_chat: exact /c/{conversation_id} title {new_title!r} did not persist {suffix}"
    )


def toggle_user_message_expand(msg_index: int = 0) -> str:
    """Expand/collapse the long user prompt of message msg_index.

    ChatGPT collapses long user messages; the toggle button has
    data-testid="collapsible-user-message-toggle" and shows 展开/收起.
    Returns the button text after the toggle.
    """
    r = js(r"""
    (() => {
      const msgs = [...document.querySelectorAll('[data-message-author-role="user"]')];
      const m = msgs[%d];
      if (!m) return {found: false};
      const b = m.querySelector('button[data-testid="collapsible-user-message-toggle"]');
      if (!b) return {found: false, has_toggle: false};
      b.click();
      return {found: true, has_toggle: true};
    })()
    """ % msg_index)
    if not r or not r.get("found"):
        raise RuntimeError(f"toggle_user_message_expand: user message #{msg_index} not found")
    if not r.get("has_toggle"):
        return "no-toggle"  # short prompt, nothing to expand
    wait(1.5)
    state = js(r"""
    (() => {
      const msgs = [...document.querySelectorAll('[data-message-author-role="user"]')];
      const m = msgs[%d];
      if (!m) return null;
      const b = m.querySelector('button[data-testid="collapsible-user-message-toggle"]');
      return b ? (b.innerText || '').trim() : null;
    })()
    """ % msg_index)
    return state or "unknown"


def expand_all_user_messages() -> int:
    """Expand every long user prompt in the current conversation. Returns the
    number of toggles actually expanded (i.e. buttons that read 展开 before
    the click). Already-expanded messages are left untouched."""
    n = 0
    for i in range(10):
        before = js(r"""
        (() => {
          const msgs = [...document.querySelectorAll('[data-message-author-role="user"]')];
          const m = msgs[%d];
          if (!m) return null;
          const b = m.querySelector('button[data-testid="collapsible-user-message-toggle"]');
          return b ? (b.innerText || '').trim() : 'no-toggle';
        })()
        """ % i)
        if before is None:
            break
        if before == "no-toggle":
            break
        if before == "展开":
            toggle_user_message_expand(i)
            n += 1
        # "收起" → already expanded; leave as is
    return n


def send_and_wait(text: str, timeout: int = 180) -> dict[str, Any]:
    """Send once, then wait for a new stable assistant turn."""
    before = js(r"""
    (() => {
      const msgs = [...document.querySelectorAll('[data-message-author-role="assistant"]')];
      return {
        assistant_count: msgs.length,
        assistant_message_ids: msgs.map(el => el.getAttribute('data-message-id')).filter(Boolean)
      };
    })()
    """) or {}
    send_evidence = send_message(text)
    if send_evidence.get("status") != "definitely_sent":
        raise RuntimeError(
            f"send_and_wait: send status unknown at {send_evidence.get('url')}; do not retry automatically"
        )
    before_ids = set(before.get("assistant_message_ids") or [])
    before_count = int(before.get("assistant_count", 0))
    last_txt = None
    stable = 0
    saw_new_assistant = False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        wait(2.0)
        state = js(r"""
        (() => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim();
          const send_btn = [...document.querySelectorAll('button')].some(el => {
            const label = norm(el.getAttribute('aria-label') || '');
            return el.getAttribute('data-testid') === 'send-button' ||
              label === '发送提示词' || label === '发送提示' || label === 'Send prompt';
          });
          const msgs = [...document.querySelectorAll('[data-message-author-role="assistant"]')];
          const last = msgs.length ? msgs[msgs.length - 1] : null;
          const last_text = last ? norm(last.innerText || '') : '';
          const last_id = last?.getAttribute('data-message-id') || null;
          const form = document.querySelector('form[data-type="unified-composer"]');
          const editor = form && (form.querySelector('[contenteditable="true"]') ||
                                  form.querySelector('textarea, [role="textbox"]'));
          const draft = editor && editor.cloneNode(true);
          if (draft) draft.querySelectorAll('[data-inline-selection-pill][data-id="plugin:connector_openai_deep_research"], [data-inline-selection-pill-cursor-target]').forEach(el => el.remove());
          const controls = [...document.querySelectorAll('button, [role="status"]')]
            .filter(el => el.offsetParent).map(el => norm(el.innerText || el.textContent || el.getAttribute('aria-label')));
          const generating = !!(form && [...form.querySelectorAll('[data-testid="stop-button"]')].some(el => el.offsetParent)) ||
            controls.some(t => /停止回答|停止生成|停止研究|正在生成|正在研究|stop generating|stop streaming/i.test(t));
          return {
            url: location.href,
            send_btn,
            generating,
            assistant_count: msgs.length,
            assistant_message_id: last_id,
            composer_empty: !!draft && !norm(draft.textContent || draft.value),
            last_len: last_text.length,
            last_tail: last_text.slice(-120)
          };
        })()
        """) or {}
        state["new_assistant"] = bool(
            (state.get("assistant_message_id") and state["assistant_message_id"] not in before_ids) or
            state.get("assistant_count", 0) > before_count
        )
        saw_new_assistant = saw_new_assistant or bool(state.get("new_assistant"))
        txt = (state.get("assistant_message_id"), state.get("last_len"), state.get("last_tail"))
        if state.get("url") == send_evidence.get("url") and state.get("composer_empty") and not state.get("generating") and state.get("new_assistant") and state.get("last_len", 0) > 0:
            if txt == last_txt:
                stable += 1
                if stable >= 2:
                    final_text = js(r"""
                    (() => {
                      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
                      const msgs = [...document.querySelectorAll('[data-message-author-role="assistant"]')];
                      const last = msgs.length ? msgs[msgs.length - 1] : null;
                      return last ? {
                        text: norm(last.innerText || ''),
                        message_id: last.getAttribute('data-message-id') || null
                      } : null;
                    })()
                    """) or {}
                    if (final_text.get("text") and final_text.get("message_id") == state.get("assistant_message_id")
                            and len(final_text["text"]) == state.get("last_len")
                            and final_text["text"][-120:] == state.get("last_tail")):
                        return {"status": "done", "text": final_text["text"],
                                "message_id": final_text.get("message_id"),
                                "url": state.get("url", "")}
            else:
                stable = 1
            last_txt = txt
        else:
            stable = 0
            last_txt = None
    if not saw_new_assistant:
        raise RuntimeError("postcondition_failed: no new assistant turn observed")
    raise RuntimeError(f"timeout: reply not finished within {timeout}s")


def switch_header_tab(tab: str) -> str:
    """Switch the top header tab between 聊天 (chat) and 工作 (workspace).

    Accepts '聊天'/'chat' or '工作'/'work' (case-insensitive). The header
    renders two `role="radio"` buttons; selection is tracked by aria-checked.
    Returns the now-selected tab label.

    NOTE: named switch_header_tab on purpose — browser-harness already exports
    a `switch_tab` helper for switching browser tabs; this would shadow it.
    """
    normalized = tab.strip().lower()
    if normalized not in {'聊天', 'chat', '工作', 'work'}:
        raise RuntimeError("precondition: header tab must be chat/聊天 or work/工作")
    target = '聊天' if normalized in ('聊天', 'chat') else '工作'
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const radios = [...document.querySelectorAll('[role="radio"]')].filter(r =>
        norm(r.innerText || r.textContent) === %r);
      const el = radios.find(r => r.offsetParent);
      if (!el) return {found: false};
      if (el.getAttribute('aria-checked') === 'true') return {found: true, already: true};
      el.click();
      return {found: true, already: false};
    })()
    """ % target)
    if not r or not r.get("found"):
        raise RuntimeError(f"switch_tab: {target!r} radio button not found")
    wait(1.5)
    check = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll('[role="radio"]')].find(r =>
        norm(r.innerText || r.textContent) === %r);
      return el ? el.getAttribute('aria-checked') : null;
    })()
    """ % target)
    if check != "true":
        raise RuntimeError(f"switch_tab: {target!r} not selected after click (aria-checked={check})")
    return target


def run(script: str | None = None) -> None:
    """CLI entry for smoke tests. Pass a pipe-delimited action string, e.g.:

    run('new_chat|switch_chat:English|scroll_conversation:down:800')
    """
    actions = (script or "open_chatgpt").split("|")
    for a in actions:
        parts = a.split(":")
        name, args = parts[0], parts[1:]
        print(f"== {name} {args} ==")
        if name == "open_chatgpt":
            open_chatgpt()
        elif name == "new_chat":
            new_chat()
        elif name == "switch_chat":
            switch_chat(args[0])
        elif name == "delete_chat":
            delete_chat(args[0])
        elif name == "select_model":
            select_model(args[0])
        elif name == "set_reasoning_effort":
            set_reasoning_effort(args[0])
        elif name == "send_message":
            send_message(":".join(args))
        elif name == "scroll_conversation":
            print("scrollTop:", scroll_conversation(args[0] if args else "down",
                                                   int(args[1]) if len(args) > 1 else 600))
        elif name == "conversation_text":
            print(conversation_text())
        else:
            raise RuntimeError(f"run: unknown action {name}")


# This file is a library when loaded with exec(...) inside browser-harness.
# Call run() explicitly for the pipe-delimited smoke runner; do not auto-open
# ChatGPT merely because an agent loaded the domain skill.
