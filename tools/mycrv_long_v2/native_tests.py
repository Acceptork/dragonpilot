#!/usr/bin/env python3
"""Run v2 longitudinal tests against staged Python modules on a built comma."""

import argparse
import importlib.util
from pathlib import Path
import sys

import pytest


def load(name, path):
  spec = importlib.util.spec_from_file_location(name, path)
  module = importlib.util.module_from_spec(spec)
  sys.modules[name] = module
  spec.loader.exec_module(module)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--staged-dir', required=True)
  parser.add_argument('tests', nargs='+')
  args = parser.parse_args()
  staged = Path(args.staged_dir)
  if (staged / 'cruise.py').exists():
    load('openpilot.selfdrive.car.cruise', staged / 'cruise.py')
  if (staged / 'updated.py').exists():
    load('openpilot.system.updated.updated', staged / 'updated.py')
  load('openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc', staged / 'long_mpc.py')
  load('openpilot.selfdrive.controls.lib.longitudinal_throttle', staged / 'longitudinal_throttle.py')
  load('openpilot.selfdrive.controls.lib.longitudinal_planner', staged / 'longitudinal_planner.py')
  load('openpilot.selfdrive.controls.longitudinal_debug', staged / 'longitudinal_debug.py')
  raise SystemExit(pytest.main(['-q', '-n', '0', *args.tests]))


if __name__ == '__main__':
  main()
