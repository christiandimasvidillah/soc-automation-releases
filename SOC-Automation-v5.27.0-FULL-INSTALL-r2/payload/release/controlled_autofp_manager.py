#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
from controlled_autofp import cfg,configure,execute
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');s=p.add_subparsers(dest='cmd',required=True);s.add_parser('status');q=s.add_parser('enable');q.add_argument('--ack',required=True);s.add_parser('disable');r=s.add_parser('run');r.add_argument('ticket');r.add_argument('--apply',action='store_true');a=p.parse_args();root=a.root.expanduser().resolve()
if a.cmd=='status':out=cfg(root)
elif a.cmd=='disable':out=configure(root,False)
elif a.cmd=='enable':
 if a.ack!='ENABLE-CONTROLLED-AUTO-FP':raise SystemExit('invalid acknowledgement')
 out=configure(root,True)
else:
 ticket=a.ticket.upper()
 if not re.fullmatch(r'[A-Z][A-Z0-9]+-[0-9]+',ticket):raise SystemExit('invalid ticket')
 rp=root/'shared/audit_logs/smb_dry_run_latest.json'
 if not rp.is_file():raise SystemExit('run SMB dry-run for this ticket first')
 report=json.loads(rp.read_text());out=execute(root,ticket,report,apply=a.apply)
print(json.dumps(out,indent=2))
