from __future__ import annotations
import fcntl,json,os,tempfile,time
from ticket_history_retention import compact_history
from retention_policy import load as load_retention_policy
from datetime import datetime,timezone
from pathlib import Path
SAFE_DETAILS={"attempt","findings_count","replacements_count","residual_count","decision","jira_status","failure_code","outcome"}
class TicketEventRecorder:
 def __init__(self,shared_dir=None):
  root=Path(shared_dir or (Path.home()/"SOC-Automation/shared")).expanduser().resolve();self.control=root/'control';self.control.mkdir(parents=True,exist_ok=True);self.events=self.control/'ticket_events.jsonl';self.live=self.control/'ticket_live_state.json';self.worker=os.getenv('SOC_WORKER_SLOT','unknown');self._last_cleanup=0
  os.chmod(self.control,0o700)
 def emit(self,ticket_key,stage,status,**details):
  safe={k:v for k,v in details.items() if k in SAFE_DETAILS and isinstance(v,(str,int,float,bool,type(None)))}
  event={"timestamp":datetime.now(timezone.utc).isoformat(),"epoch":time.time(),"ticket_key":str(ticket_key),"worker":self.worker,"pid":os.getpid(),"stage":str(stage),"status":str(status),"details":safe}
  with self.events.open('a',encoding='utf-8') as f:
   fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno());fcntl.flock(f,fcntl.LOCK_UN)
  os.chmod(self.events,0o600);self._update_live(event);self._maybe_cleanup();return event
 def _maybe_cleanup(self):
  now=time.time()
  if now-self._last_cleanup<3600:return
  self._last_cleanup=now
  policy=load_retention_policy(self.control.parent.parent)
  compact_history(self.control.parent,completed_days=policy['completed_history_days'],failed_days=policy['failed_history_days'],now=now)
 def _update_live(self,event):
  lock=self.control/'ticket_live_state.lock'
  with lock.open('a+') as lf:
   fcntl.flock(lf,fcntl.LOCK_EX)
   try:
    try:data=json.loads(self.live.read_text())
    except Exception:data={}
    data[event['ticket_key']]=event
    now=time.time();policy=load_retention_policy(self.control.parent.parent);visibility=policy['live_completed_seconds'];data={k:v for k,v in data.items() if not (str(v.get('status','')).upper() in {'COMPLETED','DISMISSED'} and now-float(v.get('epoch',0))>visibility)}
    fd,name=tempfile.mkstemp(prefix='.ticket-live-',dir=self.control);os.close(fd);tmp=Path(name);tmp.write_text(json.dumps(data,indent=2));os.chmod(tmp,0o600);os.replace(tmp,self.live)
   finally:fcntl.flock(lf,fcntl.LOCK_UN)
_default=None
def emit_ticket_event(ticket_key,stage,status,**details):
 global _default
 if _default is None:_default=TicketEventRecorder()
 try:return _default.emit(ticket_key,stage,status,**details)
 except Exception:return None
