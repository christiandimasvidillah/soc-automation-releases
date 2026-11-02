from __future__ import annotations
import hashlib,tarfile,time
from pathlib import Path, PurePosixPath

def verify_archive(path,read_all=True):
 path=Path(path).expanduser().resolve();checks=[]
 def add(name,status,detail):checks.append({'name':name,'status':status,'passed':status=='PASS','detail':detail})
 if not path.is_file():return {'status':'FAIL','valid':False,'archive':str(path),'checks':[{'name':'archive_exists','status':'FAIL','passed':False,'detail':'missing'}]}
 add('archive_exists','PASS',str(path));digest=hashlib.sha256();size=0
 with path.open('rb') as f:
  while True:
   chunk=f.read(1024*1024)
   if not chunk:break
   digest.update(chunk);size+=len(chunk)
 add('sha256','PASS',digest.hexdigest());unsafe=[];special=[];members=0;files=0;uncompressed=0
 try:
  with tarfile.open(path,'r:gz') as tar:
   for member in tar:
    members+=1;name=PurePosixPath(member.name)
    if name.is_absolute() or '..' in name.parts:unsafe.append(member.name)
    if member.issym() or member.islnk() or member.isdev():special.append(member.name)
    if member.isfile():
     files+=1;uncompressed+=max(0,member.size)
     if read_all:
      stream=tar.extractfile(member)
      if stream:
       while stream.read(1024*1024):pass
  add('gzip_tar_integrity','PASS',f'{members} members read')
 except Exception as exc:add('gzip_tar_integrity','FAIL',f'{type(exc).__name__}: {exc}')
 add('safe_member_paths','FAIL' if unsafe else 'PASS',f'{len(unsafe)} unsafe paths')
 add('no_special_members','FAIL' if special else 'PASS',f'{len(special)} links/devices')
 valid=all(x['passed'] for x in checks)
 return {'generated_at':time.time(),'status':'PASS' if valid else 'FAIL','valid':valid,'archive':str(path),'size_bytes':size,'sha256':digest.hexdigest(),'members':members,'files':files,'uncompressed_bytes':uncompressed,'checks':checks}
def latest_backup(root):
 folder=Path(root).expanduser().resolve()/'shared/backups';items=sorted(folder.glob('*.tar.gz'),key=lambda p:p.stat().st_mtime,reverse=True) if folder.is_dir() else [];return items[0] if items else None
