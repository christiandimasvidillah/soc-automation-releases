import json,tempfile
from pathlib import Path
from smb_evidence_collector import collect
class Resp:
 def __init__(self,h):self.h=h
 def json(self):return {'hits':{'hits':self.h}}
class Client:
 class S:alert_search_url='x'
 settings=S()
 def __init__(self,event):self.event=event;self.n=0;self.bodies=[]
 def _request(self,*a,**k):self.bodies.append(k['json']);self.n+=1;return Resp([self.event] if self.n==1 else [])
a={'kibana.alert.rule.name':'Rare SMB Connection to the Internet','@timestamp':'2026-08-14T13:45:36Z','host':{'id':'h','risk':{'calculated_level':'Low'}},'user':{'risk':{'calculated_level':'Low'}},'process':{'pid':4,'entity_id':'p'},'destination':{'ip':'104.26.11.44','port':445}}
e={'host':{'id':'h'},'process':{'entity_id':'p'},'destination':{'ip':'104.26.11.44','port':445},'event':{'action':['connection_attempted'],'outcome':'unknown'}}
with tempfile.TemporaryDirectory() as td:
 c=Client(e);r=collect(a,Path(td),c,lambda ip,root:{'status':'PASS','stats':{'malicious':0,'suspicious':0}},now=1);assert r['decision']['recommendation']=='AUTO_FP_ELIGIBLE';assert r['auto_fp'] is False;assert len(c.bodies)==2;assert (Path(td)/'shared/audit_logs/smb_dry_run_latest.json').exists()
print('PASS test_smb_evidence_collector')
