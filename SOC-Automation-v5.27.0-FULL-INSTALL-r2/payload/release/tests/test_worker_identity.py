from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from health_manager import HealthManager
from worker_identity import WorkerIdentity
with tempfile.TemporaryDirectory() as td:
 root=Path(td)
 blue=HealthManager(root,'4.7.0',WorkerIdentity('blue','active')); blue.register(); blue.mark_running()
 green=HealthManager(root,'4.7.0',WorkerIdentity('green','standby')); green.register(); green.mark_running()
 assert blue.pid_file != green.pid_file and blue.health_file != green.health_file
 b=json.loads(blue.health_file.read_text()); g=json.loads(green.health_file.read_text())
 assert (b['slot'],b['role'])==('blue','active')
 assert (g['slot'],g['role'])==('green','standby')
 blue.shutdown(); green.shutdown()
 assert not blue.pid_file.exists() and not green.pid_file.exists()
print('Worker identity and dual health channel tests: OK')
