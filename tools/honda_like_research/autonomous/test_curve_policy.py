import math
from types import SimpleNamespace
import pytest
import baseline_planner as baseline
from self_train_curve_policy import CurveModelPlanner

class SM(dict):pass

def run(monkeypatch,curvature=0.,age=0.,valid=True,fail=False):
  original=lambda *args:[-3.5,.25]
  monkeypatch.setattr(baseline,'limit_accel_in_turns',original)
  def update(self,sm):
    if fail:raise RuntimeError('test interrupted update')
    return baseline.limit_accel_in_turns(10.,90.,[-3.5,2.],None)
  monkeypatch.setattr(baseline.LongitudinalPlanner,'update',update)
  sm=SM(controlsState=SimpleNamespace(curvature=curvature))
  sm.valid={k:valid for k in ('carState','controlsState','modelV2')}
  sm.logMonoTime=dict(modelV2=1000000000,carState=int((1-age)*1e9),controlsState=1000000000)
  p=object.__new__(CurveModelPlanner)
  try:return p.update(sm)
  finally:assert baseline.limit_accel_in_turns is original

def test_same_total_budget(monkeypatch):
  assert run(monkeypatch)==[-3.5,1.7]

def test_high_lateral_load_has_zero_positive_headroom(monkeypatch):
  assert run(monkeypatch,curvature=.03)==[-3.5,0.]

@pytest.mark.parametrize('kwargs',[{'curvature':math.nan},{'age':.21},{'valid':False}])
def test_invalid_uses_original_formula(monkeypatch,kwargs):
  assert run(monkeypatch,**kwargs)==[-3.5,.25]

def test_exception_restores_original(monkeypatch):
  with pytest.raises(RuntimeError):run(monkeypatch,fail=True)
