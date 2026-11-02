#!/usr/bin/env python3
import argparse,datetime as dt,json,os,subprocess,sys,time
from pathlib import Path
SERVICES=('soc-manual-false-incident.service','soc-autofp-worker.service')
def run(c,t=60):
 try:
  p=subprocess.run(c,text=True,capture_output=True,timeout=t);return {'command':' '.join(map(str,c)),'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
 except Exception as e:return {'command':' '.join(map(str,c)),'returncode':99,'stderr':type(e).__name__}
def mode(root,kind,value):
 script='manual_false_incident_cli.py' if kind=='manual_false_incident' else 'background_autofp_worker.py'
 return run([sys.executable,str(root/'current'/script),'--root',str(root),'mode',value])
def service_state(u):
 p=subprocess.run(['systemctl','--user','is-active',u],text=True,capture_output=True);s=p.stdout.strip() or 'unknown';return {'unit':u,'state':s,'active':s=='active'}
def execute(root,timeout=120,manual_mode=None,autofp_mode=None):
 root=Path(root).expanduser().resolve();start=dt.datetime.now().astimezone();steps=[];resume=root/'shared/maintenance_resume_state.json';modes={'manual_false_incident':'SHADOW','background_autofp':'SHADOW'};source='safe_default'
 if resume.is_file():
  try:
   data=json.loads(resume.read_text());saved=data.get('modes',{});modes['manual_false_incident']=saved.get('manual_false_incident','SHADOW');modes['background_autofp']=saved.get('background_autofp','SHADOW');source='saved_pre_stop_modes'
   for key in tuple(modes):
    if modes[key]=='DISABLED':modes[key]='SHADOW';source='saved_modes_normalized_to_safe_shadow'
  except Exception:pass
 for key,value,allowed in [('manual_false_incident',manual_mode,{'DISABLED','SHADOW','ACTIVE'}),('background_autofp',autofp_mode,{'DISABLED','SHADOW','APPROVAL','LIMITED','GLOBAL'})]:
  if value is not None:
   value=value.upper()
   if value not in allowed:raise ValueError('invalid_'+key+'_mode')
   modes[key]=value
 if manual_mode is not None or autofp_mode is not None:source='operator_selected'
 # Start main runtime first.
 shared=root/'shared';master_pid=shared/'soc_master.pid'
 active=master_pid.exists()
 if active:rr={'returncode':0,'already_active':True}
 else:
  out=root/'shared/logs/soc_master.out';shell=f'cd {root / "manager"} && export PYTHONPATH={root / "current"}:{root / "manager"} && exec {sys.executable} soc_master.py --root {root} >> {out} 2>&1';rr=run(['tmux','new-session','-d','-s','soc-bot',shell])
  deadline=time.time()+timeout
  while rr['returncode']==0 and time.time()<deadline:
   if master_pid.exists() and any((shared/'workers'/slot/'pid.json').exists() for slot in ('blue','green')):break
   time.sleep(1)
 steps.append({'step':1,'name':'start_main_runtime','result':rr})
 steps.append({'step':2,'name':'start_manual_false_incident_service','result':run(['systemctl','--user','start',SERVICES[0]])})
 steps.append({'step':3,'name':'start_background_autofp_service','result':run(['systemctl','--user','start',SERVICES[1]])})
 steps.append({'step':4,'name':'restore_manual_false_incident_mode','target_mode':modes['manual_false_incident'],'result':mode(root,'manual_false_incident',modes['manual_false_incident'])})
 steps.append({'step':5,'name':'restore_background_autofp_mode','target_mode':modes['background_autofp'],'result':mode(root,'background_autofp',modes['background_autofp'])})
 active_slot='unknown'
 try:active_slot=json.loads((shared/'active_slot.json').read_text()).get('active_slot','unknown')
 except Exception:pass
 worker_pid=shared/'workers'/active_slot/'pid.json'
 ver={'runtime':{'master_pid_path':str(master_pid),'master_pid_file':master_pid.exists(),'active_slot':active_slot,'worker_pid_path':str(worker_pid),'worker_pid_file':worker_pid.exists()},'services':[service_state(x) for x in SERVICES],'mode_source':source,'restored_modes':modes}
 ver['all_active']=ver['runtime']['master_pid_file'] and ver['runtime']['worker_pid_file'] and all(x['active'] for x in ver['services'])
 ok=ver['all_active'] and all(x['result'].get('returncode',1)==0 for x in steps)
 rec={'schema_version':1,'action':'START_ALL','started_at':start.isoformat(),'finished_at':dt.datetime.now().astimezone().isoformat(),'user':os.getenv('USER','unknown'),'status':'PASS' if ok else 'PARTIAL_OR_FAILED','steps':steps,'verification':ver}
 audit=root/'shared/audit_logs/maintenance_actions.jsonl';audit.parent.mkdir(parents=True,exist_ok=True)
 try:
  with audit.open('a') as f:f.write(json.dumps(rec,separators=(',',':'))+'\n')
  os.chmod(audit,0o600);rec['audit']={'written':True,'path':str(audit)}
 except Exception as e:rec['status']='FAILED_AUDIT_WRITE';rec['audit']={'written':False,'error':type(e).__name__}
 latest=root/'shared/audit_logs/start_all_latest.json';latest.write_text(json.dumps(rec,indent=2)+'\n');os.chmod(latest,0o600);return rec
def build_parser():
 p=argparse.ArgumentParser()
 p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation')
 p.add_argument('--timeout',type=int,default=120)
 p.add_argument('--manual-mode',choices=['DISABLED','SHADOW','ACTIVE'])
 p.add_argument('--autofp-mode',choices=['DISABLED','SHADOW','APPROVAL','LIMITED','GLOBAL'])
 return p
def main():
 a=build_parser().parse_args()
 r=execute(a.root,a.timeout,a.manual_mode,a.autofp_mode)
 print(json.dumps(r,indent=2))
 raise SystemExit(0 if r['status']=='PASS' else 1)
if __name__=='__main__':main()
