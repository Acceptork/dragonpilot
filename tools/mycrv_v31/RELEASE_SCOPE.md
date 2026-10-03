# my-crv v3.1 RC scope

`CLOSED_COURSE_VALIDATION_REQUIRED`. This release candidate is for offline and
closed-course evaluation. It is not a road-safety certification, and it must
not be installed automatically.

The RC starts from longitudinal v3 commit
`a201e6cb75296bb1700dadf9268d857a9a597016`. Its new changes are limited
to Traditional Chinese UI text, an opt-in read-only longitudinal debug HUD,
guarded deploy/rollback tools, loggerd bookmark retention across a route
segment boundary, and a separately tested explicit RESUME set-speed restore
after a MAIN cycle. RESUME changes only the cruise helper on the driver's
button release; the route has no such episode, so closed-course validation
is required. Planner, Honda CAN mapping, steering, panda safety, and AGNOS
logic are unchanged by the new RC commits.

The following independent candidates are **not in this RC**:

- First-SET 30 km/h and long-press 10 km/h cruise changes: their isolated
  full-route replays lost generated Honda brake requests. The separately
  tested RESUME fix is included, but actual MAIN-to-RESUME behavior was not
  present in the archived route.
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
open. A user bookmark retains the current and two preceding full segments;
the logger also marks segments entered during the following ten seconds.

Only consider deployment after this exact RC commit passes native build,
Honda/longitudinal/panda tests, 42/42 continuous process replay, generated CAN
comparison and the safety gate. Deployment remains a separate user decision.
