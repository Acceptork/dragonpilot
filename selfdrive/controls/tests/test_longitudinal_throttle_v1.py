from types import SimpleNamespace

from openpilot.selfdrive.controls.lib.longitudinal_throttle import (
  CLEAR_PATH_TIME, ThrottleGate, grade_allows_override, model_allows_override, path_clear_for_throttle,
)


def radar(*leads):
  inactive = SimpleNamespace(status=False)
  return SimpleNamespace(leadOne=leads[0] if leads else inactive,
                         leadTwo=leads[1] if len(leads) > 1 else inactive)


def lead(distance, relative_speed, speed):
  return SimpleNamespace(status=True, dRel=distance, vRel=relative_speed, vLead=speed)


def test_large_cruise_gap_overrides_low_model_probability_after_half_second():
  gate = ThrottleGate()
  assert path_clear_for_throttle(70 / 3.6, radar(), 1.45, 2.5, 6.0)
  for _ in range(9):
    assert not gate.update(False, 20 / 3.6, True, True, 0.05)
  assert gate.update(False, 20 / 3.6, True, True, 0.05)
  assert gate.clear_time == CLEAR_PATH_TIME


def test_small_cruise_gap_preserves_model_coasting_near_set_speed():
  gate = ThrottleGate()
  for _ in range(20):
    assert not gate.update(False, 5 / 3.6, True, True, 0.05)


def test_cruise_gap_hysteresis_holds_throttle_until_near_set_speed():
  gate = ThrottleGate()
  for _ in range(10):
    gate.update(False, 20 / 3.6, True, True, 0.05)
  assert gate.update(False, 5 / 3.6, True, True, 0.05)
  assert not gate.update(False, 2 / 3.6, True, True, 0.05)


def test_pullaway_requires_a_safe_gap_and_sustained_positive_relative_speed():
  gate = ThrottleGate()
  v_ego = 70 / 3.6
  assert not path_clear_for_throttle(v_ego, radar(lead(25, 1.0, v_ego + 1)), 1.45, 2.5, 6.0)
  assert not path_clear_for_throttle(v_ego, radar(lead(50, -0.1, v_ego - 0.1)), 1.45, 2.5, 6.0)
  clear = path_clear_for_throttle(v_ego, radar(lead(50, 1.0, v_ego + 1)), 1.45, 2.5, 6.0)
  assert clear
  for _ in range(10):
    allowed = gate.update(False, 20 / 3.6, clear, True, 0.05, lead_present=True)
  assert allowed


def test_lead_disappearance_does_not_immediately_override_model():
  gate = ThrottleGate()
  for _ in range(9):
    assert not gate.update(False, 20 / 3.6, True, True, 0.05, lead_present=True)
  assert not gate.update(False, 20 / 3.6, True, True, 0.05, lead_present=False)
  assert gate.clear_time == 0.05


def test_disengagement_and_deceleration_reset_clear_path_timer():
  gate = ThrottleGate()
  for _ in range(9):
    gate.update(False, 15 / 3.6, True, True, 0.05)
  assert not gate.update(False, 15 / 3.6, True, False, 0.05)
  assert gate.clear_time == 0.0
  assert not gate.update(False, 0.0, True, True, 0.05)


def test_model_permission_still_passes_through():
  assert ThrottleGate().update(True, 0.0, False, False, 0.05)


def test_model_requested_deceleration_and_stop_block_override():
  assert model_allows_override(0.0, False, False)
  assert not model_allows_override(-0.2, False, False)
  assert not model_allows_override(float('nan'), False, False)
  assert not model_allows_override(0.0, True, False)
  assert not model_allows_override(0.0, False, True)


def test_strong_grade_keeps_original_model_coast_gate():
  assert grade_allows_override([0.0, 0.03, 0.0])
  assert grade_allows_override([0.0, -0.03, 0.0])
  assert not grade_allows_override([0.0, 0.1, 0.0])
  assert not grade_allows_override([0.0, -0.1, 0.0])
  assert not grade_allows_override([0.0, float('nan'), 0.0])
