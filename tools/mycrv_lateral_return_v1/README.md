# Lateral return investigation (no control change)

Branch: `my-crv-lateral-return-v1-candidate`, based on
`a201e6cb75296bb1700dadf9268d857a9a597016`. The user's ordinary
steering tune is preserved exactly. This branch contains analysis only and
is not integrated with longitudinal v3.1.

## Control path inspected

`modelV2.action.desiredCurvature` (or valid `lateralManeuverPlan`) enters
`controlsd`. `clip_curvature` bounds its rate using the current lateral jerk
limit and speed, then bounds lateral acceleration and absolute curvature.
`LatControlTorque` uses measured curvature, driver torque, a lateral delay,
friction compensation, and a torque PID. The integral freezes on safety
steering limitation, driver steering input, or low speed. Model lateral
smoothing is set to zero in this branch. A slow return can therefore originate
in model path, curvature-rate clipping, delay calibration, torque response,
or driver/EPS interaction; a single symptom cannot distinguish them.

## Archived signal audit

The read-only raw rlog audit examined segments 19–21: 18,000 controlsState
samples. Of those, 14,499 were latActive, above 8 m/s and without driver
steering pressure. In segment 20, the 95th percentile absolute requested and
measured lateral accelerations were 0.6652 and 0.6784 m/s²; in segment 21
they were 0.6925 and 0.6937 m/s². A descriptive detector seeking a sustained
turn followed by near-zero requested curvature found zero qualifying
transitions in these three segments. This is not evidence that the user's
occasional symptom never occurs. No timestamped driver-confirmed return-slow
episode is available in the annotations.

The audit script and its exact thresholds are at
`analysis_tools/v31_lateral_return_audit.py`; output is
`E:\comma_replay_results\events\v31_lateral_return_sample_stats_data.json`.
It only reads the archived rlog and writes separate analysis output.

## Decision

No curvature-rate, torque, friction, delay, steering ratio, or panda limit is
changed. Without an identified episode and synchronized model request,
`controlsState.desiredCurvature`, actual curvature, torque request/output and
driver input, changing the steering tune would be speculative. Before any
future source change, annotate a specific return-slow timestamp, replay it
with the full lateral chain, and compare command tracking and oscillation on
closed course. This investigation is **OUT OF RC**.
