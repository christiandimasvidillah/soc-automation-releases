from pathlib import Path
import json, os, sqlite3, tempfile
from soc_status import snapshot
with tempfile.TemporaryDirectory() as td:
 root=Path(td); shared=root/'shared'; (root/'current').mkdir(parents=True); (shared/'workers'/'blue').mkdir(parents=True); (shared/'workers'/'green').mkdir(parents=True)
 (root/'current'/'VERSION').write_text('5.1.0\n'); (shared/'active_slot.json').write_text('{"active_slot":"blue"}'); (shared/'master.json').write_text(json.dumps({'pid':os.getpid(),'status':'running','secret':'must-not-leak'}))
 for s,state,role in [('blue','healthy','active'),('green','ready','standby')]: (shared/'workers'/s/'health.json').write_text(json.dumps({'pid':os.getpid(),'slot':s,'status':state,'role':role,'version':'5.1.0','in_flight':0,'token':'must-not-leak'}))
 con=sqlite3.connect(shared/'ticket_locks.sqlite3'); con.execute('create table x(a)'); con.close(); out=snapshot(root)
 assert out['master']['alive'] and out['workers']['blue']['alive']; assert 'secret' not in out['master']; assert 'token' not in out['workers']['blue']; assert out['viewer_mode']=='read-only'; assert out['sqlite_integrity']=='ok'
print('Control surface tests: OK')
