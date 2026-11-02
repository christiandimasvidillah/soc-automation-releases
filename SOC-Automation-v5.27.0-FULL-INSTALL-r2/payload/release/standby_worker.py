from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class StandbyError(RuntimeError):
    pass


class StandbyWorker:
    """Lifecycle dan readiness validator untuk Green standby process."""

    def __init__(self, root: Path, *, timeout: float = 90.0, shutdown_timeout: float = 180.0) -> None:
        self.root = root
        self.shared = root / "shared"
        self.runtime_dir = self.shared / "workers" / "green"
        self.pid_file = self.runtime_dir / "pid.json"
        self.health_file = self.runtime_dir / "health.json"
        self.timeout = timeout
        self.shutdown_timeout = shutdown_timeout
        self.process: subprocess.Popen[bytes] | None = None
        self.last_exit_code: int | None = None
        self.last_error: str | None = None

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _pid_alive(pid: object) -> bool:
        if not isinstance(pid, int):
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self, release: Path, worker_script: str, python_bin: str = sys.executable) -> None:
        if self.running():
            return
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        stale = self._read_json(self.pid_file).get("pid")
        if self._pid_alive(stale):
            raise StandbyError(f"Green standby PID {stale} sudah aktif.")
        self.pid_file.unlink(missing_ok=True)
        entrypoint = release / worker_script
        env = os.environ.copy()
        env["SOC_WORKER_SLOT"] = "green"
        env["SOC_WORKER_ROLE"] = "standby"
        self.process = subprocess.Popen(
            [python_bin, str(entrypoint)],
            cwd=release,
            env=env,
            start_new_session=True,
        )
        self.last_error = None
        self.wait_ready((release / "VERSION").read_text(encoding="utf-8").strip())

    def wait_ready(self, expected_version: str) -> None:
        if self.process is None:
            raise StandbyError("Green standby belum dimulai.")
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            exit_code = self.process.poll()
            if exit_code is not None:
                self.last_exit_code = exit_code
                raise StandbyError(f"Green standby exit saat startup: {exit_code}")
            pid_data = self._read_json(self.pid_file)
            health = self._read_json(self.health_file)
            if (
                pid_data.get("pid") == self.process.pid
                and health.get("pid") == self.process.pid
                and health.get("slot") == "green"
                and health.get("role") == "standby"
                and health.get("status") == "ready"
                and health.get("version") == expected_version
                and health.get("poll_cycle", 0) == 0
                and health.get("tickets_submitted", 0) == 0
            ):
                return
            time.sleep(0.25)
        self.stop()
        raise StandbyError("Green standby tidak ready sebelum timeout.")

    def stop(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            self.process = None
            return
        try:
            os.kill(process.pid, signal.SIGTERM)
            self.last_exit_code = process.wait(timeout=self.shutdown_timeout)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            process.kill()
            self.last_exit_code = process.wait(timeout=10)
        finally:
            self.process = None

    def snapshot(self) -> dict[str, Any]:
        health = self._read_json(self.health_file)
        return {
            "standby_slot": "green",
            "standby_pid": self.process.pid if self.running() else None,
            "standby_alive": self.running(),
            "standby_status": health.get("status"),
            "standby_role": health.get("role"),
            "standby_version": health.get("version"),
            "standby_poll_cycle": health.get("poll_cycle"),
            "standby_tickets_submitted": health.get("tickets_submitted"),
            "standby_last_exit_code": self.last_exit_code,
            "standby_error": self.last_error,
        }
