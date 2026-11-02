#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,json,os,subprocess,sys
from pathlib import Path
SERVICES=('soc-manual-false-incident.service','soc-autofp-worker.service')
def run(cmd,timeout=330):
 try:
  p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout);return {'command':' '.join(map(str,cmd)),'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
 except Exception as e:return {'command':' '.join(map(str,cmd)),'returncode':99,'stderr':type(e).__name__}
def active(unit):
 p=subprocess.run(['systemctl','--user','is-active',unit],text=True,capture_output=True);state=(p.stdout.strip() or 'unknown');return {'unit':unit,'state':state,'inactive':state in {'inactive','failed','unknown','deactivating'} or p.returncode!=0}
def runtime_inactive(root):
 shared=Path(root)/'shared';mp=shared/'soc_master.pid'
 workers=[shared/'workers'/slot/'pid.json' for slot in ('blue','green')]
 return {'master_pid_path':str(mp),'master_pid_file':mp.exists(),'worker_pid_files':[str(p) for p in workers if p.exists()],'inactive':not mp.exists() and not any(p.exists() for p in workers)}
def execute(root,timeout=300):
 root=Path(root).expanduser().resolve();started=dt.datetime.now().astimezone();steps=[]
 resume=root/'shared/maintenance_resume_state.json'
 def read_mode(script):
  r=run([sys.executable,str(root/'current'/script),'--root',str(root),'status']);
  try:return json.loads(r.get('stdout') or '{}').get('mode','SHADOW')
  except Exception:return 'SHADOW'
 saved={'schema_version':1,'saved_at':started.isoformat(),'modes':{'manual_false_incident':read_mode('manual_false_incident_cli.py'),'background_autofp':read_mode('background_autofp_worker.py')}}
 resume.write_text(json.dumps(saved,indent=2)+'\n');os.chmod(resume,0o600)
 steps.append({'step':1,'name':'disable_manual_false_incident','result':run([sys.executable,str(root/'current/manual_false_incident_cli.py'),'--root',str(root),'mode','DISABLED'])})
 steps.append({'step':2,'name':'stop_manual_false_incident_service','result':run(['systemctl','--user','stop',SERVICES[0]])})
 steps.append({'step':3,'name':'disable_background_autofp','result':run([sys.executable,str(root/'current/background_autofp_worker.py'),'--root',str(root),'mode','DISABLED'])})
 steps.append({'step':4,'name':'stop_background_autofp_service','result':run(['systemctl','--user','stop',SERVICES[1]])})
 ctl=root/'manager/socctl.py';rr=run([sys.executable,str(ctl),'--root',str(root),'stop','--timeout',str(timeout)],timeout+30)
 if rr['returncode']!=0 and ('tidak aktif' in (rr.get('stderr','')+rr.get('stdout','')).lower()):rr['already_inactive']=True;rr['returncode']=0
 steps.append({'step':5,'name':'graceful_stop_main_runtime','result':rr})
 verification={'services':[active(x) for x in SERVICES],'runtime':runtime_inactive(root)}
 verification['all_inactive']=all(x['inactive'] for x in verification['services']) and verification['runtime']['inactive']
 steps.append({'step':6,'name':'verify_all_inactive','result':verification})
 ok=verification['all_inactive'] and all(x['result'].get('returncode',0)==0 for x in steps[:5])
 record={'schema_version':1,'action':'GRACEFUL_STOP_ALL','started_at':started.isoformat(),'finished_at':dt.datetime.now().astimezone().isoformat(),'user':os.getenv('USER','unknown'),'status':'PASS' if ok else 'PARTIAL_OR_FAILED','steps':steps,'verification':verification}
 audit=root/'shared/audit_logs/maintenance_actions.jsonl';audit.parent.mkdir(parents=True,exist_ok=True)
 try:
  with audit.open('a',encoding='utf-8') as f:f.write(json.dumps(record,separators=(',',':'))+'\n')
  os.chmod(audit,0o600);record['audit']={'written':True,'path':str(audit)}
 except Exception as e:record['status']='FAILED_AUDIT_WRITE';record['audit']={'written':False,'error':type(e).__name__}
 latest=root/'shared/audit_logs/graceful_stop_all_latest.json';latest.write_text(json.dumps(record,indent=2)+'\n');os.chmod(latest,0o600)
 return record
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('--timeout',type=int,default=300);a=p.parse_args();r=execute(a.root,a.timeout);print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='PASS' else 1)
if __name__=='__main__':main()
