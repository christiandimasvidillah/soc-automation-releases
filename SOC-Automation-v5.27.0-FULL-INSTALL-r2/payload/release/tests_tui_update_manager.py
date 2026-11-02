import json,tempfile,zipfile,hashlib
from pathlib import Path
from tui_update_manager import UpdateService,UpdateError
with tempfile.TemporaryDirectory() as td:
 r=Path(td); (r/'updates/incoming').mkdir(parents=True); (r/'manager').mkdir(); p=r/'updates/incoming/test.zip'
 with zipfile.ZipFile(p,'w') as z:z.writestr('manifest.json',json.dumps({'version':'9.9.9','minimum_version':'5.1.3','description':'test'}))
 s=UpdateService(r); x=s.inspect(p); assert x['version']=='9.9.9' and len(x['sha256'])==64
 try:s.inspect(r/'outside.zip'); raise AssertionError
 except UpdateError:pass
print('TUI update manager tests: OK')
