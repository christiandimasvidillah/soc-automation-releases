import json,tempfile,os
from pathlib import Path
from retention_policy import load,save,validate
with tempfile.TemporaryDirectory() as td:
 root=Path(td);assert load(root)['live_completed_seconds']==30
 p=save(root,{'live_completed_seconds':45,'completed_history_days':10,'failed_history_days':30,'raw_audit_days':14,'sanitized_audit_days':90});assert p['live_completed_seconds']==45;assert (root/'shared/retention_policy.json').stat().st_mode & 0o777==0o600
 try:validate({'live_completed_seconds':1});raise AssertionError('bound accepted')
 except ValueError:pass
 try:validate({'raw_audit_days':100,'sanitized_audit_days':90});raise AssertionError('cross-field accepted')
 except ValueError:pass
print('PASS test_retention_policy')
