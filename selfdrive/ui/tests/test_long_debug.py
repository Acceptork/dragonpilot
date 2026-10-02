import unittest
from types import SimpleNamespace
from unittest.mock import patch

from openpilot.selfdrive.ui.onroad.long_debug import build_longitudinal_debug_lines, valid_cruise_speed


class FakeSubMaster:
  def __init__(self, lead_status=True, all_valid=True, cluster_speed=90.0, cruise_speed=90.0, source="e2e", state="pid"):
    self.seen = {name: all_valid for name in ("carState", "longitudinalPlan", "carControl", "radarState")}
    self.alive = self.seen.copy()
    self.valid = self.seen.copy()
    self.data = {
      "carState": SimpleNamespace(vEgo=20.0, vCruise=cruise_speed, vCruiseCluster=cluster_speed),
      "longitudinalPlan": SimpleNamespace(aTarget=-0.3, allowThrottle=False, shouldStop=True, longitudinalPlanSource=source),
      "carControl": SimpleNamespace(longActive=True, actuators=SimpleNamespace(accel=-0.25, longControlState=state)),
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

  def test_cruise_speed_falls_back_for_unset_and_nan_cluster(self):
    assert valid_cruise_speed(-1.0, 85.0) == 85.0
    assert valid_cruise_speed(float("nan"), 85.0) == 85.0
    assert valid_cruise_speed(0.0, 85.0) == 85.0
    assert valid_cruise_speed(255.0, -1.0) is None
    with patch("openpilot.selfdrive.ui.onroad.long_debug.tr", side_effect=lambda s: s):
      assert "Set 85" in build_longitudinal_debug_lines(FakeSubMaster(cluster_speed=float("nan"), cruise_speed=85))[1]

  def test_schema_enum_labels_and_unknown_fallback(self):
    with patch("openpilot.selfdrive.ui.onroad.long_debug.tr", side_effect=lambda s: s):
      assert "Lead 1" in build_longitudinal_debug_lines(FakeSubMaster(source="lead0", state="stopping"))[5]
      assert "Stopping" in build_longitudinal_debug_lines(FakeSubMaster(source="lead0", state="stopping"))[5]
      assert "End-to-end model" in build_longitudinal_debug_lines(FakeSubMaster(source=4, state=1))[5]
      assert "PID control" in build_longitudinal_debug_lines(FakeSubMaster(source=4, state=1))[5]
      assert "Unknown (unexpected)" in build_longitudinal_debug_lines(FakeSubMaster(source="unexpected"))[5]
