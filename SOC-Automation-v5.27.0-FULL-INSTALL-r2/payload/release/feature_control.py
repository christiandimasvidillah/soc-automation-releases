#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, fcntl, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
FEATURES = (
    'jira_polling','siem_retrieval','privacy_sanitization','local_ai_detection',
    'gemini_analysis','virustotal_enrichment','sharing_allowlist',
    'telegram_notification','status_web_viewer','documentation_viewer',
)
PROFILES = {
 'FULL_AUTOMATION': {k: True for k in FEATURES},
 'JIRA_INTAKE_ONLY': {
  'jira_polling':True,'siem_retrieval':False,'privacy_sanitization':False,
  'local_ai_detection':False,'gemini_analysis':False,'virustotal_enrichment':False,
  'sharing_allowlist':False,'telegram_notification':True,'status_web_viewer':True,
  'documentation_viewer':False,
 },
 'PRIVACY_LOCAL_AI_ONLY': {
  'jira_polling':True,'siem_retrieval':True,'privacy_sanitization':True,
  'local_ai_detection':True,'gemini_analysis':False,'virustotal_enrichment':False,
  'sharing_allowlist':True,'telegram_notification':True,'status_web_viewer':True,
  'documentation_viewer':False,
 },
 'AI_ANALYSIS_NO_AUTO_ACTION': {
  'jira_polling':True,'siem_retrieval':True,'privacy_sanitization':True,
  'local_ai_detection':True,'gemini_analysis':True,'virustotal_enrichment':True,
  'sharing_allowlist':True,'telegram_notification':True,'status_web_viewer':True,
  'documentation_viewer':False,
 },
 'MAINTENANCE_SAFE_MODE': {k: False for k in FEATURES},
}

def now(): return datetime.now(timezone.utc).astimezone().isoformat()
def atomic(path: Path, data: dict):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(f'.{path.name}.{os.getpid()}.tmp')
 tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); os.chmod(tmp,0o600); os.replace(tmp,path)
def default_doc():
 return {'schema_version':SCHEMA_VERSION,'revision':1,'profile':'FULL_AUTOMATION','features':copy.deepcopy(PROFILES['FULL_AUTOMATION']),'updated_at':now(),'updated_by':os.getenv('USER','unknown')}
def validate(doc: dict) -> list[str]:
 errors=[]
 if doc.get('schema_version') != SCHEMA_VERSION: errors.append('unsupported_schema_version')
 features=doc.get('features')
 if not isinstance(features,dict): return errors+['features_not_object']
 for key in FEATURES:
  if not isinstance(features.get(key),bool): errors.append(f'invalid_boolean:{key}')
 return errors
def effective(doc: dict) -> dict:
 configured=dict(doc['features']); result={k:{'configured':v,'effective':v,'reason':None} for k,v in configured.items()}
 def block(key,reason):
  result[key]['effective']=False; result[key]['reason']=reason
 if not configured['jira_polling']:
  for key in ('siem_retrieval','privacy_sanitization','local_ai_detection','gemini_analysis','virustotal_enrichment','sharing_allowlist'): block(key,'jira_polling_disabled')
 if not result['siem_retrieval']['effective']:
  for key in ('privacy_sanitization','local_ai_detection','gemini_analysis','virustotal_enrichment','sharing_allowlist'): block(key,'siem_retrieval_disabled')
 if not result['privacy_sanitization']['effective']:
  block('local_ai_detection','privacy_sanitization_disabled'); block('gemini_analysis','privacy_sanitization_disabled')
 return result
class FeatureControl:
 def __init__(self,root: Path):
  self.root=Path(root).expanduser().resolve(); self.path=self.root/'shared/control/feature_flags.json'; self.audit=self.root/'shared/audit_logs/feature_control_audit.jsonl'; self.lock=self.root/'shared/control/feature_flags.lock'
 def load(self):
  if not self.path.exists(): atomic(self.path,default_doc())
  try: doc=json.loads(self.path.read_text(encoding='utf-8'))
  except Exception: doc=default_doc(); doc['profile']='FAIL_CLOSED'; doc['features']={k:False for k in FEATURES}; doc['features']['telegram_notification']=True
  errors=validate(doc)
  if errors: raise ValueError(','.join(errors))
  return doc
 def snapshot(self):
  doc=self.load(); raw=json.dumps(doc,sort_keys=True,separators=(',',':')).encode(); return {**doc,'config_hash':hashlib.sha256(raw).hexdigest(),'effective':effective(doc)}
 def save(self,doc,action):
  errors=validate(doc)
  if errors: raise ValueError(','.join(errors))
  self.lock.parent.mkdir(parents=True,exist_ok=True)
  with self.lock.open('a+') as handle:
   fcntl.flock(handle,fcntl.LOCK_EX); previous=self.load(); doc['revision']=int(previous.get('revision',0))+1; doc['updated_at']=now(); doc['updated_by']=os.getenv('USER','unknown'); atomic(self.path,doc)
   self.audit.parent.mkdir(parents=True,exist_ok=True)
   with self.audit.open('a',encoding='utf-8') as out: out.write(json.dumps({'timestamp':now(),'action':action,'revision':doc['revision'],'profile':doc['profile'],'updated_by':doc['updated_by']})+'\n')
   os.chmod(self.audit,0o600); fcntl.flock(handle,fcntl.LOCK_UN)
  return self.snapshot()
 def profile(self,name):
  if name not in PROFILES: raise ValueError('unknown_profile')
  doc=self.load(); doc['profile']=name; doc['features']=copy.deepcopy(PROFILES[name]); return self.save(doc,f'profile:{name}')
 def toggle(self,key,state):
  if key not in FEATURES: raise ValueError('unknown_feature')
  doc=self.load(); doc['profile']='CUSTOM'; doc['features'][key]=bool(state); return self.save(doc,f'toggle:{key}:{state}')

def main():
 p=argparse.ArgumentParser(); p.add_argument('--root',default='~/SOC-Automation'); sub=p.add_subparsers(dest='cmd',required=True)
 sub.add_parser('show'); q=sub.add_parser('profile'); q.add_argument('name',choices=sorted(PROFILES)); q=sub.add_parser('set'); q.add_argument('feature',choices=FEATURES); q.add_argument('state',choices=['ON','OFF']); sub.add_parser('profiles')
 a=p.parse_args(); ctl=FeatureControl(Path(a.root))
 if a.cmd=='show': out=ctl.snapshot()
 elif a.cmd=='profile': out=ctl.profile(a.name)
 elif a.cmd=='set': out=ctl.toggle(a.feature,a.state=='ON')
 else: out={'profiles':sorted(PROFILES),'features':list(FEATURES)}
 print(json.dumps(out,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
