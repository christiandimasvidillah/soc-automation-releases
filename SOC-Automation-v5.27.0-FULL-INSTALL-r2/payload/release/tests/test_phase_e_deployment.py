from __future__ import annotations
import importlib.util, os, tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('deploy_manager',Path(__file__).resolve().parents[1]/'deploy_manager.py'); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
class Fake(mod.TransactionalDeployer):
 def __init__(self,root,fail=False): super().__init__(root,timeout=1); self.fail=fail; self.commands=[]
 def master_ready(self): return True
 def run_command(self,command,*,stage):
  self.commands.append(stage); self.write_state(stage)
  if stage=='apply_release': self.switch('4.5.1')
  elif stage=='rollback_release': self.switch(self.previous_version)
  return object()
 def restart_worker(self,*,stage): self.commands.append(stage); self.write_state(stage)
 def validate_runtime(self,expected_version,*,timeout=None):
  if self.fail and expected_version=='4.5.1': raise mod.DeploymentError('simulated readiness failure')
  self.write_state('runtime_validated',validated_version=expected_version)
 def switch(self,version):
  tmp=self.root/'.current.test'; tmp.unlink(missing_ok=True); tmp.symlink_to(Path('releases')/f'v{version}',target_is_directory=True); os.replace(tmp,self.root/'current')
def root_at(base):
 root=base/'SOC-Automation'
 for v in ('4.5.0','4.5.1'):
  r=root/'releases'/f'v{v}'; r.mkdir(parents=True,exist_ok=True); (r/'VERSION').write_text(v+'\n')
 (root/'manager').mkdir(); (root/'shared').mkdir(); (root/'manager'/'local_release_manager.py').write_text('# fake\n'); (root/'manager'/'socctl.py').write_text('# fake\n'); (root/'current').symlink_to(Path('releases/v4.5.0'),target_is_directory=True); return root
with tempfile.TemporaryDirectory() as td:
 root=root_at(Path(td)); pkg=root/'ok.zip'; pkg.write_bytes(b'ok'); d=Fake(root); d.acquire()
 try:d.deploy(pkg)
 finally:d.release()
 assert d.current_version()=='4.5.1'; assert d.read_json(root/'shared'/'deployment.json')['status']=='committed'; assert d.commands==['dry_run','apply_release','restart_new_release']; assert not (root/'shared'/'deployment.lock').exists()
with tempfile.TemporaryDirectory() as td:
 root=root_at(Path(td)); pkg=root/'bad.zip'; pkg.write_bytes(b'bad'); d=Fake(root,True); d.acquire()
 try:
  try:d.deploy(pkg)
  except mod.DeploymentError as e: assert 'rollback otomatis berhasil' in str(e)
  else: raise AssertionError('expected failure')
 finally:d.release()
 state=d.read_json(root/'shared'/'deployment.json'); assert d.current_version()=='4.5.0'; assert state['status']=='rolled_back'; assert state['rollback_performed'] is True; assert 'rollback_release' in d.commands and 'rollback_restart' in d.commands
print('Phase E transactional deployment tests: OK')
