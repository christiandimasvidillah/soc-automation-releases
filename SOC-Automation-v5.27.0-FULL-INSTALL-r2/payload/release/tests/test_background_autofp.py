import hashlib,json,tempfile
from pathlib import Path
from autofp_candidate import create,verify
with tempfile.TemporaryDirectory() as td:
 r=Path(td);p=r/'shared/audit_logs/CSOC-1_raw.json';p.parent.mkdir(parents=True);src={'kibana.alert.uuid':'u','kibana.alert.rule.rule_id':'rid','kibana.alert.rule.name':'Rare SMB Connection to the Internet','host':{'id':'h'}};p.write_text(json.dumps({'hits':{'hits':[{'_index':'i','_source':src}]}}));rep={'decision':{'recommendation':'AUTO_FP_ELIGIBLE','blockers':[]}};c=create(r,'CSOC-1',rep,now=1);assert verify(r,c,now=2)['valid'];p.write_text('{}');assert 'raw_hash_mismatch' in verify(r,c,now=2)['reasons'];assert 'candidate_expired' in verify(r,c,now=1000)['reasons']
print('PASS test_background_autofp')
