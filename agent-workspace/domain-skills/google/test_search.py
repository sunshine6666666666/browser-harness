"""Focused regression tests for the Google search Domain Skill."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("search.py")
SPEC = spec_from_file_location("google_search", MODULE_PATH)
search_mod = module_from_spec(SPEC)
SPEC.loader.exec_module(search_mod)


def _serp_payload():
    """Simulated SERP extraction output (what js(_EXTRACT_JS) returns)."""
    return [
        {"title": "Tianxingzhou Yangtze River Bridge", "url": "https://en.wikipedia.org/wiki/Tianxingzhou_Yangtze_River_Bridge", "snippet": "The Tianxingzhou Yangtze River Bridge (Chinese: 武汉天兴洲长江大桥) is a combined road and rail bridge."},
        {"title": "天兴洲长江大桥", "url": "https://english.wuhan.gov.cn/bridge/tianxinzhou/index.shtml", "snippet": "The Tianxingzhou Yangtze River Bridge connects Qingshan District."},
        {"title": "Tianxingzhou Yangtse Bridge", "url": "https://baike.baidu.com/en/item/Tianxingzhou%20Yangtse%20Bridge/663568", "snippet": "The Tianxingzhou Yangtse Bridge is a river-crossing link."},
        {"title": "Wuhan Yangtze River Bridge", "url": "https://www.wikiwand.com/en/Wuhan_Yangtze_River_Bridge", "snippet": "The Wuhan Yangtze Great Bridge is a double-deck road and rail bridge."},
    ]


def test_search_returns_structured_results(monkeypatch):
    calls = {}
    monkeypatch.setattr(search_mod, "goto_url", lambda url: calls.setdefault("urls", []).append(url), raising=False)
    monkeypatch.setattr(search_mod, "wait", lambda _s: None, raising=False)
    monkeypatch.setattr(search_mod, "js", lambda _e: _serp_payload(), raising=False)
    monkeypatch.setattr(search_mod, "time", type("T", (), {"sleep": staticmethod(lambda _s: None)})(), raising=False)

    results = search_mod.search("武汉天兴洲长江大桥 official english name", num_results=8, min_delay=0)

    assert len(results) == 4
    r = results[0]
    assert r["query"] == "武汉天兴洲长江大桥 official english name"
    assert r["rank"] == 1
    assert r["title"] == "Tianxingzhou Yangtze River Bridge"
    assert r["url"].startswith("https://en.wikipedia.org")
    assert r["source_domain"] == "en.wikipedia.org"
    assert "武汉天兴洲长江大桥" in r["snippet"]
    assert results[1]["source_domain"] == "english.wuhan.gov.cn"
    assert results[2]["source_domain"] == "baike.baidu.com"
    assert results[3]["source_domain"] == "wikiwand.com"  # www. stripped


def test_search_ranks_are_sequential(monkeypatch):
    monkeypatch.setattr(search_mod, "goto_url", lambda url: None, raising=False)
    monkeypatch.setattr(search_mod, "wait", lambda _s: None, raising=False)
    monkeypatch.setattr(search_mod, "js", lambda _e: _serp_payload(), raising=False)
    monkeypatch.setattr(search_mod, "time", type("T", (), {"sleep": staticmethod(lambda _s: None)})(), raising=False)

    results = search_mod.search("q", num_results=8, min_delay=0)
    assert [r["rank"] for r in results] == [1, 2, 3, 4]


def test_search_caps_num_results(monkeypatch):
    seen = {}
    monkeypatch.setattr(search_mod, "goto_url", lambda url: seen.setdefault("url", url), raising=False)
    monkeypatch.setattr(search_mod, "wait", lambda _s: None, raising=False)
    monkeypatch.setattr(search_mod, "js", lambda _e: _serp_payload() * 5, raising=False)
    monkeypatch.setattr(search_mod, "time", type("T", (), {"sleep": staticmethod(lambda _s: None)})(), raising=False)

    results = search_mod.search("q", num_results=20, min_delay=0)
    assert len(results) == 20  # clamped payload
    assert "num=20" in seen["url"]

    results3 = search_mod.search("q", num_results=3, min_delay=0)
    assert len(results3) == 3


def test_search_raises_on_captcha(monkeypatch):
    monkeypatch.setattr(search_mod, "goto_url", lambda url: None, raising=False)
    monkeypatch.setattr(search_mod, "wait", lambda _s: None, raising=False)
    monkeypatch.setattr(search_mod, "js", lambda _e: "https://www.google.com/sorry/index?continue=...", raising=False)
    monkeypatch.setattr(search_mod, "time", type("T", (), {"sleep": staticmethod(lambda _s: None)})(), raising=False)

    with pytest.raises(RuntimeError, match="captcha"):
        search_mod.search("q", min_delay=0)


def test_search_raises_on_empty_serp(monkeypatch):
    monkeypatch.setattr(search_mod, "goto_url", lambda url: None, raising=False)
    monkeypatch.setattr(search_mod, "wait", lambda _s: None, raising=False)
    monkeypatch.setattr(search_mod, "js", lambda _e: [], raising=False)
    monkeypatch.setattr(search_mod, "time", type("T", (), {"sleep": staticmethod(lambda _s: None)})(), raising=False)

    with pytest.raises(RuntimeError, match="no search result"):
        search_mod.search("q", min_delay=0)


def test_search_raises_on_consent_page(monkeypatch):
    monkeypatch.setattr(search_mod, "goto_url", lambda url: None, raising=False)
    monkeypatch.setattr(search_mod, "wait", lambda _s: None, raising=False)
    # First js call returns normal URL; second (post-extraction consent check) returns True
    monkeypatch.setattr(search_mod, "js", lambda _e: True if "consent" in str(_e) else "https://www.google.com/search?q=q", raising=False)
    monkeypatch.setattr(search_mod, "time", type("T", (), {"sleep": staticmethod(lambda _s: None)})(), raising=False)

    with pytest.raises(RuntimeError, match="consent"):
        search_mod.search("q", min_delay=0)


def test_search_many_chunks_limit():
    with pytest.raises(ValueError, match="chunk"):
        search_mod.search_many(["q"] * (search_mod.MAX_BATCH_QUERIES + 1), min_delay=0)


def test_search_many_returns_per_query(monkeypatch):
    monkeypatch.setattr(search_mod, "goto_url", lambda url: None, raising=False)
    monkeypatch.setattr(search_mod, "wait", lambda _s: None, raising=False)
    monkeypatch.setattr(search_mod, "js", lambda _e: _serp_payload(), raising=False)
    monkeypatch.setattr(search_mod, "time", type("T", (), {"sleep": staticmethod(lambda _s: None)})(), raising=False)

    out = search_mod.search_many(["武汉天兴洲长江大桥 official english name", "武汉长江大桥 official english name"], min_delay=0)
    assert len(out) == 2
    assert out[0][0]["query"] == "武汉天兴洲长江大桥 official english name"
    assert out[1][0]["query"] == "武汉长江大桥 official english name"


def test_search_rejects_empty_query(monkeypatch):
    monkeypatch.setattr(search_mod, "time", type("T", (), {"sleep": staticmethod(lambda _s: None)})(), raising=False)
    with pytest.raises(ValueError, match="non-empty"):
        search_mod.search("  ", min_delay=0)
