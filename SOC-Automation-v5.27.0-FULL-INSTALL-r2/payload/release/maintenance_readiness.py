from __future__ import annotations
import json,shutil,time
from pathlib import Path

def read_json(path):
 try:value=json.loads(Path(path).read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):return {}
 return value if isinstance(value,dict) else {}

def evaluate(root,minimum_free_mb=1024,now=None):
 root=Path(root).expanduser().resolve();now=time.time() if now is None else float(now);checks=[]
 def add(name,status,detail,blocking=True):checks.append({'name':name,'status':status,'passed':status=='PASS','blocking':blocking,'detail':detail})
 version=(root/'current/VERSION').read_text(errors='replace').strip() if (root/'current/VERSION').is_file() else ''
 add('active_release','PASS' if version else 'FAIL',version or 'missing')
 workers=[]
 for path in sorted((root/'shared/workers').glob('*/health.json')):
  h=read_json(path);workers.append(h);status=str(h.get('status') or 'unknown');in_flight=int(h.get('in_flight') or 0);role=str(h.get('role') or path.parent.name);add('worker:'+path.parent.name,'PASS' if status in {'healthy','ready'} else 'FAIL',f'role={role} status={status} in_flight={in_flight}');add('worker_in_flight:'+path.parent.name,'PASS' if in_flight==0 else 'FAIL',str(in_flight))
 add('worker_inventory','PASS' if workers else 'WARN',f'{len(workers)} worker health files',blocking=False)
 preflight=read_json(root/'shared/configuration_preflight.json');add('configuration_preflight','PASS' if str(preflight.get('status')).upper()=='PASS' else 'WARN',str(preflight.get('status') or 'not evaluated'),blocking=False)
 qualification=read_json(root/'shared/release_qualification.json');add('release_qualification','PASS' if qualification.get('passed') is True else 'WARN',str(qualification.get('status') or 'not evaluated'),blocking=False)
 usage=shutil.disk_usage(root);free_mb=usage.free//(1024*1024);add('free_disk_space','PASS' if free_mb>=minimum_free_mb else 'FAIL',f'{free_mb} MB free; minimum {minimum_free_mb} MB')
 backup_dir=root/'shared/backups';backups=sorted(backup_dir.glob('*.tar.gz'),key=lambda p:p.stat().st_mtime,reverse=True) if backup_dir.is_dir() else []
 if backups:
  age_hours=round((now-backups[0].stat().st_mtime)/3600,1);add('recent_backup','PASS' if age_hours<=24 else 'WARN',f'{backups[0].name}; age={age_hours}h',blocking=False)
 else:add('recent_backup','WARN','no backup found',blocking=False)
 lock=root/'shared/deployment.json';deployment=read_json(lock);stage=str(deployment.get('stage') or deployment.get('status') or 'idle');busy=stage not in {'idle','completed','success','committed','rolled_back',''};add('deployment_idle','FAIL' if busy else 'PASS',stage)
 blocking_failures=[x for x in checks if x['blocking'] and x['status']=='FAIL'];warnings=[x for x in checks if x['status']=='WARN']
 return {'generated_at':now,'release':version,'ready':not blocking_failures,'status':'READY' if not blocking_failures else 'BLOCKED','summary':{'passed':sum(x['status']=='PASS' for x in checks),'failed':len(blocking_failures),'warnings':len(warnings),'in_flight':sum(int(x.get('in_flight') or 0) for x in workers)},'checks':checks}
