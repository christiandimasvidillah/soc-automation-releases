from __future__ import annotations
import hashlib,time
class IntakeCircuitBreaker:
 def __init__(self,threshold=3,cooldown_seconds=300):
  self.threshold=max(1,int(threshold));self.cooldown_seconds=max(1,float(cooldown_seconds));self.consecutive_failures=0;self.fingerprint=None;self.opened_at=None;self.open_until=None
 def _fingerprint(self,exc):return hashlib.sha256(f'{type(exc).__name__}:{exc}'.encode()).hexdigest()[:16]
 def success(self):self.consecutive_failures=0;self.fingerprint=None;self.opened_at=None;self.open_until=None
 def failure(self,exc,now=None):
  now=time.time() if now is None else float(now);fp=self._fingerprint(exc)
  self.consecutive_failures=self.consecutive_failures+1 if fp==self.fingerprint else 1;self.fingerprint=fp
  if self.consecutive_failures>=self.threshold:self.opened_at=now;self.open_until=now+self.cooldown_seconds
  return self.snapshot(now)
 def is_open(self,now=None):
  now=time.time() if now is None else float(now)
  if self.open_until is None:return False
  if now>=self.open_until:self.success();return False
  return True
 def snapshot(self,now=None):
  now=time.time() if now is None else float(now)
  return {'state':'open' if self.is_open(now) else 'closed','consecutive_failures':self.consecutive_failures,'failure_fingerprint':self.fingerprint,'opened_at':self.opened_at,'open_until':self.open_until}
