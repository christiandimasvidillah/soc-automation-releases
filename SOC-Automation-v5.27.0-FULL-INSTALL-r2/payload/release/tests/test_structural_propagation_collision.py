from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
for key,value in {
 "JIRA_EMAIL":"test@example.invalid","JIRA_API_TOKEN":"test","JIRA_ACCOUNT_ID":"test",
 "ELASTIC_API_KEY":"test","GEMINI_API_KEY":"test","TELEGRAM_BOT_TOKEN":"test",
 "TELEGRAM_CHAT_ID":"test","HASH_SECRET_KEY":"structural-collision-test-secret",
 "LOCAL_AI_MODEL":"test-model","AUDIT_DIR":tempfile.mkdtemp(prefix="soc-structural-collision-")
}.items(): os.environ.setdefault(key,value)
from privacy_manager import PrivacyManager
class EmptyLocalAIDetector:
 def detect(self,payload): return []
payload={
 "data":{
  "account_id":"project-sensitive-123",
  "asset_vpcs":[
   "project-sensitive-123/global/networks/prod-vpc",
   "project-sensitive-123/regions/asia-southeast2/subnetworks/prod-subnet-01"
  ]
 },
 "kibana.alert.rule.meta.kibana_siem_app_url":"https://tenant.example.internal:9243/app/security"
}
manager=PrivacyManager();manager.local_ai_detector=EmptyLocalAIDetector()
result=manager.prepare_payload(ticket_key="STRUCTURAL-COLLISION",raw_json=json.dumps(payload))
sanitized=json.loads(result.sanitized_json)
assert sanitized["data"]["account_id"].startswith("CLOUD_ACCOUNT_ID_")
assert all(value.startswith("NETWORK_") for value in sanitized["data"]["asset_vpcs"])
assert sanitized["kibana.alert.rule.meta.kibana_siem_app_url"].startswith("URL_")
assert "project-sensitive-123/" not in result.sanitized_json
assert "https://tenant.example.internal" not in result.sanitized_json
assert result.safe_for_ai is True and result.residual_count == 0
print("Structural propagation collision regression test: OK")
