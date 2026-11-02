from __future__ import annotations
import json, os, tempfile, threading, time
from pathlib import Path
from cutover_manager import CutoverError, CutoverManager
from role_gate import ActiveSlotGate

def write(path, data):
 path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data))

def health(slot, role, status):
 return {'pid':os.getpid(),'slot':slot,'role':role,'status':status,'in_flight':0,'pending_workers':0}

with tempfile.TemporaryDirectory() as td:
 root=Path(td); workers=root/'shared'/'workers'; gate=ActiveSlotGate(root/'shared','blue')
 write(workers/'blue'/'health.json',health('blue','active','healthy'))
 write(workers/'green'/'health.json',health('green','standby','ready'))
 def simulate():
  while gate.active_slot()!='green': time.sleep(.01)
  write(workers/'blue'/'health.json',health('blue','standby','ready'))
  write(workers/'green'/'health.json',health('green','active','healthy'))
  time.sleep(.15)
  write(workers/'green'/'health.json',health('green','active','unhealthy'))
  while gate.active_slot()!='blue': time.sleep(.01)
  write(workers/'blue'/'health.json',health('blue','active','healthy'))
  write(workers/'green'/'health.json',health('green','standby','ready'))
 threading.Thread(target=simulate,daemon=True).start()
 manager=CutoverManager(root,timeout=2,stabilization=.5); manager.acquire()
 try:
  try: manager.cutover('green')
  except CutoverError: pass
  else: raise AssertionError('Expected stabilization failure')
 finally: manager.release()
 audit=json.loads((root/'shared'/'cutover.json').read_text())
 assert gate.active_slot()=='blue'
 assert audit['status']=='failed_back', audit
print('Phase K stabilization and automatic failback tests: OK')
