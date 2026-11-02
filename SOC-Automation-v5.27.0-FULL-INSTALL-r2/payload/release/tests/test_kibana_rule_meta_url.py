from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
for k,v in {"JIRA_EMAIL":"test@example.invalid","JIRA_API_TOKEN":"test","JIRA_ACCOUNT_ID":"test","ELASTIC_API_KEY":"test","GEMINI_API_KEY":"test","TELEGRAM_BOT_TOKEN":"test","TELEGRAM_CHAT_ID":"test","HASH_SECRET_KEY":"kibana-meta-url-test-secret","LOCAL_AI_MODEL":"test-model","AUDIT_DIR":tempfile.mkdtemp(prefix="soc-kibana-meta-url-")}.items():os.environ.setdefault(k,v)
from privacy_manager import PrivacyManager
class EmptyLocalAIDetector:
 def detect(self,payload):return []
payload={"kibana.alert.url":"https://tenant.example.internal/app/security/alerts/redirect/id","kibana.alert.rule.meta.kibana_siem_app_url":"https://tenant.example.internal:9243/app/security","kibana.alert.rule.parameters":{"meta":{"kibana_siem_app_url":"https://tenant.example.internal:9243/app/security"}}}
m=PrivacyManager();m.local_ai_detector=EmptyLocalAIDetector();r=m.prepare_payload(ticket_key="KIBANA-META-URL",raw_json=json.dumps(payload));s=json.loads(r.sanitized_json)
assert s["kibana.alert.url"].startswith("URL_")
assert s["kibana.alert.rule.meta.kibana_siem_app_url"].startswith("URL_")
assert s["kibana.alert.rule.parameters"]["meta"]["kibana_siem_app_url"].startswith("URL_")
assert "https://tenant.example.internal" not in r.sanitized_json
assert r.safe_for_ai is True and r.residual_count==0
print("Kibana rule meta URL regression test: OK")
