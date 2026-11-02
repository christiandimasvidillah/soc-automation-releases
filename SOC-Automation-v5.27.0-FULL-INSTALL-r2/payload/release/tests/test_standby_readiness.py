from __future__ import annotations

import json
import tempfile
from pathlib import Path

from standby_worker import StandbyWorker


WORKER = r'''
import json, os, signal, time
from pathlib import Path
root = Path(os.environ["TEST_ROOT"])
runtime = root / "shared" / "workers" / "green"
runtime.mkdir(parents=True, exist_ok=True)
pid = os.getpid()
def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
write(runtime / "pid.json", {"pid": pid, "version": "4.9.0"})
write(runtime / "health.json", {
    "pid": pid, "version": "4.9.0", "slot": "green", "role": "standby",
    "status": "ready", "poll_cycle": 0, "tickets_submitted": 0
})
running = True
def stop(*_):
    global running
    running = False
signal.signal(signal.SIGTERM, stop)
while running:
    time.sleep(0.05)
(runtime / "pid.json").unlink(missing_ok=True)
'''

with tempfile.TemporaryDirectory(prefix="phase-i-") as td:
    root = Path(td)
    release = root / "release"
    release.mkdir()
    (release / "VERSION").write_text("4.9.0\n", encoding="utf-8")
    (release / "fake_worker.py").write_text(WORKER, encoding="utf-8")
    import os
    os.environ["TEST_ROOT"] = str(root)
    standby = StandbyWorker(root, timeout=5, shutdown_timeout=5)
    standby.start(release, "fake_worker.py")
    state = standby.snapshot()
    assert state["standby_alive"] is True
    assert state["standby_status"] == "ready"
    assert state["standby_role"] == "standby"
    assert state["standby_version"] == "4.9.0"
    assert state["standby_poll_cycle"] == 0
    assert state["standby_tickets_submitted"] == 0
    standby.stop()
    assert standby.running() is False

print("Green standby lifecycle and readiness tests: OK")
