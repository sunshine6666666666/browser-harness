"""ChatGPT Deep Research (深度研究) flow ops for browser-harness.

Runs inside browser-harness (heredoc: `browser-harness <<'PY'` then
`exec(open("<repo>/agent-workspace/domain-skills/chatgpt/deep_research.py").read())`
and call the functions below). Verified 2026-08-05 against chatgpt.com
Chinese UI (Pro account) with a real minimal Deep Research run.

Covered flow: arm Deep Research from the composer + menu, read its progress
from the nested sandbox connector iframe, wait for completion, and export the
finished report as Markdown. It is a companion to basic_ops.py and reuses
nothing from it except the standard harness helpers, so both files can be
exec()'d in the same script without conflicts.

DOM facts (Chinese UI, verified 2026-08-05):
- Composer + menu button: `[data-testid="composer-plus-btn"]` (aria 添加文件等).
  The menu rows are plain DIVs, NOT [role="menuitemradio"].
- The 深度研究 row is a text-leaf element whose normalized text is exactly
  深度研究, inside an ancestor whose normalized text is exactly
  `深度研究 获取详细报告`.
- After selection the composer shows a 深度研究 pill inside the ProseMirror
  composer (a span/token, not a button). Deselect = click the token then
  press Backspace; clicking the + menu row again adds a second token.
- Progress runs in a sandbox iframe
  `https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/...`.
  `iframe_target('connector-openai-deep-research')` (hyphens) returns the
  targetId; then `js(expr, target_id=tid)` must be used. The OUTER connector
  body is empty; real progress/report text lives inside nested
  `document.querySelector('iframe#root').contentDocument.body.innerText`.
  Running state: plan title + step checklist + `正在研究…` / `停止研究`.
  Completion: `研究完成情况：<time> · N 次引用 · N 个搜索` and the report
  body, with `停止研究` gone.
- Export: the finished report's export control is inside the connector
  iframe (icon button with aria-label 导出), then a menu offers
  复制内容 / 导出到 Markdown / 导出到 Word / 导出到 PDF. Clicking
  导出到 Markdown downloads `~/Downloads/deep-research-report (N).md`.

All element targeting is DOM/aria based; coordinates are computed at runtime
via getBoundingClientRect, never hardcoded. The Radix-style menu/row controls
need the full pointerdown → mousedown → pointerup → mouseup → click sequence
(CDP mouse events time out on this SPA; JS click alone may be ignored by
React for the small composer + button).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    def js(expression: str, target_id: str | None = None) -> Any: ...
    def iframe_target(name: str) -> str: ...
    def type_text(text: str) -> None: ...
    def press_key(key: str, modifiers: int = 0) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...
    def wait_for_load(timeout: float = 15.0) -> bool: ...


def _norm(s: str | None) -> str:
    return " ".join((s or "").replace("\xa0", " ").split())


def _pointer_click(js_expression: str) -> dict[str, Any]:
    """Run a JS snippet that dispatches the full pointer sequence on a target.

    The snippet must itself locate the element and return {found: True} after
    dispatching pointerdown/mousedown/pointerup/mouseup/click on it.
    """
    r = js(js_expression)
    if not r or not r.get("found"):
        raise RuntimeError(f"deep_research: element not found: {js_expression[:80]}...")
    return r


# ---------------------------------------------------------------------------
# Arm / disarm
# ---------------------------------------------------------------------------

def arm_deep_research() -> dict[str, Any]:
    """Arm Deep Research from the composer + menu; verify the composer pill.

    Returns {'armed': True, 'pill': <composer form text tail>}. Safe to call
    on a fresh home or existing conversation; does NOT send anything.
    """
    plus = js(r"""
    (() => {
      const plus = document.querySelector('[data-testid="composer-plus-btn"]');
      if (!plus || !plus.offsetParent) return {found: false};
      for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
        plus.dispatchEvent(new PointerEvent(type, {bubbles: true, cancelable: true,
          pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0}));
      }
      return {found: true};
    })()
    """)
    if not plus or not plus.get("found"):
        raise RuntimeError("arm_deep_research: composer + button not found")
    wait(1.8)
    row = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const leaves = [...document.querySelectorAll('span, div')].filter(el =>
        el.offsetParent && norm(el.innerText || '') === '深度研究' &&
        el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0);
      if (!leaves.length) return {found: false};
      const el = leaves.sort((a, b) => {
        const ar = a.getBoundingClientRect(), br = b.getBoundingClientRect();
        return (ar.width * ar.height) - (br.width * br.height);
      })[0];
      for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
        el.dispatchEvent(new PointerEvent(type, {bubbles: true, cancelable: true,
          pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0}));
      }
      return {found: true};
    })()
    """)
    if not row or not row.get("found"):
        raise RuntimeError("arm_deep_research: 深度研究 row not found in + menu")
    wait(2.0)
    check = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const form = document.querySelector('form[data-type="unified-composer"]');
      const txt = form ? norm(form.innerText || '') : '';
      return {pill: /深度研究/.test(txt), text: txt.slice(0, 120)};
    })()
    """)
    if not check or not check.get("pill"):
        raise RuntimeError("arm_deep_research: composer did not show 深度研究 pill")
    return {"armed": True, "pill": check.get("text", "")}


def disarm_deep_research() -> dict[str, Any]:
    """Remove the 深度研究 pill (click token then Backspace)."""
    token = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const form = document.querySelector('form[data-type="unified-composer"]');
      if (!form) return {found: false};
      const hits = [...form.querySelectorAll('span, div, button')].filter(el =>
        el.offsetParent && norm(el.innerText || el.textContent || '') === '深度研究');
      if (!hits.length) return {found: false};
      const interactive = hits.find(h => /cursor-t/.test((h.className || '').toString())) || hits[hits.length - 1];
      for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
        interactive.dispatchEvent(new PointerEvent(type, {bubbles: true, cancelable: true,
          pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0}));
      }
      return {found: true};
    })()
    """)
    if token and token.get("found"):
        wait(0.8)
        press_key("Backspace")
        wait(1.0)
    check = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const form = document.querySelector('form[data-type="unified-composer"]');
      const txt = form ? norm(form.innerText || '') : '';
      return {pill: /深度研究/.test(txt)};
    })()
    """)
    return {"disarmed": not (check or {}).get("pill", True)}


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

def _connector_target() -> str:
    """Resolve the Deep Research sandbox connector iframe targetId."""
    try:
        return iframe_target("connector-openai-deep-research")
    except Exception as e:
        raise RuntimeError(f"deep_research: connector iframe not found: {e}") from e


def deep_research_progress() -> dict[str, Any]:
    """Read Deep Research progress from the nested connector iframe.

    Returns {'state': 'idle'|'planning'|'running'|'done'|'unknown',
             'len': <chars>, 'text': <full text up to 2000 chars>}.

    'idle' means no connector iframe is mounted yet (nothing armed/sent).
    The main page body stays prompt-only for the whole run — never judge
    completion by main-page text length.
    """
    try:
        tid = _connector_target()
    except RuntimeError:
        return {"state": "idle", "len": 0, "text": ""}
    r = js(r"""
    (() => {
      const root = document.querySelector('iframe#root');
      if (!root) return {found: false};
      try {
        const doc = root.contentDocument;
        const txt = doc && doc.body ? doc.body.innerText || '' : '';
        return {found: true, text: txt};
      } catch (e) {
        return {found: false, error: String(e).slice(0, 120)};
      }
    })()
    """, target_id=tid) or {"found": False, "text": ""}
    txt = r.get("text") or ""
    norm = _norm(txt)
    if "研究完成" in norm and ("次引用" in norm or "次搜索" in norm) and "停止研究" not in norm:
        state = "done"
    elif "正在研究" in norm and "停止研究" in norm:
        state = "running"
    elif "计划生成倒计时" in norm or ("开始" in norm and "编辑" in norm):
        state = "planning"
    elif txt.strip():
        state = "unknown"
    else:
        state = "idle"
    return {"state": state, "len": len(txt), "text": txt[:2000]}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_deep_research_markdown(timeout: float = 30.0) -> str:
    """Export the finished report as Markdown from inside the connector iframe.

    Clicks the 导出 icon, then 导出到 Markdown, then waits for the newest
    `~/Downloads/deep-research-report (N).md` to become non-empty. Returns the
    absolute downloaded file path. Raises RuntimeError on timeout.
    """
    tid = _connector_target()
    clicked = js(r"""
    (() => {
      const root = document.querySelector('iframe#root');
      if (!root) return {found: false};
      try {
        const doc = root.contentDocument;
        if (!doc) return {found: false};
        const norm = s => (s || '').replace(/\s+/g, ' ').trim();
        const btns = [...doc.querySelectorAll('button')];
        const b = btns.find(el => el.offsetParent && /导出|export/i.test(
          norm(el.getAttribute('aria-label') || el.innerText || '')));
        if (!b) return {found: false};
        for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
          b.dispatchEvent(new PointerEvent(type, {bubbles: true, cancelable: true,
            pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0}));
        }
        return {found: true};
      } catch (e) {
        return {found: false, error: String(e).slice(0, 120)};
      }
    })()
    """, target_id=tid)
    if not clicked or not clicked.get("found"):
        raise RuntimeError("export_deep_research_markdown: 导出 button not found in connector iframe")
    wait(1.5)
    md = js(r"""
    (() => {
      const root = document.querySelector('iframe#root');
      if (!root) return {found: false};
      try {
        const doc = root.contentDocument;
        if (!doc) return {found: false};
        const norm = s => (s || '').replace(/\s+/g, ' ').trim();
        const b = [...doc.querySelectorAll('button')].find(el =>
          el.offsetParent && norm(el.innerText || el.textContent || '') === '导出到 Markdown');
        if (!b) return {found: false};
        b.click();
        return {found: true};
      } catch (e) {
        return {found: false, error: String(e).slice(0, 120)};
      }
    })()
    """, target_id=tid)
    if not md or not md.get("found"):
        raise RuntimeError("export_deep_research_markdown: 导出到 Markdown menu item not found")
    deadline = time.time() + timeout
    downloads = Path.home() / "Downloads"
    while time.time() < deadline:
        wait(2.0)
        candidates = sorted(
            downloads.glob("deep-research-report*.md"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        if candidates:
            newest = candidates[0]
            if newest.stat().st_size > 0:
                return str(newest)
    raise RuntimeError(f"export_deep_research_markdown: no non-empty report downloaded within {timeout}s")


# ---------------------------------------------------------------------------
# High-level runner
# ---------------------------------------------------------------------------

def run_deep_research(
    question: str,
    poll_interval: float = 8.0,
    timeout: float = 900.0,
    export: bool = True,
) -> dict[str, Any]:
    """Arm Deep Research, ask `question`, poll progress until done, optionally export.

    Returns {'state': 'done'|'unknown', 'question': ..., 'text': ..., 'export_path': ...}.
    This sends a real Deep Research request and consumes a Pro quota run.
    """
    arm_deep_research()
    type_text(question)
    wait(0.8)
    sent = js(r"""
    (() => {
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const form = document.querySelector('form[data-type="unified-composer"]');
      if (!form) return {found: false};
      const btn = [...form.querySelectorAll('button')].find(b =>
        ['发送提示', '发送提示词', 'Send prompt'].includes(norm(b.getAttribute('aria-label') || '')));
      if (!btn) return {found: false};
      for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
        btn.dispatchEvent(new PointerEvent(type, {bubbles: true, cancelable: true,
          pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0}));
      }
      return {found: true};
    })()
    """)
    if not sent or not sent.get("found"):
        raise RuntimeError("run_deep_research: send button not found after arming DR")
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        wait(poll_interval)
        prog = deep_research_progress()
        last = prog.get("text", "")
        if prog.get("state") == "done":
            result: dict[str, Any] = {"state": "done", "text": last}
            if export:
                result["export_path"] = export_deep_research_markdown()
            return result
    return {"state": "unknown", "text": last}


def run(script: str | None = None) -> None:
    """CLI entry for smoke tests. Pass a pipe-delimited action string, e.g.:

    run('arm_deep_research|deep_research_progress')
    """
    actions = (script or "arm_deep_research").split("|")
    for a in actions:
        parts = a.split(":")
        name, args = parts[0], parts[1:]
        print(f"== {name} {args} ==")
        if name == "arm_deep_research":
            print(arm_deep_research())
        elif name == "disarm_deep_research":
            print(disarm_deep_research())
        elif name == "deep_research_progress":
            print(deep_research_progress())
        elif name == "export_deep_research_markdown":
            print(export_deep_research_markdown())
        else:
            raise RuntimeError(f"run: unknown action {name}")


# This file is a library when loaded with exec(...) inside browser-harness.
# Call run() explicitly for the pipe-delimited smoke runner; do not auto-open
# ChatGPT merely because an agent loaded the domain skill.
