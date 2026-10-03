#!/usr/bin/env python3
import math
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.early_stop_v33 import EarlyStop, Inputs as EarlyStopInputs
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.restart_v33 import AutoRestart
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.ramp_v33 import RampRecovery
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.personality_v33 import CruiseRecovery
from cereal import log
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.overtake_v33 import OvertakePreaccel
import numpy as np

import cereal.messaging as messaging
from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LongitudinalMpc, LongitudinalPlanSource, COMFORT_BRAKE, STOP_DISTANCE, get_T_FOLLOW
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import T_IDXS as T_IDXS_MPC
from openpilot.selfdrive.controls.lib.longitudinal_throttle import ThrottleGate, grade_allows_override, model_allows_override, path_clear_for_throttle
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N, get_accel_from_plan
from openpilot.selfdrive.car.cruise import V_CRUISE_MAX, V_CRUISE_UNSET
from openpilot.common.swaglog import cloudlog
from dragonpilot.selfdrive.controls.lib.acm import ACM
from dragonpilot.selfdrive.controls.lib.aem import AEM
from dragonpilot.selfdrive.controls.lib.apm import APM

A_CRUISE_MAX_VALS = [1.6, 1.2, 0.8, 0.6]
A_CRUISE_MAX_BP = [0., 10.0, 25., 40.]
CONTROL_N_T_IDX = ModelConstants.T_IDXS[:CONTROL_N]
ALLOW_THROTTLE_THRESHOLD = 0.4
MIN_ALLOW_THROTTLE_SPEED = 2.5

# Lookup table for turns
_A_TOTAL_MAX_V = [1.7, 3.2]
_A_TOTAL_MAX_BP = [20., 40.]

class DPFlags:
  ACM = 1
  AEM = 2
  APM = 2 ** 2
  pass


def get_max_accel(v_ego):
  return np.interp(v_ego, A_CRUISE_MAX_BP, A_CRUISE_MAX_VALS)

def get_coast_accel(pitch):
  return np.sin(pitch) * -5.65 - 0.3  # fitted from data using xx/projects/allow_throttle/compute_coast_accel.py

def limit_accel_in_turns(v_ego, angle_steers, a_target, CP):
  """
  This function returns a limited long acceleration allowed, depending on the existing lateral acceleration
  this should avoid accelerating when losing the target in turns
  """
  # FIXME: This function to calculate lateral accel is incorrect and should use the VehicleModel
  # The lookup table for turns should also be updated if we do this
  a_total_max = np.interp(v_ego, _A_TOTAL_MAX_BP, _A_TOTAL_MAX_V)
  a_y = v_ego ** 2 * angle_steers * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
  a_x_allowed = math.sqrt(max(a_total_max ** 2 - a_y ** 2, 0.))

  return [a_target[0], min(a_target[1], a_x_allowed)]


from openpilot.selfdrive.controls.lib.diagnostics_v32 import OvershootEvent, emit_trace

class LongitudinalPlanner:
  def __init__(self, CP, init_v=0.0, init_a=0.0, dt=DT_MDL):
    self.CP = CP
    self.v33_stop = EarlyStop()
    self.v33_params = Params()
    self.v33_log_frame = 0
    self.v33_last_reason = None
    self.v33_restart = AutoRestart()
    self.v33_params = Params()
    self.v33_restart_frame = 0
    self.v33_restart_previous = None
    self.v33_ramp = RampRecovery()
    self.v33_params = Params()
    self.v33_ramp_frame = 0
    self.v33_ramp_previous = None
    self.v33_personality = CruiseRecovery()
    self.v33_params = Params()
    self.v33_personality_frame = 0
    self.v33_personality_previous = None
    self.v33_overtake = OvertakePreaccel()
    self.v33_params = Params()
    self.v33_overtake_frame = 0
    self.v33_overtake_previous = None
    self.mpc = LongitudinalMpc(dt=dt)
    self.fcw = False
    self.overshoot_event = OvershootEvent()
    self.diagnostic_trace = {}
    self.dt = dt
    self.allow_throttle = True
    self.throttle_gate = ThrottleGate()

    self.a_desired = init_a
    self.v_desired_filter = FirstOrderFilter(init_v, 2.0, self.dt)
    self.prev_accel_clip = [ACCEL_MIN, ACCEL_MAX]
    self.output_a_target = 0.0
    self.output_should_stop = False

    self.v_desired_trajectory = np.zeros(CONTROL_N)
    self.a_desired_trajectory = np.zeros(CONTROL_N)
    self.j_desired_trajectory = np.zeros(CONTROL_N)
    self.acm = ACM()
    self.aem = AEM()
    self.apm = APM()

  @staticmethod
  def parse_model(model_msg):
    if (len(model_msg.position.x) == ModelConstants.IDX_N and
      len(model_msg.velocity.x) == ModelConstants.IDX_N and
      len(model_msg.acceleration.x) == ModelConstants.IDX_N):
      x = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.position.x)
      v = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.velocity.x)
      a = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.acceleration.x)
      j = np.zeros(len(T_IDXS_MPC))
    else:
      x = np.zeros(len(T_IDXS_MPC))
      v = np.zeros(len(T_IDXS_MPC))
      a = np.zeros(len(T_IDXS_MPC))
      j = np.zeros(len(T_IDXS_MPC))
    if len(model_msg.meta.disengagePredictions.gasPressProbs) > 1:
      throttle_prob = model_msg.meta.disengagePredictions.gasPressProbs[1]
    else:
      throttle_prob = 1.0
    return x, v, a, j, throttle_prob

  def update(self, sm, dp_flags = 0):
    if len(sm['carControl'].orientationNED) == 3:
      accel_coast = get_coast_accel(sm['carControl'].orientationNED[1])
    else:
      accel_coast = ACCEL_MAX

    v_ego = sm['carState'].vEgo
    v_cruise_kph = min(sm['carState'].vCruise, V_CRUISE_MAX)
    v_cruise = v_cruise_kph * CV.KPH_TO_MS
    v_cruise_initialized = sm['carState'].vCruise != V_CRUISE_UNSET

    long_control_off = sm['controlsState'].longControlState == LongCtrlState.off
    force_slow_decel = sm['controlsState'].forceDecel

    # Reset current state when not engaged, or user is controlling the speed
    reset_state = long_control_off if self.CP.openpilotLongitudinalControl else not sm['selfdriveState'].enabled
    # PCM cruise speed may be updated a few cycles later, check if initialized
    reset_state = reset_state or not v_cruise_initialized

    # No change cost when user is controlling the speed, or when standstill
    prev_accel_constraint = not (reset_state or sm['carState'].standstill)

    accel_clip = [ACCEL_MIN, get_max_accel(v_ego)]
    steer_angle_without_offset = sm['carState'].steeringAngleDeg - sm['liveParameters'].angleOffsetDeg
    accel_clip = limit_accel_in_turns(v_ego, steer_angle_without_offset, accel_clip, self.CP)

    if reset_state:
      self.v_desired_filter.x = v_ego
      # Clip aEgo to cruise limits to prevent large accelerations when becoming active
      self.a_desired = np.clip(sm['carState'].aEgo, accel_clip[0], accel_clip[1])

    # Prevent divergence, smooth in current v_ego
    self.v_desired_filter.x = max(0.0, self.v_desired_filter.update(v_ego))
    personality = sm['selfdriveState'].personality
    if dp_flags & DPFlags.APM:
      personality = self.apm.get_personality(v_ego, personality)

    _, _, _, _, throttle_prob = self.parse_model(sm['modelV2'])
    # The model can request coasting despite a large cruise deficit. Permit ACC to
    # pursue the set speed after a stable clear path; MPC and turn limits still apply.
    path_clear = path_clear_for_throttle(v_ego, sm['radarState'], get_T_FOLLOW(personality), COMFORT_BRAKE, STOP_DISTANCE)
    lead_present = sm['radarState'].leadOne.status or sm['radarState'].leadTwo.status
    cruise_gap = v_cruise - v_ego if v_cruise_initialized and not force_slow_decel else 0.0
    model_allows = throttle_prob > ALLOW_THROTTLE_THRESHOLD or v_ego <= MIN_ALLOW_THROTTLE_SPEED
    radar_valid = sm.valid['radarState'] if hasattr(sm, 'valid') else True  # synthetic maneuver tests use a dict
    model_safe_to_override = model_allows_override(sm['modelV2'].action.desiredAcceleration,
                                                   sm['modelV2'].action.shouldStop,
                                                   sm['modelV2'].meta.hardBrakePredicted)
    self.allow_throttle = self.throttle_gate.update(model_allows, cruise_gap, path_clear,
                                                    not reset_state and not sm['selfdriveState'].experimentalMode and radar_valid and model_safe_to_override and
                                                    grade_allows_override(sm['carControl'].orientationNED),
                                                    self.dt, lead_present, personality)

    if not self.allow_throttle:
      clipped_accel_coast = max(accel_coast, accel_clip[0])
      clipped_accel_coast_interp = np.interp(v_ego, [MIN_ALLOW_THROTTLE_SPEED, MIN_ALLOW_THROTTLE_SPEED*2], [accel_clip[1], clipped_accel_coast])
      accel_clip[1] = min(accel_clip[1], clipped_accel_coast_interp)

    if force_slow_decel:
      v_cruise = 0.0

    self.mpc.set_weights(prev_accel_constraint, personality=personality)
    self.mpc.set_cur_state(self.v_desired_filter.x, self.a_desired)
    self.mpc.update(sm['radarState'], v_cruise, personality=personality)

    self.v_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.v_solution)
    self.a_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.a_solution)
    # ACM - Adaptive Coasting Module
    if dp_flags & DPFlags.ACM:
      user_control = long_control_off if self.CP.openpilotLongitudinalControl else not sm['selfdriveState'].enabled
      self.acm.update_states(sm['carControl'], sm['radarState'], user_control, v_ego, v_cruise)
      self.a_desired_trajectory = self.acm.update_a_desired_trajectory(self.a_desired_trajectory)
    self.j_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC[:-1], self.mpc.j_solution)

    # TODO counter is only needed because radar is glitchy, remove once radar is gone
    self.fcw = self.mpc.crash_cnt > 2 and not sm['carState'].standstill
    if self.fcw:
      cloudlog.info("FCW triggered")

    # Interpolate 0.05 seconds and save as starting point for next iteration
    a_prev = self.a_desired
    self.a_desired = float(np.interp(self.dt, CONTROL_N_T_IDX, self.a_desired_trajectory))
    self.v_desired_filter.x = self.v_desired_filter.x + self.dt * (self.a_desired + a_prev) / 2.0

    action_t =  self.CP.longitudinalActuatorDelay + DT_MDL
    output_a_target_mpc, output_should_stop_mpc = get_accel_from_plan(self.v_desired_trajectory, self.a_desired_trajectory, CONTROL_N_T_IDX,
                                                                        action_t=action_t, vEgoStopping=self.CP.vEgoStopping)
    output_a_target_e2e = sm['modelV2'].action.desiredAcceleration
    output_should_stop_e2e = sm['modelV2'].action.shouldStop

    raw_mpc_source = str(self.mpc.source)
    mode = 'blended' if sm['selfdriveState'].experimentalMode else 'acc'
    if dp_flags & DPFlags.AEM:
      self.aem.update_states(model_msg=sm['modelV2'], radar_msg=sm['radarState'], v_ego=sm['carState'].vEgo)
      mode = self.aem.get_mode(mode)

    if mode == 'blended':
      output_a_target = min(output_a_target_e2e, output_a_target_mpc)
      self.output_should_stop = output_should_stop_e2e or output_should_stop_mpc
      if output_a_target < output_a_target_mpc:
        self.mpc.source = LongitudinalPlanSource.e2e
    else:
      output_a_target = output_a_target_mpc
      self.output_should_stop = output_should_stop_mpc

    previous_clip = list(self.prev_accel_clip)
    for idx in range(2):
      accel_clip[idx] = np.clip(accel_clip[idx], self.prev_accel_clip[idx] - 0.05, self.prev_accel_clip[idx] + 0.05)
    self.output_a_target = np.clip(output_a_target, accel_clip[0], accel_clip[1])
    self.prev_accel_clip = accel_clip
    trace_time = sm.logMonoTime['modelV2'] / 1e9 if hasattr(sm, 'logMonoTime') else 0.
    pitch = sm['carControl'].orientationNED[1] if len(sm['carControl'].orientationNED)==3 else None
    grade_age = ((sm.logMonoTime['modelV2']-sm.logMonoTime['carControl'])/1e9
                 if hasattr(sm, 'logMonoTime') else None)
    throttle_reason = ('model_allows' if model_allows else 'recovery_override' if self.throttle_gate.override_active
                       else 'coast_gate')
    self.diagnostic_trace = dict(t=trace_time, e2e=output_a_target_e2e, mpc=output_a_target_mpc,
      raw_mpc_source=raw_mpc_source, selected_source=str(self.mpc.source), pre_clip=float(output_a_target), post_clip=float(self.output_a_target),
      prev_accel_clip=previous_clip, accel_limits=list(accel_clip), cruise_max=float(get_max_accel(v_ego)),
      turn_max=float(limit_accel_in_turns(v_ego,steer_angle_without_offset,[ACCEL_MIN,ACCEL_MAX],self.CP)[1]),
      throttle_reason=throttle_reason, allowThrottle=self.allow_throttle, gasPressProb=float(throttle_prob),
      model_allows=model_allows, override_active=self.throttle_gate.override_active,
      model_safe_to_override=model_safe_to_override, grade_allows=grade_allows_override(sm['carControl'].orientationNED),
      pitch=pitch, grade_age_s=grade_age, grade_fresh=grade_age is not None and 0<=grade_age<=0.2,
      cruise_gap=float(v_cruise-v_ego), vCruise=float(v_cruise_kph), vEgo=float(v_ego), aEgo=float(sm['carState'].aEgo),
      lead1=sm['radarState'].leadOne.to_dict(), lead2=sm['radarState'].leadTwo.to_dict(),
      mode=mode, personality=str(personality), shouldStop=self.output_should_stop, fcw=self.fcw,
      desired_curvature=float(sm['controlsState'].desiredCurvature), actual_curvature=float(sm['controlsState'].curvature),
      requested_torque=float(sm['carControl'].actuators.torque), steering_torque_eps=float(sm['carState'].steeringTorqueEps),
      latActive=bool(sm['carControl'].latActive), lane_change_state=str(sm['modelV2'].meta.laneChangeState),
      model_path_x=list(sm['modelV2'].position.x), model_path_y=list(sm['modelV2'].position.y),
      reset=reset_state, a_desired=float(self.a_desired), solver_status=int(self.mpc.solution_status))
    if self.overshoot_event.update(trace_time,v_ego*3.6,v_cruise_kph,not reset_state):
      self.diagnostic_trace['event_type']='OVERSHOOT_EVENT'
      cloudlog.event('OVERSHOOT_EVENT', **self.diagnostic_trace)
    # Experimental intervention occurs after the baseline target and trace inputs.
    # A disabled switch is exact identity; no shouldStop, FCW or solver state writes.
    velocities = sm['modelV2'].velocity.x
    enabled_stop = self.v33_params.get_bool('dp_exp_early_stop')
    valid_stop = (hasattr(sm, 'valid') and sm.valid['modelV2'] and sm.valid['carState']
                  and len(velocities) == ModelConstants.IDX_N)
    stop_row = self.v33_stop.update(EarlyStopInputs(
      t=trace_time, v0=float(velocities[0]) if len(velocities) else 0.,
      endpoint=float(velocities[-1]) if len(velocities) else 0.,
      desired=float(output_a_target_e2e), base=float(self.output_a_target),
      experimental=mode == 'blended', valid=bool(valid_stop), engaged=not reset_state,
      should_stop=bool(self.output_should_stop), mpc_stop=bool(output_should_stop_mpc),
      standstill=bool(sm['carState'].standstill),
      driver_override=bool(sm['carState'].brakePressed or sm['carState'].gasPressed),
      fcw=bool(self.fcw), hard_brake=bool(sm['modelV2'].meta.hardBrakePredicted),
      lead_present=bool(lead_present)), enabled_stop)
    self.output_a_target = max(float(accel_clip[0]), stop_row['after'])
    stop_row.update(feature='early_stop', enabled=enabled_stop, t=trace_time,
      vEgo=float(v_ego), vCruise=float(v_cruise_kph),
      aTarget_before=stop_row['before'], aTarget_after=float(self.output_a_target),
      lead=self.diagnostic_trace['lead1'], stop_intent=bool(self.output_should_stop),
      FCW=bool(self.fcw), personality=str(personality), pitch=pitch,
      lateral_state=self.diagnostic_trace['lane_change_state'])
    self.diagnostic_trace.setdefault('experiments', {})['stop'] = stop_row
    self.diagnostic_trace['post_clip'] = float(self.output_a_target)
    self.v33_log_frame += 1
    transition = (enabled_stop, stop_row['state'], stop_row['reason'])
    if transition != self.v33_last_reason or (enabled_stop and self.v33_log_frame % 10 == 0):
      cloudlog.event('MYCRV_EXPERIMENTAL', **stop_row)
    self.v33_last_reason = transition
    enabled_restart = self.v33_params.get_bool('dp_exp_restart')
    lead = sm['radarState'].leadOne
    second = sm['radarState'].leadTwo
    restart_lead = dict(d=float(lead.dRel), vr=float(lead.vRel), y=float(lead.yRel), prob=float(lead.modelProb)) if lead.status else None
    valid_restart = (hasattr(sm, 'valid') and all(sm.valid[k] for k in ('modelV2', 'radarState', 'carState')))
    path = list(sm['modelV2'].position.y)
    personality_name = {0: 'aggressive', 1: 'standard', 2: 'relaxed'}.get(personality.raw if hasattr(personality, 'raw') else int(personality), 'relaxed')
    restart_row = self.v33_restart.update(t=trace_time, enabled=enabled_restart,
      active=not reset_state, speed=float(v_ego), base_stop=bool(self.output_should_stop or output_should_stop_e2e or output_should_stop_mpc),
      lead=restart_lead, path_valid=bool(valid_restart and len(path) == ModelConstants.IDX_N and all(math.isfinite(x) for x in path)),
      fcw=bool(self.fcw), hard_brake=bool(sm['modelV2'].meta.hardBrakePredicted),
      driver_brake=bool(sm['carState'].brakePressed or sm['carState'].gasPressed),
      new_closer=bool(second.status and (not lead.status or second.dRel < lead.dRel - .5)),
      personality=personality_name)
    # Interlock may add HOLD. It never clears the existing stop request or forces throttle.
    before_restart = float(self.output_a_target)
    if enabled_restart:
      self.output_should_stop = self.output_should_stop or restart_row['should_stop']
      if restart_row['active']:
        self.output_a_target = min(0., self.output_a_target)
    restart_row.update(feature='restart', t=trace_time, enabled=enabled_restart,
      vEgo=float(v_ego), vCruise=float(v_cruise_kph), aTarget_before=before_restart,
      aTarget_after=float(self.output_a_target), lead=restart_lead, stop_intent=bool(self.output_should_stop),
      FCW=bool(self.fcw), personality=personality_name, pitch=pitch,
      lateral_state=self.diagnostic_trace['lane_change_state'])
    self.diagnostic_trace.setdefault('experiments', {})['restart'] = restart_row
    self.diagnostic_trace['post_clip'] = float(self.output_a_target)
    self.diagnostic_trace['shouldStop'] = bool(self.output_should_stop)
    self.v33_restart_frame += 1
    transition = (enabled_restart, restart_row['state'], restart_row['reason'])
    if transition != self.v33_restart_previous or (enabled_restart and self.v33_restart_frame % 10 == 0):
      cloudlog.event('MYCRV_EXPERIMENTAL', **restart_row)
    self.v33_restart_previous = transition
    enabled_ramp = self.v33_params.get_bool('dp_exp_ramp')
    leads = (sm['radarState'].leadOne, sm['radarState'].leadTwo)
    closing_ramp = any(l.status and (l.vRel < -0.1 or l.dRel < max(10., v_ego * get_T_FOLLOW(personality))) for l in leads)
    path_values = list(sm['modelV2'].position.x) + list(sm['modelV2'].position.y)
    valid_ramp = (hasattr(sm, 'valid') and all(sm.valid[k] for k in ('modelV2', 'radarState', 'carState', 'carControl')))
    ramp_row = self.v33_ramp.update(t=trace_time, enabled=enabled_ramp,
      base=float(self.output_a_target), e2e=float(output_a_target_e2e), mpc=float(output_a_target_mpc),
      mode=mode, valid=bool(valid_ramp), active=not reset_state, closing=closing_ramp,
      stop=bool(self.output_should_stop or output_should_stop_e2e or output_should_stop_mpc),
      fcw=bool(self.fcw), hard_brake=bool(sm['modelV2'].meta.hardBrakePredicted),
      path_valid=len(path_values) == ModelConstants.IDX_N * 2 and all(math.isfinite(x) for x in path_values),
      pitch=pitch, grade_age=grade_age, allow_throttle=bool(self.allow_throttle),
      driver_override=bool(sm['carState'].brakePressed or sm['carState'].gasPressed or force_slow_decel),
      cruise_gap=float(v_cruise - v_ego), accel_max=float(accel_clip[1]))
    self.output_a_target = ramp_row['after']
    ramp_row.update(feature='ramp', t=trace_time, enabled=enabled_ramp, vEgo=float(v_ego),
      vCruise=float(v_cruise_kph), aTarget_before=ramp_row['before'], aTarget_after=ramp_row['after'],
      lead=[l.to_dict() for l in leads], stop_intent=bool(self.output_should_stop), FCW=bool(self.fcw),
      personality=str(personality), pitch=pitch, lateral_state=self.diagnostic_trace['lane_change_state'],
      closing=closing_ramp, e2e=float(output_a_target_e2e), mpc=float(output_a_target_mpc))
    self.diagnostic_trace.setdefault('experiments', {})['ramp'] = ramp_row
    self.diagnostic_trace['post_clip'] = float(self.output_a_target)
    self.v33_ramp_frame += 1
    transition = (enabled_ramp, ramp_row['active'], ramp_row['reason'])
    if transition != self.v33_ramp_previous or (enabled_ramp and self.v33_ramp_frame % 10 == 0):
      cloudlog.event('MYCRV_EXPERIMENTAL', **ramp_row)
    self.v33_ramp_previous = transition
    enabled_personality = self.v33_params.get_bool('dp_exp_personality')
    valid_personality = (hasattr(sm, 'valid') and all(sm.valid[k] for k in ('modelV2', 'radarState', 'carState', 'carControl')))
    personality_path = list(sm['modelV2'].position.x) + list(sm['modelV2'].position.y)
    valid_personality = valid_personality and len(personality_path) == ModelConstants.IDX_N * 2 and all(math.isfinite(x) for x in personality_path)
    personality_name = {0: 'aggressive', 1: 'standard', 2: 'relaxed'}.get(personality.raw if hasattr(personality, 'raw') else int(personality), 'standard')
    personality_row = self.v33_personality.update(t=trace_time, enabled=enabled_personality,
      personality=personality_name, base=float(self.output_a_target), raw_mpc=float(output_a_target_mpc),
      cruise_cap=float(get_max_accel(v_ego)), turn_cap=self.diagnostic_trace['turn_max'], physical_cap=float(ACCEL_MAX),
      valid=bool(valid_personality and grade_age is not None and 0 <= grade_age <= .2 and grade_allows_override(sm['carControl'].orientationNED)),
      active=not reset_state, mode=mode, lead=bool(lead_present),
      stop=bool(self.output_should_stop or output_should_stop_e2e or output_should_stop_mpc),
      fcw=bool(self.fcw), hard_brake=bool(sm['modelV2'].meta.hardBrakePredicted),
      model_accel=float(output_a_target_e2e), override=bool(sm['carState'].brakePressed or sm['carState'].gasPressed or force_slow_decel),
      allow_throttle=bool(self.allow_throttle and model_allows), gap=float(v_cruise - v_ego))
    self.output_a_target = personality_row['after']
    personality_row.update(feature='personality', t=trace_time, enabled=enabled_personality,
      vEgo=float(v_ego), vCruise=float(v_cruise_kph), aTarget_before=personality_row['before'],
      aTarget_after=personality_row['after'], lead=self.diagnostic_trace['lead1'],
      stop_intent=bool(self.output_should_stop), FCW=bool(self.fcw), pitch=pitch,
      lateral_state=self.diagnostic_trace['lane_change_state'])
    self.diagnostic_trace.setdefault('experiments', {})['personality'] = personality_row
    self.diagnostic_trace['post_clip'] = float(self.output_a_target)
    self.v33_personality_frame += 1
    transition = (enabled_personality, personality_row['active'], personality_row['reason'])
    if transition != self.v33_personality_previous or (enabled_personality and self.v33_personality_frame % 10 == 0):
      cloudlog.event('MYCRV_EXPERIMENTAL', **personality_row)
    self.v33_personality_previous = transition
    enabled_overtake = self.v33_params.get_bool('dp_exp_overtake')
    cs = sm['carState']
    direction = ('left' if cs.leftBlinker else 'right') if cs.leftBlinker != cs.rightBlinker else 'none'
    torque = bool(cs.steeringPressed and ((direction == 'left' and cs.steeringTorque > 0) or (direction == 'right' and cs.steeringTorque < 0)))
    valid_overtake = (hasattr(sm, 'valid') and all(sm.valid[k] for k in ('modelV2', 'radarState', 'carState', 'carControl')))
    overtake_row = self.v33_overtake.update(t=trace_time, enabled=enabled_overtake,
      direction=direction, torque=torque, lat_active=bool(sm['carControl'].latActive),
      long_active=bool(sm['carControl'].longActive and not reset_state),
      starting=sm['modelV2'].meta.laneChangeState == log.LaneChangeState.laneChangeStarting,
      base=float(self.output_a_target), mpc=float(output_a_target_mpc), e2e=float(output_a_target_e2e),
      cap=float(accel_clip[1]), gap=float(v_cruise - v_ego),
      envelope_ok=bool(valid_overtake and path_clear and self.allow_throttle and lead_present),
      stop=bool(self.output_should_stop or output_should_stop_e2e or output_should_stop_mpc),
      fcw=bool(self.fcw), hard_brake=bool(sm['modelV2'].meta.hardBrakePredicted),
      override=bool(cs.brakePressed or cs.gasPressed or force_slow_decel))
    self.output_a_target = overtake_row['after']
    overtake_row.update(feature='overtake', t=trace_time, enabled=enabled_overtake,
      vEgo=float(v_ego), vCruise=float(v_cruise_kph), aTarget_before=overtake_row['before'],
      aTarget_after=overtake_row['after'], lead=self.diagnostic_trace['lead1'],
      lead2=self.diagnostic_trace['lead2'], stop_intent=bool(self.output_should_stop), FCW=bool(self.fcw),
      personality=str(personality), pitch=pitch, lateral_state=self.diagnostic_trace['lane_change_state'])
    self.diagnostic_trace.setdefault('experiments', {})['overtake'] = overtake_row
    self.diagnostic_trace['post_clip'] = float(self.output_a_target)
    self.v33_overtake_frame += 1
    transition = (enabled_overtake, overtake_row['stage'], overtake_row['reason'])
    if transition != self.v33_overtake_previous or (enabled_overtake and self.v33_overtake_frame % 10 == 0):
      cloudlog.event('MYCRV_EXPERIMENTAL', **overtake_row)
    self.v33_overtake_previous = transition
    emit_trace(self.diagnostic_trace)

  def publish(self, sm, pm):
    plan_send = messaging.new_message('longitudinalPlan')

    plan_send.valid = sm.all_checks(service_list=['carState', 'controlsState', 'selfdriveState', 'radarState'])

    longitudinalPlan = plan_send.longitudinalPlan
    longitudinalPlan.modelMonoTime = sm.logMonoTime['modelV2']
    longitudinalPlan.processingDelay = (plan_send.logMonoTime / 1e9) - sm.logMonoTime['modelV2']
    longitudinalPlan.solverExecutionTime = self.mpc.solve_time

    longitudinalPlan.speeds = self.v_desired_trajectory.tolist()
    longitudinalPlan.accels = self.a_desired_trajectory.tolist()
    longitudinalPlan.jerks = self.j_desired_trajectory.tolist()

    longitudinalPlan.hasLead = sm['radarState'].leadOne.status
    longitudinalPlan.longitudinalPlanSource = self.mpc.source
    longitudinalPlan.fcw = self.fcw

    longitudinalPlan.aTarget = float(self.output_a_target)
    longitudinalPlan.shouldStop = bool(self.output_should_stop)
    longitudinalPlan.allowBrake = True
    longitudinalPlan.allowThrottle = bool(self.allow_throttle)

    pm.send('longitudinalPlan', plan_send)
