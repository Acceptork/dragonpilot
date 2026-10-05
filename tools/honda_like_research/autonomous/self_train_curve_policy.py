"""Offline H2 experiment: VehicleModel-derived current lateral envelope.

No release eligibility is implied. Baseline MPC, selector, memory and stop paths
are preserved. This class is deliberately not imported by production code.
"""
import math
import baseline_planner as baseline

class CurveModelPlanner(baseline.LongitudinalPlanner):
  def update(self, sm, *args, **kwargs):
    original = baseline.limit_accel_in_turns
    t = sm.logMonoTime['modelV2']/1e9
    valid = all(sm.valid.get(k,False) and 0<=t-sm.logMonoTime[k]/1e9<=.2
                for k in ('carState','controlsState','modelV2'))
    curvature = float(sm['controlsState'].curvature)
    def using_vehicle_model(v, angle, limits, cp):
      if not valid or not math.isfinite(curvature):
        return original(v, angle, limits, cp)
      total = 1.7 if v<=20 else 3.2 if v>=40 else 1.7+(v-20)*1.5/20
      ay = abs(curvature)*v*v
      return [limits[0],min(limits[1], math.sqrt(max(total*total-ay*ay,0.)))]
    baseline.limit_accel_in_turns=using_vehicle_model
    try:
      return super().update(sm,*args,**kwargs)
    finally:
      baseline.limit_accel_in_turns=original
