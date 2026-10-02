from pathlib import Path
import runpy
import unittest


# The pure mapping can be checked without importing native Cap'n Proto on Windows.
limit_crv5g_bosch_gas = runpy.run_path(str(Path(__file__).resolve().parents[1] / "low_speed_gas.py"))["limit_crv5g_bosch_gas"]


class TestCrv5gLowSpeedGas(unittest.TestCase):
  def test_negative_decel_request_near_stop(self):
    self.assertEqual(limit_crv5g_bosch_gas(66.0, -0.11, 0.8), 0.0)
    self.assertEqual(limit_crv5g_bosch_gas(21.0, -0.17, 1.2), 0.0)

  def test_continuous_tapers(self):
    self.assertAlmostEqual(limit_crv5g_bosch_gas(100.0, -0.05, 1.0), 50.0)
    self.assertAlmostEqual(limit_crv5g_bosch_gas(100.0, -0.10, 1.75), 50.0)
    self.assertAlmostEqual(limit_crv5g_bosch_gas(100.0, -0.001, 1.0), 99.0)

  def test_stock_behavior_outside_scope(self):
    self.assertEqual(limit_crv5g_bosch_gas(100.0, 0.0, 0.8), 100.0)
    self.assertEqual(limit_crv5g_bosch_gas(100.0, 0.1, 0.8), 100.0)
    self.assertEqual(limit_crv5g_bosch_gas(100.0, -0.11, 2.0), 100.0)
