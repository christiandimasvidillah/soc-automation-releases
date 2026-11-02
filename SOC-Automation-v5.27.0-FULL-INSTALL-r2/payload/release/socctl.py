#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ControlError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


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


def atomic_request(path: Path, command: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(
            {
                "command": command,
                "requested_at": datetime.now(timezone.utc).astimezone().isoformat(),
                "requested_by_pid": os.getpid(),
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def paths(root: Path) -> dict[str, Path]:
    shared = root / "shared"
    return {
        "shared": shared,
        "control": shared / "control",
        "master_pid": shared / "soc_master.pid",
        "master_state": shared / "master.json",
        "worker_pid": shared / "workers" / "blue" / "pid.json",
        "worker_health": shared / "workers" / "blue" / "health.json",
        "green_pid": shared / "workers" / "green" / "pid.json",
        "green_health": shared / "workers" / "green" / "health.json",
    }


def command_status(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    p = paths(root)
    master_pid_data = read_json(p["master_pid"])
    master = read_json(p["master_state"])
    worker_pid_data = read_json(p["worker_pid"])
    worker = read_json(p["worker_health"])
    master_pid = master_pid_data.get("pid") or master.get("master_pid")
    worker_pid = worker_pid_data.get("pid") or worker.get("pid")
    print(f"Root             : {root}")
    print(f"Master PID       : {master_pid or '-'}")
    print(f"Master alive     : {pid_alive(master_pid)}")
    print(f"Master status    : {master.get('status', '-')}")
    print(f"Active slot      : {master.get('active_slot', 'blue')}")
    print(f"Target version   : {master.get('target_version', '-')}")
    print(f"Worker PID       : {worker_pid or '-'}")
    print(f"Worker alive     : {pid_alive(worker_pid)}")
    print(f"Worker health    : {worker.get('status', '-')}")
    print(f"Worker version   : {worker.get('version', '-')}")
    print(f"Last heartbeat   : {worker.get('last_heartbeat', '-')}")
    print(f"Last poll        : {worker.get('last_poll_finished', '-')}")
    print(f"Health state     : {master.get('worker_health_state', '-')}")
    print(f"Heartbeat age    : {master.get('heartbeat_age_seconds', '-')}")
    print(f"Restart count    : {master.get('restart_count', '-')}")
    print(f"Auto restarts    : {master.get('auto_restart_count', '-')}")
    print(f"Health restarts  : {master.get('health_restart_count', '-')}")
    print(f"Crash restarts   : {master.get('crash_restart_count', '-')}")
    print(f"Restart budget   : {master.get('restart_budget_used', '-')} / {master.get('max_restarts', '-')}")
    print(f"Last reason      : {master.get('last_restart_reason', '-')}")
    print(f"Next restart     : {master.get('next_restart_at', '-')}")
    print(f"Last command     : {master.get('last_command', '-')}")
    print(f"Last exit code   : {master.get('last_worker_exit_code', '-')}")
    green_pid_data = read_json(p["green_pid"])
    green = read_json(p["green_health"])
    green_pid = green_pid_data.get("pid") or green.get("pid")
    print(f"Green PID        : {green_pid or '-'}")
    print(f"Green alive      : {pid_alive(green_pid)}")
    print(f"Green health     : {green.get('status', '-')}")
    print(f"Green role       : {green.get('role', '-')}")
    print(f"Green version    : {green.get('version', '-')}")


def _request_and_wait(
    root: Path,
    *,
    command: str,
    timeout: float,
) -> None:
    p = paths(root)
    master_pid_data = read_json(p["master_pid"])
    master_pid = master_pid_data.get("pid")
    if not pid_alive(master_pid):
        raise ControlError("SocMaster tidak aktif.")
    old_worker = read_json(p["worker_pid"]).get("pid")
    request = p["control"] / f"{command}.request"
    atomic_request(request, command)
    print(f"Request {command} dikirim ke SocMaster PID {master_pid}.")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        master = read_json(p["master_state"])
        worker = read_json(p["worker_health"])
        worker_pid = read_json(p["worker_pid"]).get("pid")
        if command == "stop":
            master_pid_present = p["master_pid"].exists()
            worker_pid_present = p["worker_pid"].exists()
            if not master_pid_present and not worker_pid_present:
                print("Master dan worker berhenti dengan graceful.")
                return
        else:
            if (
                worker_pid != old_worker
                and pid_alive(worker_pid)
                and worker.get("status") == "healthy"
                and worker.get("version") == master.get("target_version")
            ):
                print(
                    "Restart berhasil: "
                    f"worker PID {old_worker} -> {worker_pid}, "
                    f"version {worker.get('version')}."
                )
                return
        time.sleep(0.5)
    raise ControlError(f"Timeout menunggu {command} setelah {timeout:.0f} detik.")


def command_restart(args: argparse.Namespace) -> None:
    _request_and_wait(
        Path(args.root).expanduser().resolve(),
        command="restart",
        timeout=args.timeout,
    )


def command_stop(args: argparse.Namespace) -> None:
    _request_and_wait(
        Path(args.root).expanduser().resolve(),
        command="stop",
        timeout=args.timeout,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control CLI untuk SocMaster")
    parser.add_argument("--root", default="~/SOC-Automation")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.set_defaults(func=command_status)
    restart = sub.add_parser("restart")
    restart.add_argument("--timeout", type=float, default=240.0)
    restart.set_defaults(func=command_restart)
    stop = sub.add_parser("stop")
    stop.add_argument("--timeout", type=float, default=240.0)
    stop.set_defaults(func=command_stop)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except ControlError as exc:
        print(f"CONTROL ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
