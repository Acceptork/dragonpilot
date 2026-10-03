"""Closed-course stop shaping. Brake release requires a measured distance reserve."""
import math


class StopTaper:
  def __init__(self, delay_bound=.8, gain_lower=.5, jerk=2., hold_min=1.2):
    self.delay_bound = delay_bound
    self.gain_lower = gain_lower
    self.jerk = jerk
    self.hold_min = hold_min
    self.state = 'BRAKING'
    self.command = None
    self.stopped_time = 0.
    self.enter_time = self.exit_time = None
    self.clock = 0.

  def update(self, *, speed, base, pitch, grade_fresh, stop, enabled, active,
             danger=False, driver_override=False, remaining=None, dt=.01, lower=-3.5):
    self.clock += dt
    old = self.state
    finite = all(math.isfinite(x) for x in (speed, base, dt, lower))
    valid_grade = pitch is not None and math.isfinite(pitch) and abs(pitch) <= .12 and grade_fresh
    if not enabled or not active or not stop or driver_override or not finite or not valid_grade or not 0 < dt <= .05:
      self.state = 'BRAKING'
      self.command = base
      self.stopped_time = 0.
      return self.result(base, base, 'disabled_or_missing_grade_or_stop')
    # Lower actuator gain is a research envelope, not a measured Honda guarantee.
    grade_brake = 9.81 * abs(math.sin(pitch)) / self.gain_lower
    hold = -max(self.hold_min, grade_brake + .3)
    rollback = speed < -.02
    creep = self.state == 'HOLD' and abs(speed) > .04
    self.stopped_time = self.stopped_time + dt if abs(speed) < .03 else 0.
    if self.state == 'HOLD' or rollback or self.stopped_time >= .1:
      self.state = 'HOLD'
      target = min(base, hold - (.4 if creep or rollback else 0.))
      reason = 'rollback_guard' if rollback else 'creep_guard' if creep else 'terminal_hold'
    else:
      # Pre-taper braking includes delay and downhill authority. No fabricated stop line.
      target = min(base, -1.5 - grade_brake)
      reason = 'grade_compensated_braking'
      decel_floor = max(.4, self.hold_min * self.gain_lower - 9.81 * abs(math.sin(pitch)))
      reserve = abs(speed) * self.delay_bound + speed * speed / (2 * decel_floor) + .5
      distance_valid = remaining is not None and math.isfinite(remaining) and remaining > reserve
      can_taper = (not danger and -.8 <= base < 0 and .15 < speed < .5 and distance_valid and abs(pitch) < .02)
      self.state = 'TAPER' if can_taper else 'BRAKING'
      if can_taper:
        # A release from the stronger approach command, still stronger than the baseline.
        target = min(base, -self.hold_min)
        reason = 'measured_distance_reserve'
      elif remaining is None:
        reason = 'braking_no_measured_taper_reserve'
    target = max(lower, target)
    if self.command is None:
      self.command = base
    self.command += max(-self.jerk * dt, min(self.jerk * dt, target - self.command))
    # Safety braking can bypass comfort slew; experimental shaping never weakens it.
    self.command = max(lower, min(base, self.command))
    if old != self.state:
      self.exit_time = self.enter_time = self.clock
    return self.result(base, self.command, reason)

  def result(self, base, after, reason):
    return dict(state=self.state, active=after != base, before=base, after=after,
                reason=reason, enter_time=self.enter_time, exit_time=self.exit_time)
