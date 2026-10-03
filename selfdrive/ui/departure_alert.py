"""Read-only departure cue state machine. No control outputs or engagement dependency."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Observation:
  t: float
  onroad: bool
  valid: bool
  gear: str
  speed: float
  gas: bool
  lead: dict | None
  endpoint: float
  desired_accel: float
  model_stop: bool = False
  hazard: bool = False
  closer_obstacle: bool = False


class DepartureAlerts:
  def __init__(self):
    self.last_t = None
    self.cooldown_until = -math.inf
    self.latched = False
    self.moving_since = None
    self.reset_tracking()

  def reset_tracking(self):
    self.lead_anchor = None
    self.lead_previous = None
    self.lead_still_since = None
    self.lead_moving_since = None
    self.slow_since = None
    self.slow_armed = False
    self.proceed_since = None

  def update(self, x: Observation, lead_enabled=True, signal_enabled=True):
    finite = all(math.isfinite(v) for v in [x.t, x.speed, x.endpoint, x.desired_accel])
    discontinuity = self.last_t is not None and not 0 < x.t-self.last_t <= .3
    self.last_t = x.t
    if not finite or discontinuity or not x.valid or not x.onroad or x.gear != 'drive':
      self.reset_tracking()
      self.moving_since = None
      # Data loss does not re-arm a cue already issued at the same stop.
      return None
    if x.speed >= .8:
      self.moving_since = x.t if self.moving_since is None else self.moving_since
      if x.t - self.moving_since >= 2.:
        self.latched = False
      self.reset_tracking()
      return None
    self.moving_since = None
    if x.speed > .2 or x.gas or x.hazard or x.closer_obstacle:
      self.reset_tracking()
      return None
    if self.latched or x.t < self.cooldown_until:
      return None
    kind = None
    lead = x.lead
    reliable = lead is not None and all(k in lead and math.isfinite(lead[k]) for k in ['d','vr','y','prob'])
    reliable = reliable and .8 <= lead['prob'] <= 1. and 2. <= lead['d'] <= 45. and abs(lead['y']) < 1.
    if reliable and lead_enabled:
      self.slow_since, self.slow_armed, self.proceed_since = None, False, None
      previous = self.lead_previous
      consistent = previous is not None and abs(lead['d'] - previous['d']) <= .6 and abs(lead['y'] - previous['y']) < .4
      if not consistent:
        self.lead_anchor = None
        self.lead_still_since = None
        self.lead_moving_since = None
      absolute_speed = lead['vr'] + x.speed
      if abs(absolute_speed) <= .2:
        self.lead_still_since = x.t if self.lead_still_since is None else self.lead_still_since
        if x.t - self.lead_still_since >= 1.5:
          self.lead_anchor = dict(lead)
        self.lead_moving_since = None
      elif self.lead_anchor is not None and .3 < absolute_speed < 8. and consistent and lead['d'] > previous['d']:
        self.lead_moving_since = x.t if self.lead_moving_since is None else self.lead_moving_since
        if x.t-self.lead_moving_since >= .8 and lead['d']-self.lead_anchor['d'] >= .7:
          kind = 'lead_departure'
      else:
        self.lead_moving_since = None
      self.lead_previous = dict(lead)
    else:
      had_lead = self.lead_previous is not None
      self.lead_previous = self.lead_anchor = None
      self.lead_still_since = self.lead_moving_since = None
      # A dropped/unreliable lead must not become a no-lead permission cue.
      if lead is not None or had_lead or not signal_enabled:
        self.slow_since, self.slow_armed, self.proceed_since = None, False, None
        return None
      slow = x.endpoint < 1. and (x.desired_accel <= 0. or x.model_stop)
      proceed = x.endpoint > 3. and x.desired_accel > .15 and not x.model_stop
      if slow:
        self.slow_since = x.t if self.slow_since is None else self.slow_since
        self.slow_armed = self.slow_armed or x.t-self.slow_since >= 3.
        self.proceed_since = None
      elif proceed and self.slow_armed:
        self.proceed_since = x.t if self.proceed_since is None else self.proceed_since
        if x.t-self.proceed_since >= 1.5:
          kind = 'possible_proceed'
      else:
        self.slow_since, self.slow_armed, self.proceed_since = None, False, None
    if kind is None:
      return None
    self.latched = True
    self.cooldown_until = x.t + 20.
    self.reset_tracking()
    return dict(kind=kind, text='前車已起步' if kind == 'lead_departure' else '前方可能已可通行',
                issued_at=x.t, expires_at=x.t+3., sound='prompt', control_effect='NONE')
