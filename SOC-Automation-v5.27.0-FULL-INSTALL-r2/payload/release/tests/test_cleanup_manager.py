from __future__ import annotations
import tempfile, time
from pathlib import Path
from cleanup_manager import cleanup
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    for name in ('incoming','applied','failed'):
        (root/'updates'/name).mkdir(parents=True)
    (root/'releases'/'.vbroken.staging').mkdir(parents=True)
    for i in range(6):
        p=root/'updates'/'applied'/f'patch-{i}.zip'; p.write_bytes(b'x'*(i+1));
        old=time.time()-(i*10); __import__('os').utime(p,(old,old))
    (root/'updates'/'incoming'/'download.part').write_bytes(b'partial')
    cache=root/'manager'/'__pycache__'; cache.mkdir(parents=True); (cache/'x.pyc').write_bytes(b'cache')
    preview=cleanup(root,keep_applied=2,keep_failed=1,max_age_days=30,dry_run=True)
    assert preview.removed_files and preview.removed_dirs
    assert (root/'updates'/'incoming'/'download.part').exists()
    report=cleanup(root,keep_applied=2,keep_failed=1,max_age_days=30)
    assert len(list((root/'updates'/'applied').iterdir()))==2
    assert not (root/'releases'/'.vbroken.staging').exists()
    assert not cache.exists()
    assert report.reclaimed_bytes > 0
print('Safe cleanup manager tests: OK')
