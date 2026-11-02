import json,os,tempfile,time
from pathlib import Path
from virustotal_enrichment import lookup
class Response:
 def read(self):return json.dumps({'data':{'attributes':{'asn':13335,'as_owner':'Cloudflare, Inc.','network':'104.26.0.0/20','reputation':0,'last_analysis_date':1000,'last_analysis_stats':{'malicious':0,'suspicious':0,'harmless':91}}}}).encode()
def open_ok(req,timeout):assert req.headers.get('X-apikey')=='A'*40;return Response()
with tempfile.TemporaryDirectory() as td:
 root=Path(td);(root/'shared').mkdir();(root/'shared/.env').write_text('VT_API_ENABLED=true\nVT_API_KEY='+('A'*40)+'\n');r=lookup('104.26.11.44',root,open_ok,now=1100);assert r['status']=='PASS' and r['stats']['malicious']==0 and r['as_owner']=='Cloudflare, Inc.';assert lookup('192.168.1.1',root,open_ok)['status']=='SKIPPED';assert lookup('104.26.11.44',root,lambda *x:(_ for _ in ()).throw(Exception()),now=1101)['cache']
print('PASS test_virustotal_enrichment')
