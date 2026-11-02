#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

from cleanup_manager import cleanup
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DeploymentError(RuntimeError):
    pass


class TransactionalDeployer:
    def __init__(self, root: Path, *, timeout: float = 300.0) -> None:
        self.root = root.expanduser().resolve()
        self.manager = self.root / "manager"
        self.shared = self.root / "shared"
        self.state_file = self.shared / "deployment.json"
        self.lock_file = self.shared / "deployment.lock"
        self.release_manager = self.manager / "local_release_manager.py"
        self.socctl = self.manager / "socctl.py"
        self.timeout = timeout
        self.transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{os.getpid()}"
        self.previous_version: str | None = None
        self.target_version: str | None = None
        self.package: Path | None = None
        self.package_sha256: str | None = None
        self.rollback_performed = False

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
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def atomic_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    def current_version(self) -> str:
        try:
            return (self.root / "current" / "VERSION").read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise DeploymentError(f"Tidak dapat membaca current/VERSION: {exc}") from exc

    def acquire(self) -> None:
        self.shared.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            lock = self.read_json(self.lock_file)
            raise DeploymentError(f"Deployment lain masih terkunci: {lock or self.lock_file}") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"transaction_id": self.transaction_id, "pid": os.getpid(), "started_at": self.now()}, handle, indent=2)
            handle.write("\n")

    def release(self) -> None:
        try:
            self.lock_file.unlink()
        except FileNotFoundError:
            pass

    def write_state(self, status: str, **extra: Any) -> None:
        payload = {
            "transaction_id": self.transaction_id,
            "status": status,
            "updated_at": self.now(),
            "package": str(self.package) if self.package else None,
            "package_sha256": self.package_sha256,
            "previous_version": self.previous_version,
            "target_version": self.target_version,
            "rollback_performed": self.rollback_performed,
        }
        payload.update(extra)
        self.atomic_json(self.state_file, payload)

    def run_command(self, command: list[str], *, stage: str) -> subprocess.CompletedProcess[str]:
        self.write_state(stage, command=command)
        result = subprocess.run(command, text=True, capture_output=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "unknown error").strip()
            raise DeploymentError(f"Stage {stage} gagal: {detail}")
        return result

    def master_ready(self) -> bool:
        master = self.read_json(self.shared / "master.json")
        master_pid = self.read_json(self.shared / "soc_master.pid").get("pid")
        return isinstance(master_pid, int) and master.get("status") in {"running", "worker_stale"}

    def validate_runtime(self, expected_version: str, *, timeout: float | None = None) -> None:
        deadline = time.monotonic() + (timeout or self.timeout)
        while time.monotonic() < deadline:
            master = self.read_json(self.shared / "master.json")
            active_slot = str(master.get("active_slot") or "blue")
            worker_dir = self.shared / "workers" / active_slot
            health = self.read_json(worker_dir / "health.json")
            worker_pid = self.read_json(worker_dir / "pid.json").get("pid")
            if (
                master.get("status") == "running"
                and master.get("target_version") == expected_version
                and master.get("worker_health_state") == "healthy"
                and health.get("status") == "healthy"
                and health.get("version") == expected_version
                and isinstance(worker_pid, int)
                and health.get("pid") == worker_pid
            ):
                self.write_state("runtime_validated", worker_pid=worker_pid)
                return
            if master.get("status") in {"failed", "worker_crash_loop"}:
                raise DeploymentError(f"Master melaporkan status {master.get('status')} saat validasi.")
            time.sleep(0.5)
        raise DeploymentError(f"Runtime {expected_version} tidak healthy dalam {timeout or self.timeout:.0f} detik.")

    def restart_worker(self, *, stage: str) -> None:
        self.run_command(
            [sys.executable, str(self.socctl), "--root", str(self.root), "restart", "--timeout", str(self.timeout)],
            stage=stage,
        )

    def rollback(self) -> None:
        if not self.previous_version:
            raise DeploymentError("Previous version tidak tersedia untuk rollback.")
        self.write_state("rollback_started")
        self.run_command(
            [sys.executable, str(self.release_manager), "--root", str(self.root), "rollback", "--to", self.previous_version],
            stage="rollback_release",
        )
        self.rollback_performed = True
        self.restart_worker(stage="rollback_restart")
        self.validate_runtime(self.previous_version, timeout=self.timeout)
        cleanup_report = cleanup(
            self.root,
            keep_applied=3,
            keep_failed=3,
            max_age_days=30,
        )
        self.write_state(
            "rolled_back",
            recovered_version=self.previous_version,
            cleanup_reclaimed_bytes=cleanup_report.reclaimed_bytes,
        )

    def deploy(self, package: Path, *, force: bool = False, keep: int = 5, auto_rollback: bool = True) -> None:
        self.package = package.expanduser().resolve()
        if not self.package.is_file():
            raise DeploymentError(f"Package tidak ditemukan: {self.package}")
        if not self.release_manager.is_file() or not self.socctl.is_file():
            raise DeploymentError("Manager belum lengkap: local_release_manager.py atau socctl.py tidak ditemukan.")
        if not self.master_ready():
            raise DeploymentError("SocMaster harus aktif dan running sebelum transactional deploy.")
        self.package_sha256 = self.sha256(self.package)
        self.previous_version = self.current_version()
        self.write_state("preflight")

        dry = [sys.executable, str(self.release_manager), "--root", str(self.root), "apply", "--package", str(self.package), "--dry-run", "--keep", str(keep)]
        apply = [sys.executable, str(self.release_manager), "--root", str(self.root), "apply", "--package", str(self.package), "--keep", str(keep)]
        if force:
            dry.append("--force")
            apply.append("--force")
        self.run_command(dry, stage="dry_run")

        try:
            self.run_command(apply, stage="apply_release")
            self.target_version = self.current_version()
            if self.target_version == self.previous_version:
                raise DeploymentError("Apply selesai tetapi current version tidak berubah.")
            self.write_state("release_switched")
            self.restart_worker(stage="restart_new_release")
            self.validate_runtime(self.target_version)
            cleanup_report = cleanup(
                self.root,
                keep_applied=3,
                keep_failed=3,
                max_age_days=30,
            )
            self.write_state(
                "committed",
                committed_at=self.now(),
                cleanup_removed_files=len(cleanup_report.removed_files),
                cleanup_removed_dirs=len(cleanup_report.removed_dirs),
                cleanup_reclaimed_bytes=cleanup_report.reclaimed_bytes,
            )
        except Exception as deploy_error:
            self.write_state("deployment_failed", error=str(deploy_error))
            if auto_rollback and self.current_version() != self.previous_version:
                try:
                    self.rollback()
                except Exception as rollback_error:
                    self.write_state(
                        "rollback_failed",
                        deployment_error=str(deploy_error),
                        rollback_error=str(rollback_error),
                    )
                    raise DeploymentError(
                        f"Deploy gagal ({deploy_error}); rollback juga gagal ({rollback_error})."
                    ) from rollback_error
                raise DeploymentError(
                    f"Deploy gagal dan rollback otomatis berhasil: {deploy_error}"
                ) from deploy_error
            raise


def command_deploy(args: argparse.Namespace) -> None:
    deployer = TransactionalDeployer(Path(args.root), timeout=args.timeout)
    deployer.acquire()
    try:
        deployer.deploy(
            Path(args.package),
            force=args.force,
            keep=args.keep,
            auto_rollback=not args.no_auto_rollback,
        )
        print(
            f"Deployment committed: {deployer.previous_version} -> {deployer.target_version}\n"
            f"Transaction: {deployer.transaction_id}"
        )
    finally:
        deployer.release()


def command_status(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    state = TransactionalDeployer.read_json(root / "shared" / "deployment.json")
    print(json.dumps(state, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transactional deployment orchestrator")
    parser.add_argument("--root", default="~/SOC-Automation")
    sub = parser.add_subparsers(dest="command", required=True)
    deploy = sub.add_parser("deploy", help="Dry-run, apply, restart, validate, dan rollback otomatis")
    deploy.add_argument("--package", required=True)
    deploy.add_argument("--timeout", type=float, default=300.0)
    deploy.add_argument("--keep", type=int, default=5)
    deploy.add_argument("--force", action="store_true")
    deploy.add_argument("--no-auto-rollback", action="store_true")
    deploy.set_defaults(func=command_deploy)
    status = sub.add_parser("status", help="Tampilkan transaksi deployment terakhir")
    status.set_defaults(func=command_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except (DeploymentError, OSError, subprocess.SubprocessError) as exc:
        print(f"DEPLOY ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
