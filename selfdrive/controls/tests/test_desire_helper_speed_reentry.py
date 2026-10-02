"""Synthetic lane-change entry checks without native cereal dependencies."""

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
constants = ModuleType("openpilot.common.constants")
constants.CV = SimpleNamespace(MPH_TO_MS=0.44704)
realtime = ModuleType("openpilot.common.realtime")
realtime.DT_MDL = 0.05
source = Path(__file__).resolve().parents[1] / "lib" / "desire_helper.py"
spec = importlib.util.spec_from_file_location("desire_helper_candidate", source)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"cereal": cereal, "openpilot": openpilot, "openpilot.common": common,
                              "openpilot.common.constants": constants, "openpilot.common.realtime": realtime}):
  spec.loader.exec_module(module)


def car(v=8.0, left=False, right=False, pressed=False, torque=0.0, left_blindspot=False):
  return SimpleNamespace(vEgo=v, leftBlinker=left, rightBlinker=right,
                         steeringPressed=pressed, steeringTorque=torque,
                         leftBlindspot=left_blindspot, rightBlindspot=False)


class TestSpeedGateReentry(unittest.TestCase):
  def update(self, helper, state, active=True):
    helper.update(state, active, lane_change_prob=1.0, left_edge_detected=False, right_edge_detected=False)

  def test_event_015_requires_fresh_matching_torque_after_speed_gate(self):
    helper = module.DesireHelper(dp_lat_lca_speed=20, dp_lat_lca_auto_sec=0)
    self.update(helper, car(v=8.0, left=True))
    self.assertEqual(helper.lane_change_state, LaneChangeState.off)
    self.update(helper, car(v=9.2, left=True))
    self.assertEqual(helper.lane_change_state, LaneChangeState.off)
    self.update(helper, car(v=9.9, left=True, pressed=True, torque=1.0))
    self.assertEqual(helper.lane_change_state, LaneChangeState.preLaneChange)
    self.update(helper, car(v=9.9, left=True, pressed=True, torque=1.0))
    self.assertEqual(helper.lane_change_state, LaneChangeState.laneChangeStarting)

  def test_held_torque_from_below_gate_does_not_trigger_on_speed_alone(self):
    helper = module.DesireHelper(dp_lat_lca_speed=20, dp_lat_lca_auto_sec=0)
    self.update(helper, car(v=8.0, left=True, pressed=True, torque=1.0))
    self.update(helper, car(v=9.2, left=True, pressed=True, torque=1.0))
    self.assertEqual(helper.lane_change_state, LaneChangeState.off)
    self.update(helper, car(v=9.2, left=True))
    self.update(helper, car(v=9.2, left=True, pressed=True, torque=1.0))
    self.assertEqual(helper.lane_change_state, LaneChangeState.preLaneChange)

  def test_wrong_torque_and_blindspot_still_block(self):
    helper = module.DesireHelper(dp_lat_lca_speed=20, dp_lat_lca_auto_sec=0)
    self.update(helper, car(v=8.0, left=True))
    self.update(helper, car(v=9.2, left=True, pressed=True, torque=-1.0))
    self.assertEqual(helper.lane_change_state, LaneChangeState.off)
    self.update(helper, car(v=9.2, left=True, pressed=True, torque=1.0, left_blindspot=True))
    self.assertEqual(helper.lane_change_state, LaneChangeState.preLaneChange)
    self.update(helper, car(v=9.2, left=True, pressed=True, torque=1.0, left_blindspot=True))
    self.assertEqual(helper.lane_change_state, LaneChangeState.preLaneChange)

  def test_lateral_disengagement_clears_pending_blinker(self):
    helper = module.DesireHelper(dp_lat_lca_speed=20, dp_lat_lca_auto_sec=0)
    self.update(helper, car(v=8.0, left=True))
    self.update(helper, car(v=9.2, left=True), active=False)
    self.update(helper, car(v=9.2, left=True, pressed=True, torque=1.0))
    self.assertEqual(helper.lane_change_state, LaneChangeState.off)

  def test_normal_high_speed_blinker_still_enters_pre(self):
    helper = module.DesireHelper(dp_lat_lca_speed=20, dp_lat_lca_auto_sec=0)
    self.update(helper, car(v=9.2, left=True))
    self.assertEqual(helper.lane_change_state, LaneChangeState.preLaneChange)

  def test_auto_timer_does_not_start_pending_lane_change_at_speed_crossing(self):
    helper = module.DesireHelper(dp_lat_lca_speed=20, dp_lat_lca_auto_sec=1.0)
    self.update(helper, car(v=8.0, left=True))
    for _ in range(30):
      self.update(helper, car(v=9.2, left=True))
    self.assertEqual(helper.lane_change_state, LaneChangeState.off)


if __name__ == "__main__":
  unittest.main()
