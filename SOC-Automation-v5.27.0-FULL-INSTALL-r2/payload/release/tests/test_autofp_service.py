import tempfile
from pathlib import Path
from autofp_service import poll_once,reset_circuit,summary
from background_autofp_worker import init,setmode
class J:
 def search_tickets(self,**k):return [{'key':'CSOC-1'}]
 def close(self):pass
with tempfile.TemporaryDirectory() as td:
 r=Path(td);db=init(r);setmode(db,'SHADOW');x=poll_once(r,J());assert x['skipped'][0]['reason']=='raw_audit_not_ready';assert summary(r)['circuit']=='CLOSED';reset_circuit(r)
print('PASS test_autofp_service')
