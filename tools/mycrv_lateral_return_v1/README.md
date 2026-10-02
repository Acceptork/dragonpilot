# Lateral return investigation (no control change)

Branch: `my-crv-lateral-return-v1-candidate`, based on
`a201e6cb75296bb1700dadf9268d857a9a597016`. The existing steering
tune is preserved exactly. This branch contains an analysis decision only.

The control path is `modelV2.action.desiredCurvature` or
`lateralManeuverPlan` → `controlsd.clip_curvature` → `LatControlTorque` →
Honda steering command. The clip bounds curvature rate, lateral acceleration
and maximum curvature. The torque controller uses measured curvature,
calibrated delay, friction compensation and driver input. A slow return can
arise at any of those stages; changing a torque gain or rate bound from the
symptom alone would be speculative.

An offline archived-signal audit was performed locally, but it did not
identify a driver-confirmed, timestamped slow-return episode suitable for
causal tuning. Full route-derived measurements and logs remain in the
private analysis workspace, outside this Git branch.

No curvature, torque, friction, delay, steering-ratio or panda parameter is
changed. This investigation is **OUT OF RC**. Future work requires a
timestamped episode, synchronized desired and actual curvature, torque
request and output, driver input, and closed-course checking for oscillation.
