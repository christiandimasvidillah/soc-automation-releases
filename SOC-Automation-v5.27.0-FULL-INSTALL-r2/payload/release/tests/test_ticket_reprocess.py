from __future__ import annotations
import json,os,sys,tempfile,time
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from ticket_lock import TicketLockStore
root=Path(tempfile.mkdtemp(prefix='soc-requeue-test-'));db=root/'shared/ticket_locks.sqlite3';store=TicketLockStore(db,'test-owner')
store.mark_processing('CSOC-1');store.mark_failure('CSOC-1', 'SANITIZATION_FAILED', max_attempts=1)
assert store.processing_state('CSOC-1')['state']=='blocked_manual_review'
after=store.requeue_validated('CSOC-1');assert after['state']=='pending' and after['attempts']==0 and after['failure_code'] is None
assert store.acquire('CSOC-2');store.mark_processing('CSOC-2');store.mark_failure('CSOC-2','SANITIZATION_FAILED',max_attempts=1)
try:store.requeue_validated('CSOC-2');raise AssertionError('active lease must block requeue')
except RuntimeError as exc:assert str(exc)=='TICKET_HAS_ACTIVE_LEASE'
store.close();print('Ticket reprocess regression test: OK')
