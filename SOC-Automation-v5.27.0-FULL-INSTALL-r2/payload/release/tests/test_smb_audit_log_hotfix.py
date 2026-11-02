from smb_evidence_collector import normalize_alert_payload
src={'kibana.alert.rule.name':'Rare SMB Connection to the Internet','kibana.alert.original_time':'2026-08-14T13:46:51Z'}
assert normalize_alert_payload({'hits':{'hits':[{'_source':src}]}})==src
assert normalize_alert_payload({'_source':src})==src
assert normalize_alert_payload(src)==src
for payload in ({'hits':{'hits':[]}},{'hits':{'hits':[{'_source':src},{'_source':src}]}}):
 try:normalize_alert_payload(payload);raise AssertionError('must fail')
 except ValueError as e:assert str(e)=='expected_exactly_one_alert_hit'
print('PASS test_smb_audit_log_hotfix')
