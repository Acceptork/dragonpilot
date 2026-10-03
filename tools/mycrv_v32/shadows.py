"""Offline research only. No planner, radarState, shouldStop or CAN writes."""
from dataclasses import dataclass
import math

@dataclass
class StopIntentShadow:
  endpoint: float=3.
  persistence: float=.3
  ratio: float=.5
  negative: float=-.15
  state: str='NORMAL'
  since: float | None=None
  last_t: float | None=None

  def update(self,t,v0,vend,desired,experimental,valid,confirmed=False,standstill=False):
    timely=self.last_t is None or 0<t-self.last_t<=.075
    self.last_t=t
    if not valid or not experimental or not timely or not all(math.isfinite(v) for v in (t,v0,vend,desired)):
      self.since=None;self.state='NORMAL';return self.state
    if confirmed:
      self.state='HOLD' if standstill else 'STOP_CONFIRMED'
      self.since=None;return self.state
    eligible=vend<self.endpoint and vend<self.ratio*max(v0,0) and desired<self.negative
    if not eligible:self.since=None;self.state='NORMAL'
    else:
      if self.since is None:self.since=t
      self.state='SLOWING_SUSPECT' if t-self.since>=self.persistence-1e-6 else 'NORMAL'
    return self.state

@dataclass
class LeadMemoryShadow:
  horizon: float=.3
  last: dict | None=None

  def update(self,t,lead,path_ok,ego_speed):
    reason='no_memory'
    if lead is not None and lead.get('prob',0)>.5:
      takeover=self.last is not None and lead['d'] < self.last['d']-1.
      if path_ok and lead['prob']>=.8 and 0<lead['d']<=30 and abs(lead['vr'])<30:
        # Continuity is required for persistence across identity hypotheses.
        if self.last is not None:
          age=t-self.last['t'];pred=self.last['d']+self.last['vr']*age
          continuous=0<age<=.15 and abs(lead['d']-pred)<=max(2.,3*lead.get('std',1.)) and abs(lead['vr']-self.last['vr'])<=3.
        else:continuous=False
        self.last={**lead,'t':t,'reliable':continuous}
      else:self.last=None
      return {'active':False,'age':0.,'predicted_dRel':lead['d'],'uncertainty':lead.get('std',0.),'reason':'new_closer_lead_takeover' if takeover else 'measured_lead'}
    if self.last is not None:
      age=t-self.last['t']
      uncertainty=self.last.get('std',1.)+abs(age)*2.+age*age
      predicted=self.last['d']+self.last['vr']*age
      if self.last['reliable'] and path_ok and 0<age<=self.horizon and predicted>0:
        return {'active':True,'age':age,'predicted_dRel':predicted,'uncertainty':uncertainty,'reason':'short_dropout_unknown_not_clear'}
      reason='expired' if age>self.horizon else 'geometry_or_continuity_invalid'
      self.last=None
    return {'active':False,'age':None,'predicted_dRel':None,'uncertainty':None,'reason':reason,'clear_authorized':False}

@dataclass
class RestartResearch:
  persistence: float=.8
  state: str='HOLD'
  since: float | None=None
  origin: float | None=None
  identity: object=None
  previous_position: float | None=None
  previous_t: float | None=None

  def update(self,t,identity,position,noise,stop,hard_brake,path_clear,driver_brake,new_obstacle,personality='standard'):
    dt=t-self.previous_t if self.previous_t is not None else None
    moving=(dt is not None and 0<dt<=.1 and self.previous_position is not None
            and position-self.previous_position>max(.005,noise*.05))
    self.previous_t=t;self.previous_position=position
    if stop or hard_brake or not path_clear or driver_brake or new_obstacle or identity is None or identity!=self.identity:
      self.identity=identity;self.origin=position;self.since=None;self.state='HOLD';return self.state
    if not moving or position-self.origin<=max(.3,3*noise):
      self.since=None;self.state='HOLD';return self.state
    if self.since is None:self.since=t
    extra={'aggressive':0.,'standard':.2,'relaxed':.4}[personality]
    self.state='RELEASE_ALLOWED' if t-self.since>=self.persistence+extra else 'LEAD_MOVING_PENDING'
    return self.state

@dataclass
class StopTaperResearch:
  state: str='APPROACH'
  accel: float=0.
  def update(self,speed,remaining,grade,stop_intent,release,dt=.05):
    # A deliberately restricted plant experiment: measured geometry required.
    if remaining is None or grade is None:return {'state':self.state,'request':None,'blocked':'geometry_or_grade_missing'}
    if self.state=='HOLD':
      if release:self.state='RELEASE_PENDING'
      return {'state':self.state,'request':-2.}
    if stop_intent:
      safe_taper=remaining>speed*speed/(2*.4)+.5 and abs(grade)<.02
      self.state='TAPER' if 0<speed<.8 and safe_taper else 'BRAKING'
      target=-.4 if self.state=='TAPER' else -1.5
      self.accel=max(self.accel-.8*dt,min(target,self.accel+.8*dt))
      if speed<=.02:self.state='HOLD';self.accel=-2.
    return {'state':self.state,'request':self.accel}

@dataclass
class OvertakeResearch:
  state: str='IDLE'
  last_direction: str='none'
  last_torque: bool=False
  armed_at: float | None=None
  confirmation: float | None=None
  request: float=0.
  def update(self,t,direction,torque,starting,long_active,lat_active,gap,lead_valid,margin,clear_verified,
             stop=False,fcw=False,hard_brake=False,brake=False,new_obstacle=False,cap=0.,dt=.05):
    same=direction==self.last_direction and direction!='none'
    fresh=torque and not self.last_torque
    self.last_direction=direction;self.last_torque=torque
    veto=stop or fcw or hard_brake or brake or new_obstacle or not long_active or not lat_active or direction=='none'
    if veto or (self.state not in ('IDLE','ARMED') and not same):
      self.state='IDLE';self.confirmation=None;self.request=0.;return self.result('veto')
    if not same:
      self.state='ARMED';self.armed_at=t;self.confirmation=None;self.request=0.
      return self.result('await_fresh_torque')
    if self.state=='ARMED' and fresh and t>self.armed_at:self.confirmation=t;self.state='CONFIRMED'
    if self.confirmation is None:return self.result('no_confirmation')
    if t-self.confirmation>1.0:
      self.state='IDLE';self.request=0.;self.confirmation=None;return self.result('timeout')
    if gap<10/3.6 or not lead_valid or margin is None or margin<=0 or not starting:
      self.request=0.;return self.result('margin_or_progress_unknown')
    self.state='STAGE2' if clear_verified is True else 'STAGE1'
    ceiling=min(max(0.,cap),max(0.,margin))
    self.request=min(ceiling, self.request+.2*dt) if clear_verified is True else min(ceiling,.1,self.request+.2*dt)
    return self.result('bounded_preference_only')
  def result(self,reason):
    return {'state':self.state,'preaccel_request':self.request,'stage2':'ALLOWED' if self.state=='STAGE2' else 'BLOCKED',
            'reason':reason,'production_actuation':False}

def ramp_research(e2e,mpc,closing,stop,path_reliable,hard_brake,fcw,pitch_valid):
  if not (0<e2e<=.3 and mpc>e2e+.2 and not closing and not stop and path_reliable and not hard_brake and not fcw and pitch_valid):return e2e
  return min(mpc,e2e+.1)  # offline preference only; never imported by planner
