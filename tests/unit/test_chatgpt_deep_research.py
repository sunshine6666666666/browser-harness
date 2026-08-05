from pathlib import Path

import pytest


DR_PATH = (
    Path(__file__).parents[2]
    / "agent-workspace/domain-skills/chatgpt/deep_research.py"
)


def load_dr(js_impl, *, iframe_impl=None, type_impl=None, press_impl=None):
    namespace = {
        "js": js_impl,
        "iframe_target": iframe_impl or (lambda name: "fake-target-id"),
        "type_text": type_impl or (lambda text: None),
        "press_key": press_impl or (lambda *args, **kwargs: None),
        "wait": lambda seconds=0: None,
        "wait_for_load": lambda timeout=15: True,
    }
    exec(compile(DR_PATH.read_text(), str(DR_PATH), "exec"), namespace)
    return namespace


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


def test_arm_deep_research_requires_pill_after_clicking_rows():
    calls = []

    def fake_js(script, target_id=None):
        calls.append(script)
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

    def fake_js(script, target_id=None):
        if "hits.length" in script:
            return {"found": True}
        if "pill" in script:
            return {"pill": False}
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
        if "querySelectorAll('button')" in script and "导出" in script:
            return {"found": True}
        if "导出到 Markdown" in script:
            return {"found": True}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_dr(fake_js)
    path = ops["export_deep_research_markdown"](timeout=2)
    assert path == str(fake_home / "Downloads" / "deep-research-report (3).md")
