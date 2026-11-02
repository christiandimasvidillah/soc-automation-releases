import json,tempfile,os
from pathlib import Path
from runtime_events import TicketEventRecorder
with tempfile.TemporaryDirectory() as td:
 r=TicketEventRecorder(Path(td)/'shared');r.emit('CSOC-100','PRIVACY_GATE','PASS',residual_count=0,raw_json='must-not-store')
 event=json.loads((Path(td)/'shared/control/ticket_events.jsonl').read_text());assert event['ticket_key']=='CSOC-100';assert 'raw_json' not in event['details']
 live=json.loads((Path(td)/'shared/control/ticket_live_state.json').read_text());assert live['CSOC-100']['stage']=='PRIVACY_GATE'
print('PASS test_runtime_events')
