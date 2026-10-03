import pytest
from openpilot.selfdrive.controls.lib.restart_v33 import AutoRestart

def ctx(t, displacement=None, **kw):
  d = .5 * t if displacement is None else min(displacement, .5 * t)
  return dict(t=t, enabled=True, active=True, speed=0., base_stop=False,
    lead=dict(d=10. + d, vr=.5 if displacement is None or d < displacement else 0., y=0., prob=.99),
    path_valid=True, fcw=False, hard_brake=False, driver_brake=False, new_closer=False, **kw)

@pytest.mark.parametrize('name', ['aggressive', 'standard', 'relaxed'])
def test_micro_movement_never_releases(name):
  s = AutoRestart()
  for i in range(100):
    assert s.update(**ctx(i * .05, .1, personality=name))['state'] != 'RELEASE_ALLOWED'

def test_personality_only_after_same_safety_gate():
  times = []
  for name in ['aggressive', 'standard', 'relaxed']:
    s = AutoRestart()
    for i in range(100):
      if s.update(**ctx(i * .05, personality=name))['state'] == 'RELEASE_ALLOWED':
        times.append(i * .05)
        break
  assert times[0] < times[1] < times[2]

@pytest.mark.parametrize('field', ['base_stop', 'fcw', 'hard_brake', 'new_closer'])
def test_hazard_after_release_reholds(field):
  s = AutoRestart()
  for i in range(60):
    s.update(**ctx(i * .05))
  x = ctx(3.)
  x[field] = True
  assert s.update(**x)['should_stop']

def test_loss_reassociation_and_off():
  s = AutoRestart()
  for i in range(60):
    s.update(**ctx(i * .05))
  x = ctx(3.)
  x['lead']['d'] = 4.
  assert s.update(**x)['state'] == 'HOLD'
  x['t'] = 3.05
  x['enabled'] = False
  assert not s.update(**x)['should_stop']
