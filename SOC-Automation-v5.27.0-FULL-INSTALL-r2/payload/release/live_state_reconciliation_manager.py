#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from live_state_reconciler import reconcile
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('--ticket');p.add_argument('--minimum-age-seconds',type=int,default=300);p.add_argument('--output',type=Path);a=p.parse_args();r=reconcile(a.root,a.ticket,minimum_age_seconds=max(60,a.minimum_age_seconds))
 if a.output:a.output.expanduser().resolve().write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(r,indent=2));return 0 if r['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
