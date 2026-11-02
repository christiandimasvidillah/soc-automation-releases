from __future__ import annotations
import json, os, tempfile, threading, time
from pathlib import Path
from cutover_manager import CutoverManager
from role_gate import ActiveSlotGate
with tempfile.TemporaryDirectory() as td:
 root=Path(td); workers=root/'shared'/'workers'
 for slot,role,status in [('blue','active','healthy'),('green','standby','ready')]:
  d=workers/slot; d.mkdir(parents=True)
  (d/'health.json').write_text(json.dumps({'pid':os.getpid(),'slot':slot,'role':role,'status':status,'in_flight':0,'pending_workers':0}))
 gate=ActiveSlotGate(root/'shared','blue')
 def transition():
  while gate.active_slot()!='green': time.sleep(.01)
  (workers/'blue'/'health.json').write_text(json.dumps({'pid':os.getpid(),'slot':'blue','role':'standby','status':'ready','in_flight':0,'pending_workers':0}))
  (workers/'green'/'health.json').write_text(json.dumps({'pid':os.getpid(),'slot':'green','role':'active','status':'healthy','in_flight':0,'pending_workers':0}))
 threading.Thread(target=transition,daemon=True).start()
 manager=CutoverManager(root,timeout=2); manager.acquire()
 try: manager.cutover('green')
 finally: manager.release()
 state=json.loads((root/'shared'/'cutover.json').read_text())
 assert state['status']=='cutover_complete'
 assert gate.active_slot()=='green'
print('Controlled cutover and drain tests: OK')
