from __future__ import annotations
import shutil, subprocess, sys, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as td:
 manager=Path(td)/'manager'; manager.mkdir()
 shutil.copy2(root/'cutover_manager.py',manager/'cutover_manager.py')
 shutil.copy2(root/'role_gate.py',manager/'role_gate.py')
 result=subprocess.run([sys.executable,str(manager/'cutover_manager.py'),'--help'],capture_output=True,text=True)
 assert result.returncode==0, result.stderr
 assert 'Controlled Blue/Green cutover' in result.stdout
print('Phase J manager import hotfix test: OK')
