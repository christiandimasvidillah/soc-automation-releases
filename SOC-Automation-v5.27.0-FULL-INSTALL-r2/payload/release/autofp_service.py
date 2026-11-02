from __future__ import annotations
import json,os,sqlite3,time,traceback
from pathlib import Path
from background_autofp_worker import init,mode,one
JQL='project = CSOC AND status = Waiting ORDER BY created ASC'
def state(db,k,default='0'):
 r=db.execute('SELECT v FROM state WHERE k=?',(k,)).fetchone();return r[0] if r else default
def put(db,k,v):db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(k,str(v)));db.commit()
def circuit(db,reason):put(db,'circuit','OPEN');put(db,'circuit_reason',reason);put(db,'mode','DISABLED')
def summary(root):
 db=init(root);return {'mode':mode(db),'circuit':state(db,'circuit','CLOSED'),'circuit_reason':state(db,'circuit_reason',''),'last_poll':float(state(db,'last_poll','0')),'consecutive_failures':int(state(db,'consecutive_failures','0'))}
def reset_circuit(root):
 db=init(root);put(db,'circuit','CLOSED');put(db,'circuit_reason','');put(db,'consecutive_failures','0');return summary(root)
def poll_once(root,jira=None,max_tickets=20):
 root=Path(root);db=init(root);m=mode(db);out={'mode':m,'processed':[],'skipped':[],'errors':[]};put(db,'last_poll',time.time())
 if m=='DISABLED' or state(db,'circuit','CLOSED')=='OPEN':return out
 own=jira is None
 if own:
  from jira_client import JiraClient
  jira=JiraClient()
 try:issues=jira.search_tickets(jql=JQL,fields=['key','status'],max_results=max_tickets)
 except Exception as e:
  n=int(state(db,'consecutive_failures','0'))+1;put(db,'consecutive_failures',n);out['errors'].append('jira_search_failed')
  if n>=2:circuit(db,'jira_search_failed_twice')
  if own:jira.close()
  return out
 put(db,'consecutive_failures',0)
 for issue in issues:
  ticket=issue.get('key','');raw=root/'shared/audit_logs'/f'{ticket}_raw.json'
  if not raw.is_file():out['skipped'].append({'ticket':ticket,'reason':'raw_audit_not_ready'});continue
  try:
   payload=json.loads(raw.read_text())
   from smb_evidence_collector import collect
   report=collect(payload,root)
   if report.get('status')!='PASS':out['skipped'].append({'ticket':ticket,'reason':'fresh_evidence_failed'});continue
   result=one(root,ticket,apply=False);out['processed'].append({'ticket':ticket,'action':result.get('action')})
   if result.get('action') in {'FAILED','PARTIAL'}:circuit(db,'action_failure');break
  except Exception as e:
   out['errors'].append({'ticket':ticket,'error':type(e).__name__});circuit(db,'unhandled_ticket_error');break
 if own:jira.close()
 return out
def run(root,interval=60):
 while True:
  poll_once(root);time.sleep(max(15,interval))
