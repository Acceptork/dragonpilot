# my-crv v3.1 RC scope

`CLOSED_COURSE_VALIDATION_REQUIRED`. This release candidate is for offline and
closed-course evaluation. It is not a road-safety certification, and it must
not be installed automatically.

The RC starts from longitudinal v3 commit
`a201e6cb75296bb1700dadf9268d857a9a597016`. Its new changes are limited
to Traditional Chinese UI text, an opt-in read-only longitudinal debug HUD,
and guarded deploy/rollback tools. The UI reads control state but does not
change planner, controller, Honda CAN, steering, panda safety, or AGNOS logic.

The following independent candidates are **not in this RC**:

- First-SET 30 km/h and long-press 10 km/h cruise changes: the independent
  cruise branch lost generated Honda brake requests in a full-route replay.
- Experimental stop hold and low-speed brake shaping: event_041 stopping
  remains unresolved; the independent stop branch changed stationary commands.
- Low-speed driver-confirmed lane change: physical low-speed EPS behavior and
  side-traffic safety are unverified.
- Overtake pre-acceleration: the separate branch tests intent gating, but has
  no production acceleration command and no verified old-lead path clearance.
- Steering return, lead dropout memory, EPS-aware acceleration, personality
  recovery, and automatic restart changes: no validated production control
  change is included.

The existing v3 low-speed Honda gas candidate is inherited from the base. Its
real vehicle stop, creep, hill, and restart behavior still needs closed-course
measurement. Event_041 and motorcycle/cut-in perception limitations remain
open. The existing bookmark mechanism does not guarantee a preserved full
10 seconds after a mark near a route-segment boundary.

Only consider deployment after this exact RC commit passes native build,
Honda/longitudinal/panda tests, 42/42 continuous process replay, generated CAN
comparison and the safety gate. Deployment remains a separate user decision.
