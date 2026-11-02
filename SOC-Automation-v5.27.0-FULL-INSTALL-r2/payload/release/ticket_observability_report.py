#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from ticket_observability import build_report
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('--stuck-seconds',type=int,default=300);p.add_argument('--output',type=Path);a=p.parse_args();r=build_report(a.root,max(30,a.stuck_seconds))
 if a.output:a.output.expanduser().resolve().write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
