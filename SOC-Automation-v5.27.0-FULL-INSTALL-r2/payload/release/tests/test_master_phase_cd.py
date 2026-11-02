from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
P=Path(__file__).resolve().parents[1]; MASTER=P/'soc_master.py'; CTL=P/'socctl.py'; FAKE=P/'tests'/'fake_worker.py'
def read(path):
 try:return json.loads(path.read_text())
 except (OSError,json.JSONDecodeError):return {}
def wait(pred,timeout=15):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if pred():return
  time.sleep(.1)
 raise AssertionError('timeout')
def setup(root):
 rel=root/'releases'/'v4.4.0'; shared=root/'shared'; (rel/'tests').mkdir(parents=True); shared.mkdir(); shutil.copy2(FAKE,rel/'tests'/'fake_worker.py'); (rel/'VERSION').write_text('4.4.0\n'); (root/'current').symlink_to(Path('releases/v4.4.0'),target_is_directory=True); return shared
def start(root,mode,maxr):
 env=os.environ.copy(); env['FAKE_SOC_ROOT']=str(root); env['FAKE_WORKER_MODE']=mode
 return subprocess.Popen([sys.executable,str(MASTER),'--root',str(root),'--startup-timeout','5','--shutdown-timeout','5','--control-interval','.05','--worker-script','tests/fake_worker.py','--stale-after','.25','--unhealthy-after','.55','--max-restarts',str(maxr),'--restart-window','30','--restart-backoff','.1,.2'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
def stop(root,proc):
 subprocess.run([sys.executable,str(CTL),'--root',str(root),'stop','--timeout','10'],check=True,capture_output=True,text=True); assert proc.wait(timeout=10)==0
# Health-aware stale -> unhealthy -> automatic recovery.
with tempfile.TemporaryDirectory(prefix='soc-health-') as td:
 root=Path(td); shared=setup(root); proc=start(root,'stale_once',2)
 try:
  wait(lambda: read(shared/'master.json').get('health_restart_count')==1 and read(shared/'master.json').get('status')=='running' and int((shared/'fake_worker_start_count').read_text())>=2)
  state=read(shared/'master.json'); assert state['last_restart_reason']=='health_unhealthy'; assert state['auto_restart_count']==1; assert state['worker_health_state']=='healthy'; stop(root,proc)
 finally:
  if proc.poll() is None: proc.terminate(); proc.wait(timeout=5)
# Repeated crash -> bounded retries -> crash-loop while master remains controllable.
with tempfile.TemporaryDirectory(prefix='soc-crash-') as td:
 root=Path(td); shared=setup(root); proc=start(root,'crash_after_ready',2)
 try:
  wait(lambda: read(shared/'master.json').get('status')=='worker_crash_loop')
  state=read(shared/'master.json'); assert state['auto_restart_count']==2; assert state['crash_restart_count']==2; assert state['restart_budget_used']==2; assert proc.poll() is None; assert not (shared/'soc_automation.pid').exists(); stop(root,proc)
 finally:
  if proc.poll() is None: proc.terminate(); proc.wait(timeout=5)
print('Phase C+D health and bounded recovery tests: OK')
