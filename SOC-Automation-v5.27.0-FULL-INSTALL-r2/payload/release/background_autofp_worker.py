#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,sqlite3,time
from pathlib import Path
from autofp_candidate import create,verify
from controlled_autofp import execute
DB='shared/controlled_autofp.sqlite3'
def init(root):
 p=Path(root)/DB;p.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(p);db.execute('CREATE TABLE IF NOT EXISTS state(k TEXT PRIMARY KEY,v TEXT NOT NULL)');db.execute('CREATE TABLE IF NOT EXISTS actions(idempotency_key TEXT PRIMARY KEY,ticket TEXT,status TEXT,epoch REAL)');db.execute("INSERT OR IGNORE INTO state VALUES('mode','SHADOW')");db.commit();os.chmod(p,0o600);return db
def mode(db):return db.execute("SELECT v FROM state WHERE k='mode'").fetchone()[0]
def setmode(db,value):
 if value not in {'DISABLED','SHADOW','APPROVAL','LIMITED','GLOBAL'}:raise ValueError('invalid_mode')
 db.execute("INSERT OR REPLACE INTO state VALUES('mode',?)",(value,));db.commit();return value
def one(root,ticket,apply=False):
 root=Path(root);db=init(root);m=mode(db);report_path=root/'shared/audit_logs/smb_dry_run_latest.json';report=json.loads(report_path.read_text());c=create(root,ticket,report);v=verify(root,c);row={'ticket':ticket,'mode':m,'candidate':c,'verification':v,'action':'BLOCKED'}
 if m=='DISABLED' or not v['valid']:return row
 prior=db.execute('SELECT status FROM actions WHERE idempotency_key=?',(c['idempotency_key'],)).fetchone()
 if prior:row['action']='SKIPPED_ALREADY_PROCESSED';return row
 if m=='SHADOW':row['action']='SHADOW_ELIGIBLE';return row
 if m=='APPROVAL' and not apply:row['action']='AWAITING_APPROVAL';return row
 do_apply=apply or m in {'LIMITED','GLOBAL'}
 result=execute(root,ticket,report,apply=do_apply);row['controlled_result']=result;row['action']=result['action'];db.execute('INSERT OR REPLACE INTO actions VALUES(?,?,?,?)',(c['idempotency_key'],ticket,row['action'],time.time()));db.commit();return row
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'SOC-Automation');s=p.add_subparsers(dest='cmd',required=True);s.add_parser('status');q=s.add_parser('mode');q.add_argument('value');r=s.add_parser('run-ticket');r.add_argument('ticket');r.add_argument('--apply',action='store_true');a=p.parse_args();root=a.root.expanduser().resolve();db=init(root)
 if a.cmd=='status':out={'mode':mode(db),'database':str(root/DB)}
 elif a.cmd=='mode':out={'mode':setmode(db,a.value)}
 else:out=one(root,a.ticket.upper(),a.apply)
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
