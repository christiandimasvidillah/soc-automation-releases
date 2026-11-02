#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
from datetime import datetime,timezone

DENY_PARTS={'.git','__pycache__','audit_logs','logs','backups','.venv','shared','releases'}
DENY_PATTERNS=[re.compile(x,re.I) for x in [r'\.bak(?:\.|$)',r'\.pre-',r'\.before-',r'\.broken-',r'~$',r'\.pyc$',r'^\.env$',r'\.(?:key|pem|p12|pfx|sqlite|sqlite3|db|jsonl|log)$']]
SECRET_PATTERNS=[re.compile(x.encode(),re.I) for x in [r'BEGIN [A-Z ]*PRIVATE KEY',r'AIza[0-9A-Za-z_-]{20,}',r'bot[0-9]{8,}:[A-Za-z0-9_-]{20,}',r'gh[pousr]_[A-Za-z0-9_]{20,}',r'AKIA[0-9A-Z]{16}']]
TOP_FILES={'VERSION','RELEASE.json','requirements.txt','README.md','DOCUMENTATION_ACCEPTANCE_CHECKLIST.md'}
TREES={'viewer_static','docs_static','docs','tests'}
MANAGER_FILES={'build_local_patch.py','socctl.py','deploy_manager.py','cleanup_manager.py','soc_control_tui.py','standby_worker.py','local_release_manager.py','soc-tui','cutover_manager.py','soc_master.py','build_full_local_installer.py'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def denied(p,root=None):
 try:q=p.relative_to(root) if root is not None else p
 except ValueError:q=p
 return any(x in DENY_PARTS for x in q.parts) or any(r.search(q.name) for r in DENY_PATTERNS)
PRIVATE_KEY_BLOCK=re.compile(br'-----BEGIN [A-Z ]*PRIVATE KEY-----\s*(.*?)\s*-----END [A-Z ]*PRIVATE KEY-----',re.I|re.S)
ALLOWED_SYNTHETIC_FIXTURES={'tests/test_secret_blob_hardening.py'}
def relative_identity(p,current=None):
 if current is not None:
  try:return p.relative_to(current).as_posix()
  except ValueError:pass
 return p.as_posix()
def real_private_key_material(b):
 for match in PRIVATE_KEY_BLOCK.finditer(b):
  body=re.sub(br'[^A-Za-z0-9+/=]',b'',match.group(1))
  if len(body)>=128:return True
 return False
def scan_bytes(identity,b):
 findings=[];accepted=[]
 for r in SECRET_PATTERNS:
  if not r.search(b):continue
  pattern=r.pattern.decode()
  if pattern=='BEGIN [A-Z ]*PRIVATE KEY' and identity in ALLOWED_SYNTHETIC_FIXTURES and not real_private_key_material(b):
   accepted.append({'file':identity,'pattern':'PRIVATE_KEY_TEST_FIXTURE','classification':'SYNTHETIC_NON_SECRET'})
  else:findings.append(pattern)
 return findings,accepted
def scan_file(p,current=None):return scan_bytes(relative_identity(p,current),p.read_bytes())
def selected_release(current):
 out=[]
 for p in current.iterdir():
  if p.is_file() and (p.suffix=='.py' or p.name in TOP_FILES or re.fullmatch(r'V\d+_\d+_\d+_RELEASE_NOTES_(ID|EN)\.md',p.name)) and not denied(p,current):out.append(p)
 for name in TREES:
  d=current/name
  if d.is_dir():out += [p for p in d.rglob('*') if p.is_file() and not denied(p,current)]
 return out
def selected_manager(manager):return [manager/n for n in MANAGER_FILES if (manager/n).is_file() and not denied(manager/n,manager)]
def install_script():
 lines=[
  '#!/usr/bin/env python3',
  'from pathlib import Path',
  'import argparse,os,shutil,subprocess,sys',
  "p=argparse.ArgumentParser();p.add_argument('--root',default='~/SOC-Automation');p.add_argument('--skip-dependencies',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()",
  "root=Path(a.root).expanduser().resolve();base=Path(__file__).resolve().parent",
  "(root/'releases').mkdir(parents=True,exist_ok=True);(root/'manager').mkdir(exist_ok=True);(root/'shared').mkdir(exist_ok=True)",
  "for rel in ('logs','control','audit_logs','workers','backups'):(root/'shared'/rel).mkdir(parents=True,exist_ok=True)",
  "ver=(base/'payload/release/VERSION').read_text(encoding='utf-8').strip();dest=root/'releases'/ver",
  "if dest.exists():raise SystemExit('Target release already exists: '+str(dest))",
  "shutil.copytree(base/'payload/release',dest);shutil.copytree(base/'payload/manager',root/'manager',dirs_exist_ok=True)",
  "cur=root/'current';tmp=root/'.current.new';tmp.unlink(missing_ok=True);tmp.symlink_to(dest);tmp.replace(cur)",
  "marker=root/'.installation-root';marker.write_text(str(root)+chr(10),encoding='utf-8');os.chmod(marker,0o600)",
  "launcher=root/'manager/soc-tui';os.chmod(launcher,0o750) if launcher.exists() else None",
  "venv=root/'.venv';subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)",
  "if not a.skip_dependencies:subprocess.run([str(venv/'bin/pip'),'install','-r',str(dest/'requirements.txt')],check=True)",
  "print('Installed',ver,'at',root);print('Launcher:',launcher)",
 ]
 return chr(10).join(lines)+chr(10)

def compile_gate(path,label):
 with tempfile.NamedTemporaryFile(prefix='soc-compile-',suffix='.pyc') as compiled:
  code='import py_compile,sys;py_compile.compile(sys.argv[1],cfile=sys.argv[2],doraise=True)'
  result=subprocess.run([sys.executable,'-c',code,str(path),compiled.name],text=True,capture_output=True)
 if result.returncode!=0:raise SystemExit(f'BUILD BLOCKED: {label} compile failed: {result.stderr.strip()}')

def installation_simulation(stage):
 compile_gate(stage/'install.py','generated install.py')
 with tempfile.TemporaryDirectory(prefix='soc-install-simulation-') as td:
  simroot=Path(td)/'Custom Root - SOC Test'
  result=subprocess.run([sys.executable,str(stage/'install.py'),'--root',str(simroot),'--skip-dependencies'],text=True,capture_output=True,timeout=180)
  if result.returncode!=0:raise SystemExit('BUILD BLOCKED: custom-root installation simulation failed: '+(result.stdout+result.stderr).strip())
  required=[simroot/'.installation-root',simroot/'current/VERSION',simroot/'manager/soc-tui',simroot/'.venv/bin/python']
  missing=[str(p) for p in required if not p.exists()]
  if missing:raise SystemExit('BUILD BLOCKED: simulation missing: '+', '.join(missing))
  if (simroot/'.installation-root').read_text(encoding='utf-8').strip()!=str(simroot.resolve()):raise SystemExit('BUILD BLOCKED: installation root metadata mismatch')
  compile_gate(simroot/'manager/soc_control_tui.py','installed Manager/TUI')
  installed_tui=simroot/'manager/soc_control_tui.py';original=installed_tui.read_bytes()
  installed_tui.write_text("import argparse,pathlib\np=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();print(pathlib.Path(a.root).resolve())\n",encoding='utf-8')
  clean_env=os.environ.copy()
  clean_env.pop('SOC_AUTOMATION_ROOT',None);clean_env.pop('PYTHONPATH',None)
  launcher=subprocess.run([str(simroot/'manager/soc-tui'),'--root',str(simroot)],text=True,capture_output=True,timeout=60,env=clean_env,stdin=subprocess.DEVNULL)
  installed_tui.write_bytes(original)
  if launcher.returncode!=0 or launcher.stdout.strip()!=str(simroot.resolve()):raise SystemExit('BUILD BLOCKED: custom-root launcher test failed: '+(launcher.stdout+launcher.stderr).strip())
 return {'generated_install_compile':'PASS','custom_root_simulation':'PASS','launcher_execution':'PASS','installed_tui_compile':'PASS','installation_root_metadata':'PASS'}

def build(root,out,report):
 current=(root/'current').resolve();manager=root/'manager';version=(current/'VERSION').read_text().strip();files=[]
 with tempfile.TemporaryDirectory(prefix='soc-full-safe-') as td:
  stage=Path(td)/f'SOC-Automation-v{version}-FULL-INSTALL';(stage/'payload/release').mkdir(parents=True);(stage/'payload/manager').mkdir(parents=True)
  for p in selected_release(current):
   rel=p.relative_to(current);q=stage/'payload/release'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);files.append(q)
  for p in selected_manager(manager):
   q=stage/'payload/manager'/p.name;shutil.copy2(p,q);files.append(q)
  required_release=['VERSION','RELEASE.json','requirements.txt','main.py','config.py']
  missing=[name for name in required_release if not (stage/'payload/release'/name).is_file()]
  if missing:raise SystemExit('BUILD BLOCKED: missing required release payload: '+', '.join(missing))
  release_files=[p for p in (stage/'payload/release').rglob('*') if p.is_file()]
  if len(release_files)<10:raise SystemExit(f'BUILD BLOCKED: release payload unexpectedly small ({len(release_files)} files)')
  (stage/'install.py').write_text(install_script(),encoding='utf-8');os.chmod(stage/'install.py',0o755)
  installer_validation=installation_simulation(stage)
  env=current/'env.example'
  if env.exists(): (stage/'config').mkdir();shutil.copy2(env,stage/'config/env.example')
  bad=[];accepted=[]
  for p in stage.rglob('*'):
   if p.is_file():
    if denied(p):bad.append({'file':str(p.relative_to(stage)),'reason':'denied_name'})
    identity=str(p.relative_to(stage)).replace('payload/release/','',1) if str(p.relative_to(stage)).startswith('payload/release/') else str(p.relative_to(stage))
    hits,accepted_hits=scan_bytes(identity,p.read_bytes())
    for hit in hits:bad.append({'file':str(p.relative_to(stage)),'reason':'secret_pattern','pattern':hit})
    accepted.extend(accepted_hits)
  if bad:raise SystemExit('BUILD BLOCKED: '+json.dumps(bad[:20]))
  manifest={'schema_version':2,'application':'SOC Jira Automation Full Installer','version':version,'builder_policy':'explicit-active-file-allowlist','created_at':datetime.now(timezone.utc).isoformat(),'files':{}}
  for p in sorted(stage.rglob('*')):
   if p.is_file():manifest['files'][p.relative_to(stage).as_posix()]={'sha256':sha(p),'size':p.stat().st_size}
  (stage/'manifest.json').write_text(json.dumps(manifest,indent=2));
  sums='\n'.join(f"{sha(p)}  {p.relative_to(stage).as_posix()}" for p in sorted(stage.rglob('*')) if p.is_file())+'\n';(stage/'SHA256SUMS').write_text(sums)
  out.mkdir(parents=True,exist_ok=True);z=out/f'SOC-Automation-v{version}-FULL-INSTALL.zip'
  with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as a:
   for p in sorted(stage.rglob('*')):
    if p.is_file():a.write(p,(stage.name+'/'+p.relative_to(stage).as_posix()))
  with zipfile.ZipFile(z) as a:
   if a.testzip():raise SystemExit('ZIP integrity failed')
  with tempfile.TemporaryDirectory(prefix='soc-installer-extract-check-') as extracted:
   extract_root=Path(extracted)
   with zipfile.ZipFile(z) as archive:archive.extractall(extract_root)
   package_root=extract_root/stage.name
   compile_gate(package_root/'install.py','extracted install.py')
   sums={}
   for line in (package_root/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
    digest_value,relative=line.split('  ',1);sums[relative]=digest_value
   checksum_failures=[name for name,expected in sums.items() if not (package_root/name).is_file() or sha(package_root/name)!=expected]
   if checksum_failures:raise SystemExit('BUILD BLOCKED: extracted internal checksum failure: '+', '.join(checksum_failures[:20]))
  installer_validation['extracted_install_compile']='PASS';installer_validation['internal_checksums']='PASS'
  digest=sha(z);(out/(z.name+'.sha256')).write_text(f'{digest}  {z.name}\n')
  result={'status':'PASS','version':version,'package':str(z),'sha256':digest,'file_count':len(manifest['files']),'excluded_patterns':['*.bak*','*.pre-*','*.before-*','*.broken-*','secrets','production state'],'policy':'explicit active-file allowlist','custom_root_launcher':'root-aware','installation_root_metadata':'.installation-root','builder_version':'1.27.11','cumulative_from':['1.27.8','1.27.9','1.27.10'],'installer_generation_marker':'installer-generation-v1.27.11','installer_validation':installer_validation}
  report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
def scan_pkg(p,report):
 bad=[];accepted=[]
 with zipfile.ZipFile(p) as z:
  if z.testzip():bad.append({'reason':'zip_integrity'})
  for n in z.namelist():
   q=Path(n)
   if denied(q):bad.append({'file':n,'reason':'denied_name'})
   b=z.read(n)
   identity=n.split('/payload/release/',1)[-1] if '/payload/release/' in n else n
   hits,accepted_hits=scan_bytes(identity,b)
   for hit in hits:bad.append({'file':n,'reason':'secret_pattern','pattern':hit})
   accepted.extend(accepted_hits)
 result={'status':'PASS' if not bad else 'FAIL','package':str(p),'findings':bad,'accepted_test_fixtures':accepted};report.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));raise SystemExit(0 if not bad else 2)
def scan_active_root(root,report):
 current=(root/'current').resolve();manager=root/'manager';bad=[];accepted=[];scanned=[]
 candidates=selected_release(current)+selected_manager(manager)
 for p in candidates:
  scanned.append(str(p))
  if denied(p,current if p.is_relative_to(current) else manager):bad.append({'file':str(p),'reason':'denied_name'})
  hits,accepted_hits=scan_file(p,current if p.is_relative_to(current) else manager)
  for hit in hits:bad.append({'file':str(p),'reason':'secret_pattern','pattern':hit})
  accepted.extend(accepted_hits)
 result={'status':'PASS' if not bad else 'FAIL','mode':'active_allowlisted_source_scan','scanned_file_count':len(scanned),'findings':bad,'accepted_test_fixtures':accepted,'policy':'explicit active-file allowlist + fixture-aware secret validation'}
 report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));raise SystemExit(0 if not bad else 2)
def main():
 a=argparse.ArgumentParser();a.add_argument('--root',default='~/SOC-Automation');a.add_argument('--output');a.add_argument('--report',default='installer-scan-report.json');a.add_argument('--scan-package');a.add_argument('--scan-only',action='store_true');x=a.parse_args();report=Path(x.report).expanduser().resolve()
 if x.scan_package:return scan_pkg(Path(x.scan_package).expanduser().resolve(),report)
 if x.scan_only:return scan_active_root(Path(x.root).expanduser().resolve(),report)
 if not x.output:raise SystemExit('--output required')
 build(Path(x.root).expanduser().resolve(),Path(x.output).expanduser().resolve(),report)
if __name__=='__main__':main()
