#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from feature_control import FeatureControl

SCHEMA_VERSION = 2
SAFE_FIELDS = {
    "status", "pid", "slot", "role", "version", "heartbeat_at",
    "updated_at", "last_poll", "in_flight", "restart_count",
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def qualification_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "not evaluated",
            "failure_count": None,
            "eligible_for_v5": None,
            "data_state": "missing",
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "invalid",
            "failure_count": None,
            "eligible_for_v5": None,
            "data_state": "invalid",
        }
    if not isinstance(value, dict):
        return {
            "status": "invalid",
            "failure_count": None,
            "eligible_for_v5": None,
            "data_state": "invalid",
        }
    eligibility = value.get("eligible_for_v5")
    if not isinstance(eligibility, bool):
        eligibility = None
    failures = value.get("failure_count")
    if not isinstance(failures, int) or isinstance(failures, bool) or failures < 0:
        failures = None
    declared = str(value.get("status") or "unknown").strip().lower()
    return {
        "status": declared,
        "failure_count": failures,
        "eligible_for_v5": eligibility,
        "data_state": "available",
    }


def alive(value: object) -> bool:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return False
    if pid < 2:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def public(data: dict[str, Any]) -> dict[str, Any]:
    return {key: data[key] for key in SAFE_FIELDS if key in data}


def normalize_master(raw: dict[str, Any]) -> dict[str, Any]:
    pid = raw.get("pid") or raw.get("master_pid")
    active = alive(pid)
    declared = str(raw.get("status") or "unknown").lower()
    if declared == "running" and not active:
        display_status = "stale"
    elif active:
        display_status = "running"
    else:
        display_status = "unavailable"
    return {
        "pid": pid,
        "alive": active,
        "status": raw.get("status", "unknown"),
        "display_status": display_status,
        "version": (
            raw.get("target_version")
            or raw.get("version")
            or raw.get("master_version")
            or "unknown"
        ),
        "updated_at": raw.get("updated_at"),
        "restart_count": raw.get("restart_count", 0),
    }


def snapshot(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    shared = root / "shared"
    active_doc = read_json(shared / "active_slot.json")
    active = str(active_doc.get("active_slot") or "blue")
    if active not in {"blue", "green"}:
        active = "blue"
    standby = "green" if active == "blue" else "blue"
    master = normalize_master(read_json(shared / "master.json"))
    workers: dict[str, dict[str, Any]] = {}
    for slot in ("blue", "green"):
        raw = read_json(shared / "workers" / slot / "health.json")
        doc = public(raw)
        doc["pid"] = raw.get("pid")
        doc["alive"] = alive(doc.get("pid"))
        workers[slot] = doc
    try:
        version = (root / "current" / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        version = "unknown"
    sqlite_state = "missing"
    database = shared / "ticket_locks.sqlite3"
    if database.exists():
        try:
            connection = sqlite3.connect(
                f"file:{database}?mode=ro", uri=True, timeout=2
            )
            try:
                sqlite_state = connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]
            finally:
                connection.close()
        except sqlite3.Error:
            sqlite_state = "unavailable"
    qualification = qualification_status(shared / "level3_qualification.json")
    features = FeatureControl(root).snapshot()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "active_slot": active,
        "standby_slot": standby,
        "master": master,
        "workers": workers,
        "sqlite_integrity": sqlite_state,
        "qualification": qualification,
        "viewer_mode": "read-only",
        "feature_control": features,
    }
