import json
from privacy_manager import SensitiveDataDetector,SensitiveDataSanitizer,SanitizationValidator,_enforce_sensitive_paths,_rule_for_path
url='https://kibana.example.internal/app/security/alerts/redirect/abc123'
payload={'hits':{'hits':[{'_source':{'kibana':{'alert':{'rule':{'parameters':{'meta':{'kibana_siem_app_url':url}}}}}}}]}}
path='hits.hits[]. _source.kibana.alert.rule.parameters.meta.kibana_siem_app_url'.replace('[] .','[].').replace('[]_','[]._').replace('[]..','[].')
assert _rule_for_path('hits.hits[]._source.kibana.alert.rule.parameters.meta.kibana_siem_app_url')==('INTERNAL_URL','URL')
findings=SensitiveDataDetector().discover(payload)
assert any(f.category=='INTERNAL_URL' and f.original==url for f in findings)
sanitized,count=SensitiveDataSanitizer().apply(payload,findings)
sanitized,enforced=_enforce_sensitive_paths(sanitized)
text=json.dumps(sanitized,ensure_ascii=False)
assert url not in text
value=sanitized['hits']['hits'][0]['_source']['kibana']['alert']['rule']['parameters']['meta']['kibana_siem_app_url']
assert value.startswith('URL_'),value
residuals=SanitizationValidator().validate(text,findings)
assert not any(f.category=='INTERNAL_URL' for f in residuals),[(f.category,f.path) for f in residuals]
assert count+enforced>=1
print('PASS test_kibana_siem_app_url_privacy')
