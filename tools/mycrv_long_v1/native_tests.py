#!/usr/bin/env python3
"""Run selected native tests against staged candidate modules without checkout changes."""

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
  return module


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--staged-dir', required=True)
  parser.add_argument('tests', nargs='+')
  args = parser.parse_args()
  staged = Path(args.staged_dir)
  load('openpilot.selfdrive.controls.lib.longitudinal_throttle', staged / 'longitudinal_throttle.py')
  load('openpilot.selfdrive.controls.lib.longitudinal_planner', staged / 'longitudinal_planner.py')
  load('openpilot.selfdrive.controls.longitudinal_debug', staged / 'longitudinal_debug.py')
  config = load('mycrv_staged_process_config', staged / 'process_config.py')
  from opendbc.car.honda.interface import CarInterface
  from opendbc.car.honda.values import CAR
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  assert config.mycrv_long_debug(True, None, cp)
  print('staged imports and manager predicate passed', flush=True)
  # Project pytest defaults to xdist workers, which would import baseline modules
  # instead of the staged modules injected into this process.
  raise SystemExit(pytest.main(['-q', '-n', '0', *args.tests]))


if __name__ == '__main__':
  main()
