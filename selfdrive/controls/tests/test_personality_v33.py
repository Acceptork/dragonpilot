import pytest
from openpilot.selfdrive.controls.lib.personality_v33 import CruiseRecovery

def ctx(t, name='standard', **kw):
  x = dict(t=t, enabled=True, personality=name, base=.8, raw_mpc=1.5, cruise_cap=.8,
    turn_cap=1.7, physical_cap=2., valid=True, active=True, mode='acc', lead=False,
    stop=False, fcw=False, hard_brake=False, model_accel=.2, override=False,
    allow_throttle=True, gap=20/3.6)
  return {**x, **kw}

def test_response_order():
  curves = {}
  for name in ['relaxed', 'standard', 'aggressive']:
    c = CruiseRecovery()
    curves[name] = [c.update(**ctx(i * .05, name))['after'] for i in range(100)]
  assert sum(curves['relaxed']) < sum(curves['standard']) < sum(curves['aggressive'])
  assert set(curves['standard']) == {.8}

@pytest.mark.parametrize('kw', [dict(enabled=False), dict(valid=False), dict(active=False),
  dict(mode='blended'), dict(lead=True), dict(stop=True), dict(fcw=True), dict(hard_brake=True),
  dict(model_accel=-.01), dict(override=True), dict(allow_throttle=False), dict(base=-2.), dict(gap=0.)])
@pytest.mark.parametrize('name', ['relaxed', 'standard', 'aggressive'])
def test_safety_identity(kw, name):
  c = CruiseRecovery()
  for i in range(50):
    c.update(**ctx(i * .05, name))
  x = ctx(2.5, name, **kw)
  assert c.update(**x)['after'] == x['base']

def test_turn_and_mpc_ceiling():
  c = CruiseRecovery()
  for i in range(100):
    r = c.update(**ctx(i * .05, 'aggressive', turn_cap=.85))
    assert r['after'] <= .85
  r = c.update(**ctx(5., 'aggressive', raw_mpc=.8))
  assert r['after'] == .8
