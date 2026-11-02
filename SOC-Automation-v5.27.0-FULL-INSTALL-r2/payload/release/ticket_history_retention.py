from __future__ import annotations
import fcntl,json,os,tempfile,time
from pathlib import Path
TERMINAL_SHORT={"COMPLETED","DISMISSED"}
TERMINAL_LONG={"FAILED"}
def keep_event(event,now,completed_days,failed_days):
 try:age=now-float(event.get('epoch',0))
 except Exception:return False
 status=str(event.get('status') or '').upper()
 if status in TERMINAL_SHORT:return age<=completed_days*86400
 if status in TERMINAL_LONG:return age<=failed_days*86400
 return True
def compact_history(shared_dir,completed_days=7,failed_days=30,now=None):
 now=time.time() if now is None else float(now);control=Path(shared_dir).expanduser().resolve()/'control';events=control/'ticket_events.jsonl';live=control/'ticket_live_state.json';lock=control/'ticket_history_retention.lock';control.mkdir(parents=True,exist_ok=True)
 report={"status":"PASS","completed_days":completed_days,"failed_days":failed_days,"events_before":0,"events_after":0,"events_deleted":0,"live_before":0,"live_after":0,"live_deleted":0}
 with lock.open('a+') as lf:
  fcntl.flock(lf,fcntl.LOCK_EX)
  try:
   kept=[]
   if events.is_file():
    for line in events.read_text(errors='replace').splitlines():
     try:event=json.loads(line)
     except Exception:continue
     report['events_before']+=1
     if keep_event(event,now,completed_days,failed_days):kept.append(event)
    fd,name=tempfile.mkstemp(prefix='.ticket-events-',dir=control);os.close(fd);tmp=Path(name);tmp.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in kept));os.chmod(tmp,0o600);os.replace(tmp,events)
   report['events_after']=len(kept);report['events_deleted']=report['events_before']-report['events_after']
   try:data=json.loads(live.read_text()) if live.is_file() else {}
   except Exception:data={}
   report['live_before']=len(data) if isinstance(data,dict) else 0
   clean={k:v for k,v in data.items() if keep_event(v,now,completed_days,failed_days)} if isinstance(data,dict) else {}
   fd,name=tempfile.mkstemp(prefix='.ticket-live-',dir=control);os.close(fd);tmp=Path(name);tmp.write_text(json.dumps(clean,indent=2));os.chmod(tmp,0o600);os.replace(tmp,live)
   report['live_after']=len(clean);report['live_deleted']=report['live_before']-report['live_after']
  finally:fcntl.flock(lf,fcntl.LOCK_UN)
 return report
