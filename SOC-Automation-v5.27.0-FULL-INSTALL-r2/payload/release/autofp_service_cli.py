#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from autofp_service import poll_once,reset_circuit,run,summary
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');s=p.add_subparsers(dest='cmd',required=True);s.add_parser('status');s.add_parser('poll-once');s.add_parser('reset-circuit');q=s.add_parser('run');q.add_argument('--interval',type=int,default=60);a=p.parse_args();r=a.root.expanduser().resolve()
if a.cmd=='status':out=summary(r)
elif a.cmd=='poll-once':out=poll_once(r)
elif a.cmd=='reset-circuit':out=reset_circuit(r)
else:run(r,a.interval);out={}
if a.cmd!='run':print(json.dumps(out,indent=2))
