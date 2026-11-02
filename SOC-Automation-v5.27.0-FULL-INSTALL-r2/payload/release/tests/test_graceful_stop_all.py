import tempfile
from pathlib import Path
from graceful_stop_all import runtime_inactive
with tempfile.TemporaryDirectory() as td:
 r=Path(td);assert runtime_inactive(r)['inactive'];p=r/'shared/control';p.mkdir(parents=True);(p/'master.pid.json').write_text('{}');assert not runtime_inactive(r)['inactive']
print('PASS test_graceful_stop_all')
