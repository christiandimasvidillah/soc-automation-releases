from __future__ import annotations
import json,time
from pathlib import Path

def read_json(path):
 try:value=json.loads(Path(path).read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):return {}
 return value if isinstance(value,dict) else {}

def recent_alerts(root,limit=20):
 path=Path(root)/'shared/control/operational_alerts.jsonl';out=[]
 if not path.is_file():return out
 for line in path.read_text(errors='replace').splitlines()[-limit:]:
  try:e=json.loads(line)
  except Exception:continue
  if not isinstance(e,dict):continue
  details=e.get('details') if isinstance(e.get('details'),dict) else {}
  out.append({'epoch':float(e.get('epoch') or 0),'code':str(e.get('code') or '-'),'component':str(e.get('component') or '-'),'severity':str(e.get('severity') or '-'),'worker':str(details.get('worker') or '-'),'telegram_sent':bool(e.get('telegram_sent')),'deduped':bool(e.get('deduped'))})
 return out

def build_health_center(root,now=None):
 root=Path(root).expanduser().resolve();now=time.time() if now is None else float(now);workers=[];degraded=[]
 for path in sorted((root/'shared/workers').glob('*/health.json')):
  h=read_json(path);heartbeat=h.get('last_heartbeat') or h.get('heartbeat_at');age=None
  try:
   from datetime import datetime
   age=max(0,now-datetime.fromisoformat(str(heartbeat).replace('Z','+00:00')).timestamp()) if heartbeat else None
  except Exception:age=None
  row={'slot':str(h.get('slot') or path.parent.name),'role':str(h.get('role') or '-'),'status':str(h.get('status') or 'unknown'),'version':str(h.get('version') or '-'),'pid':h.get('pid'),'heartbeat_age_seconds':round(age,1) if age is not None else None,'jira_poll_status':str(h.get('jira_poll_status') or h.get('last_poll_status') or '-'),'ticket_intake_status':str(h.get('ticket_intake_status') or '-'),'circuit_breaker':str(h.get('intake_circuit_breaker') or 'closed'),'in_flight':int(h.get('in_flight') or 0)};workers.append(row)
  if row['status'] not in {'healthy','ready'} or row['circuit_breaker']=='open' or (age is not None and age>120):degraded.append('worker:'+row['slot'])
 preflight=read_json(root/'shared/configuration_preflight.json');qualification=read_json(root/'shared/release_qualification.json');alerts=recent_alerts(root);recent_errors=sum(1 for x in alerts if x['severity'].upper()=='ERROR' and now-x['epoch']<=86400)
 if preflight and str(preflight.get('status')).upper()!='PASS':degraded.append('configuration_preflight')
 if qualification and not bool(qualification.get('passed',False)):degraded.append('release_qualification')
 overall='healthy' if not degraded else 'degraded'
 return {'generated_at':now,'overall_status':overall,'degraded_components':degraded,'summary':{'workers':len(workers),'active_workers':sum(x['role']=='active' for x in workers),'in_flight':sum(x['in_flight'] for x in workers),'open_circuits':sum(x['circuit_breaker']=='open' for x in workers),'alerts_24h':len([x for x in alerts if now-x['epoch']<=86400]),'errors_24h':recent_errors},'workers':workers,'configuration_preflight':{'status':preflight.get('status','not evaluated'),'failed':(preflight.get('summary') or {}).get('failed'),'warnings':(preflight.get('summary') or {}).get('warnings')},'release_qualification':{'status':qualification.get('status','not evaluated'),'passed':qualification.get('passed'),'failed':(qualification.get('summary') or {}).get('failed')},'recent_operational_alerts':alerts[-20:]}
