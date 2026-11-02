#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from manual_false_incident_reconciler import poll,run,setmode,status
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');s=p.add_subparsers(dest='cmd',required=True);s.add_parser('status');s.add_parser('poll-once');q=s.add_parser('mode');q.add_argument('value');r=s.add_parser('run');r.add_argument('--interval',type=int,default=30);a=p.parse_args();root=a.root.expanduser().resolve()
if a.cmd=='status':out=status(root)
elif a.cmd=='poll-once':out=poll(root)
elif a.cmd=='mode':out=setmode(root,a.value.upper())
else:run(root,a.interval);out={}
if a.cmd!='run':print(json.dumps(out,indent=2))
