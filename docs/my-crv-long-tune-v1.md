# my-crv CR-V 5G Bosch longitudinal review and v1 tune

Baseline: `my-crv` at `418216c4f8b87403aa22177a998af8c7b5c77a8c` (clean checkout). The local backup tag is `my-crv-before-long-tune`; work is on `my-crv-long-tune-v1`.

## Control path

1. `opendbc_repo/opendbc/car/honda/carstate.py` reads Honda CAN wheel and transmission speeds, applies `wheelSpeedFactor=1.025` for CR-V 5G, and filters `vEgo/aEgo`. `selfdrive/car/card.py` and `selfdrive/car/cruise.py` produce `vCruise` and `vCruiseCluster` (km/h; unset=255, max=145).
2. `selfdrive/controls/radard.py` combines radar points with `modelV2.leadsV3`. For this Bosch platform, `interface.py` sets `radarUnavailable=True`, so normal leads are vision-derived. Lead probability rises immediately but falls through a 0.2 s first-order filter; the lead threshold is 0.5. Vision `aLeadTau=0.3`; tracked radar default is 1.5. `radarDelay=0.1` is in Honda CarParams.
3. `selfdrive/controls/plannerd.py` samples `carState`, `radarState`, `modelV2`, `selfdriveState`, `controlsState`, `carControl`, and `liveParameters` at model rate. It latches ACM/AEM/APM flags at startup. With all three off, `longitudinal_planner.py` still uses `gasPressProbs[1]` to cap acceleration when it is at or below 0.4. It also applies set speed, turn acceleration, pitch-dependent coasting, `forceDecel`, and mode choice.
4. `selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py` forms cruise and two lead obstacles, selects the nearest at the current step, and solves an acceleration and jerk trajectory. `drive_helpers.get_accel_from_plan` samples it at `longitudinalActuatorDelay + DT_MDL` = about 0.55 s for Bosch. The planner clips the output to its acceleration envelope, whose bounds change by at most 0.05 m/s² per model cycle.
5. `selfdrive/controls/controlsd.py` calls `LongControl.update(aTarget, shouldStop)`. `longcontrol.py` applies the stopping/starting state machine and an acceleration PID. CR-V Bosch inherits `kp=0`, `ki=0` from the base interface, so the active control output is effectively feedforward `aTarget`, clipped to Bosch `[-3.5, 2.0]` m/s². This is not an integral windup issue on this platform.
6. `opendbc_repo/opendbc/car/honda/carcontroller.py` sends Bosch longitudinal commands at 50 Hz. It clips acceleration to `[-3.5, 2.0]`, maps gas linearly from acceleration `-0.2..2.0` to `0..1600`, and does not add a longitudinal rate limiter. `hondacan.py` sends `ACC_CONTROL.ACCEL_COMMAND`, `GAS_COMMAND`, brake bits, and standstill bits. `opendbc_repo/opendbc/safety/modes/honda.h` independently enforces `[-3.5, 2.0]` acceleration and a gas maximum of 2000; no safety file was changed.

## Values and findings

| Area | Baseline and effect | v1 action |
| --- | --- | --- |
| Cruise acceleration | `A_CRUISE_MAX_BP=[0,10,25,40]` m/s and values `[1.6,1.2,0.8,0.6]` m/s². At 70/90/100 km/h the upper envelope is about 0.95/0.80/0.76 m/s². Could limit 70–100 km/h recovery. | Hold unchanged until actual `aTarget`, actuator, and vehicle acceleration are measured. |
| Model throttle gate | A gas probability at or below 0.4 caps maximum planned acceleration toward pitch-derived coast (about `-0.3` m/s² on level road), even in normal ACC with a large cruise deficit. This is the clearest explanation for long underspeed or hesitant acceleration. Missing orientation avoids this cap. | After a stable clear path and large speed deficit, allow the existing MPC acceleration envelope. See the table below. |
| Lead response | Standard `T_FOLLOW=1.45` s and `STOP_DISTANCE=6` m. `COMFORT_BRAKE=2.5`; `LEAD_DANGER_FACTOR=0.75` and danger cost 100. Vision lead probability/filtering and acceleration extrapolation can add lag. | Preserve all spacing, braking, and obstacle costs. Only lift the model coast cap if every observed lead is pulling away beyond the existing desired gap. |
| MPC comfort | Standard and relaxed jerk factor are 1.0; aggressive is 0.5. `J_EGO_COST=5`, `A_CHANGE_COST=200` near the horizon start, decaying to zero by 2 s. These could contribute to slow acceleration buildup but need measured trajectories. | No cost change in v1. |
| Set speed overshoot | The 0.5 s Bosch delay plus 0.05 s model cycle and acceleration feedback can affect overshoot. Cruise obstacle is designed for smooth approach. `kp/ki=0` means no integral residue here. Cluster speed and filtered `vEgo` may differ. | Keep delay and feedforward unchanged. Release the new override within 2.5 km/h of set speed; log both cruise speeds and control terms. |
| Stopping/starting | `shouldStop` comes from the plan; `stopAccel=-2.0` normally, `stoppingDecelRate=0.8` m/s³, `vEgoStopping=vEgoStarting=0.5` m/s; Bosch radarless has a separate stop acceleration. | Unchanged. |
| ACM/AEM/APM | Disabled flags mean ACM coasting, AEM mode switching, and APM personality switching are bypassed. If enabled later, ACM uses a 0.98 cruise-speed ratio, 3 s lead TTC gate and 0.5 s lead cooldown; AEM uses 0.4/0.6 model gas-probability mode thresholds; APM selects aggressive below 60 km/h and returns to the chosen personality above 70 km/h. Normal planner model throttle gating is independent of these flags. | Unchanged. |
| Experimental/blended | Experimental mode chooses blended and takes `min(model desired acceleration, MPC target)`; normal mode uses MPC. With AEM off, model desired acceleration does not replace MPC, but model gas probability still controls the coast cap. | Unchanged. |
| Honda CAN | Bosch command clipping and gas map are explicit; Nidec brake hysteresis and Nidec speed-near-cruise PID limit do not apply to CR-V 5G. | Unchanged. |

The code does not establish that any one of the reported road behaviours has a single cause. The logger is intended to distinguish planner limits, lead constraints, set speed input, and actual actuator response on the next drive.

### Requested A–N audit

| Item | Code finding |
| --- | --- |
| A/B | Low `gasPressProbs[1]` can cap positive acceleration while far below `vCruise`, regardless of lead clearance. Confirmed. |
| C | Vision lead confidence and MPC obstacle prediction may delay recovery; native synthetic pullaway test measures the response, but road latency remains unknown. |
| D | Standard headway is 1.45 s, a deliberate comfort target; no evidence it is excessive for this car. |
| E/F | Jerk cost 5 and acceleration-change cost 200 can make acceleration build smoothly; contribution to reported hesitation cannot be isolated without logged trajectories. |
| G | Bosch delay is 0.5 s and planner uses about 0.55 s. No vehicle step-response measurement yet to justify changing it. |
| H | Bosch controller clips to `[-3.5,2.0]` and sends at 50 Hz; no additional longitudinal smoothing in its Python path. |
| I | The 70–100 km/h acceleration envelope is about 0.95 down to 0.76 m/s²; candidate remains below it. |
| J | MPC's cruise obstacle and long delay are plausible overshoot contributors. Synthetic approach tests can only model an idealized plant. |
| K | Bosch CR-V inherited `kp=ki=0`; acceleration feedforward is active, so PID integral residue is not the cause in this source. |
| L | Lead probability falls through a 0.2 s filter and vision matching uses a 0.5 threshold; no extra lead reacquisition timer was found. |
| M | Experimental mode OFF keeps ACC target selection, but model gas probability still gates acceleration. |
| N | ACM/AEM/APM are OFF, so their custom logic does not run; the always-on model throttle gate is the relevant custom interaction. |

### v1 changes, recorded before deployment

| Change | Old | New | Reason and expected effect | Possible side effect |
| --- | --- | --- | --- | --- |
| Low model gas probability | `allowThrottle=False` whenever `gasPressProbs[1] <= 0.4` above 2.5 m/s, then positive acceleration clipped to coast | Override after 0.5 s of valid radar state, active longitudinal control, ACC mode, set speed deficit ≥10 km/h, and a clear path. The model must request at least -0.1 m/s², with no `shouldStop` or `hardBrakePredicted`; pitch must be finite and within ±0.05 rad when available. With an observed lead, require `vRel>=0.5` m/s and `dRel` at least 2 m beyond the existing desired gap. Keep override until deficit ≤2.5 km/h. Reset after lead loss and wait 0.5 s again. | Avoid long coast at 70 when set to 90; allow measured lead pullaway to result in MPC acceleration while preserving MPC safety distance. Hysteresis avoids repeated coast/accelerate near the entry threshold. | More positive acceleration than baseline during low model throttle probability; a falsely absent lead could allow pursuit after 0.5 s, still bounded by MPC, turn limit, Honda controller and panda. |
| Diagnostic recorder | No dedicated bounded longitudinal CSV | Separate manager process, 10 Hz whenever openpilot is engaged, `/data/mycrv_long_debug`, 20 MB per file, newest 10 files, only for `HONDA_CRV_5G`; process has lower CPU priority and does no writing in control loops. `longActive` records whether openpilot actually controls the longitudinal axis. | Reveal model gate, lead, plan, command and actual vehicle response without video/GPS/audio or NVMe dependency, including when stock ACC remains in control. | Up to 200 MB of UFS space and small CPU/I/O cost. Write failures back off for 60 s. |

No first-version change to the acceleration envelope, jerk or acceleration-change costs, follow time, actuator delay, PID, Honda controller, CAN packing, FCW logic, AEB logic, AGNOS, bootloader, partitions, or panda safety limits.

## Safety note from the baseline

The baseline `opendbc_repo/opendbc/car/honda/interface.py` explicitly disables the Bosch radar ECU when openpilot longitudinal is enabled and comments that this disables stock CMBS, including AEB and FCW. `carstate.py` only publishes Bosch `stockAeb` when openpilot longitudinal is **off**. Openpilot model/planner FCW alerts remain in `selfdrive/selfdrived/selfdrived.py`; they are not equivalent to stock automatic emergency braking. This v1 change neither introduces nor reverses that existing configuration. Verify the actual device's `openpilotLongitudinalControl` and user expectations before any road use.

## Verification and deployment gate

Local Windows checks: syntax compile for all nine changed Python files and `git diff --check` passed. There is no recorded rlog in this checkout. The comma native environment imported the original planner and controlsd/plannerd, imported staged candidate modules and manager configuration, and ran all 11 candidate unit tests successfully. Six synthetic scenarios were run with both baseline and candidate native MPC without opening CAN; the results are below. The final full following-distance and maneuver run passed all cases except the two NaN recovery subtests (ACC and blended), which fail the same way on the untouched baseline due to MPC solver status 3/4. An initial candidate strong-pitch regression was fixed; the isolated strong-pitch case now matches baseline in both modes and passes the final full run. Honda interface tests: 2 passed. Honda Bosch longitudinal panda safety tests: 29 passed, 4 skipped. No live on-road startup test is possible while the device is offroad. These checks were performed before deployment.

| Native synthetic scenario | Baseline | Candidate v1 | Scope |
| --- | --- | --- | --- |
| Set 90 at 70, no lead, gas probability 0.05 | `allowThrottle=False`; `aTarget=0.50` m/s² at 1.5 s | Gate opens at 0.5 s; `aTarget=0.948` at 1.5 s | Fixed ego speed, native MPC |
| Set 90 at 85, no lead, gas probability 1.0 | At 6 s, idealized ego 89.64 km/h, `aTarget=0.068` | Same | Idealized acceleration-to-speed update; no Honda dynamics |
| Lead at 70 then pulls away 2 m/s | Gate remains false; `aTarget=0.150` by 1.25 s after pullaway | Gate opens after 0.5 s; `aTarget=0.329` by 1.25 s | Fixed ego speed, vision-like lead fields |
| Lead disappears | First frame `aTarget=0.01`; about 0.45 s later `0.40` | Same through 0.45 s; gate opens after 0.5 s and later reaches `0.821` | Shows 0.5 s guard; road surge still unverified |
| Pitch ±0.03 rad | `aTarget=0.50` at 1.5 s with low model gas | `aTarget=0.948` at 1.5 s; below existing envelope | Fixed ego speed; no grade vehicle dynamics |
| Pitch +0.10 rad | Existing coast cap retained | Same coast cap retained after guard | Regression case isolated on native maneuver test |
| Set 90 at 75, gas probability 0.01 | Gate remains false; `aTarget=0.50` at 1.5 s | Gate opens after 0.5 s; `aTarget=0.875` at 1.5 s | Fixed ego speed, native MPC |

The candidate does not raise the 70–100 km/h acceleration envelope; it restores access to its existing upper bound when the model coast request conflicts with a large, safe cruise deficit. An actual Honda acceleration response, delay, and overshoot require a vehicle log.

Before deployment, confirm the device commit equals the baseline, run native import/startup, relevant tests and six synthetic scenarios on its Linux build, and review the complete diff. The device currently has no `CarParams` or `CarParamsCache` while offroad, so its live fingerprint and `openpilotLongitudinalControl` cannot yet be confirmed; `AlphaLongitudinalEnabled` is false, and ACM/AEM/APM/Experimental are false. Deploying this branch does not change those settings. Then fetch the backup tag and tuned branch on the device, confirm the worktree is clean, switch to the tuned branch, reboot, and check available offroad processes. Check controlsd, plannerd, UI, fingerprint, longitudinal capability, and crash logs once the car is connected and these processes can start. Do not road-test longitudinal operation until those checks pass.

## Scenario observations for the next drive

1. Straight, no lead, set 90 at 70 km/h: record time from engagement or set-speed change to positive `aTarget`, actuator acceleration and `aEgo`; include low and high gas probability cases.
2. Straight, no lead, set 90 at 85 km/h and while approaching 90: check taper and peak speed against cluster and `vEgo`; note any 3–5 km/h overshoot.
3. Follow at 70, lead accelerates toward 90: check `vRel`, `dRel`, lead source, and time until `aTarget` rises; keep standard spacing.
4. Lead disappears/reappears: inspect the first second of `aTarget`, actuator and `aEgo`; no abrupt surge or shortened spacing.
5. Level road, uphill and downhill: compare `pitch`, gas probability and `allowThrottle`; ensure coast cap does not hide a large safe speed deficit.
6. At least 15 km/h below set speed with low gas probability and no lead: confirm the model cap is lifted after the 0.5 s clear-path window, without exceeding the original envelope.

Stop the drive and revert if acceleration oscillates, overshoot grows, spacing narrows, braking weakens, or processes crash.

## One-command rollback after deployment

The device must have the `my-crv-before-long-tune` tag locally. From the tuned checkout, run `sh tools/mycrv_long_v1/rollback.sh`. It refuses a dirty worktree, switches `/data/openpilot` to branch `my-crv` at the backup tag, and reboots. Until device deployment, the same baseline is preserved by the local tag.
