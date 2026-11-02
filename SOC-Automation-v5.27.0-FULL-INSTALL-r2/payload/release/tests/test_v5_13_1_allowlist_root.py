import os,tempfile
from pathlib import Path
from ticket_processor import _automation_root
with tempfile.TemporaryDirectory() as td:
 os.environ["SOC_AUTOMATION_ROOT"]=td
 assert _automation_root()==Path(td).resolve()
 del os.environ["SOC_AUTOMATION_ROOT"]
 assert _automation_root()==(Path.home()/"SOC-Automation").resolve()
src=Path(__file__).parents[1].joinpath("ticket_processor.py").read_text()
assert "self.privacy_manager.root" not in src
assert "evaluate_alert(_automation_root(), alert_text, summary)" in src
print("PASS test_v5_13_1_allowlist_root")
