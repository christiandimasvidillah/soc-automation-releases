from __future__ import annotations

import json
import tempfile
from pathlib import Path

from health_manager import HealthManager
from role_gate import ActiveSlotGate
from worker_identity import WorkerIdentity


with tempfile.TemporaryDirectory(prefix="role-gate-") as temp_name:
    shared = Path(temp_name)
    blue_gate = ActiveSlotGate(shared, "blue")
    green_gate = ActiveSlotGate(shared, "green")

    assert blue_gate.active_slot() == "blue"
    assert blue_gate.is_active() is True
    assert green_gate.is_active() is False
    assert blue_gate.role() == "active"
    assert green_gate.role() == "standby"

    blue_health = HealthManager(
        shared,
        "4.8.0",
        WorkerIdentity("blue", "active"),
    )
    green_health = HealthManager(
        shared,
        "4.8.0",
        WorkerIdentity("green", "standby"),
    )
    blue_health.register()
    green_health.register()
    blue_health.mark_role(blue_gate.role(), active_slot=blue_gate.active_slot())
    green_health.mark_role(green_gate.role(), active_slot=green_gate.active_slot())

    blue_state = json.loads(blue_health.health_file.read_text(encoding="utf-8"))
    green_state = json.loads(green_health.health_file.read_text(encoding="utf-8"))
    assert blue_state["status"] == "healthy"
    assert blue_state["role"] == "active"
    assert green_state["status"] == "ready"
    assert green_state["role"] == "standby"

    switched = blue_gate.switch("green", updated_by="test")
    assert switched["active_slot"] == "green"
    assert switched["generation"] == 2
    assert blue_gate.is_active() is False
    assert green_gate.is_active() is True

    blue_health.mark_role(blue_gate.role(), active_slot=blue_gate.active_slot())
    green_health.mark_role(green_gate.role(), active_slot=green_gate.active_slot())
    blue_state = json.loads(blue_health.health_file.read_text(encoding="utf-8"))
    green_state = json.loads(green_health.health_file.read_text(encoding="utf-8"))
    assert blue_state["status"] == "ready"
    assert green_state["status"] == "healthy"

    blue_health.shutdown()
    green_health.shutdown()

print("Active/standby role gate tests: OK")
