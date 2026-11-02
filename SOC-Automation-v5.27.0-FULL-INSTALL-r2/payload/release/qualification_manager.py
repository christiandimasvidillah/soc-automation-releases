#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


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


def check_sqlite(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "database_missing"
    try:
        con = sqlite3.connect(path, timeout=10)
        result = con.execute("PRAGMA integrity_check").fetchone()[0]
        con.close()
    except (sqlite3.Error, OSError) as exc:
        return False, f"sqlite_error:{exc}"
    return result == "ok", result


class FinalQualification:
    def __init__(self, root: Path, *, duration: float, interval: float) -> None:
        self.root = root.expanduser().resolve()
        self.shared = self.root / "shared"
        self.current = self.root / "current"
        self.duration = max(1.0, duration)
        self.interval = max(0.2, interval)
        self.report = self.shared / "level3_qualification.json"
        self.failures: list[dict[str, Any]] = []
        self.samples = 0

    def sample(self) -> dict[str, Any]:
        master = read_json(self.shared / "master.json")
        active_state = read_json(self.shared / "active_slot.json")
        active = str(active_state.get("active_slot") or "blue")
        standby = "green" if active == "blue" else "blue"
        ah = read_json(self.shared / "workers" / active / "health.json")
        sh = read_json(self.shared / "workers" / standby / "health.json")
        sqlite_ok, sqlite_detail = check_sqlite(self.shared / "ticket_locks.sqlite3")
        version = ""
        try:
            version = (self.current / "VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            pass
        checks = {
            "master_running": master.get("status") == "running",
            "active_slot_valid": active in {"blue", "green"},
            "active_pid_alive": pid_alive(ah.get("pid")),
            "active_health": ah.get("status") == "healthy",
            "active_role": ah.get("role") == "active",
            "active_identity": ah.get("slot") == active,
            "active_version": ah.get("version") == version,
            "standby_pid_alive": pid_alive(sh.get("pid")),
            "standby_health": sh.get("status") == "ready",
            "standby_role": sh.get("role") == "standby",
            "standby_identity": sh.get("slot") == standby,
            "standby_version": sh.get("version") == version,
            "standby_no_intake": int(sh.get("in_flight") or 0) == 0,
            "sqlite_integrity": sqlite_ok,
        }
        result = {
            "sampled_at": now(),
            "version": version,
            "active_slot": active,
            "standby_slot": standby,
            "sqlite_detail": sqlite_detail,
            "checks": checks,
            "passed": all(checks.values()),
        }
        if not result["passed"]:
            self.failures.append(result)
        self.samples += 1
        return result

    def run(self) -> int:
        started = now()
        deadline = time.monotonic() + self.duration
        latest: dict[str, Any] = {}
        while time.monotonic() < deadline:
            latest = self.sample()
            atomic_json(self.report, {
                "status": "running",
                "started_at": started,
                "updated_at": now(),
                "duration_seconds": self.duration,
                "samples": self.samples,
                "failure_count": len(self.failures),
                "latest": latest,
            })
            time.sleep(self.interval)
        status = "passed" if not self.failures else "failed"
        atomic_json(self.report, {
            "status": status,
            "started_at": started,
            "completed_at": now(),
            "duration_seconds": self.duration,
            "samples": self.samples,
            "failure_count": len(self.failures),
            "failures": self.failures[-20:],
            "latest": latest,
            "eligible_for_v5": status == "passed",
        })
        return 0 if status == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Level 3 final release qualification")
    parser.add_argument("--root", default="~/SOC-Automation")
    parser.add_argument("--duration", type=float, default=3600.0)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    runner = FinalQualification(Path(args.root), duration=args.duration, interval=args.interval)
    code = runner.run()
    print(json.dumps(read_json(runner.report), ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
