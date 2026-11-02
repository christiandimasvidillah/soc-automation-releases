#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CleanupReport:
    removed_files: list[str]
    removed_dirs: list[str]
    reclaimed_bytes: int = 0


def _size(path: Path) -> int:
    try:
        if path.is_file() or path.is_symlink():
            return path.stat().st_size
        return sum(item.stat().st_size for item in path.rglob('*') if item.is_file())
    except OSError:
        return 0


def _remove(path: Path, report: CleanupReport, dry_run: bool) -> None:
    size = _size(path)
    if path.is_dir() and not path.is_symlink():
        report.removed_dirs.append(str(path))
        if not dry_run:
            shutil.rmtree(path, ignore_errors=True)
    else:
        report.removed_files.append(str(path))
        if not dry_run:
            path.unlink(missing_ok=True)
    report.reclaimed_bytes += size


def cleanup(root: Path, *, keep_applied: int = 3, keep_failed: int = 3,
            max_age_days: int = 30, dry_run: bool = False) -> CleanupReport:
    root = root.expanduser().resolve()
    report = CleanupReport([], [])
    updates = root / 'updates'
    now = time.time()
    max_age = max_age_days * 86400

    # Incoming ZIP yang sukses seharusnya sudah dipindah oleh release manager.
    # Hanya bersihkan artefak temporary/partial yang bukan paket valid operator.
    for pattern in ('*.tmp', '*.part', '.*.tmp'):
        for path in (updates / 'incoming').glob(pattern):
            _remove(path, report, dry_run)

    for folder_name, keep in (('applied', keep_applied), ('failed', keep_failed)):
        folder = updates / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        archives = sorted(
            [p for p in folder.iterdir() if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for index, path in enumerate(archives):
            age = now - path.stat().st_mtime
            if index >= keep or age > max_age:
                _remove(path, report, dry_run)

    # Staging release sisa akibat process/device mati mendadak.
    releases = root / 'releases'
    for path in releases.glob('.*.staging'):
        _remove(path, report, dry_run)

    # Cache Python aman dibangun ulang; jangan sentuh shared database/log/env.
    for base in (root / 'manager', root / 'current'):
        if base.exists():
            for path in base.rglob('__pycache__'):
                _remove(path, report, dry_run)
            for path in base.rglob('*.pyc'):
                if path.exists():
                    _remove(path, report, dry_run)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='SOC Automation safe artifact cleanup')
    parser.add_argument('--root', default='~/SOC-Automation')
    parser.add_argument('--keep-applied', type=int, default=3)
    parser.add_argument('--keep-failed', type=int, default=3)
    parser.add_argument('--max-age-days', type=int, default=30)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    report = cleanup(
        Path(args.root), keep_applied=max(0, args.keep_applied),
        keep_failed=max(0, args.keep_failed), max_age_days=max(1, args.max_age_days),
        dry_run=args.dry_run,
    )
    print(json.dumps({**asdict(report), 'dry_run': args.dry_run}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
