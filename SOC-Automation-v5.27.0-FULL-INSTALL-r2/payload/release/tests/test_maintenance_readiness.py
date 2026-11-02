import json,tempfile
from pathlib import Path
from maintenance_readiness import evaluate
with tempfile.TemporaryDirectory() as td:
 root=Path(td);(root/'current').mkdir();(root/'current/VERSION').write_text('5.10.0');p=root/'shared/workers/blue';p.mkdir(parents=True);(p/'health.json').write_text(json.dumps({'status':'healthy','role':'active','in_flight':0}));r=evaluate(root,minimum_free_mb=1);assert r['ready'] and r['status']=='READY';(p/'health.json').write_text(json.dumps({'status':'healthy','role':'active','in_flight':2}));r=evaluate(root,minimum_free_mb=1);assert not r['ready'] and any(x['name']=='worker_in_flight:blue' and x['status']=='FAIL' for x in r['checks']);(p/'health.json').write_text(json.dumps({'status':'degraded','role':'active','in_flight':0}));assert not evaluate(root,minimum_free_mb=1)['ready']
print('PASS test_maintenance_readiness')
