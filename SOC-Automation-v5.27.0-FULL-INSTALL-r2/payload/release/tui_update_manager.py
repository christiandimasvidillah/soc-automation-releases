from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

class UpdateError(RuntimeError):
    pass

_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9._-]+)?$")

class UpdateService:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.incoming = self.root / "updates" / "incoming"
        self.manager = self.root / "manager"

    def packages(self):
        self.incoming.mkdir(parents=True, exist_ok=True)
        return sorted(self.incoming.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)

    def resolve_user_path(self, value):
        raw = str(value or "").strip()
        if not raw:
            raise UpdateError("Path patch tidak boleh kosong.")
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            raise UpdateError(f"File patch tidak ditemukan: {path}")
        if path.suffix.lower() != ".zip":
            raise UpdateError("Patch harus berupa file ZIP.")
        return path

    def _verify_sidecar(self, path, digest):
        candidates = [Path(str(path) + ".sha256"), path.with_suffix(path.suffix + ".sha256")]
        sidecar = next((candidate for candidate in candidates if candidate.is_file()), None)
        if sidecar is None:
            return {"present": False, "verified": False, "path": None}
        expected = sidecar.read_text(encoding="utf-8", errors="replace").strip().split()[0].lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise UpdateError(f"Format checksum tidak valid: {sidecar}")
        if expected != digest:
            raise UpdateError("Checksum SHA-256 patch tidak cocok dengan sidecar.")
        return {"present": True, "verified": True, "path": str(sidecar)}

    def inspect(self, value):
        path = self.resolve_user_path(value)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    raise UpdateError(f"ZIP rusak pada entry: {bad}")
                manifest = json.loads(archive.read("manifest.json"))
        except UpdateError:
            raise
        except Exception as exc:
            raise UpdateError(f"Manifest/ZIP tidak valid: {exc}") from exc
        version = str(manifest.get("version") or "")
        minimum = str(manifest.get("minimum_version") or "")
        if not _VERSION.fullmatch(version):
            raise UpdateError("Versi pada manifest tidak valid.")
        if minimum and not _VERSION.fullmatch(minimum):
            raise UpdateError("minimum_version pada manifest tidak valid.")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise UpdateError("Manifest tidak memiliki daftar file yang valid.")
        checksum = self._verify_sidecar(path, digest)
        return {
            "path": str(path), "name": path.name, "size": path.stat().st_size,
            "sha256": digest, "checksum_sidecar": checksum,
            "version": version, "minimum_version": minimum or None,
            "description": manifest.get("description"),
            "restart_required": bool(manifest.get("restart_required")),
            "file_count": len(files),
        }

    def run(self, args, timeout=420):
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
        return result.returncode, (result.stdout + "\n" + result.stderr).strip()

    def dry_run(self, path):
        return self.run([sys.executable, str(self.manager / "local_release_manager.py"), "--root", str(self.root), "apply", "--package", str(path), "--dry-run"])

    def deploy(self, path):
        return self.run([sys.executable, str(self.manager / "deploy_manager.py"), "--root", str(self.root), "deploy", "--package", str(path), "--timeout", "300"])

    def status(self):
        return self.run([sys.executable, str(self.manager / "deploy_manager.py"), "--root", str(self.root), "status"])
