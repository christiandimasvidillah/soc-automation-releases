import json,tempfile
from pathlib import Path
from ticket_observability import build_report
with tempfile.TemporaryDirectory() as td:
 root=Path(td);control=root/'shared/control';control.mkdir(parents=True);events=[{'ticket_key':'A','epoch':100,'stage':'SIEM','status':'RUNNING','worker':'blue','details':{}},{'ticket_key':'A','epoch':110,'stage':'GEMINI','status':'RUNNING','worker':'blue','details':{'jira_status':'Waiting'}},{'ticket_key':'B','epoch':120,'stage':'DONE','status':'COMPLETED','worker':'blue','details':{'jira_status':'Done'}}];(control/'ticket_events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in events));r=build_report(root,stuck_seconds=30,now=200);assert r['summary']['tickets']==2 and r['summary']['stuck']==1;assert r['stuck_tickets'][0]['ticket_key']=='A';assert r['slowest_stages'][0]['stage']=='SIEM'
print('PASS test_ticket_observability')
