"""Focused regression tests for the Weibo topic sort routing."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("topic_facts.py")
SPEC = spec_from_file_location("weibo_topic_facts", MODULE_PATH)
topic_facts = module_from_spec(SPEC)
SPEC.loader.exec_module(topic_facts)

BASE_URL = "https://s.weibo.com/weibo?q=%23test%23&Refer=weibo_weibo"


@pytest.mark.parametrize(
    ("sort", "path", "required"),
    [
        ("general", "/weibo", "Refer=weibo_weibo"),
        ("hot", "/hot", "xsort=hot"),
        ("time", "/realtime", "rd=realtime"),
    ],
)
def test_topic_url_for_sort_maps_visible_tabs(sort, path, required):
    url = topic_facts._topic_url_for_sort(BASE_URL, sort=sort, page=2)

    assert path in url
    assert required in url
    assert "page=2" in url
    assert "q=%23test%23" in url


def test_topic_url_for_sort_rejects_unknown_sort():
    with pytest.raises(ValueError, match="sort must be one of"):
        topic_facts._topic_url_for_sort(BASE_URL, sort="popular")


def test_fetch_topic_facts_forwards_hot_sort_across_pages(monkeypatch):
    visited = []
    payloads = [
        {
            "stats": "阅读量1万 讨论量10",
            "posts": [{
                "author": "普通用户", "verify_type": "", "text": "sample-1",
                "url": "https://weibo.com/u/1", "acts": ["1", "2", "3"],
                "images": [], "image_thumbnails": [], "videos": [],
                "time": "刚刚", "source": "微博网页版", "verified": False,
            }],
        },
        {
            "stats": "阅读量1万 讨论量10",
            "posts": [{
                "author": "普通用户", "verify_type": "", "text": "sample-2",
                "url": "https://weibo.com/u/2", "acts": ["4", "5", "6"],
                "images": [], "image_thumbnails": [], "videos": [],
                "time": "刚刚", "source": "微博网页版", "verified": False,
            }],
        },
    ]

    monkeypatch.setattr(topic_facts, "goto_url", visited.append, raising=False)
    monkeypatch.setattr(topic_facts, "wait", lambda _seconds: None, raising=False)
    monkeypatch.setattr(topic_facts, "js", lambda _expression: payloads.pop(0), raising=False)

    result = topic_facts.fetch_topic_facts(BASE_URL, max_pages=2, sort="hot")

    assert result["sort"] == "hot"
    assert result["page_count"] == 2
    assert len(result["posts"]) == 2
    assert visited[0].startswith("https://s.weibo.com/hot?")
    assert "xsort=hot" in visited[0]
    assert "page=2" in visited[1]
