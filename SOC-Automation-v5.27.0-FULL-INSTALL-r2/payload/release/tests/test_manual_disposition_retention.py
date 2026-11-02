import os,tempfile,time,json
from pathlib import Path
from ticket_lock import TicketLockStore
from audit_retention_manager import evaluate
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/'SOC-Automation';audit=root/'shared/audit_logs';audit.mkdir(parents=True);db=root/'shared/ticket_locks.sqlite3';store=TicketLockStore(db,'test')
 key='CSOC-12345';raw=audit/f'{key}_raw.json';safe=audit/f'{key}_sanitized.json';raw.write_text('{}');safe.write_text('{}')
 old=time.time()-100*86400;os.utime(raw,(old,old));os.utime(safe,(old,old))
 store.dismiss_reprocessing(key,reason='jira_done_manual',actor='test',cleanup_after=time.time()-1)
 allowed,reason=store.processing_allowed(key);assert not allowed and reason=='dismissed_manual'
 preview=evaluate(root,apply=False);assert any(x['ticket']==key and x['kind']=='raw' for x in preview['eligible']);assert raw.exists()
 applied=evaluate(root,apply=True);assert not raw.exists() and not safe.exists();assert applied['summary']['deleted']==2
 assert store.restore_reprocessing(key);assert store.manual_disposition(key) is None
 store.close()
print('PASS test_manual_disposition_retention')
