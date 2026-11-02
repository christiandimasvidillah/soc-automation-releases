from __future__ import annotations
import fcntl,json,os,re,tempfile,time,uuid
from pathlib import Path
EMAIL=re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@([A-Z0-9-]+(?:\.[A-Z0-9-]+)+)$",re.I)
TARGET_KEYS={'o365.audit.targetuserorgroupname','targetuserorgroupname'}
def paths(node,path=''):
 if isinstance(node,dict):
  for k,v in node.items():yield from paths(v,f'{path}.{k}' if path else str(k))
 elif isinstance(node,list):
  for v in node:yield from paths(v,path+'[]')
 else:yield path,node
def normalize(value):return str(value).strip().lower().strip(' <>;,')
def validate_value(kind,value):
 v=normalize(value);v=v[1:] if kind=='DOMAIN' and v.startswith('@') else v
 if kind=='EMAIL':
  if not EMAIL.fullmatch(v):raise ValueError('invalid email')
 else:
  if '@' in v or not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+',v):raise ValueError('invalid domain')
 return v
class Store:
 def __init__(self,root):
  self.root=Path(root).expanduser().resolve();self.path=self.root/'shared/control/approved_sharing_allowlist.json';self.audit=self.root/'shared/audit_logs/sharing_allowlist_audit.jsonl';self.lock=self.path.with_suffix('.lock');self.path.parent.mkdir(parents=True,exist_ok=True);self.audit.parent.mkdir(parents=True,exist_ok=True)
 def load(self):
  try:d=json.loads(self.path.read_text())
  except Exception:d={'schema_version':1,'entries':[]}
  return d if isinstance(d,dict) and isinstance(d.get('entries'),list) else {'schema_version':1,'entries':[]}
 def save(self,d,action,entry):
  with self.lock.open('a+') as lf:
   fcntl.flock(lf,fcntl.LOCK_EX);fd,n=tempfile.mkstemp(prefix='.allowlist-',dir=self.path.parent);os.close(fd);t=Path(n);t.write_text(json.dumps(d,indent=2)+'\n');os.chmod(t,0o600);os.replace(t,self.path);fcntl.flock(lf,fcntl.LOCK_UN)
  rec={'timestamp':time.time(),'action':action,'id':entry.get('id'),'type':entry.get('type'),'value':entry.get('value'),'classification':entry.get('classification'),'reference':entry.get('reference'),'operator':os.getenv('USER','unknown')}
  with self.audit.open('a') as f:f.write(json.dumps(rec,separators=(',',':'))+'\n')
  os.chmod(self.audit,0o600)
 def add(self,kind,value,classification,reason,reference,expires_at=None):
  kind=kind.upper();value=validate_value(kind,value);d=self.load()
  if any(x.get('type')==kind and x.get('value')==value for x in d['entries']):raise ValueError('duplicate entry')
  e={'id':uuid.uuid4().hex[:12],'type':kind,'value':value,'classification':classification.upper(),'reason':reason[:240],'reference':reference[:80],'enabled':True,'created_at':time.time(),'expires_at':expires_at or None};d['entries'].append(e);self.save(d,'ADD',e);return e
 def remove(self,entry_id):
  d=self.load();e=next((x for x in d['entries'] if x.get('id')==entry_id),None)
  if not e:raise ValueError('entry not found')
  d['entries']=[x for x in d['entries'] if x.get('id')!=entry_id];self.save(d,'REMOVE',e);return e
 def toggle(self,entry_id):
  d=self.load();e=next((x for x in d['entries'] if x.get('id')==entry_id),None)
  if not e:raise ValueError('entry not found')
  e['enabled']=not bool(e.get('enabled'));self.save(d,'ENABLE' if e['enabled'] else 'DISABLE',e);return e
 def match(self,email,now=None):
  now=time.time() if now is None else now;v=normalize(email);m=EMAIL.fullmatch(v)
  if not m:return None
  domain=m.group(1).lower()
  for e in self.load()['entries']:
   if not e.get('enabled'):continue
   if e.get('expires_at') and str(e['expires_at'])<time.strftime('%Y-%m-%d',time.localtime(now)):continue
   if (e.get('type')=='EMAIL' and e.get('value')==v) or (e.get('type')=='DOMAIN' and e.get('value')==domain):return e
  return None
GUEST_UPN=re.compile(r'^(?P<encoded>.+?)#ext#@(?P<tenant>[^@\s]+)$',re.I)

def _active_entries(store,now=None):
 now=time.time() if now is None else now
 result=[]
 for e in store.load().get('entries',[]):
  if not e.get('enabled'):continue
  if e.get('expires_at') and str(e['expires_at'])<time.strftime('%Y-%m-%d',time.localtime(now)):continue
  result.append(e)
 return result

def normalize_target(value,entries):
 raw=normalize(value)
 if EMAIL.fullmatch(raw):
  m=GUEST_UPN.fullmatch(raw)
  if not m:
   return {'status':'NORMALIZED','raw_value':raw,'identity_type':'EMAIL','normalized_email':raw,'normalized_domain':raw.rsplit('@',1)[1],'resource_tenant_domain':None,'confidence':'HIGH','ambiguous':False}
  encoded=m.group('encoded');tenant=m.group('tenant').rstrip('.').lower();candidates=[]
  # Deterministic reconstruction is bounded by the configured active allowlist.
  for e in entries:
   kind=str(e.get('type','')).upper();val=normalize(e.get('value',''))
   if kind=='EMAIL':
    if val.replace('@','_',1)==encoded:candidates.append((val,val.rsplit('@',1)[1],e,'HIGH'))
   elif kind=='DOMAIN':
    suffix='_'+val
    if encoded.endswith(suffix):
     local=encoded[:-len(suffix)]
     candidate=f'{local}@{val}'
     if local and EMAIL.fullmatch(candidate):candidates.append((candidate,val,e,'MEDIUM'))
  unique={(x[0],x[1],x[2].get('id')):x for x in candidates}
  candidates=list(unique.values())
  if len(candidates)==1:
   email,domain,entry,confidence=candidates[0]
   return {'status':'NORMALIZED','raw_value':raw,'identity_type':'ENTRA_GUEST_UPN','normalized_email':email,'normalized_domain':domain,'resource_tenant_domain':tenant,'confidence':confidence,'ambiguous':False,'matched_entry':entry}
  return {'status':'AMBIGUOUS','raw_value':raw,'identity_type':'ENTRA_GUEST_UPN','normalized_email':None,'normalized_domain':None,'resource_tenant_domain':tenant,'confidence':'LOW','ambiguous':True,'ambiguity_reason':'multiple_allowlist_candidates' if candidates else 'no_allowlisted_external_identity'}
 return {'status':'INVALID','raw_value':raw,'identity_type':'UNKNOWN','normalized_email':None,'normalized_domain':None,'resource_tenant_domain':None,'confidence':'NONE','ambiguous':True,'ambiguity_reason':'invalid_target_identity'}

def evaluate_alert(root,raw_json,summary):
 try:data=json.loads(raw_json)
 except Exception:return {'matched':False,'reason':'invalid_json'}
 if 'unauthorized file sharing to external domain' not in str(summary).casefold():return {'matched':False,'reason':'rule_mismatch'}
 vals=list(paths(data));operations={normalize(v) for p,v in vals if p.casefold().endswith(('operation','event.action'))};providers={normalize(v) for p,v in vals if p.casefold().endswith(('event.provider','provider'))};targets=[]
 for p,v in vals:
  if any(p.casefold().endswith(k) for k in TARGET_KEYS):
   targets.extend([normalize(x) for x in re.split(r'[;,]',str(v)) if '@' in x])
 text=json.dumps(data).casefold()
 if 'addedtosecurelink' not in operations or not ({'onedrive','sharepoint'}&providers):return {'matched':False,'reason':'context_mismatch'}
 if any(x in text for x in ('anonymouslink','anyone link','sharinglinkcreated')):return {'matched':False,'reason':'anonymous_indicator'}
 store=Store(root);entries=_active_entries(store);normalized=[normalize_target(x,entries) for x in targets]
 if not targets:return {'matched':False,'reason':'target_missing','target_count':0,'identity_normalization':[]}
 if any(x.get('ambiguous') for x in normalized):return {'matched':False,'reason':'guest_identity_ambiguous','target_count':len(targets),'identity_normalization':normalized}
 matches=[]
 for identity in normalized:
  entry=identity.get('matched_entry') or store.match(identity.get('normalized_email',''))
  if entry is None:return {'matched':False,'reason':'unapproved_target','target_count':len(targets),'identity_normalization':normalized}
  matches.append(entry)
 for identity in normalized:identity.pop('matched_entry',None)
 return {'matched':True,'reason':'APPROVED_SHARING_GUEST_IDENTITY','target_count':len(targets),'entry_ids':sorted({x['id'] for x in matches}),'identity_normalization':normalized,'recommendation':'AUTO_FP_ELIGIBLE','blockers':[]}
