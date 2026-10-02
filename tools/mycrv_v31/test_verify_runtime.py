#!/usr/bin/env python3
"""Device-independent checks for the post-reboot process gate."""

from types import SimpleNamespace
import unittest

from verify_runtime import assess_processes


def process(name, running, expected, pid=0):
  return SimpleNamespace(name=name, running=running, shouldBeRunning=expected, pid=pid)


class VerifyRuntimeTest(unittest.TestCase):
  def test_healthy_offroad_does_not_require_parked_control_processes(self):
    states = [process("ui", True, True, 10), process("pandad", True, True, 11),
              process("card", False, False), process("controlsd", False, False),
              process("plannerd", False, False)]
    missing, stopped, pids = assess_processes(states, "offroad")
    self.assertEqual((missing, stopped, pids), ((), (), {"ui": 10, "pandad": 11}))

  def test_onroad_requires_full_control_chain(self):
    states = [process("ui", True, True, 10), process("pandad", True, True, 11),
              process("card", False, False), process("controlsd", False, False),
              process("plannerd", False, False)]
    missing, stopped, _ = assess_processes(states, "onroad")
    self.assertEqual(missing, ("card", "controlsd", "plannerd"))
    self.assertFalse(stopped)

  def test_expected_process_crash_blocks_offroad_gate(self):
    states = [process("ui", True, True, 10), process("pandad", False, True, 11)]
    missing, stopped, _ = assess_processes(states, "offroad")
    self.assertEqual(missing, ("pandad",))
    self.assertEqual(stopped, ("pandad",))

  def test_invalid_mode_is_rejected(self):
    with self.assertRaises(ValueError):
      assess_processes([], "unknown")


if __name__ == "__main__":
  unittest.main()
