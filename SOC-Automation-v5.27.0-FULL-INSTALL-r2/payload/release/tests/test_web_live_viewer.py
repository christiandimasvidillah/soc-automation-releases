import json,tempfile
from pathlib import Path
from soc_viewer import ticket_snapshot
with tempfile.TemporaryDirectory() as td:
 root=Path(td);control=root/'shared/control';control.mkdir(parents=True);event={"timestamp":"x","epoch":1,"ticket_key":"CSOC-1","worker":"blue","pid":1,"stage":"PRIVACY_GATE","status":"PASS","details":{"residual_count":0,"raw_json":"secret"}};(control/'ticket_live_state.json').write_text(json.dumps({"CSOC-1":event}));(control/'ticket_events.jsonl').write_text(json.dumps(event)+'\n');data=ticket_snapshot(root);assert data['tickets'][0]['ticket_key']=='CSOC-1';assert 'raw_json' not in data['tickets'][0]['details']
print('PASS test_web_live_viewer')
