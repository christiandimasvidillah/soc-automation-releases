#!/usr/bin/env python3
from pathlib import Path
import argparse,os,shutil,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--root',default='~/SOC-Automation');p.add_argument('--skip-dependencies',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
root=Path(a.root).expanduser().resolve();base=Path(__file__).resolve().parent
(root/'releases').mkdir(parents=True,exist_ok=True);(root/'manager').mkdir(exist_ok=True);(root/'shared').mkdir(exist_ok=True)
for rel in ('logs','control','audit_logs','workers','backups'):(root/'shared'/rel).mkdir(parents=True,exist_ok=True)
ver=(base/'payload/release/VERSION').read_text(encoding='utf-8').strip();dest=root/'releases'/ver
if dest.exists():raise SystemExit('Target release already exists: '+str(dest))
shutil.copytree(base/'payload/release',dest);shutil.copytree(base/'payload/manager',root/'manager',dirs_exist_ok=True)
cur=root/'current';tmp=root/'.current.new';tmp.unlink(missing_ok=True);tmp.symlink_to(dest);tmp.replace(cur)
marker=root/'.installation-root';marker.write_text(str(root)+chr(10),encoding='utf-8');os.chmod(marker,0o600)
launcher=root/'manager/soc-tui';os.chmod(launcher,0o750) if launcher.exists() else None
venv=root/'.venv';subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
if not a.skip_dependencies:subprocess.run([str(venv/'bin/pip'),'install','-r',str(dest/'requirements.txt')],check=True)
print('Installed',ver,'at',root);print('Launcher:',launcher)
