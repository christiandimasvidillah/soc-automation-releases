#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sqlite3,time
from pathlib import Path
TERMINAL={"completed"}
def state_map(db):
 if not db.is_file():return {},{}
 con=sqlite3.connect(db)
 try:
  states=dict(con.execute("SELECT ticket_key,state FROM ticket_processing_state").fetchall())
  disp={r[0]:{"reason":r[1],"raw_cleanup_after":r[2]} for r in con.execute("SELECT ticket_key,reason,raw_cleanup_after FROM ticket_manual_disposition").fetchall()}
  return states,disp
 except sqlite3.Error:return {},{}
 finally:con.close()
def key_from(path,suffix):return path.name[:-len(suffix)]
def evaluate(root,raw_days=14,sanitized_days=90,apply=False,now=None):
 now=time.time() if now is None else float(now);audit=root/'shared/audit_logs';states,disp=state_map(root/'shared/ticket_locks.sqlite3')
 report={"status":"PASS","mode":"apply" if apply else "dry-run","policy":{"raw_days":raw_days,"sanitized_days":sanitized_days},"eligible":[],"deleted":[],"protected":[],"reclaimed_bytes":0}
 for p in sorted(audit.glob('*_raw.json')):
  key=key_from(p,'_raw.json');age=(now-p.stat().st_mtime)/86400;reason=None
  if key in disp:
   due=disp[key].get('raw_cleanup_after');reason='dismissed_due' if due is not None and due<=now else None
   if reason is None:report['protected'].append({"ticket":key,"kind":"raw","reason":"dismissed_grace_or_hold"});continue
  elif states.get(key) in TERMINAL and age>=raw_days:reason='completed_retention'
  else:report['protected'].append({"ticket":key,"kind":"raw","reason":states.get(key,'unknown_or_retryable')});continue
  item={"ticket":key,"kind":"raw","reason":reason,"bytes":p.stat().st_size,"path":str(p)};report['eligible'].append(item)
  if apply:p.unlink(missing_ok=True);report['deleted'].append(item);report['reclaimed_bytes']+=item['bytes']
 for p in sorted(audit.glob('*_sanitized.json')):
  key=key_from(p,'_sanitized.json');age=(now-p.stat().st_mtime)/86400
  if age<sanitized_days:continue
  if key not in disp and states.get(key) not in TERMINAL:report['protected'].append({"ticket":key,"kind":"sanitized","reason":states.get(key,'unknown_or_retryable')});continue
  item={"ticket":key,"kind":"sanitized","reason":"retention","bytes":p.stat().st_size,"path":str(p)};report['eligible'].append(item)
  if apply:p.unlink(missing_ok=True);report['deleted'].append(item);report['reclaimed_bytes']+=item['bytes']
 report['summary']={"eligible":len(report['eligible']),"deleted":len(report['deleted']),"protected":len(report['protected']),"reclaimed_bytes":report['reclaimed_bytes']};return report
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');p.add_argument('--raw-days',type=int,default=14);p.add_argument('--sanitized-days',type=int,default=90);p.add_argument('--apply',action='store_true');a=p.parse_args();print(json.dumps(evaluate(a.root.expanduser().resolve(),a.raw_days,a.sanitized_days,a.apply),indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
