from __future__ import annotations
import ipaddress,json,os,tempfile,time,urllib.error,urllib.request
from pathlib import Path
BASE='https://www.virustotal.com/api/v3'
def root():return Path(os.getenv('SOC_AUTOMATION_ROOT',str(Path.home()/'SOC-Automation'))).expanduser().resolve()
def env(root_path):
 d={}
 for p in [Path(root_path)/'shared/.env',Path(root_path)/'.env']:
  if p.is_file():
   for line in p.read_text(errors='replace').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):k,v=line.split('=',1);d[k.strip()]=v.strip().strip('"').strip("'")
 return d
def config(root_path):
 e=env(root_path);return {'enabled':e.get('VT_API_ENABLED','false').lower() in {'1','true','yes','on'},'api_key':os.getenv('VT_API_KEY') or e.get('VT_API_KEY',''),'ttl':max(300,int(e.get('VT_CACHE_TTL_SECONDS','86400'))),'timeout':max(2,int(e.get('VT_TIMEOUT_SECONDS','10')))}
def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);fd,n=tempfile.mkstemp(prefix='.vt-',dir=path.parent);os.close(fd);p=Path(n);p.write_text(json.dumps(data,indent=2)+'\n');os.chmod(p,0o600);os.replace(p,path)
def lookup(ip,root_path=None,opener=None,now=None,force=False):
 root_path=Path(root_path or root());now=time.time() if now is None else now
 try:obj=ipaddress.ip_address(ip)
 except ValueError:return {'status':'SKIPPED','reason':'invalid_ip'}
 if not obj.is_global:return {'status':'SKIPPED','reason':'non_public_ip','ip':str(obj)}
 c=config(root_path)
 if not c['enabled']:return {'status':'SKIPPED','reason':'disabled','ip':str(obj)}
 if not c['api_key']:return {'status':'UNAVAILABLE','reason':'api_key_missing','ip':str(obj)}
 cache_path=root_path/'shared/cache/virustotal_ip_cache.json'
 try:cache=json.loads(cache_path.read_text())
 except Exception:cache={}
 hit=cache.get(str(obj),{})
 if hit and not force and now-float(hit.get('fetched_at',0))<=c['ttl']:return dict(hit,cache=True)
 req=urllib.request.Request(f'{BASE}/ip_addresses/{obj}',headers={'accept':'application/json','x-apikey':c['api_key'],'user-agent':'SOC-Automation/5.14.0'})
 try:
  response=(opener or urllib.request.urlopen)(req,timeout=c['timeout']);payload=json.loads(response.read().decode());a=payload['data']['attributes'];stats=a.get('last_analysis_stats') or {}
  out={'status':'PASS','ip':str(obj),'asn':a.get('asn'),'as_owner':a.get('as_owner'),'network':a.get('network'),'reputation':a.get('reputation'),'last_analysis_date':a.get('last_analysis_date'),'analysis_age_seconds':max(0,now-float(a.get('last_analysis_date') or now)),'stats':{k:int(stats.get(k,0)) for k in ('malicious','suspicious','harmless','undetected','timeout')},'fetched_at':now,'cache':False}
  cache[str(obj)]=out;atomic(cache_path,cache);return out
 except urllib.error.HTTPError as e:return {'status':'UNAVAILABLE','reason':f'http_{e.code}','ip':str(obj)}
 except Exception as e:return {'status':'UNAVAILABLE','reason':type(e).__name__,'ip':str(obj)}
