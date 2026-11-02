#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_NAME = "SOC Jira Automation"
DEFAULT_KEEP_RELEASES = 5
PERSISTENT_NAMES = {".env", "logs", "audit_logs", "automation.out", "soc_automation.pid"}
EXCLUDED_COPY_NAMES = {
    ".git", ".venv", "venv", "__pycache__", ".release-backups",
    "updates", "releases", "shared", "current",
}


class ReleaseError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"Gagal membaca JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"JSON {path} harus berupa object.")
    return value


SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def safe_version(value: str) -> str:
    normalized = value.strip().lstrip("v")
    if not SEMVER_RE.fullmatch(normalized):
        raise ReleaseError(f"Versi tidak valid: {value!r}")
    return normalized


def version_tuple(value: str) -> tuple[Any, ...]:
    normalized = safe_version(value)
    match = SEMVER_RE.fullmatch(normalized)
    assert match is not None
    core = tuple(int(match.group(name)) for name in ("major", "minor", "patch"))
    pre = match.group("pre")
    if pre is None:
        return (*core, 1, ())
    identifiers: list[tuple[int, Any]] = []
    for item in pre.split("."):
        identifiers.append((0, int(item)) if item.isdigit() else (1, item))
    return (*core, 0, tuple(identifiers))


def ensure_layout(root: Path) -> None:
    for path in (
        root / "releases",
        root / "updates" / "incoming",
        root / "updates" / "applied",
        root / "updates" / "failed",
        root / "shared" / "logs",
        root / "shared" / "audit_logs",
    ):
        path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(root, 0o700)
        os.chmod(root / "shared", 0o700)
    except OSError:
        pass


def current_target(root: Path) -> Path | None:
    current = root / "current"
    if not current.exists() and not current.is_symlink():
        return None
    try:
        return current.resolve(strict=True)
    except OSError as exc:
        raise ReleaseError(f"Symlink current rusak: {exc}") from exc


def current_version(root: Path) -> str | None:
    target = current_target(root)
    if target is None:
        return None
    version_file = target / "VERSION"
    if not version_file.exists():
        raise ReleaseError(f"VERSION tidak ditemukan pada {target}")
    return version_file.read_text(encoding="utf-8").strip()


def ignore_copy(directory: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in EXCLUDED_COPY_NAMES or name in PERSISTENT_NAMES:
            ignored.add(name)
        elif name.endswith((".pyc", ".zip", ".tmp")):
            ignored.add(name)
    return ignored


def copy_source(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise ReleaseError(f"Source bukan folder: {source}")
    shutil.copytree(source, destination, ignore=ignore_copy)


def replace_path_with_symlink(path: Path, target: Path) -> None:
    if path.is_symlink() or path.exists():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    relative_target = os.path.relpath(target, path.parent)
    path.symlink_to(relative_target, target_is_directory=target.is_dir())


def attach_shared(root: Path, release: Path) -> None:
    shared = root / "shared"
    env_file = shared / ".env"
    if not env_file.exists():
        raise ReleaseError(f"Credential lokal belum tersedia: {env_file}")
    replace_path_with_symlink(release / ".env", env_file)
    replace_path_with_symlink(release / "logs", shared / "logs")
    replace_path_with_symlink(release / "audit_logs", shared / "audit_logs")


def atomic_switch(root: Path, release: Path) -> None:
    current = root / "current"
    temporary = root / ".current.new"
    if temporary.exists() or temporary.is_symlink():
        temporary.unlink()
    relative_target = os.path.relpath(release, root)
    temporary.symlink_to(relative_target, target_is_directory=True)
    os.replace(temporary, current)


def run_checks(release: Path) -> None:
    py_files = sorted(path.name for path in release.glob("*.py"))
    if not py_files:
        raise ReleaseError("Release tidak memiliki file Python.")
    print("  - syntax check")
    compile_result = subprocess.run(
        [sys.executable, "-m", "py_compile", *py_files],
        cwd=release,
        text=True,
        capture_output=True,
    )
    if compile_result.returncode != 0:
        raise ReleaseError(
            "Syntax check gagal:\n" + (compile_result.stderr or compile_result.stdout)
        )

    test_file = release / "tests" / "test_privacy_manager.py"
    if test_file.exists():
        print("  - privacy regression test")
        test_result = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=release,
            text=True,
            capture_output=True,
        )
        if test_result.returncode != 0:
            raise ReleaseError(
                "Privacy test gagal:\n" + (test_result.stderr or test_result.stdout)
            )


def write_release_metadata(
    release: Path,
    *,
    version: str,
    previous_version: str | None,
    package_hash: str | None,
    description: str,
) -> None:
    (release / "VERSION").write_text(version + "\n", encoding="utf-8")
    metadata = {
        "application": APP_NAME,
        "version": version,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "previous_version": previous_version,
        "package_sha256": package_hash,
        "status": "active",
        "description": description,
    }
    (release / "RELEASE.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def prune_releases(root: Path, keep: int) -> None:
    active = current_target(root)
    releases = sorted(
        [path for path in (root / "releases").iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    retained = 0
    for release in releases:
        if active and release.resolve() == active.resolve():
            continue
        retained += 1
        if retained >= keep:
            shutil.rmtree(release, ignore_errors=True)


def command_init(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    source = Path(args.source).expanduser().resolve()
    version = safe_version(args.version)
    ensure_layout(root)
    if current_target(root) is not None:
        raise ReleaseError("Local Release Manager sudah diinisialisasi.")

    shared_env = root / "shared" / ".env"
    source_env = source / ".env"
    if not shared_env.exists():
        if not source_env.exists():
            raise ReleaseError(".env tidak ditemukan pada source.")
        shutil.copy2(source_env, shared_env)
        try:
            os.chmod(shared_env, 0o600)
        except OSError:
            pass

    release = root / "releases" / f"v{version}"
    if release.exists():
        raise ReleaseError(f"Release sudah ada: {release}")
    copy_source(source, release)
    attach_shared(root, release)
    write_release_metadata(
        release,
        version=version,
        previous_version=None,
        package_hash=None,
        description="Initial local release import",
    )
    run_checks(release)
    atomic_switch(root, release)
    print(f"Init berhasil. current -> {release}")
    print(f"Credential lokal: {shared_env}")


def validate_zip_members(archive: zipfile.ZipFile) -> None:
    for member in archive.infolist():
        path = Path(member.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ReleaseError(f"Path tidak aman dalam ZIP: {member.filename}")
        if member.is_dir():
            continue
        if member.external_attr >> 16 & 0o170000 == 0o120000:
            raise ReleaseError(f"Symlink tidak diizinkan dalam paket: {member.filename}")


def locate_manifest(extracted: Path) -> Path:
    direct = extracted / "manifest.json"
    if direct.exists():
        return direct
    candidates = list(extracted.glob("*/manifest.json"))
    if len(candidates) == 1:
        return candidates[0]
    raise ReleaseError("manifest.json tidak ditemukan atau ambigu.")


def verify_manifest_files(package_root: Path, manifest: dict[str, Any]) -> list[Path]:
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ReleaseError("manifest.files harus berupa object non-kosong.")
    verified: list[Path] = []
    for relative_name, metadata in files.items():
        relative = Path(relative_name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ReleaseError(f"Path manifest tidak aman: {relative_name}")
        if relative_name in PERSISTENT_NAMES or relative.parts[0] in PERSISTENT_NAMES:
            raise ReleaseError(f"Paket tidak boleh mengganti data persistent: {relative_name}")
        source = package_root / relative
        if not source.is_file():
            raise ReleaseError(f"File paket tidak ditemukan: {relative_name}")
        if not isinstance(metadata, dict) or "sha256" not in metadata:
            raise ReleaseError(f"SHA-256 tidak tersedia: {relative_name}")
        actual = sha256_file(source)
        expected = str(metadata["sha256"]).lower()
        if actual != expected:
            raise ReleaseError(
                f"Hash file tidak cocok: {relative_name}\nExpected: {expected}\nActual:   {actual}"
            )
        verified.append(relative)
    return verified


def move_package(package: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / package.name
    if destination.exists():
        destination = destination_dir / (
            f"{package.stem}-{datetime.now():%Y%m%d-%H%M%S}{package.suffix}"
        )
    shutil.move(str(package), destination)


def command_apply(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    package = Path(args.package).expanduser().resolve()
    ensure_layout(root)
    active = current_target(root)
    if active is None:
        raise ReleaseError("Belum ada release aktif. Jalankan init dahulu.")
    if not package.is_file():
        raise ReleaseError(f"Paket tidak ditemukan: {package}")

    old_version = current_version(root)
    package_hash = sha256_file(package)
    staging: Path | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="soc-update-") as temp_name:
            temp = Path(temp_name)
            with zipfile.ZipFile(package) as archive:
                validate_zip_members(archive)
                archive.extractall(temp)
            manifest_path = locate_manifest(temp)
            package_root = manifest_path.parent
            manifest = read_json(manifest_path)

            if manifest.get("application") != APP_NAME:
                raise ReleaseError("Paket bukan untuk SOC Jira Automation.")
            new_version = safe_version(str(manifest.get("version", "")))
            minimum = safe_version(str(manifest.get("minimum_version", old_version)))
            if version_tuple(old_version) < version_tuple(minimum):
                raise ReleaseError(
                    f"Versi aktif {old_version} lebih lama dari minimum {minimum}."
                )
            if version_tuple(new_version) <= version_tuple(old_version) and not args.force:
                raise ReleaseError(
                    f"Versi update {new_version} tidak lebih baru dari {old_version}."
                )
            files = verify_manifest_files(package_root, manifest)

            print(f"Update {old_version} -> {new_version}")
            print(f"Package SHA-256: {package_hash}")
            for relative in files:
                print(f"  - {relative}")
            if args.dry_run:
                print("Dry-run berhasil; tidak ada file yang diubah.")
                return

            final_release = root / "releases" / f"v{new_version}"
            staging = root / "releases" / f".v{new_version}.staging"
            if final_release.exists() or staging.exists():
                raise ReleaseError(f"Release target sudah ada: v{new_version}")
            shutil.copytree(active, staging, symlinks=True)
            for relative in files:
                source = package_root / relative
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

            attach_shared(root, staging)
            write_release_metadata(
                staging,
                version=new_version,
                previous_version=old_version,
                package_hash=package_hash,
                description=str(manifest.get("description", "Local patch update")),
            )
            run_checks(staging)
            staging.rename(final_release)
            staging = None
            attach_shared(root, final_release)
            atomic_switch(root, final_release)
            move_package(package, root / "updates" / "applied")
            prune_releases(root, args.keep)
            print(f"Update berhasil. current -> {final_release}")
            print("Restart aplikasi agar module baru dimuat.")
    except Exception:
        if staging and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if package.exists() and not args.dry_run:
            move_package(package, root / "updates" / "failed")
        raise


def command_status(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    ensure_layout(root)
    target = current_target(root)
    print(f"Root    : {root}")
    print(f"Current : {target or '-'}")
    print(f"Version : {current_version(root) or '-'}")
    if target and (target / "RELEASE.json").exists():
        print((target / "RELEASE.json").read_text(encoding="utf-8"))
    health_file = root / "shared" / "health.json"
    pid_file = root / "shared" / "soc_automation.pid"
    health = read_json(health_file) if health_file.exists() else {}
    pid_data = read_json(pid_file) if pid_file.exists() else {}
    runtime_pid = pid_data.get("pid") or health.get("pid") or "-"
    print("Runtime :")
    print(f"  PID              : {runtime_pid}")
    print(f"  Health           : {health.get('status', '-')}")
    print(f"  Runtime version  : {health.get('version', '-')}")
    print(f"  Last heartbeat   : {health.get('last_heartbeat', '-')}")
    print(f"  Last poll        : {health.get('last_poll_finished', '-')}")
    print(f"  Poll cycle       : {health.get('poll_cycle', '-')}")
    print(f"  Submitted        : {health.get('tickets_submitted', '-')}")
    print(f"  Completed        : {health.get('tickets_completed', '-')}")
    print(f"  Failed           : {health.get('tickets_failed', '-')}")
    print(f"  Pending workers  : {health.get('pending_workers', '-')}")
    print(f"  In flight        : {health.get('in_flight', '-')}")
    incoming = sorted((root / "updates" / "incoming").glob("*.zip"))
    print(f"Incoming updates: {len(incoming)}")
    for item in incoming:
        print(f"  - {item.name}")


def command_rollback(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    active = current_target(root)
    if active is None:
        raise ReleaseError("Tidak ada release aktif.")
    if args.to:
        target = root / "releases" / f"v{safe_version(args.to)}"
    else:
        metadata = read_json(active / "RELEASE.json")
        previous = metadata.get("previous_version")
        if not previous:
            raise ReleaseError("Release aktif tidak memiliki previous_version.")
        target = root / "releases" / f"v{safe_version(str(previous))}"
    if not target.is_dir():
        raise ReleaseError(f"Release rollback tidak ditemukan: {target}")
    attach_shared(root, target)
    run_checks(target)
    atomic_switch(root, target)
    print(f"Rollback berhasil. current -> {target}")
    print("Restart aplikasi agar versi rollback dimuat.")



def command_stop(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    pid_file = root / "shared" / "soc_automation.pid"
    if not pid_file.exists():
        raise ReleaseError("PID file tidak ditemukan; worker mungkin tidak aktif.")
    pid_data = read_json(pid_file)
    pid = pid_data.get("pid")
    if not isinstance(pid, int) or pid < 2:
        raise ReleaseError("PID file tidak valid.")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError as exc:
        raise ReleaseError(f"Process PID {pid} tidak ditemukan.") from exc
    print(f"SIGTERM dikirim ke PID {pid}. Menunggu graceful shutdown...")
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            print("Worker berhenti dengan graceful.")
            return
        time.sleep(0.5)
    raise ReleaseError(
        f"Worker PID {pid} belum berhenti setelah {args.timeout} detik. "
        "Periksa worker yang masih memproses tiket."
    )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Release Manager untuk SOC Automation")
    parser.add_argument(
        "--root",
        default="~/SOC-Automation",
        help="Root release manager (default: ~/SOC-Automation)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Migrasikan instalasi aktif menjadi release pertama")
    init.add_argument("--source", required=True)
    init.add_argument("--version", required=True)
    init.set_defaults(func=command_init)

    apply = sub.add_parser("apply", help="Terapkan patch ZIP lokal")
    apply.add_argument("--package", required=True)
    apply.add_argument("--dry-run", action="store_true")
    apply.add_argument("--force", action="store_true")
    apply.add_argument("--keep", type=int, default=DEFAULT_KEEP_RELEASES)
    apply.set_defaults(func=command_apply)

    status = sub.add_parser("status", help="Tampilkan status release")
    status.set_defaults(func=command_status)

    rollback = sub.add_parser("rollback", help="Rollback ke previous atau versi tertentu")
    rollback.add_argument("--to")
    rollback.set_defaults(func=command_rollback)

    stop = sub.add_parser("stop", help="Kirim SIGTERM dan tunggu graceful shutdown")
    stop.add_argument("--timeout", type=float, default=120.0)
    stop.set_defaults(func=command_stop)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except (ReleaseError, OSError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
