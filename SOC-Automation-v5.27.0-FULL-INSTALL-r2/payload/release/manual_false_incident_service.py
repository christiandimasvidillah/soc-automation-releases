#!/usr/bin/env python3
import argparse,json,subprocess,sys
from pathlib import Path
UNIT='soc-manual-false-incident.service'
def call(*a):return subprocess.run(['systemctl','--user',*a],text=True,capture_output=True)
def install(root):
 d=Path.home()/'.config/systemd/user';d.mkdir(parents=True,exist_ok=True);p=d/UNIT;p.write_text('[Unit]\nDescription=SOC Manual False Incident Reconciliation\nAfter=network-online.target\n\n[Service]\nType=simple\nExecStart='+sys.executable+' '+str(Path(root)/'current/manual_false_incident_cli.py')+' --root '+str(root)+' run --interval 30\nRestart=on-failure\nRestartSec=30\nNoNewPrivileges=true\nPrivateTmp=true\n\n[Install]\nWantedBy=default.target\n');r=call('daemon-reload');return {'installed':r.returncode==0,'unit':str(p),'returncode':r.returncode}
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('cmd',choices=['install','start','stop','restart','enable','disable','status']);a=p.parse_args();root=a.root.expanduser().resolve()
if a.cmd=='install':out=install(root)
elif a.cmd=='status':
 r=call('show',UNIT,'--property=LoadState,ActiveState,SubState,UnitFileState','--no-pager');out={'returncode':r.returncode,'detail':r.stdout.strip() or r.stderr.strip()}
else:
 r=call(a.cmd,UNIT);out={'command':a.cmd,'returncode':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()}
print(json.dumps(out,indent=2))
