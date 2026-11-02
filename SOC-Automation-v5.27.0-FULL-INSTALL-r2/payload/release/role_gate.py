from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ActiveSlotGate:
    """Atomic active-slot state. Only the selected slot may perform intake."""

    VALID_SLOTS = {"blue", "green"}

    def __init__(self, shared_dir: str | Path, worker_slot: str) -> None:
        self.shared_dir = Path(shared_dir).expanduser().resolve()
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.shared_dir / "active_slot.json"
        self.worker_slot = worker_slot.strip().lower()
        if self.worker_slot not in self.VALID_SLOTS:
            raise ValueError(f"Worker slot tidak valid: {worker_slot!r}")
        self._lock = threading.RLock()
        self._ensure_initialized()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()

    def _read(self) -> dict[str, Any]:
        try:
            value = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        temporary = self.state_file.with_name(
            f".{self.state_file.name}.{os.getpid()}.tmp"
        )
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.state_file)

    def _ensure_initialized(self) -> None:
        with self._lock:
            state = self._read()
            if state.get("active_slot") in self.VALID_SLOTS:
                return
            self._atomic_write(
                {
                    "active_slot": "blue",
                    "generation": 1,
                    "updated_at": self._now(),
                    "updated_by": "bootstrap",
                }
            )

    def active_slot(self) -> str:
        value = self._read().get("active_slot")
        return value if value in self.VALID_SLOTS else "blue"

    def is_active(self) -> bool:
        return self.active_slot() == self.worker_slot

    def role(self) -> str:
        return "active" if self.is_active() else "standby"

    def switch(self, target_slot: str, *, updated_by: str = "operator") -> dict[str, Any]:
        target = target_slot.strip().lower()
        if target not in self.VALID_SLOTS:
            raise ValueError(f"Target slot tidak valid: {target_slot!r}")
        with self._lock:
            current = self._read()
            generation = int(current.get("generation") or 0) + 1
            payload = {
                "active_slot": target,
                "generation": generation,
                "updated_at": self._now(),
                "updated_by": updated_by,
            }
            self._atomic_write(payload)
            return payload
