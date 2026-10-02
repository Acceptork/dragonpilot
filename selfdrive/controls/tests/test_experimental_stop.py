import pytest
from cereal import log
from openpilot.selfdrive.controls.lib.experimental_stop import StopIntentTracker, get_stop_intent_profile


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
