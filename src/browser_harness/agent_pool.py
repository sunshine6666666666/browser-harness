"""Managed access to the dedicated Agent Chrome and disposable profile clones."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

from . import paths


LEASE_TTL_SECONDS = 30 * 60
HEARTBEAT_SECONDS = 60
WRITE_WAIT_SECONDS = 30 * 60
SHARED_CDP_URL = os.environ.get("BH_AGENT_POOL_SHARED_CDP_URL", "http://127.0.0.1:9223")
ALLOWED_SOURCE_PROFILE = Path(
    "/Users/yelin/Developer/agent-tools/chrome-profiles/hermes-agent"
).resolve()
SOURCE_PROFILE = Path(os.environ.get(
    "BH_AGENT_POOL_SOURCE_PROFILE",
    str(ALLOWED_SOURCE_PROFILE),
)).expanduser().resolve()
TEMPLATE_ROOT = Path(os.environ.get(
    "BH_AGENT_POOL_TEMPLATE_ROOT",
    "/Users/yelin/Developer/agent-tools/chrome-profiles/.agent-pool-template",
)).expanduser().resolve()
TEMP_ROOT = Path(os.environ.get(
    "BH_AGENT_POOL_TEMP_ROOT",
    "/Users/yelin/Developer/agent-tools/chrome-profiles/.agent-pool-tmp",
)).expanduser().resolve()
CHROME_BINARY = Path(os.environ.get(
    "BH_AGENT_POOL_CHROME_BINARY",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)).expanduser().resolve()
MANIFEST = ".browser-harness-agent-pool.json"
MARKER = "browser-harness-agent-pool-v1"


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
        raise PoolError(f"agent-pool state is unreadable; treating shared Chrome as busy: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise PoolError("agent-pool state has an unsupported shape; treating shared Chrome as busy")
    if not isinstance(data.get("leases"), dict) or not isinstance(data.get("write_locks"), dict):
        raise PoolError("agent-pool state is incomplete; treating shared Chrome as busy")
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


def _write_key(site: str, account: str) -> str:
    site = site.strip().lower()
    account = account.strip().lower()
    if not site or not account:
        raise PoolError("site and account must be non-empty")
    return f"{site}\n{account}"


def reserve(owner: str, site: str, account: str, mode: str, *, now: float | None = None) -> dict:
    if mode not in {"read", "write"}:
        raise PoolError("mode must be read or write")
    owner = owner.strip()
    if not owner:
        raise PoolError("owner must be non-empty")
    timestamp = _now() if now is None else now
    lease_id = uuid.uuid4().hex
    with _locked_state() as state:
        key = _write_key(site, account)
        if mode == "write" and key in state["write_locks"]:
            raise PoolError("write resource is busy")
        shared_busy = any(item.get("kind") == "shared" for item in state["leases"].values())
        kind = "temporary" if shared_busy else "shared"
        lease = {
            "id": lease_id,
            "owner": owner,
            "site": site.strip().lower(),
            "account": account.strip().lower(),
            "mode": mode,
            "kind": kind,
            "created_at": timestamp,
            "heartbeat_at": timestamp,
            "runner_pid": os.getpid(),
            "chrome_pid": None,
            "cdp_url": SHARED_CDP_URL if kind == "shared" else None,
            "profile_dir": None,
        }
        state["leases"][lease_id] = lease
        if mode == "write":
            state["write_locks"][key] = lease_id
        return dict(lease)


def reserve_wait(owner: str, site: str, account: str, mode: str, timeout: float = WRITE_WAIT_SECONDS) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        try:
            return reserve(owner, site, account, mode)
        except PoolError as exc:
            if mode != "write" or "write resource is busy" not in str(exc):
                raise
            if time.monotonic() >= deadline:
                raise PoolError(f"write resource remained busy for {timeout:g} seconds") from exc
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


def _process_command(pid: int | None) -> str:
    if not isinstance(pid, int) or pid <= 0:
        return ""
    try:
        return subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "command="],
            text=True,
            errors="replace",
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _profile_in_use(profile: Path) -> bool:
    if (profile / "SingletonLock").exists() or (profile / "SingletonLock").is_symlink():
        return True
    try:
        listing = subprocess.check_output(["ps", "-axo", "command="], text=True, errors="replace")
    except (OSError, subprocess.CalledProcessError):
        return True
    return f"--user-data-dir={profile.resolve()}" in listing


def _owned_chrome_identity(lease: dict) -> bool:
    profile = lease.get("profile_dir")
    command = _process_command(lease.get("chrome_pid"))
    if not profile or not command:
        return False
    path = Path(profile)
    try:
        manifest = _manifest(path)
    except PoolError:
        return False
    return bool(
        _is_within(path, TEMP_ROOT)
        and manifest.get("task_id") == lease.get("id")
        and command.startswith(str(CHROME_BINARY))
        and f"--user-data-dir={path.resolve()}" in command
    )


def _terminate_pid(pid: int) -> None:
    os.kill(pid, signal.SIGKILL)


def _cdp_alive(url: str | None, timeout: float = 0.3) -> bool:
    if not url:
        return False
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/json/version", timeout=timeout) as response:
            data = json.loads(response.read())
        return bool(data.get("webSocketDebuggerUrl"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _manifest(profile_dir: Path) -> dict:
    try:
        data = json.loads((profile_dir / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PoolError(f"missing or invalid managed manifest: {exc}") from exc
    if data.get("marker") != MARKER:
        raise PoolError("managed manifest marker mismatch")
    return data


def cleanup_eligibility(lease: dict, *, now: float | None = None, temp_root: Path | None = None) -> tuple[bool, str]:
    timestamp = _now() if now is None else now
    root = (temp_root or TEMP_ROOT).resolve()
    if lease.get("kind") != "temporary":
        return False, "not a temporary lease"
    raw = lease.get("profile_dir")
    if not raw:
        return False, "temporary profile path missing"
    profile = Path(raw)
    if not _is_within(profile, root) or profile.resolve() == root:
        return False, "profile path is outside managed temporary root"
    try:
        manifest = _manifest(profile)
    except PoolError as exc:
        return False, str(exc)
    if manifest.get("task_id") != lease.get("id") or profile.name != lease.get("id"):
        return False, "task identity mismatch"
    if timestamp - float(lease.get("heartbeat_at", timestamp)) <= LEASE_TTL_SECONDS:
        return False, "heartbeat has not expired"
    if _pid_alive(lease.get("runner_pid")):
        return False, "runner process is alive"
    if _pid_alive(lease.get("chrome_pid")):
        return False, "Chrome process is alive"
    if _cdp_alive(lease.get("cdp_url")):
        return False, "Chrome CDP endpoint is alive"
    if _profile_in_use(profile):
        return False, "Chrome profile is still in use"
    return True, "eligible"


def _safe_rmtree(profile_dir: Path, lease: dict, *, temp_root: Path | None = None) -> None:
    # Normal completion owns the profile, so liveness/TTL are checked by caller. Path and marker
    # remain mandatory here and are revalidated without relying on the clock.
    root = (temp_root or TEMP_ROOT).resolve()
    manifest = _manifest(profile_dir)
    if not _is_within(profile_dir, root) or profile_dir.resolve() == root:
        raise PoolError("refusing to remove path outside managed temporary root")
    if profile_dir.name != lease.get("id") or manifest.get("task_id") != lease.get("id"):
        raise PoolError("refusing to remove profile with mismatched task identity")
    if (
        _pid_alive(lease.get("chrome_pid"))
        or _cdp_alive(lease.get("cdp_url"))
        or _profile_in_use(profile_dir)
    ):
        raise PoolError("refusing to remove a profile still used by Chrome")
    shutil.rmtree(profile_dir)


def reap(*, apply: bool = False, now: float | None = None, temp_root: Path | None = None) -> list[dict]:
    timestamp = _now() if now is None else now
    results = []
    with _locked_state() as state:
        for lease_id, lease in list(state["leases"].items()):
            if lease.get("kind") == "temporary" and lease.get("profile_dir"):
                _refresh_owned_pid(lease)
            expired = timestamp - float(lease.get("heartbeat_at", timestamp)) > LEASE_TTL_SECONDS
            runner_dead = not _pid_alive(lease.get("runner_pid"))
            if lease.get("kind") == "shared":
                ok = expired and runner_dead
                reason = "stale shared lease" if ok else "shared lease is active"
            elif not lease.get("profile_dir"):
                ok = expired and runner_dead
                reason = "stale pending lease" if ok else "pending lease is active"
            else:
                ok, reason = cleanup_eligibility(lease, now=timestamp, temp_root=temp_root)
            item = {
                "lease_id": lease_id,
                "eligible": ok,
                "reason": reason,
                "deleted": False,
                "released": False,
                "terminated": False,
            }
            if (
                apply
                and lease.get("kind") == "temporary"
                and expired
                and runner_dead
                and _pid_alive(lease.get("chrome_pid"))
                and _owned_chrome_identity(lease)
            ):
                _terminate_pid(lease["chrome_pid"])
                item["terminated"] = True
                item["reason"] = "terminated stale owned Chrome; deletion deferred"
                results.append(item)
                continue
            if apply and ok:
                if lease.get("profile_dir"):
                    profile = Path(lease["profile_dir"])
                    _safe_rmtree(profile, lease, temp_root=temp_root)
                    item["deleted"] = True
                _drop_lease(state, lease_id)
                item["released"] = True
            results.append(item)
    return results


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _remove_chrome_runtime_files(profile: Path) -> None:
    for name in ("SingletonCookie", "SingletonLock", "SingletonSocket", "DevToolsActivePort"):
        path = profile / name
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)


def _copy_clone(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["cp", "-cR", str(source), str(target)], capture_output=True, text=True)
    if result.returncode != 0:
        raise PoolError(f"profile clone failed: {result.stderr.strip()}")


def _find_chrome_pid(profile: Path, cdp_url: str) -> int | None:
    port = urlparse(cdp_url).port
    try:
        listing = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True, errors="replace")
    except (OSError, subprocess.CalledProcessError):
        return None
    profile_arg = f"--user-data-dir={profile.resolve()}"
    port_arg = f"--remote-debugging-port={port}"
    for line in listing.splitlines():
        raw_pid, _, command = line.strip().partition(" ")
        if command.startswith(str(CHROME_BINARY)) and profile_arg in command and port_arg in command:
            return int(raw_pid)
    return None


def _refresh_owned_pid(lease: dict) -> int | None:
    if lease.get("kind") != "temporary" or not lease.get("profile_dir") or not lease.get("cdp_url"):
        return None
    pid = _find_chrome_pid(Path(lease["profile_dir"]), lease["cdp_url"])
    if pid:
        lease["chrome_pid"] = pid
    return pid


def _start_temporary(lease: dict) -> tuple[subprocess.Popen, dict]:
    current = TEMPLATE_ROOT / "current"
    if not current.is_dir():
        raise PoolError(f"login template is unavailable: {current}")
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    staging = TEMP_ROOT / f".staging-{lease['id']}"
    profile = TEMP_ROOT / lease["id"]
    if staging.exists() or profile.exists():
        raise PoolError(f"managed task path already exists for {lease['id']}")
    process = None
    try:
        _copy_clone(current, staging)
        _remove_chrome_runtime_files(staging)
        (staging / MANIFEST).write_text(json.dumps({
            "marker": MARKER,
            "task_id": lease["id"],
            "created_at": _now(),
        }, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, profile)
        port = _free_port()
        cdp_url = f"http://127.0.0.1:{port}"
        lease.update({"cdp_url": cdp_url, "profile_dir": str(profile)})
        with _locked_state() as state:
            if lease["id"] not in state["leases"]:
                raise PoolError("lease disappeared while temporary profile was starting")
            state["leases"][lease["id"]].update(lease)
        process = subprocess.Popen([
            str(CHROME_BINARY),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--disable-background-mode",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
            "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        lease["chrome_pid"] = process.pid
        with _locked_state() as state:
            if lease["id"] not in state["leases"]:
                process.terminate()
                raise PoolError("lease disappeared while temporary Chrome was starting")
            state["leases"][lease["id"]].update(lease)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise PoolError(f"temporary Chrome exited with {process.returncode}")
            if _cdp_alive(cdp_url):
                break
            time.sleep(0.2)
        else:
            process.terminate()
            raise PoolError("temporary Chrome did not expose CDP within 20 seconds")
        actual_pid = _find_chrome_pid(profile, cdp_url)
        if not actual_pid:
            raise PoolError("temporary Chrome PID could not be verified")
        lease["chrome_pid"] = actual_pid
        with _locked_state() as state:
            if lease["id"] not in state["leases"]:
                raise PoolError("lease disappeared after temporary Chrome started")
            state["leases"][lease["id"]].update(lease)
        return process, lease
    except BaseException:
        if process and process.poll() is None:
            process.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=10)
        if staging.exists() and _is_within(staging, TEMP_ROOT):
            shutil.rmtree(staging)
        if profile.exists() and not _pid_alive(lease.get("chrome_pid")) and not _cdp_alive(lease.get("cdp_url")):
            with contextlib.suppress(PoolError):
                _safe_rmtree(profile, lease)
        raise


def _stop_owned_chrome(lease: dict, process: subprocess.Popen | None) -> None:
    if lease.get("kind") != "temporary":
        return
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        pid = _refresh_owned_pid(lease)
        if not pid:
            if not _cdp_alive(lease.get("cdp_url")):
                return
            time.sleep(0.2)
            continue
        with _locked_state() as state:
            if lease["id"] in state["leases"]:
                state["leases"][lease["id"]].update(lease)
        if not _owned_chrome_identity(lease):
            return
        os.kill(pid, signal.SIGTERM)
        grace = time.monotonic() + 2
        while time.monotonic() < grace and _pid_alive(pid):
            time.sleep(0.1)
        if _pid_alive(pid) and _owned_chrome_identity(lease):
            os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)


def _heartbeat_loop(lease_id: str, stop: threading.Event) -> None:
    while not stop.wait(HEARTBEAT_SECONDS):
        try:
            heartbeat(lease_id)
        except PoolError:
            return


def _stop_daemon(name: str) -> None:
    from .admin import restart_daemon
    restart_daemon(name)


def run_managed(owner: str, site: str, account: str, mode: str, code: str) -> int:
    lease = reserve_wait(owner, site, account, mode)
    chrome_process = None
    stop = threading.Event()
    thread = None
    daemon_name = f"pool-{lease['id'][:16]}"
    try:
        if lease["kind"] == "temporary":
            chrome_process, lease = _start_temporary(lease)
        elif not _cdp_alive(lease["cdp_url"]):
            raise PoolError("shared Agent Chrome is unavailable")
        env = {
            **os.environ,
            "BU_NAME": daemon_name,
            "BU_CDP_URL": lease["cdp_url"],
            "BH_AGENT_POOL_CHILD": "1",
        }
        thread = threading.Thread(target=_heartbeat_loop, args=(lease["id"], stop), daemon=True)
        thread.start()
        child = subprocess.run([sys.executable, "-m", "browser_harness.run"], input=code, text=True, env=env)
        return child.returncode
    finally:
        stop.set()
        if thread:
            thread.join(timeout=2)
        try:
            _stop_daemon(daemon_name)
        except BaseException:
            pass
        _stop_owned_chrome(lease, chrome_process)
        cleanup_complete = not lease.get("profile_dir")
        if lease.get("kind") == "temporary" and lease.get("profile_dir"):
            profile = Path(lease["profile_dir"])
            if not _pid_alive(lease.get("chrome_pid")) and not _cdp_alive(lease.get("cdp_url")):
                with contextlib.suppress(PoolError):
                    _safe_rmtree(profile, lease)
            cleanup_complete = not profile.exists()
        if lease.get("kind") == "shared" or cleanup_complete:
            forget(lease["id"])


def _source_in_use(source: Path) -> bool:
    try:
        listing = subprocess.check_output(["ps", "-axo", "command="], text=True, errors="replace")
    except (OSError, subprocess.CalledProcessError):
        return True
    needle = f"--user-data-dir={source.resolve()}"
    return any("Google Chrome" in command and needle in command for command in listing.splitlines())


def snapshot() -> dict:
    if SOURCE_PROFILE != ALLOWED_SOURCE_PROFILE:
        raise PoolError("source profile is not the dedicated Agent Chrome allowlist path")
    if _cdp_alive(SHARED_CDP_URL) or _source_in_use(SOURCE_PROFILE):
        raise PoolError("Agent Chrome must be fully closed before snapshot")
    if not (SOURCE_PROFILE / "Local State").is_file():
        raise PoolError("Agent Chrome source profile is incomplete")
    TEMPLATE_ROOT.mkdir(parents=True, exist_ok=True)
    staging = TEMPLATE_ROOT / f".staging-{uuid.uuid4().hex}"
    current = TEMPLATE_ROOT / "current"
    previous = TEMPLATE_ROOT / "previous"
    _copy_clone(SOURCE_PROFILE, staging)
    _remove_chrome_runtime_files(staging)
    if not (staging / "Local State").is_file():
        shutil.rmtree(staging)
        raise PoolError("snapshot validation failed")
    if previous.exists():
        if not _is_within(previous, TEMPLATE_ROOT):
            raise PoolError("previous template escaped template root")
        shutil.rmtree(previous)
    if current.exists():
        os.replace(current, previous)
    os.replace(staging, current)
    return {"source": str(SOURCE_PROFILE), "current": str(current), "previous": str(previous) if previous.exists() else None}


def status() -> dict:
    try:
        state = _read_state()
        error = None
    except PoolError as exc:
        state = _empty_state()
        error = str(exc)
    return {
        "shared_cdp_url": SHARED_CDP_URL,
        "shared_cdp_alive": _cdp_alive(SHARED_CDP_URL),
        "source_profile": str(SOURCE_PROFILE),
        "template_ready": (TEMPLATE_ROOT / "current").is_dir(),
        "temporary_root": str(TEMP_ROOT),
        "state_error": error,
        "leases": list(state["leases"].values()),
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
    return (
        os.environ.get("BU_NAME") == "agent"
        or os.environ.get("BU_CDP_URL", "").rstrip("/") == SHARED_CDP_URL.rstrip("/")
    )


def infer_site(code: str) -> str:
    for raw in re.findall(r"https?://[^\s\"')]+", code):
        host = urlparse(raw).hostname
        if host:
            return host.lower()
    return "unknown"


def run_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="browser-harness agent-pool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    run = sub.add_parser("run")
    run.add_argument("--owner", default=_default_owner())
    run.add_argument("--site", required=True)
    run.add_argument("--account", default="default")
    run.add_argument("--mode", choices=("read", "write"), default="read")
    sub.add_parser("snapshot")
    reap_parser = sub.add_parser("reap")
    reap_parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            print(json.dumps(status(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "snapshot":
            print(json.dumps(snapshot(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "reap":
            print(json.dumps(reap(apply=args.apply), ensure_ascii=False, indent=2))
            return 0
        code = sys.stdin.read()
        if not code.strip():
            raise PoolError("agent-pool run requires a Browser Harness script on stdin")
        return run_managed(args.owner, args.site, args.account, args.mode, code)
    except PoolError as exc:
        print(f"browser-harness agent-pool: {exc}", file=sys.stderr)
        return 1
