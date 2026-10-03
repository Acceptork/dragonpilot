# Metric cruise long-hold one-step candidate — DO NOT DEPLOY

Branch: `my-crv-buttons10-single-v1-candidate`  
Base: `a201e6cb75296bb1700dadf9268d857a9a597016`

This isolated change makes one continuous metric cruise-button hold produce one aligned 10 km/h step: 83→90, 90→100, or 97→90. Another step requires releasing and pressing again. Short metric presses remain 1 km/h; imperial long-hold repetition, first SET, and RESUME remain unchanged.

Native build, syntax, Ruff, eight new focused tests, and 26 existing cruise tests passed. A continuous four-process offline replay completed all 42 archived segments and paired every generated control and Honda CAN frame against v3. The candidate set speed diverged from the recorded set speed in 34 segments, so the event safety gate is **BLOCKED** and cannot establish on-road behavior.

The separate all-frame Honda command audit **FAILED**: 95 previously present `BRAKE_REQUEST` commands disappeared, 835 `GAS_COMMAND` values rose, and 1,359 `ACCEL_COMMAND` values became more positive. These generated-command differences are sufficient to exclude this candidate from any release. They do not describe measured vehicle braking or gap.

**Status: OUT_OF_RC / DO_NOT_DEPLOY.** Keep this branch independent; do not merge it into `my-crv-v3.1-rc1` or deploy it to a vehicle. Detailed route evidence and exact timestamps remain in the private local analysis results.
