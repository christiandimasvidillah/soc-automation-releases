import tempfile
from pathlib import Path
from controlled_autofp import configure,execute
rep={'decision':{'recommendation':'AUTO_FP_ELIGIBLE','blockers':[],'connection_assessment':'NO_OBSERVED_SUCCESS','all_scoped_destinations_vt_clean':True}}
class J:
 def __init__(self):self.s='Waiting';self.t=[]
 def get_current_status(self,k):return self.s
 def transition(self,k,s):self.t.append(s);self.s=s;return True
with tempfile.TemporaryDirectory() as td:
 root=Path(td);assert execute(root,'CSOC-1',rep)['action']=='BLOCKED';configure(root,True);assert execute(root,'CSOC-1',rep)['action']=='WOULD_APPLY';j=J();r=execute(root,'CSOC-1',rep,j,True,now=1);assert r['action']=='APPLIED' and j.t==['False Incident','Done'];assert execute(root,'OTHER-1',rep)['action']=='BLOCKED'
print('PASS test_controlled_autofp')
