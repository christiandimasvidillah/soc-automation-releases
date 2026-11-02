#!/usr/bin/env python3
import argparse,json,os,re,tempfile
from pathlib import Path
from virustotal_enrichment import config,lookup
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');s=p.add_subparsers(dest='cmd',required=True);s.add_parser('status');q=s.add_parser('lookup');q.add_argument('ip');q.add_argument('--force',action='store_true');k=s.add_parser('set-key');k.add_argument('--stdin',action='store_true');s.add_parser('clear-cache');a=p.parse_args();root=a.root.expanduser().resolve()
if a.cmd=='status':
 c=config(root);out={'status':'PASS','enabled':c['enabled'],'api_key_configured':bool(c['api_key']),'cache_ttl_seconds':c['ttl'],'timeout_seconds':c['timeout']}
elif a.cmd=='lookup':out=lookup(a.ip,root,force=a.force)
elif a.cmd=='clear-cache':
 pth=root/'shared/cache/virustotal_ip_cache.json';pth.unlink(missing_ok=True);out={'status':'PASS','cleared':True}
else:
 key=os.sys.stdin.readline().strip()
 if not key or len(key)<32 or not re.fullmatch(r'[A-Za-z0-9_-]+',key):out={'status':'FAIL','reason':'invalid_api_key_format'}
 else:
  pth=root/'shared/.env';pth.parent.mkdir(parents=True,exist_ok=True);lines=pth.read_text().splitlines() if pth.exists() else [];vals={'VT_API_KEY':key,'VT_API_ENABLED':'true'};new=[]
  for line in lines:
   name=line.split('=',1)[0].strip() if '=' in line else ''
   if name in vals:new.append(name+'='+vals.pop(name))
   else:new.append(line)
  new += [k+'='+v for k,v in vals.items()];fd,n=tempfile.mkstemp(prefix='.env-',dir=pth.parent);os.close(fd);tmp=Path(n);tmp.write_text('\n'.join(new)+'\n');os.chmod(tmp,0o600);os.replace(tmp,pth);out={'status':'PASS','api_key_configured':True,'enabled':True}
print(json.dumps(out,indent=2));raise SystemExit(0 if out['status']=='PASS' else 2)
