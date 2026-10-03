"""Stage 1 preference inside existing MPC/lead envelope. Stage 2 has no provider."""
import math


class OvertakePreaccel:
  def __init__(self, maximum=.05, slew=.1):
    if not 0 < maximum <= .1 or not 0 < slew <= .2:
      raise ValueError('outside sweep envelope')
    self.maximum, self.slew = maximum, slew
    self.last_direction = 'none'
    self.last_torque = self.last_active = False
    self.epoch = 0
    self.confirmation = None
    self.consumed = False
    self.last_t = None
    self.preference = 0.
    self.enter_time = self.exit_time = None

  def update(self, *, t, enabled, direction, torque, lat_active, long_active, starting,
             base, mpc, e2e, cap, gap, envelope_ok, stop, fcw, hard_brake, override):
    dt = .05 if self.last_t is None else t - self.last_t
    changed = direction != self.last_direction
    active_edge = lat_active != self.last_active
    fresh = torque and not self.last_torque
    self.last_t, self.last_direction, self.last_torque, self.last_active = t, direction, torque, lat_active
    if active_edge:
      self.epoch += 1
    valid = all(math.isfinite(x) for x in (t, base, mpc, e2e, cap, gap)) and 0 < dt <= .075
    invalidate = not enabled or changed or active_edge or direction == 'none' or not lat_active or not long_active or override
    if invalidate:
      self.confirmation = None
      self.consumed = False
      self.preference = 0.
    elif fresh and not self.consumed:
      self.confirmation = dict(direction=direction, epoch=self.epoch, timestamp=t, consumed=True)
      self.consumed = True
    token_valid = self.confirmation is not None and t - self.confirmation['timestamp'] <= 2.
    eligible = (valid and enabled and not invalidate and token_valid and starting and gap > 10 / 3.6
      and envelope_ok and not stop and not fcw and not hard_brake and not override
      and e2e >= 0 and base >= 0 and mpc > base and cap > base)
    if eligible:
      if not self.preference:
        self.enter_time = t
      self.preference = min(self.maximum, self.preference + self.slew * dt)
      # A preference between baseline and MPC, never a relaxation of the MPC solution.
      after = min(cap, mpc, base + min(self.preference, .25 * (mpc - base)))
      reason = 'confirmed_stage1_inside_existing_mpc_envelope'
    else:
      if self.preference:
        self.exit_time = t
      self.preference = 0.
      after = base
      reason = 'confirmation_or_safety_envelope_veto'
    return dict(active=after > base, before=base, after=after, reason=reason,
      stage='STAGE1' if after > base else 'IDLE', stage2='BLOCKED_NO_VALIDATED_PATH_EXIT_PROVIDER',
      confirmation=self.confirmation, preference=self.preference, enter_time=self.enter_time, exit_time=self.exit_time)
