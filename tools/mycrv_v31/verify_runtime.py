#!/usr/bin/env python3
"""Read-only post-boot manager and live-CarParams checks for my-crv v3.1."""

import sys
import time


def assess_processes(processes, mode):
  """Return required missing/stopped names and stable PID candidates.

  Offroad manager intentionally does not run card, controlsd or plannerd.
  """
  if mode not in ("offroad", "onroad"):
    raise ValueError(f"invalid mode {mode!r}")
  required = ("ui", "pandad") if mode == "offroad" else ("ui", "pandad", "card", "controlsd", "plannerd")
  by_name = {process.name: process for process in processes}
  missing = tuple(name for name in required
                  if name not in by_name or not by_name[name].shouldBeRunning or
                  not by_name[name].running or by_name[name].pid <= 0)
  stopped = tuple(name for name, process in by_name.items()
                  if process.shouldBeRunning and not process.running)
  pids = {name: by_name[name].pid for name in required if name in by_name and name not in missing}
  return missing, stopped, pids


def main(mode):
  from cereal import car, messaging
  from openpilot.common.params import Params

  sm = messaging.SubMaster(["managerState"], poll="managerState")
  deadline = time.monotonic() + 90.0
  first = None
  first_time = None
  last_problem = "managerState has not arrived"

  while time.monotonic() < deadline:
    sm.update(5000)
    if not sm.updated["managerState"] or not sm.valid["managerState"] or not sm.alive["managerState"]:
      continue
    missing, stopped, pids = assess_processes(sm["managerState"].processes, mode)
    if missing or stopped:
      last_problem = f"missing required={missing}; stopped expected processes={stopped}"
      first = None
      first_time = None
      continue
    now = time.monotonic()
    if first != pids:
      first, first_time = pids, now
    elif first_time is not None and now - first_time >= 10.0:
      break
  else:
    raise SystemExit("manager/UI/pandad health did not stabilize: " + last_problem)

  print("managerState fresh and stable for >=10 s; required PIDs:", first)
  if mode == "offroad":
    print("PENDING_ONROAD: card/controlsd/plannerd, live fingerprint and openpilotLongitudinalControl require ignition")
    return

  params = Params()
  raw = params.get("CarParams")
  if not raw:
    raise SystemExit("onroad CarParams missing")
  cp = messaging.log_from_bytes(raw, car.CarParams)
  print("live fingerprint:", cp.carFingerprint)
  print("live openpilotLongitudinalControl:", cp.openpilotLongitudinalControl)
  if cp.carFingerprint != "HONDA_CRV_5G":
    raise SystemExit("wrong car fingerprint")
  expected_long = params.get_bool("AlphaLongitudinalEnabled")
  if cp.openpilotLongitudinalControl != expected_long:
    raise SystemExit("live Honda Bosch longitudinal mode differs from AlphaLongitudinalEnabled")
  print("ONROAD_PROCESSES_VERIFIED; closed-course validation remains required")


if __name__ == "__main__":
  if len(sys.argv) != 2 or sys.argv[1] not in ("offroad", "onroad"):
    raise SystemExit("usage: verify_runtime.py offroad|onroad")
  main(sys.argv[1])
