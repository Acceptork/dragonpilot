# NOT_FOR_DEPLOYMENT — software gates pending

Independent early-stop experimental implementation based on v3.2 RC 80e1901.
Default OFF: dp_exp_early_stop. No production or closed-course readiness claim yet.
Only a bounded additional negative acceleration offset; no terminal hold,
shouldStop override, FCW override, panda changes or invented stopping coordinates.
Live switch OFF immediately removes the experimental offset.
Intervention logs: MYCRV_EXPERIMENTAL, including target before/after and context.
