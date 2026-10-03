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
