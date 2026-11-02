#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path


def load_module():
    config = types.ModuleType("config")
    config.settings = types.SimpleNamespace(
        local_ai=types.SimpleNamespace(),
        sanitizer=types.SimpleNamespace(audit_dir=tempfile.mkdtemp()),
    )
    sys.modules["config"] = config

    data_sanitizer = types.ModuleType("data_sanitizer")
    data_sanitizer.generate_hash = lambda value: "deadbeef1234"
    data_sanitizer.log_audit_mapping = lambda *args, **kwargs: None
    data_sanitizer.save_json_comparison = lambda *args, **kwargs: None
    sys.modules["data_sanitizer"] = data_sanitizer

    local_ai = types.ModuleType("local_ai_detector")
    class LocalAIDetectorError(RuntimeError):
        pass
    class OllamaSensitiveDetector:
        def __init__(self, settings):
            self.settings = settings
        def detect(self, payload):
            return []
    local_ai.LocalAIDetectorError = LocalAIDetectorError
    local_ai.OllamaSensitiveDetector = OllamaSensitiveDetector
    sys.modules["local_ai_detector"] = local_ai

    path = Path(__file__).resolve().parents[1] / "privacy_manager.py"
    spec = importlib.util.spec_from_file_location("privacy_manager_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    pm = load_module()
    raw_ip = "10.20.30.40"
    payload = {
        "took": 1234,
        "hits": {"hits": [{"_source": {
            "source": {"ip": raw_ip},
            "related": {"ip": [raw_ip]},
            "kibana.alert.reason": f"event with source {raw_ip} created an alert",
        }}]},
    }
    findings = pm.SensitiveDataDetector().discover(payload)
    ip_paths = {f.path for f in findings if f.category == "IP_ADDRESS"}
    assert "hits.hits[]._source.source.ip" in ip_paths, ip_paths
    assert "hits.hits[]._source.related.ip[]" in ip_paths, ip_paths
    assert "hits.hits[]._source.kibana.alert.reason" in ip_paths, ip_paths

    sanitized, replacements = pm.SensitiveDataSanitizer().apply(payload, findings)
    assert sanitized["took"] == 1234, sanitized["took"]
    source_token = sanitized["hits"]["hits"][0]["_source"]["source"]["ip"]
    related_token = sanitized["hits"]["hits"][0]["_source"]["related"]["ip"][0]
    reason = sanitized["hits"]["hits"][0]["_source"]["kibana.alert.reason"]
    assert source_token == related_token == "IP_deadbeef1234"
    assert raw_ip not in reason and "IP_deadbeef1234" in reason
    assert replacements >= 3
    residuals = pm.SanitizationValidator().validate(json.dumps(sanitized), findings)
    assert not residuals, [(f.category, f.path) for f in residuals]

    class Finding:
        category = "IP_ADDRESS"
        path = "took"
    converted = pm._convert_local_ai_findings(payload, [Finding()])
    assert converted == [], converted

    class BadFinding:
        category = "IP_ADDRESS"
        path = "hits.hits.0._source.kibana.alert.reason"
    converted = pm._convert_local_ai_findings(payload, [BadFinding()])
    assert converted == [], converted

    print("PASS: recursive IP sanitization and numeric false-positive regression")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
