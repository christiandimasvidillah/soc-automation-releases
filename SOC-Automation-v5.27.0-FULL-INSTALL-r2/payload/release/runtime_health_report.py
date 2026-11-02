#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from runtime_health_center import build_health_center
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('--output',type=Path);a=p.parse_args();r=build_health_center(a.root)
 if a.output:a.output.expanduser().resolve().write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(r,indent=2));return 0 if r['overall_status']=='healthy' else 2
if __name__=='__main__':raise SystemExit(main())
