"""Conservative override for model based throttle suppression in ACC mode."""

from dataclasses import dataclass
import math


CRUISE_GAP_FOR_THROTTLE = 10.0 / 3.6  # m/s
CRUISE_GAP_RELEASE = 2.5 / 3.6  # m/s; avoid repeated coast/accel around 10 km/h
PULLAWAY_MIN_VREL = 0.5  # m/s
LEAD_DISTANCE_MARGIN = 2.0  # m
CLEAR_PATH_TIME = 0.5  # s; also protects against a one frame lead dropout
MODEL_DECEL_THRESHOLD = -0.1  # m/s²; keep meaningful model-requested deceleration
MAX_OVERRIDE_PITCH = 0.05  # rad; leave strong-grade coasting to the original planner


def model_allows_override(desired_accel, should_stop, hard_brake_predicted):
  return (math.isfinite(desired_accel) and desired_accel >= MODEL_DECEL_THRESHOLD and
          not should_stop and not hard_brake_predicted)


def grade_allows_override(orientation_ned):
  return len(orientation_ned) != 3 or (math.isfinite(orientation_ned[1]) and abs(orientation_ned[1]) <= MAX_OVERRIDE_PITCH)


def path_clear_for_throttle(v_ego, radar_state, t_follow, comfort_brake, stop_distance):
  """Only override the model when every observed lead is pulling away beyond the desired gap."""
  for lead in (radar_state.leadOne, radar_state.leadTwo):
    if not lead.status:
      continue
    desired_gap = v_ego * t_follow + stop_distance + (v_ego ** 2 - max(0.0, lead.vLead) ** 2) / (2.0 * comfort_brake)
    if lead.vRel < PULLAWAY_MIN_VREL or lead.dRel < max(stop_distance, desired_gap) + LEAD_DISTANCE_MARGIN:
      return False
  return True


@dataclass
class ThrottleGate:
  clear_time: float = 0.0
  last_lead_present: bool = False
  override_active: bool = False

  def update(self, model_allows, cruise_gap, path_clear, engaged, dt, lead_present=False):
    if self.last_lead_present and not lead_present:
      self.clear_time = 0.0
      self.override_active = False
    self.last_lead_present = lead_present
    speed_gap_sufficient = (cruise_gap >= CRUISE_GAP_FOR_THROTTLE or
                            (self.override_active and cruise_gap > CRUISE_GAP_RELEASE))
    eligible = engaged and path_clear and speed_gap_sufficient
    self.clear_time = min(CLEAR_PATH_TIME, self.clear_time + dt) if eligible else 0.0
    if self.clear_time >= CLEAR_PATH_TIME - 1e-9:
      self.clear_time = CLEAR_PATH_TIME
    self.override_active = self.clear_time >= CLEAR_PATH_TIME
    return model_allows or self.override_active
