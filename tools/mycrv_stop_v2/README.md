# my-crv stop v2 independent candidate

Base: `my-crv-long-tune-v3-candidate` at
`a201e6cb75296bb1700dadf9268d857a9a597016`.
Current candidate: `ea869e519bd76bc46b85221f8201b5c828ffe5c3`
before this documentation commit. This branch has not been deployed or
integrated into the v3.1 release candidate.

## Scope

The code carries a short `modelV2.action.shouldStop` false-dropout hold into
experimental blended planning below 2.5 m/s. It requires openpilot
longitudinal control and resets when the conditions cease. The false interval
is 0.30 s relaxed, 0.20 s standard, and 0.15 s aggressive. Model stop intent
is accepted immediately. The existing model/MPC acceleration, Honda brake
limits, FCW and collision paths are unchanged. The diagnostic fields explicitly
mark stop-line position as unavailable.

This is **not** a solution for event_041. Before the driver brake intervention
at 2516.0145 s, the archived model did not predict a complete stop in 140
consecutive 20 Hz predictions. A hold of an existing stop flag cannot create a
stop request that was absent then. There is no validated stop-line distance.
Nor does this branch implement early deceleration or terminal brake taper.

## Native offline evidence

- Native `uv sync`, schema build and SCons build: pass.
- Selected stop, planner, longcontrol and Honda tests: 25 pass.
- Longitudinal maneuvers: 4 maneuvers and 58 subtests pass.
- Honda panda safety: 259 executed pass, 52 skipped by the suite.
- Synthetic stop-intent test: pass.
- Continuous radard → plannerd → controlsd → card replay: 42/42 segments,
  zero process failures. The v3 comparison used the same archived rlog SHA,
  harness SHA and generated output services.
- Open-loop safety gate against v3: `PASS_CANDIDATE`, with no observed
  weakening of braking at the six specified safety events. This is a command
  comparison, not a prediction of vehicle stopping distance.

The complete per-field comparison found three `shouldStop` frames added while
the original car was already stationary: one at 1286.940 s and two around
2539.351–2539.399 s. These changed 15 `carControl.accel` frames and seven
Honda CAN frames. At the second occurrence the requested acceleration
changed from about +0.04 to -2.0 m/s² and `BRAKE_REQUEST` from 0 to 1 for
roughly 0.1 s. Since archived `vEgo` was approximately zero, this is a brake
hold command transition, not evidence of moving-vehicle deceleration. It is
still a significant command discontinuity that needs vehicle-level assessment.

No control-command change occurred in the event_041 review window. The branch
therefore stays independent and is **excluded from my-crv-v3.1-rc1** pending
closed-course stop/release and hold-transition testing. `PASS_CANDIDATE` does
not override that decision.

Logs and reports: `E:\comma_replay_results\v31_stop\`.
