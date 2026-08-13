import json
import shutil
import types
from pathlib import Path

import pytest

from browser_harness import agent_pool as pool


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    temporary = tmp_path / "temporary"
    monkeypatch.setattr(pool.paths, "runtime_dir", lambda: runtime)
    monkeypatch.setattr(pool, "TEMP_ROOT", temporary)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url, timeout=0.3: False)
    monkeypatch.setattr(pool, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(pool, "_profile_in_use", lambda profile: False)
    return temporary


def managed_profile(root: Path, task_id: str) -> Path:
    profile = root / task_id
    profile.mkdir(parents=True)
    (profile / pool.MANIFEST).write_text(json.dumps({"marker": pool.MARKER, "task_id": task_id}))
    return profile


def test_first_lease_gets_shared_and_second_gets_temporary(isolated):
    first = pool.reserve("researchbot", "example.com", "default", "read", now=10)
    second = pool.reserve("wikikeeper", "example.org", "default", "read", now=11)
    assert first["kind"] == "shared"
    assert second["kind"] == "temporary"


def test_write_lock_serializes_same_site_account(isolated):
    lease = pool.reserve("one", "example.com", "acct", "write", now=10)
    with pytest.raises(pool.PoolError, match="write resource is busy"):
        pool.reserve("two", "example.com", "acct", "write", now=11)
    pool.forget(lease["id"])
    assert pool.reserve("two", "example.com", "acct", "write", now=12)["mode"] == "write"


def test_different_write_keys_do_not_block(isolated):
    pool.reserve("one", "example.com", "a", "write", now=10)
    assert pool.reserve("two", "example.com", "b", "write", now=11)["mode"] == "write"


def test_heartbeat_refreshes_lease(isolated):
    lease = pool.reserve("one", "example.com", "a", "read", now=10)
    updated = pool.heartbeat(lease["id"], now=99)
    assert updated["heartbeat_at"] == 99


def test_default_owner_uses_profile_home(monkeypatch):
    monkeypatch.delenv("HERMES_PROFILE_NAME", raising=False)
    monkeypatch.delenv("HERMES_PROFILE", raising=False)
    monkeypatch.setenv("HERMES_HOME", "/Users/test/.hermes/profiles/researchbot")
    assert pool._default_owner() == "researchbot"


def test_legacy_hermes_call_is_managed(monkeypatch):
    monkeypatch.delenv("BH_AGENT_POOL_CHILD", raising=False)
    monkeypatch.setenv("HERMES_HOME", "/Users/test/.hermes/profiles/researchbot")
    assert pool.should_manage_legacy() is True
    monkeypatch.setenv("BH_AGENT_POOL_CHILD", "1")
    assert pool.should_manage_legacy() is False


def test_infer_site_uses_first_literal_url():
    assert pool.infer_site('new_tab("https://sub.example.com/path")') == "sub.example.com"
    assert pool.infer_site("print(page_info())") == "unknown"


def test_corrupt_state_fails_closed(isolated):
    path = pool._state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json")
    with pytest.raises(pool.PoolError, match="treating shared Chrome as busy"):
        pool.reserve("one", "example.com", "a", "read")


def test_cleanup_requires_expired_managed_temporary_profile(isolated):
    lease = pool.reserve("one", "example.com", "a", "read", now=0)
    second = pool.reserve("two", "example.org", "a", "read", now=0)
    profile = managed_profile(isolated, second["id"])
    second.update({"profile_dir": str(profile), "runner_pid": 999, "chrome_pid": 998, "cdp_url": "http://127.0.0.1:65530"})
    assert pool.cleanup_eligibility(second, now=pool.LEASE_TTL_SECONDS)[0] is False
    assert pool.cleanup_eligibility(second, now=pool.LEASE_TTL_SECONDS + 1) == (True, "eligible")
    assert pool.cleanup_eligibility(lease, now=pool.LEASE_TTL_SECONDS + 1)[0] is False


@pytest.mark.parametrize("bad_path", [
    Path("/Users/yelin/Developer/agent-tools/chrome-profiles/hermes-agent"),
    Path("/Users/yelin/Library/Application Support/Google/Chrome"),
])
def test_cleanup_rejects_long_lived_profiles(isolated, bad_path):
    lease = {"id": "x", "kind": "temporary", "profile_dir": str(bad_path), "heartbeat_at": 0}
    ok, reason = pool.cleanup_eligibility(lease, now=pool.LEASE_TTL_SECONDS + 1)
    assert not ok
    assert "outside managed temporary root" in reason


def test_cleanup_rejects_symlink_escape(isolated, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = isolated / "task"
    isolated.mkdir()
    link.symlink_to(outside, target_is_directory=True)
    lease = {"id": "task", "kind": "temporary", "profile_dir": str(link), "heartbeat_at": 0}
    assert pool.cleanup_eligibility(lease, now=pool.LEASE_TTL_SECONDS + 1)[0] is False


def test_reap_apply_deletes_only_eligible_profile(isolated, monkeypatch):
    pool.reserve("shared", "a.example", "a", "read", now=0)
    stale = pool.reserve("stale", "b.example", "a", "read", now=0)
    live = pool.reserve("live", "c.example", "a", "read", now=0)
    for lease in (stale, live):
        profile = managed_profile(isolated, lease["id"])
        lease.update({"profile_dir": str(profile), "runner_pid": 100 if lease is live else 99, "chrome_pid": None, "cdp_url": None})
        with pool._locked_state() as state:
            state["leases"][lease["id"]].update(lease)
    monkeypatch.setattr(pool, "_pid_alive", lambda pid: pid == 100)
    results = pool.reap(apply=True, now=pool.LEASE_TTL_SECONDS + 1)
    by_id = {item["lease_id"]: item for item in results}
    assert by_id[stale["id"]]["deleted"] is True
    assert by_id[live["id"]]["deleted"] is False
    assert not (isolated / stale["id"]).exists()
    assert (isolated / live["id"]).exists()


def test_reap_releases_stale_shared_lease_without_touching_chrome(isolated):
    lease = pool.reserve("shared", "a.example", "a", "write", now=0)
    result = pool.reap(apply=True, now=pool.LEASE_TTL_SECONDS + 1)
    assert result == [{
        "lease_id": lease["id"],
        "eligible": True,
        "reason": "stale shared lease",
        "deleted": False,
        "released": True,
        "terminated": False,
    }]
    assert pool.status()["leases"] == []


def test_reap_terminates_only_verified_stale_owned_chrome(isolated, monkeypatch):
    pool.reserve("shared", "a.example", "a", "read", now=0)
    lease = pool.reserve("temp", "b.example", "a", "read", now=0)
    profile = managed_profile(isolated, lease["id"])
    lease.update({"profile_dir": str(profile), "runner_pid": 10, "chrome_pid": 20, "cdp_url": "http://127.0.0.1:65530"})
    with pool._locked_state() as state:
        state["leases"][lease["id"]].update(lease)
    monkeypatch.setattr(pool, "_pid_alive", lambda pid: pid == 20)
    monkeypatch.setattr(pool, "_owned_chrome_identity", lambda item: item["id"] == lease["id"])
    terminated = []
    monkeypatch.setattr(pool, "_terminate_pid", terminated.append)
    results = pool.reap(apply=True, now=pool.LEASE_TTL_SECONDS + 1)
    item = next(result for result in results if result["lease_id"] == lease["id"])
    assert item["terminated"] is True
    assert item["deleted"] is False
    assert terminated == [20]
    assert profile.exists()


def test_managed_shared_run_releases_lease_and_daemon(monkeypatch):
    lease = {
        "id": "a" * 32,
        "owner": "researchbot",
        "kind": "shared",
        "cdp_url": pool.SHARED_CDP_URL,
        "profile_dir": None,
        "chrome_pid": None,
    }
    monkeypatch.setattr(pool, "reserve_wait", lambda *args, **kwargs: dict(lease))
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: True)
    calls = {}
    monkeypatch.setattr(pool.subprocess, "run", lambda command, **kwargs: calls.update(command=command, kwargs=kwargs) or types.SimpleNamespace(returncode=0))
    stopped = []
    forgotten = []
    monkeypatch.setattr(pool, "_stop_daemon", stopped.append)
    monkeypatch.setattr(pool, "forget", forgotten.append)
    assert pool.run_managed("researchbot", "example.com", "default", "read", "print(1)") == 0
    assert calls["kwargs"]["env"]["BH_AGENT_POOL_CHILD"] == "1"
    assert calls["kwargs"]["env"]["BU_CDP_URL"] == pool.SHARED_CDP_URL
    assert stopped == ["pool-" + "a" * 16]
    assert forgotten == ["a" * 32]


def test_managed_temporary_run_keeps_lease_when_cleanup_is_unsafe(tmp_path, monkeypatch):
    profile = tmp_path / ("b" * 32)
    profile.mkdir()
    lease = {
        "id": "b" * 32,
        "owner": "researchbot",
        "kind": "temporary",
        "cdp_url": "http://127.0.0.1:65530",
        "profile_dir": str(profile),
        "chrome_pid": 123,
    }
    monkeypatch.setattr(pool, "reserve_wait", lambda *args, **kwargs: dict(lease))
    monkeypatch.setattr(pool, "_start_temporary", lambda item: (None, item))
    monkeypatch.setattr(pool.subprocess, "run", lambda *args, **kwargs: types.SimpleNamespace(returncode=0))
    monkeypatch.setattr(pool, "_stop_daemon", lambda name: None)
    monkeypatch.setattr(pool, "_stop_owned_chrome", lambda item, process: None)
    monkeypatch.setattr(pool, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: False)
    monkeypatch.setattr(pool, "_safe_rmtree", lambda *args, **kwargs: (_ for _ in ()).throw(pool.PoolError("unsafe")))
    forgotten = []
    monkeypatch.setattr(pool, "forget", forgotten.append)
    assert pool.run_managed("researchbot", "example.com", "default", "read", "print(1)") == 0
    assert forgotten == []


def test_snapshot_requires_closed_source_and_keeps_previous(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "Local State").write_text("{}")
    template = tmp_path / "templates"
    monkeypatch.setattr(pool, "SOURCE_PROFILE", source)
    monkeypatch.setattr(pool, "ALLOWED_SOURCE_PROFILE", source)
    monkeypatch.setattr(pool, "TEMPLATE_ROOT", template)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: False)
    monkeypatch.setattr(pool, "_source_in_use", lambda path: False)
    monkeypatch.setattr(pool, "_copy_clone", lambda src, dst: shutil.copytree(src, dst))
    first = pool.snapshot()
    assert Path(first["current"]).is_dir()
    (source / "version").write_text("two")
    second = pool.snapshot()
    assert Path(second["current"], "version").read_text() == "two"
    assert Path(second["previous"], "Local State").is_file()
    monkeypatch.setattr(pool, "_source_in_use", lambda path: True)
    with pytest.raises(pool.PoolError, match="fully closed"):
        pool.snapshot()


def test_snapshot_source_check_ignores_stale_singleton_lock(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "SingletonLock").symlink_to("stale")
    own_check = f'python -c "check --user-data-dir={source}"'
    monkeypatch.setattr(pool.subprocess, "check_output", lambda *args, **kwargs: own_check)
    assert pool._source_in_use(source) is False
    chrome = f'Google Chrome --user-data-dir={source}'
    monkeypatch.setattr(pool.subprocess, "check_output", lambda *args, **kwargs: chrome)
    assert pool._source_in_use(source) is True


def test_find_chrome_pid_selects_main_process(tmp_path, monkeypatch):
    profile = tmp_path / "task"
    rows = "\n".join([
        f"12 {pool.CHROME_BINARY} --remote-debugging-port=5555 --user-data-dir={profile}",
        f"13 Google Chrome Helper --remote-debugging-port=5555 --user-data-dir={profile}",
    ])
    monkeypatch.setattr(pool.subprocess, "check_output", lambda *args, **kwargs: rows)
    assert pool._find_chrome_pid(profile, "http://127.0.0.1:5555") == 12


def test_stop_owned_chrome_refreshes_pid(isolated, monkeypatch):
    pool.reserve("shared", "a.example", "a", "read")
    lease = pool.reserve("temp", "b.example", "a", "read")
    profile = managed_profile(isolated, lease["id"])
    lease.update({"profile_dir": str(profile), "chrome_pid": 10, "cdp_url": "http://127.0.0.1:5555"})
    with pool._locked_state() as state:
        state["leases"][lease["id"]].update(lease)
    monkeypatch.setattr(pool, "_find_chrome_pid", lambda profile, url: 20 if 20 in alive else None)
    monkeypatch.setattr(pool, "_owned_chrome_identity", lambda item: item["chrome_pid"] == 20)
    alive = {20}
    monkeypatch.setattr(pool, "_pid_alive", lambda pid: pid in alive)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: bool(alive))
    monkeypatch.setattr(pool.os, "kill", lambda pid, sig: alive.discard(pid))
    pool._stop_owned_chrome(lease, None)
    assert lease["chrome_pid"] == 20
    assert pool._read_state()["leases"][lease["id"]]["chrome_pid"] == 20
