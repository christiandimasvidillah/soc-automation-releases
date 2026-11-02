from __future__ import annotations

import json

from privacy_manager import PrivacyManager


payload = {
    "data": {
        "asset_tags": {
            "kube-labels": (
                "app=APP_demo,"
                "cloud.google.com/"
                "SYSTEM_demo-boot-disk=x,"
                "iam.SYSTEM_demo.io/"
                "SYSTEM_demo-enabled=true"
            ),
            "kube_labels": (
                "system=SYSTEM_demo,"
                "owner=TEAM_demo"
            ),
            "environment": "prod",
        },
        "alert_category": "Data at risk",
        "risk_level": "medium",
    }
}

result = PrivacyManager().prepare_payload(
    ticket_key="KUBE-LABELS-REGRESSION",
    raw_json=json.dumps(payload),
)

sanitized = json.loads(result.sanitized_json)
tags = sanitized["data"]["asset_tags"]

print("kube-labels:", tags.get("kube-labels"))
print("kube_labels:", tags.get("kube_labels"))
print("safe_for_ai:", result.safe_for_ai)
print("residual_count:", result.residual_count)

assert tags["kube-labels"] == (
    "[REDACTED_SENSITIVE_BLOB]"
)

assert tags["kube_labels"] == (
    "[REDACTED_SENSITIVE_BLOB]"
)

assert "cloud.google.com/SYSTEM_" not in (
    result.sanitized_json
)

assert "iam.SYSTEM_" not in (
    result.sanitized_json
)

assert "system=SYSTEM_" not in (
    result.sanitized_json
)

assert result.residual_count == 0
assert result.safe_for_ai is True

print(
    "Kube-labels redaction regression test: OK"
)
