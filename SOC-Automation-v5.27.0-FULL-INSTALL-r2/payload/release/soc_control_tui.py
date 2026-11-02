#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sqlite3,subprocess,sys,zipfile
from pathlib import Path
from soc_status import snapshot

class Console:
 def __init__(self,root): self.root=Path(root).expanduser().resolve(); self.manager=self.root/'manager'; self.shared=self.root/'shared'
 def pause(self,msg='Press Enter'): input('\n'+msg)
 def run(self,args,timeout=420):
  try:r=subprocess.run(args,text=True,capture_output=True,timeout=timeout,check=False); return r.returncode,(r.stdout+'\n'+r.stderr).strip()
  except Exception as e:return 99,f'{type(e).__name__}: {e}'
 def cmd(self,args,confirm=None):
  if confirm and input(f'Type exactly "{confirm}": ').strip()!=confirm:return self.pause('Cancelled. Press Enter')
  rc,out=self.run(args); print(f'rc={rc}\n{out}'); self.pause()
 def header(self,title): print('\033[2J\033[H'+('='*72)+f'\n{title.center(72)}\n'+('='*72))
 def dashboard(self):
  self.header('DASHBOARD'); d=snapshot(self.root); print(json.dumps(d,indent=2,ensure_ascii=False)); self.pause()
 def runtime(self):
  while True:
   self.header('RUNTIME CONTROL'); print('[1] Restart active worker\n[2] Stop automation\n[3] Cut over to standby\n[4] Deployment status\n[0] Back'); c=input('Select: ')
   py=sys.executable
   if c=='0':return
   if c=='1':self.cmd([py,str(self.manager/'socctl.py'),'--root',str(self.root),'restart','--timeout','300'],'RESTART')
   elif c=='2':self.cmd([py,str(self.manager/'socctl.py'),'--root',str(self.root),'stop','--timeout','300'],'STOP')
   elif c=='3':
    target='green' if snapshot(self.root)['active_slot']=='blue' else 'blue'; self.cmd([py,str(self.manager/'cutover_manager.py'),'--root',str(self.root),'--target',target,'--timeout','300','--stabilization','180'],f'CUTOVER {target}')
   elif c=='4':self.cmd([py,str(self.manager/'deploy_manager.py'),'--root',str(self.root),'status'])
 def inspect_patch(self,path):
  p=Path(path).expanduser().resolve()
  if not p.is_file() or p.suffix.lower()!='.zip':raise ValueError('Patch must be an existing .zip file')
  with zipfile.ZipFile(p) as z:
   bad=z.testzip()
   if bad:raise ValueError(f'ZIP integrity failure: {bad}')
   m=json.loads(z.read('manifest.json'))
  return p,m,hashlib.sha256(p.read_bytes()).hexdigest()
 def updates(self):
  self.header('UPDATE MANAGER'); raw=input('Path patch ZIP: ').strip()
  try:p,m,h=self.inspect_patch(raw)
  except Exception as e:return self.pause(f'Blocked: {e}\nPress Enter')
  print(json.dumps({'path':str(p),'sha256':h,'manifest':m},indent=2,ensure_ascii=False)); print('\n[1] Dry-run\n[2] Transactional deploy\n[0] Back'); c=input('Select: '); py=sys.executable
  if c=='1':self.cmd([py,str(self.manager/'local_release_manager.py'),'--root',str(self.root),'apply','--package',str(p),'--dry-run'])
  elif c=='2':self.cmd([py,str(self.manager/'deploy_manager.py'),'--root',str(self.root),'deploy','--package',str(p),'--timeout','300'],f'DEPLOY {m.get("version")}'); raise SystemExit('Deployment finished. Reopen TUI from the new release.')
 def page(self,text,title):
  lines=text.splitlines() or ['']; step=22
  for i in range(0,len(lines),step):self.header(title); print('\n'.join(lines[i:i+step])); input(f'Page {i//step+1}/{(len(lines)+step-1)//step}; Enter=next, q=quit: ') == 'q' and (_ for _ in ()).throw(StopIteration)
 def audit(self):
  base=self.shared/'audit_logs'; files=sorted(base.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
  self.header('AUDIT VIEWER - LOCAL READ ONLY'); print('Sensitive technical evidence may be present. Nothing is sent externally.')
  for i,p in enumerate(files[:200],1):print(f'[{i}] {p.name} ({p.stat().st_size} bytes)')
  c=input('Select, path, or 0: ').strip()
  if c=='0':return
  p=files[int(c)-1] if c.isdigit() and 1<=int(c)<=len(files) else Path(c).expanduser().resolve()
  try:
   if base.resolve() not in p.parents:raise ValueError('Only shared/audit_logs is allowed')
   data=json.loads(p.read_text(errors='replace')); mode=input('[1] Summary [2] Full JSON: ')
   text=json.dumps(data,indent=2,ensure_ascii=False) if mode=='2' else json.dumps({'file':p.name,'size':p.stat().st_size,'top_level':list(data) if isinstance(data,dict) else type(data).__name__,'hits_total':(((data.get('hits') or {}).get('total') or {}).get('value') if isinstance(data,dict) else None)},indent=2)
   try:self.page(text,p.name)
   except StopIteration:pass
  except Exception as e:self.pause(f'ERROR: {e}\nPress Enter')
 def choose_file(self,base,patterns,title):
  files=[]
  for pat in patterns:files.extend(base.rglob(pat))
  files=sorted(set(files),key=lambda p:p.stat().st_mtime,reverse=True)[:200]; self.header(title)
  for i,p in enumerate(files,1):print(f'[{i}] {p.relative_to(base)}')
  c=input('Select or 0: '); return None if c=='0' else files[int(c)-1]
 def logs(self):
  p=self.choose_file(self.shared/'logs',['*.log','*.out'],'LOG VIEWER')
  if p:
   try:self.page('\n'.join(p.read_text(errors='replace').splitlines()[-500:]),p.name)
   except StopIteration:pass
 def system_health(self):
  self.header('SYSTEM HEALTH'); checks=[]
  for name,path in [('root',self.root),('current',self.root/'current'),('manager',self.manager),('shared',self.shared)]:checks.append((name,path.exists(),str(path)))
  try:d=snapshot(self.root); checks += [('schema',d.get('schema_version')==2,d.get('schema_version')),('master',d['master'].get('alive'),d['master'].get('pid')),('sqlite',d.get('sqlite_integrity') in ('ok','missing'),d.get('sqlite_integrity'))]
  except Exception as e:checks.append(('snapshot',False,str(e)))
  for n,ok,v in checks:print(f'{"PASS" if ok else "FAIL":4} {n:16} {v}')
  print('\nPython:',sys.version.split()[0],'tmux:',shutil.which('tmux') or 'missing'); self.pause()
 def privacy_regression(self):
  current=(self.root/'current').resolve(); tests=[current/'tests/test_path_scoped_sanitizer.py',current/'tests/test_privacy_manager.py']; lines=[]; passed=0
  for test in tests:
   if not test.is_file():lines.append(f'FAIL {test.name}: file not found'); continue
   rc,out=self.run([sys.executable,str(test)],timeout=180); status='PASS' if rc==0 else 'FAIL'; passed += int(rc==0); lines.append(f'{status} {test.name} (rc={rc})'); lines.extend('  '+line for line in out.splitlines()[-12:])
  lines += ['',f'Passed: {passed}',f'Failed: {len(tests)-passed}',f'Status: {"PASS" if passed==len(tests) else "FAIL"}']
  try:self.page('\n'.join(lines),'PRIVACY REGRESSION TESTS')
  except StopIteration:pass
 def server01_diagnostic(self):
  code="import json,os,tempfile\nos.environ.setdefault('AUDIT_DIR',tempfile.mkdtemp(prefix='soc-server01-tui-'))\nfrom privacy_manager import PrivacyManager\nclass EmptyLocalAIDetector:\n def detect(self,payload): return []\npayload={'host':{'name':'server01'},'kibana.alert.reason':'event on server01'}\nm=PrivacyManager();m.local_ai_detector=EmptyLocalAIDetector();r=m.prepare_payload(ticket_key='SERVER01-TUI-DIAGNOSTIC',raw_json=json.dumps(payload));s=json.loads(r.sanitized_json);host=s['host']['name'];reason=s['kibana.alert.reason'];checks={'raw_server01_remaining':r.sanitized_json.count('server01'),'pseudonyms_consistent':reason=='event on '+host,'host_is_pseudonym':host.startswith('HOST_'),'safe_for_ai':r.safe_for_ai,'residual_count':r.residual_count};expected={'raw_server01_remaining':0,'pseudonyms_consistent':True,'host_is_pseudonym':True,'safe_for_ai':True,'residual_count':0};print(json.dumps({'sanitized':s,'checks':checks,'status':'PASS' if checks==expected else 'FAIL'},indent=2))"
  rc,out=self.run([sys.executable,'-c',code],timeout=120)
  try:self.page(f'rc={rc}\n{out}','SERVER01 SANITIZER DIAGNOSTIC')
  except StopIteration:pass
 def diagnostics(self):
  while True:
   self.header('DIAGNOSTICS'); print('[1] System health\n[2] Privacy regression tests\n[3] Server01 sanitizer diagnostic\n[0] Back'); c=input('Select: ').strip()
   if c=='0':return
   if c=='1':self.system_health()
   elif c=='2':self.privacy_regression()
   elif c=='3':self.server01_diagnostic()
 def viewer(self):
  while True:
   self.header('VIEWER SERVICE'); print('[1] Start localhost:8765\n[2] Stop\n[3] Status\n[4] Show URL\n[0] Back'); c=input('Select: ')
   if c=='0':return
   if c=='1':self.cmd(['tmux','new-session','-d','-s','soc-viewer',f'cd {self.root}/current && exec {sys.executable} soc_viewer.py --root {self.root} --host 127.0.0.1 --port 8765'],'START VIEWER')
   elif c=='2':self.cmd(['tmux','kill-session','-t','soc-viewer'],'STOP VIEWER')
   elif c=='3':self.cmd(['tmux','has-session','-t','soc-viewer'])
   elif c=='4':self.pause('http://127.0.0.1:8765\nPress Enter')
 def releases(self):
  while True:
   self.header('RELEASE AND ROLLBACK'); rel=sorted((self.root/'releases').iterdir(),reverse=True) if (self.root/'releases').exists() else []; print('Current:',(self.root/'current').resolve()); print('Releases:',', '.join(p.name for p in rel)); print('\n[1] Release status\n[2] Rollback previous\n[3] Rollback to version\n[0] Back'); c=input('Select: '); py=sys.executable
   if c=='0':return
   if c=='1':self.cmd([py,str(self.manager/'local_release_manager.py'),'--root',str(self.root),'status'])
   elif c=='2':self.cmd([py,str(self.manager/'local_release_manager.py'),'--root',str(self.root),'rollback'],'ROLLBACK')
   elif c=='3':
    v=input('Version: ').strip(); self.cmd([py,str(self.manager/'local_release_manager.py'),'--root',str(self.root),'rollback','--to',v],f'ROLLBACK {v}')
 def maintenance(self):
  self.header('MAINTENANCE'); print('[1] Cleanup dry-run\n[2] Apply cleanup\n[3] Compile current Python files\n[0] Back'); c=input('Select: '); py=sys.executable
  if c=='1':self.cmd([py,str(self.manager/'cleanup_manager.py'),'--root',str(self.root),'--dry-run'])
  elif c=='2':self.cmd([py,str(self.manager/'cleanup_manager.py'),'--root',str(self.root)],'CLEANUP')
  elif c=='3':self.cmd([py,'-m','compileall','-q',str(self.root/'current')])
 def main(self):
  actions={'1':self.dashboard,'2':self.runtime,'3':self.updates,'4':self.audit,'5':self.logs,'6':self.diagnostics,'7':self.viewer,'8':self.releases,'9':self.maintenance}
  while True:
   self.header('SOC AUTOMATION CONTROL TUI'); print('[1] Dashboard\n[2] Runtime control\n[3] Update manager\n[4] Audit viewer\n[5] Log viewer\n[6] Diagnostics\n[7] Viewer service\n[8] Release and rollback\n[9] Maintenance\n[0] Exit'); c=input('Select: ').strip()
   if c=='0':return 0
   if c in actions:actions[c]()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='~/SOC-Automation');a=p.parse_args();return Console(a.root).main()
if __name__=='__main__':raise SystemExit(main())
