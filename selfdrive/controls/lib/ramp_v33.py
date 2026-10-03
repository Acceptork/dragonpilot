"""Bounded e2e/MPC preference blend; never overrides a negative model request."""
import math


class RampRecovery:
  def __init__(self, maximum=.10, blend=.25, persistence=.5, slew=.10):
    if not (0 < maximum <= .15 and 0 < blend <= .25 and persistence >= .5 and 0 < slew <= .2):
      raise ValueError('outside experimental envelope')
    self.maximum, self.blend, self.persistence, self.slew = maximum, blend, persistence, slew
    self.since = self.last_t = None
    self.preference = 0.
    self.enter_time = self.exit_time = None

  def update(self, *, t, enabled, base, e2e, mpc, mode, valid, active, closing,
             stop, fcw, hard_brake, path_valid, pitch, grade_age, allow_throttle,
             driver_override, cruise_gap, accel_max):
    dt = .05 if self.last_t is None else t - self.last_t
    self.last_t = t
    finite = all(math.isfinite(x) for x in (t, base, e2e, mpc, cruise_gap, accel_max))
    grade = (pitch is not None and grade_age is not None and math.isfinite(pitch)
             and math.isfinite(grade_age) and .01 < pitch < .12 and 0 <= grade_age <= .2)
    safe = (enabled and finite and 0 < dt <= .075 and valid and active and mode == 'blended'
            and 0 < e2e <= .3 and base >= 0 and mpc > e2e + .2 and not closing
            and not stop and not fcw and not hard_brake and path_valid and grade
            and allow_throttle and not driver_override and cruise_gap > 2.)
    if not safe:
      if self.preference:
        self.exit_time = t
      self.since = None
      self.preference = 0.
      reason = 'safety_or_eligibility_veto'
    else:
      if self.since is None:
        self.since = t
      if t - self.since >= self.persistence - 1e-6:
        if not self.preference:
          self.enter_time = t
        self.preference = min(self.maximum, self.preference + self.slew * dt)
        reason = 'bounded_positive_e2e_mpc_blend'
      else:
        reason = 'persistence_pending'
    # MPC remains the hard upper ceiling, including both recorded lead constraints.
    desired = min(mpc, e2e + min(self.preference, self.blend * max(0., mpc - e2e)), accel_max)
    after = max(base, desired) if self.preference and safe else base
    # Never let pre-existing clipping create a larger change than the preference.
    after = min(after, base + self.preference) if self.preference and safe else base
    return dict(active=after > base, before=base, after=after, reason=reason,
                preference=self.preference, enter_time=self.enter_time, exit_time=self.exit_time)
