import json,tempfile
from pathlib import Path
from manual_false_incident_reconciler import action,setmode
class S:
 def extract_alert_id(self,x):return 'alert-1'
 def safe_alert_reference(self,x):return 'ref'
 def close_alert(self,*a,**k):return True
class Settings:analysis_field_id='analysis';done_status='Done'
class J:
 account_id='me';settings=Settings()
 def get_issue(self,*a,**k):return {'fields':{'status':{'name':'False Incident'},'assignee':{'accountId':'me'},'analysis':'complete'}}
 def transition(self,*a):return True
 def get_current_status(self,*a):return 'Done'
with tempfile.TemporaryDirectory() as td:
 r=Path(td);p=r/'shared/audit_logs/CSOC-1_raw.json';p.parent.mkdir(parents=True);p.write_text('{}');j=J();s=S();assert action(r,'CSOC-1',j,s)['action']=='WOULD_COMPLETE';setmode(r,'ACTIVE');assert action(r,'CSOC-1',j,s,True)['action']=='COMPLETED';assert action(r,'CSOC-1',j,s,True)['action']=='SKIPPED_ALREADY_COMPLETED'
print('PASS test_manual_false_incident')
