import tempfile
from pathlib import Path
from operational_alerts import OperationalAlertManager
sent=[]
with tempfile.TemporaryDirectory() as td:
 m=OperationalAlertManager(Path(td),send_func=lambda x:sent.append(x) or True,dedupe_seconds=3600);a=m.notify('CODE','component',fingerprint='fp',details={'worker':'blue','secret':'never'},now=100);b=m.notify('CODE','component',fingerprint='fp',details={'worker':'blue'},now=101);assert a['telegram_sent'] and not a['deduped'];assert b['deduped'] and len(sent)==1;assert 'never' not in (Path(td)/'shared/control/operational_alerts.jsonl').read_text();assert (Path(td)/'shared/control/operational_alerts.jsonl').stat().st_mode & 0o777==0o600
print('PASS test_operational_alerts')
