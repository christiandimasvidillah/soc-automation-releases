from pathlib import Path
import json
import os
import sys
import tempfile
import types
import hashlib

stub = types.ModuleType("data_sanitizer")
stub.generate_hash = lambda value: hashlib.sha256(str(value).encode()).hexdigest()
stub.log_audit_mapping = lambda *args, **kwargs: None
stub.save_json_comparison = lambda *args, **kwargs: None
sys.modules.setdefault("data_sanitizer", stub)

from output_privacy import sanitize_ai_output
from privacy_manager import PrivacyManager
from soc_status import SCHEMA_VERSION, snapshot

blob = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURSBSRVFVRVNULS0tLS0K" * 20
payload = {
    "gcp": {"audit": {
        "request": {"spec": {"request": blob}},
        "response": {"spec": {"request": blob}},
    }}
}
result = PrivacyManager().prepare_payload(
    ticket_key="TEST-CSR-REDACTION",
    raw_json=json.dumps(payload),
)
parsed = json.loads(result.sanitized_json)
request_value = parsed["gcp"]["audit"]["request"]["spec"]["request"]
response_value = parsed["gcp"]["audit"]["response"]["spec"]["request"]
allowed = {
    "[REDACTED_CERTIFICATE_OR_ATTESTATION_BLOB]",
    "[REDACTED_SENSITIVE_BLOB]",
}
assert blob not in result.sanitized_json
assert request_value in allowed
assert response_value in allowed
assert result.safe_for_ai is True
assert result.residual_count == 0

safe = sanitize_ai_output(
    "Authorized action by USER_abc from IP_deadbeef in CLUSTER_xyz is a False Positive."
)
assert safe.safe is True and safe.withheld is False
assert not any(token in safe.text for token in ("USER_", "IP_", "CLUSTER_"))
blocked = sanitize_ai_output(
    "-----BEGIN CERTIFICATE REQUEST----- ABC -----END CERTIFICATE REQUEST-----"
)
assert blocked.withheld is True and blocked.safe is False

with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    (root / "current").mkdir()
    (root / "shared" / "workers" / "blue").mkdir(parents=True)
    (root / "shared" / "workers" / "green").mkdir(parents=True)
    (root / "current" / "VERSION").write_text("5.1.3", encoding="utf-8")
    (root / "shared" / "master.json").write_text(
        json.dumps({
            "master_pid": os.getpid(),
            "status": "running",
            "target_version": "5.1.3",
        }),
        encoding="utf-8",
    )
    state = snapshot(root)
    assert SCHEMA_VERSION == 2
    assert state.get("schema_version") == SCHEMA_VERSION
    assert state["master"]["pid"] == os.getpid()
    assert state["master"]["alive"] is True
    assert state["master"]["version"] == "5.1.3"
    assert state["master"]["display_status"] == "running"

print("v5.1.3 schema, privacy, and viewer regression tests: OK")
