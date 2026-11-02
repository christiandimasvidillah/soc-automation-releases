#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,mimetypes,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from soc_status import snapshot
from service_status import snapshot as service_snapshot
from feature_control import FeatureControl
from ai_health import snapshot as ai_snapshot
ALLOWED_DETAILS={"attempt","findings_count","replacements_count","residual_count","decision","jira_status","failure_code","outcome"}
def safe_event(value):
 if not isinstance(value,dict):return None
 details=value.get('details') if isinstance(value.get('details'),dict) else {}
 return {"timestamp":str(value.get('timestamp') or ''),"epoch":float(value.get('epoch') or 0),"ticket_key":str(value.get('ticket_key') or '')[:64],"worker":str(value.get('worker') or '')[:32],"pid":int(value.get('pid') or 0),"stage":str(value.get('stage') or '')[:64],"status":str(value.get('status') or '')[:32],"details":{k:v for k,v in details.items() if k in ALLOWED_DETAILS and isinstance(v,(str,int,float,bool,type(None)))}}
def ticket_snapshot(root):
 control=root/'shared/control';live=control/'ticket_live_state.json';events=control/'ticket_events.jsonl';items=[];timeline={}
 try:data=json.loads(live.read_text()) if live.is_file() else {}
 except Exception:data={}
 for raw in data.values() if isinstance(data,dict) else []:
  event=safe_event(raw)
  if event and event['ticket_key'] and not (event['status'] in {'COMPLETED','DISMISSED'} and time.time()-event['epoch']>30):items.append(event)
 items.sort(key=lambda x:x['epoch'],reverse=True)
 if events.is_file():
  try:
   lines=events.read_text(errors='replace').splitlines()[-2000:]
   for line in lines:
    try:event=safe_event(json.loads(line))
    except Exception:continue
    if not event or not event['ticket_key']:continue
    timeline.setdefault(event['ticket_key'],[]).append(event)
  except OSError:pass
 for item in items:
  statuses=[str(e.get('details',{}).get('jira_status')) for e in timeline.get(item['ticket_key'],[]) if e.get('details',{}).get('jira_status')]
  item['jira_status']=statuses[-1] if statuses else None
 return {"generated_at":time.time(),"refresh_seconds":1,"tickets":items[:250],"timeline":{key:value[-60:] for key,value in timeline.items() if key in {x['ticket_key'] for x in items[:250]}}}
def history_snapshot(root):
 control=root/'shared/control';events=control/'ticket_events.jsonl';grouped={}
 if events.is_file():
  try:
   for line in events.read_text(errors='replace').splitlines()[-10000:]:
    try:event=safe_event(json.loads(line))
    except Exception:continue
    if event and event['ticket_key']:grouped.setdefault(event['ticket_key'],[]).append(event)
  except OSError:pass
 rows=[]
 for key,value in grouped.items():
  value.sort(key=lambda x:x['epoch']);last=value[-1];statuses=[str(e.get('details',{}).get('jira_status')) for e in value if e.get('details',{}).get('jira_status')];rows.append({"ticket_key":key,"worker":last['worker'],"stage":last['stage'],"status":last['status'],"jira_status":statuses[-1] if statuses else None,"last_epoch":last['epoch'],"events":len(value),"timeline":value[-60:]})
 rows.sort(key=lambda x:x['last_epoch'],reverse=True)
 return {"generated_at":time.time(),"retention":{"completed_days":7,"failed_days":30},"tickets":rows[:500]}
class Handler(BaseHTTPRequestHandler):
 root:Path;static:Path
 def end_headers(self):
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:");super().end_headers()
 def do_POST(self):self.send_error(405,'Read-only viewer')
 do_PUT=do_POST;do_DELETE=do_POST;do_PATCH=do_POST
 def send_json(self,data):
  body=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode();self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/api/status':return self.send_json(snapshot(self.root))
  if path=='/api/services':return self.send_json(service_snapshot(self.root))
  if path=='/api/features':return self.send_json(FeatureControl(self.root).snapshot())
  if path=='/api/ai-health':return self.send_json(ai_snapshot(self.root))
  if path=='/api/tickets':return self.send_json(ticket_snapshot(self.root))
  if path=='/api/ticket-history':return self.send_json(history_snapshot(self.root))
  name='index.html' if path=='/' else path.lstrip('/')
  if name not in {'index.html','app.css','app.js'}:self.send_error(404);return
  file=self.static/name
  try:body=file.read_bytes()
  except OSError:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(file.name)[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,fmt,*args):return
class Server(ThreadingHTTPServer):daemon_threads=True
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='~/SOC-Automation');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765);a=p.parse_args()
 if a.host!='127.0.0.1':raise SystemExit('Viewer wajib bind ke 127.0.0.1')
 root=Path(a.root).expanduser().resolve();Handler.root=root;Handler.static=(root/'current/viewer_static').resolve();server=Server((a.host,a.port),Handler)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
 return 0
if __name__=='__main__':raise SystemExit(main())
