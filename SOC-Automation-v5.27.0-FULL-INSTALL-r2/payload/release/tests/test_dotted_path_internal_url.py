from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
for k,v in {"JIRA_EMAIL":"test@example.invalid","JIRA_API_TOKEN":"test","JIRA_ACCOUNT_ID":"test","ELASTIC_API_KEY":"test","GEMINI_API_KEY":"test","TELEGRAM_BOT_TOKEN":"test","TELEGRAM_CHAT_ID":"test","HASH_SECRET_KEY":"dotted-path-test-secret","LOCAL_AI_MODEL":"test-model","AUDIT_DIR":tempfile.mkdtemp(prefix="soc-dotted-path-")}.items():os.environ.setdefault(k,v)
from privacy_manager import PrivacyManager,_resolve_local_ai_path
payload={"hits":{"hits":[{"_source":{"host":{"name":"server01"},"kibana.alert.reason":"event on server01","kibana.alert.url":"https://tenant.example.internal/app/security/alerts/redirect/raw-alert"}}]}}
assert _resolve_local_ai_path(payload,"hits.hits.0._source.host.name")=="server01"
assert _resolve_local_ai_path(payload,"hits.hits.0._source.kibana.alert.reason")=="event on server01"
assert _resolve_local_ai_path(payload,"hits.hits.0._source.kibana.alert.url").startswith("https://")
class EmptyLocalAIDetector:
 def detect(self,payload):return []
m=PrivacyManager();m.local_ai_detector=EmptyLocalAIDetector();r=m.prepare_payload(ticket_key="DOTTED-PATH-URL",raw_json=json.dumps(payload));s=json.loads(r.sanitized_json);src=s["hits"]["hits"][0]["_source"]
assert src["kibana.alert.url"].startswith("URL_")
assert "https://tenant.example.internal" not in r.sanitized_json
assert src["kibana.alert.reason"]=="event on "+src["host"]["name"]
assert r.safe_for_ai is True and r.residual_count==0
print("Dotted path and internal URL regression test: OK")
