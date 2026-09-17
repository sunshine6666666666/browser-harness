"""Ximalaya (喜马拉雅) audio publishing flow for an attached Browser Harness tab.

Loaded like every Domain Skill helper module:

    exec(open("/abs/path/agent-workspace/domain-skills/ximalaya/publishing.py").read())

Browser Harness must be attached to a tab showing
`https://www.ximalaya.com/reform-upload/page/webCenter/upload` (open this URL
directly; the studio shell at https://studio.ximalaya.com/upload embeds the same
flow inside a cross-origin iframe that direct navigation avoids).

Safety model: login gates before every mutation, exact-target and exact-title
duplicate prevention, local-file validation, stable
pre-submit snapshots, ONE submit activation with the click fact recorded,
read-only post-submit reconciliation, and deletion guarded to records this
module created. Unknown submit/delete results are read-only recovery states,
never retry invitations.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from PIL import Image

if TYPE_CHECKING:
    def cdp(method: str, **params: Any) -> Any: ...
    def click_at_xy(x: float, y: float) -> None: ...
    def goto_url(url: str) -> Any: ...
    def js(expression: str, target_id: str | None = None) -> Any: ...
    def page_info() -> dict[str, Any]: ...
    def upload_file(selector: str, path: str) -> None: ...
    def wait(seconds: float) -> None: ...

UPLOAD_URL = "https://www.ximalaya.com/reform-upload/page/webCenter/upload"
TIME_PUBLISH_URL = "https://www.ximalaya.com/reform-upload/page/time-publish"
SOUND_MANAGE_URL = "https://www.ximalaya.com/reform-upload/page/sound/manage/"
EDIT_URL = "https://www.ximalaya.com/reform-upload/page/sound/edit/{}"
SCHEDULED_LIST_API = "https://www.ximalaya.com/reform-upload/scheduledPublish/list"
TRACKS_LIST_API = "https://www.ximalaya.com/reform-upload/manage/album/tracks"
TRACK_DETAIL_API = "https://www.ximalaya.com/revision/track/simple"
EDIT_INFO_API = "https://www.ximalaya.com/reform-upload/anchorTrack/edit"
TRACK_DELETE_API = "https://www.ximalaya.com/reform-upload/manage/album/track/delete"
ALBUMS_API = "https://www.ximalaya.com/reform-upload/album/choose"
CURRENT_USER_API = "https://www.ximalaya.com/anchor-works-web/common/getCurrentUser"
PLAYBACK_QUALITY_API = "https://mobile.ximalaya.com/mobile-playpage/playpage/track/quality"

TITLE_MAX = 40
TITLE_UNIT = "utf16_code_units"
AUDIO_EXTENSIONS = {".aiff", ".aif", ".mp3", ".wma", ".wav", ".flac",
                    ".ogg", ".mp2", ".aac", ".amr", ".m4a"}
AUDIO_MIN_BYTES = 1_048_576
AUDIO_MAX_BYTES = 1_073_741_824
COVER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
COVER_MIN_EDGE = 500
COVER_MAX_BYTES = 10_485_760
SCHEDULE_MIN_LEAD_MINUTES = 120
SCHEDULE_TIMEZONE = "Asia/Shanghai"
PUBLISH_MODES = ("immediate", "scheduled")
TRACK_EVIDENCE_MAX_PAGES = 20
DURATION_TOLERANCE_SECONDS = 1.0
REPLACEMENT_INPUT_SELECTOR = (
    'input[type=file].webuploader-element-invisible[accept*=".M4A"]'
)
FFPROBE = "/opt/homebrew/bin/ffprobe"

_CREATED_BY = "ximalaya_domain_skill"


# ------------------------------------------------------------------ helpers

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _title_units(text: str) -> int:
    """Title counter counts UTF-16 code units (CJK=1, ASCII=1, emoji=2)."""
    return len(text.encode("utf-16-le")) // 2


def _wait_until(callback, timeout: float, message: str):
    deadline = time.monotonic() + timeout
    while True:
        result = callback()
        if result:
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(message)
        wait(min(0.5, max(0.1, remaining)))


def _api_js(url: str) -> str:
    return ("(async () => { try { const r = await fetch(%s, {credentials: 'include'});"
            " const t = await r.text();"
            " return JSON.stringify({status: r.status, body: t});"
            " } catch (e) { return JSON.stringify({status: 0, err: String(e)}); }"
            " })()" % _json(url))


def _parse_api_response(raw: Any, context: str) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise RuntimeError("ximalaya %s transport failed: %r" % (context, raw))
    try:
        wrapped = json.loads(raw)
    except ValueError as exc:
        raise RuntimeError("ximalaya %s transport error: %s" % (context, exc))
    if wrapped.get("err"):
        raise RuntimeError("ximalaya %s request failed: %s" % (context, wrapped["err"]))
    if wrapped.get("status") != 200:
        raise RuntimeError("ximalaya %s http %s" % (context, wrapped.get("status")))
    try:
        parsed = json.loads(wrapped.get("body") or "{}")
    except ValueError as exc:
        raise RuntimeError("ximalaya %s response was not JSON: %s" % (context, exc)) from exc
    if parsed.get("ret") not in (0, 200, None) or parsed.get("success") is False:
        raise RuntimeError("ximalaya %s error: %s" % (context, parsed.get("msg")))
    data = parsed.get("data")
    return data if isinstance(data, dict) else parsed


def _api_get(url: str, context: str) -> dict[str, Any]:
    return _parse_api_response(js(_api_js(url)), context)


def _api_post(url: str, payload: dict[str, Any], context: str) -> dict[str, Any]:
    raw = js("""(async () => { try {
      const r = await fetch(%s, {method: 'POST', credentials: 'include',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(%s)});
      return JSON.stringify({status: r.status, body: await r.text()});
    } catch (e) { return JSON.stringify({status: 0, err: String(e)}); } })()"""
            % (_json(url), _json(payload)))
    return _parse_api_response(raw, context)


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
    })()""" % _json(selector))


def _click_visible(selector: str) -> dict[str, Any]:
    target = _visible(selector)
    if not target:
        raise RuntimeError("visible ximalaya control not found: %s" % selector)
    wait(0.2)
    target = _visible(selector)
    if not target:
        raise RuntimeError("visible ximalaya control moved away: %s" % selector)
    click_at_xy(target["x"], target["y"])
    return target


# ------------------------------------------------------------------ identity

def account_identity() -> dict[str, Any]:
    identity = _api_get(CURRENT_USER_API, "currentUser")
    uid = identity.get("uid")
    if not uid:
        raise RuntimeError("auth_required: ximalaya session is not logged in")
    return {"uid": int(uid), "name": str(identity.get("nickname") or ""), "logged_in": True}


def require_identity(expected_uid: int | None = None,
                     expected_name: str | None = None) -> dict[str, Any]:
    """Compatibility gate: require login, but do not compare account labels."""
    return account_identity()


ALBUM_CREATE_URL = "https://www.ximalaya.com/anchor-activity-web/anchor/albumMgr#/album/createFree"
ALBUM_TITLE_MAX = 25

_ALBUM_MODEL_JS = """(() => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const btn = [...document.querySelectorAll('button')].find(
    e => e.offsetParent && norm(e.innerText) === '确认创建');
  if (!btn) return '';
  const fkey = Object.keys(btn).find(k => k.indexOf('__reactInternalInstance') === 0);
  let f = btn[fkey];
  for (let d = 0; d < 12 && f; d++) {
    try {
      if (f.stateNode && f.stateNode.refs && f.stateNode.refs.$form) {
        const form = f.stateNode.refs.$form;
        const m = form.getVaildModel ? form.getVaildModel() : form.props.model;
        return JSON.stringify(m);
      }
    } catch (e) {}
    f = f.return;
  }
  return '';
})()"""


def _album_model() -> dict[str, Any]:
    """Read the album create form model (title, categoryId, image, tags...)."""
    raw = js(_ALBUM_MODEL_JS)
    if not raw:
        raise RuntimeError("ximalaya album create page not ready: form model unreadable")
    return json.loads(raw)


def _album_react_set(selector: str, value: str) -> None:
    """Set a React-controlled text input by invoking its onChange with the field name.

    Discovered 2026-09-17: the album title/selling-point inputs ignore native
    value setters and synthetic input events (model stays empty, submit
    validation reports the field missing). Calling the React onChange prop
    with ``{target: {name, value}}`` updates the model.
    """
    ok = js("((selector, value) => {\n"
            "  const el = document.querySelector(selector);\n"
            "  if (!el) return 'missing';\n"
            "  const hkey = Object.keys(el).find(k => k.indexOf('__reactEventHandlers') === 0);\n"
            "  const fn = hkey && el[hkey].onChange;\n"
            "  if (typeof fn !== 'function') return 'no-handler';\n"
            "  fn({target: {name: el.name, value: value}});\n"
            "  return 'ok';\n"
            "})(" + _json(selector) + ", " + _json(value) + ")")
    if ok != "ok":
        raise RuntimeError("ximalaya album react input not set: %s -> %s" % (selector, ok))


def _album_validate_field(prop: str, timeout: float = 10) -> str | None:
    """Run the form's per-field validator; return the error message or None."""
    js("((prop) => {\n"
       "  const norm = s => (s || '').replace(/\\\\s+/g, ' ').trim();\n"
       "  const btn = [...document.querySelectorAll('button')].find(\n"
       "    e => e.offsetParent && norm(e.innerText) === '确认创建');\n"
       "  const fkey = Object.keys(btn).find(k => k.indexOf('__reactInternalInstance') === 0);\n"
       "  let f = btn[fkey];\n"
       "  for (let d = 0; d < 12 && f; d++) {\n"
       "    try {\n"
       "      if (f.stateNode && f.stateNode.refs && f.stateNode.refs.$form) {\n"
       "        f.stateNode.refs.$form.validateField(prop, err => {\n"
       "          window.__album_field_result = err ? JSON.stringify(err).slice(0, 200) : 'OK';\n"
       "        });\n"
       "        return 'validating:' + prop;\n"
       "      }\n"
       "    } catch (e) {}\n"
       "    f = f.return;\n"
       "  }\n"
       "  window.__album_field_result = 'NO_FORM';\n"
       "  return 'no-form';\n"
       "})(" + _json(prop) + ")")
    return _wait_until(lambda: (lambda v: v if v != "pending" else None)(
        js("window.__album_field_result") or ""), timeout,
        "ximalaya album field validation never resolved: %s" % prop)


def _album_pick_tags(names: list[str], timeout: float = 10) -> dict[str, bool]:
    """Stepwise tag picking: click one tag, settle, verify checked, retry.

    The tag block is a React cascade (内容分类 -> 二级组 -> dynamic leaf rows):
    dependent rows only render after the parent tag is checked, and a single
    JS pass that clicks every tag back-to-back gets swallowed by re-renders.
    Live-verified 2026-09-17: one click per tag + ~2s settle + checked-readback
    is reliable; retry up to 4 attempts per tag before giving up.
    """
    out: dict[str, bool] = {}
    for name in names:
        wanted = _normalized_text(name)
        ok = False
        for _ in range(4):
            js("((name) => {\n"
               "  const norm = s => (s || '').replace(/\\\\s+/g, ' ').trim();\n"
               "  const wrap = document.querySelector('.album-tags1');\n"
               "  if (!wrap) return false;\n"
               "  for (const t of wrap.querySelectorAll('.xui-tag1')) {\n"
               "    if (norm(t.innerText) === name) { t.click(); return true; }\n"
               "  }\n"
               "  return false;\n"
               "})(" + _json(wanted) + ")")
            wait(2.0)
            ok = bool(js("((name) => {\n"
                         "  const norm = s => (s || '').replace(/\\\\s+/g, ' ').trim();\n"
                         "  const wrap = document.querySelector('.album-tags1');\n"
                         "  if (!wrap) return false;\n"
                         "  for (const t of wrap.querySelectorAll('.xui-tag1')) {\n"
                         "    if (norm(t.innerText) === name)"
                         " return /checked/.test(t.className);\n"
                         "  }\n"
                         "  return false;\n"
                         "})(" + _json(wanted) + ")"))
            if ok:
                break
        out[wanted] = ok
    return out


# ------------------------------------------------------------------ facts

def publishing_constraints() -> dict[str, Any]:
    return {
        "verified_date": "2026-09-07",
        "audio": {
            "extensions": sorted(AUDIO_EXTENSIONS),
            "formats_count": 11,
            "min_bytes": AUDIO_MIN_BYTES,
            "max_bytes": AUDIO_MAX_BYTES,
            "size_evidence": "declared_and_correlated",
            "bitrate": ">=64kbps recommended; below is accepted with exposure-limit warning",
            "bitrate_evidence": "enforced_as_warning",
        },
        "title": {"max": TITLE_MAX, "unit": TITLE_UNIT, "evidence": "enforced"},
        "cover": {
            "extensions": sorted(COVER_EXTENSIONS),
            "min_edge": COVER_MIN_EDGE,
            "max_bytes": COVER_MAX_BYTES,
            "min_recommend_edge": 1000,
            "crop_semantics": ("platform center-crops a 1280x720 source to 1000x1000;"
                               " a 1080x1080 source is stored verbatim"),
            "evidence": "accepted",
        },
        "schedule": {
            "timezone": SCHEDULE_TIMEZONE,
            "min_lead_minutes": SCHEDULE_MIN_LEAD_MINUTES,
            "min_lead_evidence": "enforced",
            "max_horizon": "not enforced client-side; picker navigable to 2028-12; server horizon unproven",
            "max_horizon_evidence": "client_observed_server_unknown",
            "granularity": "minute (seconds fixed 00)",
            "granularity_evidence": "enforced",
            "input_format": "YYYY-MM-DD HH:MM",
            "display_format": "YYYY-MM-DD HH:MM:00",
        },
        "required_fields": ["节目标题", "分类", "节目类型"],
        "default_fields": {"节目类型": "免费节目", "是否AI合成": "否",
                           "权限设置": "公开(value=2)", "知识产权承诺": "checked"},
        "upload_form_url": UPLOAD_URL,
    }


def list_albums() -> list[dict[str, Any]]:
    data = _api_get(ALBUMS_API + "?pageSize=50", "album list")
    return [{
        "album_id": str(item["albumId"]),
        "title": item.get("title") or "",
        "custom_title": item.get("customTitle") or "",
        "category_id": item.get("categoryId"),
        "price_type_id": item.get("priceTypeId"),
        "can_add_audio": item.get("priceTypeId") in (0, None)
                         and item.get("uploadSource") in (0, None),
    } for item in data.get("infos") or []]


def _album_tracks(album_id: str, page_size: int = 50) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    for page in range(1, TRACK_EVIDENCE_MAX_PAGES + 1):
        data = _api_get("%s?albumId=%s&page=%s&pageSize=%s&order=DESC&state=1" %
                        (TRACKS_LIST_API, album_id, page, page_size), "album tracks")
        infos = data.get("infos") or []
        tracks.extend(infos)
        total = int(data.get("totalSize") or 0)
        if (not infos or (total and page * page_size >= total)
                or (not total and len(infos) < page_size)):
            break
    return tracks


def list_album_tracks(album_id: str, expected_uid: int | None = None,
                      expected_name: str | None = None,
                      limit: int | None = None) -> list[dict[str, Any]]:
    album_id = _decimal_id(album_id, "album_id")
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0):
        raise ValueError("ximalaya track limit must be a positive integer")
    identity = require_identity(expected_uid, expected_name)
    raw_tracks = _album_tracks(album_id)
    if not raw_tracks:
        raise RuntimeError("ximalaya album %s has no tracks" % album_id)

    album_total = len(raw_tracks)
    all_track_ids: set[str] = set()
    for item in raw_tracks:
        track_id = _decimal_id(str(item.get("trackId") or ""), "track_id")
        if track_id in all_track_ids:
            raise RuntimeError("ximalaya album %s returned duplicate trackId %s" %
                               (album_id, track_id))
        all_track_ids.add(track_id)
    result: list[dict[str, Any]] = []
    for offset, item in enumerate(raw_tracks[:limit]):
        track_id = _decimal_id(str(item.get("trackId") or ""), "track_id")
        item_album_id = str(item.get("albumId") or album_id)
        if item_album_id != album_id:
            raise RuntimeError("ximalaya album track %s belongs to album %s" %
                               (track_id, item_album_id))
        title = _normalized_text(item.get("title"))
        if not title:
            raise RuntimeError("ximalaya track %s has no title" % track_id)
        observed_uid = str(item.get("anchorId") or item.get("anchorUid") or
                           item.get("accountUid") or item.get("uid") or identity["uid"])
        duration = item.get("duration") or item.get("durationSeconds") or 0
        try:
            duration_seconds = float(duration)
        except (TypeError, ValueError):
            duration_seconds = 0.0
        episode = (item.get("episodeNumber") or item.get("episodeNo") or
                   item.get("index") or album_total - offset)
        try:
            episode_number = int(episode)
        except (TypeError, ValueError):
            episode_number = album_total - offset
        result.append({
            "track_id": track_id,
            "album_id": album_id,
            "album_name": item.get("albumTitle") or "",
            "title": title,
            "episode_number": episode_number,
            "album_total": album_total,
            "duration_seconds": duration_seconds,
            "audio_resource_id": str(item.get("uploadId") or item.get("fileId") or ""),
            "audio_resource_path": _resource_path(item.get("playPath") or ""),
            "account_uid": observed_uid,
            "status": item.get("status") or "",
            "updated_at": _timestamp_text(item.get("updatedAt") or item.get("updateTime")),
            "cover_path": _resource_path(item.get("fullCoverPath") or item.get("coverPath")),
            "description": _normalized_text(item.get("intro") or item.get("richIntro") or ""),
            "category_id": item.get("categoryId") or item.get("albumCategoryId") or "",
            "record_id": str(item.get("recordId") or ""),
        })
    return result


def _normalize_schedule_time(value: Any) -> str:
    """Epoch milliseconds (or seconds) become 'YYYY-MM-DD HH:MM' Asia/Shanghai."""
    raw = str(value or "").strip()
    if raw.isdigit() and len(raw) >= 10:
        seconds = int(raw) / 1000.0 if len(raw) >= 12 else int(raw)
        tz = ZoneInfo(SCHEDULE_TIMEZONE)
        return datetime.fromtimestamp(seconds, tz).strftime("%Y-%m-%d %H:%M")
    return raw


def archive_matches(title: str) -> list[dict[str, Any]]:
    wanted = _normalized_text(title)
    matches: list[dict[str, Any]] = []
    scheduled = _api_get(SCHEDULED_LIST_API + "?page=1&pageSize=50", "scheduled list")
    for item in scheduled.get("infos") or []:
        if _normalized_text(str(item.get("title") or item.get("trackTitle") or "")) == wanted:
            matches.append({
                "content_id": str(item.get("trackId") or item.get("taskId") or item.get("id") or ""),
                "album_id": str(item.get("albumId") or ""),
                "album_name": item.get("albumTitle") or item.get("albumName") or "",
                "title": wanted,
                "state": item.get("statusText") or item.get("status") or item.get("state") or "",
                "mode": "scheduled",
                "schedule": _normalize_schedule_time(item.get("publishAt") or item.get("publishTime")),
            })
    for album in list_albums():
        tracks = _album_tracks(album["album_id"])
        for item in tracks:
            if _normalized_text(str(item.get("title") or "")) == wanted:
                matches.append({
                    "content_id": str(item.get("trackId") or ""),
                    "album_id": album["album_id"],
                    "album_name": item.get("albumTitle") or album["title"],
                    "title": wanted,
                    "state": item.get("status") or "",
                    "mode": "immediate",
                    "schedule": str(item.get("publishTime") or ""),
                })
    return matches


# ------------------------------------------------------------------ upload

def _validate_upload_file(audio_file: str) -> Path:
    path = Path(audio_file)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("ximalaya audio file missing or empty: %s" % audio_file)
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError("ximalaya unsupported audio extension: %s" % path.suffix)
    size = path.stat().st_size
    if size < AUDIO_MIN_BYTES:
        raise ValueError("ximalaya audio below %s-byte declared minimum: %s bytes" %
                         (AUDIO_MIN_BYTES, size))
    if size > AUDIO_MAX_BYTES:
        raise ValueError("ximalaya audio above 1G declared maximum: %s bytes" % size)
    return path


def _probed_audio(path: Path) -> dict[str, Any]:
    if not Path(FFPROBE).exists():
        return {}
    try:
        out = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=filename,format_name,duration,size",
             "-show_entries", "stream=codec_name,sample_rate,channels", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60, check=True).stdout
        parsed = json.loads(out)
        stream = (parsed.get("streams") or [{}])[0]
        fmt = parsed.get("format") or {}
        return {"container": fmt.get("format_name"), "duration": fmt.get("duration"),
                "size": fmt.get("size"), "filename": Path(fmt.get("filename") or path.name).name,
                "codec": stream.get("codec_name"), "sample_rate": stream.get("sample_rate"),
                "channels": stream.get("channels")}
    except (subprocess.SubprocessError, ValueError):
        return {}


def _best_playable(track_id: str) -> dict[str, Any]:
    endpoint = "%s/%s/%s" % (PLAYBACK_QUALITY_API, track_id, int(time.time() * 1000))
    request = Request(endpoint, headers={
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.ximalaya.com/sound/%s" % track_id,
        "User-Agent": "Mozilla/5.0",
    })
    try:
        with urlopen(request, timeout=30) as response:
            body = json.load(response)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("ximalaya playback metadata request failed: %s" % exc) from exc
    detail = (((body.get("data") or {}).get("debugInfo") or {})
              .get("debugDetailMap") or {}).get("detailTrackDto") or {}
    paths = (detail.get("result") or {}).get("playPathDto") or {}
    candidates = (
        ("MP3_128", "playPathHq", "hqSize"),
        ("M4A_64", "playPathAacV164", "aacV164Size"),
        ("MP3_64", "playPath64", "mp364Size"),
        ("MP3_32", "playPath32", "mp332Size"),
        ("M4A_24", "playPathAacV224", "aacV224Size"),
    )
    for quality, field, size_field in candidates:
        media_url = paths.get(field)
        if not media_url:
            continue
        host = (urlparse(media_url).hostname or "").lower()
        if not host.endswith(".xmcdn.com"):
            raise RuntimeError("ximalaya track %s returned a non-Ximalaya CDN URL" % track_id)
        return {"quality": quality, "url": media_url,
                "expected_size": int(paths.get(size_field) or 0)}
    raise RuntimeError("ximalaya track %s has no directly playable audio" % track_id)


def _safe_download_name(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", value).strip(" .")
    return (cleaned or "audio")[:120]


def _probe_download(path: Path) -> dict[str, Any]:
    probe = FFPROBE if Path(FFPROBE).exists() else "ffprobe"
    try:
        result = subprocess.run(
            [probe, "-v", "error", "-show_entries",
             "format=duration:stream=codec_name,codec_type", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60, check=True,
        )
        parsed = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise RuntimeError("ximalaya downloaded audio could not be decoded: %s" % exc) from exc
    stream = next((item for item in parsed.get("streams", [])
                   if item.get("codec_type") == "audio"), None)
    if not stream:
        raise RuntimeError("ximalaya downloaded file has no audio stream")
    return {"codec": stream.get("codec_name"),
            "duration": float((parsed.get("format") or {}).get("duration") or 0)}


def download_owned_track_once(track: dict[str, Any], output_dir: str,
                              expected_uid: int | None = None,
                              expected_name: str | None = None) -> dict[str, Any]:
    if not isinstance(track, dict):
        raise TypeError("ximalaya download requires a track evidence dict")
    identity = require_identity(expected_uid, expected_name)
    track_id = _decimal_id(track.get("track_id"), "track_id")
    album_id = _decimal_id(track.get("album_id"), "album_id")
    title = _normalized_text(track.get("title"))
    if not title:
        raise ValueError("ximalaya download requires an exact title")
    fresh = track_evidence(album_id, track_id, title)
    if not _same_track_identity(track, fresh):
        raise RuntimeError("ximalaya download live track target mismatch")

    playable = _best_playable(track_id)
    media_url = str(playable.get("url") or "")
    suffix = Path(urlparse(media_url).path).suffix.lower()
    if suffix not in {".mp3", ".m4a", ".aac"}:
        suffix = ".m4a" if str(playable.get("quality") or "").startswith("M4A") else ".mp3"
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / ("%s-%s%s" % (track_id, _safe_download_name(title), suffix))
    temporary = Path(str(target) + ".part")
    if target.exists() or temporary.exists():
        raise RuntimeError("ximalaya download target exists; refusing overwrite: %s" % target)

    request = Request(media_url, headers={
        "Accept": "audio/*,*/*;q=0.8",
        "Referer": "https://www.ximalaya.com/sound/%s" % track_id,
        "User-Agent": "Mozilla/5.0",
    })
    temporary_created = False
    try:
        with urlopen(request, timeout=60) as response, temporary.open("xb") as handle:
            temporary_created = True
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
        size = temporary.stat().st_size
        expected_size = int(playable.get("expected_size") or 0)
        if size <= 0 or (expected_size and size != expected_size):
            raise RuntimeError("ximalaya download size mismatch: %s != %s" %
                               (size, expected_size))
        media = _probe_download(temporary)
        temporary.replace(target)
    except Exception:
        if temporary_created:
            temporary.unlink(missing_ok=True)
        raise
    return {"status": "verified", "path": str(target), "quality": playable["quality"],
            "codec": media["codec"], "duration": media["duration"], "bytes": size,
            "track_id": track_id, "album_id": album_id, "title": title,
            "account": {"uid": identity["uid"], "name": identity["name"]},
            "retry": False}


JS_ROWS_STATE = """(() => {
  const rows = [...document.querySelectorAll('.upload-list-item-2or8pi-8')];
  return rows.map(r => ({
    title: ((r.querySelector('.track-title-31-gLQ0f .text-8XgXdNin') || {}).textContent || '').trim(),
    status: ((r.querySelector('.upload-status-1bUDOFDp') || {}).innerText || '').trim(),
    success: Boolean(r.querySelector('.success-FnKHWloK'))
  }));
})()"""


def prepare_upload(audio_file: str, title: str, expected_uid: int | None = None,
                   expected_name: str | None = None, timeout: int = 900) -> dict[str, Any]:
    identity = require_identity(expected_uid, expected_name)
    wanted_title = _normalized_text(title)
    units = _title_units(wanted_title)
    if not 0 < units <= TITLE_MAX:
        raise ValueError("ximalaya title must be 1..%s %s, got %s" %
                         (TITLE_MAX, TITLE_UNIT, units))
    if page_info().get("url") != UPLOAD_URL:
        raise RuntimeError("ximalaya prepare_upload requires the exact upload page")
    already = archive_matches(wanted_title)
    if already:
        raise RuntimeError("ximalaya exact title already exists, refusing duplicate upload: %s" % already)
    path = _validate_upload_file(audio_file)
    probe = _probed_audio(path)
    upload_file("input[type=file].webuploader-element-invisible", str(path))
    stem = Path(path).stem
    row = _wait_until(
        lambda: next((r for r in (js(JS_ROWS_STATE) or [])
                      if (r.get("title") or "").endswith(stem) and r.get("success")
                      and "上传成功" in r.get("status", "")), None),
        timeout, "ximalaya upload completion not observed for %s" % stem)
    return {"identity": identity, "audio": str(path), "probed": probe,
            "title": wanted_title, "upload_completed":
                {"status": row["status"], "row_title": row["title"]}}


# ------------------------------------------------------------------ form setters

JS_ALBUM_READBACK = """(() => {
  const b = document.querySelector('button[aria-label="选择专辑"]');
  return b ? (b.textContent || '').trim() : '';
})()"""


def select_album(album_id: str, expected_name: str | None = None,
                 timeout: float = 15) -> dict[str, Any]:
    albums = list_albums()
    matches = [album for album in albums if album["album_id"] == str(album_id)]
    if len(matches) != 1:
        raise RuntimeError("ximalaya album %s not found; refusing selection" % album_id)
    wanted_title = matches[0]["title"]
    if expected_name and _normalized_text(wanted_title) != _normalized_text(expected_name):
        raise RuntimeError("ximalaya album name mismatch for %s: expected %r, found %r" %
                           (album_id, expected_name, wanted_title))
    same_title = [album for album in albums
                  if _normalized_text(album["title"]) == _normalized_text(wanted_title)]
    if len(same_title) != 1:
        raise RuntimeError("ximalaya album title is not unique; refusing DOM selection")
    _click_visible('button[aria-label="选择专辑"]')
    _wait_until(lambda: js("(() => Boolean(document.querySelector('.scroll-item-8_W08IGr')))()"),
                timeout, "ximalaya album dropdown did not open")
    clicked = js("""(() => {
      const item = [...document.querySelectorAll('.scroll-item-8_W08IGr')]
        .find(e => (((e.querySelector('.album-title-text-4EH5AG-r') || {}).textContent)
                    || '').trim() === %s);
      if (!item) return false;
      item.querySelector('.scroll-item-content-252FXLKk').click();
      return true;
    })()""" % _json(wanted_title))
    if not clicked:
        raise RuntimeError("ximalaya album option %r not found in dropdown" % wanted_title)
    readback = _wait_until(lambda: (lambda v: v if v == wanted_title else None)(
        js(JS_ALBUM_READBACK) or ""), timeout,
        "ximalaya album readback never matched %r" % wanted_title)
    return {"album_id": str(album_id), "album_title": readback, "readback": True}

def create_album(title: str, category: str, cover_path: str, intro: str,
                 selling_point: str, tags: list[str],
                 expected_uid: int | None = None,
                 expected_name: str | None = None,
                 visibility: str = "public", timeout: float = 30) -> dict[str, Any]:
    """Create one free album and return its album_id (verified via list_albums diff).

    Live-verified 2026-09-17 (album 130150010). Page: ALBUM_CREATE_URL
    (React; the studio shell embeds it in a cross-origin iframe, so navigate
    to the albumMgr URL directly). Required: title (<=25 chars), category
    (level-1 li.xui-select-options_item, e.g. 外语), square cover >=500px
    (<10M, upload + crop confirm + wait for model.image), KindEditor intro
    (+ editor.sync()), selling point (customTitle rule), full tag chain
    (every is-require row needs a leaf, e.g. 内容分类 all three + leaves),
    AI-cover radio, agreement checkbox. Submit fires
    POST /anchor-activity-web/album/createFree; success returns albumId and
    navigates to #/album/editFree/<id>. Creation success counts on submit;
    platform review afterwards is out of scope.
    """
    wanted = _normalized_text(title)
    if not 0 < len(wanted) <= ALBUM_TITLE_MAX:
        raise ValueError("ximalaya album title must be 1..%s chars, got %s" %
                         (ALBUM_TITLE_MAX, len(wanted)))
    if visibility != "public":
        raise ValueError("ximalaya create_album only supports public albums")
    identity = require_identity(expected_uid, expected_name)
    albums_before = {a["album_id"] for a in list_albums()}
    _album_react_set('input[placeholder="请输入专辑名称"]', wanted)
    _album_react_set('input[placeholder="请输入专辑卖点"]', _normalized_text(selling_point))
    if not selling_point or not _normalized_text(selling_point):
        raise ValueError("ximalaya album selling point (customTitle) is required")
    picked = js("((name) => {\n"
                "  const norm = s => (s || '').replace(/\\\\s+/g, ' ').trim();\n"
                "  const items = [...document.querySelectorAll('li.xui-select-options_item')];\n"
                "  for (const it of items) {\n"
                "    if (norm(it.innerText) === name) { it.click(); return true; }\n"
                "  }\n"
                "  return false;\n"
                "})(" + _json(category) + ")")
    if not picked:
        raise RuntimeError("ximalaya album category %r not found" % category)
    wait(1.0)
    image_path, width, height = _validate_cover_file(cover_path)
    upload_file('input[type=file][accept*=".PNG"]', str(image_path))
    _wait_until(lambda: js("""(() => {
      const modals = [...document.querySelectorAll('h4')].filter(
        e => e.offsetParent && (e.innerText || '').trim() === '裁剪封面');
      return modals.length ? true : null;
    })()"""), timeout, "ximalaya album crop modal did not open")
    # The site's crop onClick goes through a canvas polyfill (toBlobHD) that is
    # briefly unavailable right after the modal opens; retry until it works.
    crop_ok = None
    for _ in range(6):
        try:
            crop_ok = js("""(() => {
              const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
              const btns = [...document.querySelectorAll('button')].filter(e => e.offsetParent);
              const b = btns.find(e => norm(e.innerText) === '确定');
              if (!b) return false;
              const key = Object.keys(b).find(k => k.indexOf('__reactEventHandlers') === 0);
              const fn = key && b[key].onClick;
              if (typeof fn !== 'function') { b.click(); return 'dom-click'; }
              fn({preventDefault() {}, stopPropagation() {}});
              return 'react-click';
            })()""")
        except Exception:
            crop_ok = None
        if crop_ok:
            break
        wait(2.0)
    if not crop_ok:
        raise RuntimeError("ximalaya album crop confirm not found")
    _wait_until(lambda: (lambda m: m.get("image") or None)(_album_model()),
                timeout, "ximalaya album cover never reached the form model")
    synced = js("((html) => {\n"
                "  const ke = document.querySelector('iframe.ke-edit-iframe');\n"
                "  if (!ke) return 'no-editor';\n"
                "  const doc = ke.contentDocument;\n"
                "  doc.body.focus();\n"
                "  doc.execCommand('selectAll', false, null);\n"
                "  if (!doc.execCommand('insertText', false, html)) return 'no-insert';\n"
                "  const eds = window.KindEditor && window.KindEditor.instances || [];\n"
                "  for (const ed of eds) { try { ed.sync(); } catch (e) {} }\n"
                "  return 'ok';\n"
                "})(" + _json(_normalized_text(intro)) + ")")
    if synced != "ok":
        raise RuntimeError("ximalaya album intro not set: %s" % synced)
    tag_out = _album_pick_tags(list(tags), timeout)
    missing = [k for k, v in tag_out.items() if not v]
    if missing:
        raise RuntimeError("ximalaya album tags not checked: %s" % missing)
    js("""(() => {
      const radios = document.querySelectorAll('input[type=radio]');
      if (radios[0] && !radios[0].checked) radios[0].click();
      const cb = document.querySelector('input[type=checkbox]');
      if (cb && !cb.checked) cb.click();
    })()""")
    wait(1.0)
    for prop in ("title", "customTitle", "richIntro", "image", "categoryId", "tags"):
        err = _album_validate_field(prop, timeout)
        if err != "OK":
            raise RuntimeError("ximalaya album field %s invalid: %s" % (prop, err))
    clicked = js("""(() => {
      const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
      const btns = [...document.querySelectorAll('button')].filter(e => e.offsetParent);
      const b = btns.find(e => norm(e.innerText) === '确认创建' && !e.disabled);
      if (!b) return false;
      b.click();
      return true;
    })()""")
    if not clicked:
        raise RuntimeError("ximalaya album submit button not clickable")
    deadline = time.monotonic() + 60
    new_ids: list[str] = []
    while time.monotonic() < deadline:
        wait(3.0)
        current = {a["album_id"] for a in list_albums()}
        new_ids = sorted(current - albums_before)
        if new_ids:
            break
    if not new_ids:
        raise RuntimeError("ximalaya album creation unverified: no new album appeared")
    if len(new_ids) != 1:
        raise RuntimeError("ximalaya album creation ambiguous: %s" % new_ids)
    album = next(a for a in list_albums() if a["album_id"] == new_ids[0])
    return {"album_id": album["album_id"], "title": album["title"],
            "category_id": album["category_id"], "cover": {"width": width, "height": height},
            "account": {"uid": identity["uid"], "name": identity["name"]}}


def set_title(title: str, timeout: float = 15) -> str:
    """Required 节目标题 setter (discovered requirement; ant-form-item-required,
    max 40 UTF-16 code units, counter N/40)."""
    wanted = _normalized_text(title)
    units = _title_units(wanted)
    if not 0 < units <= TITLE_MAX:
        raise ValueError("ximalaya title must be 1..%s %s, got %s" %
                         (TITLE_MAX, TITLE_UNIT, units))
    ok = js("((value) => {\n"
            "  const el = document.querySelector('input[placeholder=\"请输入声音标题\"]');\n"
            "  if (!el) return false;\n"
            "  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,\n"
            "                                                 'value').set;\n"
            "  setter.call(el, value);\n"
            "  el.dispatchEvent(new Event('input', {bubbles: true}));\n"
            "  el.dispatchEvent(new Event('change', {bubbles: true}));\n"
            "  el.dispatchEvent(new Event('blur', {bubbles: true}));\n"
            "  return el.value === value;\n"
            "})(" + _json(wanted) + ")")
    if not ok:
        raise RuntimeError("ximalaya title input not found or rejected the value")
    readback = _wait_until(lambda: (lambda v: v if v == wanted else None)(
        js("(() => { const i = document.querySelector('input[placeholder=\"请输入声音标题\"]');"
           "return i ? i.value : ''; })()") or ""), timeout,
        "ximalaya title readback never matched")
    return readback


def _cover_click_ok() -> bool:
    return bool(js("""(() => {
      const m = document.querySelector('.ant-modal');
      if (!m || !m.offsetParent) return false;
      const btn = [...m.querySelectorAll('button')]
        .find(b => (b.textContent || '').trim() === '确定');
      if (!btn) return false;
      btn.click();
      return true;
    })()"""))


def _cover_readback() -> str | None:
    return js("""(() => {
      const area = [...document.querySelectorAll('.ant-form-item')]
        .find(f => ((f.querySelector('.ant-form-item-label') || {}).textContent || '')
                   .trim() === '节目配图');
      if (!area) return null;
      const img = area.querySelector('img');
      if (!img || !img.offsetParent || !img.naturalWidth || !img.naturalHeight) return null;
      if (!(area.innerText || '').includes('更换图片')) return null;
      return JSON.stringify({src: (img.src || '').slice(0, 120),
                             width: img.naturalWidth, height: img.naturalHeight});
    })()""")


def _validate_cover_file(path: str) -> tuple[Path, int, int]:
    image_path = Path(path)
    if not image_path.is_file() or image_path.stat().st_size == 0:
        raise ValueError("ximalaya cover file missing or empty: %s" % path)
    if image_path.suffix.lower() not in COVER_EXTENSIONS:
        raise ValueError("ximalaya unsupported cover format: %s" % image_path.suffix)
    size = image_path.stat().st_size
    if size > COVER_MAX_BYTES:
        raise ValueError("ximalaya cover above 10M: %s bytes" % size)
    with Image.open(image_path) as image:
        width, height = image.size
    if width < COVER_MIN_EDGE or height < COVER_MIN_EDGE or width != height:
        raise ValueError("ximalaya cover %sx%s outside accepted square domain; "
                         "recommended >=1000x1000" % (width, height))
    return image_path, width, height


def set_custom_cover(path: str, timeout: float = 30) -> dict[str, Any]:
    image_path, width, height = _validate_cover_file(path)
    size = image_path.stat().st_size
    upload_file('input[type=file][accept*="png"]', str(image_path))
    _wait_until(lambda: js("""(() => {
      const m = document.querySelector('.ant-modal');
      return m && m.offsetParent ? 'open' : null;
    })()"""), timeout, "ximalaya crop modal did not open")
    if not _cover_click_ok():
        raise RuntimeError("ximalaya crop confirm button not found")
    readback = _wait_until(_cover_readback, timeout, "ximalaya cover readback missing")
    return {"filename": image_path.name, "width": width, "height": height,
            "format": image_path.suffix.lower().lstrip("."),
            "bytes": size, "crop_confirmed": True, "readback": json.loads(readback)}


_DESCRIPTION_READBACK = """(() => {
  const edifr = [...document.querySelectorAll('iframe')]
    .find(f => String(f.className).includes('ke-edit-iframe'));
  try { return edifr.contentDocument.body.innerText || ''; } catch (e) { return ''; }
})()"""

_DESCRIPTION_FORM_READBACK = """(() => {
  const root = document.querySelector('[class*="kindeditor-box"]');
  if (!root) return '';
  const key = Object.keys(root).find(name =>
    name.startsWith('__reactFiber') || name.startsWith('__reactInternalInstance'));
  if (!key) return '';
  let fiber = root[key];
  while (fiber) {
    const form = fiber.memoizedProps && fiber.memoizedProps.form;
    if (form && typeof form.getFieldsValue === 'function') {
      return form.getFieldsValue().richIntro || '';
    }
    fiber = fiber.return;
  }
  return '';
})()"""

_DESCRIPTION_FORM_SET = """((html) => {
  const root = document.querySelector('[class*="kindeditor-box"]');
  if (!root) return 'no-form';
  const key = Object.keys(root).find(name =>
    name.startsWith('__reactFiber') || name.startsWith('__reactInternalInstance'));
  if (!key) return 'no-form';
  let fiber = root[key];
  while (fiber) {
    const form = fiber.memoizedProps && fiber.memoizedProps.form;
    if (form && typeof form.setFieldsValue === 'function') {
      form.setFieldsValue({richIntro: html});
      const value = String(form.getFieldsValue().richIntro || '');
      return value.replace(/<[^>]*>/g, '').trim().includes(
        html.replace(/<[^>]*>/g, '').trim()) ? 'ok' : 'no-set';
    }
    fiber = fiber.return;
  }
  return 'no-form';
})(%s)"""

_DESCRIPTION_FORM_READY = """(() => {
  const root = document.querySelector('[class*="kindeditor-box"]');
  if (!root) return false;
  const key = Object.keys(root).find(name =>
    name.startsWith('__reactFiber') || name.startsWith('__reactInternalInstance'));
  let fiber = key ? root[key] : null;
  while (fiber) {
    const form = fiber.memoizedProps && fiber.memoizedProps.form;
    if (form && typeof form.getFieldsValue === 'function') return true;
    fiber = fiber.return;
  }
  return false;
})()"""


def _set_description_form(text: str) -> str | None:
    requested = _normalized_text(text)
    payload = ('<p style="font-size:16px;color:#333333;line-height:30px;'
               'font-family:Helvetica,Arial,sans-serif;font-weight:normal;'
               'text-align:justify;hyphens:auto;" data-flag="normal">%s</p>' % requested)
    return js(_DESCRIPTION_FORM_SET % _json(payload))


def set_description(text: str, timeout: float = 15) -> str:
    requested = _normalized_text(text)
    payload = ('<p style="font-size:16px;color:#333333;line-height:30px;'
               'font-family:Helvetica,Arial,sans-serif;font-weight:normal;'
               'text-align:justify;hyphens:auto;" data-flag="normal">%s</p>' % requested)
    result = js("((html) => {\n"
                "  const KE = window.KindEditor;\n"
                "  if (!KE || !KE.instances || !KE.instances.length) return 'no-editor';\n"
                "  const editor = KE.instances[0];\n"
                "  editor.html(html);\n"
                "  editor.sync();\n"
                "  const ta = [...document.querySelectorAll('textarea')]\n"
                "    .find(t => String(t.className).includes('ke-edit-textarea'));\n"
                "  if (!ta) return 'no-textarea';\n"
                "  const setter = Object.getOwnPropertyDescriptor(\n"
                "    HTMLTextAreaElement.prototype, 'value').set;\n"
                "  setter.call(ta, html);\n"
                "  ta.dispatchEvent(new Event('input', {bubbles: true}));\n"
                "  ta.dispatchEvent(new Event('change', {bubbles: true}));\n"
                "  return ta.value.includes(html.replace(/<[^>]*>/g, '').trim()) ? 'ok' : 'no-set';\n"
                "})(" + _json(payload) + ")")
    form_result = _set_description_form(requested)
    if form_result not in (None, "ok", "no-form", "no-set"):
        raise RuntimeError("ximalaya description Form API rejected the value: %s" % form_result)
    if result != "ok":
        raise RuntimeError("ximalaya description not set via KindEditor API: %s" % result)
    return _normalized_text(js(_DESCRIPTION_READBACK) or "")


def _save_edit_once(timeout: float = 15) -> bool:
    target = _wait_until(lambda: js("""(() => {
      const button = [...document.querySelectorAll('button')].find(b => {
        const rect = b.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && !b.disabled &&
          (b.textContent || '').replace(/\\s+/g, '').trim() === '保存';
      });
      if (!button) return null;
      button.scrollIntoView({block: 'center', inline: 'center'});
      const key = Object.keys(button).find(name =>
        name.startsWith('__reactFiber') || name.startsWith('__reactInternalInstance'));
      if (key) {
        let fiber = button[key];
        while (fiber) {
          const handler = fiber.memoizedProps && fiber.memoizedProps.onClick;
          if (typeof handler === 'function') {
            handler({
              stopPropagation() {},
              preventDefault() {},
              target: button,
            });
            return true;
          }
          fiber = fiber.return;
        }
      }
      button.click();
      button.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return true;
    })()"""), timeout, "ximalaya edit save button did not become available")
    return bool(target)


def _read_edit_description() -> str:
    iframe_text = _normalized_text(js(_DESCRIPTION_READBACK) or "")
    if iframe_text:
        return iframe_text
    form_html = str(js(_DESCRIPTION_FORM_READBACK) or "")
    return _normalized_text(html.unescape(re.sub(r"<[^>]*>", " ", form_html)))


def _wait_edit_description(expected: str, timeout: float) -> str:
    wanted = _normalized_text(expected)
    if not wanted:
        return _read_edit_description()
    return _wait_until(
        lambda: (lambda value: value if value == wanted else None)(_read_edit_description()),
        timeout, "ximalaya edit description was not ready",
    )


def _wait_edit_form_ready(timeout: float) -> bool:
    def ready():
        if _read_edit_description():
            return True
        return bool(js(_DESCRIPTION_FORM_READY))
    return bool(_wait_until(ready, timeout, "ximalaya edit form did not become ready"))


def _wait_edit_form_validation(timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        token = str(time.monotonic_ns())
        started = js("""((token) => {
          const root = document.querySelector('[class*="kindeditor-box"]');
          const key = root && Object.keys(root).find(name =>
            name.startsWith('__reactFiber') || name.startsWith('__reactInternalInstance'));
          let fiber = key ? root[key] : null;
          let form = null;
          while (fiber) {
            const candidate = fiber.memoizedProps && fiber.memoizedProps.form;
            if (candidate && typeof candidate.validateFieldsAndScroll === 'function') {
              form = candidate;
              break;
            }
            fiber = fiber.return;
          }
          if (!form) return '';
          window.__ximalayaEditValidation = {token, status: 'pending'};
          form.validateFieldsAndScroll(errors => {
            window.__ximalayaEditValidation = {
              token,
              status: errors ? 'error' : 'ok',
              error_fields: errors ? Object.keys(errors) : [],
            };
          });
          return token;
        })(%s)""" % _json(token))
        if started != token:
            raise RuntimeError("ximalaya edit form validation API not found")
        attempt_deadline = min(deadline, time.monotonic() + 5)
        while time.monotonic() < attempt_deadline:
            state = js("""((token) => {
              const result = window.__ximalayaEditValidation;
              return result && result.token === token ? result : null;
            })(%s)""" % _json(token))
            if state and state.get("status") != "pending":
                if state.get("status") != "ok":
                    raise RuntimeError("ximalaya edit validation failed: %s" %
                                       ",".join(state.get("error_fields") or []))
                return True
            wait(0.2)
    raise TimeoutError("ximalaya edit form validation did not settle")


def _edit_track_evidence(album_id: str, track_id: str, title: str) -> dict[str, Any]:
    data = _api_get("%s?trackId=%s" % (EDIT_INFO_API, track_id), "edit track evidence")
    info = data.get("trackInfo") if isinstance(data.get("trackInfo"), dict) else {}
    rich = data.get("trackRichInfo") if isinstance(data.get("trackRichInfo"), dict) else {}
    observed_track_id = str(info.get("trackId") or rich.get("trackId") or "")
    observed_album_id = str(info.get("albumId") or "")
    observed_title = _normalized_text(info.get("title"))
    if (observed_track_id != track_id or observed_album_id != album_id
            or observed_title != title):
        raise RuntimeError("ximalaya edit evidence target mismatch")
    status_info = info.get("trackStatusInfo")
    status_info = status_info if isinstance(status_info, dict) else {}
    description_html = data.get("richIntro") or rich.get("richIntro") or info.get("intro") or ""
    return {
        "track_id": track_id,
        "album_id": album_id,
        "title": observed_title,
        "cover_path": _resource_path(info.get("coverPath") or info.get("fullCoverPath")),
        "description": _normalized_text(html.unescape(re.sub(r"<[^>]*>", " ",
                                                               str(description_html)))),
        "category_id": info.get("categoryId") or info.get("albumCategoryId") or "",
        "visibility": info.get("visibleCrowdType", status_info.get("isPublic", "")),
        "publish_state": status_info.get("trackStatus") or "",
        "status": status_info.get("trackStatus") or "",
        "audio_resource_id": str(info.get("uploadId") or ""),
        "account_uid": str(info.get("anchorId") or ""),
        "edit_source": "anchor_track_edit",
    }


def _current_track_for_edit(album_id: str, track_id: str, title: str) -> dict[str, Any]:
    evidence = track_evidence(album_id, track_id, title)
    evidence.update(_edit_track_evidence(album_id, track_id, title))
    evidence["source"] = evidence.get("source", "") + "+anchor_track_edit"
    return evidence


def _fresh_track_for_edit(track: dict[str, Any], expected_uid: int | None,
                          expected_name: str | None) -> tuple[dict[str, Any], str, str, str, dict[str, Any]]:
    if not isinstance(track, dict):
        raise TypeError("ximalaya edit requires a track evidence dict")
    track_id = _decimal_id(track.get("track_id"), "track_id")
    album_id = _decimal_id(track.get("album_id"), "album_id")
    title = _normalized_text(track.get("title"))
    if not title:
        raise ValueError("ximalaya edit requires an exact title")
    identity = require_identity(expected_uid, expected_name)
    fresh = _current_track_for_edit(album_id, track_id, title)
    if not _same_track_identity(track, fresh):
        raise RuntimeError("ximalaya edit live track target mismatch")
    return identity, track_id, album_id, title, fresh


def _unchanged_track_fields(before: dict[str, Any], after: dict[str, Any],
                            include_cover: bool = True) -> bool:
    keys = ["track_id", "album_id", "album_name", "title", "audio_resource_id",
            "visibility", "category_id", "publish_state", "status"]
    if include_cover:
        keys.append("cover_path")
    return all(before.get(key) == after.get(key) for key in keys)


def update_track_description_once(track: dict[str, Any], description: str,
                                  expected_uid: int | None = None,
                                  expected_name: str | None = None,
                                  confirm: bool = False,
                                  timeout: int = 180) -> dict[str, Any]:
    if confirm is not True:
        raise ValueError("ximalaya update_track_description_once requires confirm=True")
    wanted = _normalized_text(description)
    if not wanted:
        raise ValueError("ximalaya description must be nonempty")
    identity, track_id, album_id, title, before = _fresh_track_for_edit(
        track, expected_uid, expected_name)
    save_clicks = 0
    goto_url(EDIT_URL.format(track_id))
    wait(2)
    _wait_edit_form_ready(min(timeout, 30))
    if _normalized_text(set_description(wanted)) != wanted:
        raise RuntimeError("ximalaya description form readback did not match")
    _wait_until(
        lambda: (lambda result: result if result == "ok" else None)(
            _set_description_form(wanted)),
        min(timeout, 15), "ximalaya description Form API did not accept the value",
    )
    _wait_edit_form_validation(min(timeout, 15))
    _save_edit_once(min(timeout, 15))
    save_clicks = 1
    after = None
    try:
        goto_url(SOUND_MANAGE_URL + album_id)
        wait(2)
        goto_url(EDIT_URL.format(track_id))
        wait(2)
        readback = _wait_until(
            lambda: (lambda value: value if value == wanted else None)(
                _read_edit_description()),
            timeout, "ximalaya description save readback did not match",
        )
        after = _current_track_for_edit(album_id, track_id, title)
        if readback != wanted or after.get("description") != wanted or not _unchanged_track_fields(before, after):
            raise RuntimeError("ximalaya description postcondition did not hold")
    except (RuntimeError, TimeoutError) as exc:
        return {
            "identity": identity, "status": "description_update_unverified",
            "save_clicks": save_clicks, "retry": False, "track_id": track_id,
            "album_id": album_id, "title": title, "before": before, "after": after,
            "description": wanted, "diagnostics": str(exc),
        }
    return {
        "identity": identity, "status": "description_updated", "save_clicks": save_clicks,
        "retry": False, "track_id": track_id, "album_id": album_id, "title": title,
        "before": before, "after": after, "description": wanted,
        "verification_source": "edit_page+authenticated_edit_api",
    }


def replace_track_cover_once(track: dict[str, Any], image_file: str,
                             expected_uid: int | None = None,
                             expected_name: str | None = None,
                             confirm: bool = False,
                             timeout: int = 180) -> dict[str, Any]:
    if confirm is not True:
        raise ValueError("ximalaya replace_track_cover_once requires confirm=True")
    image_path, width, height = _validate_cover_file(image_file)
    identity, track_id, album_id, title, before = _fresh_track_for_edit(
        track, expected_uid, expected_name)
    cover_uploads = 1
    crop_confirms = 0
    save_clicks = 0
    after = None
    try:
        goto_url(EDIT_URL.format(track_id))
        wait(2)
        cover = set_custom_cover(str(image_path), min(timeout, 30))
        crop_confirms = 1 if cover.get("crop_confirmed") else 0
        _wait_edit_form_validation(min(timeout, 15))
        _save_edit_once(min(timeout, 15))
        save_clicks = 1
        goto_url(SOUND_MANAGE_URL + album_id)
        wait(2)
        goto_url(EDIT_URL.format(track_id))
        wait(2)
        after = _current_track_for_edit(album_id, track_id, title)
        if (not after.get("cover_path") or after.get("cover_path") == before.get("cover_path")
                or not _unchanged_track_fields(before, after, include_cover=False)
                or after.get("description") != before.get("description")):
            raise RuntimeError("ximalaya cover postcondition did not hold")
    except (RuntimeError, TimeoutError, OSError, ValueError) as exc:
        return {
            "identity": identity, "status": "cover_replacement_unverified",
            "cover_uploads": cover_uploads, "crop_confirms": crop_confirms,
            "save_clicks": save_clicks, "retry": False, "track_id": track_id,
            "album_id": album_id, "title": title, "before": before, "after": after,
            "cover": {"path": str(image_path), "width": width, "height": height},
            "diagnostics": str(exc),
        }
    return {
        "identity": identity, "status": "cover_replaced", "cover_uploads": cover_uploads,
        "crop_confirms": crop_confirms, "save_clicks": save_clicks, "retry": False,
        "track_id": track_id, "album_id": album_id, "title": title,
        "before": before, "after": after,
        "cover": {"path": str(image_path), "width": width, "height": height},
        "verification_source": "authenticated_edit_api",
    }


def _switch_checked() -> bool:
    return bool(js("""(() => {
      const sw = document.querySelector('button[aria-label="定时发布"]');
      return sw ? sw.getAttribute('aria-checked') === 'true' : false;
    })()"""))


def set_publish_mode(mode: str) -> dict[str, Any]:
    if mode not in PUBLISH_MODES:
        raise ValueError("ximalaya publish mode must be immediate or scheduled, got %r" %
                         (mode,))
    wanted = mode == "scheduled"
    if _switch_checked() != wanted:
        js("(() => { const sw = document.querySelector('button[aria-label=\"定时发布\"]');"
           " if (sw) sw.click(); return true; })()")
        wait(0.5)
    if _switch_checked() != wanted:
        raise RuntimeError("ximalaya publish mode switch did not settle on %s" % mode)
    return {"mode": mode, "switch_checked": wanted}


def _calendar_month_text() -> str:
    return js("""(() => {
      const p = document.querySelector('.ant-calendar');
      if (!p) return '';
      const cell = p.querySelector('.ant-calendar-ym-select, .ant-calendar-my-select');
      return cell ? (cell.textContent || '').trim().slice(0, 16) : '';
    })()""") or ""
def _navigate_calendar(target: datetime, timeout: float) -> int:
    wanted = "%s年%s月" % (target.year, target.month)
    moves = 0
    while _calendar_month_text() != wanted:
        current = _calendar_month_text()
        m = re.fullmatch(r"(\d{4})年(\d{1,2})月", current)
        if not m:
            raise RuntimeError("ximalaya calendar month unreadable: %r" % current)
        year, month = int(m.group(1)), int(m.group(2))
        forward = (year, month) < (target.year, target.month)
        selector = ".ant-calendar-next-month-btn" if forward else ".ant-calendar-prev-month-btn"
        js("(s => { const el = document.querySelector(s); if (el) el.click(); return true; })()"
           % _json(selector))
        moves += 1
        if moves > 130:
            raise RuntimeError("ximalaya calendar could not reach %s" % wanted)
        wait(0.4)
    return moves


def _pick_calendar_day(target: datetime) -> bool:
    return bool(js("""(() => {
      const p = document.querySelector('.ant-calendar');
      if (!p) return false;
      const day = String(parseInt(%s, 10));
      const cells = [...p.querySelectorAll('td')].filter(td => {
        const d = td.querySelector('.ant-calendar-date');
        if (!d) return false;
        if ((d.textContent || '').trim() !== day) return false;
        return !(String(d.className).includes('ant-calendar-last-month-cell') ||
                 String(d.className).includes('ant-calendar-next-month-btn-day'));
      });
      if (!cells.length) return false;
      cells[0].querySelector('.ant-calendar-date').click();
      return true;
    })()""" % _json(str(target.day))))


def _pick_time_options(hour: str, minute: str, timeout: float) -> bool:
    js("(() => { const p = document.querySelector('.ant-calendar');"
       " const b = p && p.querySelector('.ant-calendar-time-picker-btn');"
       " if (b) b.click(); return true; })()")
    wait(0.6)
    clicked = js("""(() => {
      const p = document.querySelector('.ant-calendar');
      if (!p) return false;
      const cols = [...p.querySelectorAll('.ant-calendar-time-picker-select')];
      if (cols.length < 2) return false;
      const pick = (col, value) => {
        const li = [...col.querySelectorAll('li')]
          .find(o => (o.textContent || '').trim() === value &&
                     !String(o.className).includes('disabled'));
        if (!li) return false;
        li.click();
        return true;
      };
      return pick(cols[0], %s) && pick(cols[1], %s);
    })()""" % (_json(hour), _json(minute)))
    if not clicked:
        raise RuntimeError("ximalaya time options %s:%s not selectable (disabled or absent)" %
                           (hour, minute))
    wait(0.4)
    return True


def _calendar_confirm() -> bool:
    return bool(js("""(() => {
      const p = document.querySelector('.ant-calendar');
      if (!p) return false;
      const ok = p.querySelector('.ant-calendar-ok-btn');
      if (!ok) return false;
      ok.click();
      return true;
    })()"""))


def _schedule_input_value() -> str:
    return js("""(() => {
      const i = document.querySelector('input.ant-calendar-picker-input');
      return i ? i.value : '';
    })()""") or ""


def _minimum_slot(now: datetime) -> datetime:
    """Earliest accepted slot: now + 2h with second/microsecond zeroed when the
    wall clock sits exactly on the minute, otherwise the next whole minute."""
    if now.second == 0 and now.microsecond == 0:
        return now.replace(second=0, microsecond=0) + timedelta(minutes=SCHEDULE_MIN_LEAD_MINUTES)
    return (now + timedelta(minutes=SCHEDULE_MIN_LEAD_MINUTES)).replace(second=0, microsecond=0)


def set_schedule_datetime(value: str, timeout: float = 20) -> dict[str, Any]:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", value or ""):
        raise ValueError("ximalaya schedule must be 'YYYY-MM-DD HH:MM', got %r" % value)
    tz = ZoneInfo(SCHEDULE_TIMEZONE)
    now = datetime.now(tz)
    target = datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    minimum = _minimum_slot(now)
    if target < minimum:
        raise ValueError("ximalaya schedule %s is before the enforced two-hour minimum "
                         "lead (earliest slot %s)" % (target.strftime("%Y-%m-%d %H:%M"),
                                                      minimum.strftime("%Y-%m-%d %H:%M")))
    if not _switch_checked():
        set_publish_mode("scheduled")
    if not js("(() => { const i = document.querySelector('input.ant-calendar-picker-input');"
              " if (!i) return false; i.click(); return true; })()"):
        raise RuntimeError("ximalaya schedule datetime input not found")
    wait(1.0)

    def _calendar_open():
        return js("""(() => {
          const p = document.querySelector('.ant-calendar');
          return p && p.offsetParent ? 'open' : null;
        })()""")
    if not _calendar_open():
        js("(() => { const w = document.querySelector('.ant-calendar-picker');"
           " if (w) w.click(); return true; })()")
    _wait_until(_calendar_open, timeout, "ximalaya calendar did not open")
    _navigate_calendar(target, timeout)
    if not _pick_calendar_day(target):
        raise RuntimeError("ximalaya calendar day %s not selectable" % target.day)
    wait(0.6)
    _pick_time_options("%02d" % target.hour, "%02d" % target.minute, timeout)
    if not _calendar_confirm():
        raise RuntimeError("ximalaya calendar confirm button not found")
    readback = _wait_until(
        lambda: (lambda v: v if v.startswith(value) else None)(_schedule_input_value()),
        timeout, "ximalaya schedule readback never matched %s" % value)
    return {"date": value.split(" ")[0], "time": value.split(" ")[1],
            "timezone": SCHEDULE_TIMEZONE, "mode": "scheduled", "readback": readback}


# ------------------------------------------------------------------ snapshot / diagnostics

JS_FORM_STATE = """(() => {
  const q = s => document.querySelector(s);
  const item = label => [...document.querySelectorAll('.ant-form-item')]
    .find(f => ((f.querySelector('.ant-form-item-label') || {}).textContent || '').trim() === label);
  const category = item('分类');
  const categoryValue = category && category.querySelector('.ant-select-selection-selected-value');
  const aiItem = item('是否AI合成');
  const aiYes = aiItem && aiItem.querySelector('input[type=radio][value="true"]');
  const aiNo = aiItem && aiItem.querySelector('input[type=radio][value="false"]');
  const coverArea = item('节目配图');
  const coverImg = coverArea && coverArea.querySelector('img');
  const counter = [...document.querySelectorAll('*')]
    .find(e => e.children.length === 0 && /\\d+\\/40/.test((e.textContent || '').trim()));
  const rows = [...document.querySelectorAll('.upload-list-item-2or8pi-8')].map(r => ({
    title: ((r.querySelector('.track-title-31-gLQ0f .text-8XgXdNin') || {}).textContent || '').trim(),
    status: ((r.querySelector('.upload-status-1bUDOFDp') || {}).innerText || '').trim(),
    success: Boolean(r.querySelector('.success-FnKHWloK'))
  }));
  const errors = [...document.querySelectorAll('.ant-form-explain,[class*="error"]')]
    .filter(e => e.offsetParent && (e.innerText || '').trim())
    .map(e => (e.innerText || '').trim().slice(0, 80));
  const sw = q('button[aria-label="定时发布"]');
  const submit = q('button[aria-label="确认发布"]');
  const modal = q('.ant-modal');
  const edifr = [...document.querySelectorAll('iframe')]
    .find(f => String(f.className).includes('ke-edit-iframe'));
  let description = '';
  try { description = edifr.contentDocument.body.innerText || ''; } catch (e) {}
  return {
    title: q('input[placeholder="请输入声音标题"]') ? q('input[placeholder="请输入声音标题"]').value : '',
    title_counter: counter ? counter.textContent.trim() : '',
    album: q('button[aria-label="选择专辑"]') ? q('button[aria-label="选择专辑"]').textContent.trim() : '',
    category: categoryValue ? categoryValue.textContent.trim() : '',
    ai: (aiYes && aiYes.checked) ? '是' : ((aiNo && aiNo.checked) ? '否' : null),
    cover: coverImg && coverImg.offsetParent ? {src: (coverImg.src || '').slice(0, 120),
      width: coverImg.naturalWidth, height: coverImg.naturalHeight} : null,
    description: description.trim(),
    rows: rows,
    scheduled: sw ? sw.getAttribute('aria-checked') === 'true' : false,
    schedule: q('input.ant-calendar-picker-input') ? q('input.ant-calendar-picker-input').value : '',
    submit: submit ? {disabled: Boolean(submit.disabled), text: (submit.textContent || '').trim()} : null,
    modal: modal && modal.offsetParent ? (modal.innerText || '').trim().slice(0, 160) : '',
    validation_errors: errors
  };
})()"""


def submission_snapshot() -> dict[str, Any]:
    state = js(JS_FORM_STATE) or {}
    rows = state.get("rows") or []
    upload_ready = any(r.get("success") and "上传成功" in r.get("status", "") for r in rows)
    return {
        "identity": account_identity(),
        "upload_ready": upload_ready,
        "rows": rows,
        "title": state.get("title") or "",
        "title_counter": state.get("title_counter") or "",
        "album": state.get("album") or "",
        "category": state.get("category") or "",
        "ai": state.get("ai"),
        "cover": state.get("cover"),
        "description": state.get("description") or "",
        "scheduled": state.get("scheduled"),
        "schedule": state.get("schedule") or "",
        "submit": state.get("submit"),
        "modal": state.get("modal") or "",
        "validation_errors": state.get("validation_errors") or [],
    }


DIAGNOSTIC_REASONS = ("form_validation_failed", "confirmation_required", "platform_rejected",
                      "auth_required", "result_delayed", "click_not_accepted",
                      "submission_unverified")


def submission_diagnostics() -> dict[str, Any]:
    state = js(JS_FORM_STATE) or {}
    negative = re.compile(r"失败|错误|请.*填写|请选择|不能为空|不符合|无法|稍后重试")
    positive = re.compile(r"成功|已提交|已发布|审核中|上传完成")
    errors = state.get("validation_errors") or []
    modal = state.get("modal") or ""
    if errors:
        reason = "form_validation_failed"
    elif modal:
        reason = "confirmation_required"
    elif any(negative.search(t) for t in errors) or negative.search(modal):
        reason = "platform_rejected"
    elif positive.search(modal):
        reason = "result_delayed"
    elif not state.get("submit"):
        reason = "click_not_accepted"
    else:
        reason = "submission_unverified"
    if reason not in DIAGNOSTIC_REASONS:
        reason = "submission_unverified"
    return {"url": js("location.href") or "", "validation_errors": errors,
            "modal": modal, "submit": state.get("submit"), "rows": state.get("rows") or [],
            "reason": reason}


# ------------------------------------------------------------------ reconciliation

def _decimal_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[1-9]\d*", value):
        raise ValueError("ximalaya %s must be a nonempty decimal string" % field)
    return value


def _timestamp_text(value: Any) -> str:
    raw = str(value or "").strip()
    if raw.isdigit() and len(raw) >= 10:
        seconds = int(raw) / 1000.0 if len(raw) >= 12 else int(raw)
        return datetime.fromtimestamp(seconds, ZoneInfo(SCHEDULE_TIMEZONE)).strftime(
            "%Y-%m-%d %H:%M:%S")
    return raw


def _resource_path(value: Any) -> str:
    raw = str(value or "").strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    if raw.startswith("http://") or raw.startswith("https://"):
        from urllib.parse import urlsplit
        return urlsplit(raw).path
    return raw


def _track_audio_evidence(item: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    uri = item.get("uriInfo") if isinstance(item.get("uriInfo"), dict) else {}
    values = {
        "audio_resource_id": item.get("uploadId") or "",
        "audio_resource_path": (detail.get("playPath") or detail.get("audioPath")
                                 or detail.get("playUrl") or ""),
        "track_path": uri.get("url") or "",
    }
    return {key: (str(value) if key.endswith("_id") else _resource_path(value))
            for key, value in values.items()}


def track_evidence(album_id: str, track_id: str,
                   expected_title: str | None = None) -> dict[str, Any]:
    album_id = _decimal_id(album_id, "album_id")
    track_id = _decimal_id(track_id, "track_id")
    wanted = _normalized_text(expected_title) if expected_title is not None else None
    if expected_title is not None and not wanted:
        raise ValueError("ximalaya expected_title must be nonempty")

    page_size = 50
    found: list[dict[str, Any]] = []
    page = 0
    for page in range(1, TRACK_EVIDENCE_MAX_PAGES + 1):
        data = _api_get("%s?albumId=%s&page=%s&pageSize=%s" %
                        (TRACKS_LIST_API, album_id, page, page_size), "track evidence list")
        infos = data.get("infos") or []
        for item in infos:
            if (str(item.get("trackId") or "") == track_id
                    and str(item.get("albumId") or "") == album_id):
                found.append(item)
        total = int(data.get("totalSize") or 0)
        if not infos or (total and page * page_size >= total) or (found and not total):
            break
    if len(found) != 1:
        raise RuntimeError("ximalaya track evidence requires one exact album/track match; found %s"
                           % len(found))

    item = found[0]
    detail_data = _api_get("%s?trackId=%s" % (TRACK_DETAIL_API, track_id), "track detail")
    detail = detail_data.get("trackInfo") if isinstance(detail_data.get("trackInfo"), dict) else {}
    album = detail_data.get("albumInfo") if isinstance(detail_data.get("albumInfo"), dict) else {}
    if str(detail.get("trackId") or track_id) != track_id:
        raise RuntimeError("ximalaya track detail ID mismatch")
    detail_album_id = str(album.get("albumId") or item.get("albumId") or "")
    if detail_album_id != album_id:
        raise RuntimeError("ximalaya track detail album ID mismatch")
    title = _normalized_text(detail.get("title") or item.get("title") or "")
    if wanted is not None and title != wanted:
        raise RuntimeError("ximalaya track title mismatch: expected=%r observed=%r" %
                           (wanted, title))
    status_info = item.get("trackStatusInfo")
    status_info = status_info if isinstance(status_info, dict) else {}
    duration = detail.get("duration", item.get("duration"))
    try:
        duration_seconds = float(duration or 0)
    except (TypeError, ValueError):
        duration_seconds = 0.0
    evidence = {
        "track_id": track_id,
        "album_id": album_id,
        "album_name": item.get("albumTitle") or album.get("title") or "",
        "title": title,
        "duration_seconds": duration_seconds,
        "status": item.get("status") or status_info.get("trackStatus") or detail.get("approveStatus") or "",
        "published_at": _timestamp_text(detail.get("lastUpdate") or item.get("publishTime")),
        "updated_at": _timestamp_text(detail.get("updatedAt") or item.get("updatedAt")),
        "cover_path": _resource_path(detail.get("coverPath") or item.get("fullCoverPath")
                                      or item.get("coverPath")),
        "description": _normalized_text(detail.get("richIntro") or item.get("intro") or ""),
        "category_id": item.get("categoryId") or item.get("albumCategoryId") or "",
        "visibility": detail.get("visibleStatus", status_info.get("isPublic", "")),
        "publish_state": detail.get("approveStatus") or status_info.get("trackStatus") or "",
        "is_paid": detail.get("isPaid", album.get("isPaid")),
        "is_own": bool(detail.get("isOwn")),
        "price_type": detail.get("priceType", item.get("priceType")),
        "can_delete": detail.get("canDelete", item.get("canDelete")),
        "record_id": str(item.get("recordId") or ""),
        "account_uid": str(detail.get("anchorUid") or item.get("anchorId") or ""),
        "source": "album_tracks+track_simple",
        "page": page,
    }
    evidence.update(_track_audio_evidence(item, detail))
    return evidence


def _same_track_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (str(left.get("track_id") or "") == str(right.get("track_id") or "")
            and str(left.get("album_id") or "") == str(right.get("album_id") or "")
            and _normalized_text(left.get("title")) == _normalized_text(right.get("title")))


def _replacement_audio_changed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return any(str(before.get(key) or "") != str(after.get(key) or "")
               for key in ("audio_resource_id", "audio_resource_path", "updated_at",
                           "published_at"))


def _replacement_verified(before: dict[str, Any], after: dict[str, Any],
                          replacement: dict[str, Any]) -> bool:
    try:
        wanted_duration = float(replacement.get("duration") or 0)
    except (TypeError, ValueError):
        return False
    if not _same_track_identity(before, after):
        return False
    if abs(float(after.get("duration_seconds") or 0) - wanted_duration) > DURATION_TOLERANCE_SECONDS:
        return False
    if not _replacement_audio_changed(before, after):
        return False
    for key in ("album_name", "cover_path", "description", "visibility", "category_id",
                "publish_state", "status"):
        if key in before and key in after and before[key] != after[key]:
            return False
    return True


def _menu_item_center(label: str) -> dict[str, Any] | None:
    return js("""(() => {
      const wanted = %s;
      const el = Array.from(document.querySelectorAll(
        '.ant-popover.sound-more-popover .item-2RWRS8jo')).find(node =>
          node.offsetParent && (node.textContent || '').trim() === wanted);
      if (!el) return null;
      el.scrollIntoView({block:'center', inline:'center'});
      const r = el.getBoundingClientRect();
      return {x: r.x + r.width / 2, y: r.y + r.height / 2};
    })()""" % _json(label))


def _click_track_menu_item(label: str) -> None:
    target = _wait_until(lambda: _menu_item_center(label), 5,
                         "ximalaya track menu item did not become visible: %s" % label)
    click_at_xy(target["x"], target["y"])


def _replacement_state() -> dict[str, Any]:
    return js("""(() => {
      const modal = [...document.querySelectorAll(
        '.ant-modal,.xmDeleteModal,[class*="dialog"],[class*="Modal"]')]
        .find(e => e.offsetParent);
      const buttons = modal ? [...modal.querySelectorAll('button,a,[role="button"]')] : [];
      const confirmation = buttons
        .filter(e => e.offsetParent && !e.disabled && e.getAttribute('aria-disabled') !== 'true' &&
          /^(确定|确认|确认替换|确定替换|替换|保存|提交|提交替换)$/.test(
          (e.textContent || '').trim().replace(/\\s+/g, '')));
      return {confirmation: confirmation.length > 0};
    })()""") or {}


def replace_sound_once(track: dict[str, Any], replacement_file: str,
                       expected_uid: int | None = None, expected_name: str | None = None,
                       confirm: bool = False, timeout: int = 900) -> dict[str, Any]:
    if confirm is not True:
        raise ValueError("ximalaya replace_sound_once requires confirm=True")
    if not isinstance(track, dict):
        raise TypeError("ximalaya replace_sound_once requires a track evidence dict")
    track_id = _decimal_id(track.get("track_id"), "track_id")
    album_id = _decimal_id(track.get("album_id"), "album_id")
    title = _normalized_text(track.get("title"))
    if not title:
        raise ValueError("ximalaya replace_sound_once requires an exact title")
    identity = require_identity(expected_uid, expected_name)
    path = _validate_upload_file(replacement_file)
    replacement = _probed_audio(path)
    try:
        replacement_duration = float(replacement.get("duration") or 0)
    except (TypeError, ValueError):
        replacement_duration = 0
    if replacement_duration <= 0:
        raise ValueError("ximalaya replacement audio requires a readable positive duration")
    goto_url(SOUND_MANAGE_URL + album_id)
    wait(5)
    live_before = track_evidence(album_id, track_id, title)
    if not _same_track_identity(track, live_before):
        raise RuntimeError("ximalaya replacement live track target mismatch")
    before = dict(live_before)
    _open_track_menu(title, track_id)
    _wait_until(lambda: js("""(() => {
      const item = [...document.querySelectorAll(
        '.ant-popover.sound-more-popover .item-2RWRS8jo')]
        .find(e => e.offsetParent && e.getAttribute('aria-label') === '替换声音');
      return !!item && item.querySelectorAll(%s).length === 1;
    })()""" % _json(REPLACEMENT_INPUT_SELECTOR)), 10,
                "ximalaya replacement uploader input did not become ready")
    uploads = 1
    confirms = 0
    try:
        upload_file(REPLACEMENT_INPUT_SELECTOR, str(path))
    except Exception as exc:
        return {"identity": identity, "status": "replacement_unverified",
                "replacement_uploads": uploads, "replacement_confirms": confirms,
                "retry": False, "track_id": track_id, "album_id": album_id,
                "title": title, "before": before, "after": None,
                "replacement": {"path": str(path), "metadata": replacement},
                "diagnostics": "replacement file attachment failed: %s" % exc}

    deadline = time.monotonic() + timeout
    last_after = before
    last_error = ""
    while time.monotonic() < deadline:
        state = _replacement_state()
        if state.get("confirmation") and not confirms:
            if not _confirm_dialog_accept():
                return {"identity": identity, "status": "replacement_unverified",
                        "replacement_uploads": uploads, "replacement_confirms": confirms,
                        "retry": False, "track_id": track_id, "album_id": album_id,
                        "title": title, "before": before, "after": last_after,
                        "replacement": {"path": str(path), "metadata": replacement},
                        "diagnostics": "replacement confirmation control not activatable"}
            confirms = 1
        try:
            last_after = track_evidence(album_id, track_id, title)
        except (RuntimeError, TimeoutError) as exc:
            last_error = str(exc)
        else:
            last_error = ""
            if _replacement_verified(before, last_after, replacement):
                return {"identity": identity, "status": "replaced",
                        "replacement_uploads": uploads, "replacement_confirms": confirms,
                        "retry": False, "track_id": track_id, "album_id": album_id,
                        "title": title, "before": before, "after": last_after,
                        "replacement": {"path": str(path), "metadata": replacement},
                        "verification_source": "album_tracks+track_simple"}
        wait(min(3.0, max(0.2, deadline - time.monotonic())))
    return {"identity": identity, "status": "replacement_unverified",
            "replacement_uploads": uploads, "replacement_confirms": confirms,
            "retry": False, "track_id": track_id, "album_id": album_id,
            "title": title, "before": before, "after": last_after,
            "replacement": {"path": str(path), "metadata": replacement},
            "diagnostics": "replacement result not verified before deadline" +
                           (": %s" % last_error if last_error else "")}


def _successor_eligible(track: dict[str, Any]) -> bool:
    """Require positive free/public/deletable evidence before keepalive writes."""
    if track.get("is_paid") is not False:
        return False
    visibility = track.get("visibility")
    if visibility not in (0, 2, True, "0", "2"):
        return False
    state = track.get("publish_state")
    if state not in (1, 2, True, "1", "2"):
        return False
    return track.get("can_delete") in (None, True, "1", 1) and bool(track.get("track_id"))


def prepare_successor_upload(old_track: dict[str, Any], audio_file: str,
                             timeout: int = 900) -> dict[str, Any]:
    """Prepare one same-title successor while allowing only one exact old target."""
    if not isinstance(old_track, dict):
        raise TypeError("ximalaya successor requires an old track evidence dict")
    old_id = _decimal_id(old_track.get("track_id"), "old_track_id")
    album_id = _decimal_id(old_track.get("album_id"), "album_id")
    title = _normalized_text(old_track.get("title"))
    if not title or _title_units(title) > TITLE_MAX:
        raise ValueError("ximalaya successor title is empty or exceeds 40 UTF-16 units")
    identity = require_identity()
    fresh = track_evidence(album_id, old_id, title)
    if not _same_track_identity(old_track, fresh) or not _successor_eligible(fresh):
        raise RuntimeError("ximalaya successor old track is not a verified free public deletable target")
    matches = [m for m in archive_matches(title) if m["album_id"] == album_id]
    if len(matches) != 1 or matches[0]["content_id"] != old_id:
        raise RuntimeError("ximalaya successor requires exactly one same-title old record in target album")
    path = _validate_upload_file(audio_file)
    probe = _probed_audio(path)
    if page_info().get("url") != UPLOAD_URL:
        raise RuntimeError("ximalaya successor requires the exact upload page")
    upload_file("input[type=file].webuploader-element-invisible", str(path))
    stem = path.stem
    row = _wait_until(
        lambda: next((r for r in (js(JS_ROWS_STATE) or [])
                      if (r.get("title") or "").endswith(stem) and r.get("success")
                      and "上传成功" in r.get("status", "")), None),
        timeout, "ximalaya successor upload completion not observed for %s" % stem)
    return {"identity": identity, "status": "prepared", "old": fresh,
            "album_id": album_id, "title": title, "audio": str(path),
            "probed": probe, "upload_completed": row, "retry": False}


def submit_successor_once(old_track: dict[str, Any], run_marker: str = "",
                          timeout: int = 600) -> dict[str, Any]:
    """Publish one successor and identify it from the target album set difference."""
    if not run_marker:
        raise ValueError("ximalaya successor submit requires a nonempty run marker")
    old_id = _decimal_id(old_track.get("track_id"), "old_track_id")
    album_id = _decimal_id(old_track.get("album_id"), "album_id")
    title = _normalized_text(old_track.get("title"))
    identity = require_identity()
    before = {item["track_id"] for item in list_album_tracks(album_id)}
    if old_id not in before:
        raise RuntimeError("ximalaya successor old track disappeared before submit")
    first = submission_snapshot()
    wait(2)
    second = submission_snapshot()
    if _snapshot_comparable(first) != _snapshot_comparable(second):
        raise RuntimeError("ximalaya successor preflight was not stable")
    problems = []
    if second.get("title") != title:
        problems.append("title_readback")
    if not second.get("upload_ready") or not second.get("album"):
        problems.append("upload_or_album_missing")
    if second.get("scheduled"):
        problems.append("mode_not_immediate")
    submit = second.get("submit") or {}
    if not second.get("submit") or submit.get("disabled") or submit.get("text") != "确认发布":
        problems.append("submit_not_ready")
    if second.get("validation_errors") or second.get("modal"):
        problems.append("form_not_ready")
    if problems:
        raise RuntimeError("ximalaya successor preflight failed: %s" % ",".join(problems))
    if not js("""(() => { const b=document.querySelector('button[aria-label="确认发布"]');
      if (!b || b.disabled || !b.offsetParent) return false; b.click(); return true; })()"""):
        raise RuntimeError("ximalaya successor submit control not activatable")
    submit_clicks = 1
    wait(1.0)
    if js("""(() => { const m=document.querySelector('.ant-modal');
      return m && m.offsetParent && (m.innerText || '').includes('确认') ? 'open' : null; })()"""):
        if not _confirm_dialog_accept():
            return {"identity": identity, "status": "submission_unverified",
                    "submit_clicks": submit_clicks, "retry": False,
                    "old_track_id": old_id, "album_id": album_id, "title": title,
                    "run_marker": run_marker}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            after_items = list_album_tracks(album_id)
        except (RuntimeError, TimeoutError):
            after_items = []
        added = [item for item in after_items if item["track_id"] not in before]
        if len(added) == 1:
            new_id = added[0]["track_id"]
            try:
                successor = track_evidence(album_id, new_id, title)
            except (RuntimeError, TimeoutError):
                successor = None
            if successor and _successor_eligible(successor):
                return {"identity": identity, "status": "verified", "retry": False,
                        "submit_clicks": submit_clicks, "old_track_id": old_id,
                        "new_track_id": new_id, "album_id": album_id, "title": title,
                        "successor": successor, "before_ids": sorted(before),
                        "after_ids": sorted(item["track_id"] for item in after_items),
                        "run_marker": run_marker}
        wait(min(10, max(0.5, deadline - time.monotonic())))
    return {"identity": identity, "status": "submission_unverified", "retry": False,
            "submit_clicks": submit_clicks, "old_track_id": old_id,
            "album_id": album_id, "title": title, "run_marker": run_marker}


def delete_published_track_once(old_track: dict[str, Any], successor: dict[str, Any],
                                confirm: bool = False, timeout: int = 180) -> dict[str, Any]:
    """Delete exactly one old published track after its successor is verified."""
    if confirm is not True:
        raise ValueError("ximalaya delete_published_track_once requires confirm=True")
    if not isinstance(old_track, dict) or not isinstance(successor, dict):
        raise TypeError("ximalaya keepalive deletion requires two evidence dicts")
    old_id = _decimal_id(old_track.get("track_id"), "old_track_id")
    new_id = _decimal_id(successor.get("new_track_id") or successor.get("track_id"), "new_track_id")
    album_id = _decimal_id(old_track.get("album_id"), "album_id")
    title = _normalized_text(old_track.get("title"))
    if successor.get("status") != "verified":
        raise RuntimeError("ximalaya keepalive deletion requires a verified successor")
    if old_id == new_id or str(successor.get("album_id")) != album_id:
        raise RuntimeError("ximalaya keepalive old and successor identity mismatch")
    backup = old_track.get("local_audio_path") or old_track.get("download_path")
    if not backup or not Path(str(backup)).is_file():
        raise RuntimeError("ximalaya keepalive requires a complete local old-audio backup")
    fresh_old = track_evidence(album_id, old_id, title)
    fresh_new = track_evidence(album_id, new_id, title)
    if not _successor_eligible(fresh_old) or not _successor_eligible(fresh_new):
        raise RuntimeError("ximalaya keepalive deletion target is not positively eligible")
    current = [item["track_id"] for item in list_album_tracks(album_id)
               if _normalized_text(item.get("title")) == title]
    if sorted(current) != sorted({old_id, new_id}):
        raise RuntimeError("ximalaya keepalive requires exactly the old and successor same-title IDs before delete")
    try:
        _api_post(TRACK_DELETE_API, {"trackId": int(old_id)}, "published track deletion")
    except (RuntimeError, TimeoutError) as exc:
        error = str(exc)
    else:
        error = ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            ids = [item["track_id"] for item in list_album_tracks(album_id)
                   if _normalized_text(item.get("title")) == title]
        except (RuntimeError, TimeoutError):
            ids = []
        if old_id not in ids and ids.count(new_id) == 1:
            return {"status": "deleted", "retry": False, "delete_activated": True,
                    "old_track_id": old_id, "new_track_id": new_id, "album_id": album_id,
                    "title": title, "verification_source": "album_track_id_lists"}
        wait(min(3, max(0.2, deadline - time.monotonic())))
    return {"status": "deletion_unverified", "retry": False,
            "delete_activated": True, "old_track_id": old_id,
            "new_track_id": new_id, "album_id": album_id, "title": title,
            "diagnostics": error or "old track remains or successor is missing"}

def _match_record(item: dict[str, Any], title: str, content_id: str | None,
                  mode: str) -> dict[str, Any] | None:
    if _normalized_text(str(item.get("title") or item.get("trackTitle") or "")) != _normalized_text(title):
        return None
    record = {
        "content_id": str(item.get("trackId") or item.get("taskId") or item.get("id") or ""),
        "album_id": str(item.get("albumId") or ""),
        "album_name": item.get("albumTitle") or item.get("albumName") or "",
        "title": _normalized_text(str(item.get("title") or item.get("trackTitle") or "")),
        "state": item.get("statusText") or item.get("status") or item.get("state") or "",
        "mode": mode,
        "schedule": _normalize_schedule_time(item.get("publishAt") or item.get("publishTime")),
    }
    if content_id and record["content_id"] != str(content_id):
        return None
    return record


def manager_evidence(title: str, content_id: str | None = None,
                     expected_schedule: str | None = None,
                     attempts: int = 3) -> dict[str, Any]:
    if attempts < 1:
        raise ValueError("manager evidence attempts must be at least one")
    matches: list[dict[str, Any]] = []
    scheduled_state = ""
    immediate_state = ""
    for load in range(1, attempts + 1):
        matches = []
        scheduled = _api_get(SCHEDULED_LIST_API + "?page=1&pageSize=50", "scheduled list")
        for item in scheduled.get("infos") or []:
            record = _match_record(item, title, content_id, "scheduled")
            if record:
                matches.append(record)
        for album in list_albums():
            try:
                tracks = _album_tracks(album["album_id"])
            except RuntimeError:
                continue
            for item in tracks:
                record = _match_record(item, title, content_id, "immediate")
                if record:
                    record["album_name"] = record["album_name"] or album["title"]
                    matches.append(record)
        if matches:
            break
        wait(2.0)
    if not matches:
        raise RuntimeError("ximalaya manager evidence: no record with exact title %r after %s loads"
                           % (title, attempts))
    evidence = dict(matches[0])
    evidence["match_count"] = len(matches)
    evidence["latest"] = load <= attempts
    evidence["list_loads"] = load
    evidence["source"] = "reform_upload_api"
    if evidence["mode"] == "scheduled" and expected_schedule:
        scheduled_state = evidence["schedule"] or evidence["state"]
        evidence["schedule_match"] = (
            scheduled_state.startswith(expected_schedule)
            or evidence["state"] in ("审核中", "审核通过", "定时发布中"))
        evidence["expected_schedule"] = expected_schedule
        if not evidence["schedule_match"]:
            raise RuntimeError("ximalaya scheduled record time mismatch: expected=%r observed=%r"
                               % (expected_schedule, scheduled_state))
    else:
        evidence["schedule_match"] = True
    return evidence


def _snapshot_comparable(snapshot: dict[str, Any]) -> dict[str, Any]:
    comparable = dict(snapshot)
    comparable.pop("identity", None)
    return comparable


def submit_once(title: str, expected_uid: int | None = None,
                expected_name: str | None = None,
                expected_mode: str = "scheduled", expected_schedule: str | None = None,
                run_marker: str = "", timeout: int = 600) -> dict[str, Any]:
    if not run_marker:
        raise ValueError("ximalaya submit_once requires a nonempty run marker")
    identity = require_identity(expected_uid, expected_name)
    already = archive_matches(title)
    if len(already) > 1:
        raise RuntimeError("ximalaya exact title matched multiple records: %s" % already)
    if already:
        raise RuntimeError("ximalaya exact title already exists; refusing duplicate submission")
    first = submission_snapshot()
    wait(2)
    snapshot = submission_snapshot()
    if _snapshot_comparable(first) != _snapshot_comparable(snapshot):
        raise RuntimeError("ximalaya preflight was not stable: first=%s second=%s" %
                           (first, snapshot))
    problems = []
    if snapshot["title"] != title:
        problems.append("title_readback")
    if not snapshot["upload_ready"]:
        problems.append("upload_not_complete")
    if not snapshot["album"]:
        problems.append("album_missing")
    if expected_mode == "scheduled" and not snapshot["scheduled"]:
        problems.append("mode_not_scheduled")
    if expected_mode == "immediate" and snapshot["scheduled"]:
        problems.append("unexpected_schedule_switch")
    if expected_mode == "scheduled":
        if expected_schedule and not snapshot["schedule"].startswith(expected_schedule):
            problems.append("schedule_readback")
        if not snapshot["schedule"]:
            problems.append("schedule_missing")
    submit = snapshot["submit"] or {}
    if not snapshot["submit"] or submit.get("disabled") or submit.get("text") != "确认发布":
        problems.append("submit_not_ready")
    if snapshot["validation_errors"]:
        problems.append("validation_errors")
    if snapshot["modal"]:
        problems.append("modal_open")
    if problems:
        raise RuntimeError("ximalaya preflight failed (%s): %s" % (", ".join(problems), snapshot))
    if not js("""(() => {
      const b = document.querySelector('button[aria-label="确认发布"]');
      if (!b || b.disabled || !b.offsetParent) return false;
      b.click();
      return true;
    })()"""):
        raise RuntimeError("ximalaya submit control not activatable")
    clicked = 1
    wait(1.0)
    # one platform confirmation modal, if the flow shows one, is part of the
    # same single submission activation and is clicked at most once
    if js("""(() => {
      const m = document.querySelector('.ant-modal');
      return m && m.offsetParent && (m.innerText || '').includes('确认') ? 'open' : null;
    })()"""):
        confirmed = js("""(() => {
          const m = document.querySelector('.ant-modal');
          if (!m) return false;
          const btn = [...m.querySelectorAll('button')]
            .find(b => ['确 定', '确定', '确认', '确认发布'].includes((b.textContent || '').trim()));
          if (!btn) return false;
          btn.click();
          return true;
        })()""")
        if not confirmed:
            diagnostics = submission_diagnostics()
            return {"identity": identity, "status": "submission_unverified",
                    "submitted": True, "submit_clicks": clicked, "confirm_clicks": 0,
                    "diagnostics": diagnostics, "run_marker": run_marker,
                    "created_by": _CREATED_BY, "retry": False}
    diagnostics = None
    try:
        diagnostics = submission_diagnostics()
    except (RuntimeError, TimeoutError):
        diagnostics = None
    if diagnostics and diagnostics["reason"] in ("form_validation_failed", "platform_rejected",
                                                 "auth_required"):
        return {"identity": identity, "status": "submission_unverified", "submitted": True,
                "submit_clicks": clicked, "diagnostics": diagnostics,
                "run_marker": run_marker, "created_by": _CREATED_BY, "retry": False}
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            evidence = manager_evidence(title, None, expected_schedule
                                        if expected_mode == "scheduled" else None, attempts=1)
        except (RuntimeError, TimeoutError) as exc:
            last_error = str(exc)
            wait(min(10, max(0.5, deadline - time.monotonic())))
            continue
        if expected_mode == "immediate":
            accepted = bool(evidence["state"])
        else:
            accepted = True
        if accepted:
            return {"identity": identity, "status": "verified", "submitted": True,
                    "submit_clicks": clicked, "content_id": evidence["content_id"],
                    "title": evidence["title"], "run_marker": run_marker,
                    "mode": evidence["mode"], "schedule": evidence["schedule"],
                    "album_id": evidence["album_id"], "album_name": evidence["album_name"],
                    "state": evidence["state"], "manager": evidence,
                    "account": {"uid": identity["uid"], "name": identity["name"]},
                    "created_by": _CREATED_BY, "retry": False}
    return {"identity": identity, "status": "submission_unverified", "submitted": True,
            "submit_clicks": clicked, "diagnostics": diagnostics,
            "manager_error": last_error, "run_marker": run_marker,
            "created_by": _CREATED_BY, "retry": False}


# ------------------------------------------------------------------ deletion

JS_ROW_CONTROLS = """(() => {
  const wantedId = %s;
  const wanted = %s;
  const rows = [...document.querySelectorAll('.track-1Tfey3X4')];
  const hasId = r => wantedId && [r, ...r.querySelectorAll('*')].some(e =>
    [...e.attributes].some(a => a.value === wantedId || a.value.includes('/sound/' + wantedId)));
  const idMatches = rows.filter(hasId);
  const matches = (idMatches.length ? idMatches : rows).filter(r => {
    const name = (r.querySelector('.name-2qdbByRi') || {}).innerText || '';
    return name.trim() === wanted;
  });
  if (matches.length !== 1) return JSON.stringify({found: matches.length});
  const row = matches[0];
  row.scrollIntoView({block: 'center'});
  const box = row.querySelector('.manage-point-box-3qWnOYcX');
  if (!box) return JSON.stringify({found: 1, error: 'no manage point box'});
  box.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, view: window}));
  const rect = box.getBoundingClientRect();
  return JSON.stringify({found: 1, clicked: true,
                         x: rect.left + rect.width / 2,
                         y: rect.top + rect.height / 2});
})()"""


def _track_menu_visible() -> bool:
    return bool(js("""(() => Boolean([...document.querySelectorAll(
      '.ant-popover.sound-more-popover')].find(e => e.offsetParent)))()"""))


def _next_track_page() -> bool:
    return bool(js("""(() => {
      const next = document.querySelector('.ant-pagination-next');
      if (!next || String(next.className).includes('disabled')) return false;
      const button = next.querySelector('a,button') || next;
      button.click();
      return true;
    })()"""))


def _open_track_menu(title: str, track_id: str | None = None) -> None:
    for _ in range(TRACK_EVIDENCE_MAX_PAGES):
        raw = js(JS_ROW_CONTROLS %
                 (_json(str(track_id or "")), _json(_normalized_text(title))))
        payload = json.loads(raw) if isinstance(raw, str) else {}
        if payload.get("found") == 1 and payload.get("clicked"):
            try:
                _wait_until(_track_menu_visible, 2,
                            "ximalaya track menu did not open")
            except TimeoutError:
                if payload.get("x") is not None and payload.get("y") is not None:
                    click_at_xy(payload["x"], payload["y"])
            return
        if payload.get("found", 0) > 1:
            raise RuntimeError("ximalaya track row for %r is not uniquely actionable: %s" %
                               (title, payload))
        if not _next_track_page():
            break
        wait(0.5)
    raise RuntimeError("ximalaya track row for %r not uniquely actionable" % title)


def _confirm_dialog_accept(timeout: float = 10) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            info = page_info()
        except (NameError, RuntimeError):
            info = {}
        if isinstance(info, dict) and info.get("dialog"):
            cdp("Page.handleJavaScriptDialog", accept=True)
            return True
        if js("""(() => {
          const dialogs = [...document.querySelectorAll(
            '.ant-modal,.xmDeleteModal,[class*="dialog"],[class*="Modal"]')]
            .filter(d => d.offsetParent);
          for (const d of dialogs) {
            const btn = [...d.querySelectorAll('button,a,[role="button"]')]
              .find(b => !b.disabled && b.getAttribute('aria-disabled') !== 'true' &&
                ['确定', '确认', '确认发布', '确认替换', '确定替换', '替换',
                          '删除', '保存', '提交', '提交替换'].includes(
                (b.textContent || '').trim().replace(/\\s+/g, '')));
            if (btn) { btn.click(); return true; }
          }
          return false;
        })()"""):
            return True
        wait(min(0.5, max(0.1, deadline - time.monotonic())))
    return False


def _scheduled_row_activate(title: str) -> bool:
    return bool(js("""(() => {
      const wanted = %s;
      const controls = [...document.querySelectorAll('button,a,[role=button]')].filter(c => {
        if (c.getBoundingClientRect().width <= 0) return false;
        return /(取消|删除|撤销)/.test((c.getAttribute('aria-label') || '') +
                                       (c.textContent || '').trim());
      });
      const actionable = controls.filter(c => {
        let p = c;
        for (let k = 0; k < 10 && p; k++) {
          if ((p.innerText || '').includes(wanted)) return true;
          p = p.parentElement;
        }
        return false;
      });
      if (actionable.length !== 1) return false;
      actionable[0].click();
      return true;
    })()""" % _json(_normalized_text(title))))


def _records_absent(title: str, content_id: str | None) -> bool:
    try:
        matches = archive_matches(title)
    except (RuntimeError, TimeoutError):
        return False
    if content_id:
        matches = [m for m in matches if m["content_id"] == str(content_id)]
    return not matches


def delete_once(submission: dict[str, Any], expected_uid: int | None = None,
                expected_name: str | None = None, confirm: bool = False,
                timeout: int = 180) -> dict[str, Any]:
    if not confirm:
        raise ValueError("ximalaya delete_once requires confirm=True")
    identity = require_identity(expected_uid, expected_name)
    if submission.get("status") != "verified" or not submission.get("submitted"):
        raise RuntimeError("ximalaya delete_once requires a verified submission dict")
    if int(submission.get("submit_clicks") or 0) != 1:
        raise RuntimeError("ximalaya delete_once requires submit_clicks == 1")
    if submission.get("created_by") != _CREATED_BY:
        raise RuntimeError("ximalaya delete_once refuses records not created by this module")
    title = str(submission.get("title") or "")
    content_id = submission.get("content_id")
    run_marker = str(submission.get("run_marker") or "")
    if not title or not content_id or not run_marker or run_marker not in title:
        raise RuntimeError("ximalaya delete_once requires exact content id, title and run marker")
    live = [m for m in archive_matches(title) if m["content_id"] == str(content_id)]
    if len(live) != 1:
        raise RuntimeError("ximalaya delete_once: live manager records for content_id %s: %s" %
                           (content_id, len(live)))
    live_record = live[0]
    if (_normalized_text(live_record.get("title")) != _normalized_text(title)
            or live_record.get("album_id") != str(submission.get("album_id") or "")):
        raise RuntimeError("ximalaya delete_once: live record identity differs from submission")
    submitted_mode = submission.get("mode")
    live_mode = live_record.get("mode")
    if live_mode != submitted_mode and not (submitted_mode == "scheduled" and live_mode == "immediate"):
        raise RuntimeError("ximalaya delete_once: live mode differs from submission")
    mode = live_mode
    delete_clicks = 0
    delete_error = ""
    if mode == "immediate":
        goto_url(SOUND_MANAGE_URL + live_record["album_id"])
        wait(5)
        delete_clicks = 1
        try:
            _api_post(TRACK_DELETE_API, {"trackId": int(content_id)}, "track deletion")
        except (RuntimeError, TimeoutError) as exc:
            delete_error = str(exc)
    elif mode == "scheduled":
        goto_url(TIME_PUBLISH_URL)
        wait(5)
        if not _scheduled_row_activate(title):
            raise RuntimeError("ximalaya scheduled row control for %r not uniquely actionable" % title)
        delete_clicks = 1
    else:
        raise RuntimeError("ximalaya delete_once unsupported mode %r" % mode)
    if mode == "scheduled":
        wait(1.5)
        _confirm_dialog_accept()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _records_absent(title, content_id):
            return {"status": "deleted", "content_id": str(content_id), "title": title,
                    "run_marker": run_marker, "delete_clicks": delete_clicks,
                    "live_mode": live_mode,
                    "account": {"uid": identity["uid"], "name": identity["name"]},
                    "verification_source": "reform_upload_api_absence"}
        wait(3.0)
    return {"status": "deletion_unverified", "content_id": str(content_id), "title": title,
            "run_marker": run_marker, "delete_clicks": delete_clicks,
            "live_mode": live_mode,
            "diagnostics": delete_error or "record still visible after deadline",
            "retry": False}


# ------------------------------------------------------------------ self check

def _self_check() -> None:
    assert UPLOAD_URL.startswith("https://www.ximalaya.com/reform-upload/")
    assert SOUND_MANAGE_URL.startswith("https://www.ximalaya.com/reform-upload/")
    assert EDIT_URL.endswith("/sound/edit/{}")
    assert set(PUBLISH_MODES) == {"immediate", "scheduled"}
    assert SCHEDULE_TIMEZONE == "Asia/Shanghai"
    constraints = publishing_constraints()
    assert constraints["schedule"]["min_lead_minutes"] == 120
    assert constraints["title"]["unit"] == TITLE_UNIT
    assert sorted(AUDIO_EXTENSIONS) == sorted(set(AUDIO_EXTENSIONS))
    assert ".m4a" in AUDIO_EXTENSIONS and ".mp3" in AUDIO_EXTENSIONS
    assert ".M4A" in REPLACEMENT_INPUT_SELECTOR


_self_check()
