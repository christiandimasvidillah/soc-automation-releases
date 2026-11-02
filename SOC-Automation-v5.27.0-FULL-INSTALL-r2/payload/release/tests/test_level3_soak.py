from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from level3_soak import Level3Soak
with tempfile.TemporaryDirectory() as td:
 root=Path(td); shared=root/'shared'; (shared/'workers'/'blue').mkdir(parents=True); (shared/'workers'/'green').mkdir(parents=True)
 (shared/'master.json').write_text(json.dumps({'status':'running'}))
 (shared/'active_slot.json').write_text(json.dumps({'active_slot':'blue'}))
 (shared/'workers'/'blue'/'health.json').write_text(json.dumps({'pid':os.getpid(),'slot':'blue','role':'active','status':'healthy','in_flight':0}))
 (shared/'workers'/'green'/'health.json').write_text(json.dumps({'pid':os.getpid(),'slot':'green','role':'standby','status':'ready','in_flight':0}))
 runner=Level3Soak(root,duration=.4,interval=.1)
 assert runner.run()==0
 report=json.loads((shared/'level3_soak.json').read_text())
 assert report['status']=='passed' and report['failure_count']==0 and report['samples']>=2
print('Level 3 soak validator tests: OK')
