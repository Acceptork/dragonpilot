#!/usr/bin/env python3
"""Small, independent longitudinal CSV recorder for CR-V road tests."""

import csv
import io
import os
from pathlib import Path
import time


LOG_DIR = Path('/data/mycrv_long_debug')
MAX_FILE_BYTES = 20_000_000
MAX_FILES = 10
SAMPLE_INTERVAL = 0.1  # 10 Hz

FIELDS = (
  'timestamp', 'vEgo', 'aEgo', 'vCruise', 'vCruiseCluster', 'aTarget',
  'actuators.accel', 'longActive', 'longControlState', 'allowThrottle', 'longitudinalPlanSource',
  'lead_status', 'dRel', 'vRel', 'vLead', 'aLeadK', 'personality',
  'experimentalMode', 'gasPressProb', 'upAccelCmd', 'uiAccelCmd', 'ufAccelCmd',
  'pitch', 'lead2_status', 'lead2_dRel', 'lead2_vRel',
)
LONG_STATE_NAMES = {'0': 'off', '1': 'pid', '2': 'stopping', '3': 'starting'}
PLAN_SOURCE_NAMES = {'0': 'cruise', '1': 'lead0', '2': 'lead1', '3': 'lead2', '4': 'e2e'}
PERSONALITY_NAMES = {'0': 'aggressive', '1': 'standard', '2': 'relaxed'}


def csv_line(values):
  buffer = io.StringIO(newline='')
  csv.writer(buffer).writerow(values)
  return buffer.getvalue()


def enum_name(value, names):
  value = str(value)
  return names.get(value, value)


class RotatingLongCsv:
  def __init__(self, directory=LOG_DIR, max_file_bytes=MAX_FILE_BYTES, max_files=MAX_FILES):
    self.directory = Path(directory)
    self.max_file_bytes = max_file_bytes
    self.max_files = max_files
    self.file = None
    self.size = 0
    self.last_flush = 0.0
    self.sequence = 0

  def _prune(self):
    files = sorted(self.directory.glob('long-*.csv'))
    for old in files[:-self.max_files]:
      old.unlink()

  def _open(self):
    self.directory.mkdir(parents=True, exist_ok=True)
    self.sequence += 1
    name = (f"long-{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}-"
            f"{time.time_ns() % 1_000_000_000:09d}-{os.getpid()}-{self.sequence:05d}.csv")
    self.file = (self.directory / name).open('x', encoding='utf-8', newline='')
    header = csv_line(FIELDS)
    self.file.write(header)
    self.size = len(header.encode('utf-8'))
    self.last_flush = time.monotonic()
    self._prune()

  def write(self, values):
    row = csv_line(values)
    row_size = len(row.encode('utf-8'))
    if self.file is None:
      self._open()
    if self.size + row_size > self.max_file_bytes:
      self.close()
      self._open()
    self.file.write(row)
    self.size += row_size
    now = time.monotonic()
    if now - self.last_flush >= 1.0:
      self.file.flush()
      self.last_flush = now

  def close(self):
    if self.file is not None:
      file = self.file
      self.file = None
      try:
        file.close()
      except OSError:
        pass


def sample(sm):
  car_state = sm['carState']
  car_control = sm['carControl']
  controls_state = sm['controlsState']
  plan = sm['longitudinalPlan']
  lead = sm['radarState'].leadOne
  lead2 = sm['radarState'].leadTwo
  selfdrive_state = sm['selfdriveState']
  gas_probs = sm['modelV2'].meta.disengagePredictions.gasPressProbs
  pitch = car_control.orientationNED[1] if len(car_control.orientationNED) == 3 else ''
  return (
    time.time(), car_state.vEgo, car_state.aEgo, car_state.vCruise, car_state.vCruiseCluster,
    plan.aTarget, car_control.actuators.accel, car_control.longActive,
    enum_name(controls_state.longControlState, LONG_STATE_NAMES),
    plan.allowThrottle, enum_name(plan.longitudinalPlanSource, PLAN_SOURCE_NAMES), lead.status,
    lead.dRel if lead.status else '', lead.vRel if lead.status else '',
    lead.vLead if lead.status else '', lead.aLeadK if lead.status else '',
    enum_name(selfdrive_state.personality, PERSONALITY_NAMES), selfdrive_state.experimentalMode,
    gas_probs[1] if len(gas_probs) > 1 else '',
    controls_state.upAccelCmd, controls_state.uiAccelCmd, controls_state.ufAccelCmd, pitch,
    lead2.status, lead2.dRel if lead2.status else '', lead2.vRel if lead2.status else '',
  )


def main():
  import cereal.messaging as messaging
  from openpilot.common.swaglog import cloudlog

  try:
    os.nice(10)
  except OSError:
    pass

  sm = messaging.SubMaster(['carState', 'carControl', 'controlsState', 'longitudinalPlan',
                            'radarState', 'selfdriveState', 'modelV2'], poll='carControl')
  writer = RotatingLongCsv()
  next_sample = 0.0
  retry_at = 0.0
  try:
    while True:
      sm.update(100)
      now = time.monotonic()
      if not sm['selfdriveState'].enabled:
        writer.close()
        next_sample = now
        continue
      if now < next_sample or now < retry_at or not sm.all_checks():
        continue
      next_sample = now + SAMPLE_INTERVAL
      try:
        writer.write(sample(sm))
      except OSError as e:
        cloudlog.warning(f'longitudinal_debug write failed: {e}')
        try:
          writer.close()
        except OSError:
          pass
        retry_at = now + 60.0
  finally:
    writer.close()


if __name__ == '__main__':
  main()
