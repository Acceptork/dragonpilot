"""Read-only EPS dataset and steering-return +/-10 second capture."""
from collections import deque
import csv
import json
import os
from pathlib import Path
from queue import Queue, Full
from threading import Thread


class SteeringReturnCapture:
  def __init__(self):
    self.history = deque(maxlen=2200)
    self.pending = None
    self.armed = False
    self.zero_since = None
    self.last_t = None
    self.saturation_since = None

  def update(self, row):
    t = row['t']
    if self.last_t is not None and not 0 < t - self.last_t <= .2:
      self.history.clear()
      self.pending = None
      self.armed = False
      self.zero_since = None
      self.saturation_since = None
    self.last_t = t
    limited = row.get('steer_limited_by_safety') or row.get('rate_limiting')
    self.saturation_since = (t if self.saturation_since is None else self.saturation_since) if limited else None
    row = {**row, 'saturation_duration': t - self.saturation_since if self.saturation_since is not None else 0.}
    self.history.append(row)
    while self.history and t - self.history[0]['t'] > 10.:
      self.history.popleft()
    desired, actual = abs(row['desired_curvature']), abs(row['actual_curvature'])
    if desired > .002:
      self.armed = True
      self.zero_since = None
    elif desired < .0005 and self.armed:
      if self.zero_since is None:
        self.zero_since = t
      if actual > .001 and t - self.zero_since >= .5 and self.pending is None:
        self.pending = dict(event='STEERING_RETURN_EVENT', trigger=t, rows=list(self.history),
                            reason='desired_zero_actual_return_lag', complete=False)
        self.armed = False
    else:
      self.zero_since = None
    completed = None
    if self.pending is not None:
      if t > self.pending['trigger']:
        self.pending['rows'].append(row)
      if t - self.pending['trigger'] >= 10.:
        self.pending['complete'] = True
        completed, self.pending = self.pending, None
    return row, completed


class EpsShadow:
  def __init__(self, directory=None):
    self.directory = Path(directory or os.environ.get('MYCRV_V33_LOG_DIR', '/data/media/0/mycrv_v33'))
    self.capture = SteeringReturnCapture()
    self.queue = Queue(maxsize=4096)
    self.dropped = 0
    self.last_sample = None
    Thread(target=self._write, daemon=True, name='mycrv_eps_logger').start()

  def update(self, row):
    if self.last_sample is not None and 0 <= row['t'] - self.last_sample < .049:
      return
    self.last_sample = row['t']
    row, event = self.capture.update(row)
    row['logger_dropped'] = self.dropped
    try:
      self.queue.put_nowait((row, event))
    except Full:
      self.dropped += 1

  def _write(self):
    stream = writer = None
    while True:
      row, event = self.queue.get()
      try:
        if stream is None:
          self.directory.mkdir(parents=True, exist_ok=True)
          path = self.directory / 'EPS_CAPACITY_DATASET.csv'
          existing = path.exists() and path.stat().st_size > 0
          stream = path.open('a', newline='')
          writer = csv.DictWriter(stream, fieldnames=list(row))
          if not existing:
            writer.writeheader()
        writer.writerow(row)
        stream.flush()
        if stream.tell() > 64 * 1024 * 1024:
          stream.close()
          stream = None
          path.replace(self.directory / 'EPS_CAPACITY_DATASET.previous.csv')
        if event:
          (self.directory / ('STEERING_RETURN_EVENT_' + str(int(event['trigger'] * 1e9)) + '.json')).write_text(json.dumps(event))
          events = sorted(self.directory.glob('STEERING_RETURN_EVENT_*.json'))
          for old in events[:-20]:
            old.unlink()
      except (OSError, ValueError, TypeError):
        self.dropped += 1
        if stream is not None:
          stream.close()
        stream = None
      finally:
        self.queue.task_done()
