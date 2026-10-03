"""Opt-in bounded early slowing. Does not assert a stop coordinate or hold intent."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Inputs:
  t: float
  v0: float
  endpoint: float
  desired: float
  base: float
  experimental: bool
  valid: bool
  engaged: bool
  should_stop: bool = False
  mpc_stop: bool = False
  standstill: bool = False
  driver_override: bool = False
  fcw: bool = False
  hard_brake: bool = False
  lead_present: bool = False


class EarlyStop:
  def __init__(self, endpoint=3., ratio=.5, persistence=.5, bias_max=.15, bias_jerk=.15):
    if not (0 < endpoint <= 4 and 0 < ratio <= .5 and .3 <= persistence <= 1.
            and 0 < bias_max <= .2 and 0 < bias_jerk <= .3):
      raise ValueError('research parameter outside bounded envelope')
    self.endpoint = endpoint
    self.ratio = ratio
    self.persistence = persistence
    self.bias_max = bias_max
    self.bias_jerk = bias_jerk
    self.state = 'NORMAL'
    self.since = None
    self.last_t = None
    self.bias = 0.
    self.enter_time = None
    self.exit_time = None

  def update(self, x, enabled):
    dt = .05 if self.last_t is None else x.t - self.last_t
    self.last_t = x.t
    old = self.state
    finite = all(math.isfinite(v) for v in (x.t, x.v0, x.endpoint, x.desired, x.base))
    usable = enabled and x.valid and finite and x.engaged and x.experimental and 0 < dt <= .075 and not x.driver_override
    confirmed = x.should_stop or x.mpc_stop
    suspect = (usable and not confirmed and x.v0 > 1. and 0 <= x.endpoint < self.endpoint
               and x.endpoint < self.ratio * x.v0 and x.desired < -.15 and x.base <= 0.)
    reason = 'disabled_or_invalid'
    if not usable:
      self.state = 'NORMAL'
      self.since = None
      self.bias = 0.
    elif confirmed:
      self.state = 'HOLD' if x.standstill else 'STOP_CONFIRMED'
      self.since = None
      self.bias = 0.
      reason = 'existing_stop_authority'
    elif x.fcw or x.hard_brake:
      self.state = 'NORMAL'
      self.since = None
      self.bias = 0.
      reason = 'existing_hazard_authority'
    else:
      if suspect:
        if self.since is None:
          self.since = x.t
        self.state = 'SLOWING_SUSPECT' if x.t - self.since >= self.persistence - 1e-6 else 'NORMAL'
      else:
        self.since = None
        self.state = 'NORMAL'
      target = self.bias_max if self.state == 'SLOWING_SUSPECT' else 0.
      self.bias += max(-self.bias_jerk * dt, min(self.bias_jerk * dt, target - self.bias))
      reason = 'persistent_model_slowing' if target else 'decay' if self.bias > 1e-9 else 'not_persistent'
    if self.state != old:
      self.exit_time = x.t
      self.enter_time = x.t
    # The offset can only add braking. Existing shouldStop and FCW are untouched.
    after = x.base - self.bias if finite else x.base
    return dict(state=self.state, active=self.bias > 1e-9, reason=reason,
                enter_time=self.enter_time, exit_time=self.exit_time,
                before=x.base, after=after, added_decel=self.bias,
                should_stop_unchanged=x.should_stop, fcw_unchanged=x.fcw,
                lead_present=x.lead_present)
