#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SoakError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def pid_alive(pid: object) -> bool:
    if not isinstance(pid, int) or pid < 2:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Level3Soak:
    def __init__(self, root: Path, *, duration: float, interval: float) -> None:
        self.root = root.expanduser().resolve()
        self.shared = self.root / "shared"
        self.report_file = self.shared / "level3_soak.json"
        self.duration = duration
        self.interval = interval
        self.samples = 0
        self.failures: list[dict[str, Any]] = []
        self.started_at = now()

    def sample(self) -> dict[str, Any]:
        master = read_json(self.shared / "master.json")
        active_state = read_json(self.shared / "active_slot.json")
        active = str(active_state.get("active_slot") or "blue")
        standby = "green" if active == "blue" else "blue"
        active_health = read_json(self.shared / "workers" / active / "health.json")
        standby_health = read_json(self.shared / "workers" / standby / "health.json")
        checks = {
            "master_running": master.get("status") in {"running", "worker_stale"},
            "active_pid_alive": pid_alive(active_health.get("pid")),
            "active_healthy": active_health.get("status") == "healthy",
            "active_role": active_health.get("role") == "active",
            "active_identity": active_health.get("slot") == active,
            "standby_pid_alive": pid_alive(standby_health.get("pid")),
            "standby_ready": standby_health.get("status") == "ready",
            "standby_role": standby_health.get("role") == "standby",
            "standby_identity": standby_health.get("slot") == standby,
            "standby_no_intake": int(standby_health.get("in_flight") or 0) == 0,
        }
        result = {
            "sampled_at": now(),
            "active_slot": active,
            "standby_slot": standby,
            "checks": checks,
            "passed": all(checks.values()),
        }
        if not result["passed"]:
            self.failures.append(result)
        self.samples += 1
        return result

    def run(self) -> int:
        deadline = time.monotonic() + self.duration
        latest: dict[str, Any] = {}
        while time.monotonic() < deadline:
            latest = self.sample()
            atomic_json(
                self.report_file,
                {
                    "status": "running",
                    "started_at": self.started_at,
                    "updated_at": now(),
                    "duration_seconds": self.duration,
                    "samples": self.samples,
                    "failure_count": len(self.failures),
                    "latest": latest,
                },
            )
            time.sleep(self.interval)
        status = "passed" if not self.failures else "failed"
        atomic_json(
            self.report_file,
            {
                "status": status,
                "started_at": self.started_at,
                "completed_at": now(),
                "duration_seconds": self.duration,
                "samples": self.samples,
                "failure_count": len(self.failures),
                "failures": self.failures[-20:],
                "latest": latest,
            },
        )
        return 0 if status == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Level 3 Blue/Green soak validator")
    parser.add_argument("--root", default="~/SOC-Automation")
    parser.add_argument("--duration", type=float, default=3600.0)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    runner = Level3Soak(
        Path(args.root),
        duration=max(1.0, args.duration),
        interval=max(0.2, args.interval),
    )
    result = runner.run()
    print(json.dumps(read_json(runner.report_file), ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
