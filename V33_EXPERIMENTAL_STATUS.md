# NOT_FOR_DEPLOYMENT — software gates pending

Default OFF dp_exp_overtake. Stage 1 bounded preference between existing target and MPC.
Both lead constraints and existing follow-distance envelope remain authoritative.
Fresh same-direction driver torque and laneChangeStarting required; no blinker-only trigger.
Stage 2 BLOCKED: no validated path-exit provider. Stage 1 may be zero when the existing
MPC/lead constraint is already binding; this is recorded, not bypassed.
Sweep bounds .025/.05/.10 m/s2, default .05, positive preference slew .10 m/s3.
