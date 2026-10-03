"""Opt-in restart interlock. Releases only existing controller authority."""
import math
from openpilot.selfdrive.controls.lib.restart_motion_window_v33 import RestartMotionWindow


class AutoRestart:
  def __init__(self, persistence=.8, displacement=.3):
    self.motion_window = RestartMotionWindow()
    self.persistence = persistence
    self.displacement = displacement
    self.state = 'IDLE'
    self.previous = None
    self.origin = None
    self.since = None
    self.enter_time = self.exit_time = None

  def update(self, *, t, enabled, active, speed, base_stop, lead, path_valid,
             fcw, hard_brake, driver_brake, new_closer, personality='standard', slowing_intent=False):
    old = self.state
    reliable = (lead is not None and lead.get('prob', 0.) >= .8
      and all(math.isfinite(lead.get(k, float('nan'))) for k in ('d', 'vr', 'y'))
      and 0 < lead['d'] < 50 and abs(lead['y']) < 1.5)
    dt = t - self.previous['t'] if self.previous is not None else None
    continuous = (reliable and self.previous is not None and dt is not None and 0 < dt <= .075
      and abs(lead['d'] - (self.previous['d'] + self.previous['vr'] * dt)) < .5
      and abs(lead['vr'] - self.previous['vr']) < 1.
      and abs(lead['y'] - self.previous['y']) < .3)
    motion = self.motion_window.update(t, lead, continuous)
    self.previous = {**lead, 't': t} if reliable else None
    reason = 'disabled_or_not_holding'
    if not enabled or not active or driver_brake:
      self.motion_window.clear()
      self.state = 'IDLE'
      self.since = self.origin = None
    else:
      if self.state == 'IDLE' and abs(speed) < .05:
        self.state = 'HOLD'
        self.origin = lead['d'] if reliable else None
      if speed > 2.:
        self.state = 'IDLE'
        self.since = self.origin = None
      elif self.state != 'IDLE':
        veto = (base_stop or slowing_intent or fcw or hard_brake or not path_valid or not reliable or new_closer
                or (self.state == 'RELEASE_ALLOWED' and lead['vr'] + speed <= .15))
        if veto or not continuous:
          self.motion_window.clear()
          self.state = 'HOLD'
          self.since = None
          self.origin = lead['d'] if reliable else None
          reason = 'common_safety_gate'
        elif self.state == 'RELEASE_ALLOWED':
          reason = 'existing_controller_release_allowed'
        elif not motion:
          self.state = 'HOLD'
          self.since = None
          self.origin = lead['d']
          reason = 'movement_not_persistent'
        else:
          if self.origin is None:
            self.origin = lead['d']
          displacement = lead['d'] - self.origin
          if displacement <= self.displacement:
            self.since = None
            reason = 'displacement_below_noise_gate'
          else:
            if self.since is None:
              self.since = t
            extra = {'aggressive': 0., 'standard': .2, 'relaxed': .4}.get(personality, .4)
            self.state = 'RELEASE_ALLOWED' if t - self.since >= self.persistence + extra - 1e-6 else 'LEAD_MOVING_PENDING'
            reason = 'shared_gate_then_personality_wait'
    if self.state != old:
      self.enter_time = self.exit_time = t
    hold = enabled and active and self.state in ('HOLD', 'LEAD_MOVING_PENDING')
    return dict(state=self.state, active=bool(hold), should_stop=bool(base_stop or hold),
      reason=reason, enter_time=self.enter_time, exit_time=self.exit_time,
      association='geometry_velocity_continuity_not_raw_lead_index')

