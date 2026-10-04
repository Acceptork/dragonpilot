# V3.3.1 bounded recovery research — NOT DEPLOYABLE

This branch explores conservative e2e selection during otherwise eligible free cruise. It does not change MPC objectives, following distance, panda safety, Honda actuator limits, terminal taper, or HOLD. No vehicle was deployed and no production version or release tag was issued.

Control code tested: `f1a3d9a79747eaf89275aae96497a81ff638ff16`. The base is `cf42fa536c8aeac153d3855129deac5591eee1eb`. Subsequent documentation/tool commits do not change that control implementation.

## Implementation

A separate free-cruise / recent-curve-exit state requires cluster-speed deficit, valid fresh inputs, active Honda longitudinal ownership, no lead, no unknown lead memory, no stop/model deceleration, no FCW/hard-brake, low current curvature and a clear model forecast spanning approximately 4.7 seconds. The blend approaches a bounded MPC endpoint without selecting MPC outright. Maximum added recovery envelope is 0.8 m/s², further restricted by existing caps, with gradual upward authority and immediate safety exit. Downstream stop/memory stages remain authoritative. See the module and tests for exact predicates. This is not a traffic-light detector.

## Observations and failed release gates

- Training free-cruise mean positive final target: 0.141 → 0.318 m/s²; held-out free-cruise: 0.090 → 0.498 m/s². The preceding three-second active windows include zero outputs. These are fixed-input commands, not observed vehicle gains.
- The target curve-exit problem did not improve: the existing turn cap remained decisive. No independent curve-exit success is claimed.
- A designated stopping holdout had 27 early positive recovery frames, maximum +0.395 m/s². This reproduced both with historical recorded settings and with all eight experimental flags enabled in a separate 49,304-frame run (recorded CarParams retained). It preceded the independently reviewed red transition and did not alter the original braking onset, but violates the strict no-recovery-in-stop-window criterion. Position consequences are unproved. The holdout was not reused to tune away this result.
- Existing lead UNKNOWN behavior remains: current absence is not reliable departure evidence.
- Native build passed; 317 longitudinal/Honda tests passed; 315 Honda safety tests passed with 255 platform skips.
- 237,618 native planner frames were replayed, covering the 41 annotated windows and six historical safety windows. No lost FCW/shouldStop, weaker negative target, new solver error, or invalid positive recovery was found in signal-level comparisons. Scene-level safety still fails.
- Staged native process A/B was executed for 57 segment jobs. CAN release acceptance is **not** claimed: unchanged-code A/A already has message-alignment and CONTROL_ON differences. This infrastructure limitation must be resolved before interpreting small CAN differences causally.
- Baseline fidelity is imperfect in an existing post-selector experiment (about 0.1 m/s² difference from a recorded target window); planner replay is not presented as exact road reproduction.

**EFFECTIVENESS_GATE: FAIL. SAFETY_GATE: FAIL. HOLDOUT_GATE: FAIL. FULL_REPLAY: NOT_PASS for release acceptance. Status: RESEARCH_ONLY / NOT_DEPLOYABLE.**

Three events informed this iteration; all remaining annotation events and historical safety cases were excluded from parameter selection. Previously reviewed data is not blind validation. The Honda response reference is descriptive only and was not used to silently zero unsupported recovery cells.

## Reproduce with private inputs

Export the baseline planner from the base commit to a local file. Set `RECOVERY_BASELINE_SOURCE` to it, `RECOVERY_INPUT_ROOT` to a directory of route/segment/rlog.zst folders, `RECOVERY_EVENT_MANIFEST` to private JSON containing an `events` array with `id`, `route`, and `t`, and `RECOVERY_REPLAY_OUTPUT` to a private output directory. Use the built native environment to run `tools/honda_like_research/replay_recovery_v331.py`. A single-segment smoke of this portable tool was executed successfully.

Private routes, exact event times, driver responses, raw CAN/video and device Params are intentionally absent from this publication. Published results do not establish road-driving behavior or authorize deployment.
