import json,tempfile
from pathlib import Path
from sharing_allowlist import Store,evaluate_alert,normalize_target

def fixture(target):
 return json.dumps({'event':{'action':'AddedToSecureLink','provider':'SharePoint'},'o365':{'audit':{'TargetUserOrGroupName':target}}})

def test_guest_upn_domain_match():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);store=Store(root);store.add('DOMAIN','shinewing.id','VENDOR','Whitelisted Vendor','CHG-1')
  result=evaluate_alert(root,fixture('maulana.ihsan_shinewing.id#ext#@bjijd.onmicrosoft.com'),'Unauthorized File Sharing to External Domain')
  assert result['matched'] is True
  assert result['recommendation']=='AUTO_FP_ELIGIBLE'
  ident=result['identity_normalization'][0]
  assert ident['normalized_email']=='maulana.ihsan@shinewing.id'
  assert ident['normalized_domain']=='shinewing.id'
  assert ident['resource_tenant_domain']=='bjijd.onmicrosoft.com'

def test_guest_upn_without_external_allowlist_fails_closed():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);store=Store(root);store.add('DOMAIN','bjijd.onmicrosoft.com','VENDOR','Resource tenant only','CHG-2')
  result=evaluate_alert(root,fixture('maulana.ihsan_shinewing.id#ext#@bjijd.onmicrosoft.com'),'Unauthorized File Sharing to External Domain')
  assert result['matched'] is False
  assert result['reason']=='guest_identity_ambiguous'

def test_anonymous_indicator_blocks():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);Store(root).add('DOMAIN','shinewing.id','VENDOR','Approved','CHG-3')
  raw=json.loads(fixture('maulana.ihsan_shinewing.id#EXT#@bjijd.onmicrosoft.com'));raw['link']='AnonymousLink'
  result=evaluate_alert(root,json.dumps(raw),'Unauthorized File Sharing to External Domain')
  assert result['matched'] is False and result['reason']=='anonymous_indicator'
