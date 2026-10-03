import pytest
from cereal import car
from openpilot.selfdrive.car.cruise import VCruiseHelper
B=car.CarState.ButtonEvent.Type

def step(h,b=None,pressed=False,enabled=True,standstill=False,gas=False):
  c=car.CarState(canValid=True,vEgo=20.,vEgoRaw=20.,gasPressed=gas,
      cruiseState={"available":True,"standstill":standstill},
      buttonEvents=[] if b is None else [{"type":b,"pressed":pressed}])
  h.update_v_cruise(c,enabled,True)

@pytest.mark.parametrize('speed,button,target',[(83,B.accelCruise,90),(90,B.accelCruise,100),(97,B.decelCruise,90)])
def test_hold_once_release_and_repeat(speed,button,target):
  h=VCruiseHelper(car.CarParams(pcmCruise=False)); h.v_cruise_kph=speed
  step(h,button,True)
  for _ in range(49): step(h)
  assert h.v_cruise_kph==speed
  step(h)
  assert h.v_cruise_kph==target
  for _ in range(200): step(h)
  assert h.v_cruise_kph==target
  step(h,button,False)
  assert h.v_cruise_kph==target
  step(h,button,True)
  for _ in range(50): step(h)
  assert h.v_cruise_kph==target+(10 if button==B.accelCruise else -10)

@pytest.mark.parametrize('hold',[1,49,50,51])
def test_release_boundary(hold):
  h=VCruiseHelper(car.CarParams(pcmCruise=False)); h.v_cruise_kph=83
  step(h,B.accelCruise,True)
  for _ in range(hold-1): step(h)
  step(h,B.accelCruise,False)
  assert h.v_cruise_kph==(90 if hold>50 else 84)

def test_standstill_and_enable_edge():
  for standstill in [False,True]:
    h=VCruiseHelper(car.CarParams(pcmCruise=False)); h.v_cruise_kph=83
    step(h,B.accelCruise,True,enabled=False,standstill=standstill)
    for _ in range(100): step(h,standstill=standstill)
    step(h,B.accelCruise,False,standstill=standstill)
    assert h.v_cruise_kph==83
