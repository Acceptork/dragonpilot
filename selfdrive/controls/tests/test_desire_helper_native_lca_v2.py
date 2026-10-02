"""Native cereal lane-change candidate checks.

Run in the candidate checkout's own venv after its SCons build. These tests
verify state transitions and do not claim Honda EPS actuation at low speed.
"""

from pathlib import Path
import unittest

from cereal import log, messaging
from openpilot.selfdrive.controls.lib import desire_helper


def state(*, speed=0.6, left=False, right=False, pressed=False, torque=0.,
          left_blindspot=None, right_blindspot=None):
  cs = messaging.new_message("carState").carState
  cs.vEgo = speed
  cs.leftBlinker = left
  cs.rightBlinker = right
  cs.steeringPressed = pressed
  cs.steeringTorque = torque
  if left_blindspot is not None:
    cs.leftBlindspot = left_blindspot
  if right_blindspot is not None:
    cs.rightBlindspot = right_blindspot
  return cs


def step(helper, cs, *, lateral_active=True, left_edge=False, right_edge=False, prob=1.0):
  helper.update(cs, lateral_active=lateral_active, lane_change_prob=prob,
                left_edge_detected=left_edge, right_edge_detected=right_edge)
  return helper.lane_change_state


class TestNativeDriverConfirmedLca(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    root = Path(__file__).resolve().parents[3]
    actual = Path(desire_helper.__file__).resolve()
    assert actual == root / "selfdrive/controls/lib/desire_helper.py", (actual, root)

  def test_one_to_three_kph_requires_directional_torque(self):
    for kph in (1, 3):
      with self.subTest(kph=kph):
        helper = desire_helper.DesireHelper(dp_lat_lca_speed=20)
        self.assertEqual(step(helper, state(speed=kph / 3.6, left=True)), log.LaneChangeState.preLaneChange)
        self.assertEqual(step(helper, state(speed=kph / 3.6, left=True)), log.LaneChangeState.preLaneChange)
        self.assertEqual(step(helper, state(speed=kph / 3.6, left=True, pressed=True, torque=-1.)),
                         log.LaneChangeState.preLaneChange)
        self.assertEqual(step(helper, state(speed=kph / 3.6, left=True, pressed=True, torque=1.)),
                         log.LaneChangeState.laneChangeStarting)
        self.assertEqual(helper.desire, log.Desire.laneChangeLeft)

  def test_blindspot_values_do_not_gate_driver_confirmed_start(self):
    for blindspot in (None, False, True):
      with self.subTest(blindspot=blindspot):
        helper = desire_helper.DesireHelper(dp_lat_lca_speed=20)
        step(helper, state(left=True))
        self.assertEqual(step(helper, state(left=True, pressed=True, torque=1.,
                                            left_blindspot=blindspot)), log.LaneChangeState.laneChangeStarting)

  def test_road_edge_still_blocks(self):
    helper = desire_helper.DesireHelper(dp_lat_lca_speed=20)
    step(helper, state(left=True))
    self.assertEqual(step(helper, state(left=True, pressed=True, torque=1.), left_edge=True),
                     log.LaneChangeState.preLaneChange)
    self.assertEqual(step(helper, state(left=True, pressed=True, torque=1.)),
                     log.LaneChangeState.laneChangeStarting)

  def test_legacy_auto_timer_cannot_bypass_torque(self):
    helper = desire_helper.DesireHelper(dp_lat_lca_speed=20, dp_lat_lca_auto_sec=0.5)
    step(helper, state(left=True))
    for _ in range(100):
      self.assertEqual(step(helper, state(left=True)), log.LaneChangeState.preLaneChange)
      self.assertEqual(helper.desire, log.Desire.none)

  def test_lateral_inactive_blocks_low_speed_entry(self):
    helper = desire_helper.DesireHelper(dp_lat_lca_speed=20)
    self.assertEqual(step(helper, state(speed=1 / 3.6, left=True, pressed=True, torque=1.),
                          lateral_active=False), log.LaneChangeState.off)

  def test_disabled_setting_preserved(self):
    helper = desire_helper.DesireHelper(dp_lat_lca_speed=0)
    self.assertEqual(step(helper, state(speed=10., left=True, pressed=True, torque=1.)),
                     log.LaneChangeState.off)


if __name__ == "__main__":
  unittest.main()
