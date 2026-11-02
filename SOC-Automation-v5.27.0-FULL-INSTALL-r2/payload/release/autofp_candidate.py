from __future__ import annotations
import hashlib,json,os,tempfile,time
from pathlib import Path
from smb_evidence_collector import normalize_alert_payload

def val(o,key):return o.get(key) if isinstance(o,dict) else None
def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);fd,n=tempfile.mkstemp(prefix='.candidate-',dir=path.parent);os.close(fd);p=Path(n);p.write_text(json.dumps(data,indent=2)+'\n');os.chmod(p,0o600);os.replace(p,path)
def create(root,ticket,report,now=None,ttl=900):
 root=Path(root);raw=root/'shared/audit_logs'/f'{ticket}_raw.json';b=raw.read_bytes();payload=json.loads(b);src=normalize_alert_payload(payload);now=time.time() if now is None else now
 c={'schema_version':1,'ticket_key':ticket,'alert_uuid':val(src,'kibana.alert.uuid'),'alert_index':(payload.get('hits',{}).get('hits',[{}])[0].get('_index') if isinstance(payload.get('hits'),dict) else None),'rule_id':val(src,'kibana.alert.rule.rule_id'),'rule_name':val(src,'kibana.alert.rule.name'),'host_id':(src.get('host') or {}).get('id'),'raw_sha256':hashlib.sha256(b).hexdigest(),'evaluated_at':now,'valid_until':now+ttl,'policy_version':'5.19.0','decision':report.get('decision',{})}
 c['idempotency_key']=hashlib.sha256(f"{ticket}|{c['alert_uuid']}|5.19.0".encode()).hexdigest();atomic(root/'shared/audit_logs/auto_fp_candidates'/f'{ticket}.json',c);return c
def verify(root,candidate,now=None):
 root=Path(root);now=time.time() if now is None else now;ticket=candidate.get('ticket_key','');raw=root/'shared/audit_logs'/f'{ticket}_raw.json';reasons=[]
 if not raw.is_file():reasons.append('raw_missing')
 else:
  b=raw.read_bytes()
  if hashlib.sha256(b).hexdigest()!=candidate.get('raw_sha256'):reasons.append('raw_hash_mismatch')
  try:
   src=normalize_alert_payload(json.loads(b))
   if src.get('kibana.alert.uuid')!=candidate.get('alert_uuid'):reasons.append('alert_uuid_mismatch')
  except Exception:reasons.append('raw_invalid')
 if now>float(candidate.get('valid_until',0)):reasons.append('candidate_expired')
 d=candidate.get('decision') or {}
 if d.get('recommendation')!='AUTO_FP_ELIGIBLE' or d.get('blockers'):reasons.append('candidate_not_eligible')
 return {'valid':not reasons,'reasons':reasons}
