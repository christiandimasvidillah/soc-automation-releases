from pathlib import Path
for name in ('worker_manager.py','ticket_processor.py'):
 text=(Path(__file__).parents[1]/name).read_text();assert 'JIRA_STATUS_TRANSITION' in text
html=(Path(__file__).parents[1]/'viewer_static/index.html').read_text();assert html.count('<details')>=3 and html.index('Workers')<html.index('LIVE PIPELINE')
js=(Path(__file__).parents[1]/'viewer_static/app.js').read_text();assert 'jira_status' in js
print('PASS test_jira_status_events')
