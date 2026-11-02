import tempfile
from pathlib import Path
from release_qualification_gate import check_release
with tempfile.TemporaryDirectory() as td:
 root=Path(td)
 for name in ('runtime_events.py','ticket_processor.py','privacy_manager.py','ticket_lock.py','soc_viewer.py','ticket_history_retention.py'):(root/name).write_text('def ok():\n return True\n')
 (root/'worker_manager.py').write_text('from runtime_events import emit_ticket_event\ndef run():\n emit_ticket_event("X","Y","PASS")\n')
 (root/'VERSION').write_text('test')
 (root/'tests').mkdir()
 for name in ('test_worker_runtime_event_import.py','test_runtime_events.py','test_ticket_history_retention.py','test_web_live_viewer.py','test_jira_status_events.py'):(root/'tests'/name).write_text('print("PASS")\n')
 result=check_release(root);assert result['passed'],result
 (root/'worker_manager.py').write_text('def run():\n emit_ticket_event("X","Y","PASS")\n')
 result=check_release(root);assert not result['passed'];assert any(x['name'].endswith('emit_ticket_event') and not x['passed'] for x in result['checks'])
print('PASS test_release_qualification_gate')
