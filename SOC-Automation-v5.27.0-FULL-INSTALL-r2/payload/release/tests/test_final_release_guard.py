from __future__ import annotations
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from final_release_guard import evaluate

with tempfile.TemporaryDirectory() as td:
    root = Path(td); shared = root / "shared"; current = root / "current"
    current.mkdir(); (shared / "workers" / "blue").mkdir(parents=True); (shared / "workers" / "green").mkdir(parents=True)
    (current / "VERSION").write_text("4.12.0-rc1\n")
    (shared / "master.json").write_text(json.dumps({"status":"running"}))
    (shared / "active_slot.json").write_text(json.dumps({"active_slot":"blue"}))
    active={"pid":os.getpid(),"slot":"blue","role":"active","status":"healthy","version":"4.12.0-rc1","in_flight":0}
    standby={"pid":os.getpid(),"slot":"green","role":"standby","status":"ready","version":"4.12.0-rc1","in_flight":0}
    (shared / "workers" / "blue" / "health.json").write_text(json.dumps(active))
    (shared / "workers" / "green" / "health.json").write_text(json.dumps(standby))
    (shared / "level3_qualification.json").write_text(json.dumps({"status":"passed","failure_count":0,"eligible_for_v5":True,"latest":{"version":"4.12.0-rc1"}}))
    con=sqlite3.connect(shared / "ticket_locks.sqlite3"); con.execute("CREATE TABLE leases (id TEXT PRIMARY KEY)"); con.commit(); con.close()
    result=evaluate(root)
    assert result["eligible"], result["failed_checks"]
print("Final v5 promotion guard tests: OK")
