"""Read-only diagnostics. No actuator or engagement writes."""
from dataclasses import dataclass
import json
import math
import os

@dataclass
class OvershootEvent:
  since: float | None = None
  armed: bool = True
  last_t: float | None = None

  def update(self,t,speed_kph,target_kph,active):
    if self.last_t is not None and (t<=self.last_t or t-self.last_t>0.2):self.since=None
    self.last_t=t
    if not active or not all(math.isfinite(v) for v in (t,speed_kph,target_kph)) or not 8<=target_kph<=145:
      self.since=None;self.armed=True;return False
    if speed_kph<target_kph+0.5:self.armed=True
    if speed_kph<=target_kph+2:self.since=None;return False
    if self.since is None:self.since=t
    if self.armed and t-self.since>=1.0:
      self.armed=False;return True
    return False

def emit_trace(row):
  # Explicit local replay opt-in. Never fail control due to a diagnostic sink.
  path=os.environ.get('MYCRV_V32_TRACE_FILE')
  if path:
    try:
      with open(path,'a') as f:f.write(json.dumps(row,allow_nan=False,default=str)+'\n')
    except (OSError,ValueError,TypeError):pass
