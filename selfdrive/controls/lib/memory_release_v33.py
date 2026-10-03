"""Bound upward recovery after memory constrains a target; never delay braking."""
import math


class MemoryRelease:
  def __init__(self, jerk=2.):
    self.jerk = jerk
    self.previous = None
    self.time = None
    self.pending = False

  def update(self, *, t, baseline, constrained, enabled, authority, driver_override):
    valid = all(math.isfinite(x) for x in (t, baseline, constrained))
    dt = t-self.time if self.time is not None else None
    if not valid or not enabled or not authority or driver_override or (dt is not None and not 0 < dt <= .2):
      self.previous = self.time = None
      self.pending = False
      return dict(after=constrained, release_active=False, release_reason='disabled_authority_driver_or_time')
    after = min(baseline, constrained)
    if self.pending and self.previous is not None:
      after = min(after, self.previous + self.jerk * min(dt, .05))
    release_active = after < min(baseline, constrained)
    self.pending = after < baseline
    self.previous, self.time = after, t
    return dict(after=after, release_active=release_active,
                release_reason='bounded_memory_recovery' if release_active else 'baseline_or_immediate_constraint')
