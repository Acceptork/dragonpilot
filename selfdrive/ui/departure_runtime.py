"""Sound/UI-only adapter. Never publishes vehicle or planner messages."""
import json
import math
from openpilot.selfdrive.ui.departure_alert import DepartureAlerts, Observation
from openpilot.common.swaglog import cloudlog

CUE_KEY = 'dp_departure_alert_cue'


class DepartureRuntime:
  def __init__(self, params):
    self.params = params
    self.machine = DepartureAlerts()
    self.was_onroad = False
    self.cue_expires_at = 0.

  def update(self, sm, now):
    onroad = bool(sm.valid['deviceState'] and sm['deviceState'].started
                  and 0 <= now-sm.recv_time['deviceState'] < 2.)
    if not onroad:
      if self.was_onroad:
        # An offroad/freshness interruption must not re-arm the same stop.
        self.machine.reset_tracking()
        self.machine.moving_since = None
        self.params.put_nonblocking(CUE_KEY, '')
      self.was_onroad = False
      self.cue_expires_at = 0.
      return None
    self.was_onroad = True
    cs, md, radar = sm['carState'], sm['modelV2'], sm['radarState']
    valid = cs.canValid and all(sm.valid[k] and 0<=now-sm.recv_time[k]<=.25 for k in ('carState','modelV2','radarState'))
    lead = dict(d=float(radar.leadOne.dRel),vr=float(radar.leadOne.vRel),y=float(radar.leadOne.yRel),
                prob=float(radar.leadOne.modelProb)) if radar.leadOne.status else None
    velocity = md.velocity.x
    observation = Observation(t=now,onroad=onroad,valid=bool(valid),gear=str(cs.gearShifter),
      speed=float(cs.vEgo),gas=bool(cs.gasPressed),lead=lead,
      endpoint=float(velocity[-1]) if len(velocity)==33 else float('nan'),
      desired_accel=float(md.action.desiredAcceleration),model_stop=bool(md.action.shouldStop),
      hazard=bool(md.meta.hardBrakePredicted or radar.leadOne.fcw or radar.leadTwo.fcw),
      closer_obstacle=bool(radar.leadTwo.status and (lead is None or radar.leadTwo.dRel<lead['d']-.5)))
    if self.cue_expires_at and (now>=self.cue_expires_at or not valid or observation.speed>.2
                               or observation.gas or observation.hazard or observation.closer_obstacle):
      self.params.put_nonblocking(CUE_KEY, '')
      self.cue_expires_at = 0.
    previous_state = self.machine.state
    lead_enabled = self.params.get_bool('dp_departure_lead_alert')
    signal_enabled = self.params.get_bool('dp_departure_signal_alert')
    if not sm.updated['modelV2']:
      # Revalidate pending cues on every caller frame, but never advance evidence on a reused model frame.
      pending = self.machine.pending_kind
      invalid = (not valid or observation.gear != 'drive' or observation.speed > .2
                 or observation.gas or observation.hazard or observation.closer_obstacle
                 or not all(math.isfinite(v) for v in (observation.speed, observation.endpoint, observation.desired_accel)))
      if pending:
        invalid = invalid or observation.model_stop or observation.speed-self.machine.pending_speed >= .1
        if pending == 'lead_departure':
          previous = self.machine.lead_previous
          invalid = invalid or not lead_enabled or lead is None or previous is None
          if lead is not None and previous is not None:
            invalid = invalid or (not all(math.isfinite(v) for v in lead.values()) or not .8 <= lead['prob'] <= 1.
              or not 2. <= lead['d'] <= 45. or abs(lead['y']) >= 1.
              or not .3 < lead['vr']+observation.speed < 8.
              or abs(lead['d']-previous['d']) > .6 or abs(lead['y']-previous['y']) >= .4)
        else:
          invalid = invalid or not signal_enabled or lead is not None or observation.endpoint <= 3. or observation.desired_accel <= .15
      if invalid:
        self.machine.reset_tracking()
        self.machine.moving_since = None
      event = None
    else:
      event = self.machine.update(observation, lead_enabled, signal_enabled)
    if self.machine.state != previous_state:
      cloudlog.event('MYCRV_DEPARTURE_STATE', previous=previous_state, state=self.machine.state,
                     pending_kind=self.machine.pending_kind, confirmed_at=self.machine.pending_since,
                     vEgo=observation.speed, gas=observation.gas, valid=observation.valid,
                     hazard=observation.hazard, closer_obstacle=observation.closer_obstacle,
                     gear=observation.gear, control_effect='NONE')
    if event:
      self.cue_expires_at = event['expires_at']
      self.params.put_nonblocking(CUE_KEY, json.dumps(event,ensure_ascii=False))
      cloudlog.event('MYCRV_DEPARTURE_ALERT', **event, vEgo=observation.speed, lead=lead,
                     gear=observation.gear, independent_of_engagement=True)
    return event


def current_cue(params, now, onroad):
  if not onroad:
    return None
  try:
    event=json.loads(params.get(CUE_KEY) or '{}')
    if not 0 <= now-event['issued_at'] < 3. or now>=event['expires_at']:
      return None
    key={'lead_departure':'dp_departure_lead_alert','possible_proceed':'dp_departure_signal_alert'}[event['kind']]
    if not params.get_bool(key):
      return None
    # Fixed UI text, never trust an arbitrary persisted string as a notification.
    return '前車已起步' if event['kind']=='lead_departure' else '前方可能已可通行'
  except (ValueError,TypeError,KeyError):
    return None
