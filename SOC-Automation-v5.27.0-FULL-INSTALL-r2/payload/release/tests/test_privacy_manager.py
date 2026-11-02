from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

# Config memerlukan environment wajib. Nilai ini hanya untuk regression test lokal.
os.environ.setdefault("JIRA_EMAIL", "test@example.invalid")
os.environ.setdefault("JIRA_API_TOKEN", "test")
os.environ.setdefault("JIRA_ACCOUNT_ID", "test")
os.environ.setdefault("ELASTIC_API_KEY", "test")
os.environ.setdefault("GEMINI_API_KEY", "test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test")
os.environ.setdefault("HASH_SECRET_KEY", "local-regression-test-secret")
os.environ.setdefault("AUDIT_DIR", tempfile.mkdtemp(prefix="soc-privacy-test-"))

from privacy_manager import PrivacyManager

payload = {
    "hits": {"hits": [{
        "_index": ".internal.alerts-security.alerts-default-000026",
        "_id": "raw-alert-id",
        "_source": {
            "agent": {"id": "agent-raw-id"},
            "host": {"name": "server01", "id": "host-raw-id"},
            "event": {"id": "event-raw-id"},
            "kibana.alert.reason": "event on server01",
            "kibana.alert.ancestors": [{
                "id": "ancestor-raw-id",
                "index": ".ds-private-index",
            }],
            "registry": {
                "path": "HKLM\\SYSTEM\\ControlSet001\\Services\\x\\NetworkProvider\\ProviderPath",
                "data": {"strings": ["C:\\Windows\\System32\\sample.dll"]},
            },
            "network_path": "\\\\fileserver01\\finance\\report.csv",
            "source": {"ip": "10.20.30.40"},
            "user": {"name": "SYSTEM", "id": "S-1-5-18", "domain": "NT AUTHORITY"},
        },
    }]},
}

first = PrivacyManager().prepare_payload(
    ticket_key="LOCAL-RELEASE-TEST",
    raw_json=json.dumps(payload),
)
assert first.safe_for_ai and first.residual_count == 0, first.residual_categories
sanitized_first = json.loads(first.sanitized_json)
source_first = sanitized_first["hits"]["hits"][0]["_source"]
assert source_first["host"]["name"].startswith("HOST_")
assert source_first["kibana.alert.reason"] == (
    "event on " + source_first["host"]["name"]
)
for secret in (
    "server01", "host-raw-id", "agent-raw-id", "event-raw-id",
    "ancestor-raw-id", ".ds-private-index", "fileserver01", "10.20.30.40",
):
    assert secret not in first.sanitized_json, secret
for required in (
    "Services", "NetworkProvider", "ProviderPath", "System32", "SYSTEM", "S-1-5-18",
):
    assert required in first.sanitized_json, required

second = PrivacyManager().prepare_payload(
    ticket_key="LOCAL-RELEASE-TEST-SECOND",
    raw_json=first.sanitized_json,
)
assert second.safe_for_ai and second.residual_count == 0, second.residual_categories
print("Privacy regression test: OK")
