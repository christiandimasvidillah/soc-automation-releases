#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from standby_worker import StandbyError, StandbyWorker


class MasterError(RuntimeError):
    pass


class SocMaster:
    """Supervisor dual-process active/standby untuk SOC Automation Level 3 foundation."""

    def __init__(
        self,
        root: Path,
        *,
        startup_timeout: float = 90.0,
        shutdown_timeout: float = 180.0,
        control_interval: float = 1.0,
        worker_script: str = "main.py",
        python_bin: str = sys.executable,
        stale_after: float = 90.0,
        unhealthy_after: float = 180.0,
        max_restarts: int = 3,
        restart_window: float = 600.0,
        restart_backoff: tuple[float, ...] = (5.0, 15.0, 30.0),
    ) -> None:
        self.root = root.expanduser().resolve()
        self.current = self.root / "current"
        self.shared = self.root / "shared"
        self.control_dir = self.shared / "control"
        self.master_pid_file = self.shared / "soc_master.pid"
        self.master_state_file = self.shared / "master.json"
        self.worker_slot = "blue"
        self.worker_role = "active"
        self.worker_runtime_dir = self.shared / "workers" / self.worker_slot
        self.active_slot_file = self.shared / "active_slot.json"
        self.worker_pid_file = self.worker_runtime_dir / "pid.json"
        self.worker_health_file = self.worker_runtime_dir / "health.json"
        self.startup_timeout = startup_timeout
        self.shutdown_timeout = shutdown_timeout
        self.control_interval = control_interval
        self.worker_script = worker_script
        self.python_bin = python_bin
        self.stale_after = stale_after
        self.unhealthy_after = unhealthy_after
        self.max_restarts = max_restarts
        self.restart_window = restart_window
        self.restart_backoff = restart_backoff or (5.0,)
        self.process: subprocess.Popen[bytes] | None = None
        self.standby = StandbyWorker(
            self.root,
            timeout=startup_timeout,
            shutdown_timeout=shutdown_timeout,
        )
        self.stop_requested = False
        self.restart_requested = False
        self.started_at = self._now()
        self.worker_started_at: str | None = None
        self.last_worker_exit_code: int | None = None
        self.restart_count = 0
        self.auto_restart_count = 0
        self.health_restart_count = 0
        self.crash_restart_count = 0
        self.restart_history: deque[float] = deque()
        self.next_restart_at: str | None = None
        self.worker_health_state = "unknown"
        self.last_restart_reason: str | None = None
        self.last_command: str | None = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()

    @staticmethod
    def _parse_timestamp(value: object) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _heartbeat_age(self, health: dict[str, Any] | None = None) -> float | None:
        health = health or self._worker_health()
        heartbeat = self._parse_timestamp(health.get("last_heartbeat"))
        if heartbeat is None:
            return None
        return max(0.0, (datetime.now(timezone.utc) - heartbeat).total_seconds())

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _atomic_json(self, path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def _current_version(self) -> str:
        try:
            return (self.current / "VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            return "unknown"

    def _worker_health(self) -> dict[str, Any]:
        active_slot = (self._read_json(self.active_slot_file) or {}).get("active_slot", "blue")
        return self._read_json(self.shared / "workers" / active_slot / "health.json") or {}

    def _write_state(self, status: str, **extra: Any) -> None:
        health = self._worker_health()
        worker_pid = health.get("pid")
        payload = {
            "status": status,
            "master_pid": os.getpid(),
            "master_version": "4.10.0-phase-j",
            "started_at": self.started_at,
            "updated_at": self._now(),
            "current_release": str(self.current.resolve()) if self.current.exists() else None,
            "target_version": self._current_version(),
            "active_slot": (self._read_json(self.active_slot_file) or {}).get("active_slot", self.worker_slot),
            "worker_role": health.get("role", self.worker_role),
            "worker_pid": worker_pid,
            "worker_version": health.get("version"),
            "worker_health": health.get("status"),
            "worker_started_at": self.worker_started_at,
            "restart_count": self.restart_count,
            "auto_restart_count": self.auto_restart_count,
            "health_restart_count": self.health_restart_count,
            "crash_restart_count": self.crash_restart_count,
            "max_restarts": self.max_restarts,
            "restart_window_seconds": self.restart_window,
            "restart_budget_used": len(self.restart_history),
            "next_restart_at": self.next_restart_at,
            "worker_health_state": self.worker_health_state,
            "heartbeat_age_seconds": self._heartbeat_age(health),
            "stale_after_seconds": self.stale_after,
            "unhealthy_after_seconds": self.unhealthy_after,
            "last_restart_reason": self.last_restart_reason,
            "last_worker_exit_code": self.last_worker_exit_code,
            "last_command": self.last_command,
        }
        payload.update(self.standby.snapshot())
        payload.update(extra)
        self._atomic_json(self.master_state_file, payload)

    def acquire(self) -> None:
        self.shared.mkdir(parents=True, exist_ok=True)
        self.control_dir.mkdir(parents=True, exist_ok=True)
        self.worker_runtime_dir.mkdir(parents=True, exist_ok=True)
        active_state = self._read_json(self.active_slot_file)
        if not active_state or active_state.get("active_slot") not in {"blue", "green"}:
            self._atomic_json(
                self.active_slot_file,
                {
                    "active_slot": "blue",
                    "generation": 1,
                    "updated_at": self._now(),
                    "updated_by": "soc_master_bootstrap",
                },
            )
        existing = self._read_json(self.master_pid_file)
        if existing:
            pid = existing.get("pid")
            if isinstance(pid, int) and pid != os.getpid() and self._pid_alive(pid):
                raise MasterError(f"SocMaster lain masih aktif dengan PID {pid}.")
        worker = self._read_json(self.worker_pid_file)
        if worker:
            pid = worker.get("pid")
            if isinstance(pid, int) and self._pid_alive(pid):
                raise MasterError(
                    f"Worker PID {pid} masih aktif di luar supervisor. "
                    "Hentikan worker Level 2 terlebih dahulu."
                )
        self._atomic_json(
            self.master_pid_file,
            {"pid": os.getpid(), "started_at": self.started_at},
        )
        self._write_state("starting")

    def release(self) -> None:
        existing = self._read_json(self.master_pid_file)
        if existing and existing.get("pid") == os.getpid():
            try:
                self.master_pid_file.unlink()
            except FileNotFoundError:
                pass

    def _install_signals(self) -> None:
        def handle(signum: int, _frame: object) -> None:
            self.last_command = signal.Signals(signum).name
            self.stop_requested = True
            self._write_state("stopping")

        signal.signal(signal.SIGTERM, handle)
        signal.signal(signal.SIGINT, handle)

    def _clear_stale_worker_files(self) -> None:
        pid_data = self._read_json(self.worker_pid_file)
        if pid_data:
            pid = pid_data.get("pid")
            if isinstance(pid, int) and self._pid_alive(pid):
                raise MasterError(f"Worker lain masih aktif dengan PID {pid}.")
            try:
                self.worker_pid_file.unlink()
            except FileNotFoundError:
                pass

    def start_worker(self) -> None:
        active_state = self._read_json(self.active_slot_file) or {}
        if active_state.get("active_slot") != "blue":
            self._atomic_json(self.active_slot_file, {
                "active_slot": "blue",
                "generation": int(active_state.get("generation") or 0) + 1,
                "updated_at": self._now(),
                "updated_by": "phase_j_safe_restart_baseline",
            })
        self._clear_stale_worker_files()
        release = self.current.resolve(strict=True)
        entrypoint = release / self.worker_script
        if not entrypoint.is_file():
            raise MasterError(f"Worker entrypoint tidak ditemukan: {entrypoint}")
        self.worker_started_at = self._now()
        worker_env = os.environ.copy()
        worker_env["SOC_WORKER_SLOT"] = self.worker_slot
        worker_env["SOC_WORKER_ROLE"] = self.worker_role
        self.process = subprocess.Popen(
            [self.python_bin, str(entrypoint)],
            cwd=release,
            env=worker_env,
            start_new_session=True,
        )
        self._write_state("worker_starting")
        self.wait_until_ready()
        try:
            self.standby.start(release, self.worker_script, self.python_bin)
        except StandbyError as exc:
            self.standby.last_error = str(exc)
            raise MasterError(f"Green standby readiness gagal: {exc}") from exc
        self._write_state("running")

    def wait_until_ready(self) -> None:
        if self.process is None:
            raise MasterError("Worker belum dijalankan.")
        expected_version = self._current_version()
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            exit_code = self.process.poll()
            if exit_code is not None:
                self.last_worker_exit_code = exit_code
                raise MasterError(f"Worker exit saat startup dengan kode {exit_code}.")
            pid_data = self._read_json(self.worker_pid_file) or {}
            health = self._worker_health()
            if (
                pid_data.get("pid") == self.process.pid
                and health.get("pid") == self.process.pid
                and health.get("status") == "healthy"
                and health.get("version") == expected_version
            ):
                self.worker_health_state = "healthy"
                return
            time.sleep(0.5)
        self.stop_worker()
        raise MasterError(
            f"Worker tidak healthy dalam {self.startup_timeout:.0f} detik."
        )

    def _prune_restart_history(self) -> None:
        cutoff = time.monotonic() - self.restart_window
        while self.restart_history and self.restart_history[0] < cutoff:
            self.restart_history.popleft()

    def _restart_budget_available(self) -> bool:
        self._prune_restart_history()
        return len(self.restart_history) < self.max_restarts

    def _restart_delay(self) -> float:
        index = min(len(self.restart_history), len(self.restart_backoff) - 1)
        return self.restart_backoff[index]

    def _wait_backoff(self, delay: float, reason: str) -> bool:
        deadline = time.monotonic() + delay
        self.next_restart_at = datetime.fromtimestamp(
            time.time() + delay,
            tz=timezone.utc,
        ).astimezone().isoformat()
        self._write_state("restart_backoff", restart_reason=reason)
        while time.monotonic() < deadline:
            self._consume_requests()
            if self.stop_requested:
                self.next_restart_at = None
                return False
            if self.restart_requested:
                self.restart_requested = False
                self.restart_history.clear()
                self.next_restart_at = None
                return True
            time.sleep(min(self.control_interval, 0.5))
        self.next_restart_at = None
        return True

    def _bounded_restart(self, reason: str) -> bool:
        if not self._restart_budget_available():
            self.last_restart_reason = reason
            self.worker_health_state = "crash_loop"
            self._write_state("worker_crash_loop", restart_reason=reason)
            return False
        delay = self._restart_delay()
        self.restart_history.append(time.monotonic())
        self.restart_count += 1
        self.auto_restart_count += 1
        if reason.startswith("health_"):
            self.health_restart_count += 1
        else:
            self.crash_restart_count += 1
        self.last_restart_reason = reason
        if not self._wait_backoff(delay, reason):
            return False
        self.start_worker()
        return True

    def _evaluate_health(self) -> str:
        health = self._worker_health()
        age = self._heartbeat_age(health)
        if age is None:
            self.worker_health_state = "unknown"
        elif age > self.unhealthy_after:
            self.worker_health_state = "unhealthy"
        elif age > self.stale_after:
            self.worker_health_state = "stale"
        elif health.get("status") == "healthy":
            self.worker_health_state = "healthy"
        else:
            self.worker_health_state = str(health.get("status") or "unknown")
        return self.worker_health_state

    def stop_worker(self) -> None:
        self.standby.stop()
        process = self.process
        if process is None or process.poll() is not None:
            return
        self._write_state("worker_stopping")
        try:
            os.kill(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            self.last_worker_exit_code = process.wait(timeout=self.shutdown_timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            self.last_worker_exit_code = process.wait(timeout=10)
            self._write_state("worker_killed_after_timeout")
        finally:
            self.process = None

    def _consume_requests(self) -> None:
        stop_request = self.control_dir / "stop.request"
        restart_request = self.control_dir / "restart.request"
        if stop_request.exists():
            self.last_command = "stop"
            stop_request.unlink(missing_ok=True)
            restart_request.unlink(missing_ok=True)
            self.stop_requested = True
        elif restart_request.exists():
            self.last_command = "restart"
            restart_request.unlink(missing_ok=True)
            self.restart_requested = True

    def run(self) -> int:
        self.acquire()
        self._install_signals()
        try:
            try:
                self.start_worker()
            except Exception as exc:
                self.last_worker_exit_code = self.process.poll() if self.process else 1
                self.process = None
                if not self._bounded_restart(f"startup_failure:{type(exc).__name__}"):
                    self._write_state("worker_crash_loop", error=str(exc))

            while not self.stop_requested:
                self._consume_requests()
                if self.stop_requested:
                    break

                if self.restart_requested:
                    self.restart_requested = False
                    self.restart_history.clear()
                    self.last_command = "restart"
                    self.last_restart_reason = "manual"
                    self._write_state("restarting")
                    self.stop_worker()
                    self.restart_count += 1
                    self.start_worker()
                    continue

                if self.standby.process is not None and self.standby.process.poll() is not None:
                    self.standby.last_exit_code = self.standby.process.returncode
                    self.standby.process = None
                    try:
                        self.standby.start(self.current.resolve(strict=True), self.worker_script, self.python_bin)
                    except Exception as exc:
                        self.standby.last_error = str(exc)
                        self._write_state("standby_failed", error=str(exc))

                if self.process is not None:
                    exit_code = self.process.poll()
                    if exit_code is not None:
                        self.last_worker_exit_code = exit_code
                        self.process = None
                        self._clear_stale_worker_files()
                        self.worker_health_state = "exited"
                        self._write_state("worker_exited")
                        self._bounded_restart(f"worker_exit:{exit_code}")
                        continue

                    health_state = self._evaluate_health()
                    if health_state == "unhealthy":
                        self._write_state("worker_unhealthy")
                        self.stop_worker()
                        self._bounded_restart("health_unhealthy")
                        continue
                    if health_state == "stale":
                        self._write_state("worker_stale")
                    else:
                        self._write_state("running")
                else:
                    # Crash-loop mode keeps master alive for manual restart/stop.
                    self._write_state("worker_crash_loop")

                time.sleep(self.control_interval)

            self.stop_worker()
            self._write_state("stopped", stopped_at=self._now())
            return 0
        except Exception as exc:
            self._write_state("failed", error=str(exc))
            self.stop_worker()
            raise
        finally:
            self.release()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SOC Automation local supervisor")
    parser.add_argument("--root", default="~/SOC-Automation")
    parser.add_argument("--startup-timeout", type=float, default=90.0)
    parser.add_argument("--shutdown-timeout", type=float, default=180.0)
    parser.add_argument("--control-interval", type=float, default=1.0)
    parser.add_argument("--worker-script", default="main.py")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--stale-after", type=float, default=90.0)
    parser.add_argument("--unhealthy-after", type=float, default=180.0)
    parser.add_argument("--max-restarts", type=int, default=3)
    parser.add_argument("--restart-window", type=float, default=600.0)
    parser.add_argument(
        "--restart-backoff",
        default="5,15,30",
        help="Daftar detik backoff dipisahkan koma",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        restart_backoff = tuple(
            float(value.strip())
            for value in args.restart_backoff.split(",")
            if value.strip()
        )
    except ValueError:
        print("MASTER ERROR: --restart-backoff tidak valid", file=sys.stderr)
        return 2
    master = SocMaster(
        Path(args.root),
        startup_timeout=args.startup_timeout,
        shutdown_timeout=args.shutdown_timeout,
        control_interval=args.control_interval,
        worker_script=args.worker_script,
        python_bin=args.python_bin,
        stale_after=args.stale_after,
        unhealthy_after=args.unhealthy_after,
        max_restarts=args.max_restarts,
        restart_window=args.restart_window,
        restart_backoff=restart_backoff,
    )
    try:
        return master.run()
    except (MasterError, OSError, subprocess.SubprocessError) as exc:
        print(f"MASTER ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
