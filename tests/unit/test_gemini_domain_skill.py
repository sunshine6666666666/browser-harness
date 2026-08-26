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


def test_turn_match_accepts_a_visible_wrapper_around_submitted_text():
    namespace = load_skill()

    assert namespace["_turn_matches"](
        "BH-GEMINI-AUDIT-20260827-014800",
        "You said: BH-GEMINI-AUDIT-20260827-014800 (submitted)",
    )


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


def test_rename_conversation_targets_exact_current_url_and_observes_persistence():
    namespace = load_skill()
    conversation_id = "abc12345_exact"
    title = "2026-08-27 English Coach"
    calls = []
    title_reads = {"n": 0}

    def fake_js(script, target_id=None):
        calls.append(script)
        if script == "location.href":
            return f"https://gemini.google.com/app/{conversation_id}"
        if "url.pathname === '/app/' + wanted" in script and "menu_present" in script:
            return {"found": True, "count": 1, "menu_present": True}
        if "const wanted =" in script and "url.pathname === '/app/' + wanted" in script and "menu_present" not in script:
            title_reads["n"] += 1
            return {"found": True, "count": 1, "input_present": False, "title": title}
        if "['重命名', 'Rename'].includes" in script:
            return {"found": True}
        if "(e.type || 'text') === 'text'" in script and "value_set" not in script:
            return {"found": True, "value": "old title"}
        if "value_set" in script:
            return {"found": True, "blurred": True, "value_set": True}
        raise AssertionError(f"unexpected JS: {script[:160]}")

    namespace["js"] = fake_js
    namespace["_click_js"] = lambda script: (
        {"found": True} if "const wanted" in script or "重命名" in script or "打开边栏" in script else
        (_ for _ in ()).throw(AssertionError(f"unexpected click script: {script[:120]}"))
    )
    namespace["wait"] = lambda seconds=0: None

    result = namespace["rename_conversation"](title)

    assert result["status"] == "definitely_renamed"
    assert result["conversation_id"] == conversation_id
    assert title_reads["n"] == 2
    assert all(conversation_id in script for script in calls if "url.pathname" in script)


def test_rename_conversation_does_not_touch_browser_for_ambiguous_exact_rows():
    namespace = load_skill()
    calls = []

    def fake_js(script, target_id=None):
        calls.append(script)
        if script == "location.href":
            return "https://gemini.google.com/app/abc12345_exact"
        if "menu_present" in script:
            return {"found": False, "count": 2}
        raise AssertionError(f"unexpected JS after exact-row failure: {script[:120]}")

    namespace["js"] = fake_js
    namespace["_click_js"] = lambda script: {"found": False}
    result = namespace["rename_conversation"]("new title")

    assert result["status"] == "failed"
    assert len(calls) == 2


def test_conversation_snapshot_marks_partial_without_claiming_full_coverage():
    namespace = load_skill()
    visible = [{"role": "user", "text": "visible prompt", "id": "u1"}]
    namespace["js"] = lambda script, target_id=None: "https://gemini.google.com/app/abc12345_exact" if script == "location.href" else None
    namespace["full_conversation"] = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boundary"))
    namespace["conversation_turns"] = lambda: visible

    result = namespace["conversation_snapshot"]()

    assert result["coverage"] == "partial"
    assert result["turns"] == visible
    assert result["status"] == "partial"


def test_full_conversation_reads_virtualized_pages_to_stable_boundaries():
    namespace = load_skill()
    page_turns = iter([
        [{"role": "user", "text": "one", "id": "u1"}],
        [{"role": "user", "text": "one", "id": "u1"}],
        [{"role": "user", "text": "one", "id": "u1"}],
        [{"role": "user", "text": "one", "id": "u1"}],
        [{"role": "user", "text": "one", "id": "u1"},
         {"role": "assistant", "text": "first", "id": "a1"}],
        [{"role": "assistant", "text": "first", "id": "a1"},
         {"role": "user", "text": "two", "id": "u2"},
         {"role": "assistant", "text": "second", "id": "a2"}],
        [{"role": "user", "text": "two", "id": "u2"},
         {"role": "assistant", "text": "second", "id": "a2"}],
        [{"role": "user", "text": "two", "id": "u2"},
         {"role": "assistant", "text": "second", "id": "a2"}],
    ])
    page_states = iter([
        {"moved": True}, {"moved": False}, {"moved": False},
        {"moved": True}, {"moved": False}, {"moved": False},
        {"moved": False}, {"moved": False},
    ])
    namespace["conversation_turns"] = lambda: next(page_turns)
    namespace["_page_or_static"] = lambda direction, wait_s: next(page_states)
    namespace["expand_all_user_messages"] = lambda: 0
    namespace["js"] = lambda script, target_id=None: "https://gemini.google.com/app/abc12345_exact" if script == "location.href" else None

    result = namespace["full_conversation"](max_pages=20, wait_s=0)

    assert result["status"] == "complete"
    assert [(turn["role"], turn["text"]) for turn in result["turns"]] == [
        ("user", "one"), ("assistant", "first"),
        ("user", "two"), ("assistant", "second"),
    ]
    assert result["pages"] == 8


def test_summary_request_is_idempotent_against_full_ordered_turns():
    namespace = load_skill()
    prompt = "Please summarize this conversation once."
    namespace["conversation_snapshot"] = lambda: {
        "coverage": "full",
        "url": "https://gemini.google.com/app/abc12345_exact",
        "turns": [
            {"role": "user", "text": prompt, "id": "u1"},
            {"role": "assistant", "text": "summary", "id": "a1"},
        ],
    }
    sent = []
    namespace["send_message"] = lambda text: sent.append(text)

    result = namespace["request_conversation_summary"](prompt)

    assert result["status"] == "already_requested"
    assert sent == []
