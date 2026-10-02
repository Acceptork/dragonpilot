from openpilot.selfdrive.controls.lib.experimental_stop import StopIntentTracker


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
