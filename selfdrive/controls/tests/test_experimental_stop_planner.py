import pytest

from cereal import log
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.tools.mycrv_long_v2.synthetic import messages


@pytest.mark.parametrize(('personality', 'release_frames'), [
  (log.LongitudinalPersonality.relaxed, 6),
  (log.LongitudinalPersonality.standard, 4),
  (log.LongitudinalPersonality.aggressive, 3),
])
def test_blended_stop_flicker_and_restart(personality, release_frames):
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  cp.openpilotLongitudinalControl = True
  planner = LongitudinalPlanner(cp, init_v=1.0)
  sm = messages(1.0, 0.0, 50.0, 1.0, personality, 0.0)
  sm['selfdriveState'].experimentalMode = True
  sm['modelV2'].action.shouldStop = True
  planner.update(sm)
  assert planner.output_should_stop
  assert planner.raw_should_stop_e2e
  assert not planner.should_stop_mpc

  sm['modelV2'].action.shouldStop = False
  for _ in range(release_frames - 1):
    planner.update(sm)
    assert planner.output_should_stop
  planner.update(sm)
  assert not planner.output_should_stop


def test_normal_acc_does_not_hold_model_stop_intent():
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  cp.openpilotLongitudinalControl = True
  planner = LongitudinalPlanner(cp, init_v=1.0)
  sm = messages(1.0, 0.0, 50.0, 1.0, log.LongitudinalPersonality.standard, 0.0)
  sm['modelV2'].action.shouldStop = True
  planner.update(sm)
  assert not planner.experimental_stop_intent_active
  sm['modelV2'].action.shouldStop = False
  planner.update(sm)
  assert not planner.output_should_stop
