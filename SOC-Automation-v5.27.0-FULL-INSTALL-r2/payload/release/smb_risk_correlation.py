from __future__ import annotations
from collections import Counter
from smb_correlation import correlate

def val(obj,*path):
    for key in path:
        if not isinstance(obj,dict): return None
        obj=obj.get(key)
    return obj

def src(item): return item.get('_source',item) if isinstance(item,dict) else {}
def level(value): return str(value or '').strip().lower()

def assess(alert, related_events, related_alerts, vt_result=None):
    a=src(alert); connection=correlate(a,related_events)
    if connection.get('assessment')=='NOT_APPLICABLE':
        return {'status':'SKIPPED','decision':'NOT_APPLICABLE','auto_fp':False}
    host_risk=level(val(a,'host','risk','calculated_level'))
    user_risk=level(val(a,'user','risk','calculated_level'))
    high_related=[]; destinations=[]; repeated=0
    for item in related_alerts:
        event=src(item); severity=level(val(event,'kibana.alert.severity') or val(event,'event','severity'))
        if severity in {'high','critical'}: high_related.append(severity)
        ip=val(event,'destination','ip') or val(event,'destination','address')
        if ip: destinations.append(str(ip))
        if val(event,'destination','port') in (139,445): repeated += 1
    fanout=len(set(destinations))
    vt=vt_result or {}; stats=vt.get('stats') or {}
    vt_clean=(vt.get('status')=='PASS' and int(stats.get('malicious',0))==0 and int(stats.get('suspicious',0))==0)
    blockers=[]
    if connection.get('assessment')!='ATTEMPT_ONLY': blockers.append('connection_not_attempt_only')
    if host_risk in {'high','critical'}: blockers.append('host_risk_high')
    if user_risk in {'high','critical'}: blockers.append('user_risk_high')
    if high_related: blockers.append('related_high_or_critical_alert')
    if fanout>3: blockers.append('destination_fanout')
    if repeated>5: blockers.append('repeated_external_smb')
    if not vt_clean: blockers.append('vt_not_clean_or_unavailable')
    recommendation='AUTO_FP_ELIGIBLE' if not blockers else 'MANUAL_REVIEW'
    return {
      'status':'PASS','connection_assessment':connection.get('assessment'),
      'host_risk':host_risk or 'unknown','user_risk':user_risk or 'unknown',
      'related_high_critical_count':len(high_related),'destination_fanout':fanout,
      'related_smb_events':repeated,'virustotal_clean':vt_clean,
      'recommendation':recommendation,'blockers':blockers,'auto_fp':False,
      'mode':'DRY_RUN_ONLY'
    }
