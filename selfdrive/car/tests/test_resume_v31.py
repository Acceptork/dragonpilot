"""Non-PCM Honda RESUME after MAIN temporarily hides a previous set speed."""

import pytest

from cereal import car
from openpilot.common.constants import CV
from openpilot.selfdrive.car.cruise import VCruiseHelper, V_CRUISE_UNSET


ButtonEvent = car.CarState.ButtonEvent
ButtonType = ButtonEvent.Type


def car_state(*, available=True, button=None, speed_kph=0):
  cs = car.CarState(cruiseState={"available": available}, vEgo=speed_kph * CV.KPH_TO_MS)
  if button is not None:
    cs.buttonEvents = [ButtonEvent(type=button, pressed=False)]
  return cs


def test_resume_after_main_cycle_recovers_last_adjusted_speed_only_on_resume():
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.initialize_v_cruise(car_state(speed_kph=87, button=ButtonType.decelCruise), False)
  helper.v_cruise_kph = 91  # speed after normal +/- adjustments
  helper.update_v_cruise(car_state(), enabled=False, is_metric=True)
  for _ in range(20):
    helper.update_v_cruise(car_state(available=False), enabled=False, is_metric=True)
  assert helper.v_cruise_kph == V_CRUISE_UNSET
  helper.update_v_cruise(car_state(), enabled=False, is_metric=True)
  assert helper.v_cruise_kph == V_CRUISE_UNSET  # MAIN alone cannot restore it
  helper.update_v_cruise(car_state(button=ButtonType.accelCruise), enabled=False, is_metric=True)
  assert helper.v_cruise_kph == 91  # carState is valid before selfdrived's resumeBlocked gate
  assert helper.initialize_v_cruise(car_state(button=ButtonType.accelCruise), False)
  assert helper.v_cruise_kph == 91


def test_never_set_resume_remains_blocked():
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.update_v_cruise(car_state(button=ButtonType.accelCruise), enabled=False, is_metric=True)
  assert helper.v_cruise_kph == V_CRUISE_UNSET


def test_set_after_main_cycle_uses_current_speed_not_previous_set():
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.initialize_v_cruise(car_state(speed_kph=87, button=ButtonType.decelCruise), False)
  helper.update_v_cruise(car_state(available=False), enabled=False, is_metric=True)
  helper.update_v_cruise(car_state(button=ButtonType.decelCruise, speed_kph=53), enabled=False, is_metric=True)
  assert helper.v_cruise_kph == V_CRUISE_UNSET
  assert helper.initialize_v_cruise(car_state(button=ButtonType.decelCruise, speed_kph=53), False)
  assert helper.v_cruise_kph == 53


def test_no_restore_until_main_available_and_no_pcm_change():
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.initialize_v_cruise(car_state(speed_kph=87, button=ButtonType.decelCruise), False)
  helper.update_v_cruise(car_state(available=False, button=ButtonType.accelCruise), enabled=False, is_metric=True)
  assert helper.v_cruise_kph == V_CRUISE_UNSET
  pcm = VCruiseHelper(car.CarParams(pcmCruise=True))
  pcm.update_v_cruise(car_state(button=ButtonType.accelCruise), enabled=False, is_metric=True)
  assert pcm.last_valid_set_speed_kph == 0


def test_press_without_release_does_not_restore_hidden_speed():
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.initialize_v_cruise(car_state(speed_kph=87, button=ButtonType.decelCruise), False)
  helper.update_v_cruise(car_state(available=False), enabled=False, is_metric=True)
  pressed = car.CarState(cruiseState={"available": True},
                         buttonEvents=[ButtonEvent(type=ButtonType.accelCruise, pressed=True)])
  helper.update_v_cruise(pressed, enabled=False, is_metric=True)
  assert helper.v_cruise_kph == V_CRUISE_UNSET


@pytest.mark.parametrize("remembered", [0, 7, 146, 255])
def test_invalid_memory_never_bypasses_resume_block(remembered):
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.last_valid_set_speed_kph = remembered
  helper.update_v_cruise(car_state(button=ButtonType.accelCruise), enabled=False, is_metric=True)
  assert helper.v_cruise_kph == V_CRUISE_UNSET


def test_honda_res_accel_falling_edge_restores_after_main_cycle():
  """Use Honda's actual button mapper, not a hand-built button event."""
  from types import SimpleNamespace
  from opendbc.car import create_button_events
  from opendbc.car.honda.carstate import BUTTONS_DICT
  from opendbc.car.honda.values import CruiseButtons
  from opendbc.car.interfaces import CarStateBase

  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.initialize_v_cruise(car_state(speed_kph=87, button=ButtonType.decelCruise), False)
  helper.update_v_cruise(car_state(available=False), enabled=False, is_metric=True)

  press = create_button_events(CruiseButtons.RES_ACCEL, 0, BUTTONS_DICT)
  release = create_button_events(0, CruiseButtons.RES_ACCEL, BUTTONS_DICT)
  honda_interface = SimpleNamespace(CP=car.CarParams(pcmCruise=False))
  assert len(press) == len(release) == 1
  assert press[0].type == release[0].type == ButtonType.accelCruise
  assert press[0].pressed and not release[0].pressed
  assert not CarStateBase.update_button_enable(honda_interface, press)
  assert CarStateBase.update_button_enable(honda_interface, release)

  helper.update_v_cruise(car.CarState(cruiseState={"available": True}, buttonEvents=press),
                         enabled=False, is_metric=True)
  assert helper.v_cruise_kph == V_CRUISE_UNSET
  helper.update_v_cruise(car.CarState(cruiseState={"available": True}, buttonEvents=release),
                         enabled=False, is_metric=True)
  assert helper.v_cruise_kph == 87


def test_new_set_replaces_resume_memory_after_main_cycle():
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.initialize_v_cruise(car_state(speed_kph=87, button=ButtonType.decelCruise), False)
  helper.update_v_cruise(car_state(available=False), enabled=False, is_metric=True)
  assert helper.initialize_v_cruise(car_state(speed_kph=53, button=ButtonType.decelCruise), False)
  assert helper.last_valid_set_speed_kph == 53
  helper.update_v_cruise(car_state(available=False), enabled=False, is_metric=True)
  helper.update_v_cruise(car_state(button=ButtonType.accelCruise), enabled=False, is_metric=True)
  assert helper.v_cruise_kph == 53


def test_resume_restore_does_not_add_one_with_stale_enabled_frame():
  helper = VCruiseHelper(car.CarParams(pcmCruise=False))
  helper.initialize_v_cruise(car_state(speed_kph=87, button=ButtonType.decelCruise), False)
  press = car.CarState(cruiseState={"available": True},
                       buttonEvents=[ButtonEvent(type=ButtonType.accelCruise, pressed=True)])
  helper.update_v_cruise(press, enabled=True, is_metric=True)
  helper.update_v_cruise(car_state(available=False), enabled=True, is_metric=True)
  helper.update_v_cruise(car_state(button=ButtonType.accelCruise), enabled=True, is_metric=True)
  assert helper.v_cruise_kph == 87
  assert helper.last_valid_set_speed_kph == 87
