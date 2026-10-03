"""Bound stop-release output while preserving driver and baseline brake priority."""
import math


class RestartRelease:
  def __init__(self, jerk=2.):
    self.jerk = jerk
    self.previous = None
    self.was_stopping = False
    self.releasing = False

  def update(self, *, base, stopping, enabled, active, driver_override, dt=.01):
    valid = math.isfinite(base) and math.isfinite(dt) and 0 < dt <= .05
    if not enabled or not active or driver_override or not valid:
      self.previous = None
      self.was_stopping = self.releasing = False
      return dict(after=base, active=False, reason='disabled_authority_driver_or_invalid')
    if self.was_stopping and not stopping and self.previous is not None and self.previous < 0:
      self.releasing = True
    after = base
    # A renewed stop must not discard a stricter in-flight release command.
    # min() still gives any stronger baseline braking immediate priority.
    if self.releasing:
      after = min(base, self.previous + self.jerk * dt)
      self.releasing = after < base
    self.previous = after
    self.was_stopping = stopping
    return dict(after=after, active=after != base,
                reason='bounded_stop_release' if after != base else 'baseline')

