#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,socket,time
from pathlib import Path
from feature_control import FeatureControl

def tcp(url):
 try:
  from urllib.parse import urlparse
  p=urlparse(url); s=socket.create_connection((p.hostname,p.port or (443 if p.scheme=='https' else 80)),timeout=.5); s.close(); return True
 except Exception:return False
def snapshot(root):
 from config import settings
 flags=FeatureControl(root).snapshot(); eff=flags['effective']
 local={'provider':settings.local_ai.provider,'model':settings.local_ai.model,'endpoint':settings.local_ai.endpoint,'configured':True,'reachable':tcp(settings.local_ai.endpoint),'mode':'ENABLED' if eff['local_ai_detection']['effective'] else 'DISABLED'}
 models=list(settings.gemini.allowed_models)
 gemini={'provider':'Google Gemini','models':models,'preferred_model':models[0] if models else None,'credential_configured':bool(settings.gemini.api_key),'mode':'ENABLED' if eff['gemini_analysis']['effective'] else 'DISABLED','status':'CONFIGURED' if settings.gemini.api_key else 'UNAVAILABLE'}
 return {'generated_at':time.time(),'profile':flags['profile'],'revision':flags['revision'],'local_ai':local,'gemini':gemini}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='~/SOC-Automation');a=p.parse_args();print(json.dumps(snapshot(Path(a.root).expanduser().resolve()),indent=2))
if __name__=='__main__':main()
