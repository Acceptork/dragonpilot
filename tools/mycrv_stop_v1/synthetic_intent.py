#!/usr/bin/env python3
"""Measure only temporal stop-intent behavior; no stop-line estimate exists."""

import json

from cereal import car, log
from openpilot.selfdrive.controls.lib.experimental_stop import StopIntentTracker, get_stop_intent_profile
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState, long_control_state_trans


DT = 0.05
PERSONALITIES = {
  'relaxed': log.LongitudinalPersonality.relaxed,
  'standard': log.LongitudinalPersonality.standard,
  'aggressive': log.LongitudinalPersonality.aggressive,
}


def simulate(personality):
  tracker = StopIntentTracker()
  cp = car.CarParams.new_message(startingState=False, vEgoStarting=0.5)
  state = LongCtrlState.stopping
  release_time = get_stop_intent_profile(personality).release_time
  false_flicker_held = False
  green_release_delay = None
  red_after_lead_leaves_stopped = False
  for frame in range(60):
    t = frame * DT
    # Red from 0 to 2 s, with one false frame at 1 s; lead leaves at 1.5 s.
    raw_stop = t < 2.0 and frame != 20
    should_stop = tracker.update(raw_stop, True, DT, release_time)
    state = long_control_state_trans(cp, True, state, 0.1, should_stop, False, False)
    if frame == 20:
      false_flicker_held = should_stop and state == LongCtrlState.stopping
    if frame == 30:
      red_after_lead_leaves_stopped = should_stop and state == LongCtrlState.stopping
    if frame >= 40 and green_release_delay is None and state != LongCtrlState.stopping:
      green_release_delay = round((frame - 39) * DT, 2)
  assert false_flicker_held and red_after_lead_leaves_stopped
  assert green_release_delay is not None and green_release_delay <= release_time + DT
  return {
    'stopIntentReleaseTimeS': release_time,
    'singleFalseFrameHeld': false_flicker_held,
    'leadLeavesWhileRedHeld': red_after_lead_leaves_stopped,
    'greenReleaseDelayS': green_release_delay,
    'stopLineDistanceM': None,
    'finalStopErrorM': None,
    'peakDecelMps2': None,
    'peakJerkMps3': None,
  }


if __name__ == '__main__':
  print(json.dumps({name: simulate(personality) for name, personality in PERSONALITIES.items()}, sort_keys=True))
