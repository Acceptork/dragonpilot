"""Narrow blended-selector recovery. Research only until all release gates pass.

Model deceleration and downstream safety retain priority. No actuator, following
distance, or MPC objective changes. The Honda reference is descriptive, not a
hard eligibility lookup over sparsely populated cells.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Inputs:
  t: float
  base: float
  e2e: float
  mpc: float
  cap: float
  cruise_cap: float
  turn_cap: float
  v: float
  cluster: float
  cruise: float
  ay: float
  forecast_ay: float
  endpoint: float
  curvature: float
  pitch: float
  valid: bool = True
  active: bool = True
  blended: bool = True
  driver: bool = False
  lead: bool = False
  memory: bool = False
  stop: bool = False
  fcw: bool = False
  hard_brake: bool = False
  allow: bool = True
  path_valid: bool = True
  solver_ok: bool = True


class Recovery:
  def __init__(self):
    self.last_t = None
    self.last_final = None
    self.clear_since = None
    self.curve_at = None
    self.curve_peak = 0.
    self.offset = 0.

  def observe_final(self, target):
    self.last_final = float(target) if math.isfinite(target) else None

  def update(self, x):
    row = dict(state='INACTIVE', reason='veto', active=False, before=x.base,
               after=x.base, ceiling=None, weight=0., deficit_kph=x.cruise-x.cluster*3.6)
    def veto(reason):
      self.clear_since = None
      self.offset = 0.
      row['reason'] = reason
      return row

    numeric = (x.t,x.base,x.e2e,x.mpc,x.cap,x.cruise_cap,x.turn_cap,x.v,
               x.cluster,x.cruise,x.ay,x.forecast_ay,x.endpoint,x.curvature,x.pitch)
    if not all(math.isfinite(n) for n in numeric):
      self.__init__()
      return veto('nonfinite')
    dt = x.t-self.last_t if self.last_t is not None else None
    self.last_t = x.t
    if dt is None or not 0 < dt <= .15:
      self.last_final = None
      self.curve_at = None
      self.curve_peak = 0.
      return veto('initial_or_time_gap')
    if not (x.valid and x.path_valid and x.solver_ok):
      self.curve_at = None
      return veto('invalid_or_stale')
    if not (x.active and x.blended) or x.driver:
      self.curve_at = None
      return veto('ownership_or_driver')
    if x.ay >= .8 or x.turn_cap < x.cruise_cap-.05:
      self.curve_at = x.t
      self.curve_peak = max(self.curve_peak, x.ay)
    recent_curve = self.curve_at is not None and 0 <= x.t-self.curve_at <= 8.
    if not recent_curve:
      self.curve_peak = 0.
    if x.stop or x.e2e < 0 or x.base < 0 or x.endpoint < max(2.,x.v-.5):
      return veto('stop_or_model_deceleration')
    if x.fcw or x.hard_brake or x.lead or x.memory:
      return veto('lead_or_collision_or_memory')
    if not x.allow or abs(x.pitch) > .08:
      return veto('throttle_or_grade')
    if x.ay > .5 or abs(x.curvature) > .005 or x.forecast_ay > .8 or x.turn_cap < x.cruise_cap-.01:
      return veto('curve_or_next_curve')
    gap = row['deficit_kph']
    if x.v < 5 or x.cluster < 5 or not 5 <= gap < 80 or not 0 < x.cruise <= 145:
      return veto('cluster_deficit')
    if x.mpc-x.e2e < .15 or min(x.cap,x.cruise_cap,x.turn_cap,.8) <= x.base:
      return veto('no_selector_headroom')
    if recent_curve and x.ay >= self.curve_peak-.2:
      return veto('curve_not_falling')
    state = 'CURVE_EXIT_RECOVERY' if recent_curve else 'FREE_CRUISE_RECOVERY'
    if self.clear_since is None:
      self.clear_since = x.t
    if x.t-self.clear_since < (.6 if recent_curve else .8):
      row['state'] = 'ARMING_'+state
      row['reason'] = 'clear_path_dwell'
      return row
    weight = min(.65, max(0.,gap/10*.65))
    endpoint = min(x.mpc,x.cap,x.cruise_cap,x.turn_cap,.8)
    desired = max(x.base,(1-weight)*x.e2e+weight*endpoint)
    # Smooth only added authority. Baseline braking is never delayed for jerk.
    self.offset = min(max(0.,desired-x.base),self.offset+.3*dt)
    ceiling = max(x.base,(self.last_final if self.last_final is not None else x.base)+.3*dt)
    after = min(x.base+self.offset,ceiling,endpoint)
    row.update(state=state,reason='bounded_selector_blend',active=after>x.base+1e-9,
               after=after,ceiling=min(ceiling,endpoint),weight=weight)
    return row


def planner_inputs(sm, cp, *, t, base, e2e, mpc, cap, cruise_cap, turn_cap,
                   mode, stop, fcw, allow, solver_ok, memory):
  """Fail closed on missing fields, invalid services, or incomplete trajectories."""
  cs, cc, md = sm['carState'], sm['carControl'], sm['modelV2']
  services = ('carState','carControl','controlsState','selfdriveState','radarState','modelV2','liveParameters')
  fresh = hasattr(sm,'valid') and hasattr(sm,'logMonoTime')
  if fresh:
    fresh = all(sm.valid.get(k,False) and k in sm.logMonoTime and
                0 <= t-sm.logMonoTime[k]/1e9 <= (1.5 if k=='liveParameters' else .2) for k in services)
  vx, px, py, yaw = map(list,(md.velocity.x,md.position.x,md.position.y,md.orientationRate.z))
  path_ok = all(len(a)==33 for a in (vx,px,py,yaw)) and all(math.isfinite(v) for v in vx+px+py+yaw)
  path_ok = path_ok and all(b>=a for a,b in zip(px,px[1:])) and all(v>=0 for v in vx)
  # Model T_IDXS uses quadratic spacing; index 22 spans 4.73 s.
  forecast = max(abs(yaw[i])*max(cs.vEgo,vx[i]) for i in range(23)) if path_ok else math.inf
  leads = (sm['radarState'].leadOne, sm['radarState'].leadTwo)
  lead_valid = all(all(math.isfinite(v) for v in (l.dRel,l.vRel,l.modelProb)) for l in leads)
  return Inputs(t=t,base=float(base),e2e=float(e2e),mpc=float(mpc),cap=float(cap),
    cruise_cap=float(cruise_cap),turn_cap=float(turn_cap),v=float(cs.vEgo),cluster=float(cs.vEgoCluster),
    cruise=float(cs.vCruise),ay=abs(sm['controlsState'].curvature)*cs.vEgo**2,
    forecast_ay=forecast,endpoint=vx[-1] if path_ok else math.nan,
    curvature=float(sm['controlsState'].curvature),pitch=float(cc.orientationNED[1]) if len(cc.orientationNED)==3 else math.nan,
    valid=bool(fresh and cs.canValid and lead_valid),active=bool(cp.openpilotLongitudinalControl and cp.brand=='honda' and cc.longActive and
      sm['selfdriveState'].enabled and str(sm['controlsState'].longControlState)=='pid'),
    blended=mode=='blended',driver=bool(cs.gasPressed or cs.brakePressed or cs.leftBlinker or cs.rightBlinker or sm['controlsState'].forceDecel),
    lead=any(l.status for l in leads),memory=memory,stop=bool(stop or md.action.shouldStop or cs.standstill or (path_ok and min(vx)<2.)),
    fcw=fcw,hard_brake=bool(md.meta.hardBrakePredicted),allow=allow,path_valid=path_ok,solver_ok=solver_ok)
