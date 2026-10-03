from dataclasses import replace
import math
import pytest
from openpilot.selfdrive.controls.lib.early_stop_v33 import EarlyStop, Inputs


def sample(t, **kw):
  return replace(Inputs(t, 8., 1., -.3, -.3, True, True, True), **kw)


def test_persistence_bounded_and_no_hold():
  s = EarlyStop()
  rows = [s.update(sample(i * .05), True) for i in range(80)]
  assert all(r['after'] <= r['before'] for r in rows)
  assert all(r['added_decel'] == 0 for r in rows[:10])
  assert rows[-1]['state'] == 'SLOWING_SUSPECT'
  assert rows[-1]['added_decel'] == pytest.approx(.15)
  assert all(abs(b['added_decel'] - a['added_decel']) <= .00750001 for a, b in zip(rows, rows[1:]))


@pytest.mark.parametrize('kw', [dict(valid=False), dict(experimental=False), dict(engaged=False),
  dict(driver_override=True), dict(fcw=True), dict(hard_brake=True), dict(should_stop=True),
  dict(mpc_stop=True), dict(endpoint=5.), dict(desired=.1), dict(base=.1), dict(v0=0.)])
def test_gate_identity(kw):
  s = EarlyStop()
  for i in range(40):
    x = sample(i * .05, **kw)
    assert s.update(x, True)['after'] == x.base


def test_off_identity_even_after_activation():
  s = EarlyStop()
  for i in range(40):
    s.update(sample(i * .05), True)
  assert s.update(sample(2.), False)['after'] == -.3


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf')])
def test_invalid_resets(bad):
  s = EarlyStop()
  for i in range(40):
    s.update(sample(i * .05), True)
  assert not s.update(sample(2., endpoint=bad), True)['active']


def test_gap_and_clock_reset():
  for t in [5., -1., 1.95]:
    s = EarlyStop()
    for i in range(40):
      s.update(sample(i * .05), True)
    assert not s.update(sample(t), True)['active']


def test_existing_stop_authority_unchanged():
  s = EarlyStop()
  r = s.update(sample(0., should_stop=True, standstill=True), True)
  assert r['state'] == 'HOLD'
  assert r['after'] == r['before']
  assert r['should_stop_unchanged']
