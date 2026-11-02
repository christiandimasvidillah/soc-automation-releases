import json,tempfile,time
from pathlib import Path
from maintenance_readiness import evaluate
with tempfile.TemporaryDirectory() as td:
 root=Path(td);(root/'current').mkdir();(root/'current/VERSION').write_text('5.11.0')
 worker=root/'shared/workers/blue';worker.mkdir(parents=True);(worker/'health.json').write_text(json.dumps({'status':'healthy','role':'active','in_flight':0}))
 backup_dir=root/'shared/backups';backup_dir.mkdir(parents=True);backup=backup_dir/'pre-update-5.11.0-test.tar.gz';backup.write_bytes(b'test');now=time.time();
 deployment=root/'shared/deployment.json';deployment.write_text(json.dumps({'stage':'committed'}))
 result=evaluate(root,minimum_free_mb=1,now=now)
 checks={x['name']:x for x in result['checks']}
 assert checks['recent_backup']['status']=='PASS',checks['recent_backup']
 assert backup.name in checks['recent_backup']['detail']
 assert checks['deployment_idle']['status']=='PASS',checks['deployment_idle']
 assert checks['deployment_idle']['detail']=='committed'
 assert result['ready'] is True,result
print('PASS test_maintenance_readiness_hotfix')
