#!/usr/bin/env python3
from __future__ import annotations
import argparse,ast,importlib.util,json,py_compile,sys,time
from pathlib import Path
CORE_MODULES=("runtime_events.py","worker_manager.py","ticket_processor.py","privacy_manager.py","ticket_lock.py","soc_viewer.py","ticket_history_retention.py")
REQUIRED_SYMBOLS={"worker_manager.py":{"emit_ticket_event":"runtime_events"},"ticket_processor.py":{"emit_ticket_event":"runtime_events"}}
def check_release(release:Path):
 release=release.expanduser().resolve();checks=[]
 def add(name,passed,detail):checks.append({"name":name,"passed":bool(passed),"detail":str(detail)})
 version=(release/'VERSION').read_text().strip() if (release/'VERSION').is_file() else ''
 add('version_file',bool(version),version or 'missing')
 for name in CORE_MODULES:
  path=release/name
  if not path.is_file():add(f'file:{name}',False,'missing');continue
  try:py_compile.compile(str(path),doraise=True);add(f'syntax:{name}',True,'compiled')
  except Exception as exc:add(f'syntax:{name}',False,f'{type(exc).__name__}: {exc}')
  try:tree=ast.parse(path.read_text(encoding='utf-8'));add(f'ast:{name}',True,'parsed')
  except Exception as exc:add(f'ast:{name}',False,f'{type(exc).__name__}: {exc}')
 for filename,symbols in REQUIRED_SYMBOLS.items():
  path=release/filename
  if not path.is_file():continue
  try:tree=ast.parse(path.read_text(encoding='utf-8'))
  except Exception:continue
  imports={(node.module,alias.name) for node in ast.walk(tree) if isinstance(node,ast.ImportFrom) for alias in node.names}
  calls={node.func.id for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
  for symbol,module in symbols.items():
   used=symbol in calls;imported=(module,symbol) in imports
   add(f'symbol:{filename}:{symbol}',not used or imported,f'used={used} imported={imported} module={module}')
 tests=(release/'tests')
 selected=['test_worker_runtime_event_import.py','test_runtime_events.py','test_ticket_history_retention.py','test_web_live_viewer.py','test_jira_status_events.py']
 for name in selected:
  path=tests/name
  if not path.is_file():add(f'test:{name}',False,'missing');continue
  result=subprocess_run(path,release);add(f'test:{name}',result[0],result[1])
 passed=all(x['passed'] for x in checks)
 return {'schema_version':1,'generated_at':time.time(),'release':str(release),'version':version,'status':'passed' if passed else 'failed','passed':passed,'checks':checks,'summary':{'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks)}}
def subprocess_run(path,release):
 import os,subprocess
 env=os.environ.copy();env['PYTHONPATH']=str(release)
 try:r=subprocess.run([sys.executable,str(path)],text=True,capture_output=True,timeout=120,env=env)
 except Exception as exc:return False,f'{type(exc).__name__}: {exc}'
 detail=(r.stdout+r.stderr).strip()[-2000:] or f'returncode={r.returncode}'
 return r.returncode==0,detail
def main():
 p=argparse.ArgumentParser(description='SOC Automation release qualification gate');p.add_argument('--release',type=Path,default=Path.home()/'SOC-Automation/current');p.add_argument('--report',type=Path);a=p.parse_args();result=check_release(a.release)
 if a.report:a.report.expanduser().resolve().write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2));return 0 if result['passed'] else 2
if __name__=='__main__':raise SystemExit(main())
