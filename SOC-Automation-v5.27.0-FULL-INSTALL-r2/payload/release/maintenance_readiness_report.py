#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from maintenance_readiness import evaluate
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('--minimum-free-mb',type=int,default=1024);p.add_argument('--output',type=Path);a=p.parse_args();r=evaluate(a.root,max(128,a.minimum_free_mb))
 if a.output:a.output.expanduser().resolve().write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(r,indent=2));return 0 if r['ready'] else 2
if __name__=='__main__':raise SystemExit(main())
