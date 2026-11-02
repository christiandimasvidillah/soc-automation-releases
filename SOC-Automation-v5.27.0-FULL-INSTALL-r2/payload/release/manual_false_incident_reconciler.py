from __future__ import annotations
import json,os,sqlite3,time
from pathlib import Path
JQL='project = CSOC AND status = "False Incident" AND assignee = currentUser() ORDER BY updated ASC'
DB='shared/manual_false_incident.sqlite3'
def dbopen(root):
 p=Path(root)/DB;p.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(p);db.execute('CREATE TABLE IF NOT EXISTS state(k TEXT PRIMARY KEY,v TEXT NOT NULL)');db.execute('CREATE TABLE IF NOT EXISTS actions(ticket TEXT PRIMARY KEY,alert_id TEXT,status TEXT,epoch REAL,detail TEXT)');db.execute("INSERT OR IGNORE INTO state VALUES('mode','SHADOW')");db.commit();os.chmod(p,0o600);return db
def getmode(db):return db.execute("SELECT v FROM state WHERE k='mode'").fetchone()[0]
def setmode(root,value):
 if value not in {'DISABLED','SHADOW','ACTIVE'}:raise ValueError('invalid_mode')
 db=dbopen(root);db.execute("INSERT OR REPLACE INTO state VALUES('mode',?)",(value,));db.commit();return {'mode':value}
def status(root):
 db=dbopen(root);counts={k:v for k,v in db.execute('SELECT status,count(*) FROM actions GROUP BY status')};return {'mode':getmode(db),'database':str(Path(root)/DB),'counts':counts,'jql_scope':'CSOC / False Incident / currentUser'}
def raw_for(root,ticket):return Path(root)/'shared/audit_logs'/f'{ticket}_raw.json'
def action(root,ticket,jira,siem,apply=False):
 db=dbopen(root);m=getmode(db);row={'ticket':ticket,'mode':m,'action':'BLOCKED','reasons':[]}
 if m=='DISABLED':row['reasons'].append('feature_disabled');return row
 prior=db.execute("SELECT status FROM actions WHERE ticket=?",(ticket,)).fetchone()
 issue=jira.get_issue(ticket,fields=['status','assignee',jira.settings.analysis_field_id]);fields=issue.get('fields',{});st=(fields.get('status') or {}).get('name','Unknown');assignee=(fields.get('assignee') or {}).get('accountId')
 if st.casefold()!='false incident':row['reasons'].append('status_not_false_incident')
 if assignee!=jira.account_id:row['reasons'].append('assignee_not_current_account')
 analysis=(fields.get(jira.settings.analysis_field_id) or '').strip()
 if not analysis:row['reasons'].append('analysis_not_completed')
 raw=raw_for(root,ticket)
 if not raw.is_file():row['reasons'].append('automation_raw_not_found')
 alert_id=None
 if raw.is_file():
  try:alert_id=siem.extract_alert_id(json.loads(raw.read_text()))
  except Exception:row['reasons'].append('alert_identity_invalid')
 if not alert_id:row['reasons'].append('alert_id_missing')
 if prior and prior[0]=='COMPLETED':row.update({'action':'SKIPPED_ALREADY_COMPLETED','reasons':[]});return row
 if row['reasons']:return row
 row['alert_reference']=siem.safe_alert_reference(alert_id)
 if m=='SHADOW' or not apply:row['action']='WOULD_COMPLETE';return row
 if not jira.transition(ticket,jira.settings.done_status):row.update({'action':'FAILED_JIRA_DONE'});return row
 live=jira.get_current_status(ticket)
 if live.casefold()!=jira.settings.done_status.casefold():row.update({'action':'FAILED_JIRA_VERIFICATION','live_status':live});return row
 try:
  siem.close_alert(alert_id,closing_reason='False Positive');row.update({'action':'COMPLETED','jira_status':live,'siem_status':'closed'})
 except Exception as e:row.update({'action':'PARTIAL_SIEM_CLOSE_FAILED','jira_status':live,'siem_status':'close_failed','error':type(e).__name__})
 db.execute('INSERT OR REPLACE INTO actions VALUES(?,?,?,?,?)',(ticket,alert_id,row['action'],time.time(),json.dumps(row,separators=(',',':'))));db.commit();return row
def poll(root,jira=None,siem=None,apply=None,max_results=50):
 root=Path(root);db=dbopen(root);m=getmode(db);out={'mode':m,'matched':0,'completed':[],'skipped':[],'errors':[]}
 if m=='DISABLED':return out
 ownj=jira is None;owns=siem is None
 if ownj:
  from jira_client import JiraClient;jira=JiraClient()
 if owns:
  from siem_client import SiemClient;siem=SiemClient()
 try:
  issues=jira.search_tickets(jql=JQL,fields=['key'],max_results=max_results);out['matched']=len(issues)
  for x in issues:
   t=x.get('key','')
   try:
    r=action(root,t,jira,siem,apply=(m=='ACTIVE' if apply is None else apply));(out['completed'] if r['action'] in {'COMPLETED','PARTIAL_SIEM_CLOSE_FAILED','WOULD_COMPLETE'} else out['skipped']).append(r)
   except Exception as e:out['errors'].append({'ticket':t,'error':type(e).__name__})
 finally:
  if ownj:jira.close()
  if owns:siem.close()
 return out
def run(root,interval=30):
 while True:poll(root);time.sleep(max(15,interval))
