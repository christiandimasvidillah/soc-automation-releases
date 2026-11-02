from __future__ import annotations
import json,os,tempfile
from pathlib import Path
DEFAULTS={"live_completed_seconds":30,"completed_history_days":7,"failed_history_days":30,"raw_audit_days":14,"sanitized_audit_days":90}
BOUNDS={"live_completed_seconds":(5,3600),"completed_history_days":(1,365),"failed_history_days":(7,730),"raw_audit_days":(1,365),"sanitized_audit_days":(7,1095)}
def validate(values):
 out=dict(DEFAULTS)
 for key,value in values.items():
  if key not in DEFAULTS:continue
  try:number=int(value)
  except (TypeError,ValueError):raise ValueError(f'{key} must be an integer')
  low,high=BOUNDS[key]
  if not low<=number<=high:raise ValueError(f'{key} must be between {low} and {high}')
  out[key]=number
 if out['sanitized_audit_days']<out['raw_audit_days']:raise ValueError('sanitized_audit_days must be >= raw_audit_days')
 if out['failed_history_days']<out['completed_history_days']:raise ValueError('failed_history_days must be >= completed_history_days')
 return out
def path_for(root):return Path(root).expanduser().resolve()/'shared/retention_policy.json'
def load(root):
 path=path_for(root)
 try:data=json.loads(path.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):data={}
 return validate(data if isinstance(data,dict) else {})
def save(root,values):
 policy=validate(values);path=path_for(root);path.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(prefix='.retention-policy-',dir=path.parent);os.close(fd);tmp=Path(name);tmp.write_text(json.dumps(policy,indent=2)+'\n',encoding='utf-8');os.chmod(tmp,0o600);os.replace(tmp,path);return policy
