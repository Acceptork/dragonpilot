import pytest

from cereal import log
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import get_T_FOLLOW, get_jerk_factor
from openpilot.selfdrive.controls.lib.longitudinal_throttle import ThrottleGate, get_recovery_policy


@pytest.mark.parametrize(("personality", "enter_kph", "release_kph", "frames", "headway", "jerk_factor"), [
  (log.LongitudinalPersonality.relaxed, 12.0, -1.5, 14, 1.75, 1.25),
  (log.LongitudinalPersonality.standard, 10.0, -1.5, 10, 1.45, 1.0),
  (log.LongitudinalPersonality.aggressive, 7.0, -1.5, 7, 1.25, 0.4),
])
def test_personality_recovery_and_comfort(personality, enter_kph, release_kph, frames, headway, jerk_factor):
  policy = get_recovery_policy(personality)
  assert policy.enter_gap * 3.6 == pytest.approx(enter_kph)
  assert policy.release_gap * 3.6 == pytest.approx(release_kph)
  assert get_T_FOLLOW(personality) == headway
  assert get_jerk_factor(personality) == jerk_factor

  gate = ThrottleGate()
  for _ in range(frames - 1):
    assert not gate.update(False, 15 / 3.6, True, True, 0.05, personality=personality)
  assert gate.update(False, 15 / 3.6, True, True, 0.05, personality=personality)
  assert gate.update(False, (release_kph + 0.1) / 3.6, True, True, 0.05, personality=personality)
  assert not gate.update(False, (release_kph - 0.1) / 3.6, True, True, 0.05, personality=personality)


@pytest.mark.parametrize("personality", [log.LongitudinalPersonality.relaxed,
                                           log.LongitudinalPersonality.standard,
                                           log.LongitudinalPersonality.aggressive])
def test_no_personality_overrides_a_blocked_path(personality):
  gate = ThrottleGate()
  for _ in range(30):
    assert not gate.update(False, 30 / 3.6, False, True, 0.05, personality=personality)
