# Overtake pre-acceleration research candidate

This branch is **research only**. The offline prototype in
tools/mycrv_v31/overtake_preaccel_research.py is not imported by plannerd,
modeld, controlsd or card. It sends **no acceleration or CAN command**.

It requires a new directional blinker followed by a fresh matching driver
steering-torque onset, then a model laneChangeStarting transition. It also
requires active longitudinal and lateral control, a meaningful cruise gap, no
stop/brake/FCW/cut-in indication, and a conservative margin to the original
lead. The original lead is never discarded merely because the driver signaled
an overtake. A lost lead does not prove clearance.

The Stage 1 numerical preview is deliberately **not connected** to the MPC:
the current MPC lead obstacle and danger-zone terms are soft costs, so adding
positive acceleration after solving or reducing smoothness costs has not been
shown to preserve original-lane distance. Stage 2 is available only if a
trusted external path-clear signal is supplied; this repository does not
currently produce one. The available private driving record does not
establish a safe original-lane margin and verified path clearance for this
feature. Its event-specific measurements remain outside this branch.

**CLOSED_COURSE_VALIDATION_REQUIRED** and target-lane sensing/research are
required before any control integration. The driver remains responsible for
mirror and adjacent-lane checks. This branch must stay outside v3.1 RC.
