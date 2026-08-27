import io
import json
import sys
import types

import pytest

from browser_harness import agent_pool as pool


PRIMARY = {"name": "共享主浏览器", "cdp_url": "http://127.0.0.1:9223", "status": "running", "health": "ok"}
MONITOR = {"name": "热点监控", "cdp_url": "http://127.0.0.1:9224", "status": "running", "health": "ok"}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(pool.paths, "runtime_dir", lambda: runtime)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url, timeout=0.3: False)
    monkeypatch.setattr(pool, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(pool, "_resolve_browser", lambda name: dict(MONITOR if name == "热点监控" else PRIMARY))
    return runtime


def persist_lease(lease: dict) -> None:
    with pool._locked_state() as state:
        state["leases"][lease["id"]] = dict(lease)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload.encode()


def test_only_one_shared_lease_exists_at_a_time(isolated):
    first = pool.reserve("researchbot", "example.com", "default", "read", now=10)
    assert first["kind"] == "shared"
    with pytest.raises(pool.PoolError, match="managed browser is busy"):
        pool.reserve("wikikeeper", "example.org", "default", "read", now=11)
    pool.forget(first["id"])
    assert pool.reserve("wikikeeper", "example.org", "default", "read", now=12)["kind"] == "shared"


def test_write_lock_serializes_same_site_account(isolated):
    lease = pool.reserve("one", "example.com", "acct", "write", now=10)
    with pytest.raises(pool.PoolError, match="write resource is busy"):
        pool.reserve("two", "example.com", "acct", "write", now=11)
    pool.forget(lease["id"])
    assert pool.reserve("two", "example.com", "acct", "write", now=12)["mode"] == "write"


def test_different_write_keys_still_share_one_browser(isolated):
    pool.reserve("one", "example.com", "a", "write", now=10)
    with pytest.raises(pool.PoolError, match="managed browser is busy"):
        pool.reserve("two", "example.com", "b", "write", now=11)


def test_different_browsers_hold_independent_leases(isolated):
    first = pool.reserve("one", "example.com", "a", "write", browser=PRIMARY, now=10)
    second = pool.reserve("two", "example.com", "a", "write", browser=MONITOR, now=11)
    assert first["resource_key"] != second["resource_key"]
    assert {first["browser_name"], second["browser_name"]} == {"共享主浏览器", "热点监控"}


def test_resolver_uses_exact_browser_name_and_validates_output(monkeypatch):
    calls = []
    payload = {**MONITOR, "port": 9224}
    monkeypatch.setattr(pool.subprocess, "run", lambda command, **kwargs: (
        calls.append((command, kwargs)) or types.SimpleNamespace(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )
    ))
    resolved = pool._resolve_browser("热点监控")
    assert calls[0][0][-2:] == ["--name", "热点监控"]
    assert calls[0][1]["timeout"] == 10
    assert resolved["cdp_url"] == MONITOR["cdp_url"]


def test_resolver_rejects_non_loopback_cdp(monkeypatch):
    payload = {**MONITOR, "cdp_url": "http://192.168.1.2:9224"}
    monkeypatch.setattr(pool.subprocess, "run", lambda *args, **kwargs: types.SimpleNamespace(
        returncode=0, stdout=json.dumps(payload), stderr=""
    ))
    with pytest.raises(pool.PoolError, match="loopback"):
        pool._resolve_browser("热点监控")


def _audit_result(*registered):
    return types.SimpleNamespace(
        returncode=0,
        stdout=json.dumps({"registered": list(registered)}),
        stderr="",
    )


def test_browser_name_for_cdp_matches_healthy_registered_port(monkeypatch):
    browser = {"name": "SAU-自媒体运营-2号-9226", "port": 9226,
               "status": "running", "health": "ok", "problems": []}
    monkeypatch.setattr(pool.subprocess, "run", lambda *args, **kwargs: _audit_result(browser))
    assert pool.browser_name_for_cdp("http://127.0.0.1:9226") == browser["name"]


def test_browser_name_for_cdp_keeps_unregistered_endpoint_exact(monkeypatch):
    monkeypatch.setattr(pool.subprocess, "run", lambda *args, **kwargs: _audit_result())
    assert pool.browser_name_for_cdp("http://127.0.0.1:9333") is None


def test_browser_name_for_cdp_ignores_remote_websocket(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("remote endpoints must not invoke fleet audit")
    monkeypatch.setattr(pool.subprocess, "run", fail)
    assert pool.browser_name_for_cdp("wss://provider.example/devtools/browser/id") is None


def test_browser_name_for_cdp_rejects_malformed_port():
    with pytest.raises(pool.PoolError, match="invalid port"):
        pool.browser_name_for_cdp("http://127.0.0.1:not-a-port")


def test_browser_name_for_cdp_rejects_duplicate_registration(monkeypatch):
    browser = {"name": "browser", "port": 9226, "status": "running",
               "health": "ok", "problems": []}
    monkeypatch.setattr(pool.subprocess, "run", lambda *args, **kwargs: _audit_result(browser, browser))
    with pytest.raises(pool.PoolError, match="multiple registrations"):
        pool.browser_name_for_cdp("ws://localhost:9226")


def test_browser_name_for_cdp_rejects_unhealthy_registration(monkeypatch):
    browser = {"name": "browser", "port": 9226, "status": "running",
               "health": "error", "problems": ["conflict"]}
    monkeypatch.setattr(pool.subprocess, "run", lambda *args, **kwargs: _audit_result(browser))
    with pytest.raises(pool.PoolError, match="not healthy"):
        pool.browser_name_for_cdp("http://127.0.0.1:9226")


def test_heartbeat_refreshes_lease(isolated):
    lease = pool.reserve("one", "example.com", "a", "read", now=10)
    updated = pool.heartbeat(lease["id"], now=99)
    assert updated["heartbeat_at"] == 99


def test_reap_reports_dead_runner_window_and_remaining_ttl(isolated):
    pool.reserve("one", "example.com", "a", "write", now=0)
    now = pool.DEAD_RUNNER_GRACE_SECONDS - 1

    result = pool.reap(now=now)

    assert result[0]["eligible"] is False
    assert result[0]["runner_dead"] is True
    assert result[0]["heartbeat_age_seconds"] == now
    assert result[0]["remaining_ttl_seconds"] == pool.LEASE_TTL_SECONDS - now
    assert result[0]["reap_in_seconds"] == 1
    assert "controlled reap window" in result[0]["reason"]


def test_reap_releases_dead_runner_after_controlled_window(isolated):
    lease = pool.reserve("one", "example.com", "a", "write", now=0)
    now = pool.DEAD_RUNNER_GRACE_SECONDS + 1

    result = pool.reap(apply=True, now=now)

    assert result[0]["lease_id"] == lease["id"]
    assert result[0]["eligible"] is True
    assert result[0]["runner_dead"] is True
    assert result[0]["remaining_ttl_seconds"] == pool.LEASE_TTL_SECONDS - now
    assert result[0]["released"] is True
    assert pool.status()["leases"] == []


def test_reap_keeps_live_runner_even_after_ttl(isolated, monkeypatch):
    monkeypatch.setattr(pool, "_pid_alive", lambda pid: True)
    pool.reserve("one", "example.com", "a", "write", now=0)

    result = pool.reap(now=pool.LEASE_TTL_SECONDS + 1)

    assert result[0]["eligible"] is False
    assert result[0]["runner_dead"] is False
    assert result[0]["remaining_ttl_seconds"] == 0.0
    assert result[0]["reap_in_seconds"] is None
    assert result[0]["reason"] == "shared lease is active"


def test_run_managed_passes_configured_wait_timeout(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        pool,
        "_run_with_lease",
        lambda *args, **kwargs: seen.update(args=args, kwargs=kwargs) or 0,
    )

    assert pool.run_managed(
        "owner", "example.com", "default", "read", "print(1)",
        browser_name="browser", wait_timeout=12.5,
    ) == 0
    assert seen["kwargs"]["wait_timeout"] == 12.5


def test_cli_exposes_wait_timeout(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        pool,
        "run_managed",
        lambda *args, **kwargs: seen.update(args=args, kwargs=kwargs) or 0,
    )
    monkeypatch.setattr(pool.sys, "stdin", io.StringIO("print(1)"))

    assert pool.run_cli(["run", "--site", "example.com", "--wait-timeout", "7.5"]) == 0
    assert seen["kwargs"]["wait_timeout"] == 7.5


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


def test_list_page_targets_rejects_non_loopback_cdp(monkeypatch):
    called = []
    monkeypatch.setattr(pool.urllib.request, "urlopen", lambda *args, **kwargs: called.append(args))
    for url in ("", "https://127.0.0.1:9223", "http://192.168.1.2:9223", "http://127.0.0.1", "http://127.0.0.1:0"):
        with pytest.raises(pool.PoolError):
            pool.list_page_targets(url)
    assert called == []


def test_close_task_targets_closes_only_current_minus_baseline(monkeypatch):
    current = {"keep-a", "new-b", "new-c"}
    close_calls = []

    def fake_urlopen(url, timeout):
        if url.endswith("/json/list"):
            return FakeResponse(json.dumps([
                {"type": "page", "id": target_id} for target_id in sorted(current)
            ]))
        close_calls.append(url.rsplit("/", 1)[-1])
        current.remove(close_calls[-1])
        return FakeResponse("OK")

    monkeypatch.setattr(pool.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-a")
    result = pool.close_task_targets("http://127.0.0.1:9223", ["keep-a"], "browser-a")
    assert close_calls == ["new-b", "new-c"]
    assert result == {
        "closed": ["new-b", "new-c"],
        "remaining": [],
        "baseline_preserved": True,
        "browser_restarted": False,
    }


def test_close_task_targets_preserves_baseline_when_close_fails(monkeypatch):
    close_calls = []

    def fake_urlopen(url, timeout):
        if url.endswith("/json/list"):
            return FakeResponse(json.dumps([
                {"type": "page", "id": "keep-a"},
                {"type": "page", "id": "new-b"},
            ]))
        close_calls.append(url.rsplit("/", 1)[-1])
        raise OSError("close failed")

    monkeypatch.setattr(pool.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-a")
    with pytest.raises(pool.PoolError, match="close failed"):
        pool.close_task_targets("http://127.0.0.1:9223", ["keep-a"], "browser-a")
    assert close_calls == ["new-b"]


def test_close_task_targets_allows_baseline_to_disappear(monkeypatch):
    states = iter([{"keep-a", "new-b"}, set()])
    monkeypatch.setattr(pool, "list_page_targets", lambda url: next(states))
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-a")
    monkeypatch.setattr(pool.urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse("OK"))
    result = pool.close_task_targets("http://127.0.0.1:9223", ["keep-a"], "browser-a")
    assert result["closed"] == ["new-b"]
    assert result["browser_restarted"] is False


def test_close_task_targets_does_not_touch_restarted_browser(monkeypatch):
    close_calls = []
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-b")
    monkeypatch.setattr(pool, "list_page_targets", lambda url: {"new-browser-tab"})
    monkeypatch.setattr(pool.urllib.request, "urlopen", lambda url, timeout: close_calls.append(url))
    result = pool.close_task_targets("http://127.0.0.1:9223", ["old-tab"], "browser-a")
    assert result["browser_restarted"] is True
    assert result["closed"] == []
    assert close_calls == []


def test_corrupt_state_fails_closed(isolated):
    path = pool._state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json")
    with pytest.raises(pool.PoolError, match="treating managed browsers as busy"):
        pool.reserve("one", "example.com", "a", "read")


def test_duplicate_browser_leases_fail_closed(isolated):
    path = pool._state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    leases = {
        lease_id: {"id": lease_id, "cdp_url": PRIMARY["cdp_url"]}
        for lease_id in ("a", "b")
    }
    path.write_text(json.dumps({"version": 1, "leases": leases, "write_locks": {}}))
    with pytest.raises(pool.PoolError, match="duplicate browser leases"):
        pool._read_state()


def test_reap_releases_stale_shared_lease_without_touching_chrome(isolated):
    lease = pool.reserve("shared", "a.example", "a", "write", now=0)
    result = pool.reap(apply=True, now=pool.LEASE_TTL_SECONDS + 1)
    assert result == [{
        "lease_id": lease["id"],
        "eligible": True,
        "reason": "legacy stale shared lease; no target cleanup evidence",
        "deleted": False,
        "released": True,
        "terminated": False,
        "runner_alive": False,
        "runner_dead": True,
        "child_alive": None,
        "heartbeat_age_seconds": pool.LEASE_TTL_SECONDS + 1,
        "remaining_ttl_seconds": 0.0,
        "reclaimable_in_seconds": 0.0,
        "reap_in_seconds": 0.0,
    }]
    assert pool.status()["leases"] == []


def test_reap_cleans_stale_shared_task_targets_before_releasing_lease(isolated, monkeypatch):
    lease = pool.reserve("shared", "a.example", "a", "read", now=0)
    with pool._locked_state() as state:
        state["leases"][lease["id"]]["baseline_target_ids"] = ["keep-a"]
        state["leases"][lease["id"]]["browser_identity"] = "browser-a"
    cleaned = []
    monkeypatch.setattr(pool, "close_task_targets", lambda url, baseline, identity: cleaned.append((url, baseline, identity)) or {
        "closed": ["new-b"], "remaining": [], "baseline_preserved": True, "browser_restarted": False,
    })
    result = pool.reap(apply=True, now=pool.LEASE_TTL_SECONDS + 1)
    assert cleaned == [(PRIMARY["cdp_url"], ["keep-a"], "browser-a")]
    assert result[0]["released"] is True
    assert pool.status()["leases"] == []


def test_reap_keeps_stale_shared_lease_when_target_cleanup_fails(isolated, monkeypatch):
    lease = pool.reserve("shared", "a.example", "a", "read", now=0)
    with pool._locked_state() as state:
        state["leases"][lease["id"]]["baseline_target_ids"] = ["keep-a"]
        state["leases"][lease["id"]]["browser_identity"] = "browser-a"
    monkeypatch.setattr(pool, "close_task_targets", lambda *args: (_ for _ in ()).throw(pool.PoolError("cleanup failed")))
    result = pool.reap(apply=True, now=pool.LEASE_TTL_SECONDS + 1)
    assert result[0]["released"] is False
    assert "cleanup failed" in result[0]["reason"]
    assert pool.status()["leases"][0]["id"] == lease["id"]


def test_reap_reclaims_tracked_orphan_after_short_grace(isolated, monkeypatch):
    lease = pool.reserve("shared", "a.example", "a", "write", now=0)
    with pool._locked_state() as state:
        state["leases"][lease["id"]].update({
            "child_pid": 999_999,
            "baseline_target_ids": ["keep-a"],
            "browser_identity": "browser-a",
        })
    monkeypatch.setattr(pool, "close_task_targets", lambda *args: {
        "closed": [], "remaining": [], "baseline_preserved": True,
        "browser_restarted": False,
    })

    waiting = pool.reap(now=pool.DEAD_RUNNER_GRACE_SECONDS - 1)[0]
    assert waiting["eligible"] is False
    assert "controlled reap window has 1 seconds remaining" in waiting["reason"]
    assert waiting["reclaimable_in_seconds"] == 1

    reclaimed = pool.reap(apply=True, now=pool.DEAD_RUNNER_GRACE_SECONDS + 1)[0]
    assert reclaimed["eligible"] is True
    assert reclaimed["released"] is True
    assert reclaimed["terminated"] is False
    assert pool.status()["leases"] == []


def test_reap_terminates_tracked_orphan_before_releasing(isolated, monkeypatch):
    lease = pool.reserve("shared", "a.example", "a", "write", now=0)
    with pool._locked_state() as state:
        state["leases"][lease["id"]].update({
            "child_pid": 123,
            "child_pgid": 123,
            "baseline_target_ids": ["keep-a"],
            "browser_identity": "browser-a",
        })
    monkeypatch.setattr(pool, "_child_alive", lambda current: True)
    terminated = []
    monkeypatch.setattr(
        pool, "_terminate_lease_child",
        lambda current: terminated.append(current["child_pid"]) or True,
    )
    monkeypatch.setattr(pool, "close_task_targets", lambda *args: {
        "closed": [], "remaining": [], "baseline_preserved": True,
        "browser_restarted": False,
    })

    result = pool.reap(apply=True, now=pool.DEAD_RUNNER_GRACE_SECONDS + 1)[0]
    assert terminated == [123]
    assert result["terminated"] is True
    assert result["released"] is True
    assert pool.status()["leases"] == []


def test_status_reports_runner_child_and_reclaim_timing(isolated):
    lease = pool.reserve("shared", "a.example", "a", "read", now=0)
    with pool._locked_state() as state:
        state["leases"][lease["id"]]["child_pid"] = 999_999
    current = pool.status()["leases"][0]
    assert current["runner_alive"] is False
    assert current["child_alive"] is False
    assert current["heartbeat_age_seconds"] >= 0
    assert current["reclaimable_in_seconds"] == 0


def test_run_child_records_process_group_and_exit_code(isolated):
    lease = pool.reserve("shared", "a.example", "a", "read")
    assert pool._run_child(
        lease,
        [sys.executable, "-c", "raise SystemExit(7)"],
        {},
    ) == 7
    recorded = pool._read_state()["leases"][lease["id"]]
    assert recorded["child_pid"] > 0
    if pool.os.name == "posix":
        assert recorded["child_pgid"] == recorded["child_pid"]


def test_terminate_process_stops_real_process_group():
    process = pool.subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=pool.os.name == "posix",
    )
    try:
        pool._terminate_process(process)
        assert process.returncode != 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_managed_shared_run_releases_lease_and_daemon(isolated, monkeypatch):
    lease = {
        "id": "a" * 32,
        "owner": "researchbot",
        "kind": "shared",
        "browser_name": PRIMARY["name"],
        "cdp_url": PRIMARY["cdp_url"],
        "profile_dir": None,
        "chrome_pid": None,
    }
    monkeypatch.setattr(pool, "reserve_wait", lambda *args, **kwargs: dict(lease))
    persist_lease(lease)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: True)
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-a")
    monkeypatch.setattr(pool, "list_page_targets", lambda url: {"keep-a"})
    monkeypatch.setattr(pool, "close_task_targets", lambda url, baseline, identity: {
        "closed": [], "remaining": [], "baseline_preserved": True,
        "browser_restarted": False,
    })
    calls = {}
    monkeypatch.setattr(pool, "_run_child", lambda lease, command, env, input_text=None: (
        calls.update(command=command, env=env, input_text=input_text) or 0
    ))
    stopped = []
    forgotten = []
    monkeypatch.setattr(pool, "_stop_daemon", stopped.append)
    monkeypatch.setattr(pool, "forget", forgotten.append)
    assert pool.run_managed("researchbot", "example.com", "default", "read", "print(1)") == 0
    assert calls["env"]["BH_AGENT_POOL_CHILD"] == "1"
    assert calls["env"]["BU_CDP_URL"] == PRIMARY["cdp_url"]
    assert calls["input_text"] == "print(1)"
    assert stopped == ["pool-" + "a" * 16]
    assert forgotten == ["a" * 32]


def test_sigterm_stops_child_and_releases_lease(isolated, monkeypatch):
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: True)
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-a")
    monkeypatch.setattr(pool, "list_page_targets", lambda url: set())
    monkeypatch.setattr(pool, "close_task_targets", lambda *args: {
        "closed": [], "remaining": [], "baseline_preserved": True,
        "browser_restarted": False,
    })
    monkeypatch.setattr(pool, "_stop_daemon", lambda name: None)
    timer = pool.threading.Timer(
        0.1,
        lambda: pool.os.kill(pool.os.getpid(), pool.signal.SIGTERM),
    )
    timer.start()
    try:
        result = pool.run_command_managed(
            "researchbot",
            "example.com",
            "default",
            "write",
            [sys.executable, "-c", "import time; time.sleep(60)"],
        )
    finally:
        timer.cancel()
    assert result == 128 + pool.signal.SIGTERM
    assert pool.status()["leases"] == []
    assert pool.status()["write_locks"] == {}


def test_unavailable_shared_browser_does_not_leave_a_lease(isolated, monkeypatch):
    monkeypatch.setattr(pool, "_stop_daemon", lambda name: None)
    with pytest.raises(pool.PoolError, match="unavailable"):
        pool.run_managed("researchbot", "example.com", "default", "read", "print(1)")
    assert pool.status()["leases"] == []


def test_managed_shared_run_records_baseline_and_cleans_new_targets(isolated, monkeypatch):
    lease = {
        "id": "c" * 32,
        "owner": "researchbot",
        "kind": "shared",
        "browser_name": PRIMARY["name"],
        "cdp_url": PRIMARY["cdp_url"],
        "profile_dir": None,
        "chrome_pid": None,
    }
    monkeypatch.setattr(pool, "reserve_wait", lambda *args, **kwargs: dict(lease))
    persist_lease(lease)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: True)
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-a")
    baselines = []
    monkeypatch.setattr(pool, "list_page_targets", lambda url: {"keep-a", "keep-b"})
    monkeypatch.setattr(pool, "close_task_targets", lambda url, baseline, identity: baselines.append((list(baseline), identity)) or {
        "closed": ["new-c"], "remaining": [], "baseline_preserved": True,
        "browser_restarted": False,
    })
    monkeypatch.setattr(pool, "_run_child", lambda *args, **kwargs: 0)
    monkeypatch.setattr(pool, "_stop_daemon", lambda name: None)
    monkeypatch.setattr(pool, "forget", lambda lease_id: None)
    assert pool.run_managed("researchbot", "example.com", "default", "read", "print(1)") == 0
    assert baselines == [(["keep-a", "keep-b"], "browser-a")]


def test_managed_shared_run_keeps_lease_when_target_cleanup_fails(isolated, monkeypatch):
    lease = {
        "id": "d" * 32,
        "owner": "researchbot",
        "kind": "shared",
        "browser_name": PRIMARY["name"],
        "cdp_url": PRIMARY["cdp_url"],
        "profile_dir": None,
        "chrome_pid": None,
    }
    monkeypatch.setattr(pool, "reserve_wait", lambda *args, **kwargs: dict(lease))
    persist_lease(lease)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: True)
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-a")
    monkeypatch.setattr(pool, "list_page_targets", lambda url: {"keep-a"})
    monkeypatch.setattr(pool, "close_task_targets", lambda *args: (_ for _ in ()).throw(pool.PoolError("cleanup failed")))
    monkeypatch.setattr(pool, "_run_child", lambda *args, **kwargs: 0)
    monkeypatch.setattr(pool, "_stop_daemon", lambda name: None)
    forgotten = []
    monkeypatch.setattr(pool, "forget", forgotten.append)
    assert pool.run_managed("researchbot", "example.com", "default", "read", "print(1)") == 1
    assert forgotten == []


def test_exec_passes_argv_without_shell_and_exports_pool_environment(isolated, monkeypatch):
    lease = {
        "id": "e" * 32,
        "owner": "researchbot",
        "kind": "shared",
        "browser_name": PRIMARY["name"],
        "cdp_url": PRIMARY["cdp_url"],
        "profile_dir": None,
        "chrome_pid": None,
    }
    monkeypatch.setattr(pool, "reserve_wait", lambda *args, **kwargs: dict(lease))
    persist_lease(lease)
    monkeypatch.setattr(pool, "_cdp_alive", lambda url: True)
    monkeypatch.setattr(pool, "browser_identity", lambda url: "browser-a")
    monkeypatch.setattr(pool, "list_page_targets", lambda url: set())
    monkeypatch.setattr(pool, "close_task_targets", lambda *args: {
        "closed": [], "remaining": [], "baseline_preserved": True,
        "browser_restarted": False,
    })
    calls = {}
    monkeypatch.setattr(pool, "_run_child", lambda lease, command, env, input_text=None: (
        calls.update(command=command, env=env, input_text=input_text) or 7
    ))
    monkeypatch.setattr(pool, "_stop_daemon", lambda name: None)
    monkeypatch.setattr(pool, "forget", lambda lease_id: None)
    assert pool.run_command_managed("researchbot", "example.com", "default", "read", ["printf", "hello world"]) == 7
    assert calls["command"] == ["printf", "hello world"]
    assert calls["env"]["BH_AGENT_POOL_CHILD"] == "1"
    assert calls["env"]["BH_AGENT_POOL_LEASE_ID"] == "e" * 32
    assert calls["env"]["BU_CDP_URL"] == PRIMARY["cdp_url"]
    assert calls["input_text"] is None


def test_exec_rejects_empty_command():
    with pytest.raises(pool.PoolError, match="command must be non-empty"):
        pool.run_command_managed("researchbot", "example.com", "default", "read", [])
