from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
for key,value in {
 "JIRA_EMAIL":"test@example.invalid","JIRA_API_TOKEN":"test","JIRA_ACCOUNT_ID":"test",
 "ELASTIC_API_KEY":"test","GEMINI_API_KEY":"test","TELEGRAM_BOT_TOKEN":"test",
 "TELEGRAM_CHAT_ID":"test","HASH_SECRET_KEY":"local-hardening-test-secret",
 "LOCAL_AI_MODEL":"test-model","AUDIT_DIR":tempfile.mkdtemp(prefix="soc-offset-hardening-")
}.items(): os.environ.setdefault(key,value)
from privacy_manager import PrivacyManager
class EmptyLocalAIDetector:
 def detect(self,payload): return []
payload={
 "host":{"name":"server01"},
 "plain":"server01 SERVER01 (server01), server01: server01",
 "negative":["fileserver01","server01.example.local","server01-backup","xserver01"],
 "nested":[{"message":"event on server01"},{"message":"SERVER01 failed"}],
 "event":{"description":"The vulnerable rule should remain readable."},
}
m=PrivacyManager();m.local_ai_detector=EmptyLocalAIDetector()
r=m.prepare_payload(ticket_key="OFFSET-HARDENING",raw_json=json.dumps(payload))
s=json.loads(r.sanitized_json);host=s["host"]["name"]
assert host.startswith("HOST_")
assert s["plain"]==f"{host} {host} ({host}), {host}: {host}"
assert s["negative"]==payload["negative"]
assert s["nested"][0]["message"]==f"event on {host}"
assert s["nested"][1]["message"]==f"{host} failed"
assert s["event"]["description"]==payload["event"]["description"]
assert r.safe_for_ai is True and r.residual_count==0
m2=PrivacyManager();m2.local_ai_detector=EmptyLocalAIDetector()
r2=m2.prepare_payload(ticket_key="OFFSET-HARDENING-IDEMPOTENT",raw_json=r.sanitized_json)
assert json.loads(r2.sanitized_json)==s
assert r2.safe_for_ai is True and r2.residual_count==0
print("Offset propagation hardening regression test: OK")
