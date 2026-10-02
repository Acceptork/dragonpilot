"""Bounded model stop-intent hold for blended longitudinal control.

ModelV2 provides a stop intent, not a measured stop-line position. This module
must not turn its trajectory endpoint into an assumed road marking location.
"""

from dataclasses import dataclass
from cereal import log


@dataclass(frozen=True)
class StopIntentProfile:
  release_time: float


# These only govern how long a transient model shouldStop=False is ignored.
# Braking strength, distance, and Honda limits remain owned by the existing path.
STOP_INTENT_PROFILES = {
  log.LongitudinalPersonality.relaxed: StopIntentProfile(0.30),
  log.LongitudinalPersonality.standard: StopIntentProfile(0.20),
  log.LongitudinalPersonality.aggressive: StopIntentProfile(0.15),
}


def get_stop_intent_profile(personality) -> StopIntentProfile:
  for key, profile in STOP_INTENT_PROFILES.items():
    if personality == key:
      return profile
  raise NotImplementedError("Longitudinal personality not supported")


def stop_intent_hold_enabled(mode: str, experimental_mode: bool, openpilot_longitudinal: bool,
                             reset_state: bool, v_ego: float) -> bool:
  return (mode == 'blended' and experimental_mode and openpilot_longitudinal and
          not reset_state and 0.0 <= v_ego < 2.5)


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
