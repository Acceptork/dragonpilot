import pytest
from openpilot.selfdrive.controls.lib.taper_v33 import StopTaper

def ctx(**kw):
  return dict(speed=.4, base=-.5, pitch=0., grade_fresh=True, stop=True,
    enabled=True, active=True, remaining=4., dt=.05, **kw)

def test_taper_keeps_brake_and_does_not_weaken_baseline():
  s = StopTaper()
  for i in range(40):
    r = s.update(**ctx())
    assert r['after'] <= -.5
  assert r['state'] == 'TAPER'
  assert r['after'] == pytest.approx(-1.2)

def test_no_fake_stop_coordinate():
  s = StopTaper()
  x = ctx()
  x['remaining'] = None
  assert s.update(**x)['state'] == 'BRAKING'

def test_hold_hysteresis_creep_and_rollback():
  s = StopTaper()
  x = ctx()
  x['speed'] = 0.
  for _ in range(30):
    r = s.update(**x)
  assert r['state'] == 'HOLD'
  x['speed'] = .08
  assert s.update(**x)['reason'] == 'creep_guard'
  x['speed'] = -.08
  assert s.update(**x)['reason'] == 'rollback_guard'

@pytest.mark.parametrize('key,value', [('enabled', False), ('active', False), ('stop', False),
  ('pitch', None), ('grade_fresh', False), ('driver_override', True)])
def test_veto_identity(key, value):
  s = StopTaper()
  x = ctx()
  x[key] = value
  assert s.update(**x)['after'] == x['base']

def test_danger_braking_never_weakened():
  s = StopTaper()
  for speed in [2., 1., .4, .2, 0.]:
    x = ctx()
    x.update(speed=speed, danger=True, base=-3.)
    assert s.update(**x)['after'] <= -3.


@pytest.mark.parametrize('veto', ['stop','grade_fresh'])
def test_existing_extra_brake_releases_with_bounded_slew(veto):
  s=StopTaper();x=ctx()
  for _ in range(40):s.update(**x)
  before=s.command
  x[veto]=False;x['base']=.1
  for _ in range(20):
    r=s.update(**x)
    assert r['after']<=x['base']
    assert r['after']-before<=s.jerk*x['dt']+1e-12
    before=r['after']
  assert r['after']==x['base'] and not s.extra_active


def test_no_extra_brake_does_not_smooth_baseline_recovery():
  s=StopTaper();x=ctx();x['stop']=False
  assert s.update(**x)['after']==-.5
  x['base']=.2
  assert s.update(**x)['after']==.2


@pytest.mark.parametrize('field', ['enabled','active','driver_override'])
def test_release_never_delays_driver_or_authority_handoff(field):
  s=StopTaper();x=ctx()
  for _ in range(40):s.update(**x)
  x[field]=True if field=='driver_override' else False
  x['base']=.1
  assert s.update(**x)['after']==.1
  assert not s.extra_active


def test_release_immediately_accepts_stronger_baseline_braking():
  s=StopTaper();x=ctx()
  for _ in range(40):s.update(**x)
  x.update(stop=False,base=-3.)
  assert s.update(**x)['after']==-3.
