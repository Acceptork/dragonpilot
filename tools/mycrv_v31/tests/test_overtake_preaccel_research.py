"""Offline intent/envelope checks; no planner or CAN command is changed."""

from dataclasses import replace
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from overtake_preaccel_research import OvertakeIntentResearch, Snapshot, Stage  # noqa: E402


BASE = Snapshot(
  blinker="none", steering_pressed=False, steering_torque=0.,
  lane_change_state="off", long_active=True, lat_active=True,
  v_ego=80 / 3.6, v_cruise=124 / 3.6, a_target=0.1, existing_accel_max=0.8,
  lead_status=True, d_rel=80., v_rel=5 / 3.6, v_lead=85 / 3.6, lead_model_prob=0.95,
)


def frame(**values):
  return replace(BASE, **values)


def confirm(research, **values):
  common = {"blinker": "left", **values}
  armed = research.update(frame(**common, lane_change_state="preLaneChange"))
  assert armed.stage == Stage.ARMED
  research.update(frame(**common, lane_change_state="preLaneChange", steering_pressed=True, steering_torque=1.))
  return research.update(frame(**common, lane_change_state="laneChangeStarting",
                               steering_pressed=True, steering_torque=1.))


class TestOvertakeResearch(unittest.TestCase):
  def test_80_to_124_with_lead_85_confirmed_has_only_preview(self):
    research = OvertakeIntentResearch("standard")
    out = confirm(research)
    self.assertEqual(out.stage, Stage.ORIGINAL_LEAD_MARGIN)
    self.assertGreater(out.original_lead_margin, 0)
    self.assertGreater(out.preview_additional_accel, 0)
    self.assertLessEqual(out.preview_additional_accel, 0.10)
    self.assertEqual(out.reason, "preview_only_mpc_not_overridden")

  def test_very_close_original_lead_forbids_preview(self):
    research = OvertakeIntentResearch()
    out = confirm(research, d_rel=25.)
    self.assertEqual(out.stage, Stage.CONFIRMED_WAIT)
    self.assertEqual(out.preview_additional_accel, 0.)
    self.assertLess(out.original_lead_margin, 0.)

  def test_archived_segment_20_closing_lead_forbids_preview(self):
    # Approximate synchronized snapshot at the recorded model transition.
    # The source messages are not stamped at precisely the same instant, so
    # this is an input-point check, not a process replay or outcome claim.
    v_ego = 74.6 / 3.6
    v_rel = -3.59
    research = OvertakeIntentResearch()
    out = confirm(research, v_ego=v_ego, v_cruise=100 / 3.6,
                  d_rel=78.4, v_rel=v_rel, v_lead=v_ego + v_rel,
                  lead_model_prob=0.63)
    self.assertEqual(out.stage, Stage.CONFIRMED_WAIT)
    self.assertEqual(out.preview_additional_accel, 0.)
    self.assertLess(out.original_lead_margin, 0.)

  def test_blinker_without_torque_cannot_confirm(self):
    research = OvertakeIntentResearch()
    research.update(frame(blinker="left", lane_change_state="preLaneChange"))
    for _ in range(8):
      out = research.update(frame(blinker="left", lane_change_state="laneChangeStarting"))
      self.assertEqual(out.preview_additional_accel, 0.)
      self.assertIsNone(out.confirmed_at_frame)

  def test_torque_without_blinker_cannot_confirm(self):
    research = OvertakeIntentResearch()
    for _ in range(8):
      out = research.update(frame(steering_pressed=True, steering_torque=1.,
                                  lane_change_state="laneChangeStarting"))
      self.assertEqual(out.stage, Stage.OFF)
      self.assertEqual(out.preview_additional_accel, 0.)

  def test_cutin_motorcycle_or_brake_cancels(self):
    for hazard in ({"fresh_cutin": True}, {"motorcycle_reported": True},
                   {"driver_brake": True}, {"should_stop": True},
                   {"hard_brake_predicted": True}, {"fcw": True},
                   {"a_target": -0.1}):
      with self.subTest(hazard=hazard):
        research = OvertakeIntentResearch()
        self.assertGreater(confirm(research).preview_additional_accel, 0.)
        out = research.update(frame(blinker="left", lane_change_state="laneChangeStarting",
                                    steering_pressed=True, steering_torque=1., **hazard))
        self.assertEqual(out.stage, Stage.OFF)
        self.assertEqual(out.preview_additional_accel, 0.)
        out = research.update(frame(blinker="left", lane_change_state="laneChangeStarting",
                                    steering_pressed=True, steering_torque=1.))
        self.assertEqual(out.preview_additional_accel, 0.)

  def test_path_clear_requires_external_proof_and_preview_slews(self):
    research = OvertakeIntentResearch()
    confirm(research)
    lost = research.update(frame(blinker="left", lane_change_state="laneChangeStarting",
                                 lead_status=False, steering_pressed=True, steering_torque=1.))
    self.assertEqual(lost.stage, Stage.CONFIRMED_WAIT)
    self.assertEqual(lost.preview_additional_accel, 0.)
    values = []
    for _ in range(8):
      out = research.update(frame(blinker="left", lane_change_state="laneChangeFinishing",
                                  lead_status=False, path_clear_verified=True))
      self.assertEqual(out.stage, Stage.PATH_CLEAR_VERIFIED)
      values.append(out.preview_additional_accel)
    self.assertTrue(all(0 <= b - a <= 0.0200001 for a, b in zip([0.] + values[:-1], values)))
    self.assertLessEqual(values[-1], 0.20)

  def test_small_cruise_gap_no_extra_preview(self):
    research = OvertakeIntentResearch()
    out = confirm(research, v_cruise=82 / 3.6)
    self.assertEqual(out.stage, Stage.CONFIRMED_WAIT)
    self.assertEqual(out.preview_additional_accel, 0.)

  def test_held_torque_from_before_blinker_not_fresh(self):
    research = OvertakeIntentResearch()
    research.update(frame(steering_pressed=True, steering_torque=1.))
    research.update(frame(blinker="left", lane_change_state="preLaneChange",
                          steering_pressed=True, steering_torque=1.))
    out = research.update(frame(blinker="left", lane_change_state="laneChangeStarting",
                                steering_pressed=True, steering_torque=1.))
    self.assertEqual(out.preview_additional_accel, 0.)
    self.assertIsNone(out.confirmed_at_frame)

  def test_closing_or_unreliable_lead_blocks_preview(self):
    for values in ({"v_rel": -1.0, "v_lead": BASE.v_ego - 1.0},
                   {"lead_model_prob": 0.1}, {"d_rel": float("nan")},
                   {"lead_status": False}):
      with self.subTest(values=values):
        research = OvertakeIntentResearch()
        out = confirm(research, **values)
        self.assertEqual(out.preview_additional_accel, 0.)

  def test_personality_changes_only_preview_not_safety_margin(self):
    results = []
    for personality in ("relaxed", "standard", "aggressive"):
      research = OvertakeIntentResearch(personality)
      confirm(research)
      for _ in range(20):
        out = research.update(frame(blinker="left", lane_change_state="laneChangeStarting",
                                    steering_pressed=True, steering_torque=1.))
      results.append(out)
    self.assertEqual([r.original_lead_margin for r in results], [results[0].original_lead_margin] * 3)
    self.assertEqual([r.stage for r in results], [Stage.ORIGINAL_LEAD_MARGIN] * 3)
    self.assertEqual([r.preview_additional_accel for r in results], [0.05, 0.10, 0.15])


if __name__ == "__main__":
  unittest.main()
