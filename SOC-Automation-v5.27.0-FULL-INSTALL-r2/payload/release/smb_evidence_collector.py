from __future__ import annotations
import json,os,tempfile,time
from pathlib import Path
from smb_observed_success_policy import decide
from virustotal_enrichment import lookup

def v(o,*p):
 for k in p:
  if not isinstance(o,dict):return None
  o=o.get(k)
 return o

def source(x):return x.get('_source',x)

def normalize_alert_payload(payload):
 if not isinstance(payload,dict):raise ValueError("alert_payload_not_object")
 hits=payload.get("hits")
 if isinstance(hits,dict) and "hits" in hits:
  items=hits.get("hits") or []
  if len(items)!=1:raise ValueError("expected_exactly_one_alert_hit")
  payload=items[0]
 if isinstance(payload,dict) and isinstance(payload.get("_source"),dict):payload=payload["_source"]
 if not isinstance(payload,dict):raise ValueError("alert_source_not_object")
 return payload
def write_atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);fd,n=tempfile.mkstemp(prefix='.smb-audit-',dir=path.parent);os.close(fd);p=Path(n);p.write_text(json.dumps(data,indent=2)+'\n');os.chmod(p,0o600);os.replace(p,path)
def query(client,body):
 response=client._request('POST',client.settings.alert_search_url,expected_statuses={200},json=body)
 data=response.json();return data.get('hits',{}).get('hits',[])
def collect(alert,root_path,client=None,vt_lookup=lookup,now=None):
 root_path=Path(root_path)
 try:a=normalize_alert_payload(alert)
 except ValueError as exc:return {'status':'FAIL','reason':str(exc),'auto_fp':False}
 now=time.time() if now is None else now
 if v(a,'kibana.alert.rule.name')!='Rare SMB Connection to the Internet':return {'status':'SKIPPED','reason':'not_applicable','auto_fp':False}
 ts=v(a,'kibana.alert.original_time') or v(a,'kibana.alert.original_event.created') or v(a,'event','created') or v(a,'@timestamp');host=v(a,'host','id');entity=v(a,'process','entity_id');ip=v(a,'destination','ip');port=v(a,'destination','port')
 if not all((ts,host,entity,ip,port)):return {'status':'FAIL','reason':'required_correlation_fields_missing','auto_fp':False}
 common=[{'term':{'host.id':host}},{'term':{'process.entity_id':entity}},{'term':{'destination.ip':ip}},{'term':{'destination.port':port}}]
 event_body={'size':200,'query':{'bool':{'filter':common+[{'range':{'@timestamp':{'gte':f'{ts}||-60s','lte':f'{ts}||+120s'}}}]}}}
 alert_body={'size':100,'query':{'bool':{'filter':[{'term':{'host.id':host}},{'range':{'@timestamp':{'gte':f'{ts}||-15m','lte':f'{ts}||+15m'}}}]}}}
 own=client is None
 if own:
  from siem_client import SiemClient
  c=SiemClient()
 else:c=client
 try:events=query(c,event_body);alerts=query(c,alert_body)
 finally:
  if own:c.close()
 ips={str(ip)}
 for item in alerts:
  e=source(item);dip=v(e,'destination','ip')
  if dip:ips.add(str(dip))
 vt_by_ip={dip:vt_lookup(dip,root_path) for dip in sorted(ips)}
 decision=decide(a,alerts,vt_by_ip);report={'status':'PASS','mode':'DRY_RUN_ONLY','collected_at':now,'evidence_counts':{'related_events':len(events),'related_alerts':len(alerts)},'virustotal_cluster':{'queried_ips':len(vt_by_ip),'clean_ips':sum(1 for r in vt_by_ip.values() if r.get('status')=='PASS' and not int((r.get('stats') or {}).get('malicious',0)) and not int((r.get('stats') or {}).get('suspicious',0)))},'decision':decision,'auto_fp':False}
 write_atomic(root_path/'shared/audit_logs/smb_dry_run_latest.json',report)
 journal=root_path/'shared/audit_logs/smb_dry_run_audit.jsonl';journal.parent.mkdir(parents=True,exist_ok=True)
 with journal.open('a',encoding='utf-8') as f:f.write(json.dumps({'epoch':now,'recommendation':decision.get('recommendation'),'blockers':decision.get('blockers',[]),'auto_fp':False})+'\n')
 os.chmod(journal,0o600);return report
