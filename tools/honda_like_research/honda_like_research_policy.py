"""RESEARCH ONLY. Pre-selector e2e envelope proposal, no production wiring.

This does not command CAN, modify MPC outputs, or clear any stop authority.
All thresholds are frozen engineering research bounds, not road-validated tuning.
"""
import math

class RecoveryPolicy:
  def __init__(self, model):
    self.cells={tuple(c['key']):c for c in model['cells'] if c['supported']}
    self.last=None;self.clear=0.;self.had_curve=None;self.had_lead=None;self.lift=0.

  def update(self, *, t, v, cluster, cruise, e2e, mpc, cap, ay, predicted_ay,
             stop, fcw, hard_brake, lead, driver, active, allow, valid, pitch,
             standstill, blinker=False, model_endpoint=0.):
    nums=(t,v,cluster,cruise,e2e,mpc,cap,ay,predicted_ay,pitch,model_endpoint)
    dt=0. if self.last is None else t-self.last
    self.last=t
    finite=all(math.isfinite(x) for x in nums)
    if not finite or not valid or not 0<dt<=.15:
      self.clear=0.;self.lift=0.;self.had_curve=None;self.had_lead=None
      return e2e,'UNKNOWN','invalid_or_discontinuous'
    if ay>=.5 or predicted_ay>=.8:self.had_curve=t
    if lead:self.had_lead=t
    if not active or driver:state='UNKNOWN'
    elif stop:state='STANDSTILL' if standstill else 'STOP_TERMINAL' if v<2. else 'STOP_APPROACH'
    elif standstill:state='STANDSTILL'
    elif hard_brake or fcw:state='UNKNOWN'
    elif ay>=.5 or predicted_ay>=.8:state='CURVE_APPROACH'
    elif blinker:state='OVERTAKE_INTENT'
    elif lead:state='LEAD_FOLLOW'
    elif v<2.:state='RESTART'
    elif self.had_curve is not None and t-self.had_curve<4:state='CURVE_EXIT_RECOVERY'
    elif self.had_lead is not None and t-self.had_lead<4:state='LEAD_CLEAR_RECOVERY'
    else:state='FREE_CRUISE'
    eligible=(state in ('FREE_CRUISE','CURVE_EXIT_RECOVERY','LEAD_CLEAR_RECOVERY') and
              active and not any((driver,stop,fcw,hard_brake,lead,standstill,blinker)) and
              allow and ay<.5 and predicted_ay<.8 and e2e>=0 and mpc>e2e and cap>e2e and
              cruise-cluster*3.6>=5 and model_endpoint>=v-.5 and abs(pitch)<.06)
    if not eligible:
      self.clear=0.;self.lift=0.
      return e2e,state,'authority_or_safety_veto'
    self.clear+=dt
    if self.clear<1.:return e2e,state,'clear_path_dwell'
    key=(int(cluster*3.6//20),int((cruise-cluster*3.6)//5),'up' if pitch>.02 else 'down' if pitch<-.02 else 'flat')
    cell=self.cells.get(key)
    if cell is None:
      self.lift=0.
      return e2e,state,'unsupported_honda_cell'
    goal=min(max(0.,cell['train']['p50']),mpc,cap,e2e+.15)
    self.lift=min(.15,self.lift+.15*dt,max(0.,goal-e2e))
    return e2e+self.lift,state,'supported_preselector_proposal'
