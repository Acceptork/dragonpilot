import unittest
from types import SimpleNamespace
from unittest.mock import patch

from openpilot.selfdrive.ui.onroad.long_debug import build_longitudinal_debug_lines


class FakeSubMaster:
  def __init__(self, lead_status=True, all_valid=True):
    self.seen = {name: all_valid for name in ("carState", "longitudinalPlan", "carControl", "radarState")}
    self.alive = self.seen.copy()
    self.valid = self.seen.copy()
    self.data = {
      "carState": SimpleNamespace(vEgo=20.0, vCruise=90.0, vCruiseCluster=90.0),
      "longitudinalPlan": SimpleNamespace(aTarget=-0.3, allowThrottle=False, shouldStop=True, longitudinalPlanSource="e2e"),
      "carControl": SimpleNamespace(longActive=True, actuators=SimpleNamespace(accel=-0.25, longControlState="pid")),
      "radarState": SimpleNamespace(leadOne=SimpleNamespace(status=lead_status, dRel=30.0, vRel=-2.0)),
    }

  def __getitem__(self, key):
    return self.data[key]


class TestLongitudinalDebugLines(unittest.TestCase):
  def test_uses_observed_values_without_interpreting_safety(self):
    with patch("openpilot.selfdrive.ui.onroad.long_debug.tr", side_effect=lambda s: s):
      lines = build_longitudinal_debug_lines(FakeSubMaster())
    assert "20.0" not in lines[1]  # vEgo is m/s; UI reports 72 km/h
    assert "72.0" in lines[1] and "90" in lines[1]
    assert "-0.30" in lines[2] and "-0.25" in lines[2]
    assert "30.0 m" in lines[3] and "-2.0 m/s" in lines[3]
    assert "Throttle allowed 0" in lines[4] and "Stop intent 1" in lines[4]

  def test_stale_service_suppresses_values(self):
    with patch("openpilot.selfdrive.ui.onroad.long_debug.tr", side_effect=lambda s: s):
      lines = build_longitudinal_debug_lines(FakeSubMaster(all_valid=False))
    assert lines == ("Longitudinal data unavailable",)

  def test_missing_lead_is_not_zero_range(self):
    with patch("openpilot.selfdrive.ui.onroad.long_debug.tr", side_effect=lambda s: s):
      lines = build_longitudinal_debug_lines(FakeSubMaster(lead_status=False))
    assert lines[3] == "No lead"
