#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from role_gate import ActiveSlotGate
except ModuleNotFoundError as exc:
    raise SystemExit(
        "CUTOVER ERROR: role_gate.py tidak ditemukan di folder manager. "
        "Jalankan: bash ~/SOC-Automation/current/activate_phase_e.sh"
    ) from exc


class CutoverError(RuntimeError):
    pass


class CutoverManager:
    def __init__(self, root: Path, *, timeout: float = 300.0, stabilization: float = 180.0) -> None:
        self.root = root.expanduser().resolve()
        self.shared = self.root / "shared"
        self.workers = self.shared / "workers"
        self.audit_file = self.shared / "cutover.json"
        self.lock_file = self.shared / "cutover.lock"
        self.timeout = timeout
        self.stabilization = stabilization

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()

    @staticmethod
    def read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def atomic_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    @staticmethod
    def pid_alive(pid: object) -> bool:
        if not isinstance(pid, int):
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def health(self, slot: str) -> dict[str, Any]:
        return self.read_json(self.workers / slot / "health.json")

    def acquire(self) -> None:
        try:
            descriptor = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise CutoverError("Cutover lain masih berjalan.") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "started_at": self.now()}, handle)

    def release(self) -> None:
        self.lock_file.unlink(missing_ok=True)

    def write_audit(self, status: str, **extra: Any) -> None:
        state = self.read_json(self.audit_file)
        state.update({"status": status, "updated_at": self.now(), **extra})
        self.atomic_json(self.audit_file, state)

    def validate_ready(self, slot: str) -> None:
        health = self.health(slot)
        pid = health.get("pid")
        if not self.pid_alive(pid):
            raise CutoverError(f"Slot {slot} tidak hidup.")
        if health.get("slot") != slot:
            raise CutoverError(f"Identitas health slot {slot} tidak cocok.")
        if health.get("status") not in {"ready", "healthy"}:
            raise CutoverError(f"Slot {slot} belum ready: {health.get('status')}")

    def wait_transition(self, source: str, target: str) -> None:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            source_health = self.health(source)
            target_health = self.health(target)
            source_drained = (
                source_health.get("role") == "standby"
                and source_health.get("status") == "ready"
                and int(source_health.get("in_flight") or 0) == 0
                and int(source_health.get("pending_workers") or 0) == 0
            )
            target_active = (
                target_health.get("role") == "active"
                and target_health.get("status") == "healthy"
                and self.pid_alive(target_health.get("pid"))
            )
            if source_drained and target_active:
                self.write_audit(
                    "cutover_complete",
                    source_slot=source,
                    target_slot=target,
                    source_health=source_health,
                    target_health=target_health,
                    completed_at=self.now(),
                )
                return
            time.sleep(0.5)
        raise CutoverError("Cutover timeout: target belum healthy atau source belum drained.")

    def stabilize(self, source: str, target: str) -> None:
        deadline = time.monotonic() + self.stabilization
        self.write_audit(
            "stabilizing",
            source_slot=source,
            target_slot=target,
            stabilization_seconds=self.stabilization,
        )
        while time.monotonic() < deadline:
            health = self.health(target)
            target_ok = (
                health.get("slot") == target
                and health.get("role") == "active"
                and health.get("status") == "healthy"
                and self.pid_alive(health.get("pid"))
            )
            if not target_ok:
                raise CutoverError(
                    f"Target {target} gagal selama stabilization: "
                    f"status={health.get('status')} role={health.get('role')}"
                )
            time.sleep(min(1.0, max(0.1, self.stabilization / 20)))
        self.write_audit(
            "committed",
            source_slot=source,
            target_slot=target,
            committed_at=self.now(),
        )

    def failback(self, source: str, failed_target: str, reason: str) -> None:
        gate = ActiveSlotGate(self.shared, source)
        gate.switch(source, updated_by="cutover_automatic_failback")
        self.write_audit(
            "failback_started",
            source_slot=source,
            failed_target=failed_target,
            failback_reason=reason,
        )
        self.wait_transition(failed_target, source)
        self.write_audit(
            "failed_back",
            active_slot=source,
            failed_target=failed_target,
            failback_reason=reason,
            failed_back_at=self.now(),
        )

    def cutover(self, target: str) -> None:
        gate = ActiveSlotGate(self.shared, "blue")
        source = gate.active_slot()
        if target == source:
            raise CutoverError(f"Slot {target} sudah aktif.")
        self.validate_ready(source)
        self.validate_ready(target)
        self.write_audit("preflight", source_slot=source, target_slot=target, started_at=self.now())
        gate.switch(target, updated_by="cutover_manager")
        self.write_audit("slot_switched", source_slot=source, target_slot=target)
        try:
            self.wait_transition(source, target)
            self.stabilize(source, target)
        except Exception as exc:
            self.write_audit("cutover_failed", error=str(exc))
            try:
                self.failback(source, target, str(exc))
            except Exception as failback_exc:
                self.write_audit(
                    "failback_failed",
                    error=str(exc),
                    failback_error=str(failback_exc),
                )
                raise CutoverError(
                    f"Cutover gagal ({exc}); failback juga gagal ({failback_exc})"
                ) from failback_exc
            raise CutoverError(
                f"Cutover gagal; automatic failback ke {source} berhasil: {exc}"
            ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled Blue/Green cutover and drain")
    parser.add_argument("--root", default="~/SOC-Automation")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--target", choices=("blue", "green"), required=True)
    parser.add_argument("--stabilization", type=float, default=180.0)
    args = parser.parse_args()
    manager = CutoverManager(Path(args.root), timeout=args.timeout, stabilization=max(0.0, args.stabilization))
    try:
        manager.acquire()
        manager.cutover(args.target)
        print(f"Cutover selesai. Active slot: {args.target}")
        return 0
    except (CutoverError, OSError, ValueError) as exc:
        print(f"CUTOVER ERROR: {exc}", file=__import__('sys').stderr)
        return 1
    finally:
        manager.release()


if __name__ == "__main__":
    raise SystemExit(main())
