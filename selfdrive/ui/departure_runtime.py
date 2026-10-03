"""Sound/UI-only adapter. Never publishes vehicle or planner messages."""
import json
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
        self.machine = DepartureAlerts()
        self.params.put_nonblocking(CUE_KEY, '')
      self.was_onroad = False
      self.cue_expires_at = 0.
      return None
    self.was_onroad = True
    if not sm.updated['modelV2']:
      return None
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
    event = self.machine.update(observation, self.params.get_bool('dp_departure_lead_alert'),
                                self.params.get_bool('dp_departure_signal_alert'))
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
