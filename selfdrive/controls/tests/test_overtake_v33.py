import pytest
from openpilot.selfdrive.controls.lib.overtake_v33 import OvertakePreaccel

def ctx(t, **kw):
  x = dict(t=t, enabled=True, direction='left', torque=False, lat_active=True,
    long_active=True, starting=True, base=.1, mpc=.5, e2e=.1, cap=.8, gap=12.,
    envelope_ok=True, stop=False, fcw=False, hard_brake=False, override=False)
  return {**x, **kw}

@pytest.mark.parametrize('maximum', [.025, .05, .1])
def test_stage1_bounded_sweep(maximum):
  s = OvertakePreaccel(maximum=maximum)
  s.update(**ctx(0.))
  rows = [s.update(**ctx(i * .05, torque=True)) for i in range(1, 30)]
  assert max(r['after'] for r in rows) == pytest.approx(.1 + maximum)
  assert all(r['stage2'].startswith('BLOCKED') for r in rows)

@pytest.mark.parametrize('case', ['blinker', 'torque', 'held', 'inactive_transition'])
def test_no_confirmation_shortcuts(case):
  s = OvertakePreaccel()
  for i in range(40):
    x = ctx(i * .05, torque=case != 'blinker', direction='none' if case == 'torque' else 'left',
            lat_active=i > 10 if case == 'inactive_transition' else True)
    assert not s.update(**x)['active']

@pytest.mark.parametrize('kw', [dict(stop=True), dict(fcw=True), dict(hard_brake=True),
  dict(envelope_ok=False), dict(e2e=-.1), dict(override=True), dict(lat_active=False),
  dict(long_active=False), dict(direction='right'), dict(mpc=.05), dict(cap=.05)])
def test_hazard_immediate_veto(kw):
  s = OvertakePreaccel()
  s.update(**ctx(0.))
  for i in range(1, 20):
    s.update(**ctx(i * .05, torque=True))
  x = ctx(1., torque=True, **kw)
  assert s.update(**x)['after'] == x['base']

def test_one_shot_timeout():
  s = OvertakePreaccel()
  s.update(**ctx(0.))
  for i in range(1, 100):
    r = s.update(**ctx(i * .05, torque=i % 2 == 1))
    if i > 42:
      assert not r['active']
