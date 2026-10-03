# Metric long-press ±10 km/h candidate status

**OUT_OF_RC / DO_NOT_DEPLOY**

- Branch: `my-crv-buttons10-isolation-candidate`; tested commit: `921c643d8cf5f21385279f9a2000baa0847d8f48`.
- Base: `my-crv-long-tune-v3-candidate` at `a201e6cb75296bb1700dadf9268d857a9a597016`.
- Scope: metric cruise long-press step from 5 to 10 km/h with the existing repeated-step behavior; short press, imperial step, SET, and RESUME are unchanged.
- Native cruise tests: **20 PASS**. Continuous four-process replay: **42/42 segments completed** with fixed archived inputs.
- Global Honda command audit versus the v3 base: **427 `BRAKE_REQUEST` 1→0 frames**, **2,215 `GAS_COMMAND` increases**, and **2,132 more-positive `ACCEL_COMMAND` frames**. `CONTROL_ON` had no 1→0 change. The global command gate **FAILS**; the event gate is **BLOCKED** by cruise-state divergence and flags weaker response in event_005.

Holding the button can repeat a 10 km/h step, so this candidate is not limited to one aligned step per physical press. The replay compares newly generated commands under fixed recorded inputs; it cannot establish the vehicle's new speed, gap, or stopping position. Keep this branch independent. It has not been deployed.
