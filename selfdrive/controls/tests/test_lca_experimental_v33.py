from types import SimpleNamespace
import pytest
from openpilot.selfdrive.controls.lib.desire_helper_experimental_v33 import DesireHelper,LaneChangeState

def cs(speed=10,blink=True,torque=0,bsm=None):
  c=SimpleNamespace(vEgo=speed/3.6,leftBlinker=blink,rightBlinker=False,steeringPressed=bool(torque),steeringTorque=torque)
  if bsm is not None:c.leftBlindspot=bsm;c.rightBlindspot=bsm
  return c

@pytest.mark.parametrize('speed',[0,1,3,5,10,20])
@pytest.mark.parametrize('bsm',[None,False,True])
def test_fresh_confirmation_without_speed_or_bsm_gate(speed,bsm):
  h=DesireHelper();h.update(cs(speed,bsm=bsm),True,1.,False,False)
  assert h.lane_change_state==LaneChangeState.preLaneChange
  h.update(cs(speed,torque=1,bsm=bsm),True,1.,False,False)
  assert h.lane_change_state==LaneChangeState.laneChangeStarting
  assert h.token.consumed and h.token.epoch==h.epoch

@pytest.mark.parametrize('case',['only_blink','only_torque','opposite','held_before','held_inactive','edge'])
def test_refusals(case):
  h=DesireHelper()
  if case=='held_before':h.update(cs(blink=False,torque=1),True,1.,False,False)
  h.update(cs(torque=1 if case in ['held_before','held_inactive'] else 0),case!='held_inactive',1.,False,False)
  for _ in range(20):
    h.update(cs(blink=case!='only_torque',torque=0 if case=='only_blink' else -1 if case=='opposite' else 1),True,1.,case=='edge',False)
    assert h.lane_change_state!=LaneChangeState.laneChangeStarting

@pytest.mark.parametrize('case',['cancel','off','opposite_blink','inactive','timeout'])
def test_invalidation(case):
  h=DesireHelper();h.update(cs(),True,1.,False,False);h.update(cs(torque=1),True,1.,False,False)
  c=cs(torque=1)
  if case=='off':c.leftBlinker=False
  if case=='opposite_blink':c.leftBlinker=False;c.rightBlinker=True
  if case=='timeout':h.lane_change_timer=11
  h.update(c,case!='inactive',1.,False,False,cancel=case=='cancel')
  assert h.token is None
  assert h.desire == 0

def test_completion_requires_release_then_new_torque():
  h=DesireHelper();h.update(cs(),True,1.,False,False);h.update(cs(torque=1),True,1.,False,False)
  for _ in range(60):h.update(cs(torque=1),True,0.,False,False)
  assert h.lane_change_state==LaneChangeState.preLaneChange and h.token is None
  h.update(cs(torque=0),True,0.,False,False);h.update(cs(torque=1),True,0.,False,False)
  assert h.lane_change_state==LaneChangeState.laneChangeStarting

from types import SimpleNamespace
from cereal import car, log
import openpilot.selfdrive.controls.lib.desire_helper as dispatch
from openpilot.selfdrive.controls.lib.desire_helper_baseline_v33 import DesireHelper as Baseline

def state(blink=False, torque=0., speed=20., cancel=False):
  return SimpleNamespace(vEgo=speed, vCruise=90., leftBlinker=blink, rightBlinker=False,
    steeringPressed=torque != 0., steeringTorque=torque, leftBlindspot=False, rightBlindspot=False,
    buttonEvents=[SimpleNamespace(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)] if cancel else [])

def test_off_is_exact_baseline_dispatch(monkeypatch):
  monkeypatch.setattr(dispatch, 'Params', lambda: SimpleNamespace(get_bool=lambda key: False))
  wrapper, baseline = dispatch.DesireHelper(), Baseline()
  for i in range(200):
    cs = state(blink=20<=i<170, torque=1. if 40<=i<45 else 0.)
    args = (cs, True, 0. if i>70 else 1., False, False)
    wrapper.update(*args)
    baseline.update(*args)
    for key in ['lane_change_state', 'lane_change_direction', 'lane_change_ll_prob', 'desire']:
      assert getattr(wrapper, key) == getattr(baseline, key)

def test_live_toggle_invalidates_held_confirmation(monkeypatch):
  flag = [False]
  monkeypatch.setattr(dispatch, 'Params', lambda: SimpleNamespace(get_bool=lambda key: flag[0]))
  h = dispatch.DesireHelper()
  h.update(state(True, 1.), True, 1., False, False)
  flag[0] = True
  for _ in range(10):
    h.update(state(True, 1.), True, 1., False, False)
    assert h.desire == log.Desire.none
  h.update(state(True), True, 1., False, False)
  h.update(state(True, 1.), True, 1., False, False)
  assert h.lane_change_state == log.LaneChangeState.laneChangeStarting
  flag[0] = False
  h.update(state(False), False, 1., False, False)
  assert h.desire == log.Desire.none

def test_native_cancel_event_reaches_helper(monkeypatch):
  monkeypatch.setattr(dispatch, 'Params', lambda: SimpleNamespace(get_bool=lambda key: True))
  h = dispatch.DesireHelper()
  h.update(state(True), True, 1., False, False)
  h.update(state(True, 1.), True, 1., False, False)
  assert h.token is not None
  h.update(state(True, 1., cancel=True), True, 1., False, False)
  assert h.token is None
  assert h.desire == log.Desire.none

def test_logged_active_matches_enum(monkeypatch):
  monkeypatch.setattr(dispatch, 'Params', lambda: SimpleNamespace(get_bool=lambda key: True))
  events = []
  monkeypatch.setattr(dispatch.cloudlog, 'event', lambda name, **kw: events.append(kw))
  h = dispatch.DesireHelper()
  h.update(state(True), True, 1., False, False)
  h.update(state(True, 1.), True, 1., False, False)
  assert events[-1]['active']
