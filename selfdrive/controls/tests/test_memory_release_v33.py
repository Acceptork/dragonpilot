import pytest
from openpilot.selfdrive.controls.lib.memory_release_v33 import MemoryRelease


def step(f, t, baseline=1., constrained=None, **kw):
  return f.update(t=t, baseline=baseline, constrained=baseline if constrained is None else constrained,
                  enabled=kw.get('enabled', True), authority=kw.get('authority', True),
                  driver_override=kw.get('driver_override', False))


def test_observed_reacquire_jump_is_bounded_and_eventually_recovers():
  f = MemoryRelease()
  step(f, 0., baseline=.764, constrained=-.579)
  row = step(f, .05, baseline=.728)
  assert row['after'] == pytest.approx(-.479) and row['release_active']
  for i in range(2, 20):
    previous = row['after']
    row = step(f, i*.05, baseline=.728)
    assert row['after'] <= previous + .100000001
    assert row['after'] <= .728
  assert row['after'] == .728 and not row['release_active']


def test_more_urgent_braking_is_immediate():
  f = MemoryRelease()
  step(f, 0., constrained=-.5)
  assert step(f, .05, baseline=-2.)['after'] == -2.
  assert step(f, .1, constrained=-3.)['after'] == -3.


@pytest.mark.parametrize('override', ['enabled', 'authority', 'driver_override'])
def test_takeover_and_disable_do_not_retain_release(override):
  f = MemoryRelease()
  step(f, 0., constrained=-1.)
  kw = {override: override == 'driver_override'}
  assert step(f, .05, **kw)['after'] == 1.
  assert step(f, .1)['after'] == 1.


@pytest.mark.parametrize('t', [0., -.1, 1., float('nan')])
def test_bad_time_discards_previous_command(t):
  f = MemoryRelease()
  step(f, 0., constrained=-1.)
  assert step(f, t)['after'] == 1.
  assert not f.pending


def test_no_memory_constraint_leaves_arbitrary_baseline_unchanged():
  f = MemoryRelease()
  for i, value in enumerate([0., 2., -3., 1., 0., 1.8]):
    assert step(f, i*.05, baseline=value)['after'] == value


def test_unknown_cannot_become_positive_through_release_filter():
  f = MemoryRelease()
  step(f, 0., constrained=-1.)
  for i in range(1, 40):
    assert step(f, i*.05, constrained=0.)['after'] <= 0.
