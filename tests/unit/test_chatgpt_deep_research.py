from pathlib import Path

import pytest


DR_PATH = (
    Path(__file__).parents[2]
    / "agent-workspace/domain-skills/chatgpt/deep_research.py"
)


def load_dr(js_impl, *, iframe_impl=None, type_impl=None, press_impl=None):
    def fake_cdp(method, **kwargs):
        if method == "DOM.getDocument":
            return {"root": {"nodeId": 1}}
        if method == "DOM.querySelectorAll":
            try:
                present = iframe_impl("connector-openai-deep-research") if iframe_impl else "fake-target-id"
            except RuntimeError as exc:
                if "no such iframe" not in str(exc):
                    raise
                present = None
            return {"nodeIds": [2] if present else []}
        if method == "DOM.describeNode":
            return {"node": {"frameId": "fake-target-id"}}
        if method == "Target.getTargets":
            return {"targetInfos": [{"type": "iframe", "targetId": "fake-target-id",
                                     "url": "https://connector-openai-deep-research.example/"}]}
        raise AssertionError(method)

    namespace = {
        "cdp": fake_cdp,
        "js": js_impl,
        "iframe_target": iframe_impl or (lambda name: "fake-target-id"),
        "type_text": type_impl or (lambda text: None),
        "press_key": press_impl or (lambda *args, **kwargs: None),
        "wait": lambda seconds=0: None,
        "wait_for_load": lambda timeout=15: True,
    }
    exec(compile(DR_PATH.read_text(), str(DR_PATH), "exec"), namespace)
    return namespace


def test_connector_does_not_read_a_different_tabs_target():
    ops = load_dr(lambda *a, **k: pytest.fail("must not evaluate another tab"))
    original = ops["cdp"]
    ops["cdp"] = lambda method, **kwargs: (
        {"node": {"frameId": "this-tabs-frame"}} if method == "DOM.describeNode"
        else original(method, **kwargs)
    )
    result = ops["deep_research_progress"]()
    assert result["state"] == "unknown"
    assert "not attached" in result["reason"]


def test_progress_classifies_planning_state():
    def fake_js(script, target_id=None):
        if "iframe#root" in script:
            return {"found": True, "text": "最小验证：1+1\n识别计划\n计划生成倒计时：27 秒\n27\n编辑\n取消\n开始"}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    prog = ops["deep_research_progress"]()
    assert prog["state"] == "planning"


def test_progress_classifies_running_state():
    def fake_js(script, target_id=None):
        if "iframe#root" in script:
            return {"found": True, "text": "计划标题\n步骤1\n正在研究…\n停止研究"}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    prog = ops["deep_research_progress"]()
    assert prog["state"] == "running"


def test_progress_classifies_done_state():
    def fake_js(script, target_id=None):
        if "iframe#root" in script:
            return {"found": True, "text": "研究完成情况：<1m · 5 次引用 · 3 个搜索\n深度研究报告\n正文"}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    prog = ops["deep_research_progress"]()
    assert prog["state"] == "done"


def test_progress_returns_idle_when_connector_iframe_missing():
    def iframe_impl(name):
        raise RuntimeError("no such iframe")

    ops = load_dr(lambda *a, **k: None, iframe_impl=iframe_impl)
    prog = ops["deep_research_progress"]()
    assert prog["state"] == "idle"


def test_progress_returns_idle_when_connector_target_is_absent():
    ops = load_dr(lambda *a, **k: None, iframe_impl=lambda name: None)
    assert ops["deep_research_progress"]()["state"] == "idle"


def test_arm_deep_research_requires_pill_after_clicking_rows():
    calls = []

    def fake_js(script, target_id=None):
        calls.append(script)
        if "data-inline-selection-pill" in script and "count" in script:
            return {"count": 0}
        if "composer-plus-btn" in script:
            return {"found": True}
        if "深度研究" in script and "leaves" in script:
            return {"found": True}
        if "unified-composer" in script and "pill" in script:
            return {"pill": True, "text": "深度研究 Pro"}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    result = ops["arm_deep_research"]()
    assert result["armed"] is True


def test_arm_deep_research_raises_without_pill():
    def fake_js(script, target_id=None):
        if "data-inline-selection-pill" in script and "count" in script:
            return {"count": 0}
        if "composer-plus-btn" in script:
            return {"found": True}
        if "深度研究" in script and "leaves" in script:
            return {"found": True}
        if "unified-composer" in script and "pill" in script:
            return {"pill": False, "text": ""}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    with pytest.raises(RuntimeError, match="pill"):
        ops["arm_deep_research"]()


def test_disarm_deep_research_clicks_token_and_backspace():
    pressed = []
    seen = {"token": False}

    def fake_js(script, target_id=None):
        if "const el = form" in script:
            if seen["token"]:
                return {"found": False}
            seen["token"] = True
            return {"found": True}
        if "const count" in script:
            return {"count": 0}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js, press_impl=pressed.append)
    result = ops["disarm_deep_research"]()
    assert result["disarmed"] is True
    assert pressed == ["Backspace"]


def test_export_markdown_returns_newest_nonempty_download(tmp_path, monkeypatch):
    report = tmp_path / "deep-research-report (3).md"
    report.write_text("2")

    # Point Path.home() at a fake root whose Downloads is tmp_path.
    fake_home = tmp_path.parent / "fakehome"
    (fake_home / "Downloads").mkdir(parents=True)
    (fake_home / "Downloads" / "deep-research-report (2).md").write_text("stale")
    (fake_home / "Downloads" / "deep-research-report (3).md").write_text("2")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    def fake_js(script, target_id=None):
        if "导出到 Markdown" in script:
            (fake_home / "Downloads" / "deep-research-report (4).md").write_text("fresh")
            return {"found": True}
        if "querySelectorAll('button')" in script and "导出" in script:
            return {"found": True}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    path = ops["export_deep_research_markdown"](timeout=2)
    assert path == str(fake_home / "Downloads" / "deep-research-report (4).md")


def test_progress_returns_unknown_when_nested_connector_is_unreadable():
    def fake_js(script, target_id=None):
        if "iframe#root" in script:
            return {"found": False, "error": "nested frame unavailable"}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    progress = ops["deep_research_progress"]()

    assert progress["state"] == "unknown"
    assert "nested" in progress["reason"]


def test_run_deep_research_requires_shared_sender_before_arming():
    def forbidden_js(script, target_id=None):
        raise AssertionError("runner must check send_message before any UI action")

    ops = load_dr(forbidden_js)
    with pytest.raises(RuntimeError, match="precondition"):
        ops["run_deep_research"]("synthetic question", timeout=0)


def test_run_deep_research_uses_shared_sender_once():
    sends = []
    ops = load_dr(lambda *a, **k: None)
    ops["arm_deep_research"] = lambda: {"armed": True}
    ops["send_message"] = lambda question: sends.append(question) or {"status": "definitely_sent"}
    ops["deep_research_progress"] = lambda: {"state": "done", "text": "synthetic report"}

    result = ops["run_deep_research"]("synthetic question", export=False)

    assert result["state"] == "done"
    assert result["submission_count"] == 1
    assert sends == ["synthetic question"]


def test_run_deep_research_keeps_polling_after_transient_unknown():
    states = iter([
        {"state": "unknown", "reason": "transient connector text", "text": "starting"},
        {"state": "running", "text": "正在研究… 停止研究"},
        {"state": "done", "text": "研究完成 3 次引用"},
    ])
    ops = load_dr(lambda *a, **k: None)
    ops["arm_deep_research"] = lambda: {"armed": True}
    ops["send_message"] = lambda question: {"status": "definitely_sent", "url": "https://chatgpt.com/c/test"}
    ops["deep_research_progress"] = lambda: next(states)
    result = ops["run_deep_research"]("synthetic question", poll_interval=0.1, export=False)
    assert result["state"] == "done"
    assert result["submission_count"] == 1


def test_export_markdown_does_not_reuse_preexisting_download(tmp_path, monkeypatch):
    fake_home = tmp_path / "fakehome"
    downloads = fake_home / "Downloads"
    downloads.mkdir(parents=True)
    (downloads / "deep-research-report (1).md").write_text("old report")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    def fake_js(script, target_id=None):
        if "querySelectorAll('button')" in script and "导出" in script:
            return {"found": True}
        if "导出到 Markdown" in script:
            return {"found": True}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    with pytest.raises(RuntimeError, match="no fresh non-empty report"):
        ops["export_deep_research_markdown"](timeout=0.01)
