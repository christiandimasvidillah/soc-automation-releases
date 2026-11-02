from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from health_manager import HealthManager, HealthManagerError

with tempfile.TemporaryDirectory(prefix="soc-health-test-") as temp_name:
    shared = Path(temp_name)
    health = HealthManager(shared, "4.2.0")
    health.register()
    assert (shared / "soc_automation.pid").exists()
    health.mark_running()
    health.mark_poll_started(poll_cycle=1, in_flight=0, pending_workers=0)
    health.mark_poll_finished(
        submitted=2,
        in_flight=2,
        pending_workers=2,
    )
    health.mark_worker_finished(successful=True)
    health.mark_worker_finished(successful=False)
    payload = json.loads((shared / "health.json").read_text(encoding="utf-8"))
    assert payload["status"] == "healthy"
    assert payload["version"] == "4.2.0"
    assert payload["poll_cycle"] == 1
    assert payload["tickets_submitted"] == 2
    assert payload["tickets_completed"] == 1
    assert payload["tickets_failed"] == 1
    health.request_shutdown(signal_name="SIGTERM")
    health.shutdown(exit_code=0)
    assert not (shared / "soc_automation.pid").exists()
    stopped = json.loads((shared / "health.json").read_text(encoding="utf-8"))
    assert stopped["status"] == "stopped"
    assert stopped["exit_code"] == 0

print("Health manager regression test: OK")
