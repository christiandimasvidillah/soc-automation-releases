from __future__ import annotations

def v(o,*p):
 for k in p:
  if not isinstance(o,dict):return None
  o=o.get(k)
 return o

def src(x):return x.get('_source',x) if isinstance(x,dict) else {}
def one(x):return x[0] if isinstance(x,list) and x else x

def same_scope(alert,item):
 a=src(alert);e=src(item)
 return (v(e,'host','id')==v(a,'host','id') and v(e,'process','entity_id')==v(a,'process','entity_id') and
         v(e,'source','ip')==v(a,'source','ip') and v(e,'destination','port')==v(a,'destination','port') and
         (v(e,'kibana.alert.rule.name') or v(e,'signal','rule','name'))==v(a,'kibana.alert.rule.name'))

def action_values(event):
 x=v(event,'event','action') or v(event,'kibana.alert.original_event.action') or []
 return {str(i).lower() for i in (x if isinstance(x,list) else [x])}

def has_success(event):
 e=src(event);actions=action_values(e);out=str(v(e,'event','outcome') or v(e,'kibana.alert.original_event.outcome') or '').lower()
 return out=='success' or bool(actions & {'connection_established','connection_accepted','connection_success'}) or bool(v(e,'network','bytes') or v(e,'destination','bytes'))

def decide(alert,related_alerts,vt_by_ip):
 a=src(alert);scoped=[src(x) for x in related_alerts if same_scope(a,x)]
 destinations=sorted({str(v(x,'destination','ip')) for x in scoped if v(x,'destination','ip')})
 initial_actions=action_values(a);initial_out=str(v(a,'event','outcome') or v(a,'kibana.alert.original_event.outcome') or '').lower()
 no_observed_success=('connection_attempted' in initial_actions and initial_out=='unknown' and not has_success(a) and not any(has_success(x) for x in scoped))
 vt_fail=[]
 for ip in sorted(set(destinations+[str(v(a,'destination','ip'))])):
  r=vt_by_ip.get(ip,{}) ;st=r.get('stats') or {}
  if r.get('status')!='PASS' or int(st.get('malicious',0)) or int(st.get('suspicious',0)):vt_fail.append(ip)
 blockers=[]
 if not no_observed_success:blockers.append('observed_or_unresolved_success_evidence')
 if vt_fail:blockers.append('cluster_vt_not_clean_or_unavailable')
 if str(v(a,'host','risk','calculated_level') or '').lower() in {'high','critical'}:blockers.append('host_risk_high')
 if str(v(a,'user','risk','calculated_level') or '').lower() in {'high','critical'}:blockers.append('user_risk_high')
 high=sum(1 for x in scoped if str(v(x,'kibana.alert.severity') or '').lower() in {'high','critical'})
 if high:blockers.append('scoped_high_or_critical_alert')
 return {'status':'PASS','connection_assessment':'NO_OBSERVED_SUCCESS' if no_observed_success else 'SUCCESS_EVIDENCE_PRESENT_OR_UNRESOLVED','scoped_related_alerts':len(scoped),'scoped_destination_fanout':len(destinations),'all_scoped_destinations_vt_clean':not vt_fail,'vt_failed_ips':vt_fail,'recommendation':'AUTO_FP_ELIGIBLE' if not blockers else 'MANUAL_REVIEW','blockers':blockers,'auto_fp':False,'mode':'DRY_RUN_ONLY'}
