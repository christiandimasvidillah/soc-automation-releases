from __future__ import annotations
import json,os,re,stat,time
from pathlib import Path
REQUIRED=("JIRA_EMAIL","JIRA_API_TOKEN","JIRA_ACCOUNT_ID","ELASTIC_API_KEY","GEMINI_API_KEY","HASH_SECRET_KEY","TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID")
GEMINI_DEFAULT_MODELS=("gemini-3.5-flash","gemini-3.1-flash-lite","gemini-2.5-flash","gemini-2.5-flash-lite")
SENSITIVE_MARKERS=("TOKEN","KEY","SECRET","PASSWORD")
def parse_env(path):
 out={}
 if not path.is_file():return out
 for raw in path.read_text(errors='replace').splitlines():
  line=raw.strip()
  if not line or line.startswith('#') or '=' not in line:continue
  key,value=line.split('=',1);key=key.strip()
  if re.fullmatch(r'[A-Z][A-Z0-9_]*',key):out[key]=value.strip().strip('"').strip("'")
 return out
def masked(value):
 if not value:return 'NOT SET'
 return 'SET ('+str(len(value))+' chars)'
def run_preflight(root,environment=None):
 root=Path(root).expanduser().resolve();env_file=root/'shared/.env';file_values=parse_env(env_file);process=dict(os.environ if environment is None else environment);checks=[];variables=[]
 def add(name,status,detail):checks.append({'name':name,'status':status,'passed':status=='PASS','detail':detail})
 if not env_file.is_file():add('shared_env_file','FAIL','missing')
 else:
  mode=stat.S_IMODE(env_file.stat().st_mode);add('shared_env_permission','PASS' if mode==0o600 else 'FAIL',oct(mode))
 for key in REQUIRED:
  process_value=process.get(key,'').strip();file_value=file_values.get(key,'').strip();effective=process_value or file_value;source='process_env' if process_value else ('shared_env' if file_value else 'missing');shadowed=bool(process_value and file_value and process_value!=file_value)
  variables.append({'name':key,'source':source,'state':masked(effective),'shadowed':shadowed})
  add('required:'+key,'PASS' if effective else 'FAIL',source)
  if shadowed:add('shadow:'+key,'WARN','process environment overrides shared/.env')
 allowed=process.get('GEMINI_ALLOWED_MODELS','').strip() or file_values.get('GEMINI_ALLOWED_MODELS','').strip()
 fallback=process.get('GEMINI_FALLBACK_MODELS','').strip() or file_values.get('GEMINI_FALLBACK_MODELS','').strip()
 model_source='process_env' if process.get('GEMINI_ALLOWED_MODELS','').strip() else ('shared_env' if file_values.get('GEMINI_ALLOWED_MODELS','').strip() else 'runtime_default')
 selected=allowed or ','.join(GEMINI_DEFAULT_MODELS)
 models=[x.strip() for x in selected.split(',') if x.strip()]
 variables.append({'name':'GEMINI_ALLOWED_MODELS','source':model_source,'state':('SET ('+str(len(models))+' models)') if model_source!='runtime_default' else 'SET ('+str(len(models))+' runtime-default models)','shadowed':bool(process.get('GEMINI_ALLOWED_MODELS','').strip() and file_values.get('GEMINI_ALLOWED_MODELS','').strip() and process.get('GEMINI_ALLOWED_MODELS','').strip()!=file_values.get('GEMINI_ALLOWED_MODELS','').strip())})
 add('gemini_model_configuration','PASS' if models else 'FAIL',model_source)
 if fallback:
  fallback_models=[x.strip() for x in fallback.split(',') if x.strip()];variables.append({'name':'GEMINI_FALLBACK_MODELS','source':'process_env' if process.get('GEMINI_FALLBACK_MODELS','').strip() else 'shared_env','state':'SET ('+str(len(fallback_models))+' models)','shadowed':False})
 chat=process.get('TELEGRAM_CHAT_ID') or file_values.get('TELEGRAM_CHAT_ID','')
 if chat:add('telegram_chat_id_format','PASS' if re.fullmatch(r'-?\d+',chat.strip()) else 'FAIL','numeric' if re.fullmatch(r'-?\d+',chat.strip()) else 'invalid format')
 local_url=process.get('LOCAL_AI_URL') or file_values.get('LOCAL_AI_URL') or process.get('OLLAMA_BASE_URL') or file_values.get('OLLAMA_BASE_URL')
 if local_url:add('local_ai_endpoint','PASS' if any(x in local_url.lower() for x in ('127.0.0.1','localhost')) else 'WARN','localhost' if any(x in local_url.lower() for x in ('127.0.0.1','localhost')) else 'non-local endpoint configured')
 failed=sum(x['status']=='FAIL' for x in checks);warnings=sum(x['status']=='WARN' for x in checks)
 return {'generated_at':time.time(),'status':'PASS' if failed==0 else 'FAIL','summary':{'passed':sum(x['status']=='PASS' for x in checks),'failed':failed,'warnings':warnings},'env_file':str(env_file),'variables':variables,'checks':checks,'secrets_disclosed':False}
