from __future__ import annotations
import json, os, signal, sys, time
from datetime import datetime, timezone
from pathlib import Path
root=Path(os.environ['FAKE_SOC_ROOT']); shared=root/'shared'; shared.mkdir(parents=True,exist_ok=True)
pid_file=shared/'soc_automation.pid'; health_file=shared/'health.json'; count_file=shared/'fake_worker_start_count'
running=True; version=(root/'current'/'VERSION').read_text().strip(); mode=os.getenv('FAKE_WORKER_MODE','stable')
try: count=int(count_file.read_text())+1
except (OSError,ValueError): count=1
count_file.write_text(str(count))
def now(): return datetime.now(timezone.utc).astimezone().isoformat()
def write(path,payload):
 t=path.with_name(f'.{path.name}.{os.getpid()}.tmp'); t.write_text(json.dumps(payload,indent=2)+'\n'); os.replace(t,path)
def stop(_s,_f):
 global running; running=False
signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
write(pid_file,{'pid':os.getpid(),'version':version,'started_at':now()}); started=time.monotonic()
while running:
 write(health_file,{'status':'healthy','pid':os.getpid(),'version':version,'last_heartbeat':now(),'last_poll_finished':now(),'fake_mode':mode,'fake_start_count':count})
 if mode=='crash_after_ready' and time.monotonic()-started>=0.35: sys.exit(7)
 if mode=='stale_once' and count==1:
  while running: time.sleep(0.1)
  break
 time.sleep(0.1)
write(health_file,{'status':'stopped','pid':os.getpid(),'version':version,'last_heartbeat':now(),'fake_start_count':count})
pid_file.unlink(missing_ok=True)
