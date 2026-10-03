"""Free-cruise positive response only; no changes to following or braking weights."""
import math


class CruiseRecovery:
  def __init__(self):
    self.previous_t = None
    self.previous_output = 0.
    self.since = None
    self.headroom = 0.
    self.enter_time = self.exit_time = None
    self.previous_personality = None

  def update(self, *, t, enabled, personality, base, raw_mpc, cruise_cap, turn_cap,
             physical_cap, valid, active, mode, lead, stop, fcw, hard_brake,
             model_accel, override, allow_throttle, gap):
    dt = .05 if self.previous_t is None else t - self.previous_t
    self.previous_t = t
    finite = all(math.isfinite(v) for v in (t, base, raw_mpc, cruise_cap, turn_cap, physical_cap, model_accel, gap))
    eligible = (enabled and valid and active and finite and 0 < dt <= .075 and mode == 'acc'
      and not lead and not stop and not fcw and not hard_brake and model_accel >= 0.
      and not override and allow_throttle and gap > 2. / 3.6 and base > 0. and raw_mpc > 0.)
    if not eligible:
      if self.since is not None:
        self.exit_time = t
      self.since = None
      self.headroom = 0.
      after, reason = base, 'common_safety_or_mode_veto'
    else:
      if self.since is None or personality != self.previous_personality:
        self.since = self.enter_time = t
        self.headroom = 0.
      if personality == 'relaxed':
        # Rate-limit only a positive increase; a smaller baseline target wins immediately.
        after = min(base, max(0., self.previous_output) + .15 * dt)
        reason = 'relaxed_positive_response'
      elif personality == 'aggressive' and t - self.since >= .7:
        # Cruise-only headroom; neither turn nor physical cap is relaxed. MPC remains ceiling.
        self.headroom = min(.15, self.headroom + .15 * dt)
        approach = max(0., (gap - 2. / 3.6) / 5.)
        ceiling = min(raw_mpc, cruise_cap + min(self.headroom, approach), turn_cap, physical_cap)
        after = max(base, min(ceiling, base + self.headroom))
        reason = 'aggressive_free_cruise_headroom'
      else:
        after, reason = base, 'standard_or_persistence_pending'
    self.previous_output = after
    self.previous_personality = personality
    return dict(active=after != base, before=base, after=after, reason=reason,
      enter_time=self.enter_time, exit_time=self.exit_time, headroom=self.headroom,
      personality=personality)
