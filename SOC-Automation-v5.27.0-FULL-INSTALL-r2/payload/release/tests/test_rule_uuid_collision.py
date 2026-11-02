from __future__ import annotations
import json
from privacy_manager import PrivacyManager
A="81032261-9398-4e22-a607-3feaf2000001"
B="81032261-9398-4c82-c05b-60e100000002"
payload={"kibana.alert.rule.uuid":A,"kibana.alert.rule.rule_id":B,"kibana.alert.rule.parameters":{"rule_id":B},"kibana.alert.ancestors":[{"rule":A},{"rule":"RUSER_legacy_malformed"}],"kibana":{"alert":{"rule":{"uuid":A,"rule_id":B,"parameters":{"rule_id":B}},"ancestors":[{"rule":A}]}}}
r=PrivacyManager().prepare_payload(ticket_key="RULE-UUID-TEST",raw_json=json.dumps(payload))
t=r.sanitized_json; d=json.loads(t)
assert A not in t and B not in t and "RUSER_" not in t
assert r.residual_count==0 and r.safe_for_ai is True
x=d["kibana.alert.rule.uuid"]
assert x.startswith("RULE_")
assert x==d["kibana"]["alert"]["rule"]["uuid"]==d["kibana"]["alert"]["ancestors"][0]["rule"]
print("Rule UUID collision regression test: OK")
