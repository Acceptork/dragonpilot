#!/usr/bin/env python3
import math
from openpilot.selfdrive.controls.lib.taper_v33 import StopTaper
from openpilot.selfdrive.controls.lib.eps_shadow_v33 import EpsShadow
from numbers import Number

from cereal import car, log
import cereal.messaging as messaging
from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process, DT_CTRL, Priority, Ratekeeper
from openpilot.common.swaglog import cloudlog

from opendbc.car.car_helpers import interfaces
from opendbc.car.vehicle_model import VehicleModel
from opendbc.safety import ALTERNATIVE_EXPERIENCE
from openpilot.selfdrive.controls.lib.drive_helpers import clip_curvature
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.selfdrive.controls.lib.latcontrol_pid import LatControlPID
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle, STEER_ANGLE_SATURATION_THRESHOLD
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.selfdrive.modeld.modeld import LAT_SMOOTH_SECONDS
from openpilot.selfdrive.locationd.helpers import PoseCalibrator, Pose

State = log.SelfdriveState.OpenpilotState
LaneChangeState = log.LaneChangeState
LaneChangeDirection = log.LaneChangeDirection

ACTUATOR_FIELDS = tuple(car.CarControl.Actuators.schema.fields.keys())


class Controls:
  def __init__(self) -> None:
    self.params = Params()
    cloudlog.info("controlsd is waiting for CarParams")
    self.CP = messaging.log_from_bytes(self.params.get("CarParams", block=True), car.CarParams)
    cloudlog.info("controlsd got CarParams")

    self.CI = interfaces[self.CP.carFingerprint](self.CP)

    self.sm = messaging.SubMaster(['liveDelay', 'liveParameters', 'liveTorqueParameters', 'modelV2', 'selfdriveState',
                                   'liveCalibration', 'livePose', 'longitudinalPlan', 'lateralManeuverPlan', 'carState', 'carOutput',
                                   'driverMonitoringState', 'onroadEvents', 'driverAssistance', 'carStateExt'], poll='selfdriveState')
    self.pm = messaging.PubMaster(['carControl', 'controlsState', 'controlsStateExt'])

    self.steer_limited_by_safety = False
    self.curvature = 0.0
    self.desired_curvature = 0.0

    self.pose_calibrator = PoseCalibrator()
    self.calibrated_pose: Pose | None = None

    self.v33_taper = StopTaper()
    self.v33_taper_frame = 0
    self.v33_taper_previous = None
    self.v33_eps = EpsShadow()
    self.v33_lca_context_active = False
    self.v33_lca_context_enter = self.v33_lca_context_exit = None
    self.v33_lca_context_previous = None
    self.v33_lca_context_frame = 0
    self.LoC = LongControl(self.CP)
    self.VM = VehicleModel(self.CP)
    self.LaC: LatControl
    if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
      self.LaC = LatControlAngle(self.CP, self.CI, DT_CTRL)
    elif self.CP.lateralTuning.which() == 'pid':
      self.LaC = LatControlPID(self.CP, self.CI, DT_CTRL)
    elif self.CP.lateralTuning.which() == 'torque':
      self.LaC = LatControlTorque(self.CP, self.CI, DT_CTRL)

    # dp - ALKA: cache enabled state (CP doesn't change after init)
    self.alka_enabled = bool(self.CP.alternativeExperience & ALTERNATIVE_EXPERIENCE.ALKA)
    self.alka_active = False

  def update(self):
    self.sm.update(15)
    if self.sm.updated["liveCalibration"]:
      self.pose_calibrator.feed_live_calib(self.sm['liveCalibration'])
    if self.sm.updated["livePose"]:
      device_pose = Pose.from_live_pose(self.sm['livePose'])
      self.calibrated_pose = self.pose_calibrator.build_calibrated_pose(device_pose)

  def state_control(self):
    CS = self.sm['carState']

    # Update VehicleModel
    lp = self.sm['liveParameters']
    x = max(lp.stiffnessFactor, 0.1)
    sr = max(lp.steerRatio, 0.1)
    self.VM.update_params(x, sr)

    steer_angle_without_offset = math.radians(CS.steeringAngleDeg - lp.angleOffsetDeg)
    self.curvature = -self.VM.calc_curvature(steer_angle_without_offset, CS.vEgo, lp.roll)

    # Update Torque Params
    if self.CP.lateralTuning.which() == 'torque':
      torque_params = self.sm['liveTorqueParameters']
      if self.sm.all_checks(['liveTorqueParameters']) and torque_params.useParams:
        self.LaC.update_live_torque_params(torque_params.latAccelFactorFiltered, torque_params.latAccelOffsetFiltered,
                                           torque_params.frictionCoefficientFiltered)

    long_plan = self.sm['longitudinalPlan']
    model_v2 = self.sm['modelV2']

    CC = car.CarControl.new_message()
    CC.enabled = self.sm['selfdriveState'].enabled

    # Check which actuators can be enabled
    standstill = abs(CS.vEgo) <= max(self.CP.minSteerSpeed, 0.3) or CS.standstill
    # dp - ALKA: check conditions (alka_enabled is cached in __init__)
    if self.alka_enabled:
      # Read lkas_on state from carstate (published via carStateExt)
      lkas_on = self.sm['carStateExt'].lkasOn
      # Conditions: lkas_on, gear not in P/N/R, calibration complete, seatbelt latched, doors closed
      calibrated = self.sm['liveCalibration'].calStatus == log.LiveCalibrationData.Status.calibrated
      gear_ok = CS.gearShifter not in (car.CarState.GearShifter.park, car.CarState.GearShifter.neutral, car.CarState.GearShifter.reverse)
      self.alka_active = lkas_on and gear_ok and calibrated and not CS.seatbeltUnlatched and not CS.doorOpen
    CC.latActive = (self.sm['selfdriveState'].active or self.alka_active) and not CS.steerFaultTemporary and not CS.steerFaultPermanent and \
                   (not standstill or self.CP.steerAtStandstill)
    CC.longActive = CC.enabled and not any(e.overrideLongitudinal for e in self.sm['onroadEvents']) and self.CP.openpilotLongitudinalControl

    actuators = CC.actuators
    actuators.longControlState = self.LoC.long_control_state

    # Enable blinkers while lane changing
    if model_v2.meta.laneChangeState != LaneChangeState.off:
      CC.leftBlinker = model_v2.meta.laneChangeDirection == LaneChangeDirection.left
      CC.rightBlinker = model_v2.meta.laneChangeDirection == LaneChangeDirection.right

    if not CC.latActive:
      self.LaC.reset()
    if not CC.longActive:
      self.LoC.reset()

    # accel PID loop
    pid_accel_limits = self.CI.get_pid_accel_limits(self.CP, CS.vEgo, CS.vCruise * CV.KPH_TO_MS)
    actuators.accel = float(self.LoC.update(CC.longActive, CS, long_plan.aTarget, long_plan.shouldStop, pid_accel_limits))
    enabled_taper = self.params.get_bool('dp_exp_taper')
    taper_time = self.sm.logMonoTime['carState'] / 1e9
    grade_age = (self.sm.logMonoTime['carState'] - self.sm.logMonoTime['livePose']) / 1e9
    pitch = float(self.calibrated_pose.orientation.xyz[1]) if self.calibrated_pose is not None else None
    measured_reserve = None
    for lead in model_v2.leadsV3:
      if lead.prob > .8 and len(lead.x) and len(lead.y) and abs(lead.y[0]) < 1.:
        distance = float(lead.x[0]) - 6.
        measured_reserve = distance if measured_reserve is None else min(measured_reserve, distance)
    taper_row = self.v33_taper.update(speed=float(CS.vEgo), base=float(actuators.accel),
      pitch=pitch, grade_fresh=bool(self.sm.valid['livePose'] and 0 <= grade_age <= .2),
      stop=bool(long_plan.shouldStop), enabled=enabled_taper, active=bool(CC.longActive and CS.vEgo < 2.),
      danger=bool(long_plan.fcw or model_v2.meta.hardBrakePredicted or long_plan.aTarget < -1.5),
      driver_override=bool(CS.brakePressed or CS.gasPressed), remaining=measured_reserve,
      dt=DT_CTRL, lower=float(pid_accel_limits[0]))
    actuators.accel = float(taper_row['after'])
    taper_row.update(feature='taper', t=taper_time, enabled=enabled_taper,
      vEgo=float(CS.vEgo), vCruise=float(CS.vCruise), aTarget_before=float(long_plan.aTarget),
      aTarget_after=float(long_plan.aTarget), actuator_before=taper_row['before'], actuator_after=taper_row['after'],
      lead_reserve=measured_reserve, stop_intent=bool(long_plan.shouldStop), FCW=bool(long_plan.fcw),
      personality=str(self.sm['selfdriveState'].personality), pitch=pitch, grade_age=grade_age,
      lateral_state=str(model_v2.meta.laneChangeState), signed_speed_available=False)
    self.v33_taper_frame += 1
    transition = (enabled_taper, taper_row['state'], taper_row['reason'])
    if transition != self.v33_taper_previous or (enabled_taper and self.v33_taper_frame % 10 == 0):
      cloudlog.event('MYCRV_EXPERIMENTAL', **taper_row)
    self.v33_taper_previous = transition


    # Steering PID loop and lateral MPC
    # Reset desired curvature to current to avoid violating the limits on engage
    if self.sm.valid['lateralManeuverPlan']:
      new_desired_curvature = self.sm['lateralManeuverPlan'].desiredCurvature if CC.latActive else self.curvature
    else:
      new_desired_curvature = model_v2.action.desiredCurvature if CC.latActive else self.curvature
    self.desired_curvature, curvature_limited = clip_curvature(CS.vEgo, self.desired_curvature, new_desired_curvature, lp.roll)
    lat_delay = self.sm["liveDelay"].lateralDelay + LAT_SMOOTH_SECONDS

    actuators.curvature = self.desired_curvature
    steer, steeringAngleDeg, lac_log = self.LaC.update(CC.latActive, CS, self.VM, lp,
                                                       self.steer_limited_by_safety, self.desired_curvature,
                                                       curvature_limited, lat_delay)
    actuators.torque = float(steer)
    actuators.steeringAngleDeg = float(steeringAngleDeg)
    # Read-only dataset; absent signals remain absent rather than inferred safe.
    self.v33_eps.update(dict(t=self.sm.logMonoTime['carState'] / 1e9,
      requested_torque=float(actuators.torque),
      applied_torque=float(self.sm['carOutput'].actuatorsOutput.torque),
      applied_valid=bool(self.sm.valid['carOutput']),
      steeringTorqueEps=float(CS.steeringTorqueEps),
      steer_limited_by_safety=bool(self.steer_limited_by_safety),
      desired_curvature=float(self.desired_curvature), actual_curvature=float(self.curvature),
      lateral_error=None, lateral_error_source='not_available_in_current_controlsd_contract',
      rate_limiting=bool(curvature_limited),
      driver_countersteer=bool(CS.steeringPressed and CS.steeringTorque * self.desired_curvature < 0),
      laneChangeFinishing=bool(model_v2.meta.laneChangeState == LaneChangeState.laneChangeFinishing),
      latActive=bool(CC.latActive), vEgo=float(CS.vEgo), vCruise=float(CS.vCruise),
      aTarget_before=float(long_plan.aTarget), aTarget_after=float(long_plan.aTarget),
      stop_intent=bool(long_plan.shouldStop), FCW=bool(long_plan.fcw),
      personality=str(self.sm['selfdriveState'].personality),
      pitch=float(self.calibrated_pose.orientation.xyz[1]) if self.calibrated_pose is not None else None))
    # Read-only context; confirmation/road-edge decisions remain in DesireHelper.
    lca_enabled = self.params.get_bool('dp_exp_lca')
    lca_time = self.sm.logMonoTime['carState'] / 1e9
    lca_state = model_v2.meta.laneChangeState
    lca_active = bool(lca_enabled and CC.latActive and lca_state in
      (LaneChangeState.laneChangeStarting, LaneChangeState.laneChangeFinishing))
    if lca_active != self.v33_lca_context_active:
      if lca_active:
        self.v33_lca_context_enter = lca_time
      else:
        self.v33_lca_context_exit = lca_time
    lca_transition = (lca_enabled, lca_active, str(lca_state))
    self.v33_lca_context_frame += 1
    if lca_transition != self.v33_lca_context_previous or (lca_enabled and self.v33_lca_context_frame % 10 == 0):
      cloudlog.event('MYCRV_EXPERIMENTAL_LCA_CONTEXT', feature='lca', t=lca_time,
        enabled=lca_enabled, active=lca_active, reason=str(lca_state),
        active_basis='model_lane_change_state_and_lateral_authority; see helper confirmation log',
        enter_time=self.v33_lca_context_enter, exit_time=self.v33_lca_context_exit,
        vEgo=float(CS.vEgo), vCruise=float(CS.vCruise),
        aTarget_before=float(long_plan.aTarget), aTarget_after=float(long_plan.aTarget),
        lead=[dict(prob=float(lead.prob), x=list(lead.x), y=list(lead.y)) for lead in model_v2.leadsV3],
        lead_source='modelV2.leadsV3', stop_intent=bool(long_plan.shouldStop), FCW=bool(long_plan.fcw),
        personality=str(self.sm['selfdriveState'].personality),
        pitch=float(self.calibrated_pose.orientation.xyz[1]) if self.calibrated_pose is not None else None,
        lateral_state=str(lca_state), latActive=bool(CC.latActive))
    self.v33_lca_context_active = lca_active
    self.v33_lca_context_previous = lca_transition
    # Ensure no NaNs/Infs
    for p in ACTUATOR_FIELDS:
      attr = getattr(actuators, p)
      if not isinstance(attr, Number):
        continue

      if not math.isfinite(attr):
        cloudlog.error(f"actuators.{p} not finite {actuators.to_dict()}")
        setattr(actuators, p, 0.0)

    return CC, lac_log

  def publish(self, CC, lac_log):
    CS = self.sm['carState']

    # Orientation and angle rates can be useful for carcontroller
    # Only calibrated (car) frame is relevant for the carcontroller
    CC.currentCurvature = self.curvature
    if self.calibrated_pose is not None:
      CC.orientationNED = self.calibrated_pose.orientation.xyz.tolist()
      CC.angularVelocity = self.calibrated_pose.angular_velocity.xyz.tolist()

    CC.cruiseControl.override = CC.enabled and not CC.longActive and self.CP.openpilotLongitudinalControl
    CC.cruiseControl.cancel = CS.cruiseState.enabled and (not CC.enabled or not self.CP.pcmCruise)
    CC.cruiseControl.resume = CC.enabled and CS.cruiseState.standstill and not self.sm['longitudinalPlan'].shouldStop

    hudControl = CC.hudControl
    hudControl.setSpeed = float(CS.vCruiseCluster * CV.KPH_TO_MS)
    hudControl.speedVisible = CC.enabled
    hudControl.lanesVisible = CC.enabled
    hudControl.leadVisible = self.sm['longitudinalPlan'].hasLead
    hudControl.leadDistanceBars = self.sm['selfdriveState'].personality.raw + 1
    hudControl.visualAlert = self.sm['selfdriveState'].alertHudVisual

    hudControl.rightLaneVisible = True
    hudControl.leftLaneVisible = True
    if self.sm.valid['driverAssistance']:
      hudControl.leftLaneDepart = self.sm['driverAssistance'].leftLaneDeparture
      hudControl.rightLaneDepart = self.sm['driverAssistance'].rightLaneDeparture

    if self.sm['selfdriveState'].active:
      CO = self.sm['carOutput']
      if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
        self.steer_limited_by_safety = abs(CC.actuators.steeringAngleDeg - CO.actuatorsOutput.steeringAngleDeg) > \
                                              STEER_ANGLE_SATURATION_THRESHOLD
      else:
        self.steer_limited_by_safety = abs(CC.actuators.torque - CO.actuatorsOutput.torque) > 1e-2

    # TODO: both controlsState and carControl valids should be set by
    #       sm.all_checks(), but this creates a circular dependency

    # controlsState
    dat = messaging.new_message('controlsState')
    dat.valid = CS.canValid
    cs = dat.controlsState

    cs.curvature = self.curvature
    cs.longitudinalPlanMonoTime = self.sm.logMonoTime['longitudinalPlan']
    cs.lateralPlanMonoTime = self.sm.logMonoTime['modelV2']
    cs.desiredCurvature = self.desired_curvature
    cs.longControlState = self.LoC.long_control_state
    cs.upAccelCmd = float(self.LoC.pid.p)
    cs.uiAccelCmd = float(self.LoC.pid.i)
    cs.ufAccelCmd = float(self.LoC.pid.f)
    cs.forceDecel = bool((self.sm['driverMonitoringState'].alertLevel == log.DriverMonitoringState.AlertLevel.three) or
                         (self.sm['selfdriveState'].state == State.softDisabling))

    lat_tuning = self.CP.lateralTuning.which()
    if self.CP.steerControlType == car.CarParams.SteerControlType.angle:
      cs.lateralControlState.angleState = lac_log
    elif lat_tuning == 'pid':
      cs.lateralControlState.pidState = lac_log
    elif lat_tuning == 'torque':
      cs.lateralControlState.torqueState = lac_log

    self.pm.send('controlsState', dat)

    # controlsStateExt
    dat = messaging.new_message('controlsStateExt')
    dat.valid = True
    dat.controlsStateExt.alkaActive = self.alka_active
    self.pm.send('controlsStateExt', dat)

    # carControl
    cc_send = messaging.new_message('carControl')
    cc_send.valid = CS.canValid
    cc_send.carControl = CC
    self.pm.send('carControl', cc_send)

  def run(self):
    rk = Ratekeeper(100, print_delay_threshold=None)
    while True:
      self.update()
      CC, lac_log = self.state_control()
      self.publish(CC, lac_log)
      rk.monitor_time()


def main():
  config_realtime_process(4, Priority.CTRL_HIGH)
  controls = Controls()
  controls.run()


if __name__ == "__main__":
  main()
