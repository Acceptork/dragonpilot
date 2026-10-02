import pytest
from cereal import log
from openpilot.selfdrive.controls.lib.experimental_stop import StopIntentTracker, get_stop_intent_profile, stop_intent_hold_enabled


@pytest.mark.parametrize(('personality', 'release_time'), [
  (log.LongitudinalPersonality.relaxed, 0.30),
  (log.LongitudinalPersonality.standard, 0.20),
  (log.LongitudinalPersonality.aggressive, 0.15),
])
def test_personality_stop_release_time(personality, release_time):
  assert get_stop_intent_profile(personality).release_time == release_time


def test_stop_intent_starts_immediately_and_releases_after_stable_false():
  tracker = StopIntentTracker()
  assert tracker.update(True, True, 0.05, 0.2)
  for _ in range(3):
    assert tracker.update(False, True, 0.05, 0.2)
  assert not tracker.update(False, True, 0.05, 0.2)


def test_single_false_frame_does_not_release_stop():
  tracker = StopIntentTracker()
  assert tracker.update(True, True, 0.05, 0.2)
  assert tracker.update(False, True, 0.05, 0.2)
  assert tracker.update(True, True, 0.05, 0.2)
  assert tracker.false_time == 0.0


def test_disengage_or_mode_exit_resets_stop_intent():
  tracker = StopIntentTracker()
  assert tracker.update(True, True, 0.05, 0.2)
  assert not tracker.update(False, False, 0.05, 0.2)
  assert not tracker.update(False, True, 0.05, 0.2)


@pytest.mark.parametrize(('mode', 'experimental', 'op_long', 'reset', 'speed', 'expected'), [
  ('blended', True, True, False, 0.1, True),
  ('blended', True, True, False, 2.49, True),
  ('blended', True, True, False, 2.5, False),
  ('acc', True, True, False, 0.1, False),
  ('blended', False, True, False, 0.1, False),
  ('blended', True, False, False, 0.1, False),
  ('blended', True, True, True, 0.1, False),
])
def test_hold_is_confined_to_active_low_speed_experimental_control(mode, experimental, op_long, reset, speed, expected):
  assert stop_intent_hold_enabled(mode, experimental, op_long, reset, speed) is expected
