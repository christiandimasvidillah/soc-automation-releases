#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from retention_policy import DEFAULTS,load,save
from audit_retention_manager import evaluate
from ticket_history_retention import compact_history
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');sub=p.add_subparsers(dest='cmd',required=True);sub.add_parser('show');u=sub.add_parser('set')
 for key in DEFAULTS:u.add_argument('--'+key.replace('_','-'),dest=key,type=int)
 sub.add_parser('preview');a=sub.add_parser('apply');a.add_argument('--confirm',action='store_true');args=p.parse_args();root=args.root.expanduser().resolve();policy=load(root)
 if args.cmd=='set':policy=save(root,{**policy,**{k:getattr(args,k) for k in DEFAULTS if getattr(args,k) is not None}})
 if args.cmd in {'show','set'}:out={'status':'PASS','policy':policy,'path':str(root/'shared/retention_policy.json')}
 else:
  do_apply=args.cmd=='apply' and args.confirm
  audit=evaluate(root,policy['raw_audit_days'],policy['sanitized_audit_days'],do_apply)
  history=compact_history(root/'shared',policy['completed_history_days'],policy['failed_history_days']) if do_apply else {'status':'PREVIEW_ONLY','completed_days':policy['completed_history_days'],'failed_days':policy['failed_history_days']}
  out={'status':'PASS','mode':'apply' if do_apply else 'preview','policy':policy,'audit':audit,'history':history}
 print(json.dumps(out,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
