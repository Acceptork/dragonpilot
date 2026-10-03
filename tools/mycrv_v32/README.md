# my-crv v3.2 — RESEARCH / NOT_FOR_DEPLOYMENT

Status: **PASS_CANDIDATE: SET30, metric buttons10, read-only diagnostics. Personality/LCA/research excluded.**

Baseline: `c791595652c2b7e24bbdf7165f65d4b217b08c4e` (`my-crv-v3.1-rc1`).
Tested runtime commit: `b890922b99865f162a2c866860eacb66bf2f4faf`. This final publication change is documentation only.
Device connection, deployment and reboot: **NOT RUN**. No production tag.

Native replay reuses fixed recorded CAN/model inputs; it is not a calibrated vehicle closed loop.
UI target changes are evaluated with fixed-target identity, button-specific shared prefixes, and RC/new-target-history counterfactuals.
No arbitrary tolerance discards lost BRAKE_REQUEST. Every directional difference is retained with target/history context.
FCW, stop, lead, engagement, Honda and panda constraints remain mandatory.

Local evidence: `V32_DEVELOPMENT_REPORT.md` and `v32_results/` in the Taifly workspace.
Raw route/video data is not included in this branch.
