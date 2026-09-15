import json
import re
from datetime import datetime
from pathlib import Path

import pytest

PUBLISHING_PATH = (
    Path(__file__).parents[2]
    / "agent-workspace/domain-skills/ximalaya/publishing.py"
)

ALBUM = {"album_id": "88294964",
         "title": "雅思口语播客 | 雅思口语常考话题 | 英语磨耳朵"}
TEST_UID = 123456789
TEST_NAME = "测试账号"


class FakePage:
    def __init__(self):
        self.uid = TEST_UID
        self.nickname = TEST_NAME
        self.logged_out = False
        self.albums = [dict(ALBUM, category_id=5, price_type_id=0,
                            custom_title="雅思口语素材磨耳朵")]
        self.scheduled_records = []
        self.tracks = []
        self.track_details = {}
        self.album_readback = ALBUM["title"]
        self.dropdown_open = False
        self.title_value = ""
        self.title_events = []
        self.description_html = ""
        self.description_textarea = ""
        self.scheduled_switch = False
        self.schedule_value = ""
        self.calendar_month = "2026年9月"
        self.calendar_navigations = []
        self.picked_day = None
        self.picked_time = None
        self.ok_clicked = False
        self.modal = ""
        self.crop_modal_open = True
        self.rows = [{"title": "audio-new", "status": "上传成功", "success": True}]
        self.cover_state = None
        self.cover_service_state = {
            "src": "/cover-b.jpg", "width": 1000, "height": 1000,
        }
        self.save_clicks = 0
        self.save_target = None
        self.edit_reopens = 0
        self.edit_validation_runs = 0
        self.edit_validation_token = None
        self.edit_track_data = None
        self.save_delay = 0
        self.readback_delay = 0
        self.upload_calls = []
        self.clicks = []
        self.gotos = []
        self.submit_disabled = False
        self.validation_errors = []
        self.confirm_modal_will_open = False
        self.menu_result = {"found": 1, "clicked": True}
        self.popover_delete = True
        self.confirm_dialog_available = True
        self.page_url = "https://www.ximalaya.com/reform-upload/page/webCenter/upload"
        self._times_patched = False

    # ---- js dispatcher -------------------------------------------------
    def js(self, script):
        s = script
        if "window.__ximalayaEditValidation = {token, status: 'pending'}" in s:
            match = re.search(r"\}\)\((.*?)\)\s*$", s, re.S)
            self.edit_validation_token = json.loads(match.group(1)) if match else None
            self.edit_validation_runs += 1
            return self.edit_validation_token
        if "result.token === token" in s and "__ximalayaEditValidation" in s:
            return {"token": self.edit_validation_token, "status": "ok",
                    "error_fields": []}
        if "/anchor-works-web/common/getCurrentUser" in s:
            if self.logged_out:
                return '{"status":200,"body":"{\\"msg\\":\\"成功\\",\\"data\\":{}}"}'
            return json.dumps({"status": 200, "body": json.dumps(
                {"msg": "成功", "data": {"uid": self.uid, "nickname": self.nickname}})})

        if "/reform-upload/album/choose" in s:
            return json.dumps({"status": 200, "body": json.dumps(
                {"ret": 0, "data": {"totalSize": len(self.albums),
                                    "infos": [{"albumId": int(a["album_id"]),
                                               "title": a["title"],
                                               "customTitle": a["custom_title"],
                                               "categoryId": a["category_id"],
                                               "priceTypeId": a["price_type_id"],
                                               "uploadSource": 0}
                                              for a in self.albums]}})})
        if "/reform-upload/scheduledPublish/list" in s:
            return json.dumps({"status": 200, "body": json.dumps(
                {"ret": 0, "data": {"totalSize": len(self.scheduled_records),
                                    "infos": self.scheduled_records}})})
        if "/reform-upload/manage/album/tracks" in s:
            match = re.search(r"albumId=(\d+)", s)
            wanted = match.group(1) if match else ""
            infos = [t for t in self.tracks if str(t.get("albumId")) == wanted]
            return json.dumps({"status": 200, "body": json.dumps(
                {"ret": 0, "data": {"totalSize": len(infos), "infos": infos}})})
        if "/revision/track/simple" in s:
            match = re.search(r"trackId=(\d+)", s)
            detail = self.track_details.get(match.group(1) if match else "")
            if detail is None:
                return json.dumps({"status": 200, "body": json.dumps(
                    {"ret": 200, "data": {}})})
            return json.dumps({"status": 200, "body": json.dumps(
                {"ret": 200, "data": {"trackInfo": detail["trackInfo"],
                                         "albumInfo": detail.get("albumInfo", {})}})})
        if "/reform-upload/anchorTrack/edit" in s:
            return json.dumps({"status": 200, "body": json.dumps(
                {"ret": 0, "data": self.edit_track_data or {}})})

        if "const el = Array.from(document.querySelectorAll" in s and "return {x:" in s:
            if ".track-1Tfey3X4" not in s and "确认发布" in s:
                return {"x": 10, "y": 20, "text": "确认发布"}
            return {"x": 10, "y": 20, "text": ""}

        if 'button[aria-label="选择专辑"]' in s and "return b ? (b.textContent" in s:
            return self.album_readback
        if "Boolean(document.querySelector('.scroll-item-8_W08IGr'))" in s:
            return self.dropdown_open
        if ".scroll-item-content-252FXLKk').click()" in s:
            self.dropdown_open = False
            return True

        if "请输入声音标题" in s and "return el.value === value" in s:
            match = re.search(r"\}\)\((.*?)\)\s*$", s, re.S)
            if match:
                try:
                    self.title_value = json.loads(match.group(1))
                except ValueError:
                    self.title_value = ""
            self.title_events = ["input", "change", "blur"]
            return True
        if "请输入声音标题" in s and "return i ? i.value" in s:
            return self.title_value

        if "ant-form-item" in s and "validation_errors" in s:
            return {
                "title": self.title_value,
                "title_counter": "",
                "album": self.album_readback,
                "category": "外语",
                "ai": "否",
                "cover": self.cover_state and json.loads(json.dumps(self.cover_state)),
                "description": self.description_html.strip(),
                "rows": list(self.rows),
                "scheduled": self.scheduled_switch,
                "schedule": self.schedule_value,
                "submit": {"disabled": self.submit_disabled, "text": "确认发布"},
                "modal": self.modal,
                "validation_errors": list(self.validation_errors),
            }

        if "setFieldsValue({richIntro: html})" in s:
            return "ok"

        if "KindEditor" in s and "editor.html(html)" in s:
            match = re.search(r"\}\)\((.*?)\)\s*$", s, re.S)
            if match:
                try:
                    html = json.loads(match.group(1))
                except ValueError:
                    html = ""
                self.description_textarea = html
                self.description_html = re.sub(r"<[^>]+>", " ", html)
            return "ok"

        if "anchor-cropper" in s and "确定" in s and "btn.click()" in s:
            return self.crop_modal_open
        if ".ant-modal" in s and "offsetParent ? 'open'" in s:
            return "open" if self.crop_modal_open else None
        if "ke-edit-iframe" in s and "insertHTML" in s:
            match = re.search(r"\}\)\((.*?)\)\s*$", s, re.S)
            if match:
                try:
                    html = json.loads(match.group(1))
                except ValueError:
                    html = ""
                self.description_textarea = html
                self.description_html = re.sub(r"<[^>]+>", " ", html)
            return True
        if "ke-edit-textarea" in s:
            return self.description_textarea
        if "contentDocument.body.innerText" in s and "ant-form-item" not in s:
            return self.description_html
        if "更换图片" in s:
            return json.dumps(self.cover_state) if self.cover_state else None

        if "保存" in s and "getBoundingClientRect" in s and "return {x:" in s:
            self.save_target = (30, 40)
            return {"x": 30, "y": 40}
        if "保存" in s and "memoizedProps.onClick" in s and "return true" in s:
            self.save_clicks += 1
            return True
        if "保存" in s and "button.click()" in s and "return true" in s:
            self.save_clicks += 1
            return True

        if "定时发布" in s and "aria-checked" in s and "sw.click()" not in s:
            return self.scheduled_switch
        if "定时发布" in s and "sw.click()" in s:
            self.scheduled_switch = not self.scheduled_switch
            return True

        if "ant-calendar-ym-select" in s:
            return self.calendar_month
        if "next-month-btn" in s and "el.click()" in s:
            self.calendar_navigations.append("next")
            year, month = map(int, re.fullmatch(r"(\d{4})年(\d{1,2})月", self.calendar_month).groups())
            month += 1
            if month == 13:
                year, month = year + 1, 1
            self.calendar_month = "%d年%d月" % (year, month)
            return True
        if "prev-month-btn" in s and "el.click()" in s:
            self.calendar_navigations.append("prev")
            year, month = map(int, re.fullmatch(r"(\d{4})年(\d{1,2})月", self.calendar_month).groups())
            month -= 1
            if month == 0:
                year, month = year - 1, 12
            self.calendar_month = "%d年%d月" % (year, month)
            return True
        if "ant-calendar-date" in s and "cells[0].querySelector" in s:
            match = re.search(r'parseInt\("(.*?)"', s)
            self.picked_day = int(match.group(1)) if match else None
            return True
        if "ant-calendar-time-picker-select" in s:
            values = re.findall(r'\("([^"]+)"\)', s)
            self.picked_time = values[-2:]
            return True
        if "ant-calendar-ok-btn" in s:
            self.ok_clicked = True
            self.schedule_value = self.pending_schedule
            return True
        if 'button[aria-label="确认发布"]' in s and "b.click()" in s:
            self.submit_js_clicks = getattr(self, "submit_js_clicks", 0) + 1
            return True
        if "input.ant-calendar-picker-input" in s and "return i ? i.value" in s:
            return self.schedule_value
        if ".ant-calendar" in s and "offsetParent ? 'open'" in s:
            return "open"
        if "input.ant-calendar-picker-input" in s and "i.click()" in s:
            return True
        if "input.ant-calendar-picker-input" in s:
            return self.schedule_value

        if "upload-list-item-2or8pi-8" in s:
            return list(self.rows)

        if "location.href" in s and "ant-form-item" not in s:
            return self.gotos[-1] if self.gotos else ""
        if ".ant-modal" in s and "includes('确认')" in s:
            return "open" if self.confirm_modal_will_open else None
        if ".ant-modal" in s and "'确定'" in s and "btn.click()" in s:
            return self.crop_modal_open
        if "确 定" in s and "btn.click()" in s:
            return self.confirm_dialog_available
        if ".track-1Tfey3X4" in s:
            return json.dumps(self.menu_result)
        if "sound-more-popover" in s:
            return self.popover_delete
        if "取消|删除|撤销" in s:
            return True
        return None

    # ---- injected helpers ----------------------------------------------
    def click_at_xy(self, x, y):
        self.clicks.append((x, y))
        if self.save_target == (x, y):
            self.save_clicks += 1
            self.save_target = None

    def goto_url(self, url):
        self.gotos.append(url)
        if "/reform-upload/page/sound/edit/" in url:
            self.edit_reopens += 1

    def upload_file(self, selector, path):
        self.upload_calls.append((selector, Path(path)))
        if 'accept*="png"' in selector and self.cover_state is None:
            self.cover_state = dict(self.cover_service_state)


def load_publishing(page=None):
    page = page or FakePage()
    page.pending_schedule = ""
    namespace = {
        "js": page.js,
        "wait": lambda seconds=0: None,
        "click_at_xy": page.click_at_xy,
        "goto_url": page.goto_url,
        "upload_file": page.upload_file,
        "page_info": lambda: {"url": page.page_url},
    }
    exec(compile(PUBLISHING_PATH.read_text(), str(PUBLISHING_PATH), "exec"), namespace)
    # route schedule readback: ok button stores pending value
    original_js = page.js

    def js_with_schedule(script):
        if "ant-calendar-ok-btn" in script:
            page.schedule_value = page.pending_schedule
        return original_js(script)

    page.js = js_with_schedule
    namespace["js"] = js_with_schedule
    return namespace, page


# ---------------------------------------------------------------- identity

def test_account_identity_rejects_logged_out_session():
    namespace, page = load_publishing()
    page.logged_out = True
    with pytest.raises(RuntimeError, match="auth_required"):
        namespace["account_identity"]()


def test_require_identity_only_requires_a_logged_in_session():
    namespace, page = load_publishing()
    observed = namespace["require_identity"](999, "其他名字")
    assert observed == {"uid": TEST_UID, "name": TEST_NAME, "logged_in": True}


def test_require_identity_still_rejects_a_logged_out_session():
    namespace, page = load_publishing()
    page.logged_out = True
    with pytest.raises(RuntimeError, match="auth_required"):
        namespace["require_identity"](999, "其他名字")


def test_constraints_have_no_unknown_critical_values():
    namespace, _ = load_publishing()
    constraints = namespace["publishing_constraints"]()
    assert constraints["title"]["max"] == 40
    assert constraints["title"]["unit"] == "utf16_code_units"
    assert constraints["schedule"]["min_lead_minutes"] == 120
    assert constraints["schedule"]["timezone"] == "Asia/Shanghai"
    assert constraints["schedule"]["granularity"].startswith("minute")
    assert constraints["cover"]["max_bytes"] == 10_485_760
    assert constraints["audio"]["formats_count"] == 11
    assert constraints["schedule"]["max_horizon_evidence"] == "client_observed_server_unknown"
    assert "album" not in constraints
    blob = json.dumps(constraints, ensure_ascii=False)
    for critical in ("min_lead_evidence", "granularity_evidence", "evidence"):
        assert critical in blob
    assert '"max_bytes": 1073741824' in blob


# ---------------------------------------------------------------- upload prep

def test_prepare_upload_rejects_missing_empty_and_unsupported_files(tmp_path):
    namespace, page = load_publishing()
    with pytest.raises(ValueError, match="missing or empty"):
        namespace["prepare_upload"](str(tmp_path / "missing.m4a"), "标题", TEST_UID)
    empty = tmp_path / "empty.mp3"
    empty.touch()
    with pytest.raises(ValueError, match="missing or empty"):
        namespace["prepare_upload"](str(empty), "标题", TEST_UID)
    bad = tmp_path / "clip.txt"
    bad.write_bytes(b"x" * 2_000_000)
    with pytest.raises(ValueError, match="unsupported audio extension"):
        namespace["prepare_upload"](str(bad), "标题", TEST_UID)
    tiny = tmp_path / "tiny.mp3"
    tiny.write_bytes(b"x" * 100)
    with pytest.raises(ValueError, match="below"):
        namespace["prepare_upload"](str(tiny), "标题", TEST_UID)
    assert page.upload_calls == []


def test_prepare_upload_blocks_exact_title_duplicate_before_upload():
    namespace, page = load_publishing()
    page.tracks = [{"albumId": 88294964, "trackId": 1, "title": "已有标题",
                    "albumTitle": ALBUM["title"], "status": "已发布"}]
    page.pending_schedule = ""
    with pytest.raises(RuntimeError, match="already exists"):
        namespace["prepare_upload"]("/tmp/any.mp3", "已有标题", TEST_UID)
    assert page.upload_calls == []


def test_prepare_upload_waits_for_explicit_processing_completion(tmp_path):
    namespace, page = load_publishing()
    audio = tmp_path / "audio-new.m4a"
    audio.write_bytes(b"x" * 2_000_000)
    result = namespace["prepare_upload"](str(audio), "全新标题", TEST_UID)
    assert result["upload_completed"]["status"].startswith("上传成功")
    assert page.upload_calls[0][0] == "input[type=file].webuploader-element-invisible"
    page.rows = []
    with pytest.raises(TimeoutError):
        namespace["prepare_upload"](str(audio), "另一标题", TEST_UID, timeout=0)


def test_prepare_upload_rejects_the_wrong_page_before_upload(tmp_path):
    namespace, page = load_publishing()
    page.page_url = "https://www.ximalaya.com/reform-upload/page/sound/manage/7980411"
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"x" * 2_000_000)
    with pytest.raises(RuntimeError, match="exact upload page"):
        namespace["prepare_upload"](str(audio), "标题", TEST_UID)
    assert page.upload_calls == []


def test_album_tracks_paginates_without_a_reported_total():
    namespace, _ = load_publishing()
    calls = []
    pages = [{"infos": [{"trackId": n} for n in range(50)]},
             {"infos": [{"trackId": 50}]}]

    def api_get(url, context):
        calls.append((url, context))
        return pages.pop(0)

    namespace["_api_get"] = api_get
    assert len(namespace["_album_tracks"]("7")) == 51
    assert len(calls) == 2


def test_list_album_tracks_returns_newest_first_with_episode_numbers():
    namespace, page = load_publishing()
    page.tracks = [
        {"trackId": 12, "albumId": 88294964, "title": "最新", "duration": 90,
         "uploadId": "resource-12", "anchorId": 999, "updatedAt": "2026-09-14 12:00:00"},
        {"trackId": 11, "albumId": 88294964, "title": "中间", "duration": 80,
         "uploadId": "resource-11", "anchorId": TEST_UID, "updatedAt": "2026-09-13 12:00:00"},
        {"trackId": 10, "albumId": 88294964, "title": "最早", "duration": 70,
         "uploadId": "resource-10", "anchorId": TEST_UID, "updatedAt": "2026-09-12 12:00:00"},
    ]
    result = namespace["list_album_tracks"]("88294964", TEST_UID, TEST_NAME)
    assert [item["track_id"] for item in result] == ["12", "11", "10"]
    assert [item["episode_number"] for item in result] == [3, 2, 1]
    assert all(item["album_total"] == 3 for item in result)
    assert result[0]["audio_resource_id"] == "resource-12"
    assert result[0]["account_uid"] == "999"


def test_download_owned_track_requires_login_and_exact_track(tmp_path):
    namespace, page = load_publishing()
    track = {"track_id": "42", "album_id": "88294964", "title": "精确标题"}
    page.logged_out = True
    namespace["_best_playable"] = lambda *args: pytest.fail("download started before login gate")
    with pytest.raises(RuntimeError, match="auth_required"):
        namespace["download_owned_track_once"](track, str(tmp_path), TEST_UID, TEST_NAME)

    page.logged_out = False
    namespace["track_evidence"] = lambda *args: dict(track, title="其他标题",
                                                       account_uid="999")
    with pytest.raises(RuntimeError, match="target mismatch"):
        namespace["download_owned_track_once"](track, str(tmp_path), TEST_UID, TEST_NAME)


def test_download_owned_track_writes_part_then_verified_file(tmp_path):
    namespace, _ = load_publishing()
    track = {"track_id": "42", "album_id": "88294964", "title": "精确标题"}
    namespace["track_evidence"] = lambda *args: dict(track, account_uid="999")
    namespace["_best_playable"] = lambda track_id: {
        "quality": "MP3_128", "url": "https://audio.xmcdn.com/track-42.mp3",
        "expected_size": 11,
    }

    class Response:
        def __init__(self):
            self.sent = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            if self.sent:
                return b""
            self.sent = True
            return b"audio-bytes"

    namespace["urlopen"] = lambda request, timeout=0: Response()
    namespace["_probe_download"] = lambda path: {
        "codec": "mp3", "duration": 90.0,
    }
    result = namespace["download_owned_track_once"](track, str(tmp_path), TEST_UID, TEST_NAME)
    target = Path(result["path"])
    assert result["status"] == "verified"
    assert target.is_file()
    assert target.read_bytes() == b"audio-bytes"
    assert result["bytes"] == 11
    assert not Path(str(target) + ".part").exists()


def test_archive_matches_fails_closed_when_an_album_cannot_be_read():
    namespace, _ = load_publishing()
    namespace["list_albums"] = lambda: [{"album_id": "7", "title": "专辑"}]
    namespace["_album_tracks"] = lambda album_id: (_ for _ in ()).throw(
        RuntimeError("album list unavailable"))
    with pytest.raises(RuntimeError, match="album list unavailable"):
        namespace["archive_matches"]("标题")


# ---------------------------------------------------------------- album / cover

def test_select_album_requires_exact_stable_id_and_readback():
    namespace, page = load_publishing()
    page.dropdown_open = True
    result = namespace["select_album"]("88294964", ALBUM["title"])
    assert result == {"album_id": "88294964", "album_title": ALBUM["title"],
                      "readback": True}
    with pytest.raises(RuntimeError, match="not found"):
        namespace["select_album"]("999")
    page.album_readback = "另一个专辑"
    page.dropdown_open = True
    with pytest.raises(TimeoutError):
        namespace["select_album"]("88294964", timeout=0)


def test_select_album_refuses_ambiguous_duplicate_titles():
    namespace, page = load_publishing()
    page.albums.append(dict(page.albums[0], album_id="7980411"))
    with pytest.raises(RuntimeError, match="title is not unique"):
        namespace["select_album"]("88294964")
    assert page.clicks == []


def test_custom_cover_validates_file_and_returns_exact_metadata(tmp_path):
    namespace, page = load_publishing()
    from PIL import Image
    cover = tmp_path / "cover.png"
    Image.new("RGB", (1080, 1080)).save(cover)
    page.crop_modal_open = True
    page.cover_state = {"src": "http://fdfs.xmcdn.com/x.jpeg", "width": 1080, "height": 1080}
    result = namespace["set_custom_cover"](str(cover), timeout=0)
    assert result["filename"] == "cover.png"
    assert (result["width"], result["height"]) == (1080, 1080)
    assert result["crop_confirmed"] is True
    assert result["readback"]["width"] == 1080
    assert page.upload_calls[0][0] == 'input[type=file][accept*="png"]'
    small = tmp_path / "small.png"
    Image.new("RGB", (400, 400)).save(small)
    with pytest.raises(ValueError, match="square"):
        namespace["set_custom_cover"](str(small), timeout=0)


# ---------------------------------------------------------------- text setters

def test_text_limits_follow_discovered_counting_semantics():
    namespace, _ = load_publishing()
    set_title = namespace["set_title"]
    assert namespace["set_title"](  # CJK counts 1
        "中" * 40, timeout=0) == "中" * 40
    emoji = "🎵" * 40
    with pytest.raises(ValueError, match="1..40"):
        set_title(emoji)
    with pytest.raises(ValueError, match="1..40"):
        set_title("A" * 41)
    assert set_title("A" * 40, timeout=0) == "A" * 40


def test_title_setter_dispatches_framework_events():
    namespace, page = load_publishing()
    namespace["set_title"]("我的标题", timeout=0)
    assert page.title_value == "我的标题"
    assert page.title_events == ["input", "change", "blur"]


def test_description_sets_editor_and_reads_back_normalized_text():
    namespace, page = load_publishing()
    result = namespace["set_description"]("  第一行\n第二行  ", timeout=0)
    assert result == "第一行 第二行"
    assert "第一行 第二行" in page.description_textarea


# ---------------------------------------------------------------- modes / schedule

def test_publish_mode_accepts_only_immediate_or_scheduled():
    namespace, page = load_publishing()
    with pytest.raises(ValueError, match="immediate or scheduled"):
        namespace["set_publish_mode"]("draft")
    result = namespace["set_publish_mode"]("scheduled")
    assert result == {"mode": "scheduled", "switch_checked": True}
    result = namespace["set_publish_mode"]("immediate")
    assert result == {"mode": "immediate", "switch_checked": False}


def test_schedule_datetime_enforces_timezone_lead_horizon_and_granularity(monkeypatch):
    namespace, page = load_publishing()

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 7, 16, 24, 30, tzinfo=tz)

    monkeypatch.setitem(namespace, "datetime", FixedDateTime)
    page.scheduled_switch = True
    page.pending_schedule = "2026-09-07 18:25:00"
    result = namespace["set_schedule_datetime"]("2026-09-07 18:25")
    assert result == {"date": "2026-09-07", "time": "18:25",
                      "timezone": "Asia/Shanghai", "mode": "scheduled",
                      "readback": "2026-09-07 18:25:00"}
    with pytest.raises(ValueError, match="two-hour minimum lead"):
        namespace["set_schedule_datetime"]("2026-09-07 18:23")
    with pytest.raises(ValueError, match="YYYY-MM-DD HH:MM"):
        namespace["set_schedule_datetime"]("2026-09-07 18:2x")
    with pytest.raises(ValueError, match="YYYY-MM-DD HH:MM"):
        namespace["set_schedule_datetime"]("2026-09-07 18:25:30")


# ---------------------------------------------------------------- snapshot / submit

def _snapshot_fields():
    return {
        "identity": {"uid": TEST_UID, "name": TEST_NAME, "logged_in": True},
        "upload_ready": True, "rows": [{"title": "audio-new", "status": "上传成功",
                                        "success": True}],
        "title": "标题", "title_counter": "2/40",
        "album": ALBUM["title"], "category": "外语", "ai": "否",
        "cover": {"src": "x", "width": 1080, "height": 1080},
        "description": "简介", "scheduled": True,
        "schedule": "2026-09-07 18:25:00",
        "submit": {"disabled": False, "text": "确认发布"},
        "modal": "", "validation_errors": [],
    }


def test_submission_snapshot_contains_every_required_field():
    namespace, _ = load_publishing()
    snapshot = namespace["submission_snapshot"]()
    assert set(snapshot) >= {
        "identity", "upload_ready", "rows", "title", "title_counter", "album",
        "category", "ai", "cover", "description", "scheduled", "schedule",
        "submit", "modal", "validation_errors"}
    assert snapshot["upload_ready"] is True
    assert snapshot["submit"]["text"] == "确认发布"
    assert snapshot["scheduled"] is False  # switch starts off in FakePage


def _configure_submit(namespace, page, schedule="2026-09-07 18:25:00",
                      mode="scheduled"):
    namespace["require_identity"] = lambda uid, name=None: {
        "uid": uid, "name": name, "logged_in": True}
    namespace["archive_matches"] = lambda title: []
    snapshot = _snapshot_fields()
    snapshot["scheduled"] = mode == "scheduled"
    snapshot["schedule"] = schedule if mode == "scheduled" else ""
    calls = {"n": 0}

    def snapshot_fn():
        calls["n"] += 1
        return dict(snapshot)
    namespace["submission_snapshot"] = snapshot_fn
    namespace["manager_evidence"] = lambda title, cid=None, sched=None, attempts=3: {
        "content_id": "42", "title": title, "album_id": "88294964",
        "album_name": ALBUM["title"], "state": "审核中" if mode == "immediate" else "定时",
        "mode": mode, "schedule": schedule, "match_count": 1, "latest": True,
        "list_loads": 1, "source": "reform_upload_api", "schedule_match": True}
    return snapshot, calls


def test_submit_once_requires_two_stable_valid_snapshots():
    namespace, page = load_publishing()
    _configure_submit(namespace, page)
    calls = {"n": 0}
    base = _snapshot_fields()
    mutable = dict(base)

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            mutable["title"] = "变化中"
            return dict(mutable)
        mutable["title"] = "标题"
        return dict(mutable)
    namespace["submission_snapshot"] = flaky
    with pytest.raises(RuntimeError, match="not stable"):
        namespace["submit_once"]("标题", TEST_UID, TEST_NAME, "scheduled",
                                 "2026-09-07 18:25", "RUN", timeout=0)
    assert page.clicks == []


def test_submit_once_clicks_exactly_once_then_reconciles_read_only():
    namespace, page = load_publishing()
    _configure_submit(namespace, page)
    result = namespace["submit_once"]("标题", TEST_UID, TEST_NAME,
                                      "scheduled", "2026-09-07 18:25", "RUN",
                                      timeout=1)
    assert result["status"] == "verified"
    assert result["submit_clicks"] == 1
    assert result["content_id"] == "42"
    assert result["created_by"] == "ximalaya_domain_skill"
    assert result["run_marker"] == "RUN"
    assert page.submit_js_clicks == 1  # single activation on the submit control


def test_submit_once_returns_nonretryable_unknown_after_ambiguous_click():
    namespace, page = load_publishing()
    _configure_submit(namespace, page)

    def missing_manager(*args, **kwargs):
        raise RuntimeError("no record yet")
    namespace["manager_evidence"] = missing_manager
    result = namespace["submit_once"]("标题", TEST_UID, TEST_NAME,
                                      "scheduled", "2026-09-07 18:25", "RUN",
                                      timeout=0.01)
    assert result["status"] == "submission_unverified"
    assert result["submitted"] is True
    assert result["submit_clicks"] == 1
    assert result["retry"] is False
    assert page.submit_js_clicks == 1


def test_manager_evidence_requires_exact_title_and_content_id():
    namespace, page = load_publishing()
    with pytest.raises(RuntimeError, match="no record"):
        namespace["manager_evidence"]("不存在", attempts=1)
    page.scheduled_records = [{"trackId": 7, "albumId": 88294964,
                               "albumTitle": ALBUM["title"],
                               "title": "标题X", "status": "定时发布中",
                               "publishTime": "2026-09-07 18:25"}]
    page.tracks = []
    evidence = namespace["manager_evidence"]("标题X", content_id="7",
                                             expected_schedule="2026-09-07 18:25",
                                             attempts=2)
    assert evidence["content_id"] == "7"
    assert evidence["mode"] == "scheduled"
    assert evidence["schedule_match"] is True
    assert evidence["list_loads"] == 1
    page.scheduled_records = [{"trackId": 7, "albumId": 88294964,
                               "albumTitle": ALBUM["title"],
                               "title": "标题X", "status": "已排期",
                               "publishTime": "2026-09-07 18:25"}]
    with pytest.raises(RuntimeError, match="time mismatch"):
        namespace["manager_evidence"]("标题X", content_id="7",
                                      expected_schedule="2026-09-09 09:09",
                                      attempts=1)


def _track_fixture(duration=90, upload_id="upload-before", updated_at="2026-09-07 10:00:00"):
    title = "BH替换标题-RUN"
    item = {
        "trackId": 42, "albumId": 88294964, "albumTitle": ALBUM["title"],
        "title": title, "duration": duration, "uploadId": upload_id,
        "recordId": 99, "coverPath": "/cover.jpg", "fullCoverPath": "/cover.jpg",
        "intro": "简介", "categoryId": 5,
        "trackStatusInfo": {"trackStatus": 1, "isPublic": True},
    }
    detail = {
        "trackId": 42, "anchorUid": TEST_UID, "title": title,
        "duration": duration, "lastUpdate": "2026-09-07 10:00:00",
        "updatedAt": updated_at, "coverPath": "//imagev2.xmcdn.com/cover.jpg",
        "richIntro": "简介", "approveStatus": 1, "visibleStatus": 0,
    }
    return item, {"trackInfo": detail, "albumInfo": {"albumId": 88294964,
                                                          "title": ALBUM["title"]}}


def test_track_evidence_requires_exact_album_track_and_title():
    namespace, page = load_publishing()
    item, detail = _track_fixture()
    page.tracks = [item]
    page.track_details["42"] = detail
    evidence = namespace["track_evidence"]("88294964", "42", item["title"])
    assert evidence["track_id"] == "42"
    assert evidence["album_id"] == "88294964"
    assert evidence["title"] == item["title"]
    assert evidence["duration_seconds"] == 90.0
    assert evidence["audio_resource_id"] == "upload-before"
    with pytest.raises(RuntimeError, match="title mismatch"):
        namespace["track_evidence"]("88294964", "42", "其他标题")


def test_track_evidence_rejects_missing_or_ambiguous_records():
    namespace, page = load_publishing()
    with pytest.raises(RuntimeError, match="one exact album/track match"):
        namespace["track_evidence"]("88294964", "42")
    item, detail = _track_fixture()
    page.tracks = [item, dict(item)]
    page.track_details["42"] = detail
    with pytest.raises(RuntimeError, match="one exact album/track match"):
        namespace["track_evidence"]("88294964", "42")


def _replacement_track():
    return {"track_id": "42", "album_id": "88294964", "title": "BH替换标题-RUN"}


def _replacement_evidence(duration=90, upload_id="upload-before", updated_at="2026-09-07 10:00:00"):
    return {
        "track_id": "42", "album_id": "88294964", "album_name": ALBUM["title"],
        "title": "BH替换标题-RUN", "duration_seconds": float(duration),
        "status": 1, "published_at": "2026-09-07 10:00:00",
        "updated_at": updated_at, "cover_path": "/cover.jpg", "description": "简介",
        "category_id": 5, "visibility": 0, "publish_state": 1,
        "audio_resource_id": upload_id, "audio_resource_path": "/track/42",
    }


def test_edit_track_evidence_uses_authenticated_creator_state():
    namespace, page = load_publishing()
    page.edit_track_data = {
        "trackInfo": {
            "trackId": 42, "albumId": 88294964, "title": "BH替换标题-RUN",
            "coverPath": "https://imagev2.xmcdn.com/group/cover-b.jpg",
            "categoryId": 5, "visibleCrowdType": 0, "uploadId": "upload-after",
            "anchorId": TEST_UID, "trackStatusInfo": {"trackStatus": 1},
        },
        "richIntro": "<p>简介 B</p>",
    }
    result = namespace["_edit_track_evidence"](
        "88294964", "42", "BH替换标题-RUN",
    )
    assert result["description"] == "简介 B"
    assert result["cover_path"] == "/group/cover-b.jpg"
    assert result["audio_resource_id"] == "upload-after"
    assert result["account_uid"] == str(TEST_UID)
    assert result["edit_source"] == "anchor_track_edit"


def test_update_track_description_once_requires_confirm_and_exact_track():
    namespace, page = load_publishing()
    track = _replacement_track()
    with pytest.raises(ValueError, match="confirm=True"):
        namespace["update_track_description_once"](track, "简介B", TEST_UID, TEST_NAME)
    namespace["_current_track_for_edit"] = lambda *args: _replacement_evidence() | {
        "title": "其他标题",
    }
    with pytest.raises(RuntimeError, match="target mismatch"):
        namespace["update_track_description_once"](
            track, "简介B", TEST_UID, TEST_NAME, confirm=True,
        )
    assert page.gotos == []


def test_update_track_description_once_saves_once_and_reopens_for_readback():
    namespace, page = load_publishing()
    track = _replacement_track()
    before = _replacement_evidence()
    after = dict(before, description="Browser Harness 后台焦点回归测试 B")
    page.description_html = before["description"]
    states = iter((before, after))
    namespace["track_evidence"] = lambda *args: next(states)
    edit_states = iter((before, after))
    namespace["_edit_track_evidence"] = lambda *args: next(edit_states)
    result = namespace["update_track_description_once"](
        track, "Browser Harness 后台焦点回归测试 B", TEST_UID, TEST_NAME,
        confirm=True, timeout=1,
    )
    assert result["status"] == "description_updated"
    assert result["save_clicks"] == page.save_clicks == 1
    assert page.edit_validation_runs == 1
    assert page.edit_reopens == 2
    assert result["after"]["description"] == "Browser Harness 后台焦点回归测试 B"
    assert result["retry"] is False


def test_update_track_description_once_returns_nonretryable_unknown():
    namespace, page = load_publishing()
    track = _replacement_track()
    before = _replacement_evidence()
    namespace["track_evidence"] = lambda *args: before
    namespace["_edit_track_evidence"] = lambda *args: before
    namespace["_wait_edit_form_ready"] = lambda *args: True
    namespace["_read_edit_description"] = lambda *args: (_ for _ in ()).throw(
        TimeoutError("description readback delayed"))
    result = namespace["update_track_description_once"](
        track, "简介B", TEST_UID, TEST_NAME, confirm=True, timeout=1,
    )
    assert result["status"] == "description_update_unverified"
    assert result["save_clicks"] == page.save_clicks == 1
    assert result["retry"] is False


def test_replace_track_cover_once_requires_confirm_and_exact_track(tmp_path):
    namespace, page = load_publishing()
    from PIL import Image
    cover = tmp_path / "cover.png"
    Image.new("RGB", (1000, 1000)).save(cover)
    track = _replacement_track()
    with pytest.raises(ValueError, match="confirm=True"):
        namespace["replace_track_cover_once"](track, str(cover), TEST_UID, TEST_NAME)
    namespace["_current_track_for_edit"] = lambda *args: _replacement_evidence() | {
        "track_id": "43",
    }
    with pytest.raises(RuntimeError, match="target mismatch"):
        namespace["replace_track_cover_once"](
            track, str(cover), TEST_UID, TEST_NAME, confirm=True,
        )
    assert page.gotos == []
    assert page.upload_calls == []


def test_replace_track_cover_once_saves_once_and_verifies_path_change(tmp_path):
    namespace, page = load_publishing()
    from PIL import Image
    cover = tmp_path / "cover.png"
    Image.new("RGB", (1000, 1000)).save(cover)
    track = _replacement_track()
    before = _replacement_evidence()
    after = dict(before, cover_path="/cover-b.jpg")
    states = iter((before, after))
    namespace["track_evidence"] = lambda *args: next(states)
    edit_states = iter((before, after))
    namespace["_edit_track_evidence"] = lambda *args: next(edit_states)
    result = namespace["replace_track_cover_once"](
        track, str(cover), TEST_UID, TEST_NAME, confirm=True, timeout=1,
    )
    assert result["status"] == "cover_replaced"
    assert result["cover_uploads"] == 1
    assert result["crop_confirms"] == 1
    assert result["save_clicks"] == page.save_clicks == 1
    assert page.edit_validation_runs == 1
    assert result["after"]["cover_path"] == "/cover-b.jpg"
    assert result["retry"] is False


def test_replace_track_cover_once_returns_nonretryable_unknown(tmp_path):
    namespace, page = load_publishing()
    from PIL import Image
    cover = tmp_path / "cover.png"
    Image.new("RGB", (1000, 1000)).save(cover)
    track = _replacement_track()
    before = _replacement_evidence()
    namespace["track_evidence"] = lambda *args: before
    namespace["_edit_track_evidence"] = lambda *args: before
    result = namespace["replace_track_cover_once"](
        track, str(cover), TEST_UID, TEST_NAME, confirm=True, timeout=0.01,
    )
    assert result["status"] == "cover_replacement_unverified"
    assert result["cover_uploads"] == 1
    assert result["crop_confirms"] == 1
    assert result["save_clicks"] == page.save_clicks == 1
    assert result["retry"] is False
    assert len(page.upload_calls) == 1


def test_ximalaya_domain_skill_never_activates_or_brings_tab_to_front():
    source = PUBLISHING_PATH.read_text()
    for forbidden in (
        "activate_tab(", "activate=True", "Target.activateTarget", "Page.bringToFront",
    ):
        assert forbidden not in source


def test_replace_sound_once_requires_confirm_and_exact_snapshot(tmp_path):
    namespace, page = load_publishing()
    track = _replacement_track()
    with pytest.raises(ValueError, match="confirm=True"):
        namespace["replace_sound_once"](track, "/tmp/missing.m4a", TEST_UID)
    audio = tmp_path / "replacement.m4a"
    audio.write_bytes(b"x" * 2_000_000)
    namespace["_probed_audio"] = lambda path: {"duration": "268.329796"}
    namespace["track_evidence"] = lambda *args: dict(track, title="其他标题")
    with pytest.raises(RuntimeError, match="target mismatch"):
        namespace["replace_sound_once"](track, str(audio), TEST_UID,
                                          TEST_NAME, confirm=True, timeout=0)
    assert page.gotos == ["https://www.ximalaya.com/reform-upload/page/sound/manage/88294964"]
    assert page.upload_calls == []


def test_replace_sound_once_validates_file_before_page_mutation():
    namespace, page = load_publishing()
    with pytest.raises(ValueError, match="missing or empty"):
        namespace["replace_sound_once"](_replacement_track(), "/tmp/missing.m4a",
                                          TEST_UID, TEST_NAME, confirm=True)
    assert page.gotos == []
    assert page.upload_calls == []


def test_replace_sound_once_requires_probe_duration_before_page_mutation(tmp_path):
    namespace, page = load_publishing()
    audio = tmp_path / "replacement.m4a"
    audio.write_bytes(b"x" * 2_000_000)
    namespace["_probed_audio"] = lambda path: {}
    with pytest.raises(ValueError, match="readable positive duration"):
        namespace["replace_sound_once"](_replacement_track(), str(audio), TEST_UID,
                                          TEST_NAME, confirm=True)
    assert page.gotos == []
    assert page.upload_calls == []


def test_replace_sound_once_blocks_logged_out_or_live_record_mismatch(tmp_path):
    namespace, page = load_publishing()
    audio = tmp_path / "replacement.m4a"
    audio.write_bytes(b"x" * 2_000_000)
    page.logged_out = True
    with pytest.raises(RuntimeError, match="auth_required"):
        namespace["replace_sound_once"](_replacement_track(), str(audio), TEST_UID,
                                          TEST_NAME, confirm=True)
    assert page.gotos == []
    page.logged_out = False
    namespace["track_evidence"] = lambda *args: _replacement_evidence(upload_id="other") | {
        "track_id": "43"}
    namespace["_probed_audio"] = lambda path: {"duration": "268.329796"}
    with pytest.raises(RuntimeError, match="target mismatch"):
        namespace["replace_sound_once"](_replacement_track(), str(audio), TEST_UID,
                                          TEST_NAME, confirm=True, timeout=0)
    assert page.gotos == ["https://www.ximalaya.com/reform-upload/page/sound/manage/88294964"]


def test_replace_sound_once_opens_exact_row_and_uploads_once(tmp_path):
    namespace, page = load_publishing()
    page.menu_result = {"found": 1, "clicked": True, "x": 99, "y": 55}
    page.popover_delete = False
    audio = tmp_path / "replacement.m4a"
    audio.write_bytes(b"x" * 2_000_000)
    before = _replacement_evidence()
    namespace["track_evidence"] = lambda *args: before
    namespace["_probed_audio"] = lambda path: {"duration": "268.329796", "size": 2_000_000}
    result = namespace["replace_sound_once"](_replacement_track(), str(audio), TEST_UID,
                                              TEST_NAME, confirm=True, timeout=0.01)
    assert result["status"] == "replacement_unverified"
    assert result["replacement_uploads"] == 1
    assert page.gotos == ["https://www.ximalaya.com/reform-upload/page/sound/manage/88294964"]
    assert len(page.upload_calls) == 1
    assert page.upload_calls[0][0] == namespace["REPLACEMENT_INPUT_SELECTOR"]
    assert page.clicks == [(99, 55), (10, 20)]


def test_replace_sound_once_verifies_same_track_with_changed_audio(tmp_path):
    namespace, _ = load_publishing()
    audio = tmp_path / "replacement.m4a"
    audio.write_bytes(b"x" * 2_000_000)
    before = _replacement_evidence()
    after = _replacement_evidence(268, "upload-after", "2026-09-08 07:00:00")
    states = iter((before, after))
    namespace["track_evidence"] = lambda *args: next(states)
    namespace["_probed_audio"] = lambda path: {"duration": "268.329796", "size": 2_000_000}
    result = namespace["replace_sound_once"](_replacement_track(), str(audio), TEST_UID,
                                              TEST_NAME, confirm=True, timeout=1)
    assert result["status"] == "replaced"
    assert result["replacement_uploads"] == 1
    assert result["retry"] is False
    assert result["before"]["track_id"] == result["after"]["track_id"] == "42"
    assert result["before"]["title"] == result["after"]["title"]
    assert result["after"]["duration_seconds"] == 268


def test_replace_sound_once_returns_nonretryable_unknown_without_second_upload(tmp_path):
    namespace, page = load_publishing()
    audio = tmp_path / "replacement.m4a"
    audio.write_bytes(b"x" * 2_000_000)
    before = _replacement_evidence()
    namespace["track_evidence"] = lambda *args: before
    namespace["_probed_audio"] = lambda path: {"duration": "268.329796", "size": 2_000_000}
    result = namespace["replace_sound_once"](_replacement_track(), str(audio), TEST_UID,
                                              TEST_NAME, confirm=True, timeout=0.01)
    assert result["status"] == "replacement_unverified"
    assert result["replacement_uploads"] == 1
    assert result["retry"] is False
    assert len(page.upload_calls) == 1


# ---------------------------------------------------------------- deletion

def _verified_submission(mode="scheduled"):
    return {"status": "verified", "submitted": True, "submit_clicks": 1,
            "content_id": "42", "title": "BH标题-RUN", "run_marker": "RUN",
            "mode": mode, "schedule": "2026-09-07 18:25",
            "album_id": "88294964", "album_name": ALBUM["title"],
            "account": {"uid": TEST_UID, "name": TEST_NAME},
            "created_by": "ximalaya_domain_skill"}


def test_delete_once_requires_confirm_and_verified_submission():
    namespace, page = load_publishing()
    with pytest.raises(ValueError, match="confirm=True"):
        namespace["delete_once"](_verified_submission(), TEST_UID, TEST_NAME,
                                 confirm=False, timeout=0)
    bad = _verified_submission()
    bad["status"] = "submission_unverified"
    with pytest.raises(RuntimeError, match="verified submission"):
        namespace["delete_once"](bad, TEST_UID, TEST_NAME, confirm=True, timeout=0)
    bad = _verified_submission()
    bad["created_by"] = "someone_else"
    with pytest.raises(RuntimeError, match="created by this module"):
        namespace["delete_once"](bad, TEST_UID, TEST_NAME, confirm=True, timeout=0)
    assert page.clicks == []


def test_delete_once_rejects_nonledger_or_logged_out_session():
    namespace, page = load_publishing()
    page.logged_out = True
    with pytest.raises(RuntimeError, match="auth_required"):
        namespace["delete_once"](_verified_submission(), TEST_UID, TEST_NAME,
                                 confirm=True, timeout=0)
    page.logged_out = False
    namespace["archive_matches"] = lambda title: []  # record absent from live manager
    with pytest.raises(RuntimeError, match="live manager records"):
        namespace["delete_once"](_verified_submission(), TEST_UID, TEST_NAME,
                                 confirm=True, timeout=0)
    bad = _verified_submission()
    bad["title"] = "无marker标题"
    bad["run_marker"] = "RUN"
    with pytest.raises(RuntimeError, match="run marker"):
        namespace["delete_once"](bad, TEST_UID, TEST_NAME, confirm=True, timeout=0)


def test_delete_once_clicks_exact_record_once_then_reconciles_read_only():
    namespace, page = load_publishing()
    namespace["require_identity"] = lambda uid, name=None: {"uid": uid, "name": name}
    archive_states = [[{"content_id": "42", "album_id": "88294964",
                        "album_name": ALBUM["title"],
                        "title": _verified_submission()["title"],
                        "state": "定时", "mode": "scheduled", "schedule": ""}],
                      [], []]

    def staged_archive(title):
        return archive_states.pop(0) if archive_states else []
    namespace["archive_matches"] = staged_archive
    result = namespace["delete_once"](_verified_submission("scheduled"), TEST_UID,
                                      TEST_NAME, confirm=True, timeout=5)
    assert result["status"] == "deleted"
    assert result["delete_clicks"] == 1
    assert result["content_id"] == "42"
    assert result["verification_source"].endswith("absence")


def test_delete_once_uses_live_mode_after_scheduled_record_auto_publishes():
    namespace, page = load_publishing()
    submission = _verified_submission("scheduled")
    namespace["require_identity"] = lambda uid, name=None: {"uid": uid, "name": name}
    api_calls = []
    namespace["_api_post"] = lambda *args: api_calls.append(args) or {"ret": 0}
    namespace["archive_matches"] = lambda title: [{
        "content_id": "42", "album_id": "88294964", "album_name": ALBUM["title"],
        "title": submission["title"], "state": "已发布", "mode": "immediate", "schedule": "",
    }]
    result = namespace["delete_once"](submission, TEST_UID, TEST_NAME,
                                       confirm=True, timeout=0)
    assert result["status"] == "deletion_unverified"
    assert result["live_mode"] == "immediate"
    assert page.gotos == ["https://www.ximalaya.com/reform-upload/page/sound/manage/88294964"]
    assert page.clicks == []
    assert api_calls == [(namespace["TRACK_DELETE_API"], {"trackId": 42},
                          "track deletion")]


def test_delete_once_returns_nonretryable_unknown_after_api_transport_error():
    namespace, _ = load_publishing()
    submission = _verified_submission("immediate")
    namespace["require_identity"] = lambda uid, name=None: {"uid": uid, "name": name}
    namespace["archive_matches"] = lambda title: [{
        "content_id": "42", "album_id": "88294964", "album_name": ALBUM["title"],
        "title": submission["title"], "state": "已发布", "mode": "immediate",
        "schedule": "",
    }]
    namespace["_api_post"] = lambda *args: (_ for _ in ()).throw(
        RuntimeError("response lost"))
    result = namespace["delete_once"](submission, TEST_UID, TEST_NAME,
                                       confirm=True, timeout=0)
    assert result["status"] == "deletion_unverified"
    assert result["delete_clicks"] == 1
    assert result["retry"] is False
    assert result["diagnostics"] == "response lost"


def test_delete_once_returns_nonretryable_unknown_after_ambiguous_click():
    namespace, page = load_publishing()
    namespace["require_identity"] = lambda uid, name=None: {"uid": uid, "name": name}

    def stubborn(title):
        return [{"content_id": "42", "album_id": "88294964",
                 "album_name": ALBUM["title"], "title": title,
                 "state": "定时", "mode": "scheduled", "schedule": ""}]
    namespace["archive_matches"] = stubborn
    result = namespace["delete_once"](_verified_submission("scheduled"), TEST_UID,
                                      TEST_NAME, confirm=True, timeout=0)
    assert result["status"] == "deletion_unverified"
    assert result["delete_clicks"] == 1
    assert result["retry"] is False


def test_confirm_dialog_accepts_pending_native_dialog_without_page_js():
    namespace, _ = load_publishing()
    calls = []
    namespace["page_info"] = lambda: {"dialog": True}
    namespace["cdp"] = lambda method, **params: calls.append((method, params))
    namespace["js"] = lambda script: pytest.fail("page JS must not run while dialog is pending")
    assert namespace["_confirm_dialog_accept"](timeout=0.1) is True
    assert calls == [("Page.handleJavaScriptDialog", {"accept": True})]


def test_confirm_dialog_waits_for_enabled_dom_button():
    namespace, _ = load_publishing()
    scripts = []
    states = iter((False, True))
    namespace["page_info"] = lambda: {"dialog": False}
    namespace["js"] = lambda script: (scripts.append(script) or next(states))
    assert namespace["_confirm_dialog_accept"](timeout=1) is True
    assert len(scripts) == 2
    assert "!b.disabled" in scripts[0]
    assert "aria-disabled" in scripts[0]


def test_confirm_dialog_accepts_ximalaya_delete_modal_button():
    namespace, _ = load_publishing()
    scripts = []
    namespace["page_info"] = lambda: {"dialog": False}
    namespace["js"] = lambda script: (scripts.append(script) or "删除" in script)
    assert namespace["_confirm_dialog_accept"](timeout=1) is True
    assert "ant-modal" in scripts[0]
    assert "xmDeleteModal" in scripts[0]
    assert "删除" in scripts[0]


def test_module_self_check_runs_on_import():
    namespace, _ = load_publishing()
    assert namespace["UPLOAD_URL"].startswith("https://www.ximalaya.com/reform-upload/")
    assert namespace["_self_check"]() is None
