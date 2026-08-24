"""Gray-release, read-only Bilibili clicks that prefer background DOM activation."""
from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import urlparse

if TYPE_CHECKING:
    def activate_tab(target: Any) -> str: ...
    def click_at_xy(x: float, y: float, button: str = "left", clicks: int = 1) -> None: ...
    def current_tab() -> dict[str, Any]: ...
    def goto_url(url: str) -> Any: ...
    def js(expression: str) -> Any: ...
    def new_tab(url: str = "about:blank") -> str: ...
    def page_info() -> dict[str, Any]: ...
    def wait(seconds: float = 1.0) -> None: ...
    def wait_for_load(timeout: float = 15.0) -> bool: ...


_CLICKABLE = "a,button,[role=button],[role=link],[role=tab],input[type=button],input[type=submit]"


def _locator_script(selector: str, text: str | None, exact: bool, index: int, click: bool) -> str:
    return """(() => {
  const norm = value => String(value || '').replace(/\\s+/g, ' ').trim();
  const wanted = %s;
  const nodes = Array.from(document.querySelectorAll(%s)).filter(el => {
    if (el.disabled || el.getAttribute('aria-disabled') === 'true') return false;
    if (wanted === null) return true;
    const actual = norm(el.innerText || el.textContent || el.value || el.getAttribute('aria-label'));
    return %s ? actual === wanted : actual.includes(wanted);
  });
  const el = nodes[%d];
  if (!el) return {found: false};
  el.scrollIntoView({block: 'center', inline: 'center'});
  const r = el.getBoundingClientRect();
  %s
  return {found: true, x: r.x + r.width / 2, y: r.y + r.height / 2,
          tag: el.tagName, text: norm(el.innerText || el.textContent || el.value),
          href: el.href || '', target: el.target || ''};
})()""" % (
        json.dumps(text, ensure_ascii=False),
        json.dumps(selector),
        "true" if exact else "false",
        index,
        "el.click();" if click else "",
    )


def _verified(verify: Callable[[], bool], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if verify():
                return True
        except Exception:
            pass
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        wait(min(0.2, remaining))


def bilibili_click_readonly(*, verify: Callable[[], bool], selector: str | None = None,
                            text: str | None = None, exact: bool = True, index: int = 0,
                            timeout: float = 4.0, fallback: bool = True) -> dict[str, Any]:
    """Click a Bilibili control and prove its read-only outcome.

    Uses HTMLElement.click() first so a hidden tab can stay in the background.
    When verification fails, the opt-in compatibility fallback activates the
    attached tab and uses the existing coordinate click.
    """
    if not callable(verify):
        raise TypeError("verify must be callable")
    if index < 0 or timeout < 0:
        raise ValueError("index and timeout must be non-negative")
    host = (urlparse(page_info().get("url", "")).hostname or "").lower()
    if host != "bilibili.com" and not host.endswith(".bilibili.com"):
        raise RuntimeError("bilibili_click_readonly is restricted to Bilibili")
    if verify():
        raise RuntimeError("verification condition is already true before the click")

    selector = selector or _CLICKABLE
    probe = js(_locator_script(selector, text, exact, index, False))
    if not isinstance(probe, dict) or not probe.get("found"):
        raise RuntimeError("Bilibili control not found")

    href = probe.get("href", "")
    try:
        if href.startswith(("http://", "https://")):
            if probe.get("target") == "_blank":
                new_tab(href)
            else:
                goto_url(href)
            wait_for_load()
        else:
            js(_locator_script(selector, text, exact, index, True))
    except Exception:
        pass  # navigation may destroy the old execution context after a valid action
    if _verified(verify, timeout):
        result = {"status": "ok", "mode": "silent", "target": probe}
        print("[bilibili-click] silent success:", probe.get("text") or probe.get("tag"))
        return result

    if not fallback:
        raise RuntimeError("Bilibili silent click did not complete the task")

    activate_tab(current_tab())
    probe = js(_locator_script(selector, text, exact, index, False))
    if not isinstance(probe, dict) or not probe.get("found"):
        raise RuntimeError("Bilibili control disappeared before fallback")
    click_at_xy(probe["x"], probe["y"])
    if not _verified(verify, timeout):
        raise RuntimeError("Bilibili silent and fallback clicks did not complete the task")
    result = {"status": "ok", "mode": "fallback", "target": probe}
    print("[bilibili-click] fallback success:", probe.get("text") or probe.get("tag"))
    return result
