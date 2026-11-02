from __future__ import annotations
import json,os,re,time
from pathlib import Path
from runtime_events import TicketEventRecorder
TERMINAL_PIPELINE={'COMPLETED','FAILED','DISMISSED'}
DEFAULT_JIRA_TERMINAL={'done','closed','resolved','cancelled','canceled'}
def _json(path):
 try:value=json.loads(Path(path).read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):return {}
 return value if isinstance(value,dict) else {}
def total_in_flight(root):
 total=0
 for p in (Path(root)/'shared/workers').glob('*/health.json'):
  try:total+=max(0,int(_json(p).get('in_flight') or 0))
  except (TypeError,ValueError):pass
 return total
def reconcile(root,ticket_key=None,jira=None,now=None,minimum_age_seconds=300):
 root=Path(root).expanduser().resolve();now=time.time() if now is None else float(now);live_path=root/'shared/control/ticket_live_state.json';live=_json(live_path);in_flight=total_in_flight(root);result={'status':'PASS','changed':0,'skipped':0,'failed':0,'in_flight':in_flight,'tickets':[]}
 if in_flight:
  result.update(status='BLOCKED',failed=1,reason='runtime has tickets in flight');return result
 key_filter=str(ticket_key or '').strip().upper()
 if key_filter and not re.fullmatch(r'[A-Z][A-Z0-9_]*-\d+',key_filter):result.update(status='FAIL',failed=1,reason='invalid ticket key');return result
 allowed={x.strip().casefold() for x in os.getenv('JIRA_TERMINAL_STATUSES','').split(',') if x.strip()} or DEFAULT_JIRA_TERMINAL

 if jira is None:
  from jira_client import JiraClient
  client=JiraClient()
 else:client=jira
 recorder=TicketEventRecorder(root/'shared')
 try:
  for key,event in live.items():
   key=str(key).upper();event=event if isinstance(event,dict) else {};pipeline=str(event.get('status') or '').upper();age=max(0,now-float(event.get('epoch') or 0))
   if key_filter and key!=key_filter:continue
   if pipeline in TERMINAL_PIPELINE or age<minimum_age_seconds:result['skipped']+=1;continue
   try:status=str(client.get_current_status(key) or 'Unknown')
   except Exception as exc:result['failed']+=1;result['tickets'].append({'ticket_key':key,'action':'ERROR','reason':type(exc).__name__});continue
   if status.casefold() not in allowed:result['skipped']+=1;result['tickets'].append({'ticket_key':key,'action':'SKIPPED','jira_status':status});continue
   recorder.emit(key,'JIRA_TERMINAL_RECONCILIATION','COMPLETED',jira_status=status,outcome='ghost_live_state_closed');result['changed']+=1;result['tickets'].append({'ticket_key':key,'action':'COMPLETED','jira_status':status})
 finally:
  if jira is None:client.close()
 if result['failed']:result['status']='PARTIAL' if result['changed'] else 'FAIL'
 return result
