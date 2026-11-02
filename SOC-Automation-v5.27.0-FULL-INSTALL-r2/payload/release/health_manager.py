from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from worker_identity import WorkerIdentity


class HealthManagerError(RuntimeError):
    pass


class HealthManager:
    """Menyimpan PID dan status runtime secara atomik pada shared directory."""

    def __init__(self, shared_dir: str | Path, version: str, identity: WorkerIdentity | None = None) -> None:
        self.shared_dir = Path(shared_dir).expanduser().resolve()
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        self.version = version.strip() or "unknown"
        self.identity = identity or WorkerIdentity.from_environment()
        self.runtime_dir = self.identity.runtime_dir(self.shared_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.pid = os.getpid()
        self.pid_file = self.identity.pid_file(self.shared_dir)
        self.health_file = self.identity.health_file(self.shared_dir)
        self.started_at = self._now()
        self.started_monotonic = time.monotonic()
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {
            "status": "starting",
            "slot": self.identity.slot,
            "role": self.identity.role,
            "version": self.version,
            "pid": self.pid,
            "started_at": self.started_at,
            "last_heartbeat": self.started_at,
            "last_poll_started": None,
            "last_poll_finished": None,
            "last_poll_status": None,
            "poll_cycle": 0,
            "tickets_submitted": 0,
            "tickets_completed": 0,
            "tickets_failed": 0,
            "in_flight": 0,
            "pending_workers": 0,
            "shutdown_requested": False,
            "uptime_seconds": 0,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()

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

    def _atomic_write(self, path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_name(f".{path.name}.{self.pid}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def register(self) -> None:
        with self._lock:
            existing = self._read_json(self.pid_file)
            if existing:
                existing_pid = existing.get("pid")
                if (
                    isinstance(existing_pid, int)
                    and existing_pid != self.pid
                    and self._pid_alive(existing_pid)
                ):
                    raise HealthManagerError(
                        "Instance SOC Automation lain masih aktif "
                        f"dengan PID {existing_pid}."
                    )
            self._atomic_write(
                self.pid_file,
                {
                    "pid": self.pid,
                    "version": self.version,
                    "started_at": self.started_at,
                },
            )
            self.update(status="starting")

    def update(self, **changes: Any) -> None:
        with self._lock:
            self._state.update(changes)
            self._state["last_heartbeat"] = self._now()
            self._state["uptime_seconds"] = round(
                time.monotonic() - self.started_monotonic,
                3,
            )
            self._atomic_write(self.health_file, dict(self._state))

    def mark_running(self) -> None:
        self.update(status="healthy")

    def mark_role(self, role: str, *, active_slot: str) -> None:
        status = "healthy" if role == "active" else "ready"
        self.update(status=status, role=role, active_slot=active_slot)

    def mark_poll_started(
        self,
        *,
        poll_cycle: int,
        in_flight: int,
        pending_workers: int,
    ) -> None:
        self.update(
            status="healthy",
            poll_cycle=poll_cycle,
            last_poll_started=self._now(),
            last_poll_status="running",
            in_flight=in_flight,
            pending_workers=pending_workers,
        )

    def mark_poll_finished(
        self,
        *,
        submitted: int,
        in_flight: int,
        pending_workers: int,
        poll_status: str = "success",
    ) -> None:
        with self._lock:
            self._state["tickets_submitted"] += max(0, submitted)
        self.update(
            last_poll_finished=self._now(),
            last_poll_status=poll_status,
            in_flight=in_flight,
            pending_workers=pending_workers,
        )

    def mark_intake_health(self, *, status: str, circuit: dict[str, Any], error_code: str | None = None) -> None:
        degraded = status not in {"success", "idle"}
        self.update(
            status="degraded" if degraded else "healthy",
            jira_poll_status="success",
            ticket_intake_status=status,
            intake_circuit_breaker=circuit.get("state", "closed"),
            intake_consecutive_failures=circuit.get("consecutive_failures", 0),
            intake_failure_fingerprint=circuit.get("failure_fingerprint"),
            intake_open_until=circuit.get("open_until"),
            intake_error_code=error_code,
        )

    def mark_worker_finished(self, *, successful: bool) -> None:
        with self._lock:
            key = "tickets_completed" if successful else "tickets_failed"
            self._state[key] += 1
        self.update()

    def request_shutdown(self, *, signal_name: str | None = None) -> None:
        self.update(
            status="stopping",
            shutdown_requested=True,
            shutdown_signal=signal_name,
        )

    def shutdown(self, *, exit_code: int = 0) -> None:
        with self._lock:
            self.update(
                status="stopped" if exit_code == 0 else "failed",
                exit_code=exit_code,
                stopped_at=self._now(),
            )
            existing = self._read_json(self.pid_file)
            if existing and existing.get("pid") == self.pid:
                try:
                    self.pid_file.unlink()
                except FileNotFoundError:
                    pass
