#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,re,socket,tempfile,time,getpass
from pathlib import Path
from privacy_manager import PrivacyManager
from ticket_lock import TicketLockStore
KEY_RE=re.compile(r"^[A-Z][A-Z0-9_]+-[0-9]+$")
REASONS={"jira_done_manual","false_positive_manual","duplicate_ticket","no_further_analysis","other"}
def safe_key(value):
 key=value.strip().upper()
 if not KEY_RE.fullmatch(key):raise SystemExit("Invalid ticket key")
 return key
def raw_path(root,key):return root/'shared/audit_logs'/f'{key}_raw.json'
def retest(root,key):
 path=raw_path(root,key)
 if not path.is_file():raise RuntimeError(f'RAW_AUDIT_NOT_FOUND: {path}')
 raw=path.read_text(encoding='utf-8')
 audit=tempfile.mkdtemp(prefix=f'soc-retest-{key}-');os.environ['AUDIT_DIR']=audit
 result=PrivacyManager().prepare_payload(ticket_key=f'{key}-RETEST',raw_json=raw)
 return {'ticket_key':key,'source':str(path),'release':(root/'current/VERSION').read_text().strip(),'safe_for_ai':result.safe_for_ai,'findings_count':result.findings_count,'replacements_count':result.replacements_count,'residual_count':result.residual_count,'residual_categories':list(result.residual_categories),'status':'PASS' if result.safe_for_ai and result.residual_count==0 else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');sub=p.add_subparsers(dest='cmd',required=True)
 for name in ('state','retest','requeue','restore'):
  x=sub.add_parser(name);x.add_argument('ticket_key')
 x=sub.add_parser('dismiss');x.add_argument('ticket_key');x.add_argument('--reason',choices=sorted(REASONS),required=True);x.add_argument('--actor',default=getpass.getuser());x.add_argument('--cleanup-grace-days',type=int,default=7);x.add_argument('--keep-raw',action='store_true')
 a=p.parse_args();root=a.root.expanduser().resolve();key=safe_key(a.ticket_key);store=TicketLockStore(root/'shared/ticket_locks.sqlite3',f'tui-reprocess-{socket.gethostname()}-{os.getpid()}')
 try:
  if a.cmd=='state':out={'ticket_key':key,'state':store.processing_state(key),'manual_disposition':store.manual_disposition(key)}
  elif a.cmd=='retest':out=retest(root,key)
  elif a.cmd=='dismiss':
   cleanup_after=None if a.keep_raw else time.time()+max(0,a.cleanup_grace_days)*86400
   out={'ticket_key':key,'status':'DISMISSED','manual_disposition':store.dismiss_reprocessing(key,reason=a.reason,actor=a.actor,cleanup_after=cleanup_after),'raw_cleanup_scheduled':cleanup_after is not None}
  elif a.cmd=='restore':
   raw=raw_path(root,key)
   if not raw.is_file():raise RuntimeError('RAW_AUDIT_NOT_FOUND_RESTORE_BLOCKED')
   changed=store.restore_reprocessing(key);out={'ticket_key':key,'status':'RESTORED' if changed else 'NOT_DISMISSED','raw_audit_available':True}
  else:
   if store.manual_disposition(key) is not None:raise RuntimeError('TICKET_DISMISSED_RESTORE_REQUIRED')
   check=retest(root,key)
   if check['status']!='PASS':raise RuntimeError('PRIVACY_RETEST_NOT_PASSED')
   before=store.processing_state(key);after=store.requeue_validated(key);out={'ticket_key':key,'privacy_retest':check,'state_before':before,'state_after':after,'status':'REQUEUED'}
  print(json.dumps(out,indent=2,ensure_ascii=False));return 0
 except Exception as exc:print(json.dumps({'ticket_key':key,'status':'FAIL','error':str(exc)},indent=2));return 2
 finally:store.close()
if __name__=='__main__':raise SystemExit(main())
