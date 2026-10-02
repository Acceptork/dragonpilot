"""Synthetic tests for the driver-confirmed all-speed LCA state machine.

These tests exercise DesireHelper only. Honda EPS actuation at low speed is a
separate, unresolved physical capability check.
"""

from enum import IntEnum
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class LaneChangeState(IntEnum):
  off = 0
  preLaneChange = 1
  laneChangeStarting = 2
  laneChangeFinishing = 3


class LaneChangeDirection(IntEnum):
  none = 0
  left = 1
  right = 2


class Desire(IntEnum):
  none = 0
  laneChangeLeft = 1
  laneChangeRight = 2
  keepLeft = 3
  keepRight = 4


log = SimpleNamespace(LaneChangeState=LaneChangeState, LaneChangeDirection=LaneChangeDirection, Desire=Desire)
cereal = ModuleType("cereal")
cereal.log = log
openpilot = ModuleType("openpilot")
common = ModuleType("openpilot.common")
realtime = ModuleType("openpilot.common.realtime")
realtime.DT_MDL = 0.05
source = Path(__file__).resolve().parents[1] / "lib" / "desire_helper.py"
spec = importlib.util.spec_from_file_location("desire_helper_candidate", source)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"cereal": cereal, "openpilot": openpilot, "openpilot.common": common,
                              "openpilot.common.realtime": realtime}):
  spec.loader.exec_module(module)


def car(v=1.0, left=False, right=False, pressed=False, torque=0.0,
        left_blindspot=None, right_blindspot=None):
  # The absence of these attributes represents a missing BSM source.
  state = SimpleNamespace(vEgo=v, leftBlinker=left, rightBlinker=right,
                          steeringPressed=pressed, steeringTorque=torque)
  if left_blindspot is not None:
    state.leftBlindspot = left_blindspot
  if right_blindspot is not None:
    state.rightBlindspot = right_blindspot
  return state


class TestDriverConfirmedLca(unittest.TestCase):
  def helper(self, enabled=20, auto_sec=0):
    return module.DesireHelper(dp_lat_lca_speed=enabled, dp_lat_lca_auto_sec=auto_sec)

  def step(self, helper, state, active=True, left_edge=False, right_edge=False, prob=1.0):
    helper.update(state, active, lane_change_prob=prob,
                  left_edge_detected=left_edge, right_edge_detected=right_edge)
    return helper.lane_change_state

  def test_disabled_setting_stays_off(self):
    helper = self.helper(enabled=0)
    for speed in (0, 0.27, 0.83, 9.2):
      self.assertEqual(self.step(helper, car(v=speed, left=True, pressed=True, torque=1)), LaneChangeState.off)

  def test_no_minimum_speed_but_torque_is_required(self):
    for speed in (0, 1 / 3.6, 3 / 3.6, 9.2):
      with self.subTest(speed=speed):
        helper = self.helper()
        self.assertEqual(self.step(helper, car(v=speed, left=True)), LaneChangeState.preLaneChange)
        for _ in range(40):
          self.assertEqual(self.step(helper, car(v=speed, left=True)), LaneChangeState.preLaneChange)
          self.assertEqual(helper.desire, Desire.none)
        self.assertEqual(self.step(helper, car(v=speed, left=True, pressed=True, torque=1)), LaneChangeState.laneChangeStarting)
        self.assertEqual(helper.desire, Desire.laneChangeLeft)

  def test_opposite_torque_cannot_confirm(self):
    helper = self.helper()
    self.step(helper, car(left=True))
    for _ in range(4):
      self.assertEqual(self.step(helper, car(left=True, pressed=True, torque=-1)), LaneChangeState.preLaneChange)
    self.assertEqual(self.step(helper, car(left=True, pressed=True, torque=1)), LaneChangeState.laneChangeStarting)

  def test_left_and_right_blindspot_values_are_not_read(self):
    for blindspot in (None, False, True):
      with self.subTest(blindspot=blindspot):
        for side in ("left", "right"):
          helper = self.helper()
          self.step(helper, car(**{side: True}))
          attrs = {"left_blindspot": blindspot} if side == "left" else {"right_blindspot": blindspot}
          torque = 1 if side == "left" else -1
          self.assertEqual(self.step(helper, car(pressed=True, torque=torque, **{side: True}, **attrs)),
                           LaneChangeState.laneChangeStarting)

  def test_road_edge_protection_remains(self):
    helper = self.helper()
    self.step(helper, car(left=True))
    for _ in range(3):
      self.assertEqual(self.step(helper, car(left=True, pressed=True, torque=1), left_edge=True),
                       LaneChangeState.preLaneChange)
    self.assertEqual(self.step(helper, car(left=True, pressed=True, torque=1)), LaneChangeState.laneChangeStarting)

  def test_auto_timer_cannot_replace_driver_torque(self):
    helper = self.helper(auto_sec=0.5)
    self.step(helper, car(left=True))
    for _ in range(120):
      self.assertEqual(self.step(helper, car(left=True)), LaneChangeState.preLaneChange)
      self.assertEqual(helper.desire, Desire.none)

  def test_cancel_and_reentry_require_new_blinker_edge(self):
    helper = self.helper()
    self.step(helper, car(left=True))
    self.assertEqual(self.step(helper, car()), LaneChangeState.off)
    self.assertEqual(self.step(helper, car(left=True)), LaneChangeState.preLaneChange)
    self.assertEqual(self.step(helper, car(left=True), active=False), LaneChangeState.off)
    self.assertEqual(self.step(helper, car(left=True, pressed=True, torque=1)), LaneChangeState.off)
    self.step(helper, car())
    self.assertEqual(self.step(helper, car(left=True)), LaneChangeState.preLaneChange)

  def test_lateral_disengagement_clears_active_preparation(self):
    helper = self.helper()
    self.step(helper, car(left=True))
    self.assertEqual(self.step(helper, car(left=True), active=False), LaneChangeState.off)
    self.assertEqual(helper.lane_change_direction, LaneChangeDirection.none)

  def test_original_completion_allows_continuous_blinker_reentry(self):
    helper = self.helper()
    self.step(helper, car(left=True))
    self.step(helper, car(left=True, pressed=True, torque=1))
    for _ in range(12):
      self.step(helper, car(left=True), prob=0.0)
    self.assertEqual(helper.lane_change_state, LaneChangeState.laneChangeFinishing)
    for _ in range(21):
      self.step(helper, car(left=True), prob=0.0)
    self.assertEqual(helper.lane_change_state, LaneChangeState.preLaneChange)
    self.assertEqual(self.step(helper, car(left=True, pressed=True, torque=1)), LaneChangeState.laneChangeStarting)

  def test_timer_limit_preserved(self):
    helper = self.helper()
    self.step(helper, car(left=True))
    self.step(helper, car(left=True, pressed=True, torque=1))
    for _ in range(202):
      self.step(helper, car(left=True), prob=1.0)
    self.assertEqual(helper.lane_change_state, LaneChangeState.off)


if __name__ == "__main__":
  unittest.main()
