from __future__ import annotations
import html,json,os,tempfile,time
from pathlib import Path
class OperationalAlertManager:
 def __init__(self,root,send_func=None,dedupe_seconds=3600):
  self.root=Path(root).expanduser().resolve();self.path=self.root/'shared/control/operational_alerts.jsonl';self.state_path=self.root/'shared/control/operational_alert_state.json';self.path.parent.mkdir(parents=True,exist_ok=True);self.send_func=send_func;self.dedupe_seconds=max(60,int(dedupe_seconds))
 def _state(self):
  try:value=json.loads(self.state_path.read_text())
  except Exception:value={}
  return value if isinstance(value,dict) else {}
 def _save(self,value):
  fd,name=tempfile.mkstemp(prefix='.operational-alert-',dir=self.state_path.parent);os.close(fd);tmp=Path(name);tmp.write_text(json.dumps(value,indent=2)+'\n');os.chmod(tmp,0o600);os.replace(tmp,self.state_path)
 def notify(self,code,component,severity='ERROR',fingerprint=None,details=None,now=None):
  now=time.time() if now is None else float(now);key=str(fingerprint or code);state=self._state();last=float(state.get(key,0));deduped=key in state and now-last<self.dedupe_seconds
  safe={k:v for k,v in (details or {}).items() if k in {'worker','occurrences','circuit_state','open_until','recovery'} and isinstance(v,(str,int,float,bool,type(None)))}
  event={'epoch':now,'code':str(code),'component':str(component),'severity':str(severity),'fingerprint':key,'deduped':deduped,'details':safe,'telegram_sent':False}
  if not deduped and self.send_func is not None:
   message='<b>SOC Automation Operational Alert</b>\n\n'+f'<b>Severity:</b> {html.escape(str(severity))}\n<b>Component:</b> {html.escape(str(component))}\n<b>Code:</b> <code>{html.escape(str(code))}</code>'
   if safe.get('worker'):message+=f'\n<b>Worker:</b> {html.escape(str(safe["worker"]))}'
   if safe.get('occurrences') is not None:message+=f'\n<b>Occurrences:</b> {int(safe["occurrences"])}'
   try:event['telegram_sent']=bool(self.send_func(message))
   except Exception:event['telegram_sent']=False
   state[key]=now;self._save(state)
  with self.path.open('a',encoding='utf-8') as f:f.write(json.dumps(event,separators=(',',':'))+'\n')
  os.chmod(self.path,0o600);return event
