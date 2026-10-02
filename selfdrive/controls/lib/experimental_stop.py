"""Bounded model stop-intent hold for blended longitudinal control.

ModelV2 provides a stop intent, not a measured stop-line position. This module
must not turn its trajectory endpoint into an assumed road marking location.
"""

from dataclasses import dataclass


@dataclass
class StopIntentTracker:
  latched: bool = False
  false_time: float = 0.0

  def reset(self) -> None:
    self.latched = False
    self.false_time = 0.0

  def update(self, raw_should_stop: bool, active: bool, dt: float, release_time: float) -> bool:
    if not active:
      self.reset()
    elif raw_should_stop:
      # Never delay the start of model-requested stopping.
      self.latched = True
      self.false_time = 0.0
    elif self.latched:
      self.false_time += dt
      if self.false_time >= release_time:
        self.reset()
    return self.latched
