#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from smb_risk_correlation import assess
p=argparse.ArgumentParser();p.add_argument('--alert',type=Path,required=True);p.add_argument('--events',type=Path,required=True);p.add_argument('--alerts',type=Path,required=True);p.add_argument('--vt',type=Path);a=p.parse_args()
def read(path): return json.loads(path.read_text())
def hits(value): return value.get('hits',{}).get('hits',[]) if isinstance(value,dict) else value
vt=read(a.vt) if a.vt else None
print(json.dumps(assess(read(a.alert),hits(read(a.events)),hits(read(a.alerts)),vt),indent=2))
