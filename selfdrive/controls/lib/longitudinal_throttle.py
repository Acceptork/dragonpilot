"""Conservative override for model based throttle suppression in ACC mode."""

from dataclasses import dataclass
import math
from cereal import log


CRUISE_GAP_FOR_THROTTLE = 10.0 / 3.6  # m/s
CRUISE_GAP_RELEASE = 2.5 / 3.6  # m/s; avoid repeated coast/accel around 10 km/h
PULLAWAY_MIN_VREL = 0.5  # m/s
LEAD_DISTANCE_MARGIN = 2.0  # m
CLEAR_PATH_TIME = 0.5  # s; also protects against a one frame lead dropout
MODEL_DECEL_THRESHOLD = -0.1  # m/s²; keep meaningful model-requested deceleration
MAX_OVERRIDE_PITCH = 0.05  # rad; leave strong-grade coasting to the original planner


@dataclass(frozen=True)
class RecoveryPolicy:
  enter_gap: float
  release_gap: float
  clear_path_time: float


RECOVERY_POLICIES = {
  # Once safely enabled, leave the final cruise taper to MPC. Re-applying the
  # model coast cap near set speed produces an avoidable coast/recover cycle.
  # A >1.5 km/h overshoot returns to model coasting as a conservative backstop.
  log.LongitudinalPersonality.relaxed: RecoveryPolicy(12.0 / 3.6, -1.5 / 3.6, 0.7),
  log.LongitudinalPersonality.standard: RecoveryPolicy(CRUISE_GAP_FOR_THROTTLE, -1.5 / 3.6, CLEAR_PATH_TIME),
  log.LongitudinalPersonality.aggressive: RecoveryPolicy(7.0 / 3.6, -1.5 / 3.6, 0.35),
}


def get_recovery_policy(personality):
  # Cap'n Proto enum readers compare equal to these values but hash differently.
  for key, policy in RECOVERY_POLICIES.items():
    if personality == key:
      return policy
  raise NotImplementedError("Longitudinal personality not supported")


def model_allows_override(desired_accel, should_stop, hard_brake_predicted):
  return (math.isfinite(desired_accel) and desired_accel >= MODEL_DECEL_THRESHOLD and
          not should_stop and not hard_brake_predicted)


def grade_allows_override(orientation_ned):
  return len(orientation_ned) != 3 or (math.isfinite(orientation_ned[1]) and abs(orientation_ned[1]) <= MAX_OVERRIDE_PITCH)


def lead_desired_distance(v_ego, v_lead, t_follow, comfort_brake, stop_distance):
  return max(stop_distance, v_ego * t_follow + stop_distance +
             (v_ego ** 2 - max(0.0, v_lead) ** 2) / (2.0 * comfort_brake))


def path_clear_for_throttle(v_ego, radar_state, t_follow, comfort_brake, stop_distance):
  """Only override the model when every observed lead is pulling away beyond the desired gap."""
  for lead in (radar_state.leadOne, radar_state.leadTwo):
    if not lead.status:
      continue
    desired_gap = lead_desired_distance(v_ego, lead.vLead, t_follow, comfort_brake, stop_distance)
    if lead.vRel < PULLAWAY_MIN_VREL or lead.dRel < desired_gap + LEAD_DISTANCE_MARGIN:
      return False
  return True


@dataclass
class ThrottleGate:
  clear_time: float = 0.0
  last_lead_present: bool = False
  override_active: bool = False

  def update(self, model_allows, cruise_gap, path_clear, engaged, dt, lead_present=False,
             personality=log.LongitudinalPersonality.standard):
    policy = get_recovery_policy(personality)
    if self.last_lead_present and not lead_present:
      self.clear_time = 0.0
      self.override_active = False
    self.last_lead_present = lead_present
    speed_gap_sufficient = (cruise_gap >= policy.enter_gap or
                            (self.override_active and cruise_gap > policy.release_gap))
    eligible = engaged and path_clear and speed_gap_sufficient
    self.clear_time = min(policy.clear_path_time, self.clear_time + dt) if eligible else 0.0
    if self.clear_time >= policy.clear_path_time - 1e-9:
      self.clear_time = policy.clear_path_time
    self.override_active = self.clear_time >= policy.clear_path_time
    return model_allows or self.override_active
