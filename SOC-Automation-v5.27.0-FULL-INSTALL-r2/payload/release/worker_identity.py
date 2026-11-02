from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VALID_SLOTS = {"blue", "green"}
VALID_ROLES = {"active", "standby", "draining"}


@dataclass(frozen=True)
class WorkerIdentity:
    slot: str
    role: str

    @classmethod
    def from_environment(cls) -> "WorkerIdentity":
        slot = os.getenv("SOC_WORKER_SLOT", "blue").strip().lower()
        role = os.getenv("SOC_WORKER_ROLE", "active").strip().lower()
        if slot not in VALID_SLOTS:
            raise ValueError(f"SOC_WORKER_SLOT tidak valid: {slot!r}")
        if role not in VALID_ROLES:
            raise ValueError(f"SOC_WORKER_ROLE tidak valid: {role!r}")
        return cls(slot=slot, role=role)

    def runtime_dir(self, shared_dir: str | Path) -> Path:
        return Path(shared_dir).expanduser().resolve() / "workers" / self.slot

    def pid_file(self, shared_dir: str | Path) -> Path:
        return self.runtime_dir(shared_dir) / "pid.json"

    def health_file(self, shared_dir: str | Path) -> Path:
        return self.runtime_dir(shared_dir) / "health.json"
