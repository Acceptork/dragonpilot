# NOT_FOR_DEPLOYMENT — software gates pending

Default OFF dp_exp_lead_memory; sidecar shadow always records association decisions.
Active adds a separate MPC constraint and takes min(existing target, memory target),
ORs stop/FCW, never publishes altered radarState. New closer measured lead wins immediately.
0.2/0.3/0.5 s synthetic sweep, default .3. Unknown after expiration prevents positive
recovery until reliable reacquire or driver OFF; this deliberate limitation is logged.
Never-seen leads are PERCEPTION_LIMITATION, not repaired perception.
