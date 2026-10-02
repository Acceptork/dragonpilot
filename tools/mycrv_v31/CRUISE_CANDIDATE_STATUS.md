# Cruise candidate status

**OUT_OF_RC / DO_NOT_DEPLOY**

This branch changes first-SET and cruise-button behavior. Native build and unit tests pass, but an offline control-chain replay found a generated Honda Bosch `BRAKE_REQUEST` regression. Some affected frames also changed to a positive `GAS_COMMAND` while longitudinal control was active.

The safety gate is **FAIL**. Passing unit tests or panda safety tests does not establish that this candidate is safe to drive. Process replay compares commands under fixed recorded inputs; it cannot predict the vehicle's physical response.

Keep this branch independent. Do not merge it into the integrated release candidate or deploy it to the comma. Rework the cruise behavior, rerun the full offline command comparison with the same safety gate, and complete closed-course validation before considering vehicle use.

Detailed route, timestamps, command traces, and driver data are kept only in the private local analysis results. They are intentionally absent from this repository.
