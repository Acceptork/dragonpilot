#!/usr/bin/env python3
"""Compare the two pre-existing longitudinal regression edge cases."""

import argparse
import importlib.util
import os
from pathlib import Path
import sys


def load(name, path):
  spec = importlib.util.spec_from_file_location(name, path)
  module = importlib.util.module_from_spec(spec)
  sys.modules[name] = module
  spec.loader.exec_module(module)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--staged-dir')
  args = parser.parse_args()
  if args.staged_dir:
    staged = Path(args.staged_dir)
    load('openpilot.selfdrive.controls.lib.longitudinal_throttle', staged / 'longitudinal_throttle.py')
    load('openpilot.selfdrive.controls.lib.longitudinal_planner', staged / 'longitudinal_planner.py')

  from openpilot.selfdrive.test.longitudinal_maneuvers.test_longitudinal import create_maneuvers
  for e2e in (False, True):
    maneuvers = create_maneuvers({'e2e': e2e, 'force_decel': False})
    for maneuver in maneuvers:
      if maneuver.title not in ('NaN recovery', 'slow to 5m/s with allow_throttle = False and pitch = +0.1'):
        continue
      sys.stdout.flush()
      saved_stdout = os.dup(1)
      sink = os.open(os.devnull, os.O_WRONLY)
      try:
        os.dup2(sink, 1)
        valid, output = maneuver.evaluate()
        sys.stdout.flush()
      finally:
        os.dup2(saved_stdout, 1)
        os.close(saved_stdout)
        os.close(sink)
      print(f'{maneuver.title}; e2e={e2e}; valid={valid}; final_speed={output[-1, 3]:.3f} m/s', flush=True)


if __name__ == '__main__':
  main()
