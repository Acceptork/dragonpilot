import pytest
from openpilot.selfdrive.controls.lib.ramp_v33 import RampRecovery

def ctx(t, **kw):
  x = dict(t=t, enabled=True, base=.1, e2e=.1, mpc=.5, mode='blended', valid=True,
    active=True, closing=False, stop=False, fcw=False, hard_brake=False, path_valid=True,
    pitch=.05, grade_age=.01, allow_throttle=True, driver_override=False, cruise_gap=8., accel_max=1.)
  return {**x, **kw}

def test_positive_bounded_ramp():
  c = RampRecovery()
  rows = [c.update(**ctx(i * .05)) for i in range(60)]
  assert rows[-1]['after'] == pytest.approx(.2)
  assert all(.1 <= r['after'] <= .2 + 1e-9 for r in rows)
  assert all(b['after'] - a['after'] <= .0050001 for a, b in zip(rows, rows[1:]))

@pytest.mark.parametrize('kw', [dict(enabled=False), dict(closing=True), dict(stop=True), dict(fcw=True),
  dict(hard_brake=True), dict(path_valid=False), dict(valid=False), dict(active=False), dict(mode='acc'),
  dict(e2e=-.01), dict(base=-.1), dict(pitch=None), dict(grade_age=.3), dict(pitch=0.),
  dict(allow_throttle=False), dict(driver_override=True), dict(cruise_gap=1.), dict(mpc=.2)])
def test_veto_immediate_after_activation(kw):
  c = RampRecovery()
  for i in range(60):
    c.update(**ctx(i * .05))
  x = ctx(3., **kw)
  assert c.update(**x)['after'] == x['base']

def test_closing_025_never_blends():
  c = RampRecovery()
  for i in range(200):
    r = c.update(**ctx(i * .05, closing=True, mpc=1.2))
    assert not r['active']
