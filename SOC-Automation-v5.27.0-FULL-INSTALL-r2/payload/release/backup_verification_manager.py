#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from backup_verifier import latest_backup,verify_archive
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('--archive',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();archive=a.archive or latest_backup(a.root)
 result=verify_archive(archive) if archive else {'status':'FAIL','valid':False,'archive':None,'checks':[{'name':'backup_available','status':'FAIL','passed':False,'detail':'no backup found'}]}
 if a.output:a.output.expanduser().resolve().write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2));return 0 if result['valid'] else 2
if __name__=='__main__':raise SystemExit(main())
