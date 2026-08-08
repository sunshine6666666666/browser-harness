from pathlib import Path

import pytest


OPS_PATH = (
    Path(__file__).parents[2]
    / "agent-workspace/domain-skills/chatgpt/basic_ops.py"
)


def load_ops(js_impl, *, click_impl=None, type_impl=None, press_impl=None, goto_impl=None):
    namespace = {
        "js": js_impl,
        "click_at_xy": click_impl or (lambda *args, **kwargs: None),
        "type_text": type_impl or (lambda text: None),
        "press_key": press_impl or (lambda *args, **kwargs: None),
        "wait": lambda seconds=0: None,
        "wait_for_load": lambda timeout=15: True,
        "new_tab": lambda url="about:blank": url,
        "goto_url": goto_impl or (lambda url: None),
        "cdp": lambda *args, **kwargs: None,
        "list_tabs": lambda include_chrome=True: [],
        "switch_tab": lambda target: None,
        "close_tab": lambda target=None: None,
        "capture_screenshot": lambda *args, **kwargs: None,
    }
    exec(compile(OPS_PATH.read_text(), str(OPS_PATH), "exec"), namespace)
    return namespace


def test_new_chat_rejects_unchanged_existing_conversation():
    old_url = "https://chatgpt.com/c/existing-conversation"

    def fake_js(script):
        if "const links" in script:
            return {"found": True, "x": 10, "y": 10}
        if script == "location.href":
            return old_url
        if "form[data-type=\"unified-composer\"]" in script:
            return {
                "url": old_url,
                "composer_found": True,
                "composer_empty": True,
            }
        if "location.href.endsWith" in script:
            return True
        raise AssertionError(f"unexpected JS: {script[:100]}")

    ops = load_ops(fake_js)

    with pytest.raises(RuntimeError, match="unchanged|fresh chat"):
        ops["new_chat"]()


def test_new_chat_rejects_different_existing_conversation_with_empty_composer():
    old_url = "https://chatgpt.com/c/existing-conversation"
    different_old_url = "https://chatgpt.com/c/different-existing-conversation"

    def fake_js(script):
        if script == "location.href":
            return old_url
        if "const links" in script:
            return {"found": True, "clicked": True}
        if "form[data-type=\"unified-composer\"]" in script:
            return {
                "url": different_old_url,
                "path": "/c/different-existing-conversation",
                "composer_found": True,
                "composer_empty": True,
            }
        raise AssertionError(f"unexpected JS: {script[:100]}")

    ops = load_ops(fake_js)

    with pytest.raises(RuntimeError, match="fresh home"):
        ops["new_chat"]()


def test_new_chat_uses_dom_click_and_returns_fresh_home_evidence():
    old_url = "https://chatgpt.com/c/existing-conversation"

    def fake_js(script):
        if script == "location.href":
            return old_url
        if "const links" in script:
            return {"found": True, "clicked": True}
        if "form[data-type=\"unified-composer\"]" in script:
            return {
                "url": "https://chatgpt.com/",
                "path": "/",
                "composer_found": True,
                "composer_empty": True,
            }
        raise AssertionError(f"unexpected JS: {script[:100]}")

    def forbidden_coordinate_click(*args, **kwargs):
        raise AssertionError("new_chat should use the stable DOM click path")

    ops = load_ops(fake_js, click_impl=forbidden_coordinate_click)

    evidence = ops["new_chat"]()

    assert evidence["path"] == "/"
    assert evidence["composer_empty"] is True


def test_open_model_picker_uses_dom_click_instead_of_cdp_coordinates():
    menu_counts = iter([0, 1, 1])

    def fake_js(script):
        if "querySelectorAll('[role=\"menu\"]')" in script and "模型" in script:
            return False
        if "visibleMenus" in script:
            return next(menu_counts)
        if "const scoped =" in script:
            return {"found": True, "x": 100, "y": 100, "expanded": False, "text": "中"}
        if "const form = document.querySelector('form[data-type=\"unified-composer\"]')" in script:
            return {"found": True, "expanded": False, "clicked": True, "text": "中"}
        if "!!document.querySelector('[role=\"menu\"]')" in script:
            return True
        if "startsWith('模型')" in script:
            return False
        if "const pre = '高级'" in script or "const pre = 'Advanced'" in script:
            return {"found": False}
        if "const items = [...document.querySelectorAll('[role=\"menuitem\"]')]" in script:
            return {"has_advanced": False, "items": ["GPT-5.6 Sol", "中"]}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    def fail_click(*args):
        raise AssertionError("open_model_picker must prefer a DOM click on this SPA")

    ops = load_ops(fake_js, click_impl=fail_click)
    ops["open_model_picker"]()


def test_close_visible_menus_unwinds_every_open_layer():
    counts = iter([2, 0])
    pressed = []

    def fake_js(script):
        if "visibleMenus" in script:
            return next(counts)
        if "form[data-type=\"unified-composer\"]" in script:
            return {"found": True}
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_ops(fake_js, press_impl=pressed.append)
    ops["_close_visible_menus"]()

    assert pressed == []

def test_close_visible_menus_tolerates_usable_panel_after_cleanup_failure():
    # Issue #12: a model/effort panel that stays visible after trigger/Escape
    # cleanup but is fully usable must not be reported as a hard failure.
    counts = iter([2, 1, 1, 1, 1, 1])
    pressed = []

    def fake_js(script):
        if "visibleMenus" in script:
            return next(counts)
        if "form[data-type=\"unified-composer\"]" in script:
            return {"found": True}
        if "querySelectorAll('[role=\"menu\"]')" in script and "模型" in script:
            return True
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_ops(fake_js, press_impl=pressed.append)
    ops["_close_visible_menus"](tolerate_usable=True)

    assert pressed == ["Escape"] * 4


def test_close_visible_menus_still_raises_without_tolerate_usable():
    counts = iter([2, 1, 1, 1, 1, 1])

    def fake_js(script):
        if "visibleMenus" in script:
            return next(counts)
        if "form[data-type=\"unified-composer\"]" in script:
            return {"found": True}
        if "querySelectorAll('[role=\"menu\"]')" in script and "模型" in script:
            return True
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_ops(fake_js)
    with pytest.raises(RuntimeError, match="remained visible"):
        ops["_close_visible_menus"]()


def test_open_model_picker_reuses_already_usable_panel():
    # Issue #12: when the model/effort panel is already open and usable,
    # open_model_picker must reuse it instead of close→reopen raising a false
    # cleanup failure.
    def fake_js(script):
        if "querySelectorAll('[role=\"menu\"]')" in script and "模型" in script:
            return True
        raise AssertionError(f"unexpected JS: {script[:80]}")

    ops = load_ops(fake_js)
    ops["open_model_picker"]()


def test_set_reasoning_effort_tries_both_reasoning_labels():
    # Issue #12: label drift 推理强度 → 思考强度. The helper must try the new
    # label when the old one is not found. _verify_radio_after_reopen is mocked
    # so the test stays focused on the label fallback in set_reasoning_effort.
    requested = "中"
    label_attempts = []

    def fake_js(script):
        if "visibleMenus" in script:
            return 0
        if "menuitemradio" in script and requested in script:
            return {"found": True, "x": 30, "y": 30, "checked": True}
        if "const pre" in script:
            label_attempts.append(script.split("const pre = ")[1].split(";")[0].strip())
            return {"found": False}
        if "const norm" in script and "return el ? norm" in script:
            return "中"
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    ops["open_model_picker"] = lambda: None
    ops["_verify_radio_after_reopen"] = lambda name, *, model, first_token=False: {
        "name": name, "checked": True
    }

    evidence = ops["set_reasoning_effort"](requested)

    assert evidence["name"] == requested
    assert evidence["checked"] is True
    assert label_attempts == ["'推理强度'", "'思考强度'"]



def test_select_model_supports_live_direct_submenu_and_verifies_exact_radio():
    requested = "GPT-5.6 Sol"

    def fake_js(script):
        if "visibleMenus" in script:
            return 0
        if "const pre" in script:
            return {"found": False}
        if "aria-haspopup=\"menu\"" in script or "data-has-submenu" in script:
            assert "pointerdown" in script
            return {"found": True, "clicked": True}
        if "menuitemradio" in script and requested in script:
            return {"found": True, "x": 30, "y": 30, "checked": True}
        if "const norm" in script and "return el ? norm" in script:
            return "中"
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    ops["open_model_picker"] = lambda: None

    evidence = ops["select_model"](requested)

    assert evidence["name"] == requested
    assert evidence["checked"] is True


def test_set_reasoning_effort_supports_live_top_level_radio_and_verifies_checked():
    requested = "中"

    def fake_js(script):
        if "visibleMenus" in script:
            return 0
        if "const pre" in script:
            return {"found": False}
        if "menuitemradio" in script and requested in script:
            return {"found": True, "x": 30, "y": 30, "checked": True}
        if "const norm" in script and "return el ? norm" in script:
            return "中"
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    ops["open_model_picker"] = lambda: None

    evidence = ops["set_reasoning_effort"](requested)

    assert evidence["name"] == requested
    assert evidence["checked"] is True


def test_advanced_menu_item_uses_pointer_sequence_without_coordinate_click():
    def fake_js(script):
        assert "pointerdown" in script
        return {"found": True, "clicked": True}

    ops = load_ops(fake_js, click_impl=lambda *args: (_ for _ in ()).throw(AssertionError("coordinate click used")))
    assert ops["_click_advanced_item"]("模型") is True


def test_radio_target_activates_unchecked_item_with_pointer_sequence():
    requested = "高"

    def fake_js(script):
        assert "const activate = true" in script
        assert "pointerdown" in script
        return {"found": True, "checked": False, "activated": True}

    ops = load_ops(fake_js)
    result = ops["_radio_target"](requested, first_token=True, activate=True)

    assert result["activated"] is True


def test_send_message_returns_definite_live_evidence_from_unified_composer():
    typed = []
    calls = []

    def fake_js(script):
        calls.append(script)
        if "existing_user_messages" in script:
            return {
                "found": True,
                "empty": True,
                "url": "https://chatgpt.com/",
                "user_count": 0,
                "user_message_ids": [],
                "last_user_turn": -1,
            }
        if "activate_send_button" in script:
            assert "pointerdown" in script
            return {"found": True, "clicked": True}
        if "send_button" in script:
            return {"found": True}
        if "last_user_message" in script:
            return {
                "url": "https://chatgpt.com/c/test-chat",
                "composer_empty": True,
                "user_count": 1,
                "last_user_message_id": "new-short-message",
                "last_user_turn": 1,
                "last_user_message": "hello from regression test",
            }
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js, type_impl=typed.append)

    evidence = ops["send_message"]("hello from regression test")

    assert typed == ["hello from regression test"]
    assert evidence["status"] == "definitely_sent"
    assert evidence["url"] == "https://chatgpt.com/c/test-chat"
    assert evidence["expected_user_message_found"] is True
    assert all("form[data-type=\"unified-composer\"]" in script for script in calls[:2])


def test_send_message_accepts_a_collapsed_long_message_prefix_as_evidence():
    marker = "MAINTENANCE-LONG-SEND-2026-08-04"
    message = marker + " " + ("validated role artifact " * 300)
    rendered_prefix = " ".join(message.split())[:180] + " 展开"

    def fake_js(script):
        if "existing_user_messages" in script:
            return {
                "found": True,
                "empty": True,
                "url": "https://chatgpt.com/",
                "user_count": 0,
                "user_message_ids": [],
                "last_user_turn": -1,
            }
        if "activate_send_button" in script:
            return {"found": True, "clicked": True}
        if "send_button" in script:
            return {"found": True}
        if "last_user_message" in script:
            return {
                "url": "https://chatgpt.com/c/long-send-test",
                "composer_empty": True,
                "user_count": 1,
                "last_user_message_id": "new-long-message",
                "last_user_turn": 1,
                "last_user_message": rendered_prefix,
            }
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    evidence = ops["send_message"](message)

    assert evidence["status"] == "definitely_sent"
    assert evidence["expected_user_message_found"] is True
    assert evidence["message_match"] == "collapsed_prefix"


def test_send_message_waits_for_a_canonical_conversation_url():
    post_send_states = iter([
        {
            "url": "https://chatgpt.com/c/WEB:temporary-id",
            "composer_empty": True,
            "user_count": 1,
            "last_user_message_id": "canonical-message",
            "last_user_turn": 1,
            "last_user_message": "canonical url regression",
        },
        {
            "url": "https://chatgpt.com/c/6a71b7a7-3c8c-83ea-a7b2-a8b07df96fd6",
            "composer_empty": True,
            "user_count": 1,
            "last_user_message_id": "canonical-message",
            "last_user_turn": 1,
            "last_user_message": "canonical url regression",
        },
    ])

    def fake_js(script):
        if "existing_user_messages" in script:
            return {
                "found": True,
                "empty": True,
                "url": "https://chatgpt.com/",
                "user_count": 0,
                "user_message_ids": [],
                "last_user_turn": -1,
            }
        if "activate_send_button" in script:
            return {"found": True, "clicked": True}
        if "send_button" in script:
            return {"found": True}
        if "last_user_message" in script:
            return next(post_send_states)
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    evidence = ops["send_message"]("canonical url regression")

    assert evidence["status"] == "definitely_sent"
    assert evidence["url"] == "https://chatgpt.com/c/6a71b7a7-3c8c-83ea-a7b2-a8b07df96fd6"


def test_send_message_accepts_a_new_message_id_when_virtualized_count_is_fixed():
    def fake_js(script):
        if "existing_user_messages" in script:
            return {
                "found": True,
                "empty": True,
                "url": "https://chatgpt.com/c/existing-chat",
                "user_count": 4,
                "user_message_ids": ["old-1", "old-2", "old-3", "old-4"],
                "last_user_message_id": "old-4",
                "last_user_turn": 7,
            }
        if "activate_send_button" in script:
            return {"found": True, "clicked": True}
        if "send_button" in script:
            return {"found": True}
        if "last_user_message" in script:
            return {
                "url": "https://chatgpt.com/c/existing-chat",
                "composer_empty": True,
                "user_count": 4,
                "last_user_message_id": "new-5",
                "last_user_turn": 9,
                "last_user_message": "fixed virtual window send",
            }
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    evidence = ops["send_message"]("fixed virtual window send")

    assert evidence["status"] == "definitely_sent"
    assert evidence["message_id"] == "new-5"


def test_send_message_rejects_duplicate_old_turn_and_nonempty_composer_after_noop():
    def fake_js(script):
        if "existing_user_messages" in script:
            return {
                "found": True,
                "empty": True,
                "url": "https://chatgpt.com/c/existing-chat",
                "user_count": 1,
                "user_message_ids": ["old-continue"],
                "last_user_message_id": "old-continue",
                "last_user_turn": 1,
            }
        if "activate_send_button" in script:
            return {"found": True, "clicked": True}
        if "send_button" in script:
            return {"found": True}
        if "last_user_message" in script:
            return {
                "url": "https://chatgpt.com/c/existing-chat",
                "composer_empty": False,
                "user_count": 2,
                "last_user_message_id": "old-continue",
                "last_user_turn": 1,
                "last_user_message": "continue",
            }
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    evidence = ops["send_message"]("continue", evidence_timeout=0.01)

    assert evidence["status"] == "unknown"
    assert evidence["expected_user_message_found"] is False


def test_send_message_returns_unknown_after_click_without_post_send_evidence():
    def fake_js(script):
        if "existing_user_messages" in script:
            return {"found": True, "empty": True, "url": "https://chatgpt.com/", "user_count": 0}
        if "activate_send_button" in script:
            assert "pointerdown" in script
            return {"found": True, "clicked": True}
        if "send_button" in script:
            return {"found": True}
        raise AssertionError(f"unexpected JS: {script[:100]}")

    ops = load_ops(fake_js)
    evidence = ops["send_message"]("uncertain send", evidence_timeout=0)

    assert evidence["status"] == "unknown"
    assert evidence["expected_user_message_found"] is False


def test_send_message_converts_activation_exception_to_unknown_without_retry_signal():
    def fake_js(script):
        if "existing_user_messages" in script:
            return {"found": True, "empty": True, "url": "https://chatgpt.com/", "user_count": 0}
        if "activate_send_button" in script:
            raise RuntimeError("execution context destroyed during click")
        if "send_button" in script:
            return {"found": True}
        raise AssertionError(f"unexpected JS: {script[:100]}")

    ops = load_ops(fake_js)
    evidence = ops["send_message"]("possibly sent")

    assert evidence["status"] == "unknown"
    assert evidence["reason"] == "send_activation_exception"


def test_send_message_tolerates_a_transient_post_send_evidence_exception():
    evidence_reads = 0

    def fake_js(script):
        nonlocal evidence_reads
        if "existing_user_messages" in script:
            return {
                "found": True,
                "empty": True,
                "url": "https://chatgpt.com/",
                "user_count": 0,
                "user_message_ids": [],
                "last_user_turn": -1,
            }
        if "activate_send_button" in script:
            return {"found": True, "clicked": True}
        if "send_button" in script:
            return {"found": True}
        if "last_user_message" in script:
            evidence_reads += 1
            if evidence_reads == 1:
                raise RuntimeError("execution context destroyed after navigation")
            return {
                "url": "https://chatgpt.com/c/transient-recovered",
                "composer_empty": True,
                "user_count": 1,
                "last_user_message_id": "recovered-message",
                "last_user_turn": 1,
                "last_user_message": "recover evidence",
            }
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    evidence = ops["send_message"]("recover evidence")

    assert evidence["status"] == "definitely_sent"
    assert evidence["message_id"] == "recovered-message"


def test_send_message_returns_unknown_when_post_send_evidence_keeps_raising():
    def fake_js(script):
        if "existing_user_messages" in script:
            return {
                "found": True,
                "empty": True,
                "url": "https://chatgpt.com/",
                "user_count": 0,
                "user_message_ids": [],
                "last_user_turn": -1,
            }
        if "activate_send_button" in script:
            return {"found": True, "clicked": True}
        if "send_button" in script:
            return {"found": True}
        if "last_user_message" in script:
            raise RuntimeError("execution context destroyed after navigation")
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)
    evidence = ops["send_message"]("uncertain after click", evidence_timeout=0.01)

    assert evidence["status"] == "unknown"
    assert evidence["reason"] == "post_send_evidence_unavailable"


def test_send_message_rejects_nonempty_composer_before_typing_or_clicking():
    typed = []
    clicks = []
    ops = load_ops(
        lambda script: {"found": True, "empty": False, "url": "https://chatgpt.com/", "user_count": 0},
        type_impl=typed.append,
        click_impl=lambda *args: clicks.append(args),
    )

    with pytest.raises(RuntimeError, match="must be empty"):
        ops["send_message"]("do not send")
    assert typed == []
    assert clicks == []


def test_rename_chat_refuses_title_fragments_before_touching_browser():
    def unexpected_js(script):
        raise AssertionError(f"browser should not be touched: {script[:100]}")

    ops = load_ops(unexpected_js)

    with pytest.raises(RuntimeError, match="exact conversation URL or ID"):
        ops["rename_chat"]("ambiguous title fragment", "new title")


@pytest.mark.parametrize(
    "unsafe",
    [
        "some title /c/abcdefgh",
        "https://evil.example/c/abcdefgh",
        "https://chatgpt.com.evil.example/c/abcdefgh",
    ],
)
def test_conversation_id_rejects_prefixed_paths_and_foreign_hosts(unsafe):
    ops = load_ops(lambda script: None)
    with pytest.raises(RuntimeError, match="exact conversation URL or ID"):
        ops["_conversation_id"](unsafe)


def test_exact_options_lookup_fails_without_target_row_button():
    clicks = []
    ops = load_ops(
        lambda script: {"found": False, "count": 1},
        click_impl=lambda *args: clicks.append(args),
    )

    with pytest.raises(RuntimeError, match="exact sidebar row"):
        ops["_open_exact_conversation_options"]("abcdefgh")
    assert clicks == []


def test_rename_chat_targets_exact_url_and_verifies_persisted_title():
    conversation_id = "6a712ec4-5f78-83ea-b6fd-2b58edb87c98"
    new_title = "Verified Maintenance Chat"
    calls = []
    clicks = []
    navigations = []

    def fake_js(script):
        calls.append(script)
        if "history-item-" in script:
            return {"found": True}
        if "t === '重命名'" in script:
            return {"found": True}
        if "HTMLInputElement.prototype" in script:
            assert "el.blur()" in script
            assert "pointerdown" in script
            return {"found": True, "blurred": True, "commit_dispatched": True}
        if "inputGone" in script:
            return {"found": True, "input_gone": True, "title": new_title}
        raise AssertionError(f"unexpected JS: {script[:100]}")

    ops = load_ops(
        fake_js,
        click_impl=lambda *args: clicks.append(args),
        goto_impl=navigations.append,
    )
    result = ops["rename_chat"](
        f"https://chatgpt.com/c/{conversation_id}",
        new_title,
    )

    assert result == new_title
    assert clicks == []
    assert navigations == ["https://chatgpt.com/", f"https://chatgpt.com/c/{conversation_id}"]
    assert all(conversation_id in script for script in (calls[0], calls[-1]))


def test_send_and_wait_stops_on_unknown_send_without_retrying():
    ops = load_ops(lambda script: None)
    ops["send_message"] = lambda text: {"status": "unknown", "url": "https://chatgpt.com/"}

    with pytest.raises(RuntimeError, match="unknown.*do not retry"):
        ops["send_and_wait"]("hello", timeout=0)


def test_page_conversation_uses_real_page_keys_and_returns_virtualizer_state():
    states = iter([
        {"found": True, "scroll_top": 0, "scroll_height": 68000, "client_height": 800, "message_count": 19},
        {"found": True, "scroll_top": 760, "scroll_height": 68000, "client_height": 800, "message_count": 25},
    ])
    pressed = []

    def fake_js(script):
        if "message_count" in script:
            return next(states)
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js, press_impl=pressed.append)
    evidence = ops["page_conversation"]("down", steps=1)

    assert pressed == ["PageDown"]
    assert evidence["scroll_top"] == 760
    assert evidence["message_count"] == 25
    assert evidence["moved"] is True


def test_read_markdown_block_summary_returns_the_full_editor_text():
    full_markdown = "# 今日英语训练总结\n\n" + ("完整内容 " * 700)

    def fake_js(script):
        if "writing-block-editor" in script:
            return [{"text": full_markdown, "chars": len(full_markdown)}]
        raise AssertionError(f"unexpected JS: {script[:120]}")

    ops = load_ops(fake_js)

    assert ops["read_markdown_block_summary"]() == full_markdown
