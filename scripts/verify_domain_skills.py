#!/usr/bin/env python3
"""Validate Browser Harness domain-skill registry and runtime wiring."""
from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "agent-workspace" / "domain-skills"
REGISTRY = ROOT / "registry.json"
DEFAULT_LINK = Path.home() / ".config" / "browser-harness" / "agent-workspace" / "domain-skills"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-workspace", type=Path,
                        help="Explicit BH_AGENT_WORKSPACE used by the checkout launcher")
    args = parser.parse_args()
    errors: list[str] = []
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL registry unreadable: {exc}")
        return 1

    skills = data.get("skills")
    if data.get("version") != 1 or not isinstance(skills, dict):
        errors.append("registry requires version=1 and a skills object")
        skills = {}

    written = {
        path.name
        for path in ROOT.iterdir()
        if path.is_dir() and any(path.rglob("*.md"))
    }
    registered = set(skills)
    if missing := sorted(written - registered):
        errors.append(f"unregistered skill directories: {missing}")
    if stale := sorted(registered - written):
        errors.append(f"registry entries without Markdown: {stale}")

    for skill, patterns in skills.items():
        if not isinstance(patterns, list) or not patterns:
            errors.append(f"{skill}: host pattern list is empty")
            continue
        for pattern in patterns:
            if not isinstance(pattern, str) or "." not in pattern or "/" in pattern:
                errors.append(f"{skill}: invalid host pattern {pattern!r}")

    runtime_root = args.runtime_workspace / "domain-skills" if args.runtime_workspace else DEFAULT_LINK
    if args.runtime_workspace and not runtime_root.is_dir():
        errors.append(f"explicit runtime domain-skills directory missing: {runtime_root}")
    elif not args.runtime_workspace and not DEFAULT_LINK.is_symlink():
        errors.append(f"default runtime path is not a symlink: {DEFAULT_LINK}")
    elif runtime_root.resolve() != ROOT.resolve():
        errors.append(f"runtime path targets {runtime_root.resolve()}, expected {ROOT.resolve()}")

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1

    print(f"PASS registry={len(registered)} skills; runtime_root={runtime_root.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
