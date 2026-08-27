"""Serialized access to managed Chrome profiles."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse

from . import paths


LEASE_TTL_SECONDS = 30 * 60
HEARTBEAT_SECONDS = 60
# A dead runner is given two heartbeat intervals before its lease becomes
# reclaimable. This tolerates one missed heartbeat and scheduler jitter while
# releasing leases well before the normal 30-minute TTL after a caller timeout.
DEAD_RUNNER_GRACE_SECONDS = 2 * HEARTBEAT_SECONDS
WRITE_WAIT_SECONDS = 30 * 60
FLEET_SCRIPT = Path(os.environ.get(
    "BH_BROWSER_FLEET_SCRIPT",
    "~/.codex/skills/browser-fleet-manager/scripts/browser_fleet.py",
)).expanduser()
CDP_TIMEOUT_SECONDS = 2
TARGET_CLOSE_ATTEMPTS = 10
TARGET_CLOSE_DELAY_SECONDS = 0.1
PROCESS_TERMINATION_SECONDS = 5
FORCE_KILL_SIGNAL = getattr(signal, "SIGKILL", signal.SIGTERM)


class PoolError(RuntimeError):
    pass


def _now() -> float:
    return time.time()


def _pool_dir() -> Path:
    return paths.ensure_private_dir(paths.runtime_dir() / "agent-pool")


def _state_path() -> Path:
    return _pool_dir() / "state.json"


def _lock_path() -> Path:
    return _pool_dir() / "state.lock"


def _empty_state() -> dict:
    return {"version": 1, "leases": {}, "write_locks": {}}


def _read_state() -> dict:
    path = _state_path()
    if not path.exists():
        return _empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PoolError(f"agent-pool state is unreadable; treating managed browsers as busy: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise PoolError("agent-pool state has an unsupported shape; treating managed browsers as busy")
    if not isinstance(data.get("leases"), dict) or not isinstance(data.get("write_locks"), dict):
        raise PoolError("agent-pool state is incomplete; treating managed browsers as busy")
    resources = set()
    for lease_id, lease in data["leases"].items():
        if not isinstance(lease, dict) or lease.get("id") != lease_id or not lease.get("cdp_url"):
            raise PoolError("agent-pool lease identity is invalid; treating managed browsers as busy")
        resource = lease.get("resource_key") or _validate_cdp_url(lease["cdp_url"])
        if resource in resources:
            raise PoolError("agent-pool has duplicate browser leases; treating managed browsers as busy")
        resources.add(resource)
    if any(lease_id not in data["leases"] for lease_id in data["write_locks"].values()):
        raise PoolError("agent-pool has an orphaned write lock; treating managed browsers as busy")
    return data


def _write_state(state: dict) -> None:
    path = _state_path()
    tmp = path.with_suffix(f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


@contextlib.contextmanager
def _locked_state():
    lock = _lock_path()
    with lock.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        state = _read_state()
        try:
            yield state
        except BaseException:
            raise
        else:
            _write_state(state)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_key(resource_key: str, site: str, account: str) -> str:
    site = site.strip().lower()
    account = account.strip().lower()
    if not site or not account:
        raise PoolError("site and account must be non-empty")
    return f"{resource_key}\n{site}\n{account}"


def reserve(owner: str, site: str, account: str, mode: str, *, browser: dict | None = None,
            now: float | None = None) -> dict:
    if mode not in {"read", "write"}:
        raise PoolError("mode must be read or write")
    owner = owner.strip()
    if not owner:
        raise PoolError("owner must be non-empty")
    timestamp = _now() if now is None else now
    browser = browser or _resolve_browser(None)
    cdp_url = _validate_cdp_url(browser["cdp_url"])
    resource_key = cdp_url
    lease_id = uuid.uuid4().hex
    with _locked_state() as state:
        key = _write_key(resource_key, site, account)
        if mode == "write" and key in state["write_locks"]:
            raise PoolError("write resource is busy")
        for existing in state["leases"].values():
            existing_key = existing.get("resource_key")
            if not existing_key and existing.get("cdp_url"):
                existing_key = _validate_cdp_url(existing["cdp_url"])
            if not existing_key:
                raise PoolError("lease state has no browser resource; treating managed browsers as busy")
            if existing_key == resource_key:
                raise PoolError(f"managed browser is busy: {browser['name']}")
        lease = {
            "id": lease_id,
            "owner": owner,
            "site": site.strip().lower(),
            "account": account.strip().lower(),
            "mode": mode,
            "kind": "shared",
            "browser_name": browser["name"],
            "resource_key": resource_key,
            "created_at": timestamp,
            "heartbeat_at": timestamp,
            "runner_pid": os.getpid(),
            "child_tracking": True,
            "chrome_pid": None,
            "cdp_url": cdp_url,
            "profile_dir": None,
        }
        state["leases"][lease_id] = lease
        if mode == "write":
            state["write_locks"][key] = lease_id
        return dict(lease)


def reserve_wait(owner: str, site: str, account: str, mode: str,
                 timeout: float = WRITE_WAIT_SECONDS, browser_name: str | None = None) -> dict:
    if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
        raise PoolError("wait timeout must be a finite non-negative number")
    browser = _resolve_browser(browser_name)
    deadline = time.monotonic() + timeout
    while True:
        try:
            return reserve(owner, site, account, mode, browser=browser)
        except PoolError as exc:
            waiting_for_browser = "managed browser is busy" in str(exc)
            waiting_for_write = mode == "write" and "write resource is busy" in str(exc)
            if not (waiting_for_browser or waiting_for_write):
                raise
            if time.monotonic() >= deadline:
                raise PoolError(f"managed browser remained busy for {timeout:g} seconds: {browser['name']}") from exc
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))


def heartbeat(lease_id: str, *, now: float | None = None) -> dict:
    with _locked_state() as state:
        lease = state["leases"].get(lease_id)
        if not lease:
            raise PoolError(f"unknown lease {lease_id}")
        lease["heartbeat_at"] = _now() if now is None else now
        return dict(lease)


def _drop_lease(state: dict, lease_id: str) -> dict | None:
    lease = state["leases"].pop(lease_id, None)
    if not lease:
        return None
    for key, owner_id in list(state["write_locks"].items()):
        if owner_id == lease_id:
            state["write_locks"].pop(key, None)
    return lease


def forget(lease_id: str) -> dict | None:
    with _locked_state() as state:
        return _drop_lease(state, lease_id)


def _pid_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _child_alive(lease: dict) -> bool | None:
    pid = lease.get("child_pid")
    if not isinstance(pid, int) or pid <= 0:
        return None
    pgid = lease.get("child_pgid")
    if os.name == "posix" and isinstance(pgid, int) and pgid > 0:
        try:
            os.killpg(pgid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
    return _pid_alive(pid)


def _record_child(lease_id: str, pid: int) -> None:
    with _locked_state() as state:
        lease = state["leases"].get(lease_id)
        if not lease:
            raise PoolError(f"unknown lease {lease_id}")
        lease["child_pid"] = pid
        lease["child_pgid"] = pid if os.name == "posix" else None
        lease["child_started_at"] = _now()


def _lease_activity(lease: dict, timestamp: float) -> dict:
    heartbeat_age = max(0.0, timestamp - float(lease.get("heartbeat_at", timestamp)))
    runner_alive = _pid_alive(lease.get("runner_pid"))
    child_alive = _child_alive(lease)
    tracked_child = lease.get("child_tracking") is True or child_alive is not None
    grace = DEAD_RUNNER_GRACE_SECONDS if tracked_child else LEASE_TTL_SECONDS
    reclaimable_in = None if runner_alive else max(0.0, grace - heartbeat_age)
    return {
        "runner_alive": runner_alive,
        "runner_dead": not runner_alive,
        "child_alive": child_alive,
        "heartbeat_age_seconds": round(heartbeat_age, 3),
        "remaining_ttl_seconds": round(
            max(0.0, LEASE_TTL_SECONDS - heartbeat_age), 3
        ),
        "reclaimable_in_seconds": (
            None if reclaimable_in is None else round(reclaimable_in, 3)
        ),
        "reap_in_seconds": (
            None if reclaimable_in is None else round(reclaimable_in, 3)
        ),
    }


def _terminate_lease_child(lease: dict) -> bool:
    if _child_alive(lease) is not True:
        return False
    pid = lease["child_pid"]
    pgid = lease.get("child_pgid")

    def send(sig: int) -> None:
        if os.name == "posix" and isinstance(pgid, int) and pgid > 0:
            os.killpg(pgid, sig)
        else:
            os.kill(pid, sig)

    try:
        send(signal.SIGTERM)
    except ProcessLookupError:
        return False
    deadline = time.monotonic() + PROCESS_TERMINATION_SECONDS
    while _child_alive(lease) is True and time.monotonic() < deadline:
        time.sleep(0.05)
    if _child_alive(lease) is True:
        try:
            send(FORCE_KILL_SIGNAL)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + PROCESS_TERMINATION_SECONDS
        while _child_alive(lease) is True and time.monotonic() < deadline:
            time.sleep(0.05)
    if _child_alive(lease) is True:
        raise PoolError("orphaned child process group did not terminate")
    return True


def _terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    def send(sig: int) -> None:
        if os.name == "posix":
            os.killpg(process.pid, sig)
        elif sig == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()

    try:
        send(signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=PROCESS_TERMINATION_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        send(FORCE_KILL_SIGNAL)
        process.wait(timeout=PROCESS_TERMINATION_SECONDS)
    except (ProcessLookupError, subprocess.TimeoutExpired) as exc:
        raise PoolError("child process group did not terminate") from exc


def _cdp_alive(url: str | None, timeout: float = 0.3) -> bool:
    if not url:
        return False
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/json/version", timeout=timeout) as response:
            data = json.loads(response.read())
        return bool(data.get("webSocketDebuggerUrl"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _validate_cdp_url(cdp_url: str) -> str:
    parsed = urlparse(cdp_url or "")
    try:
        port = parsed.port
    except ValueError as exc:
        raise PoolError("CDP URL must include a valid port") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or not 1 <= (port or 0) <= 65535
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise PoolError("CDP URL must be an http loopback URL with a valid port")
    return cdp_url.rstrip("/")


def _resolve_browser(browser_name: str | None) -> dict:
    command = [sys.executable, str(FLEET_SCRIPT), "resolve"]
    if browser_name:
        command.extend(["--name", browser_name])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PoolError(f"browser fleet resolver failed: {exc}") from exc
    if result.returncode != 0:
        raise PoolError(f"browser fleet resolver rejected the request: {result.stderr.strip()}")
    try:
        browser = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PoolError("browser fleet resolver returned invalid JSON") from exc
    if (
        not isinstance(browser, dict)
        or not isinstance(browser.get("name"), str)
        or browser.get("status") != "running"
        or browser.get("health") != "ok"
    ):
        raise PoolError("browser fleet resolver returned an unhealthy browser")
    if browser_name and browser["name"] != browser_name:
        raise PoolError("browser fleet resolver returned the wrong browser")
    browser["cdp_url"] = _validate_cdp_url(browser.get("cdp_url", ""))
    return browser


def browser_name_for_cdp(cdp_url: str | None) -> str | None:
    if not cdp_url:
        return None
    parsed = urlparse(cdp_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise PoolError("explicit CDP URL has an invalid port") from exc
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not port:
        return None
    command = [sys.executable, str(FLEET_SCRIPT), "audit"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PoolError(f"browser fleet audit failed: {exc}") from exc
    if result.returncode != 0:
        raise PoolError(f"browser fleet audit rejected the request: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PoolError("browser fleet audit returned invalid JSON") from exc
    registered = data.get("registered") if isinstance(data, dict) else None
    if not isinstance(registered, list):
        raise PoolError("browser fleet audit returned no registered browser list")
    matches = [item for item in registered if isinstance(item, dict) and item.get("port") == port]
    if not matches:
        return None
    if len(matches) != 1:
        raise PoolError(f"browser fleet has multiple registrations for CDP port {port}")
    browser = matches[0]
    if (browser.get("status") != "running" or browser.get("health") != "ok"
            or browser.get("problems")):
        raise PoolError(f"registered browser on CDP port {port} is not healthy")
    name = browser.get("name")
    if not isinstance(name, str) or not name:
        raise PoolError(f"registered browser on CDP port {port} has no name")
    return name


def list_page_targets(cdp_url: str) -> set[str]:
    base_url = _validate_cdp_url(cdp_url)
    try:
        with urllib.request.urlopen(
            base_url + "/json/list", timeout=CDP_TIMEOUT_SECONDS
        ) as response:
            data = json.loads(response.read())
        if not isinstance(data, list):
            raise PoolError("CDP /json/list response must be a list")
        targets = set()
        for item in data:
            if not isinstance(item, dict):
                raise PoolError("CDP /json/list contains a non-object target")
            target_id = item.get("id")
            if item.get("type") == "page" and isinstance(target_id, str) and target_id:
                targets.add(target_id)
        return targets
    except PoolError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise PoolError(f"failed to list CDP page targets: {exc}") from exc


def browser_identity(cdp_url: str) -> str:
    base_url = _validate_cdp_url(cdp_url)
    try:
        with urllib.request.urlopen(
            base_url + "/json/version", timeout=CDP_TIMEOUT_SECONDS
        ) as response:
            data = json.loads(response.read())
        identity = data.get("webSocketDebuggerUrl") if isinstance(data, dict) else None
        if not isinstance(identity, str) or not identity:
            raise PoolError("CDP /json/version has no browser identity")
        return identity
    except PoolError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise PoolError(f"failed to read CDP browser identity: {exc}") from exc


def close_task_targets(
    cdp_url: str,
    baseline_target_ids: list[str],
    expected_browser_identity: str,
) -> dict:
    base_url = _validate_cdp_url(cdp_url)
    if any(not isinstance(target_id, str) or not target_id for target_id in baseline_target_ids):
        raise PoolError("baseline target IDs must be non-empty strings")
    if not expected_browser_identity:
        raise PoolError("expected browser identity must be non-empty")

    def restarted() -> bool:
        return browser_identity(base_url) != expected_browser_identity

    if restarted():
        return {
            "closed": [],
            "remaining": [],
            "baseline_preserved": True,
            "browser_restarted": True,
        }
    baseline = set(baseline_target_ids)
    current = list_page_targets(base_url)
    candidates = sorted(current - baseline)
    closed = []
    for target_id in candidates:
        if restarted():
            return {
                "closed": closed,
                "remaining": [],
                "baseline_preserved": True,
                "browser_restarted": True,
            }
        close_url = f"{base_url}/json/close/{quote(target_id, safe='')}"
        try:
            with urllib.request.urlopen(close_url, timeout=CDP_TIMEOUT_SECONDS) as response:
                response.read()
        except (OSError, TypeError, ValueError) as exc:
            raise PoolError(f"failed to close CDP target {target_id}: {exc}") from exc
        closed.append(target_id)

    remaining = sorted(candidates)
    for attempt in range(TARGET_CLOSE_ATTEMPTS):
        if restarted():
            return {
                "closed": closed,
                "remaining": [],
                "baseline_preserved": True,
                "browser_restarted": True,
            }
        current = list_page_targets(base_url)
        remaining = sorted(current - baseline)
        if not remaining:
            return {
                "closed": closed,
                "remaining": remaining,
                "baseline_preserved": True,
                "browser_restarted": False,
            }
        if attempt + 1 < TARGET_CLOSE_ATTEMPTS:
            time.sleep(TARGET_CLOSE_DELAY_SECONDS)
    raise PoolError(f"CDP task targets remain after cleanup: {remaining}")


def reap(*, apply: bool = False, now: float | None = None) -> list[dict]:
    timestamp = _now() if now is None else now
    results = []
    with _locked_state() as state:
        for lease_id, lease in list(state["leases"].items()):
            activity = _lease_activity(lease, timestamp)
            tracked_child = (
                lease.get("child_tracking") is True
                or activity["child_alive"] is not None
            )
            grace = DEAD_RUNNER_GRACE_SECONDS if tracked_child else LEASE_TTL_SECONDS
            eligible = activity["runner_dead"] and activity["heartbeat_age_seconds"] > grace
            if eligible and activity["child_alive"]:
                reason = "orphaned shared lease; child process group will be terminated"
            elif eligible and (
                "baseline_target_ids" not in lease or "browser_identity" not in lease
            ):
                reason = "legacy stale shared lease; no target cleanup evidence"
            elif eligible:
                reason = "dead runner grace elapsed"
            elif activity["runner_alive"]:
                reason = "shared lease is active"
            else:
                remaining = activity["reap_in_seconds"] or 0.0
                reason = (
                    "runner PID is dead; controlled reap window has "
                    f"{remaining:g} seconds remaining"
                )
            item = {
                "lease_id": lease_id,
                "eligible": eligible,
                "reason": reason,
                "deleted": False,
                "released": False,
                "terminated": False,
                **activity,
            }
            if apply and eligible:
                try:
                    item["terminated"] = _terminate_lease_child(lease)
                except PoolError as exc:
                    item["reason"] = f"orphaned child cleanup failed: {exc}"
                    results.append(item)
                    continue
                if (
                    "baseline_target_ids" in lease
                    and "browser_identity" in lease
                ):
                    try:
                        close_task_targets(
                            lease["cdp_url"],
                            lease["baseline_target_ids"],
                            lease["browser_identity"],
                        )
                    except PoolError as exc:
                        item["reason"] = f"stale shared target cleanup failed: {exc}"
                        results.append(item)
                        continue
                _drop_lease(state, lease_id)
                item["released"] = True
            results.append(item)
    return results


def _heartbeat_loop(lease_id: str, stop: threading.Event) -> None:
    while not stop.wait(HEARTBEAT_SECONDS):
        try:
            heartbeat(lease_id)
        except PoolError:
            return


def _stop_daemon(name: str) -> None:
    from .admin import restart_daemon
    restart_daemon(name)


def _record_shared_baseline(lease: dict) -> None:
    identity = browser_identity(lease["cdp_url"])
    baseline = sorted(list_page_targets(lease["cdp_url"]))
    if browser_identity(lease["cdp_url"]) != identity:
        raise PoolError("shared browser restarted while target baseline was recorded")
    lease["browser_identity"] = identity
    lease["baseline_target_ids"] = baseline
    with _locked_state() as state:
        current = state["leases"].get(lease["id"])
        if not current:
            raise PoolError("lease disappeared before shared target baseline was recorded")
        current.update(lease)


def _cleanup_managed_lease(lease: dict, daemon_name: str) -> list[str]:
    errors = []
    if _child_alive(lease) is True:
        return ["child process group is still active; lease retained"]
    try:
        _stop_daemon(daemon_name)
    except Exception as exc:
        errors.append(f"daemon cleanup failed: {exc}")

    if "baseline_target_ids" in lease and "browser_identity" in lease:
        try:
            close_task_targets(
                lease["cdp_url"],
                lease["baseline_target_ids"],
                lease["browser_identity"],
            )
        except PoolError as exc:
            errors.append(f"shared target cleanup failed: {exc}")

    if not errors:
        try:
            forget(lease["id"])
        except Exception as exc:
            errors.append(f"lease release failed: {exc}")
    return errors


class _TerminationRequested(BaseException):
    def __init__(self, signum: int):
        self.signum = signum


@contextlib.contextmanager
def _termination_handlers():
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = {}

    def interrupt(signum, _frame):
        raise _TerminationRequested(signum)

    for signum in (signal.SIGTERM, getattr(signal, "SIGHUP", None)):
        if signum is not None:
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, interrupt)
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def _run_child(lease: dict, command: list[str], env: dict, input_text: str | None = None) -> int:
    process = subprocess.Popen(
        command,
        env=env,
        stdin=subprocess.PIPE if input_text is not None else None,
        text=input_text is not None,
        start_new_session=os.name == "posix",
    )
    child = {
        "child_pid": process.pid,
        "child_pgid": process.pid if os.name == "posix" else None,
        "child_started_at": _now(),
    }
    lease.update(child)
    try:
        _record_child(lease["id"], process.pid)
        if input_text is None:
            return process.wait()
        process.communicate(input_text)
        return process.returncode
    except BaseException:
        _terminate_process(process)
        raise


def _run_with_lease(owner: str, site: str, account: str, mode: str, child_runner,
                    browser_name: str | None = None,
                    wait_timeout: float = WRITE_WAIT_SECONDS) -> int:
    lease = reserve_wait(
        owner,
        site,
        account,
        mode,
        timeout=wait_timeout,
        browser_name=browser_name,
    )
    stop = threading.Event()
    thread = None
    daemon_name = f"pool-{lease['id'][:16]}"
    child_returncode = None
    cleanup_errors = []
    try:
        with _termination_handlers():
            try:
                if not _cdp_alive(lease["cdp_url"]):
                    raise PoolError(f"managed browser is unavailable: {lease['browser_name']}")
                _record_shared_baseline(lease)
                env = {
                    **os.environ,
                    "BU_NAME": daemon_name,
                    "BU_CDP_URL": lease["cdp_url"],
                    "BH_AGENT_POOL_CHILD": "1",
                    "BH_AGENT_POOL_LEASE_ID": lease["id"],
                }
                thread = threading.Thread(
                    target=_heartbeat_loop, args=(lease["id"], stop), daemon=True
                )
                thread.start()
                child_returncode = child_runner(lease, env)
            except _TerminationRequested as exc:
                child_returncode = 128 + exc.signum
    finally:
        stop.set()
        if thread:
            thread.join(timeout=2)
        cleanup_errors = _cleanup_managed_lease(lease, daemon_name)
    if cleanup_errors:
        print("browser-harness agent-pool: " + "; ".join(cleanup_errors), file=sys.stderr)
        return child_returncode if child_returncode not in (None, 0) else 1
    return child_returncode if child_returncode is not None else 0


def run_managed(owner: str, site: str, account: str, mode: str, code: str,
                browser_name: str | None = None,
                wait_timeout: float = WRITE_WAIT_SECONDS) -> int:
    if not code.strip():
        raise PoolError("agent-pool run requires a Browser Harness script on stdin")
    return _run_with_lease(
        owner,
        site,
        account,
        mode,
        lambda lease, env: _run_child(
            lease,
            [sys.executable, "-m", "browser_harness.run"],
            env,
            code,
        ),
        browser_name,
        wait_timeout=wait_timeout,
    )


def run_command_managed(owner: str, site: str, account: str, mode: str, command: list[str],
                        browser_name: str | None = None,
                        wait_timeout: float = WRITE_WAIT_SECONDS) -> int:
    if not command:
        raise PoolError("command must be non-empty")
    if (
        len(command) >= 3
        and Path(command[0]).name == "browser-harness"
        and command[1:3] == ["agent-pool", "exec"]
    ):
        raise PoolError("agent-pool exec cannot wrap itself")
    return _run_with_lease(
        owner,
        site,
        account,
        mode,
        lambda lease, env: _run_child(lease, command, env),
        browser_name,
        wait_timeout=wait_timeout,
    )


def status(browser_name: str | None = None) -> dict:
    try:
        state = _read_state()
        error = None
    except PoolError as exc:
        state = _empty_state()
        error = str(exc)
    try:
        browser = _resolve_browser(browser_name)
        browser_error = None
    except PoolError as exc:
        browser = None
        browser_error = str(exc)
    return {
        "selected_browser": browser,
        "selected_browser_alive": _cdp_alive(browser["cdp_url"]) if browser else False,
        "browser_error": browser_error,
        "mode": "per-browser",
        "state_error": error,
        "leases": [
            {**lease, **_lease_activity(lease, _now())}
            for lease in state["leases"].values()
        ],
        "write_locks": state["write_locks"],
    }


def _default_owner() -> str:
    explicit = os.environ.get("HERMES_PROFILE_NAME") or os.environ.get("HERMES_PROFILE")
    if explicit and explicit.strip():
        return explicit.strip()
    home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser().resolve()
    if home.parent.name == "profiles":
        return home.name
    return "default"


def should_manage_legacy() -> bool:
    if os.environ.get("BH_AGENT_POOL_CHILD") == "1":
        return False
    if os.environ.get("HERMES_HOME") or os.environ.get("HERMES_PROFILE_NAME") or os.environ.get("HERMES_PROFILE"):
        return True
    return os.environ.get("BU_NAME") == "agent"


def infer_site(code: str) -> str:
    for raw in re.findall(r"https?://[^\s\"')]+", code):
        host = urlparse(raw).hostname
        if host:
            return host.lower()
    return "unknown"


def run_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="browser-harness agent-pool")
    sub = parser.add_subparsers(dest="command", required=True)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--browser")
    run = sub.add_parser("run")
    run.add_argument("--owner", default=_default_owner())
    run.add_argument("--site", required=True)
    run.add_argument("--account", default="default")
    run.add_argument("--mode", choices=("read", "write"), default="read")
    run.add_argument("--browser")
    run.add_argument("--wait-timeout", type=float, default=WRITE_WAIT_SECONDS,
                     help="maximum seconds to wait for a lease (default: 1800)")
    exec_parser = sub.add_parser("exec")
    exec_parser.add_argument("--owner", default=_default_owner())
    exec_parser.add_argument("--site", required=True)
    exec_parser.add_argument("--account", default="default")
    exec_parser.add_argument("--mode", choices=("read", "write"), default="read")
    exec_parser.add_argument("--browser")
    exec_parser.add_argument("--wait-timeout", type=float, default=WRITE_WAIT_SECONDS,
                             help="maximum seconds to wait for a lease (default: 1800)")
    exec_parser.add_argument("command_argv", nargs=argparse.REMAINDER)
    reap_parser = sub.add_parser("reap")
    reap_parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            print(json.dumps(status(args.browser), ensure_ascii=False, indent=2))
            return 0
        if args.command == "reap":
            print(json.dumps(reap(apply=args.apply), ensure_ascii=False, indent=2))
            return 0
        if args.command == "exec":
            command = list(args.command_argv)
            if command and command[0] == "--":
                command = command[1:]
            if not command:
                raise PoolError("agent-pool exec requires a command after --")
            return run_command_managed(
                args.owner, args.site, args.account, args.mode, command, args.browser,
                wait_timeout=args.wait_timeout,
            )
        code = sys.stdin.read()
        if not code.strip():
            raise PoolError("agent-pool run requires a Browser Harness script on stdin")
        return run_managed(
            args.owner, args.site, args.account, args.mode, code, args.browser,
            wait_timeout=args.wait_timeout,
        )
    except PoolError as exc:
        print(f"browser-harness agent-pool: {exc}", file=sys.stderr)
        return 1
