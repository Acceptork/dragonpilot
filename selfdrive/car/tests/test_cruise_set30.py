"""Focused first-SET tests for the independent 30 km/h candidate."""

import pytest

from cereal import car
from openpilot.common.constants import CV
from openpilot.selfdrive.car.cruise import VCruiseHelper, V_CRUISE_UNSET


ButtonEvent = car.CarState.ButtonEvent
ButtonType = ButtonEvent.Type


def helper():
  return VCruiseHelper(car.CarParams(pcmCruise=False))


def set_frame():
  # card retains the button frame while the current CAN frame supplies speed.
  return car.CarState(vEgo=0, buttonEvents=[ButtonEvent(type=ButtonType.decelCruise, pressed=False)])


def moving_frame(kph):
  speed = kph * CV.KPH_TO_MS
  return car.CarState(vEgo=speed, vEgoRaw=speed, canValid=True, standstill=False)


@pytest.mark.parametrize("experimental_mode", [False, True])
@pytest.mark.parametrize(("speed_kph", "expected_kph"), [(15, 30), (25, 30), (30, 30), (53, 53), (87, 87)])
def test_first_set_uses_current_valid_speed_with_floor(experimental_mode, speed_kph, expected_kph):
  cruise = helper()
  assert cruise.initialize_v_cruise(set_frame(), experimental_mode, current_CS=moving_frame(speed_kph))
  assert cruise.v_cruise_kph == expected_kph
  assert cruise.v_cruise_cluster_kph == expected_kph


def test_valid_standstill_uses_30_in_experimental_mode():
  cruise = helper()
  current = car.CarState(vEgo=0, vEgoRaw=0, canValid=True, standstill=True)
  assert cruise.initialize_v_cruise(set_frame(), True, current_CS=current)
  assert cruise.v_cruise_kph == 30


def test_invalid_standstill_bit_uses_recent_moving_speed():
  cruise = helper()
  cruise.update_v_cruise(moving_frame(83), enabled=False, is_metric=True)
  invalid = car.CarState(vEgo=0, vEgoRaw=0, canValid=False, standstill=True)
  assert cruise.initialize_v_cruise(set_frame(), True, current_CS=invalid)
  assert cruise.v_cruise_kph == 83


def test_invalid_standstill_without_fresh_speed_waits_instead_of_guessing():
  cruise = helper()
  invalid = car.CarState(vEgo=0, vEgoRaw=0, canValid=False, standstill=True)
  assert not cruise.initialize_v_cruise(set_frame(), True, current_CS=invalid)
  assert cruise.v_cruise_kph == V_CRUISE_UNSET

  cruise.update_v_cruise(moving_frame(83), enabled=False, is_metric=True)
  for _ in range(21):
    cruise.update_v_cruise(car.CarState(canValid=False), enabled=False, is_metric=True)
  assert not cruise.initialize_v_cruise(set_frame(), True, current_CS=invalid)
  assert cruise.v_cruise_kph == V_CRUISE_UNSET


def test_invalid_standstill_uses_speed_at_freshness_boundary():
  cruise = helper()
  cruise.update_v_cruise(moving_frame(83), enabled=False, is_metric=True)
  for _ in range(20):
    cruise.update_v_cruise(car.CarState(canValid=False), enabled=False, is_metric=True)
  invalid = car.CarState(vEgo=0, vEgoRaw=0, canValid=False, standstill=True)
  assert cruise.initialize_v_cruise(set_frame(), True, current_CS=invalid)
  assert cruise.v_cruise_kph == 83


def test_valid_low_speed_uses_floor_even_when_not_standstill():
  cruise = helper()
  speed = 3 * CV.KPH_TO_MS
  current = car.CarState(vEgo=speed, vEgoRaw=speed, canValid=True, standstill=False)
  assert cruise.initialize_v_cruise(set_frame(), False, current_CS=current)
  assert cruise.v_cruise_kph == 30
