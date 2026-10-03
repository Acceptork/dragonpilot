import pytest

from cereal import car
from openpilot.selfdrive.car.cruise import VCruiseHelper


ButtonEvent = car.CarState.ButtonEvent
ButtonType = car.CarState.ButtonEvent.Type


def state(button=None, pressed=None):
  events = [] if button is None else [ButtonEvent(type=button, pressed=pressed)]
  return car.CarState(cruiseState={"available": True}, buttonEvents=events)


def helper_at(speed):
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.v_cruise_kph = speed
  return helper


def hold(helper, button, frames, metric=True):
  helper.update_v_cruise(state(button, True), enabled=True, is_metric=metric)
  for _ in range(frames):
    helper.update_v_cruise(state(), enabled=True, is_metric=metric)


@pytest.mark.parametrize("start,button,expected", [
  (83, ButtonType.accelCruise, 90),
  (90, ButtonType.accelCruise, 100),
  (97, ButtonType.decelCruise, 90),
])
def test_metric_hold_one_aligned_step(start, button, expected):
  helper = helper_at(start)
  hold(helper, button, 49)
  assert helper.v_cruise_kph == start
  helper.update_v_cruise(state(), enabled=True, is_metric=True)
  assert helper.v_cruise_kph == expected
  for _ in range(101):
    helper.update_v_cruise(state(), enabled=True, is_metric=True)
  assert helper.v_cruise_kph == expected
  helper.update_v_cruise(state(button, False), enabled=True, is_metric=True)
  assert helper.v_cruise_kph == expected


def test_metric_new_hold_gets_one_new_step():
  helper = helper_at(83)
  hold(helper, ButtonType.accelCruise, 110)
  assert helper.v_cruise_kph == 90
  helper.update_v_cruise(state(ButtonType.accelCruise, False), enabled=True, is_metric=True)
  hold(helper, ButtonType.accelCruise, 110)
  assert helper.v_cruise_kph == 100
  helper.update_v_cruise(state(ButtonType.accelCruise, False), enabled=True, is_metric=True)
  assert helper.v_cruise_kph == 100


@pytest.mark.parametrize("start,button,expected", [
  (83, ButtonType.accelCruise, 84),
  (97, ButtonType.decelCruise, 96),
])
def test_metric_short_press_is_one_kph(start, button, expected):
  helper = helper_at(start)
  hold(helper, button, 2)
  helper.update_v_cruise(state(button, False), enabled=True, is_metric=True)
  assert helper.v_cruise_kph == expected


def test_imperial_long_hold_keeps_existing_repeat():
  helper = helper_at(80)
  hold(helper, ButtonType.accelCruise, 50, metric=False)
  assert helper.v_cruise_kph == 88
  for _ in range(50):
    helper.update_v_cruise(state(), enabled=True, is_metric=False)
  assert helper.v_cruise_kph == 96


def test_first_set_and_resume_unchanged():
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  set_event = car.CarState(vEgo=53 / 3.6, vEgoRaw=53 / 3.6, canValid=True,
                           buttonEvents=[ButtonEvent(type=ButtonType.decelCruise, pressed=False)])
  assert helper.initialize_v_cruise(set_event, experimental_mode=False, current_CS=set_event)
  assert helper.v_cruise_kph == 53
  helper.v_cruise_kph_last = 87
  resume_event = car.CarState(buttonEvents=[ButtonEvent(type=ButtonType.resumeCruise, pressed=False)])
  assert helper.initialize_v_cruise(resume_event, experimental_mode=False)
  assert helper.v_cruise_kph == 87
