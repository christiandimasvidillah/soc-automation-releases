#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from configuration_preflight import run_preflight
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('--output',type=Path);a=p.parse_args();r=run_preflight(a.root)
 if a.output:a.output.expanduser().resolve().write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2));return 0 if r['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
