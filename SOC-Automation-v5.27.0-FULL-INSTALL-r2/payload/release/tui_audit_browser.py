from __future__ import annotations
import json
import re
from pathlib import Path

class AuditError(RuntimeError):
    pass

_ESCAPE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]|\x1b\[[0-?]*[ -/]*[@-~]")
_SENSITIVE_KEY = re.compile(r"(?:private[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|password|authorization|credential-id|spec\.request|certificate|attestation|vm[_-]?identity)", re.I)
_ENCODED = re.compile(r"^[A-Za-z0-9+/=\s]{256,}$")

class AuditBrowser:
    def __init__(self, root, max_size=5 * 1024 * 1024):
        self.root = Path(root).expanduser().resolve()
        self.audit_dir = (self.root / "shared" / "audit_logs").resolve()
        self.max_size = max_size

    def files(self, query=""):
        if not self.audit_dir.is_dir():
            return []
        needle = query.strip().lower()
        values = []
        for path in self.audit_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in {".json", ".log", ".txt"}:
                continue
            if needle and needle not in path.name.lower():
                continue
            values.append(path)
        return sorted(values, key=lambda path: path.stat().st_mtime, reverse=True)

    def resolve(self, value):
        path = Path(value).expanduser().resolve()
        try:
            path.relative_to(self.audit_dir)
        except ValueError as exc:
            raise AuditError("File audit harus berada di shared/audit_logs.") from exc
        if not path.is_file():
            raise AuditError("File audit tidak ditemukan.")
        if path.suffix.lower() not in {".json", ".log", ".txt"}:
            raise AuditError("Jenis file audit tidak didukung.")
        if path.stat().st_size > self.max_size:
            raise AuditError(f"File terlalu besar untuk TUI ({path.stat().st_size} bytes).")
        return path

    def _safe_scalar(self, key_path, value):
        if not isinstance(value, str):
            return value
        cleaned = _ESCAPE.sub("", value)
        if _SENSITIVE_KEY.search(key_path) or _ENCODED.fullmatch(cleaned.strip()):
            return "[REDACTED_IN_TUI_PREVIEW]"
        if len(cleaned) > 500:
            return cleaned[:500] + f" ... [TRUNCATED {len(cleaned) - 500} chars]"
        return cleaned

    def _sanitize(self, value, prefix=""):
        if isinstance(value, dict):
            return {str(key): self._sanitize(item, f"{prefix}.{key}" if prefix else str(key)) for key, item in value.items()}
        if isinstance(value, list):
            limit = 100
            result = [self._sanitize(item, f"{prefix}[]") for item in value[:limit]]
            if len(value) > limit:
                result.append(f"[TRUNCATED {len(value) - limit} list items]")
            return result
        return self._safe_scalar(prefix, value)

    def preview(self, value):
        path = self.resolve(value)
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            parsed = json.loads(text)
            safe = self._sanitize(parsed)
            rendered = json.dumps(safe, indent=2, ensure_ascii=False)
            kind = "json"
        except json.JSONDecodeError:
            rendered = _ESCAPE.sub("", text)
            if len(rendered) > 20000:
                rendered = rendered[:20000] + "\n[TRUNCATED FILE PREVIEW]"
            kind = "text"
        return {"path": str(path), "name": path.name, "size": path.stat().st_size, "kind": kind, "content": rendered}
