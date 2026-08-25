import json
import re
from pathlib import Path

import pytest
from PIL import Image


PUBLISHING_PATH = (
    Path(__file__).parents[2]
    / "agent-workspace/domain-skills/bilibili/publishing.py"
)


class FakePage:
    def __init__(self):
        self.tags = ["原创", "短片"]
        self.pending_text = ""
        self.cover_marked = False
        self.cover_uploaded = False
        self.cover_ready = False
        self.cover_filename = ""
        self.partition_selector = True
        self.partition = "知识"
        self.description = ""
        self.description_events = []
        self.declaration = "内容无需标注"
        self.schedule = {"scheduled": True, "schedule_date": "2026-08-30", "schedule_time": "22:00"}
        self.title = "中奖彩票：赢得大奖反而陷入困境？数千名足球球迷的荒谬遭遇｜外刊播客｜中英+文稿"
        self.submit_text = "立即投稿"
        self.reject_tags = set()
        self.last_option = ""
        self.pending_hour = ""
        self.upload_calls = []

    def js(self, script):
        if "input.setAttribute('data-bh-cover-input'" in script:
            self.cover_marked = True
            return True
        if "custom_cover_set: Boolean(filename" in script:
            return {"cover_ready": self.cover_ready,
                    "custom_cover_set": self.cover_ready and self.cover_marked,
                    "cover_filename": self.cover_filename}
        if ".label-item-v2-content" in script:
            return list(self.tags)
        if "dispatchEvent(new Event('input'" in script and "placeholder" in script:
            return None
        if "const wanted =" in script:
            wanted = json.loads(re.search(r"const wanted = (.*?);", script).group(1))
            self.last_option = wanted
            return {"x": 10, "y": 20} if wanted in {"完成", "知识", "内容无需标注", "2026-08-30"} else None
        if "return {x:" in script:
            return {"x": 10, "y": 20} if self.partition_selector else None
        if "return node?.querySelector" in script:
            return self.partition
        if "el.innerText =" in script and ".ql-editor" in script:
            value = json.loads(re.search(r"el\.innerText = (.*?);", script).group(1))
            self.description = value
            self.description_events = ["beforeinput", "input", "change", "blur"]
            return True
        if ".ql-editor[contenteditable=\"true\"]" in script:
            return self.description
        if "scheduled: document" in script:
            return dict(self.schedule)
        if "input[type=date]" in script:
            value = json.loads(re.search(r"setter\.call\(input, (.*?)\);", script).group(1))
            self.schedule["schedule_date"] = value
            return True
        if "time-switch-wrp" in script and "classList.contains" in script:
            return self.schedule["scheduled"]
        if "time-switch-wrp" in script and ".click()" in script:
            self.schedule["scheduled"] = True
            return True
        if "time-picker-panel-select-item" in script:
            match = re.search(r"pick\(panels\[\d+\], (\"[^\"]+\")", script) or re.search(r"=== (\"[^\"]+\")", script)
            value = json.loads(match.group(1))
            if "panels.length >= 2" in script:
                self.pending_hour = value
            else:
                self.schedule["schedule_time"] = "%s:%s" % (self.pending_hour, value)
            return True
        if ".date-picker-timer .date-show" in script:
            return self.schedule["schedule_time"]
        if "input[placeholder=\"请输入稿件标题\"]" in script:
            return self.title
        if "input[placeholder*=\"创作声明\"]" in script:
            return self.declaration
        if "submit-add" in script:
            return self.submit_text
        if "x/web-interface/nav" in script:
            return {"code": 0, "mid": 518800384, "uname": "水蜜桃英语", "isLogin": True}
        if "x2/creative/web/archives" in script:
            return []
        if "article-card.v2" in script:
            return None
        if "querySelectorAll('input[type=file]'" in script:
            return True
        if "getBoundingClientRect" in script:
            return {"x": 10, "y": 20, "text": ""}
        return None

    def fill_input(self, selector, text, **kwargs):
        self.pending_text = text

    def press_key(self, key, modifiers=0):
        if key == "Enter" and self.pending_text not in self.reject_tags:
            if self.pending_text not in self.tags:
                self.tags.append(self.pending_text)

    def click_at_xy(self, x, y, button="left", clicks=1):
        if self.last_option == "完成":
            self.cover_ready = True
            self.cover_filename = self.upload_calls[-1][1].name
        elif self.last_option == "知识":
            self.partition = "知识"
        elif self.last_option == "内容无需标注":
            self.declaration = "内容无需标注"


def load_publishing(page=None):
    page = page or FakePage()
    namespace = {
        "js": page.js,
        "wait": lambda seconds=0: None,
        "upload_file": lambda selector, path: page.upload_calls.append((selector, Path(path))),
        "fill_input": page.fill_input,
        "press_key": page.press_key,
        "click_at_xy": page.click_at_xy,
        "activate_tab": lambda target: None,
        "current_tab": lambda: {"targetId": "bili"},
        "goto_url": lambda url: None,
        "page_info": lambda: {"url": "https://member.bilibili.com/platform/upload/video/frame"},
    }
    exec(compile(PUBLISHING_PATH.read_text(), str(PUBLISHING_PATH), "exec"), namespace)
    return namespace, page


def test_custom_cover_rejects_missing_and_empty_before_upload(tmp_path):
    namespace, page = load_publishing()
    with pytest.raises(ValueError):
        namespace["set_custom_cover"](str(tmp_path / "missing.png"))
    empty = tmp_path / "empty.png"
    empty.touch()
    with pytest.raises(ValueError):
        namespace["set_custom_cover"](str(empty))
    assert page.upload_calls == []


def test_custom_cover_returns_dimensions_after_dom_acceptance(tmp_path):
    cover = tmp_path / "cover.png"
    Image.new("RGB", (1280, 720), "#123456").save(cover)
    namespace, page = load_publishing()
    result = namespace["set_custom_cover"](str(cover), timeout=0)
    assert result == {"custom_cover_set": True, "filename": "cover.png", "width": 1280, "height": 720}
    assert page.upload_calls[0][0] == 'input[type=file][data-bh-cover-input="1"]'


def test_tags_preserve_auto_tags_and_normalize_duplicates():
    namespace, page = load_publishing()
    selected = namespace["set_tags"]([" 英语学习 ", "英语学习", "英语听力", "英语新闻", "足球", "彩票"], timeout=0)
    assert selected == ["原创", "短片", "英语学习", "英语听力", "英语新闻", "足球", "彩票"]


def test_tags_report_rejected_target_and_observed_values():
    namespace, page = load_publishing()
    page.reject_tags.add("彩票")
    with pytest.raises(RuntimeError, match=r"彩票.*原创.*短片"):
        namespace["set_tags"](["彩票"], timeout=0)


def test_partition_requires_real_selector_not_body_text():
    namespace, page = load_publishing()
    page.partition_selector = False
    with pytest.raises(RuntimeError, match="selector"):
        namespace["set_partition"]("知识", timeout=0)
    page.partition_selector = True
    assert namespace["set_partition"]("知识", timeout=0) == "知识"


def test_description_dispatches_and_reads_back_normalized_text():
    namespace, page = load_publishing()
    assert namespace["set_description"]("  第一行\n第二行  ", timeout=0) == "第一行 第二行"
    assert page.description_events == ["beforeinput", "input", "change", "blur"]


def test_schedule_datetime_accepts_date_and_time_and_enforces_bounds(monkeypatch):
    namespace, _ = load_publishing()
    assert namespace["set_schedule_datetime"]("2026-08-30 22:00", timeout=0) == {
        "schedule_date": "2026-08-30", "schedule_time": "22:00", "schedule": "2026-08-30 22:00"
    }
    with pytest.raises(ValueError, match="divisible"):
        namespace["set_schedule_datetime"]("2026-08-30 22:01")
    with pytest.raises(ValueError, match="future"):
        namespace["set_schedule_datetime"]("2020-01-01 00:00")
    with pytest.raises(ValueError, match="fifteen"):
        namespace["set_schedule_datetime"]("2099-01-01 00:00")


def test_snapshot_contains_real_contract_fields():
    namespace, page = load_publishing()
    page.cover_marked = page.cover_ready = True
    page.cover_filename = "cover.png"
    page.description = "描述文本"
    snapshot = namespace["submission_snapshot"]()
    assert set(snapshot) == {
        "title", "cover_ready", "custom_cover_set", "cover_filename", "partition",
        "description", "tags", "declaration", "scheduled", "schedule_date",
        "schedule_time", "submit_text",
    }
    assert snapshot["cover_ready"] is True
    assert snapshot["custom_cover_set"] is True
    assert snapshot["partition"] == "知识"
    assert snapshot["description"] == "描述文本"
    assert snapshot["submit_text"] == "立即投稿"


def _valid_snapshot():
    return {
        "title": "标题", "cover_ready": True, "custom_cover_set": True,
        "cover_filename": "cover.png", "partition": "知识", "description": "描述",
        "tags": ["英语学习"], "declaration": "内容无需标注", "scheduled": True,
        "schedule_date": "2026-08-30", "schedule_time": "22:00", "submit_text": "立即投稿",
    }


def _configure_submit(namespace, archive_values, manager_values, clicks):
    namespace["require_identity"] = lambda mid, name=None: {"mid": mid, "uname": name}
    archive_iter = iter(archive_values)
    archive_last = archive_values[-1] if archive_values else []
    namespace["archive_matches"] = lambda title: next(archive_iter, archive_last)
    namespace["submission_snapshot"] = _valid_snapshot
    namespace["_click_visible"] = lambda selector: clicks.append(selector)
    manager_iter = iter(manager_values)
    manager_last = manager_values[-1] if manager_values else {"schedule_match": True}
    namespace["manager_evidence"] = lambda title, schedule, strict=False: next(manager_iter, manager_last)
    namespace["wait"] = lambda seconds=0: None


def test_submit_once_clicks_once_when_manager_evidence_is_delayed():
    namespace, _ = load_publishing()
    clicks = []
    archive = [{"aid": 7, "bvid": "BV1"}]
    _configure_submit(namespace, [[], archive, archive, archive],
                      [{"text": "未就绪", "schedule_match": False},
                       {"text": "仍未就绪", "schedule_match": False},
                       {"text": "定时发布 2026年08月30日 22:00", "schedule_match": True}], clicks)
    result = namespace["submit_once"]("标题", 518800384, "水蜜桃英语", "2026-08-30 22:00", timeout=1)
    assert result["status"] == "verified"
    assert result["archive"]["bvid"] == "BV1"
    assert result["submit_clicks"] == 1
    assert clicks == [".submit-add"]


def test_submit_once_returns_accepted_but_unverified_without_retry_signal():
    namespace, _ = load_publishing()
    clicks = []
    archive = [{"aid": 8, "bvid": "BV2"}]
    _configure_submit(namespace, [[], archive],
                      [{"text": "定时发布尚未显示", "schedule_match": False}], clicks)
    result = namespace["submit_once"]("标题", 518800384, "水蜜桃英语", "2026-08-30 22:00", timeout=0.01)
    assert result["status"] == "accepted_but_schedule_unverified"
    assert result["archive"] == archive[0]
    assert result["expected_schedule"] == "2026-08-30 22:00"
    assert result["submit_clicks"] == 1
    assert clicks == [".submit-add"]


def test_submit_once_zero_archive_raises_do_not_retry_message():
    namespace, _ = load_publishing()
    clicks = []
    _configure_submit(namespace, [[]], [], clicks)
    with pytest.raises(TimeoutError, match="do not retry blindly"):
        namespace["submit_once"]("标题", 518800384, "水蜜桃英语", "2026-08-30 22:00", timeout=0)
    assert clicks == [".submit-add"]


def test_submit_once_rejects_multiple_archive_records():
    namespace, _ = load_publishing()
    clicks = []
    _configure_submit(namespace, [[{"aid": 1}, {"aid": 2}]], [], clicks)
    with pytest.raises(RuntimeError, match="multiple records"):
        namespace["submit_once"]("标题", 518800384, "水蜜桃英语", "2026-08-30 22:00", timeout=1)
    assert clicks == []


def test_submit_once_blocks_preexisting_exact_title_before_click():
    namespace, _ = load_publishing()
    clicks = []
    _configure_submit(namespace, [[{"aid": 3, "bvid": "BV3"}]], [], clicks)
    with pytest.raises(RuntimeError, match="already exists"):
        namespace["submit_once"]("标题", 518800384, "水蜜桃英语", "2026-08-30 22:00", timeout=1)
    assert clicks == []
