import os,tempfile
from pathlib import Path
from configuration_preflight import REQUIRED,run_preflight
assert 'GEMINI_MODEL' not in REQUIRED
with tempfile.TemporaryDirectory() as td:
 root=Path(td);shared=root/'shared';shared.mkdir();values={k:'value123' for k in REQUIRED};values['TELEGRAM_CHAT_ID']='-100123';values['GEMINI_ALLOWED_MODELS']='model-a,model-b';values['GEMINI_FALLBACK_MODELS']='model-c';env=shared/'.env';env.write_text(''.join(f'{k}={v}\n' for k,v in values.items()));os.chmod(env,0o600);r=run_preflight(root,{});assert r['status']=='PASS',r;assert not any(x['name']=='required:GEMINI_MODEL' for x in r['checks']);assert any(x['name']=='gemini_model_configuration' and x['passed'] for x in r['checks']);assert any(x['name']=='GEMINI_ALLOWED_MODELS' and x['state']=='SET (2 models)' for x in r['variables'])
 values.pop('GEMINI_ALLOWED_MODELS');values.pop('GEMINI_FALLBACK_MODELS');env.write_text(''.join(f'{k}={v}\n' for k,v in values.items()));r=run_preflight(root,{});assert r['status']=='PASS';assert any(x['name']=='GEMINI_ALLOWED_MODELS' and x['source']=='runtime_default' for x in r['variables'])
print('PASS test_gemini_preflight_hotfix')
