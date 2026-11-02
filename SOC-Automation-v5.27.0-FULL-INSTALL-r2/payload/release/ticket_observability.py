from __future__ import annotations
import json,time
from collections import Counter,defaultdict
from pathlib import Path
TERMINAL={'COMPLETED','FAILED','DISMISSED'}
def load_events(root,limit=20000):
 path=Path(root).expanduser().resolve()/'shared/control/ticket_events.jsonl';out=[]
 if not path.is_file():return out
 for line in path.read_text(errors='replace').splitlines()[-limit:]:
  try:e=json.loads(line)
  except Exception:continue
  if isinstance(e,dict) and e.get('ticket_key') and e.get('epoch'):out.append(e)
 return out
def build_report(root,stuck_seconds=300,now=None,limit=20000):
 now=time.time() if now is None else float(now);groups=defaultdict(list)
 for e in load_events(root,limit):groups[str(e['ticket_key'])].append(e)
 tickets=[];stage_samples=defaultdict(list);status_counts=Counter();worker_counts=Counter();stuck=[]
 for key,events in groups.items():
  events.sort(key=lambda x:float(x.get('epoch',0)));first,last=events[0],events[-1];status=str(last.get('status') or 'UNKNOWN').upper();status_counts[status]+=1;worker_counts[str(last.get('worker') or 'unknown')]+=1
  for a,b in zip(events,events[1:]):
   delta=max(0,float(b.get('epoch',0))-float(a.get('epoch',0)));stage_samples[str(a.get('stage') or 'UNKNOWN')].append(delta)
  elapsed=max(0,float(last.get('epoch',0))-float(first.get('epoch',0)));age=max(0,now-float(last.get('epoch',0)));jira='-'
  for e in events:
   d=e.get('details') if isinstance(e.get('details'),dict) else {}
   if d.get('jira_status'):jira=str(d['jira_status'])
  row={'ticket_key':key,'worker':str(last.get('worker') or '-'),'stage':str(last.get('stage') or '-'),'status':status,'jira_status':jira,'events':len(events),'elapsed_seconds':round(elapsed,3),'last_event_age_seconds':round(age,3)};tickets.append(row)
  if status not in TERMINAL and age>=stuck_seconds:stuck.append(row)
 tickets.sort(key=lambda x:x['last_event_age_seconds']);stuck.sort(key=lambda x:x['last_event_age_seconds'],reverse=True)
 stages=[]
 for stage,values in stage_samples.items():
  values=sorted(values);n=len(values);stages.append({'stage':stage,'samples':n,'average_seconds':round(sum(values)/n,3),'p95_seconds':round(values[min(n-1,max(0,int(n*.95)-1))],3),'max_seconds':round(values[-1],3)})
 stages.sort(key=lambda x:x['average_seconds'],reverse=True)
 completed=[x['elapsed_seconds'] for x in tickets if x['status']=='COMPLETED']
 return {'generated_at':now,'stuck_threshold_seconds':stuck_seconds,'summary':{'tickets':len(tickets),'completed':status_counts['COMPLETED'],'failed':status_counts['FAILED'],'active':sum(v for k,v in status_counts.items() if k not in TERMINAL),'stuck':len(stuck),'average_completed_seconds':round(sum(completed)/len(completed),3) if completed else 0},'status_counts':dict(status_counts),'worker_counts':dict(worker_counts),'slowest_stages':stages[:15],'stuck_tickets':stuck[:100],'tickets':tickets[:500]}
