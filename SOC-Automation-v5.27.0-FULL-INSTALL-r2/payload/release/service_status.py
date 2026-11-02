#!/usr/bin/env python3
import argparse,json,os,re,socket,sqlite3,subprocess
from datetime import datetime,timezone
from pathlib import Path

def rj(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def alive(p):
 try:p=int(p);os.kill(p,0);return p>1
 except Exception:return False
def extract_pid(path):
 p=Path(path);d=rj(p)
 keys=('pid','process_id','processId','master_pid','worker_pid','main_pid','MainPID')
 def walk(x):
  if isinstance(x,dict):
   for k in keys:
    if k in x:
     try:return int(x[k])
     except Exception:pass
   for v in x.values():
    q=walk(v)
    if q:return q
  if isinstance(x,list):
   for v in x:
    q=walk(v)
    if q:return q
  return None
 q=walk(d)
 if q:return q
 try:
  m=re.search(r'\b([1-9][0-9]{1,9})\b',p.read_text());return int(m.group(1)) if m else None
 except Exception:return None
def systemd(name):
 try:
  p=subprocess.run(['systemctl','--user','show',name,'--property=LoadState,ActiveState,SubState,MainPID','--no-pager'],text=True,capture_output=True,timeout=4)
  d={}
  for line in p.stdout.splitlines():
   if '=' in line:k,v=line.split('=',1);d[k]=v
  q=int(d.get('MainPID','0')) if d.get('MainPID','0').isdigit() else 0
  return d.get('LoadState','not-found'),d.get('ActiveState','inactive'),d.get('SubState','dead'),(q or None)
 except Exception:return 'unknown','unknown','unknown',None
def tmux_pid(session):
 try:
  p=subprocess.run(['tmux','list-panes','-t',session,'-F','#{pane_pid}'],text=True,capture_output=True,timeout=3)
  for x in p.stdout.split():
   if x.isdigit() and alive(int(x)):return int(x)
 except Exception:pass
 return None
def process_pid(tokens):
 try:
  p=subprocess.run(['ps','-u',str(os.getuid()),'-o','pid=,args='],text=True,capture_output=True,timeout=4)
  for line in p.stdout.splitlines():
   if all(t.lower() in line.lower() for t in tokens):
    q=line.strip().split(None,1)[0]
    if q.isdigit() and int(q)!=os.getpid():return int(q)
 except Exception:pass
 return None
def listening(port):
 try:
  with socket.create_connection(('127.0.0.1',port),timeout=.5):return True
 except Exception:return False
def sqlite_mode(path,default='UNKNOWN'):
 try:
  c=sqlite3.connect(f'file:{path}?mode=ro',uri=True,timeout=2);row=c.execute("SELECT v FROM state WHERE k='mode'").fetchone();c.close();return str(row[0]) if row else default
 except Exception:return default
def viewer(name,label,unit_name,session,script,port):
 load,a,sub,p=systemd(unit_name);p=p or tmux_pid(session) or process_pid([script])
 live=bool((a=='active' and alive(p)) or alive(p) or listening(port))
 return {'id':name,'name':label,'mode':'read-only','state':'RUNNING' if live else 'INACTIVE','pid':p,'health':'LISTENING' if listening(port) else ('ALIVE' if alive(p) else 'DEAD'),'detection':{'systemd_load':load,'systemd_active':a,'systemd_sub':sub,'tmux_session':session,'port':port}}
def snapshot(root):
 root=Path(root);sh=root/'shared';out=[]
 mp=extract_pid(sh/'soc_master.pid') or tmux_pid('soc-bot') or process_pid(['soc_master.py'])
 out.append({'id':'socmaster','name':'SocMaster','mode':None,'state':'RUNNING' if alive(mp) else 'STOPPED','pid':mp,'health':'ALIVE' if alive(mp) else 'NOT_RUNNING'})
 active=rj(sh/'active_slot.json').get('active_slot','blue')
 for c in ('blue','green'):
  p=extract_pid(sh/'workers'/c/'pid.json') or process_pid(['worker',c])
  out.append({'id':c+'_worker','name':c.title()+' worker','mode':'active' if c==active else 'standby','state':'RUNNING' if alive(p) else 'STOPPED','pid':p,'health':'HEALTHY' if alive(p) else 'NOT_RUNNING'})
 for sid,label,u,db,script in [('manual_false_incident','Manual False-Incident','soc-manual-false-incident.service','manual_false_incident.sqlite3','manual_false_incident_cli.py'),('background_autofp','Background Auto-FP','soc-autofp-worker.service','controlled_autofp.sqlite3','background_autofp_worker.py')]:
  load,a,sub,p=systemd(u);p=p or process_pid([script]);live=(a=='active' and alive(p)) or alive(p)
  out.append({'id':sid,'name':label,'mode':sqlite_mode(sh/db),'state':'RUNNING' if live else a.upper(),'pid':p,'health':'HEALTHY' if live else sub.upper(),'detection':{'systemd_load':load}})
 out.append(viewer('status_web_viewer','Status Web Viewer','soc-viewer.service','soc-viewer','soc_viewer.py',8765))
 out.append(viewer('documentation_viewer','Documentation Viewer','soc-docs-viewer.service','soc-docs','soc_docs_server.py',8766))
 ok=False
 for db in (sh/'soc_automation.db',sh/'ticket_locks.sqlite3',sh/'controlled_autofp.sqlite3'):
  if db.exists():
   try:c=sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=2);c.execute('select 1');c.close();ok=True;break
   except Exception:pass
 out.append({'id':'sqlite','name':'SQLite','mode':None,'state':'AVAILABLE' if ok else 'UNAVAILABLE','pid':None,'health':'OK' if ok else 'CHECK_REQUIRED'})
 return {'generated_at':datetime.now(timezone.utc).isoformat(),'services':out}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='~/SOC-Automation');p.add_argument('--json',action='store_true');a=p.parse_args();print(json.dumps(snapshot(Path(a.root).expanduser().resolve()),indent=2))
if __name__=='__main__':main()
