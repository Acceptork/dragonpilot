from dataclasses import replace
import math
import pytest
from openpilot.selfdrive.controls.lib.recovery_v331 import Inputs, Recovery


def sample(t=0., **kwargs):
  return replace(Inputs(t=t,base=.05,e2e=.05,mpc=1.,cap=.75,cruise_cap=.75,turn_cap=2.,
    v=30.,cluster=32.,cruise=125.,ay=.1,forecast_ay=.2,endpoint=31.,curvature=.0001,pitch=.01),**kwargs)


def armed():
  p=Recovery()
  for i in range(80):
    r=p.update(sample(i*.05));p.observe_final(r['after'])
  assert r['active']
  return p,r


def test_substantial_bounded_recovery_and_ramp():
  p=Recovery();last=.05; changed=0
  for i in range(100):
    r=p.update(sample(i*.05));p.observe_final(r['after'])
    assert .05 <= r['after'] < .75
    assert r['after']-last <= .0150001
    last=r['after'];changed+=r['active']
  assert changed>60 and r['after']>.25
  assert r['after']<sample().mpc


@pytest.mark.parametrize('field,value',[
 ('valid',False),('path_valid',False),('active',False),('blended',False),('driver',True),
 ('stop',True),('fcw',True),('hard_brake',True),('lead',True),('memory',True),('allow',False),
 ('solver_ok',False),('e2e',-.001),('base',-.01),('endpoint',0.),('ay',.51),
 ('forecast_ay',.81),('turn_cap',.6),('curvature',.006),('pitch',.081),('cluster',35.),
 ('cap',0.),('v',1.),('cruise',255.)])
def test_immediate_veto_without_positive_tail(field,value):
  p,_=armed();x=sample(4.,**{field:value});r=p.update(x)
  assert not r['active'] and r['after']==x.base
  r=p.update(sample(4.05))
  assert not r['active']


@pytest.mark.parametrize('field',['t','base','e2e','mpc','cap','cruise_cap','turn_cap','v','cluster','cruise','ay','forecast_ay','endpoint','curvature','pitch'])
@pytest.mark.parametrize('value',[math.nan,math.inf,-math.inf])
def test_nonfinite_never_creates_authority(field,value):
  p,_=armed();r=p.update(sample(4.,**({field:value} if field!='t' else {})) if field!='t' else sample(value))
  assert not r['active'] and r['reason']=='nonfinite'


@pytest.mark.parametrize('t',[3.9,3.95,4.5])
def test_stale_repeated_and_backward_time_reset(t):
  p,_=armed();r=p.update(sample(t));assert not r['active']


def test_curve_exit_separate_state_and_next_curve_cancels():
  p=Recovery()
  for i in range(10):
    r=p.update(sample(i*.05,ay=1.5,turn_cap=.2));p.observe_final(r['after'])
  for i in range(10,45):
    r=p.update(sample(i*.05));p.observe_final(r['after'])
  assert r['state']=='CURVE_EXIT_RECOVERY' and r['active']
  r=p.update(sample(2.25,forecast_ay=1.))
  assert not r['active'] and r['after']==.05


def test_raw_speed_deficit_cannot_substitute_for_cluster():
  p=Recovery()
  for i in range(80):r=p.update(sample(i*.05,v=27.,cluster=125/3.6))
  assert not r['active'] and r['reason']=='cluster_deficit'


def test_memory_unknown_never_times_out_into_recovery():
  p=Recovery()
  for i in range(1200):r=p.update(sample(i*.05,memory=True))
  assert not r['active']
