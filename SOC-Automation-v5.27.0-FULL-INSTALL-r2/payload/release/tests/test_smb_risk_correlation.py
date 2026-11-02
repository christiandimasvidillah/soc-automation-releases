from smb_risk_correlation import assess
alert={'kibana.alert.rule.name':'Rare SMB Connection to the Internet','host':{'id':'h','risk':{'calculated_level':'Low'}},'user':{'risk':{'calculated_level':'Low'}},'process':{'pid':4,'entity_id':'p'},'destination':{'ip':'104.26.11.44','port':445}}
event={'host':{'id':'h'},'process':{'entity_id':'p'},'destination':{'ip':'104.26.11.44','port':445},'event':{'action':['connection_attempted'],'outcome':'unknown'}}
vt={'status':'PASS','stats':{'malicious':0,'suspicious':0}}
r=assess(alert,[event],[],vt);assert r['recommendation']=='AUTO_FP_ELIGIBLE' and r['auto_fp'] is False
bad={'kibana.alert.severity':'high','destination':{'ip':'8.8.8.8','port':445}}
r=assess(alert,[event],[bad],vt);assert r['recommendation']=='MANUAL_REVIEW' and 'related_high_or_critical_alert' in r['blockers']
r=assess(alert,[event],[],{'status':'UNAVAILABLE'});assert 'vt_not_clean_or_unavailable' in r['blockers']
print('PASS test_smb_risk_correlation')
