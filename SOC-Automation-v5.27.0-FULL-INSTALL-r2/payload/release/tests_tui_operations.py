import json
import tempfile
import zipfile
from pathlib import Path
from tui_audit_browser import AuditBrowser, AuditError
from tui_update_manager import UpdateService, UpdateError

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "updates" / "incoming").mkdir(parents=True)
    (root / "manager").mkdir()
    patch = root / "external-patch.zip"
    manifest = {"version":"9.9.9","minimum_version":"5.2.0","description":"test","files":{"VERSION":{"sha256":"0"*64,"required":True}}}
    with zipfile.ZipFile(patch, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
    service = UpdateService(root)
    info = service.inspect(patch)
    assert info["version"] == "9.9.9"
    assert len(info["sha256"]) == 64
    Path(str(patch) + ".sha256").write_text(info["sha256"] + "  " + patch.name + "\n")
    assert service.inspect(patch)["checksum_sidecar"]["verified"] is True

    audit_dir = root / "shared" / "audit_logs"
    audit_dir.mkdir(parents=True)
    audit = audit_dir / "CSOC-1_sanitized.json"
    blob = "A" * 600
    audit.write_text(json.dumps({"event":{"action":"create"},"gcp":{"audit":{"request":{"spec":{"request":blob}}}},"user":"USER_test","escape":"\u001b[31mred"}))
    browser = AuditBrowser(root)
    files = browser.files("CSOC-1")
    assert files == [audit]
    preview = browser.preview(audit)["content"]
    assert blob not in preview
    assert "REDACTED_IN_TUI_PREVIEW" in preview
    assert "\u001b" not in preview and "\x1b" not in preview
    outside = root / "outside.json"; outside.write_text("{}")
    try:
        browser.preview(outside)
        raise AssertionError("outside path accepted")
    except AuditError:
        pass

print("v5.3.0 TUI update-path and audit-browser tests: OK")
