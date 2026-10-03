# my-crv v3.2 — RESEARCH / NOT_FOR_DEPLOYMENT

Status: **BLOCKED_LATERAL_VALIDATION: helper tests pass; modeld closed-loop and vehicle EPS capability unverified.**

Baseline: `c791595652c2b7e24bbdf7165f65d4b217b08c4e` (`my-crv-v3.1-rc1`).
Tested runtime commit: `aa15cbd916b4e205bfc22305edb180d45c7179f0`. This final publication change is documentation only.
Device connection, deployment and reboot: **NOT RUN**. No production tag.

Native replay reuses fixed recorded CAN/model inputs; it is not a calibrated vehicle closed loop.
UI target changes are evaluated with fixed-target identity, button-specific shared prefixes, and RC/new-target-history counterfactuals.
No arbitrary tolerance discards lost BRAKE_REQUEST. Every directional difference is retained with target/history context.
FCW, stop, lead, engagement, Honda and panda constraints remain mandatory.

Local evidence: `V32_DEVELOPMENT_REPORT.md` and `v32_results/` in the Taifly workspace.
Raw route/video data is not included in this branch.

此車型無可靠盲點資料，變換車道前請自行確認後方安全。
方向燈＋新同方向駕駛 torque 確認；helper 無速度/BSM gate，實際 steering 仍尊重 lateralActive 與 Honda/EPS/panda 能力。
