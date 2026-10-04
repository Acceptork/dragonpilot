# Honda-like longitudinal research — RESEARCH_ONLY / NOT_DEPLOYABLE

This branch contains an isolated pre-selector recovery proposal and its tests.
Production controls, Honda command mapping, safety, UI and Params defaults are unchanged.
The observed reference supports steady cruise, not positive-deficit recovery: the
proposal falls back to existing output on every replayed frame. No driving improvement
is demonstrated. This is not an installation or deployment release.

All 41 driver classifications are complete; free text is optional. The frozen split is
18 TRAIN / 10 VALIDATION / 13 HOLDOUT. Previously reviewed events are tuning-excluded,
not blind validation. Public artifacts contain aggregate results only: no route IDs,
precise event timestamps, per-event driver classifications, raw CAN, video, or Params.

Tests: `python -m unittest discover -s tools/honda_like_research -p 'test_*.py'`.
The native harness requires a separately supplied private 41-event SPLIT_MANIFEST.json
and locally retained logs. Set OPENPILOT_RESEARCH_TREE, PRIVATE_RESEARCH_ROOT,
PRIVATE_RAW_ROOT (and PRIVATE_LEGACY_RAW_ROOT for --legacy-only). It intentionally
refuses an empty event manifest. Store the reference and private manifest inside
PRIVATE_RESEARCH_ROOT/overnight_20261005. The hard-coded output subdirectory is an
analysis run name, not an event timestamp.

Fixed-input planner/MPC replay is not a closed-loop vehicle plant. The separate native
plannerd/controlsd/card coverage audit uses current production; the proposal is not
wired into that process. Zero changes cannot establish efficacy or a deployment gate.
