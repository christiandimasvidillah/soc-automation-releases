from __future__ import annotations
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from qualification_manager import FinalQualification

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    shared = root / "shared"
    (root / "current").mkdir(parents=True)
    (shared / "workers" / "blue").mkdir(parents=True)
    (shared / "workers" / "green").mkdir(parents=True)
    (root / "current" / "VERSION").write_text("4.12.0-rc1\n")
    (shared / "master.json").write_text(json.dumps({"status": "running"}))
    (shared / "active_slot.json").write_text(json.dumps({"active_slot": "blue"}))
    common = {"pid": os.getpid(), "version": "4.12.0-rc1", "in_flight": 0}
    (shared / "workers" / "blue" / "health.json").write_text(json.dumps({**common, "slot": "blue", "role": "active", "status": "healthy"}))
    (shared / "workers" / "green" / "health.json").write_text(json.dumps({**common, "slot": "green", "role": "standby", "status": "ready"}))
    con = sqlite3.connect(shared / "ticket_locks.sqlite3")
    con.execute("CREATE TABLE leases (ticket TEXT PRIMARY KEY)")
    con.commit(); con.close()
    runner = FinalQualification(root, duration=0.35, interval=0.1)
    assert runner.run() == 0
    report = json.loads((shared / "level3_qualification.json").read_text())
    assert report["status"] == "passed"
    assert report["eligible_for_v5"] is True
    assert report["failure_count"] == 0
print("Final Level 3 qualification tests: OK")
