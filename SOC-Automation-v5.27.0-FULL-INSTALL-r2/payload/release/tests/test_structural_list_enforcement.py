from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
for k,v in {"JIRA_EMAIL":"test@example.invalid","JIRA_API_TOKEN":"test","JIRA_ACCOUNT_ID":"test","ELASTIC_API_KEY":"test","GEMINI_API_KEY":"test","TELEGRAM_BOT_TOKEN":"test","TELEGRAM_CHAT_ID":"test","HASH_SECRET_KEY":"structural-list-test-secret","LOCAL_AI_MODEL":"test-model","AUDIT_DIR":tempfile.mkdtemp(prefix="soc-list-enforce-")}.items():os.environ.setdefault(k,v)
from privacy_manager import PrivacyManager
class EmptyLocalAIDetector:
 def detect(self,payload):return []
payload={"data":{"account_id":"project-sensitive-123","asset_vpcs":["project-sensitive-123/global/networks/prod-vpc","project-sensitive-123/regions/asia-southeast2/subnetworks/prod-subnet-01"]}}
m=PrivacyManager();m.local_ai_detector=EmptyLocalAIDetector();r=m.prepare_payload(ticket_key="STRUCTURAL-LIST",raw_json=json.dumps(payload));s=json.loads(r.sanitized_json)
assert len(s["data"]["asset_vpcs"])==2
assert all(value.startswith("NETWORK_") for value in s["data"]["asset_vpcs"])
assert all("/" not in value for value in s["data"]["asset_vpcs"])
assert r.safe_for_ai is True and r.residual_count==0
print("Structural list enforcement regression test: OK")
