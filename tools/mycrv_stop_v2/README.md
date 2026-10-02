# Experimental stop intent hold — independent candidate

This candidate is based on `my-crv-long-tune-v3-candidate` at
`a201e6cb75296bb1700dadf9268d857a9a597016`. It is not deployed or
integrated into a release candidate.

The code holds a transient `modelV2.action.shouldStop=false` for a short
interval below 2.5 m/s in experimental blended mode with openpilot
longitudinal control. True stop intent is accepted immediately. The hold
releases after 0.30 s relaxed, 0.20 s standard, or 0.15 s aggressive.
Existing acceleration targets, Honda brake limits, FCW and collision logic
remain unchanged. Diagnostic fields do not claim a stop-line location.

The feature cannot create an earlier stop request when the model trajectory
does not predict stopping. It does not implement early braking, a calibrated
stop-line controller, or terminal brake taper. Offline replay also showed
brief brake-hold command transitions while stationary; physical comfort and
release behavior remain unverified. Therefore this branch stays independent
and is **excluded from my-crv-v3.1-rc1** pending closed-course validation.

Native build, focused control tests, Honda safety tests, and a continuous
four-process archived-route replay were executed locally. Their full inputs,
event-level metrics, comparison outputs, and logs remain in the private
analysis workspace and are not included in this Git branch.
