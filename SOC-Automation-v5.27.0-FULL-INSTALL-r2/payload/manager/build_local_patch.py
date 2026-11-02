#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

APP_NAME = "SOC Jira Automation"
FORBIDDEN = {".env", "logs", "audit_logs", "automation.out", "soc_automation.pid"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local SOC patch package")
    parser.add_argument("--source", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--minimum-version", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    selected: list[Path] = []
    for name in args.files:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise SystemExit(f"Path tidak aman: {name}")
        if relative.parts[0] in FORBIDDEN:
            raise SystemExit(f"Data persistent tidak boleh masuk patch: {name}")
        path = source / relative
        if not path.is_file():
            raise SystemExit(f"File tidak ditemukan: {path}")
        selected.append(relative)

    manifest = {
        "application": APP_NAME,
        "version": args.version.lstrip("v"),
        "minimum_version": args.minimum_version.lstrip("v"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": args.description,
        "restart_required": True,
        "files": {
            str(relative): {
                "sha256": sha256_file(source / relative),
                "required": True,
            }
            for relative in selected
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="soc-patch-") as temp_name:
        temp = Path(temp_name)
        for relative in selected:
            destination = temp / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, destination)
        (temp / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(temp.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(temp))

    checksum = sha256_file(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{checksum}  {output.name}\n",
        encoding="utf-8",
    )
    print(f"Patch: {output}")
    print(f"SHA-256: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
