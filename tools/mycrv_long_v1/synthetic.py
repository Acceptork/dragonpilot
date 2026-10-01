#!/usr/bin/env python3
"""Run six offline CR-V 5G longitudinal scenarios with the native MPC solver.

Usage on a built comma checkout:
  python tools/mycrv_long_v1/synthetic.py [--staged-dir /tmp/mycrv-long-v1]

The staged form loads candidate Python files without replacing the running checkout.
No messaging sockets or CAN devices are opened.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from cereal import log
import cereal.messaging as messaging
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.modeld.constants import ModelConstants


DT = 0.05


def load_planner(staged_dir):
  if staged_dir is None:
    from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
    return LongitudinalPlanner

  staged = Path(staged_dir)
  helper_name = 'openpilot.selfdrive.controls.lib.longitudinal_throttle'
  helper_spec = importlib.util.spec_from_file_location(helper_name, staged / 'longitudinal_throttle.py')
  helper = importlib.util.module_from_spec(helper_spec)
  sys.modules[helper_name] = helper
  helper_spec.loader.exec_module(helper)

  planner_spec = importlib.util.spec_from_file_location('mycrv_staged_longitudinal_planner', staged / 'longitudinal_planner.py')
  planner = importlib.util.module_from_spec(planner_spec)
  planner_spec.loader.exec_module(planner)
  return planner.LongitudinalPlanner


def make_messages(v_ego, v_cruise, gas_prob, pitch=0.0, lead_distance=None, lead_speed=None):
  car_state = messaging.new_message('carState').carState
  car_state.vEgo = v_ego
  car_state.aEgo = 0.0
  car_state.vCruise = v_cruise * 3.6
  car_state.standstill = False

  controls = messaging.new_message('controlsState').controlsState
  controls.longControlState = LongCtrlState.pid
  controls.forceDecel = False

  selfdrive = messaging.new_message('selfdriveState').selfdriveState
  selfdrive.enabled = True
  selfdrive.experimentalMode = False
  selfdrive.personality = log.LongitudinalPersonality.standard

  car_control = messaging.new_message('carControl').carControl
  car_control.orientationNED = [0.0, pitch, 0.0]

  live_params = messaging.new_message('liveParameters').liveParameters
  live_params.angleOffsetDeg = 0.0

  model = messaging.new_message('modelV2').modelV2
  t = np.array(ModelConstants.T_IDXS)
  position = log.XYZTData.new_message()
  position.x = (v_ego * t).tolist()
  model.position = position
  velocity = log.XYZTData.new_message()
  velocity.x = [v_ego] * len(t)
  model.velocity = velocity
  acceleration = log.XYZTData.new_message()
  acceleration.x = [0.0] * len(t)
  model.acceleration = acceleration
  model.meta.disengagePredictions.gasPressProbs = [gas_prob] * 6
  model.action.desiredAcceleration = 0.0

  radar = messaging.new_message('radarState').radarState
  if lead_distance is not None:
    lead = log.RadarState.LeadData.new_message()
    lead.status = True
    lead.dRel = lead_distance
    lead.vLead = lead_speed
    lead.vRel = lead_speed - v_ego
    lead.aLeadK = 0.0
    lead.aLeadTau = 0.3
    lead.modelProb = 0.9
    radar.leadOne = lead

  return {'carState': car_state, 'controlsState': controls, 'selfdriveState': selfdrive,
          'carControl': car_control, 'liveParameters': live_params, 'modelV2': model,
          'radarState': radar}


def run_case(planner_cls, updates, initial_speed):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  CP.openpilotLongitudinalControl = True
  planner = planner_cls(CP, init_v=initial_speed)
  result = []
  for update in updates:
    planner.update(make_messages(**update))
    result.append({'aTarget': round(float(planner.output_a_target), 3),
                   'allowThrottle': bool(planner.allow_throttle),
                   'source': str(planner.mpc.source)})
  return result


def run_cruise_approach(planner_cls, initial_speed, cruise_speed):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  CP.openpilotLongitudinalControl = True
  planner = planner_cls(CP, init_v=initial_speed)
  speed = initial_speed
  result = []
  for _ in range(120):
    planner.update(make_messages(speed, cruise_speed, gas_prob=1.0))
    accel = float(planner.output_a_target)
    speed += accel * DT  # idealized plant; the real Honda command path is not modeled
    result.append({'aTarget': round(accel, 3), 'vEgoKph': round(speed * 3.6, 2)})
  return result


def scenarios(planner_cls):
  kph = lambda v: v / 3.6
  cases = {}
  cases['1_90_set_70_no_lead'] = run_case(planner_cls,
    [dict(v_ego=kph(70), v_cruise=kph(90), gas_prob=0.05)] * 30, kph(70))
  cases['2_90_set_85_taper'] = run_cruise_approach(planner_cls, kph(85), kph(90))
  cases['3_lead_pulls_away'] = run_case(planner_cls,
    [dict(v_ego=kph(70), v_cruise=kph(90), gas_prob=0.05, lead_distance=30.0, lead_speed=kph(70))] * 12 +
    [dict(v_ego=kph(70), v_cruise=kph(90), gas_prob=0.05, lead_distance=30.0 + 2.0 * i * DT,
          lead_speed=kph(70) + 2.0) for i in range(25)], kph(70))
  cases['4_lead_disappears'] = run_case(planner_cls,
    [dict(v_ego=kph(70), v_cruise=kph(90), gas_prob=0.05, lead_distance=30.0, lead_speed=kph(70))] * 12 +
    [dict(v_ego=kph(70), v_cruise=kph(90), gas_prob=0.05)] * 20, kph(70))
  cases['5_uphill_pitch'] = run_case(planner_cls,
    [dict(v_ego=kph(70), v_cruise=kph(90), gas_prob=0.05, pitch=0.03)] * 30, kph(70))
  cases['5_downhill_pitch'] = run_case(planner_cls,
    [dict(v_ego=kph(70), v_cruise=kph(90), gas_prob=0.05, pitch=-0.03)] * 30, kph(70))
  cases['5_strong_pitch_keeps_model_coast'] = run_case(planner_cls,
    [dict(v_ego=kph(70), v_cruise=kph(90), gas_prob=0.05, pitch=0.1)] * 30, kph(70))
  cases['6_low_model_gas_15_gap'] = run_case(planner_cls,
    [dict(v_ego=kph(75), v_cruise=kph(90), gas_prob=0.01)] * 30, kph(75))
  return cases


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--staged-dir')
  args = parser.parse_args()
  result = scenarios(load_planner(args.staged_dir))
  for name, frames in result.items():
    sample_idx = [0, 9, 19, 29]
    if name.startswith('2_'):
      sample_idx = [0, 19, 39, 79, len(frames) - 1]
    if name.startswith(('3_', '4_')):
      sample_idx = [11, 12, 21, 31, len(frames) - 1]
    print(json.dumps({'scenario': name, 'frames': {str(i): frames[i] for i in sample_idx}}, ensure_ascii=False))


if __name__ == '__main__':
  main()
