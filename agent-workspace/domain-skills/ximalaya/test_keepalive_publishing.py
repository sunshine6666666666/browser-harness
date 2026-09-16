import importlib.util
from pathlib import Path

import pytest


BASE = Path(__file__).parents[3] / "tests/unit/test_ximalaya_publishing.py"
spec = importlib.util.spec_from_file_location("ximalaya_base_tests", BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def evidence(track_id, album_id="88294964", title="保活标题"):
    return {
        "track_id": str(track_id), "album_id": album_id, "album_name": "测试专辑",
        "title": title, "duration_seconds": 90.0, "status": 1,
        "published_at": "2026-09-16 10:00:00", "updated_at": "2026-09-16 10:00:00",
        "cover_path": "/cover.jpg", "description": "简介", "category_id": 5,
        "visibility": 0, "publish_state": 1, "is_paid": False, "is_own": True,
        "can_delete": True, "audio_resource_id": "resource-" + str(track_id),
        "audio_resource_path": "/track/" + str(track_id),
    }


def load():
    return base.load_publishing()


def test_successor_preflight_ignores_other_album_same_title(tmp_path):
    namespace, page = load()
    old = evidence("42")
    namespace["track_evidence"] = lambda *args: old
    namespace["archive_matches"] = lambda title: [
        {"content_id": "77", "album_id": "999", "title": title},
        {"content_id": "42", "album_id": "88294964", "title": title},
    ]
    namespace["_validate_upload_file"] = lambda path: Path(path)
    namespace["_probed_audio"] = lambda path: {"duration": 90.0}
    audio = tmp_path / "audio-new.m4a"
    audio.write_bytes(b"x")
    result = namespace["prepare_successor_upload"](old, str(audio))
    assert result["status"] == "prepared"
    assert len(page.upload_calls) == 1


def test_successor_preflight_does_not_require_account_identity_fields(tmp_path):
    namespace, page = load()
    old = evidence("42")
    old["is_own"] = None
    old["account_uid"] = ""
    namespace["track_evidence"] = lambda *args: old
    namespace["archive_matches"] = lambda title: [{
        "content_id": "42", "album_id": "88294964", "title": title,
    }]
    namespace["_validate_upload_file"] = lambda path: Path(path)
    namespace["_probed_audio"] = lambda path: {"duration": 90.0}
    audio = tmp_path / "audio-new.m4a"
    audio.write_bytes(b"x")
    result = namespace["prepare_successor_upload"](old, str(audio))
    assert result["status"] == "prepared"
    assert len(page.upload_calls) == 1


def test_successor_preflight_rejects_missing_free_evidence(tmp_path):
    namespace, page = load()
    old = evidence("42")
    old["is_paid"] = None
    namespace["track_evidence"] = lambda *args: old
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="free public deletable"):
        namespace["prepare_successor_upload"](old, str(audio))
    assert page.upload_calls == []


def test_successor_submit_uses_unique_album_set_difference(monkeypatch):
    namespace, page = load()
    old = evidence("42")
    namespace["list_album_tracks"] = lambda album_id: [
        {"track_id": "42"},
    ] if not getattr(page, "successor_seen", False) else [
        {"track_id": "42"}, {"track_id": "99"},
    ]
    namespace["track_evidence"] = lambda album, track, title: evidence(track)
    snapshot = {
        "identity": {"uid": 1, "name": "test"}, "upload_ready": True,
        "rows": [], "title": old["title"], "album": "测试专辑", "scheduled": False,
        "schedule": "", "submit": {"disabled": False, "text": "确认发布"},
        "validation_errors": [], "modal": "",
    }
    namespace["submission_snapshot"] = lambda: dict(snapshot)
    original = namespace["list_album_tracks"]
    calls = {"n": 0}

    def tracks(album_id):
        calls["n"] += 1
        return [{"track_id": "42"}] if calls["n"] == 1 else [{"track_id": "42"}, {"track_id": "99"}]

    namespace["list_album_tracks"] = tracks
    result = namespace["submit_successor_once"](old, run_marker="keepalive", timeout=1)
    assert result["status"] == "verified"
    assert result["new_track_id"] == "99"
    assert result["submit_clicks"] == 1
    assert page.submit_js_clicks == 1


def test_successor_submit_unknown_never_clicks_twice():
    namespace, page = load()
    old = evidence("42")
    namespace["list_album_tracks"] = lambda album_id: [{"track_id": "42"}]
    namespace["track_evidence"] = lambda *args: evidence("42")
    snapshot = {
        "identity": {"uid": 1, "name": "test"}, "upload_ready": True,
        "rows": [], "title": old["title"], "album": "测试专辑", "scheduled": False,
        "schedule": "", "submit": {"disabled": False, "text": "确认发布"},
        "validation_errors": [], "modal": "",
    }
    namespace["submission_snapshot"] = lambda: dict(snapshot)
    result = namespace["submit_successor_once"](old, run_marker="keepalive", timeout=0.01)
    assert result["status"] == "submission_unverified"
    assert result["retry"] is False
    assert page.submit_js_clicks == 1


def test_published_delete_requires_verified_successor_and_deletes_old_once(tmp_path):
    namespace, _ = load()
    old = evidence("42")
    backup = tmp_path / "old.m4a"
    backup.write_bytes(b"old")
    old["local_audio_path"] = str(backup)
    successor = {"status": "verified", "track_id": "99", "new_track_id": "99",
                 "album_id": "88294964", "title": old["title"]}
    namespace["track_evidence"] = lambda album, track, title: evidence(track)
    calls = {"list": 0, "post": 0}

    def tracks(album_id):
        calls["list"] += 1
        return ([{"track_id": "42", "title": old["title"]},
                 {"track_id": "99", "title": old["title"]}]
                if calls["list"] == 1 else [{"track_id": "99", "title": old["title"]}])

    namespace["list_album_tracks"] = tracks
    namespace["_api_post"] = lambda *args: calls.__setitem__("post", calls["post"] + 1) or {}
    result = namespace["delete_published_track_once"](old, successor, confirm=True, timeout=1)
    assert result["status"] == "deleted"
    assert result["delete_activated"] is True
    assert calls["post"] == 1

    with pytest.raises(RuntimeError, match="verified successor"):
        namespace["delete_published_track_once"](
            old, {**successor, "status": "submission_unverified"}, confirm=True,
        )
