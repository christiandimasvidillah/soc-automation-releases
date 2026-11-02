from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
MASTER = PROJECT / "soc_master.py"
CTL = PROJECT / "socctl.py"
FAKE = PROJECT / "tests" / "fake_worker.py"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def wait_for(predicate, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise AssertionError("Timeout menunggu kondisi test")


with tempfile.TemporaryDirectory(prefix="soc-master-test-") as temp_name:
    root = Path(temp_name)
    release = root / "releases" / "v4.3.0"
    shared = root / "shared"
    release.mkdir(parents=True)
    shared.mkdir(parents=True)
    (release / "tests").mkdir()
    shutil.copy2(FAKE, release / "tests" / "fake_worker.py")
    (release / "VERSION").write_text("4.3.0\n", encoding="utf-8")
    (root / "current").symlink_to(Path("releases/v4.3.0"), target_is_directory=True)

    env = os.environ.copy()
    env["FAKE_SOC_ROOT"] = str(root)
    master = subprocess.Popen(
        [
            sys.executable,
            str(MASTER),
            "--root", str(root),
            "--startup-timeout", "10",
            "--shutdown-timeout", "10",
            "--control-interval", "0.1",
            "--worker-script", "tests/fake_worker.py",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for(
            lambda: read_json(shared / "master.json").get("status") == "running"
            and read_json(shared / "health.json").get("status") == "healthy"
        )
        first_pid = read_json(shared / "soc_automation.pid").get("pid")
        assert isinstance(first_pid, int)

        status = subprocess.run(
            [sys.executable, str(CTL), "--root", str(root), "status"],
            check=True,
            text=True,
            capture_output=True,
        )
        assert "Master alive     : True" in status.stdout
        assert "Worker health    : healthy" in status.stdout

        restarted = subprocess.run(
            [
                sys.executable, str(CTL), "--root", str(root),
                "restart", "--timeout", "20",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        second_pid = read_json(shared / "soc_automation.pid").get("pid")
        assert isinstance(second_pid, int) and second_pid != first_pid
        assert "Restart berhasil" in restarted.stdout
        assert read_json(shared / "master.json").get("restart_count") == 1

        stopped = subprocess.run(
            [
                sys.executable, str(CTL), "--root", str(root),
                "stop", "--timeout", "20",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        assert "berhenti dengan graceful" in stopped.stdout
        assert master.wait(timeout=10) == 0
        assert not (shared / "soc_master.pid").exists()
        assert not (shared / "soc_automation.pid").exists()
        assert read_json(shared / "master.json").get("status") == "stopped"
    finally:
        if master.poll() is None:
            master.terminate()
            try:
                master.wait(timeout=5)
            except subprocess.TimeoutExpired:
                master.kill()
        out, err = master.communicate()
        if master.returncode not in (0, None):
            print(out)
            print(err, file=sys.stderr)

print("Level 2.5 Phase A+B lifecycle test: OK")
