from pathlib import Path

import pytest


OPS_PATH = (
    Path(__file__).parents[2]
    / "agent-workspace/domain-skills/bilibili/interactions.py"
)


def load_ops(js_impl, verify_values, *, clicks=None, activations=None, tabs=None, navigations=None):
    values = iter(verify_values)
    clicks = clicks if clicks is not None else []
    activations = activations if activations is not None else []
    tabs = tabs if tabs is not None else []
    navigations = navigations if navigations is not None else []
    namespace = {
        "js": js_impl,
        "page_info": lambda: {"url": "https://www.bilibili.com/"},
        "wait": lambda seconds=0: None,
        "current_tab": lambda: {"targetId": "bili"},
        "activate_tab": activations.append,
        "click_at_xy": lambda x, y: clicks.append((x, y)),
        "new_tab": tabs.append,
        "goto_url": navigations.append,
        "wait_for_load": lambda timeout=15: True,
    }
    exec(compile(OPS_PATH.read_text(), str(OPS_PATH), "exec"), namespace)
    return namespace["bilibili_click_readonly"], lambda: next(values)


def probe_js(script):
    return {"found": True, "x": 10, "y": 20, "tag": "A", "text": "热门"}


def test_silent_click_must_verify_the_task():
    click, verify = load_ops(probe_js, [False, True])
    result = click(text="热门", verify=verify, timeout=0)
    assert result["mode"] == "silent"


def test_blank_target_link_uses_background_tab_navigation():
    tabs = []

    def link_js(script):
        return {"found": True, "x": 10, "y": 20, "tag": "A", "text": "热门",
                "href": "https://www.bilibili.com/v/popular/all", "target": "_blank"}

    click, verify = load_ops(link_js, [False, True], tabs=tabs)
    assert click(text="热门", verify=verify, timeout=0)["mode"] == "silent"
    assert tabs == ["https://www.bilibili.com/v/popular/all"]


def test_failed_silent_click_falls_back_and_reports_it():
    clicks, activations = [], []
    click, verify = load_ops(
        probe_js, [False, False, True], clicks=clicks, activations=activations
    )
    result = click(text="热门", verify=verify, timeout=0)
    assert result["mode"] == "fallback"
    assert activations == [{"targetId": "bili"}]
    assert clicks == [(10, 20)]


def test_disabled_fallback_never_activates_or_clicks():
    clicks, activations = [], []
    click, verify = load_ops(
        probe_js, [False, False], clicks=clicks, activations=activations
    )
    with pytest.raises(RuntimeError, match="silent click did not complete"):
        click(text="热门", verify=verify, timeout=0, fallback=False)
    assert activations == []
    assert clicks == []


def test_both_click_paths_failing_is_not_success():
    click, verify = load_ops(probe_js, [False, False, False])
    with pytest.raises(RuntimeError, match="silent and fallback"):
        click(text="热门", verify=verify, timeout=0)


def test_gray_helper_rejects_non_bilibili_pages():
    namespace = {
        "js": probe_js,
        "page_info": lambda: {"url": "https://example.com/"},
        "wait": lambda seconds=0: None,
        "current_tab": lambda: {},
        "activate_tab": lambda target: None,
        "click_at_xy": lambda x, y: None,
        "new_tab": lambda url: None,
        "goto_url": lambda url: None,
        "wait_for_load": lambda timeout=15: True,
    }
    exec(compile(OPS_PATH.read_text(), str(OPS_PATH), "exec"), namespace)
    with pytest.raises(RuntimeError, match="restricted to Bilibili"):
        namespace["bilibili_click_readonly"](verify=lambda: False)
