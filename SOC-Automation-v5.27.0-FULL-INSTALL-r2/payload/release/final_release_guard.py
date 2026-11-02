#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

EXPECTED_SOURCE_VERSION = "4.12.0-rc1"
FINAL_VERSION = "5.0.0"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def pid_alive(value: object) -> bool:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return False
    if pid < 2:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def sqlite_ok(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        con = sqlite3.connect(path, timeout=10)
        result = con.execute("PRAGMA integrity_check").fetchone()[0]
        con.close()
    except (sqlite3.Error, OSError):
        return False
    return result == "ok"


def evaluate(root: Path, *, expected_current: str = EXPECTED_SOURCE_VERSION) -> dict[str, Any]:
    root = root.expanduser().resolve()
    shared = root / "shared"
    current = root / "current"
    try:
        version = (current / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        version = ""
    qualification = read_json(shared / "level3_qualification.json")
    master = read_json(shared / "master.json")
    active_state = read_json(shared / "active_slot.json")
    active = str(active_state.get("active_slot") or "")
    standby = "green" if active == "blue" else "blue" if active == "green" else ""
    active_health = read_json(shared / "workers" / active / "health.json") if active else {}
    standby_health = read_json(shared / "workers" / standby / "health.json") if standby else {}
    checks = {
        "source_version": version == expected_current,
        "qualification_passed": qualification.get("status") == "passed",
        "qualification_no_failures": int(qualification.get("failure_count") or 0) == 0,
        "qualification_eligible": qualification.get("eligible_for_v5") is True,
        "qualification_version": qualification.get("latest", {}).get("version") == expected_current,
        "master_running": master.get("status") == "running",
        "active_slot_valid": active in {"blue", "green"},
        "active_alive": pid_alive(active_health.get("pid")),
        "active_healthy": active_health.get("status") == "healthy",
        "active_role": active_health.get("role") == "active",
        "active_version": active_health.get("version") == expected_current,
        "standby_alive": pid_alive(standby_health.get("pid")),
        "standby_ready": standby_health.get("status") == "ready",
        "standby_role": standby_health.get("role") == "standby",
        "standby_version": standby_health.get("version") == expected_current,
        "standby_no_intake": int(standby_health.get("in_flight") or 0) == 0,
        "sqlite_integrity": sqlite_ok(shared / "ticket_locks.sqlite3"),
    }
    return {
        "source_version": version,
        "target_version": FINAL_VERSION,
        "eligible": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Guard final promotion to SOC Automation v5.0.0")
    parser.add_argument("--root", default="~/SOC-Automation")
    parser.add_argument("--expected-current", default=EXPECTED_SOURCE_VERSION)
    args = parser.parse_args()
    result = evaluate(Path(args.root), expected_current=args.expected_current)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["eligible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
