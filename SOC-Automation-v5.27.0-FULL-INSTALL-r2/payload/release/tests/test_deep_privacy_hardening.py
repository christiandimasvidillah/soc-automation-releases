from __future__ import annotations
import json
from privacy_manager import PrivacyManager
payload={'hits':{'hits':[{'_source':{'data':{
 'findings':{'Database':{'name':'db-internal','id':'11111111-1111-4111-8111-111111111111'},'name':'private.table','id':'finding-private','SensitiveDbEntries':[{'Sample':'Name: masked-person Address: masked-place','Identifier':'Personal Information'}]},
 'asset_name':'prod-db-internal','cluster_name':'prod-db-internal','account_name':'private-project','cloud_provider_id':'private-project','account_id':'22222222-2222-4222-8222-222222222222','alert_id':'vendor-123','alert_ui_link':'https://vendor.example/alerts/vendor-123','asset_tags':{'owner':'private-team','projectid':'private-project','environment':'prod','component':'postgres'}}}}]}}
raw=json.dumps(payload)
result=PrivacyManager().prepare_payload(ticket_key='TEST-PRIVACY',raw_json=raw)
out=json.loads(result.sanitized_json); text=result.sanitized_json
sample=out['hits']['hits'][0]['_source']['data']['findings']['SensitiveDbEntries'][0]['Sample']
assert sample=='[REDACTED_SENSITIVE_SAMPLE]'
for secret in ('masked-person','masked-place','db-internal','private.table','prod-db-internal','private-project','vendor-123','private-team'):
 assert secret not in text, secret
assert 'postgres' in text and 'prod' in text
assert result.safe_for_ai, result.residual_categories
print('Deep privacy hardening tests: OK')
