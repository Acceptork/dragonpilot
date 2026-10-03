import math
import pytest
from cereal import car
from openpilot.selfdrive.car.cruise import VCruiseHelper
B = car.CarState.ButtonEvent.Type

def cs(speed=0., valid=True, standstill=False, button=B.decelCruise):
  return car.CarState(vEgo=speed/3.6, vEgoRaw=speed/3.6, canValid=valid, standstill=standstill,
                     cruiseState={"available": True}, buttonEvents=[{"type":button,"pressed":False}])

@pytest.mark.parametrize('speed', [0,15,25,30,53,87,120])
@pytest.mark.parametrize('experimental', [False,True])
def test_set_floor(speed,experimental):
  h=VCruiseHelper(car.CarParams(pcmCruise=False))
  c=cs(speed,standstill=speed==0)
  assert h.initialize_v_cruise(c,experimental,current_CS=c)
  assert h.v_cruise_kph == max(round(speed),30)
  assert h.v_cruise_cluster_kph == h.v_cruise_kph
  assert h.last_valid_set_speed_kph == h.v_cruise_kph

@pytest.mark.parametrize('age,valid',[(0,True),(20,True),(21,False)])
@pytest.mark.parametrize('standstill',[False,True])
def test_cache_validity(age,valid,standstill):
  h=VCruiseHelper(car.CarParams(pcmCruise=False))
  h.update_v_cruise(cs(87),False,True)
  for _ in range(age): h.update_v_cruise(cs(0,False),False,True)
  c=cs(0,False,standstill)
  assert h.initialize_v_cruise(c,True,current_CS=c) == valid
  if valid: assert h.v_cruise_kph==87

@pytest.mark.parametrize('bad',[float('nan'),float('inf')])
def test_bad_speed_rejected(bad):
  h=VCruiseHelper(car.CarParams(pcmCruise=False))
  c=cs(bad,False)
  assert not h.initialize_v_cruise(c,False,current_CS=c)

def test_resume_then_reset_and_main():
  h=VCruiseHelper(car.CarParams(pcmCruise=False))
  c=cs(87)
  assert h.initialize_v_cruise(c,False,current_CS=c)
  h.update_v_cruise(car.CarState(cruiseState={"available":False}),False,True)
  resume=cs(15,button=B.resumeCruise)
  h.update_v_cruise(resume,False,True)
  assert h.v_cruise_kph==87
  c=cs(25)
  assert h.initialize_v_cruise(c,True,current_CS=c)
  assert h.v_cruise_kph==30
  assert h.initialize_v_cruise(resume,False,current_CS=resume)
  assert h.v_cruise_kph==30

def test_no_cycle_clamp_and_pcm():
  h=VCruiseHelper(car.CarParams(pcmCruise=False))
  h.v_cruise_kph=15
  c=cs(25); c.buttonEvents=[]
  h.update_v_cruise(c,False,True)
  assert h.v_cruise_kph==15
  p=VCruiseHelper(car.CarParams(pcmCruise=True))
  c.cruiseState.speed=20/3.6; c.cruiseState.speedCluster=20/3.6
  p.update_v_cruise(c,True,True)
  assert p.initialize_v_cruise(c,True,current_CS=c)
  assert p.v_cruise_kph==pytest.approx(20)
