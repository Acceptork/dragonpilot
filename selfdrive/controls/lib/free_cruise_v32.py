"""Positive recovery shaping only after a stable, valid ACC clear-path interval."""
from dataclasses import dataclass
import math

@dataclass
class FreeCruiseRecovery:
  clear_time: float = 0.
  ramp: float = 0.
  active: bool = False
  reason: str = 'ineligible'

  def update(self, base, cap, gap, personality, eligible, dt=0.05):
    if not eligible or not all(math.isfinite(x) for x in (base,cap,gap,dt)) or dt<=0 or base<=0 or gap<=3/3.6:
      self.clear_time=0.; self.ramp=0.; self.active=False; self.reason='veto_or_approach'
      return base
    self.clear_time=min(0.7,self.clear_time+dt)
    if self.clear_time < 0.7-1e-6:
      self.reason='clear_persistence'
      return base
    if not self.active: self.ramp=max(0.,base); self.active=True
    name=str(personality)
    rate={'relaxed':0.15,'standard':0.3,'aggressive':0.6}[name]
    self.ramp=min(max(0.,cap),self.ramp+rate*dt)
    self.reason='free_cruise_'+name
    if name=='standard': return base
    if name=='relaxed': return min(base,self.ramp)
    # Only a bounded preference toward the existing cruise envelope, tapering
    # with speed error; no MPC weights, following gaps or braking changes.
    return min(cap,max(base,min(self.ramp,gap/4.,base+0.15)))
