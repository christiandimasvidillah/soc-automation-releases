#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from sharing_allowlist import Store
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');s=p.add_subparsers(dest='cmd',required=True);s.add_parser('list');a=s.add_parser('add');a.add_argument('--type',choices=['EMAIL','DOMAIN'],required=True);a.add_argument('--value',required=True);a.add_argument('--classification',choices=['INTERNAL','VENDOR'],required=True);a.add_argument('--reason',required=True);a.add_argument('--reference',required=True);a.add_argument('--expires-at');r=s.add_parser('remove');r.add_argument('id');t=s.add_parser('toggle');t.add_argument('id');x=p.parse_args();st=Store(x.root)
try:
 if x.cmd=='list':out={'status':'PASS','entries':st.load()['entries']}
 elif x.cmd=='add':out={'status':'PASS','entry':st.add(x.type,x.value,x.classification,x.reason,x.reference,x.expires_at)}
 elif x.cmd=='remove':out={'status':'PASS','entry':st.remove(x.id)}
 else:out={'status':'PASS','entry':st.toggle(x.id)}
except ValueError as e:out={'status':'FAIL','error':str(e)}
print(json.dumps(out,indent=2));raise SystemExit(0 if out['status']=='PASS' else 2)
