"""ChatGPT basic conversation-lifecycle ops for browser-harness.

Runs inside browser-harness (heredoc: `browser-harness <<'PY'` then
`exec(open("<repo>/agent-workspace/domain-skills/chatgpt/basic_ops.py").read())`
and call the functions below). Verified 2026-08-03 against chatgpt.com
Chinese UI (model picker "5.6 Sol 中" style, sidebar history items).

Covered lifecycle: open site, new chat, switch chat, delete chat,
select model, set reasoning effort, send message, scroll conversation,
close tab. Settings/personalization are intentionally out of scope.

All element targeting is DOM/aria/testid based; coordinates are computed
at runtime via getBoundingClientRect, never hardcoded.
"""

from __future__ import annotations

import time
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
    def list_tabs(include_chrome: bool = True) -> list[dict[str, Any]]: ...
    def switch_tab(target: str) -> None: ...
    def close_tab(target: str | None = None) -> None: ...
    def capture_screenshot(path: str | None = None, full: bool = False, max_dim: int | None = None) -> str: ...


def _norm(s: str | None) -> str:
    return " ".join((s or "").replace("\xa0", " ").split())


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
        const isPicker = b.matches('[aria-haspopup="menu"]') || b.classList.contains('__composer-pill');
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
        b.offsetParent && (b.matches('[aria-haspopup="menu"]') || b.classList.contains('__composer-pill'))
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


def open_chatgpt(url: str = "https://chatgpt.com/") -> None:
    """Open ChatGPT in a new tab and wait for load."""
    new_tab(url)
    wait_for_load(timeout=15)
    wait(2.0)
    st = js("location.href")
    if "chatgpt.com" not in st:
        raise RuntimeError(f"open_chatgpt: landed on unexpected URL {st}")


def new_chat() -> None:
    """Click sidebar '新聊天' and verify we land on the chatgpt.com home/composer."""
    _click_element_center(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const links = [...document.querySelectorAll('a')].filter(a =>
        /新聊天|New chat/i.test(norm(a.innerText || a.textContent)) && a.offsetParent);
      if (!links.length) return {found: false};
      const b = links[0].getBoundingClientRect();
      return {found: true, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2)};
    })()
    """, expect="new-chat link")
    wait(2.0)
    if not js("location.href.endsWith('/') || /\\/c\\//.test(location.href)"):
        raise RuntimeError("new_chat: unexpected URL after click")


def switch_chat(title_fragment: str) -> None:
    """Switch to a sidebar conversation whose visible title contains the fragment."""
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const frag = %r;
      const a = [...document.querySelectorAll('a[href*="/c/"]')].find(x =>
        x.offsetParent && norm(x.innerText).includes(frag));
      if (!a) return {found: false};
      const b = a.getBoundingClientRect();
      return {found: true, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2)};
    })()
    """ % title_fragment)
    if not r or not r.get("found"):
        raise RuntimeError(f"switch_chat: no sidebar item containing {title_fragment!r}")
    click_at_xy(r["x"], r["y"])
    wait(2.0)
    url = js("location.href")
    if "/c/" not in url:
        raise RuntimeError(f"switch_chat: did not navigate to a conversation ({url})")


def _hover_and_get_options_button(title_fragment: str) -> dict[str, Any]:
    """Hover the sidebar item and CLICK its '对话选项' (options) button via JS.

    CDP mouse events were observed to time out repeatedly on this page; JS
    click + synthetic hover events are the stable path. Returns {'found': True}
    when the options menu is expected to be open.
    """
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const frag = %r;
      const a = [...document.querySelectorAll('a[href*="/c/"]')].find(x =>
        x.offsetParent && norm(x.innerText).includes(frag));
      if (!a) return {found: false};
      // synthetic hover so the trailing options button becomes active
      for (const type of ['mouseover', 'mouseenter', 'mousemove', 'pointerover']) {
        a.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true}));
      }
      const item = a.closest('li') || a.parentElement;
      const btn = [...item.querySelectorAll('button')].find(b =>
        /history-item-\d+-options/i.test(b.getAttribute('data-testid') || ''));
      if (!btn) {
        const alt = [...document.querySelectorAll('button')].find(b =>
          /history-item-\d+-options/i.test(b.getAttribute('data-testid') || ''));
        if (!alt) return {found: false};
        alt.click();
        return {found: true};
      }
      btn.click();
      return {found: true};
    })()
    """ % title_fragment)
    if not r or not r.get("found"):
        raise RuntimeError(f"options: options button for {title_fragment!r} did not appear on hover")
    wait(1.2)
    return r


def delete_chat(title_fragment: str, confirm: bool = True) -> None:
    """Delete a conversation via sidebar options menu (destructive!).

    Requires confirm=True (default) — never auto-delete without the caller
    explicitly confirming. Deletes ONLY the conversation whose visible title
    contains title_fragment.
    """
    if not confirm:
        raise RuntimeError("delete_chat: confirm must be True (destructive operation)")
    opt = _hover_and_get_options_button(title_fragment)
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
        raise RuntimeError("delete_chat: no 删除 menu item")
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
        raise RuntimeError("delete_chat: confirmation dialog did not appear")
    wait(3.0)
    gone = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const frag = %r;
      return ![...document.querySelectorAll('a[href*="/c/"]')].some(x => norm(x.innerText).includes(frag));
    })()
    """ % title_fragment)
    if not gone:
        # sidebar may still be animating; retry once after a longer wait
        wait(2.5)
        gone = js(r"""
        (() => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim();
          const frag = %r;
          return ![...document.querySelectorAll('a[href*="/c/"]')].some(x => norm(x.innerText).includes(frag));
        })()
        """ % title_fragment)
    if not gone:
        raise RuntimeError(f"delete_chat: {title_fragment!r} still present after delete")


def open_model_picker() -> None:
    """Click the composer model/effort picker button to open the model panel.

    Handles both UI styles: model+effort (e.g. '5.6 Sol 中') and capability
    slider (e.g. '极高'). Then ensures the advanced view is expanded.
    """
    r = _find_composer_picker()
    if not r or not r.get("found"):
        raise RuntimeError("open_model_picker: composer model button not found")
    for attempt in range(2):
        click_at_xy(r["x"], r["y"])
        wait(1.4)
        if js("!!document.querySelector('[role=\"menu\"]')"):
            break
        # panel did not open — likely a leftover closing overlay; clear and retry
        press_key("Escape")
        wait(0.8)
    if not js("!!document.querySelector('[role=\"menu\"]')"):
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
        adv = js(r"""
        (() => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim();
          const el = [...document.querySelectorAll('[role="menuitem"], button')].find(i => {
            const t = norm(i.innerText || i.textContent);
            return (t === '高级' || t === 'Advanced') && i.offsetParent;
          });
          if (!el) return {found: false};
          const b = el.getBoundingClientRect();
          return {found: true, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2)};
        })()
        """)
        if adv and adv.get("found"):
            click_at_xy(adv["x"], adv["y"])
            wait(1.0)


def _click_advanced_item(prefix: str) -> None:
    """Click an advanced-view menu item whose text starts with prefix (模型/推理强度/速度)."""
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const pre = %r;
      const el = [...document.querySelectorAll('[role="menuitem"]')].find(i =>
        norm(i.innerText || i.textContent).startsWith(pre));
      if (!el) return {found: false};
      const b = el.getBoundingClientRect();
      return {found: true, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2)};
    })()
    """ % prefix)
    if not r or not r.get("found"):
        raise RuntimeError(f"advanced item {prefix!r} not found in model panel")
    click_at_xy(r["x"], r["y"])
    wait(1.0)


def select_model(model_name: str) -> None:
    """Select a model from the picker, e.g. 'GPT-5.6 Sol', 'GPT-5.6 Terra', 'GPT-5.6 Luna'.

    Opens the picker, expands the model submenu, clicks the radio with the
    exact label, and verifies the composer picker shows the new model.
    """
    open_model_picker()
    _click_advanced_item("模型")
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const name = %r;
      const els = [...document.querySelectorAll('[role="menuitemradio"]')].filter(e =>
        norm(e.innerText || e.textContent) === name);
      if (!els.length) return {found: false};
      // rightmost submenu wins (avoids same-named entries in the capability slider)
      els.sort((a, b) => b.getBoundingClientRect().x - a.getBoundingClientRect().x);
      const el = els[0];
      const b = el.getBoundingClientRect();
      return {found: true, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2)};
    })()
    """ % model_name)
    if not r or not r.get("found"):
        raise RuntimeError(f"select_model: model {model_name!r} not in list")
    click_at_xy(r["x"], r["y"])
    wait(1.2)
    st = _composer_state()
    if model_name.replace("GPT-", "").split(" ")[0] not in st and model_name not in st:
        raise RuntimeError(f"select_model: composer shows {st!r}, expected {model_name!r}")


def set_reasoning_effort(level: str) -> None:
    """Set reasoning effort. Chinese UI levels: 轻度/中/高/极高/最高/超高."""
    open_model_picker()
    _click_advanced_item("推理强度")
    r = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const lvl = %r;
      const els = [...document.querySelectorAll('[role="menuitemradio"]')].filter(e =>
        norm(e.innerText || e.textContent).split(/\s+/)[0] === lvl);
      if (!els.length) return {found: false};
      // rightmost submenu wins (avoids same-named entries in the capability slider)
      els.sort((a, b) => b.getBoundingClientRect().x - a.getBoundingClientRect().x);
      const el = els[0];
      const b = el.getBoundingClientRect();
      return {found: true, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2)};
    })()
    """ % level)
    if not r or not r.get("found"):
        raise RuntimeError(f"set_reasoning_effort: level {level!r} not found")
    click_at_xy(r["x"], r["y"])
    wait(1.0)
    st = _composer_state()
    if level not in st:
        raise RuntimeError(f"set_reasoning_effort: composer shows {st!r}, expected {level!r}")


def send_message(text: str) -> None:
    """Focus composer, type a message and click the send button (aria-label 发送提示).

    Note: pressing Return alone did NOT send in the verified UI; the explicit
    send button is the reliable path.
    """
    foc = js(r"""
    (() => {
      const el = document.querySelector('[contenteditable="true"]') || document.querySelector('textarea, [role="textbox"]');
      if (!el) return {found: false};
      el.focus();
      return {found: true};
    })()
    """)
    if not foc or not foc.get("found"):
        raise RuntimeError("send_message: composer not found")
    wait(0.4)
    type_text(text)
    wait(0.5)
    btn = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const b = [...document.querySelectorAll('button')].find(el =>
        norm(el.getAttribute('aria-label') || '') === '发送提示' ||
        norm(el.getAttribute('aria-label') || '') === 'Send prompt');
      if (!b) return {found: false};
      const r = b.getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
    })()
    """)
    if not btn or not btn.get("found"):
        raise RuntimeError("send_message: send button not found")
    click_at_xy(btn["x"], btn["y"])
    wait(1.5)
    empty = js("((document.querySelector('[contenteditable=\"true\"]')||{}).innerText||'').trim() === ''")
    if not empty:
        raise RuntimeError("send_message: composer still has text after send")


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


def close_extra_tab(keep_url_fragment: str | None = None) -> int:
    """Close the most recently opened content tab. Returns remaining tab count.

    If keep_url_fragment is given, never close a tab whose URL contains it.
    """
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


def export_share_link(chat_title_fragment: str | None = None) -> str:
    """Export the current (or named) conversation as a public share link.

    Primary path: click the header share-chat-button — it copies the
    conversation-level public link to the clipboard directly (toast: 公开链接
    已复制到剪贴板; no dialog). Fallback: message-level share button
    (share-prompt-link-turn-action-button) which yields a message-level
    /s/p_... link (single message only) for conversations whose header share
    button is disabled (e.g. workspace conversations).

    Reads the clipboard via `pbpaste`. Returns the chatgpt.com/share/... URL.

    NOTE: the returned link is PUBLIC on the internet once created. The
    conversation remains shared until the user revokes it in ChatGPT.
    """
    import subprocess
    if chat_title_fragment:
        switch_chat(chat_title_fragment)
    wait(1.0)
    # -- path 1: header share button (conversation-level link) --
    r = js(r"""
    (() => {
      const b = [...document.querySelectorAll('button')].find(x => x.getAttribute('data-testid') === 'share-chat-button');
      if (!b || b.disabled) return {found: false};
      const r = b.getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
    })()
    """)
    if r.get("found"):
        cdp("Input.dispatchMouseEvent", type="mouseMoved", x=r["x"], y=r["y"])
        wait(0.4)
        cdp("Input.dispatchMouseEvent", type="mousePressed", x=r["x"], y=r["y"], button="left", clickCount=1)
        wait(0.15)
        cdp("Input.dispatchMouseEvent", type="mouseReleased", x=r["x"], y=r["y"], button="left", clickCount=1)
        wait(1.5)
        link = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
        if link.startswith("https://chatgpt.com/share/"):
            return link

    # -- path 2: message-level share button (hover + click) --
    r = js(r"""
    (() => {
      const btns = [...document.querySelectorAll('button[data-testid="share-prompt-link-turn-action-button"]')].filter(b => {
        const r = b.getBoundingClientRect();
        return r.width > 0 && r.y > 0 && r.y < innerHeight;
      });
      if (!btns.length) return {found: false};
      const b = btns[0];
      const r = b.getBoundingClientRect();
      return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
    })()
    """)
    if not r or not r.get("found"):
        # message action buttons only appear on hover — hover the last visible message
        h = js(r"""
        (() => {
          const msgs = [...document.querySelectorAll('[data-message-author-role]')].filter(m => {
            const r = m.getBoundingClientRect();
            return r.width > 0 && r.y > 0 && r.y < innerHeight * 0.7;
          });
          if (!msgs.length) return {found: false};
          const m = msgs[msgs.length - 1];
          const r = m.getBoundingClientRect();
          return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
        })()
        """)
        if not h or not h.get("found"):
            raise RuntimeError("export_share_link: no visible share button (header disabled, no message buttons)")
        cdp("Input.dispatchMouseEvent", type="mouseMoved", x=h["x"], y=h["y"])
        wait(0.8)
        r = js(r"""
        (() => {
          const btns = [...document.querySelectorAll('button[data-testid="share-prompt-link-turn-action-button"]')].filter(b => {
            const r = b.getBoundingClientRect();
            return r.width > 0 && r.y > 0 && r.y < innerHeight;
          });
          if (!btns.length) return {found: false};
          const b = btns[0];
          const r = b.getBoundingClientRect();
          return {found: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
        })()
        """)
    if not r or not r.get("found"):
        raise RuntimeError("export_share_link: no visible share button")
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=r["x"], y=r["y"])
    wait(0.3)
    cdp("Input.dispatchMouseEvent", type="mousePressed", x=r["x"], y=r["y"], button="left", clickCount=1)
    wait(0.2)
    cdp("Input.dispatchMouseEvent", type="mouseReleased", x=r["x"], y=r["y"], button="left", clickCount=1)
    wait(2.0)
    # dialog: 分享提示 with 复制链接 button
    cp = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const els = [...document.querySelectorAll('button, [role="button"]')].filter(el => {
        const t = norm(el.innerText || el.textContent);
        return (t === '复制链接' || t === 'Copy link') && el.offsetParent;
      });
      if (!els.length) return {found: false};
      const b = els[0].getBoundingClientRect();
      return {found: true, x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2)};
    })()
    """)
    if not cp or not cp.get("found"):
        raise RuntimeError("export_share_link: share dialog with 复制链接 did not appear")
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=cp["x"], y=cp["y"])
    wait(0.3)
    cdp("Input.dispatchMouseEvent", type="mousePressed", x=cp["x"], y=cp["y"], button="left", clickCount=1)
    wait(0.2)
    cdp("Input.dispatchMouseEvent", type="mouseReleased", x=cp["x"], y=cp["y"], button="left", clickCount=1)
    wait(2.0)
    link = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
    if not (link.startswith("https://chatgpt.com/share/") or link.startswith("https://chatgpt.com/s/")):
        raise RuntimeError(f"export_share_link: clipboard does not contain a share link: {link[:60]!r}")
    # close the dialog
    press_key("Escape")
    wait(0.5)
    return link


def read_shared_conversation(url: str, close_after: bool = True) -> str:
    """Open a chatgpt.com/share/... or chatgpt.com/s/... link in a new tab and
    return the visible conversation text. Closes the tab when close_after.

    Note: /share/ links render the full conversation inline; /s/p_... links
    (message-level) may render a broken UI (Failed to fetch template) with the
    data embedded in a React Router stream — see
    agent-browser-operations references/chatgpt-shared-extraction.md for the
    extraction fallback.
    """
    new_tab(url)
    wait(3.5)
    body = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const t = norm(document.body.innerText || document.body.textContent);
      const idx = t.indexOf('这是已分享的 ChatGPT 对话副本');
      return {url: location.href, title: document.title, body: (idx >= 0 ? t.slice(idx) : t)};
    })()
    """)
    if close_after:
        share_key = url.split("/")[-1]
        for t in list_tabs(include_chrome=False):
            if share_key in t["url"] or "/share/" in t["url"] or "/s/" in t["url"]:
                if t["url"].startswith("https://chatgpt.com") and not t["url"].startswith("https://chatgpt.com/c/"):
                    close_tab(t["targetId"])
                    break
        wait(1.0)
    return body.get("body", "") or ""


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


def rename_chat(title_fragment: str, new_title: str) -> str:
    """Rename a conversation via sidebar options → 重命名.

    Hover the sidebar item, click its options button, click 重命名, clear the
    input and type the new title. Returns the sidebar title after rename.
    """
    opt = _hover_and_get_options_button(title_fragment)
    ren = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const el = [...document.querySelectorAll('[role="menuitem"]')].find(i => {
        const t = norm(i.innerText || i.textContent);
        return t === '重命名' && i.offsetParent;
      });
      if (!el) return {found: false};
      el.click();
      return {found: true};
    })()
    """)
    if not ren or not ren.get("found"):
        raise RuntimeError("rename_chat: 重命名 menu item not found")
    wait(1.2)
    # rename input appears; select-all + type new title
    inp = js(r"""
    (() => {
      const el = document.querySelector('input[type="text"], textarea') || document.querySelector('[role="textbox"]');
      if (!el || el.offsetParent === null) return {found: false};
      el.focus();
      return {found: true};
    })()
    """)
    if not inp or not inp.get("found"):
        raise RuntimeError("rename_chat: rename input not found")
    wait(0.4)
    press_key("Meta+A")
    wait(0.4)
    type_text(new_title)
    wait(0.6)
    # save: blur + synthetic Enter (plain Return keypress did not save)
    js(r"""
    (() => {
      const el = document.querySelector('input[type="text"], textarea');
      if (!el) return null;
      el.blur();
      el.dispatchEvent(new Event('blur', {bubbles: true}));
      el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', bubbles: true, cancelable: true}));
      el.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', bubbles: true}));
      return true;
    })()
    """)
    wait(2.0)
    # verify new title in sidebar
    check = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const a = [...document.querySelectorAll('a[href*="/c/"]')].find(x => x.offsetParent && norm(x.innerText).includes(%r));
      return a ? norm(a.innerText).split('\n')[0] : null;
    })()
    """ % new_title)
    if not check:
        raise RuntimeError(f"rename_chat: renamed title {new_title!r} not found in sidebar")
    return check


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


def send_and_wait(text: str, timeout: int = 180) -> str:
    """Send a message and wait until ChatGPT finishes replying.

    Polls every 2s: generation is done when the composer's send button
    (aria-label 发送提示) is visible again AND the last assistant message text
    has been stable for 2 consecutive polls. Returns the last assistant
    message text (truncated to 4000 chars).
    """
    send_message(text)
    last_txt = ""
    stable = 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        wait(2.0)
        state = js(r"""
        (() => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim();
          const send_btn = [...document.querySelectorAll('button')].some(el =>
            norm(el.getAttribute('aria-label') || '') === '发送提示' ||
            norm(el.getAttribute('aria-label') || '') === 'Send prompt');
          const msgs = [...document.querySelectorAll('[data-message-author-role="assistant"]')];
          const last = msgs.length ? norm(msgs[msgs.length - 1].innerText || '') : '';
          return {send_btn: send_btn, last_len: last.length, last_tail: last.slice(-120)};
        })()
        """)
        txt = state.get("last_tail", "")
        if state.get("send_btn") and state.get("last_len", 0) > 0:
            if txt == last_txt:
                stable += 1
                if stable >= 2:
                    return js(r"""
                    (() => {
                      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
                      const msgs = [...document.querySelectorAll('[data-message-author-role="assistant"]')];
                      const last = msgs.length ? msgs[msgs.length - 1] : null;
                      return last ? norm(last.innerText || '').slice(0, 4000) : '';
                    })()
                    """)
            else:
                stable = 1
            last_txt = txt
        else:
            stable = 0
            last_txt = ""
    raise RuntimeError(f"send_and_wait: reply not finished within {timeout}s")


def switch_header_tab(tab: str) -> str:
    """Switch the top header tab between 聊天 (chat) and 工作 (workspace).

    Accepts '聊天'/'chat' or '工作'/'work' (case-insensitive). The header
    renders two `role="radio"` buttons; selection is tracked by aria-checked.
    Returns the now-selected tab label.

    NOTE: named switch_header_tab on purpose — browser-harness already exports
    a `switch_tab` helper for switching browser tabs; this would shadow it.
    """
    target = '聊天' if tab.strip().lower() in ('聊天', 'chat') else '工作'
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
