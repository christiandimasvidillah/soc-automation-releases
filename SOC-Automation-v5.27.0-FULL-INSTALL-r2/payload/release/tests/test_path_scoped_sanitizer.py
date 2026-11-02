from __future__ import annotations
import json
import os
import sys
import tempfile
from pathlib import Path
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
os.environ.setdefault("JIRA_EMAIL", "test@example.invalid")
os.environ.setdefault("JIRA_API_TOKEN", "test")
os.environ.setdefault("JIRA_ACCOUNT_ID", "test")
os.environ.setdefault("ELASTIC_API_KEY", "test")
os.environ.setdefault("GEMINI_API_KEY", "test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test")
os.environ.setdefault("HASH_SECRET_KEY", "local-regression-test-secret")
os.environ.setdefault("LOCAL_AI_MODEL", "test-model")
os.environ.setdefault(
    "AUDIT_DIR",
    tempfile.mkdtemp(prefix="soc-path-sanitizer-test-"),
)
from privacy_manager import PrivacyManager
class EmptyLocalAIDetector:
    def detect(self, payload):
        return []
payload = {
    "host": {
        "name": "ul",
    },
    "event": {
        "description": (
            "The vulnerable rule should remain readable."
        ),
    },
    "kibana.alert.reason": "event on ul",
}
manager = PrivacyManager()
manager.local_ai_detector = EmptyLocalAIDetector()
result = manager.prepare_payload(
    ticket_key="PATH-SCOPED-SANITIZER-TEST",
    raw_json=json.dumps(payload),
)
sanitized = json.loads(result.sanitized_json)
assert sanitized["host"]["name"].startswith("HOST_")
assert sanitized["event"]["description"] == (
    "The vulnerable rule should remain readable."
)
assert sanitized["kibana.alert.reason"].startswith("event on HOST_")
assert "event on ul" not in result.sanitized_json
assert result.safe_for_ai is True
assert result.residual_count == 0
print("Path-scoped sanitizer regression test: OK")
