"""SET and button behavior for the isolated my-crv longitudinal v3.1 candidate."""

import pytest

from cereal import car
from openpilot.common.constants import CV
from openpilot.selfdrive.car.cruise import VCruiseHelper, CRUISE_LONG_PRESS


ButtonEvent = car.CarState.ButtonEvent
ButtonType = ButtonEvent.Type


def make_helper():
  return VCruiseHelper(car.CarParams(pcmCruise=False))


def set_button():
  return car.CarState(buttonEvents=[ButtonEvent(type=ButtonType.decelCruise, pressed=False)])


@pytest.mark.parametrize("experimental_mode", [False, True])
@pytest.mark.parametrize(("moving_kph", "expected_kph"), [(15, 30), (25, 30), (30, 30), (53, 53), (87, 87)])
def test_first_set_uses_fresh_current_speed_with_30_kph_floor(experimental_mode, moving_kph, expected_kph):
  helper = make_helper()
  speed = moving_kph * CV.KPH_TO_MS
  current = car.CarState(vEgo=speed, vEgoRaw=speed, canValid=True, standstill=False)
  assert helper.initialize_v_cruise(set_button(), experimental_mode, current_CS=current)
  assert helper.v_cruise_kph == expected_kph
  assert helper.v_cruise_cluster_kph == expected_kph


def test_short_press_is_one_kph():
  helper = make_helper()
  helper.v_cruise_kph = 83
  held = car.CarState(cruiseState={"available": True}, buttonEvents=[ButtonEvent(type=ButtonType.accelCruise, pressed=True)])
  released = car.CarState(cruiseState={"available": True}, buttonEvents=[ButtonEvent(type=ButtonType.accelCruise, pressed=False)])
  helper.update_v_cruise(held, enabled=True, is_metric=True)
  helper.update_v_cruise(released, enabled=True, is_metric=True)
  assert helper.v_cruise_kph == 84


@pytest.mark.parametrize(("initial", "button", "expected"), [
  (83, ButtonType.accelCruise, 90),
  (90, ButtonType.accelCruise, 100),
  (97, ButtonType.decelCruise, 90),
])
def test_long_press_aligns_to_ten_kph(initial, button, expected):
  helper = make_helper()
  helper.v_cruise_kph = initial
  held = car.CarState(cruiseState={"available": True}, buttonEvents=[ButtonEvent(type=button, pressed=True)])
  unchanging = car.CarState(cruiseState={"available": True})
  released = car.CarState(cruiseState={"available": True}, buttonEvents=[ButtonEvent(type=button, pressed=False)])
  helper.update_v_cruise(held, enabled=True, is_metric=True)
  for _ in range(CRUISE_LONG_PRESS):
    helper.update_v_cruise(unchanging, enabled=True, is_metric=True)
  assert helper.v_cruise_kph == expected
  helper.update_v_cruise(released, enabled=True, is_metric=True)
  assert helper.v_cruise_kph == expected  # release does not add a short step


def test_resume_preserves_last_valid_set_after_cruise_unavailable():
  helper = make_helper()
  speed = 87 * CV.KPH_TO_MS
  assert helper.initialize_v_cruise(set_button(), False,
                                    current_CS=car.CarState(vEgo=speed, vEgoRaw=speed, canValid=True))
  for _ in range(20):
    helper.update_v_cruise(car.CarState(cruiseState={"available": False}), enabled=False, is_metric=True)
  assert helper.v_cruise_kph != 87
  resume = car.CarState(buttonEvents=[ButtonEvent(type=ButtonType.resumeCruise, pressed=False)])
  assert helper.initialize_v_cruise(resume, False, current_CS=car.CarState(canValid=False))
  assert helper.v_cruise_kph == 87


def test_invalid_standstill_frame_uses_recent_valid_speed():
  helper = make_helper()
  speed = 83 * CV.KPH_TO_MS
  helper.update_v_cruise(car.CarState(vEgo=speed, vEgoRaw=speed, canValid=True), enabled=False, is_metric=True)
  invalid = car.CarState(vEgo=0, vEgoRaw=0, canValid=False, standstill=True)
  assert helper.initialize_v_cruise(set_button(), True, current_CS=invalid)
  assert helper.v_cruise_kph == 83


def test_valid_standstill_does_not_reuse_prior_high_speed():
  helper = make_helper()
  speed = 83 * CV.KPH_TO_MS
  helper.update_v_cruise(car.CarState(vEgo=speed, vEgoRaw=speed, canValid=True), enabled=False, is_metric=True)
  valid_stop = car.CarState(vEgo=0, vEgoRaw=0, canValid=True, standstill=True)
  assert helper.initialize_v_cruise(set_button(), True, current_CS=valid_stop)
  assert helper.v_cruise_kph == 30


def test_stale_speed_does_not_become_a_guess():
  helper = make_helper()
  speed = 83 * CV.KPH_TO_MS
  helper.update_v_cruise(car.CarState(vEgo=speed, vEgoRaw=speed, canValid=True), enabled=False, is_metric=True)
  for _ in range(21):
    helper.update_v_cruise(car.CarState(canValid=False), enabled=False, is_metric=True)
  invalid = car.CarState(vEgo=0, vEgoRaw=0, canValid=False, standstill=False)
  assert not helper.initialize_v_cruise(set_button(), True, current_CS=invalid)
