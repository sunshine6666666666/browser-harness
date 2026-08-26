from pathlib import Path


SKILL_PATH = (
    Path(__file__).parents[2]
    / "agent-workspace/domain-skills/gemini/basic_ops.py"
)
DOC_PATH = SKILL_PATH.with_suffix(".md")


def load_skill():
    namespace = {
        "js": lambda script, target_id=None: None,
        "wait": lambda seconds=0: None,
        "wait_for_load": lambda timeout=15: True,
        "new_tab": lambda url="about:blank": "tab",
        "goto_url": lambda url: None,
        "type_text": lambda text: None,
        "press_key": lambda key, modifiers=0: None,
        "cdp": lambda method, **params: None,
        "list_tabs": lambda include_chrome=True: [],
        "switch_tab": lambda target: None,
        "close_tab": lambda target=None: None,
    }
    exec(compile(SKILL_PATH.read_text(), str(SKILL_PATH), "exec"), namespace)
    return namespace


def test_start_deep_research_scrolls_then_clicks_exactly_once():
    namespace = load_skill()
    clicks = []

    def fake_js(script, target_id=None):
        if "scrollIntoView" in script:
            return {"found": True}
        if script == "location.href":
            return "https://gemini.google.com/app/conversation"
        return None

    namespace["js"] = fake_js
    namespace["_click_js"] = lambda script: clicks.append(script) or {"found": True}

    result = namespace["start_deep_research"]()

    assert result["status"] == "started"
    assert len(clicks) == 1


def test_wait_for_reply_ignores_old_reply_and_requires_stable_new_reply():
    namespace = load_skill()
    states = iter([
        {"assistant_count": 1, "has_stop": False, "len": 100},
        {"assistant_count": 2, "has_stop": False, "len": 120},
        {"assistant_count": 2, "has_stop": False, "len": 150},
        {"assistant_count": 2, "has_stop": False, "len": 150},
    ])
    observed = []

    def reply_state():
        state = next(states)
        observed.append(state)
        return state

    namespace["_reply_count_before_send"] = 1
    namespace["_reply_state"] = reply_state
    namespace["js"] = lambda script, target_id=None: "https://gemini.google.com/app/conversation"

    result = namespace["wait_for_reply"](timeout=1)

    assert result["status"] == "reply"
    assert result["assistant_count"] == 2
    assert len(observed) == 4


def test_skill_does_not_close_arbitrary_tabs_or_claim_bilibili_port():
    namespace = load_skill()
    assert "close_extra_tab" not in namespace
    assert "BU_CDP_URL=http://127.0.0.1:9226" not in DOC_PATH.read_text()


def test_merge_turn_page_preserves_order_with_mixed_ids():
    namespace = load_skill()
    accumulated = [
        {"role": "user", "text": "one", "id": "u1"},
        {"role": "assistant", "text": "first", "id": None},
    ]
    page = [
        {"role": "assistant", "text": "first", "id": None},
        {"role": "user", "text": "two", "id": "u2"},
        {"role": "assistant", "text": "second", "id": None},
    ]

    added = namespace["_merge_turn_page"](accumulated, page)

    assert added == 2
    assert [(turn["role"], turn["text"]) for turn in accumulated] == [
        ("user", "one"),
        ("assistant", "first"),
        ("user", "two"),
        ("assistant", "second"),
    ]


def test_share_url_allowlist_rejects_userinfo_ports_and_malformed_uuid():
    allowed = load_skill()["_share_url_allowed"]

    assert allowed("https://g.co/gemini/share/abcdef")
    assert allowed(
        "https://gemini.google.com/share/abcdef"
        "?skid=12345678-1234-1234-1234-123456789abc"
    )
    assert not allowed("https://attacker@g.co/gemini/share/abcdef")
    assert not allowed("https://g.co:444/gemini/share/abcdef")
    assert not allowed(
        "https://gemini.google.com/share/abcdef"
        "?skid=------------------------------------"
    )
