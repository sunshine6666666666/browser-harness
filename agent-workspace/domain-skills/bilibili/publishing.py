"""Bilibili creator upload flow for an attached Browser Harness tab.

The business gates mirror SAU's proven Bilibili CLI: verify identity, reject
exact-title duplicates, prepare one form, submit once, then read archive
evidence back from the creator API.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from PIL import Image

if TYPE_CHECKING:
    def activate_tab(target: Any) -> str: ...
    def click_at_xy(x: float, y: float, button: str = "left", clicks: int = 1) -> None: ...
    def current_tab() -> dict[str, Any]: ...
    def goto_url(url: str) -> None: ...
    def js(expression: str) -> Any: ...
    def page_info() -> dict[str, Any]: ...
    def type_text(text: str) -> None: ...
    def upload_file(selector: str, path: str) -> None: ...
    def wait(seconds: float = 1.0) -> None: ...
    def fill_input(selector: str, text: str, clear_first: bool = True, timeout: float = 0.0) -> None: ...
    def press_key(key: str, modifiers: int = 0) -> None: ...


UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"
MANAGER_URL = "https://member.bilibili.com/platform/upload-manager/article"
ARCHIVES_URL = "https://member.bilibili.com/x2/creative/web/archives/sp?pn=1&ps=20"


def _visible(selector: str) -> dict[str, Any] | None:
    return js("""(() => {
      const el = Array.from(document.querySelectorAll(%s)).find(node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      });
      if (!el) return null;
      el.scrollIntoView({block: 'center', inline: 'center'});
      const r = el.getBoundingClientRect();
      return {x: r.x + r.width / 2, y: r.y + r.height / 2,
              text: (el.innerText || el.textContent || '').trim()};
    })()""" % json.dumps(selector))


def _click_visible(selector: str) -> None:
    target = _visible(selector)
    if not target:
        raise RuntimeError("visible Bilibili control not found: %s" % selector)
    wait(0.2)
    target = _visible(selector)
    if not target:
        raise RuntimeError("visible Bilibili control moved away: %s" % selector)
    click_at_xy(target["x"], target["y"])


def _set_input(selector: str, value: str) -> None:
    ok = js("""(() => {
      const el = Array.from(document.querySelectorAll(%s)).find(node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      });
      if (!el) return false;
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(el, %s);
      el.dispatchEvent(new Event('input', {bubbles: true}));
      el.dispatchEvent(new Event('change', {bubbles: true}));
      el.dispatchEvent(new Event('blur', {bubbles: true}));
      return el.value === %s;
    })()""" % (json.dumps(selector), json.dumps(value), json.dumps(value)))
    if not ok:
        raise RuntimeError("could not set Bilibili field: %s" % selector)


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _wait_until(callback, timeout: float, message: str):
    deadline = time.monotonic() + timeout
    while True:
        result = callback()
        if result:
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(message)
        wait(min(0.2, remaining))


def _selected_tags() -> list[str]:
    return js("Array.from(document.querySelectorAll('.label-item-v2-content')).map(e => (e.innerText || '').trim()).filter(Boolean)") or []


def _visible_text(text: str, selector: str = "button,[role=button],[role=option],.bcc-option,.drop-list-item,.drop-list-v2-item,.menu-item,.button,.btn,[class*=button],[class*=btn],[class*=submit]") -> dict[str, Any] | None:
    return js("""(() => {
      const wanted = %s;
      const el = Array.from(document.querySelectorAll(%s)).find(node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && (node.innerText || node.textContent || '').trim() === wanted;
      });
      if (!el) return null;
      el.scrollIntoView({block: 'center', inline: 'center'});
      const r = el.getBoundingClientRect();
      return {x: r.x + r.width / 2, y: r.y + r.height / 2};
    })()""" % (json.dumps(text), json.dumps(selector)))


def _click_visible_text(text: str, selector: str = "button,[role=button],[role=option],.bcc-option,.drop-list-item,.drop-list-v2-item,.menu-item,.button,.btn,[class*=button],[class*=btn],[class*=submit]") -> None:
    target = _visible_text(text, selector)
    if not target:
        raise RuntimeError("visible Bilibili option not found: %s" % text)
    click_at_xy(target["x"], target["y"])


def _schedule_state() -> dict[str, Any]:
    return js("""(() => ({
      scheduled: document.querySelector('.time-switch-wrp .switch-container')?.classList.contains('switch-container-active') || false,
      schedule_date: document.querySelector('.date-picker-date .date-show')?.innerText.trim() || '',
      schedule_time: document.querySelector('.date-picker-timer .date-show')?.innerText.trim() || ''
    }))()""") or {"scheduled": False, "schedule_date": "", "schedule_time": ""}


def _cover_state() -> dict[str, Any]:
    return js("""(() => {
      const visible = node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      };
      const input = Array.from(document.querySelectorAll('input[type=file][data-bh-cover-input="1"]'))
        .find(node => node.files?.length || visible(node));
      const filename = input?.files?.[0]?.name || input?.value?.split('\\\\').pop() ||
        window.__bhCoverFilename || '';
      const image = Array.from(document.querySelectorAll(
        '.cover-wrp img,.cover-preview img,.cover-image img,.cover-slot img:not(.add-icon)'
      )).find(visible);
      return {
        cover_ready: !Boolean(document.querySelector('.cover-empty-pill')),
        custom_cover_set: Boolean(filename && !document.querySelector('.cover-empty-pill')),
        cover_filename: filename
      };
    })()""") or {"cover_ready": False, "custom_cover_set": False, "cover_filename": ""}


def _partition_value() -> str:
    return _normalized_text(js("""(() => {
      const visible = node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      };
      const node = Array.from(document.querySelectorAll('.video-human-type .select-item-cont')).find(visible);
      return node?.innerText || '';
    })()"""))


def submission_diagnostics() -> dict[str, Any]:
    evidence = js("""(() => {
      const visible = node => {
        const r = node.getBoundingClientRect();
        const style = getComputedStyle(node);
        return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
      };
      const text = node => (node.innerText || node.textContent || node.getAttribute('aria-label') ||
        node.getAttribute('placeholder') || node.getAttribute('title') || '').trim().replace(/\\s+/g, ' ');
      const unique = values => Array.from(new Set(values.filter(Boolean)));
      const collect = selector => unique(Array.from(document.querySelectorAll(selector)).filter(visible).map(text));
      const validationSelectors = '[role="alert"],[aria-invalid="true"],.el-form-item__error,.bcc-form-item-error,.error-text,.error-msg,.error-tip,.input-error-text,.section-title-warning';
      const toastSelectors = '.bcc-toast,.el-message,.videoup-notification-dialog,.notify-tips,[class*="toast"]';
      const modalSelectors = '.bcc-dialog__wrap,.el-message-box,.el-dialog__wrapper,[role="dialog"],.modal-content';
      const submit = Array.from(document.querySelectorAll('.submit-add,button')).find(node =>
        visible(node) && text(node) === '立即投稿');
      const important = unique((document.body?.innerText || '').split('\\n').map(value => value.trim())
        .filter(value => /必填|请选择|失败|错误|投稿|确认|稍后|至少|超过|违规|封面|分区|标签/.test(value)))
        .slice(0, 16).join(' | ').slice(0, 1200);
      return {
        url: location.href,
        validation_errors: collect(validationSelectors),
        toasts: collect(toastSelectors),
        modals: collect(modalSelectors),
        submit_button: submit ? {
          text: text(submit),
          disabled: Boolean(submit.disabled || submit.closest('[disabled]') ||
            /(^|[-_ ])disabled?($|[-_ ])/i.test(String(submit.className || '')) ||
            getComputedStyle(submit).pointerEvents === 'none'),
          aria_disabled: submit.getAttribute('aria-disabled') || submit.closest('[aria-disabled]')?.getAttribute('aria-disabled') || '',
          class_name: String(submit.className || '')
        } : null,
        page_text_summary: important
      };
    })()""") or {}
    evidence.setdefault("url", "")
    evidence.setdefault("validation_errors", [])
    evidence.setdefault("toasts", [])
    evidence.setdefault("modals", [])
    evidence.setdefault("submit_button", None)
    evidence.setdefault("page_text_summary", "")
    negative_pattern = r"失败|错误|请.*填写|请选择|不符合|无法|稍后重试"
    success_notices = [
        text for text in evidence["validation_errors"]
        if re.search(r"(?:上传|处理)(?:完成|成功)|已上传", text)
        and not re.search(negative_pattern, text)
    ]
    if success_notices:
        evidence["validation_errors"] = [
            text for text in evidence["validation_errors"] if text not in success_notices
        ]
        evidence["toasts"] = list(dict.fromkeys([*evidence["toasts"], *success_notices]))
    negative_toast = any(re.search(negative_pattern, text) for text in evidence["toasts"])
    positive_toast = any(re.search(r"成功|已提交|审核中|上传完成", text)
                         for text in evidence["toasts"])
    if evidence["validation_errors"]:
        reason = "form_validation_failed"
    elif evidence["modals"]:
        reason = "confirmation_required"
    elif negative_toast:
        reason = "platform_rejected"
    elif positive_toast:
        reason = "archive_evidence_delayed"
    elif evidence["url"].startswith(UPLOAD_URL) and evidence["submit_button"]:
        reason = "click_not_accepted"
    else:
        reason = "submission_unverified"
    evidence["reason"] = reason
    return evidence


def account_identity() -> dict[str, Any]:
    identity = js("""fetch('https://api.bilibili.com/x/web-interface/nav', {
      credentials: 'include'
    }).then(r => r.json()).then(x => ({
      code: x.code, mid: x.data && x.data.mid, uname: x.data && x.data.uname,
      isLogin: Boolean(x.data && x.data.isLogin)
    }))""")
    if not identity or identity.get("code") != 0 or not identity.get("isLogin"):
        raise RuntimeError("Bilibili session is not logged in")
    return identity


def archive_matches(title: str) -> list[dict[str, Any]]:
    return js("""fetch(%s, {credentials: 'include'})
      .then(r => r.json()).then(x => {
        if (x.code !== 0) throw new Error('archive API: ' + x.code + ' ' + x.message);
        return ((x.data && x.data.arc_audits) || []).map(row => row.Archive || row)
          .filter(row => String(row.title || '').trim() === %s)
          .map(row => ({aid: row.aid || row.id, bvid: row.bvid || '',
                        title: row.title || '', state: row.state ?? row.status,
                        dtime: row.dtime || row.pubtime || null,
                        cover_present: Boolean(row.cover || row.pic || row.cover_url)}));
      })""" % (json.dumps(ARCHIVES_URL), json.dumps(title.strip()))) or []


def require_identity(expected_mid: int, expected_name: str | None = None) -> dict[str, Any]:
    observed = account_identity()
    if int(observed["mid"]) != int(expected_mid):
        raise RuntimeError("blocked publish identity: expected mid=%s, observed mid=%s" %
                           (expected_mid, observed["mid"]))
    if expected_name and expected_name not in str(observed.get("uname") or ""):
        raise RuntimeError("blocked publish identity: expected name=%s, observed name=%s" %
                           (expected_name, observed.get("uname")))
    return observed


def prepare_upload(video_file: str, title: str, expected_mid: int,
                   expected_name: str | None = None, timeout: int = 600) -> dict[str, Any]:
    path = Path(video_file)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("video file is missing or empty: %s" % path)
    if not title.strip() or len(title) > 80:
        raise ValueError("Bilibili title must contain 1-80 characters")
    identity = require_identity(expected_mid, expected_name)
    if archive_matches(title):
        raise RuntimeError("Bilibili exact title already exists; refusing duplicate submission")
    if page_info().get("url") != UPLOAD_URL:
        goto_url(UPLOAD_URL)
        wait(3)
    if _visible_text("不用了", "*"):
        js("""(() => {
          const node = Array.from(document.querySelectorAll('*')).find(item => {
            const r = item.getBoundingClientRect();
            return r.width > 0 && r.height > 0 &&
              (item.innerText || item.textContent || '').trim() === '不用了';
          });
          if (node) node.click();
        })()""")
        wait(1)
    current_file = js("document.querySelector('input[type=file][accept*=\".mp4\"]')?.value || ''")
    if path.name not in current_file:
        upload_file('input[type=file][accept*=".mp4"]', str(path))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = js("document.body.innerText") or ""
        if "上传完成" in body:
            break
        wait(2)
    else:
        raise TimeoutError("Bilibili video upload did not reach 上传完成")
    _set_input('input[placeholder="请输入稿件标题"]', title)
    return {"identity": identity, "title": title, "video": str(path), "uploaded": True}


def choose_recommended_cover() -> None:
    if not js("Boolean(document.querySelector('.cover-empty-pill'))"):
        return
    js("document.querySelector('.cover-empty-pill').click()")
    wait(1)
    result = js("""(() => {
      const buttons = Array.from(document.querySelectorAll('.button.submit,button')).filter(b => {
        const r = b.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && (b.innerText || '').trim() === '完成';
      });
      const b = buttons[buttons.length - 1];
      if (!b) return false;
      b.click();
      return true;
    })()""")
    if not result:
        raise RuntimeError("Bilibili cover completion button not found")
    wait(1)
    if js("Boolean(document.querySelector('.cover-empty-pill'))"):
        raise RuntimeError("Bilibili recommended cover was not accepted")


def set_custom_cover(path: str, timeout: float = 30) -> dict[str, Any]:
    image_path = Path(path)
    if not image_path.is_file() or image_path.stat().st_size == 0:
        raise ValueError("Bilibili cover file is missing or empty: %s" % image_path)
    try:
        with Image.open(image_path) as image:
            width, height = image.size
    except (OSError, ValueError) as exc:
        raise ValueError("Bilibili cover file is not a readable image: %s" % image_path) from exc
    js("""(() => {
      const el = document.querySelector('.cover-empty-pill');
      if (!el) return false;
      el.click();
      return true;
    })()""")
    cover_input_selector = 'input[type=file][accept*="image/png"]'
    marked = _wait_until(lambda: js("""(() => {
      const input = document.querySelector('.cover-editor-panel-select input[type=file][accept*="image/png"]');
      if (!input) return false;
      input.setAttribute('data-bh-cover-input', '1');
      return true;
    })()"""), timeout, "Bilibili custom cover image input not found")
    if not marked:
        raise RuntimeError("Bilibili custom cover image input not found")
    upload_file('.cover-editor-panel-select ' + cover_input_selector, str(image_path))
    filename = _wait_until(
        lambda: js("document.querySelector('.cover-editor-panel-select input[type=file][accept*=\"image/png\"]')?.files?.[0]?.name || ''"),
        timeout,
        "Bilibili custom cover filename was not read back",
    )
    js("window.__bhCoverFilename = %s" % json.dumps(filename))
    completed = _wait_until(lambda: js("""(() => {
      const visible = node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      };
      const node = Array.from(document.querySelectorAll('*')).find(item =>
        visible(item) && (item.innerText || item.textContent || '').trim() === '完成'
      );
      if (!node) return false;
      node.click();
      return true;
    })()"""), timeout, "Bilibili cover completion button not found")
    if not completed:
        raise RuntimeError("Bilibili cover completion button not found")
    state = _wait_until(
        lambda: (lambda value: value if value.get("cover_ready") and value.get("custom_cover_set")
                 and value.get("cover_filename") == image_path.name else None)(_cover_state()),
        timeout,
        "Bilibili custom cover was not accepted",
    )
    return {"custom_cover_set": True, "filename": state["cover_filename"],
            "width": width, "height": height}


def set_tags(tags: list[str], timeout: float = 10) -> list[str]:
    normalized = []
    for tag in tags:
        value = _normalized_text(tag)
        if not value:
            raise ValueError("Bilibili tags cannot contain blank entries")
        if value not in normalized:
            normalized.append(value)
    if not normalized:
        raise ValueError("Bilibili requires at least one tag")
    selector = 'input[placeholder="按回车键Enter创建标签"]'
    for tag in normalized:
        if tag in _selected_tags():
            continue
        recommended = js("""(() => {
          const visible = node => {
            const r = node.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          };
          const node = Array.from(document.querySelectorAll('.hot-tag-container:not(.hot-tag-container-selected)'))
            .find(item => visible(item) && (item.innerText || item.textContent || '').trim() === %s);
          if (!node) return false;
          node.click();
          return true;
        })()""" % json.dumps(tag))
        if recommended:
            try:
                _wait_until(lambda: tag in _selected_tags(), timeout,
                            "Bilibili recommended tag was not accepted: %s" % tag)
                continue
            except TimeoutError as exc:
                raise RuntimeError("Bilibili recommended tag was not accepted: %s; observed=%s" %
                                   (tag, _selected_tags())) from exc
        focused = js("""(() => {
          const input = Array.from(document.querySelectorAll(%s)).find(node => {
            const r = node.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          });
          if (!input) return false;
          input.focus();
          return true;
        })()""" % json.dumps(selector))
        if not focused:
            raise RuntimeError("visible Bilibili tag input not found")
        type_text(tag)
        js("""(() => {
          const el = Array.from(document.querySelectorAll(%s)).find(node => {
            const r = node.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          });
          if (el) {
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
          }
        })()""" % json.dumps(selector))
        press_key("Enter")
        try:
            _wait_until(lambda: tag in _selected_tags(), timeout,
                        "Bilibili tag was not accepted: %s" % tag)
        except TimeoutError as exc:
            raise RuntimeError("Bilibili tag was not accepted: %s; observed=%s" %
                               (tag, _selected_tags())) from exc
    return _selected_tags()


def set_declaration(label: str = "内容无需标注") -> None:
    current = _normalized_text(js("""(() => {
      const input = Array.from(document.querySelectorAll('input[placeholder*="创作声明"]')).find(node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      });
      return input?.value || '';
    })()"""))
    if current == label:
        return
    _click_visible('input[placeholder*="创作声明"]')
    _click_visible_text(label, ".bcc-option,[role=option],button,.drop-list-v2-item")
    observed = _normalized_text(js("""(() => {
      const input = Array.from(document.querySelectorAll('input[placeholder*="创作声明"]')).find(node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      });
      return input?.value || '';
    })()"""))
    if observed != label:
        raise RuntimeError("Bilibili declaration was not accepted: %s" % observed)


def set_partition(name: str, timeout: float = 10) -> str:
    requested = _normalized_text(name)
    if not requested:
        raise ValueError("Bilibili partition name cannot be blank")
    opened = js("""(() => {
      const node = Array.from(document.querySelectorAll('.video-human-type .select-item-cont')).find(item => {
        const r = item.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      });
      if (!node) return false;
      node.click();
      return true;
    })()""")
    if not opened:
        raise RuntimeError("visible Bilibili partition selector not found")
    _wait_until(lambda: _visible_text(requested), timeout,
                "Bilibili partition option was not found: %s" % requested)
    selected = js("""(() => {
      const visible = node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      };
      const node = Array.from(document.querySelectorAll('.drop-list-v2-item .item-cont-main,.drop-list-v2-item,[role=option],.drop-list-item'))
        .find(item => visible(item) && (item.innerText || item.textContent || '').trim() === %s);
      if (!node) return false;
      node.click();
      return true;
    })()""" % json.dumps(requested))
    if not selected:
        raise RuntimeError("Bilibili partition option was not found: %s" % requested)
    try:
        return _wait_until(lambda: _partition_value() if _partition_value() == requested else None,
                           timeout, "Bilibili partition was not accepted: %s" % requested)
    except TimeoutError:
        second = _visible_text(requested)
        if second:
            click_at_xy(second["x"], second["y"])
        return _wait_until(lambda: _partition_value() if _partition_value() == requested else None,
                           timeout, "Bilibili partition was not accepted: requested=%s observed=%s" %
                           (requested, _partition_value()))


def set_description(text: str, timeout: float = 10) -> str:
    requested = _normalized_text(text)
    ok = js("""(() => {
      const el = Array.from(document.querySelectorAll('.ql-editor[contenteditable="true"]')).find(node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      });
      if (!el) return false;
      el.focus();
      el.innerText = %s;
      for (const type of ['beforeinput', 'input', 'change', 'blur']) {
        el.dispatchEvent(new Event(type, {bubbles: true}));
      }
      return true;
    })()""" % json.dumps(requested))
    if not ok:
        raise RuntimeError("visible Bilibili description editor not found")
    _wait_until(
        lambda: _normalized_text(js("document.querySelector('.ql-editor[contenteditable=\"true\"]')?.innerText || ''")) == requested,
        timeout,
        "Bilibili description was not accepted",
    )
    return _normalized_text(js("document.querySelector('.ql-editor[contenteditable=\"true\"]')?.innerText || ''"))


def _set_schedule_time_value(hour: int, minute: int) -> str:
    active = js("document.querySelector('.time-switch-wrp .switch-container')?.classList.contains('switch-container-active')")
    if not active:
        js("document.querySelector('.time-switch-wrp .switch-container').click()")
        wait(0.4)
    picker_open = js("""(() => {
      const el = document.querySelector('.time-picker-container');
      if (!el) return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    })()""")
    if not picker_open:
        js("document.querySelector('.date-picker-timer').click()")
        wait(0.2)
    ok = js("""(() => {
      const panels = document.querySelectorAll('.time-picker-panel-select-wrp');
      const pick = (panel, value) => {
        const el = Array.from(panel.querySelectorAll('.time-picker-panel-select-item'))
          .find(x => x.textContent.trim() === value && !x.classList.contains('time-select-disabled'));
        if (!el) return false;
        el.click();
        return true;
      };
      return panels.length >= 2 && pick(panels[0], %s);
    })()""" % json.dumps(f"{hour:02d}"))
    wait(0.2)
    ok = bool(ok) and bool(js("""(() => {
      const panels = document.querySelectorAll('.time-picker-panel-select-wrp');
      if (panels.length < 2) return false;
      const el = Array.from(panels[1].querySelectorAll('.time-picker-panel-select-item'))
        .find(x => x.textContent.trim() === %s && !x.classList.contains('time-select-disabled'));
      if (!el) return false;
      el.click();
      return true;
    })()""" % json.dumps(f"{minute:02d}")))
    wait(0.3)
    observed = js("document.querySelector('.date-picker-timer .date-show')?.innerText.trim() || ''")
    expected = f"{hour:02d}:{minute:02d}"
    if not ok or observed != expected:
        raise RuntimeError("Bilibili schedule time was not accepted: %s" % observed)
    return expected


def set_schedule_datetime(value: str, timeout: float = 15) -> dict[str, str]:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", value or ""):
        raise ValueError("Bilibili schedule must use YYYY-MM-DD HH:MM")
    try:
        target = datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("Bilibili schedule must use YYYY-MM-DD HH:MM") from exc
    if target.minute % 5:
        raise ValueError("Bilibili schedule minute must be divisible by five")
    now = datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
    if target < now + timedelta(minutes=5):
        raise ValueError("Bilibili schedule must be at least five minutes in the future")
    if target > now + timedelta(days=15):
        raise ValueError("Bilibili schedule cannot be more than fifteen days ahead")
    date, clock = value.split(" ", 1)
    active = js("document.querySelector('.time-switch-wrp .switch-container')?.classList.contains('switch-container-active')")
    if not active:
        js("document.querySelector('.time-switch-wrp .switch-container')?.click()")
        wait(0.4)
    date_set = js("""(() => {
      const input = Array.from(document.querySelectorAll('input[type=date],.date-picker-date input')).find(node => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      });
      if (!input) return false;
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(input, %s);
      input.dispatchEvent(new Event('input', {bubbles: true}));
      input.dispatchEvent(new Event('change', {bubbles: true}));
      return true;
    })()""" % json.dumps(date))
    if not date_set:
        opened = js("""(() => {
          const node = document.querySelector('.date-picker-date');
          if (!node) return false;
          node.click();
          return true;
        })()""")
        if not opened:
            raise RuntimeError("Bilibili schedule date control not found")
        wait(0.3)
        selected = js("""(() => {
          const day = %s;
          const node = Array.from(document.querySelectorAll('.date-picker-body-item.date-item'))
            .find(item => item.getBoundingClientRect().width > 0 && item.innerText.trim() === day);
          if (!node) return false;
          node.click();
          return true;
        })()""" % json.dumps(str(target.day)))
        if not selected:
            _click_visible_text(str(target.day), ".date-picker-body-item.date-item,button,[role=option],.calendar-day,.date-picker-panel *")
    hour, minute = map(int, clock.split(":", 1))
    _set_schedule_time_value(hour, minute)
    state = _wait_until(
        lambda: (lambda current: current if current.get("scheduled") and
                 current.get("schedule_date") == date and current.get("schedule_time") == clock else None)(_schedule_state()),
        timeout,
        "Bilibili schedule readback did not match: %s" % value,
    )
    return {"schedule_date": state["schedule_date"], "schedule_time": state["schedule_time"],
            "schedule": "%s %s" % (state["schedule_date"], state["schedule_time"])}


def set_schedule_time(hour: int, minute: int) -> str:
    if not 0 <= hour <= 23 or minute not in range(0, 60, 5):
        raise ValueError("Bilibili schedule requires hour 0-23 and a 5-minute minute value")
    value = "%s %02d:%02d" % (datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d"), hour, minute)
    return set_schedule_datetime(value)["schedule_time"]


def submission_snapshot() -> dict[str, Any]:
    cover = _cover_state()
    schedule = _schedule_state()
    diagnostics = submission_diagnostics()
    submit = diagnostics.get("submit_button") or {}
    return {
        "title": _normalized_text(js("document.querySelector('input[placeholder=\"请输入稿件标题\"]')?.value || ''")),
        "cover_ready": bool(cover.get("cover_ready")),
        "custom_cover_set": bool(cover.get("custom_cover_set")),
        "cover_filename": cover.get("cover_filename", ""),
        "partition": _partition_value(),
        "description": _normalized_text(js("document.querySelector('.ql-editor[contenteditable=\"true\"]')?.innerText || ''")),
        "tags": _selected_tags(),
        "declaration": _normalized_text(js("document.querySelector('input[placeholder*=\"创作声明\"]')?.value || ''")),
        "scheduled": bool(schedule.get("scheduled")),
        "schedule_date": schedule.get("schedule_date", ""),
        "schedule_time": schedule.get("schedule_time", ""),
        "submit_text": submit.get("text", ""),
        "submit_enabled": not bool(submit.get("disabled") or submit.get("aria_disabled") == "true"),
        "validation_errors": diagnostics.get("validation_errors", []),
    }


def manager_evidence(title: str, expected_schedule: str | None = None,
                     strict: bool = True, attempts: int = 3) -> dict[str, Any]:
    if attempts < 1:
        raise ValueError("manager evidence attempts must be at least one")
    expected_title = title.strip()
    observed_title = ""
    evidence = None
    for list_loads in range(1, attempts + 1):
        goto_url(MANAGER_URL)
        wait(4)
        evidence = js("""(() => {
          const card = document.querySelector('.article-card.v2');
          if (!card) return null;
          return {title: (card.querySelector('a.name')?.innerText || '').trim(),
                  href: card.querySelector('a.name')?.href || '',
                  text: (card.innerText || '').trim()};
        })()""")
        observed_title = (evidence or {}).get("title", "")
        if observed_title == expected_title:
            break
    else:
        raise RuntimeError(
            "Bilibili creator manager latest record did not match exact title "
            "after %s list loads: expected=%r observed=%r" %
            (attempts, expected_title, observed_title)
        )
    evidence["latest"] = True
    evidence["list_loads"] = list_loads
    if expected_schedule:
        date, clock = expected_schedule.split(" ", 1)
        chinese = "%s年%s月%s日 %s" % (*date.split("-"), clock)
        evidence["schedule_match"] = "定时发布" in evidence["text"] and chinese in evidence["text"]
        evidence["expected_schedule"] = expected_schedule
        if strict and not evidence["schedule_match"]:
            raise RuntimeError("Bilibili manager schedule mismatch: %s" % evidence["text"])
    else:
        evidence["schedule_match"] = True
    return evidence


def submit_once(title: str, expected_mid: int, expected_name: str | None = None,
                expected_schedule: str | None = None, timeout: int = 600) -> dict[str, Any]:
    identity = require_identity(expected_mid, expected_name)
    existing = archive_matches(title)
    if len(existing) > 1:
        raise RuntimeError("Bilibili archive title matched multiple records")
    if existing:
        raise RuntimeError("Bilibili exact title already exists; refusing duplicate submission")
    first_snapshot = submission_snapshot()
    wait(2)
    snapshot = submission_snapshot()
    if first_snapshot != snapshot:
        raise RuntimeError("Bilibili preflight was not stable: first=%s second=%s" %
                           (first_snapshot, snapshot))
    observed_schedule = "%s %s" % (snapshot.get("schedule_date"), snapshot.get("schedule_time"))
    if (snapshot.get("title") != title or not snapshot.get("cover_ready") or
            not snapshot.get("custom_cover_set") or not snapshot.get("tags") or
            not snapshot.get("partition") or not snapshot.get("description") or
            not snapshot.get("declaration") or not snapshot.get("scheduled") or
            snapshot.get("submit_text") != "立即投稿" or not snapshot.get("submit_enabled") or
            snapshot.get("validation_errors") or
            (expected_schedule and observed_schedule != expected_schedule)):
        raise RuntimeError("Bilibili preflight failed: %s" % snapshot)
    js("document.querySelector('input[placeholder=\"请输入稿件标题\"]')?.click()")
    wait(0.3)
    picker_open = js("""(() => {
      const el = document.querySelector('.time-picker-container');
      if (!el) return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    })()""")
    if picker_open:
        js("document.querySelector('.date-picker-timer')?.click()")
        wait(0.3)
    activate_tab(current_tab())
    _click_visible('.submit-add')
    clicked = True
    wait(0.5)
    diagnostics = submission_diagnostics()
    if diagnostics["reason"] in {"form_validation_failed", "confirmation_required", "platform_rejected"}:
        return {"identity": identity, "submitted": False, "status": "not_accepted",
                "reason": diagnostics["reason"], "diagnostics": diagnostics,
                "submit_clicks": int(clicked)}
    deadline = time.monotonic() + timeout
    archive = None
    last_manager_error = ""
    manager_loads = 0
    while time.monotonic() < deadline:
        matches = archive_matches(title)
        if len(matches) == 1:
            archive = matches[0]
        elif len(matches) > 1:
            raise RuntimeError("Bilibili archive title matched multiple records")
        if manager_loads < 3:
            manager_loads += 1
            try:
                manager = manager_evidence(
                    title, expected_schedule, strict=False, attempts=1
                )
            except RuntimeError as exc:
                last_manager_error = str(exc)
            else:
                if manager.get("schedule_match"):
                    result = {
                        "identity": identity, "submitted": True, "status": "verified",
                        "manager": manager, "verification_source": "manager_latest",
                        "submit_clicks": int(clicked),
                    }
                    if archive is not None:
                        result["archive"] = archive
                    return result
                last_manager_error = (
                    manager.get("text") or
                    "Bilibili manager schedule evidence is not ready"
                )
        diagnostics = submission_diagnostics()
        if diagnostics["reason"] in {
                "form_validation_failed", "confirmation_required", "platform_rejected"}:
            return {"identity": identity, "submitted": False, "status": "not_accepted",
                    "reason": diagnostics["reason"], "diagnostics": diagnostics,
                    "submit_clicks": int(clicked)}
        wait(min(3, max(0, deadline - time.monotonic())))
    if archive is not None:
        return {"identity": identity, "submitted": True,
                "status": "accepted_but_schedule_unverified", "archive": archive,
                "expected_schedule": expected_schedule, "manager_error": last_manager_error,
                "submit_clicks": int(clicked)}
    return {"identity": identity, "submitted": False, "status": "not_accepted",
            "reason": diagnostics["reason"], "diagnostics": diagnostics,
            "submit_clicks": int(clicked)}


def _self_check() -> None:
    assert UPLOAD_URL.startswith("https://member.bilibili.com/")
    assert len("巴黎奥运选手赛后身体不适") <= 80


_self_check()
