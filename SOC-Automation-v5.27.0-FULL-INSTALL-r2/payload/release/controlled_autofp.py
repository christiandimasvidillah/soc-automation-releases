from __future__ import annotations
import json,os,tempfile,time
from pathlib import Path
RULE='Rare SMB Connection to the Internet';REASON='SYSTEM_SMB_ATTEMPT_NO_OBSERVED_SUCCESS_CLEAN_DESTINATION_CLUSTER'
def cfg(root):
 p=Path(root)/'shared/config/controlled_autofp.json'
 d={'enabled':False,'project':'CSOC','hourly_cap':2,'daily_cap':5,'rule':RULE,'false_status':'False Incident','done_status':'Done'}
 try:d.update(json.loads(p.read_text()))
 except Exception:pass
 return d
def atomic(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);fd,n=tempfile.mkstemp(prefix='.autofp-',dir=p.parent);os.close(fd);q=Path(n);q.write_text(json.dumps(d,indent=2)+'\n');os.chmod(q,0o600);os.replace(q,p)
def configure(root,enabled):
 d=cfg(root);d['enabled']=bool(enabled);atomic(Path(root)/'shared/config/controlled_autofp.json',d);return d
def history(root):
 p=Path(root)/'shared/audit_logs/controlled_autofp.jsonl';out=[]
 if p.is_file():
  for line in p.read_text(errors='replace').splitlines():
   try:out.append(json.loads(line))
   except Exception:pass
 return out
def gate(root,ticket,report,now=None):
 c=cfg(root);now=time.time() if now is None else now;d=report.get('decision') or {};reasons=[]
 if not c['enabled']:reasons.append('pilot_disabled')
 if not ticket.startswith(c['project']+'-'):reasons.append('project_not_allowed')
 if d.get('recommendation')!='AUTO_FP_ELIGIBLE' or d.get('blockers'):reasons.append('policy_not_eligible')
 if d.get('connection_assessment')!='NO_OBSERVED_SUCCESS':reasons.append('assessment_not_allowed')
 if not d.get('all_scoped_destinations_vt_clean'):reasons.append('vt_cluster_not_clean')
 h=history(root);hour=sum(1 for x in h if x.get('action')=='APPLIED' and now-float(x.get('epoch',0))<3600);day=sum(1 for x in h if x.get('action')=='APPLIED' and now-float(x.get('epoch',0))<86400)
 if hour>=int(c['hourly_cap']):reasons.append('hourly_cap_reached')
 if day>=int(c['daily_cap']):reasons.append('daily_cap_reached')
 return {'allowed':not reasons,'reasons':reasons,'hour_count':hour,'day_count':day,'config':c}
def audit(root,row):
 p=Path(root)/'shared/audit_logs/controlled_autofp.jsonl';p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('a') as f:f.write(json.dumps(row,separators=(',',':'))+'\n')
 os.chmod(p,0o600)
def execute(root,ticket,report,jira=None,apply=False,now=None):
 now=time.time() if now is None else now;g=gate(root,ticket,report,now);row={'epoch':now,'ticket':ticket,'reason_code':REASON,'gate':g,'action':'BLOCKED','apply_requested':bool(apply)}
 if not g['allowed']:audit(root,row);return row
 if not apply:row['action']='WOULD_APPLY';audit(root,row);return row
 own=jira is None
 if own:
  from jira_client import JiraClient
  jira=JiraClient()
 try:
  before=jira.get_current_status(ticket)
  if not jira.transition(ticket,g['config']['false_status']):raise RuntimeError('false_incident_transition_failed')
  if not jira.transition(ticket,g['config']['done_status']):raise RuntimeError('done_transition_failed')
  after=jira.get_current_status(ticket);row.update({'action':'APPLIED','before_status':before,'after_status':after})
 except Exception as e:row.update({'action':'FAILED','error':type(e).__name__})
 finally:
  if own:jira.close()
 audit(root,row);return row
