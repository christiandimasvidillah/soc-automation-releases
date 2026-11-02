from smb_observed_success_policy import decide
a={'kibana.alert.rule.name':'Rare SMB Connection to the Internet','host':{'id':'h','risk':{'calculated_level':'Low'}},'user':{'risk':{'calculated_level':'Low'}},'process':{'entity_id':'p'},'source':{'ip':'10.0.0.1'},'destination':{'ip':'1.1.1.1','port':445},'event':{'action':['connection_attempted'],'outcome':'unknown'}}
def rel(ip):return {'kibana.alert.rule.name':a['kibana.alert.rule.name'],'kibana.alert.severity':'medium','host':{'id':'h'},'process':{'entity_id':'p'},'source':{'ip':'10.0.0.1'},'destination':{'ip':ip,'port':445},'event':{'action':['connection_attempted'],'outcome':'unknown'}}
vt={ip:{'status':'PASS','stats':{'malicious':0,'suspicious':0}} for ip in ['1.1.1.1','1.0.0.1','8.8.8.8','8.8.4.4','9.9.9.9']}
r=decide(a,[rel(x) for x in vt],vt);assert r['recommendation']=='AUTO_FP_ELIGIBLE' and r['scoped_destination_fanout']==5 and r['connection_assessment']=='NO_OBSERVED_SUCCESS' and r['auto_fp'] is False
bad=rel('1.1.1.1');bad['event']={'action':['connection_established'],'outcome':'success'};assert decide(a,[bad],vt)['recommendation']=='MANUAL_REVIEW'
vt['8.8.8.8']={'status':'PASS','stats':{'malicious':1,'suspicious':0}};assert 'cluster_vt_not_clean_or_unavailable' in decide(a,[rel(x) for x in vt],vt)['blockers']
print('PASS test_smb_observed_success_policy')
