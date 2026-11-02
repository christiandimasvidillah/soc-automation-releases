import json,tempfile
from pathlib import Path
from runtime_health_center import build_health_center
with tempfile.TemporaryDirectory() as td:
 root=Path(td);p=root/'shared/workers/blue';p.mkdir(parents=True);(p/'health.json').write_text(json.dumps({'slot':'blue','role':'active','status':'healthy','in_flight':2,'intake_circuit_breaker':'closed'}));(root/'shared/configuration_preflight.json').write_text(json.dumps({'status':'PASS','summary':{'failed':0,'warnings':0}}));(root/'shared/release_qualification.json').write_text(json.dumps({'status':'passed','passed':True,'summary':{'failed':0}}));r=build_health_center(root,now=100);assert r['overall_status']=='healthy' and r['summary']['in_flight']==2;(p/'health.json').write_text(json.dumps({'slot':'blue','role':'active','status':'degraded','intake_circuit_breaker':'open'}));r=build_health_center(root,now=100);assert r['overall_status']=='degraded' and r['summary']['open_circuits']==1
print('PASS test_runtime_health_center')
