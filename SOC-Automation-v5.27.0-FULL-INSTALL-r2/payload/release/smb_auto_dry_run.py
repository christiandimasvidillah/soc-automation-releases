#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
from smb_evidence_collector import collect
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');g=p.add_mutually_exclusive_group(required=True);g.add_argument('--alert',type=Path);g.add_argument('--ticket');a=p.parse_args();root=a.root.expanduser().resolve()
if a.ticket:
 if not re.fullmatch(r'[A-Z][A-Z0-9]+-[0-9]+',a.ticket.upper()):raise SystemExit('invalid ticket key')
 path=root/'shared/audit_logs'/f'{a.ticket.upper()}_raw.json'
else:path=a.alert
if not path.is_file():raise SystemExit(f'audit log not found: {path}')
print(json.dumps(collect(json.loads(path.read_text()),root),indent=2))
