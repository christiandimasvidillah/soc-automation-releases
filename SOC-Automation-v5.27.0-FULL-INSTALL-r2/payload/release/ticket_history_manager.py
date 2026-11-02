#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from ticket_history_retention import compact_history
def history(shared,limit=250):
 events=shared/'control/ticket_events.jsonl';grouped={}
 if events.is_file():
  for line in events.read_text(errors='replace').splitlines():
   try:e=json.loads(line)
   except Exception:continue
   key=str(e.get('ticket_key') or '')
   if key:grouped.setdefault(key,[]).append(e)
 rows=[]
 for key,items in grouped.items():
  items.sort(key=lambda x:float(x.get('epoch',0)));last=items[-1];rows.append({"ticket_key":key,"worker":last.get('worker'),"stage":last.get('stage'),"status":last.get('status'),"last_epoch":last.get('epoch'),"events":len(items),"timeline":items[-60:]})
 rows.sort(key=lambda x:float(x.get('last_epoch',0)),reverse=True);return rows[:limit]
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');sub=p.add_subparsers(dest='cmd',required=True);sub.add_parser('list');c=sub.add_parser('cleanup');c.add_argument('--completed-days',type=int,default=7);c.add_argument('--failed-days',type=int,default=30);a=p.parse_args();root=a.root.expanduser().resolve();shared=root/'shared'
 if a.cmd=='list':out={"status":"PASS","tickets":history(shared)}
 else:out=compact_history(shared,a.completed_days,a.failed_days)
 print(json.dumps(out,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
