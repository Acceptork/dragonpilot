"""Offline-only overtake intent and safety-envelope research prototype.

Nothing in production imports this module. Its preview acceleration MUST NOT be
sent to the planner, MPC, controller, or CAN: the available route does not
establish adjacent-lane clearance or validate lead-constrained response.
"""

from dataclasses import dataclass
from enum import Enum
from math import isfinite


DT = 0.05
FOLLOW_TIME = 1.45  # Standard time gap is used for every personality here.
COMFORT_BRAKE = 2.5
STOP_DISTANCE = 6.0
EXTRA_MARGIN = 20.0
MIN_CRUISE_GAP = 5 / 3.6
MAX_TORQUE_CONFIRM_AGE = 3  # 20 Hz model frames
PREVIEW_SLEW_PER_FRAME = 0.02


class Stage(str, Enum):
  OFF = "off"
  ARMED = "armed"
  CONFIRMED_WAIT = "confirmed_wait"
  ORIGINAL_LEAD_MARGIN = "original_lead_margin"
  PATH_CLEAR_VERIFIED = "path_clear_verified"


@dataclass(frozen=True)
class Snapshot:
  blinker: str  # none, left, right
  steering_pressed: bool
  steering_torque: float
  lane_change_state: str  # off, preLaneChange, laneChangeStarting, laneChangeFinishing
  long_active: bool
  lat_active: bool
  v_ego: float
  v_cruise: float
  a_target: float
  existing_accel_max: float
  lead_status: bool
  d_rel: float
  v_rel: float
  v_lead: float
  lead_model_prob: float
  should_stop: bool = False
  driver_brake: bool = False
  hard_brake_predicted: bool = False
  fcw: bool = False
  fresh_cutin: bool = False
  motorcycle_reported: bool = False
  path_clear_verified: bool = False  # No trusted source currently produces this.


@dataclass(frozen=True)
class Preview:
  stage: Stage
  reason: str
  preview_additional_accel: float
  original_lead_margin: float | None
  confirmed_at_frame: int | None


class OvertakeIntentResearch:
  """Tracks a fresh driver torque onset following a new directional blinker.

  The model lane-change state must then reach starting within a few frames.
  This is only an intent hypothesis; it never certifies adjacent-lane safety.
  """

  def __init__(self, personality: str = "standard"):
    if personality not in ("relaxed", "standard", "aggressive"):
      raise ValueError(personality)
    self.personality = personality
    self.frame = 0
    self.last_blinker = "none"
    self.blinker_start_frame = -1
    self.prev_matching_torque = False
    self.torque_onset_frame: int | None = None
    self.confirmed_at_frame: int | None = None
    self.armed = False
    self.preview = 0.0
    self.prev_lane_change_state = "off"

  def _clear(self) -> None:
    self.armed = False
    self.torque_onset_frame = None
    self.confirmed_at_frame = None
    self.preview = 0.0

  @staticmethod
  def _lead_margin(s: Snapshot) -> float | None:
    vals = (s.v_ego, s.v_cruise, s.d_rel, s.v_rel, s.v_lead, s.lead_model_prob)
    if not s.lead_status or not all(isfinite(v) for v in vals):
      return None
    if s.v_ego < 0 or s.d_rel < 0 or s.v_lead < 0 or s.lead_model_prob < 0.5:
      return None
    if abs((s.v_lead - s.v_ego) - s.v_rel) > 2.0:
      return None
    closing_brake_distance = max(0.0, (s.v_ego ** 2 - s.v_lead ** 2) / (2 * COMFORT_BRAKE))
    conservative_distance = FOLLOW_TIME * s.v_ego + STOP_DISTANCE + closing_brake_distance + EXTRA_MARGIN
    return s.d_rel - conservative_distance

  def update(self, s: Snapshot) -> Preview:
    self.frame += 1
    if s.blinker not in ("none", "left", "right"):
      raise ValueError(s.blinker)
    matching_torque = s.steering_pressed and (
      (s.blinker == "left" and s.steering_torque > 0) or
      (s.blinker == "right" and s.steering_torque < 0)
    )
    new_model_start = s.lane_change_state == "laneChangeStarting" and self.prev_lane_change_state != "laneChangeStarting"
    self.prev_lane_change_state = s.lane_change_state
    new_blinker = s.blinker != "none" and s.blinker != self.last_blinker
    if new_blinker:
      self._clear()
      self.armed = True
      self.blinker_start_frame = self.frame
    self.last_blinker = s.blinker

    hazard = (s.should_stop or s.driver_brake or s.hard_brake_predicted or s.fcw or
              s.fresh_cutin or s.motorcycle_reported or s.a_target < 0)
    if s.blinker == "none" or not s.long_active or not s.lat_active or hazard:
      self._clear()
      self.prev_matching_torque = matching_torque
      return Preview(Stage.OFF, "inactive_or_stop_brake_hazard", 0.0, None, None)

    if s.lane_change_state == "off" and self.confirmed_at_frame is not None:
      self._clear()
    if self.armed and matching_torque and not self.prev_matching_torque and self.frame > self.blinker_start_frame:
      self.torque_onset_frame = self.frame
    self.prev_matching_torque = matching_torque

    if (self.armed and self.torque_onset_frame is not None and
        self.frame - self.torque_onset_frame <= MAX_TORQUE_CONFIRM_AGE and
        new_model_start):
      self.confirmed_at_frame = self.frame
      self.armed = False
    if self.confirmed_at_frame is None:
      return Preview(Stage.ARMED if self.armed else Stage.OFF, "await_fresh_torque_and_model_acceptance",
                     0.0, None, None)
    if s.lane_change_state not in ("laneChangeStarting", "laneChangeFinishing"):
      self._clear()
      return Preview(Stage.OFF, "lane_change_not_active", 0.0, None, None)
    if s.v_cruise - s.v_ego < MIN_CRUISE_GAP:
      self.preview = 0.0
      return Preview(Stage.CONFIRMED_WAIT, "small_cruise_gap", 0.0, None, self.confirmed_at_frame)

    # A lost lead is not evidence that the old lane is clear. Stage 2 requires
    # independent, explicit path-clear evidence that this repo cannot provide.
    if not s.lead_status and s.path_clear_verified:
      target = {"relaxed": 0.10, "standard": 0.20, "aggressive": 0.30}[self.personality]
      self.preview = min(target, self.preview + PREVIEW_SLEW_PER_FRAME)
      self.preview = min(self.preview, max(0.0, s.existing_accel_max - s.a_target))
      return Preview(Stage.PATH_CLEAR_VERIFIED, "external_path_clear_required",
                     self.preview, None, self.confirmed_at_frame)
    margin = self._lead_margin(s)
    if margin is None:
      self.preview = 0.0
      return Preview(Stage.CONFIRMED_WAIT, "lead_missing_or_unreliable", 0.0, None, self.confirmed_at_frame)
    if margin <= 0 or s.v_rel < -0.5:
      self.preview = 0.0
      return Preview(Stage.CONFIRMED_WAIT, "original_lead_too_close_or_closing", 0.0, margin, self.confirmed_at_frame)

    target = {"relaxed": 0.05, "standard": 0.10, "aggressive": 0.15}[self.personality]
    self.preview = min(target, self.preview + PREVIEW_SLEW_PER_FRAME)
    self.preview = min(self.preview, max(0.0, s.existing_accel_max - s.a_target))
    return Preview(Stage.ORIGINAL_LEAD_MARGIN, "preview_only_mpc_not_overridden",
                   self.preview, margin, self.confirmed_at_frame)
