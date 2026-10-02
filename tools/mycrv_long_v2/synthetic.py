#!/usr/bin/env python3
"""Compare v2 personalities with native MPC and an idealized 0.5 s actuator.

This does not model Honda CAN, tires, grades, or collision dynamics.
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
KPH = 3.6
PERSONALITIES = {'relaxed': log.LongitudinalPersonality.relaxed,
                 'standard': log.LongitudinalPersonality.standard,
                 'aggressive': log.LongitudinalPersonality.aggressive}
CASES = {
  '01_70_to_90_clear': (70, 90, 24, 0.05, 0.0, None),
  '02_85_to_90_clear': (85, 90, 12, 1.0, 0.0, None),
  '03_steady_90': (90, 90, 10, 1.0, 0.0, None),
  '04_lead_70_to_90': (70, 90, 10, 0.05, 0.0, 'pullaway'),
  '05_lead_brakes': (90, 90, 8, 1.0, 0.0, 'brakes'),
  '06_cut_in': (90, 90, 8, 1.0, 0.0, 'cutin'),
  '07_lead_lost': (70, 90, 8, 0.05, 0.0, 'lost'),
  '08_lead_reacquired': (70, 90, 8, 0.05, 0.0, 'reacquired'),
  '09_low_gas_prob_75_to_90': (75, 90, 24, 0.01, 0.0, None),
  '10_uphill': (70, 90, 8, 0.05, 0.03, None),
  '10_downhill': (70, 90, 8, 0.05, -0.03, None),
  '10_strong_grade': (70, 90, 8, 0.05, 0.10, None),
}


def load(name, path):
  spec = importlib.util.spec_from_file_location(name, path)
  module = importlib.util.module_from_spec(spec)
  sys.modules[name] = module
  spec.loader.exec_module(module)


def load_candidate(staged_dir):
  if staged_dir:
    staged = Path(staged_dir)
    load('openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc', staged / 'long_mpc.py')
    load('openpilot.selfdrive.controls.lib.longitudinal_throttle', staged / 'longitudinal_throttle.py')
    load('openpilot.selfdrive.controls.lib.longitudinal_planner', staged / 'longitudinal_planner.py')
  from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
  return LongitudinalPlanner


def messages(speed, actual_accel, cruise_kph, gas_prob, personality, pitch, gap=None, lead_speed=None, lead_accel=0.0):
  car_state = messaging.new_message('carState').carState
  car_state.vEgo = speed
  car_state.aEgo = actual_accel
  car_state.vCruise = cruise_kph
  controls = messaging.new_message('controlsState').controlsState
  controls.longControlState = LongCtrlState.pid
  selfdrive = messaging.new_message('selfdriveState').selfdriveState
  selfdrive.enabled = True
  selfdrive.personality = personality
  car_control = messaging.new_message('carControl').carControl
  car_control.orientationNED = [0.0, pitch, 0.0]
  live_params = messaging.new_message('liveParameters').liveParameters
  live_params.angleOffsetDeg = 0.0
  model = messaging.new_message('modelV2').modelV2
  t = np.array(ModelConstants.T_IDXS)
  position = log.XYZTData.new_message()
  position.x = (speed * t).tolist()
  model.position = position
  velocity = log.XYZTData.new_message()
  velocity.x = [speed] * len(t)
  model.velocity = velocity
  acceleration = log.XYZTData.new_message()
  acceleration.x = [0.0] * len(t)
  model.acceleration = acceleration
  model.meta.disengagePredictions.gasPressProbs = [gas_prob] * 6
  model.action.desiredAcceleration = 0.0
  radar = messaging.new_message('radarState').radarState
  if gap is not None:
    lead = log.RadarState.LeadData.new_message()
    lead.status = True
    lead.dRel = max(0.0, gap)
    lead.vLead = lead_speed
    lead.vRel = lead_speed - speed
    lead.aLeadK = lead_accel
    lead.aLeadTau = 0.3
    lead.modelProb = 0.9
    radar.leadOne = lead
  return {'carState': car_state, 'controlsState': controls, 'selfdriveState': selfdrive,
          'carControl': car_control, 'liveParameters': live_params, 'modelV2': model,
          'radarState': radar}


def lead_motion(kind, time_s, ego_position, lead_position):
  if kind is None:
    return None, None, 0.0, lead_position
  if kind == 'pullaway':
    lead_speed = min(90.0, 70.0 + max(0.0, time_s - 1.0) * 5.4) / KPH
    lead_accel = 1.5 if 1.0 <= time_s < 4.7 else 0.0
  elif kind == 'brakes':
    lead_speed = max(70.0, 90.0 - max(0.0, time_s - 1.0) * 7.2) / KPH
    lead_accel = -2.0 if 1.0 <= time_s < 3.8 else 0.0
  else:
    lead_speed = (75.0 if kind == 'cutin' else 70.0) / KPH
    lead_accel = 0.0
  if kind == 'cutin' and abs(time_s - 2.0) < DT / 2:
    lead_position = ego_position + 28.0
  if kind == 'reacquired' and abs(time_s - 2.0) < DT / 2:
    lead_position = ego_position + 32.0
  lead_position += lead_speed * DT
  visible = ((kind in ('pullaway', 'brakes')) or
             (kind == 'cutin' and time_s >= 2.0) or
             (kind == 'lost' and time_s < 1.0) or
             (kind == 'reacquired' and (time_s < 1.0 or time_s >= 2.0)))
  return (lead_position - ego_position if visible else None), lead_speed, lead_accel, lead_position


def simulate(planner_cls, case, personality):
  initial_kph, cruise_kph, duration, gas_prob, pitch, lead_kind = CASES[case]
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  CP.openpilotLongitudinalControl = True
  speed = initial_kph / KPH
  planner = planner_cls(CP, init_v=speed)
  actual_accel = ego_position = 0.0
  lead_position = 60.0 if lead_kind == 'brakes' else 35.0
  if lead_kind in ('lost', 'reacquired'):
    lead_position = 30.0
  outputs, speeds, gaps, predicted_gaps = [], [], [], []
  first_positive = None
  time_to = {80: None, 85: None, 90: None}
  samples = {}
  for frame in range(round(duration / DT)):
    time_s = frame * DT
    gap, lead_speed, lead_accel, lead_position = lead_motion(lead_kind, time_s, ego_position, lead_position)
    sm = messages(speed, actual_accel, cruise_kph, gas_prob, personality, pitch, gap, lead_speed, lead_accel)
    planner.update(sm)
    target = float(planner.output_a_target)
    outputs.append(target)
    if first_positive is None and target > 0.1:
      first_positive = time_s
    if gap is not None:
      gaps.append(gap)
      lead_xv = planner.mpc.process_lead(sm['radarState'].leadOne)
      predicted_gaps.append(float(np.min(lead_xv[:, 0] - planner.mpc.x_sol[:, 0])))
    if frame in (0, 7, 9, 13, 19, 39, 99):
      samples[f'{time_s:.2f}'] = round(target, 3)
    actual_accel += (target - actual_accel) * DT / 0.5
    speed = max(0.0, speed + actual_accel * DT)
    ego_position += speed * DT
    speeds.append(speed * KPH)
    for threshold in time_to:
      # MPC can approach the set speed asymptotically, so count 89.9 as 90.
      arrival_speed = threshold - (0.1 if threshold == 90 else 0.0)
      if time_to[threshold] is None and speed * KPH >= arrival_speed:
        time_to[threshold] = round(time_s + DT, 2)
  max_jerk = max((abs(b - a) / DT for a, b in zip(outputs, outputs[1:])), default=0.0)
  return {'aTargetAt': samples, 'peakAccel': round(max(outputs), 3),
          'firstPositive': None if first_positive is None else round(first_positive, 2),
          'timeTo80_85_90': time_to, 'maxOvershootKph': round(max(0.0, max(speeds) - cruise_kph), 2),
          'maxDecel': round(min(outputs), 3), 'maxJerk': round(max_jerk, 3),
          'minGap': None if not gaps else round(min(gaps), 2),
          'minPredictedGap': None if not predicted_gaps else round(min(predicted_gaps), 2),
          'finalSpeedKph': round(speeds[-1], 2)}


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--staged-dir')
  args = parser.parse_args()
  planner_cls = load_candidate(args.staged_dir)
  for case in CASES:
    results = {name: simulate(planner_cls, case, personality) for name, personality in PERSONALITIES.items()}
    print(json.dumps({'scenario': case, 'modes': results}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
  main()
