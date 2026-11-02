import json,tempfile
from pathlib import Path
from sharing_allowlist import Store,evaluate_alert
with tempfile.TemporaryDirectory() as td:
 root=Path(td);s=Store(root);e=s.add('DOMAIN','bjjid.onmicrosoft.com','VENDOR','approved','CHG-1');assert s.match('user@bjjid.onmicrosoft.com');assert not s.match('user@bjjid.onmicrosoft.com.attacker.test')
 alert={'event':{'provider':'OneDrive'},'operation':'AddedToSecureLink','o365':{'audit':{'TargetUserOrGroupName':'user@bjjid.onmicrosoft.com'}}};r=evaluate_alert(root,json.dumps(alert),'Unauthorized File Sharing to External Domain');assert r['matched'];alert['o365']['audit']['TargetUserOrGroupName']='user@unknown.test';assert not evaluate_alert(root,json.dumps(alert),'Unauthorized File Sharing to External Domain')['matched'];s.toggle(e['id']);assert not s.match('user@bjjid.onmicrosoft.com')
print('PASS test_sharing_allowlist')
