"""Non-PCM Honda RESUME after MAIN temporarily hides a previous set speed."""

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
