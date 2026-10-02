# Experimental stop intent candidate

Base: `my-crv-long-tune-v2` at `a1e028371cdfe87471f694c87fc3d17060f969c4`.
This branch is an isolated candidate. It has not been deployed.

## Existing path

`modelV2` predicts an ego trajectory. `modeld.get_action_from_model` applies
`get_accel_from_plan` to its speed and acceleration, producing
`desiredAcceleration` and `shouldStop`. The former is smoothed over 0.3 s. The
model action has no explicit stop-line coordinate. The model action's
`shouldStop` threshold is a predicted speed below 0.3 m/s with target
acceleration below 0.1 m/s². In blended mode the planner uses the lower of
the model and MPC acceleration targets, and the OR of their stop flags.
`longcontrol` enters `stopping` immediately on the resulting flag and ramps
the last acceleration down by `stoppingDecelRate` until `stopAccel`.
Honda Bosch then clips the requested acceleration to its existing bounds and
forms the unchanged CAN command.

The CR-V interface reports `stopAccel=-2.0 m/s²`,
`stoppingDecelRate=0.8 m/s³`, `vEgoStopping=0.5 m/s`,
`vEgoStarting=0.5 m/s`, `startAccel=0`, `startingState=false`, and
`longitudinalActuatorDelay=0.5 s`. The device currently has
`AlphaLongitudinalEnabled=false`, so its active CarParams use stock PCM cruise
(`openpilotLongitudinalControl=false`, `pcmCruise=true`). This experimental
stop-intent filter would be inactive in that configuration.

## Candidate behavior

The candidate immediately honors `shouldStop=true`. At less than 2.5 m/s,
with active openpilot longitudinal control in experimental/blended mode only,
it ignores short `shouldStop=false` dropouts. It releases after a continuous
false interval of 0.30 s (relaxed), 0.20 s (standard), or 0.15 s
(aggressive). It resets when disengaged, outside that mode, or above that
speed. It does not alter acceleration targets, braking strength, MPC weights,
normal ACC, Honda commands, or any collision constraint.

The CSV explicitly records `stopPointAvailable=false`,
`stopControllerActive=false`, and empty distance/offset fields. It records
raw/filtered stop intent, MPC and model acceleration, the final plan, state,
and release time. No stop-line or front-bumper location has been validated;
the predicted trajectory endpoint must not be treated as a road marking.

## Isolated results

- Native build and schema compilation succeeded in `/data/mycrv_stop_test`.
- Stop tracker/logger/longcontrol tests: 18 passed. Planner integration: 4 passed.
- Normal ACC synthetic output: byte-identical to v2 for 12 cases × 3 personalities.
- Honda interface and safety: 317 passed, 255 skipped.
- One-frame false stop intent stayed latched; model intent stayed true when a
  synthetic lead left while the light remained red. Green release took 0.30,
  0.20, and 0.15 s for relaxed, standard, and aggressive respectively.
- Stop-line error, peak deceleration, and peak jerk cannot be measured from
  this intent-only simulation. The 14 requested spatial stop scenarios cannot
  be validated without a trustworthy model stop point and actual route data.
- The full longitudinal maneuver suite has two `NaN recovery` failures
  (blended and ACC, without force decel). The same scenarios fail on deployed
  v2, so this branch did not introduce them. This is still a failed deployment
  gate; the branch remains undeployed.

## Needed for a stop-line controller

Obtain route logs with experimental mode, current CarParams, model prediction,
radar, control output, and a ground-truth road marking or calibrated
camera-to-front-bumper offset. Verify whether a model prediction endpoint
corresponds to the line and quantify its uncertainty before using a distance
profile or claiming a final 2–3 m offset. Do not enable openpilot Bosch
longitudinal merely to activate this candidate: that decision changes the
stock collision-warning/braking configuration and is outside this tune.
