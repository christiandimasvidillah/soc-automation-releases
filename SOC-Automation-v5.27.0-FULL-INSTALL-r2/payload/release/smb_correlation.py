from __future__ import annotations
import json

def val(o,*p):
 for k in p:
  if not isinstance(o,dict):return None
  o=o.get(k)
 return o
def arr(v):return v if isinstance(v,list) else ([] if v is None else [v])
def same(e,a):
 return all(val(e,*p)==val(a,*p) for p in [("host","id"),("process","entity_id"),("destination","ip"),("destination","port")])
def correlate(alert,events):
 src=alert.get("_source",alert);rule=val(src,"kibana.alert.rule.name")
 if rule!="Rare SMB Connection to the Internet":return {"status":"SKIPPED","assessment":"NOT_APPLICABLE"}
 if val(src,"process","pid")!=4 or val(src,"destination","port") not in (139,445):return {"status":"PASS","assessment":"UNKNOWN_AFTER_CORRELATION","reason":"context_mismatch"}
 matched=[e.get("_source",e) for e in events if same(e.get("_source",e),src)]
 actions={str(x).lower() for e in matched for x in arr(val(e,"event","action"))};outcomes={str(val(e,"event","outcome") or "").lower() for e in matched}
 text=json.dumps(matched).lower();auth=any(x in text for x in ("ntlm","authentication","logon"));transfer=any((val(e,"network","bytes") or val(e,"destination","bytes") or 0)>0 for e in matched)
 established=bool(actions & {"connection_established","connection_accepted","connection_success"}) or "success" in outcomes
 if auth or transfer or established:a="SUCCESSFUL" if (auth or transfer or "success" in outcomes) else "ESTABLISHED"
 elif matched:a="ATTEMPT_ONLY"
 else:a="UNKNOWN_AFTER_CORRELATION"
 return {"status":"PASS","assessment":a,"matched_events":len(matched),"established":established,"authentication_observed":auth,"transfer_observed":transfer,"auto_fp":False}
