import random
import pytest
from openpilot.selfdrive.controls.lib.restart_v33 import AutoRestart
from openpilot.selfdrive.controls.lib.restart_motion_window_v33 import RestartMotionWindow


def run(seed, speed=.5, noise=.1, stopped_at=None, **extra):
  rng = random.Random(seed)
  state = AutoRestart()
  outputs = []
  for i in range(160):
    t = i * .05
    distance = speed * (min(t, stopped_at) if stopped_at is not None else t)
    vr = speed if stopped_at is None or t < stopped_at else 0.
    inputs = dict(t=t, enabled=True, active=True, speed=0., base_stop=False,
      lead=dict(d=10 + distance + rng.uniform(-noise, noise), vr=vr, y=0., prob=.99),
      path_valid=True, fcw=False, hard_brake=False, driver_brake=False, new_closer=False)
    inputs.update(extra)
    outputs.append(state.update(**inputs))
  return outputs


@pytest.mark.parametrize('seed', range(20))
def test_persistent_motion_with_bounded_distance_noise(seed):
  assert any(r['state'] == 'RELEASE_ALLOWED' for r in run(seed))


@pytest.mark.parametrize('seed', range(20))
def test_ten_cm_then_stop_never_releases(seed):
  assert not any(r['state'] == 'RELEASE_ALLOWED' for r in run(seed, stopped_at=.2))


@pytest.mark.parametrize('seed', range(20))
def test_stationary_with_distance_noise_never_releases(seed):
  assert not any(r['state'] == 'RELEASE_ALLOWED' for r in run(seed, speed=0.))


@pytest.mark.parametrize('field', ['base_stop', 'fcw', 'hard_brake', 'driver_brake', 'new_closer'])
def test_common_veto_wins_over_filtered_motion(field):
  assert not any(r['state'] == 'RELEASE_ALLOWED' for r in run(1, **{field: True}))


def test_positive_velocity_without_distance_progress_is_not_motion():
  window = RestartMotionWindow()
  for i in range(100):
    assert not window.update(i*.05, dict(d=10., vr=.5), True)


def test_dropout_discards_old_motion_evidence():
  window = RestartMotionWindow()
  for i in range(20):
    window.update(i*.05, dict(d=10.+i*.025, vr=.5), True)
  assert not window.update(1., None, False)
  assert not window.update(1.05, dict(d=10.525, vr=.5), True)


def test_excessive_noise_is_not_reliable_motion():
  window = RestartMotionWindow()
  for i in range(100):
    assert not window.update(i*.05, dict(d=10.+i*.025+(.4 if i%2 else -.4), vr=.5), True)
