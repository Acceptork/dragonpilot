# First SET 30 km/h candidate status

**OUT_OF_RC / DO_NOT_DEPLOY**

- Branch: `my-crv-set30-isolation-candidate`; tested commit: `4e7878ed874af8a39a83ba9239275037a6b6f674`.
- Base: `my-crv-long-tune-v3-candidate` at `a201e6cb75296bb1700dadf9268d857a9a597016`.
- Scope: first SET speed initialization and a fresh moving-speed fallback; no controller or safety-limit changes.
- Native cruise tests: **41 PASS**. Continuous four-process replay: **42/42 segments completed** with fixed archived inputs.
- Global Honda command audit versus the v3 base: **158 `BRAKE_REQUEST` 1→0 frames**, **1,781 `GAS_COMMAND` increases**, and **1,942 more-positive `ACCEL_COMMAND` frames**. `CONTROL_ON` had no 1→0 change. The global command gate **FAILS**; the event gate is **BLOCKED** by cruise-state divergence and flags weaker response in event_005.

The candidate reproduces one software route to a fixed 50 km/h SET fallback, but the historical vehicle observation lacks its exact button frame and `CarParams`, so its root cause remains unproven. The replay compares newly generated commands under fixed recorded inputs; it cannot establish the vehicle's new speed, gap, or stopping position. Keep this branch independent. It has not been deployed.
