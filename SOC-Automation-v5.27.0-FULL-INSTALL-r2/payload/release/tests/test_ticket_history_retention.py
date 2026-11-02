import json,tempfile,time
from pathlib import Path
from ticket_history_retention import compact_history
with tempfile.TemporaryDirectory() as td:
 shared=Path(td)/'shared';control=shared/'control';control.mkdir(parents=True);now=time.time();events=[{"epoch":now-8*86400,"ticket_key":"OLD","status":"COMPLETED"},{"epoch":now-2*86400,"ticket_key":"NEW","status":"COMPLETED"},{"epoch":now-20*86400,"ticket_key":"FAIL","status":"FAILED"}];(control/'ticket_events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in events));(control/'ticket_live_state.json').write_text(json.dumps({x['ticket_key']:x for x in events}));r=compact_history(shared,7,30,now);assert r['events_deleted']==1;left=(control/'ticket_events.jsonl').read_text();assert 'OLD' not in left and 'NEW' in left and 'FAIL' in left
print('PASS test_ticket_history_retention')
