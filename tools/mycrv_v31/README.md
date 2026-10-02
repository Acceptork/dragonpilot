# my-crv v3.1 release and rollback scripts

`CLOSED_COURSE_VALIDATION_REQUIRED`. These scripts prepare an exact, reviewed
RC commit for a parked comma device. They do not certify road use, and the
repository's AGNOS or panda safety code is not updated by this workflow.

## Before using

Publish `my-crv-v3.1-rc1` branch and annotated tag, record their exact commit
SHA, and review the candidate report. Keep the device on the known clean v2
checkout `a1e028371cdfe87471f694c87fc3d17060f969c4`. The script refuses
an onroad device, a dirty tree, another starting commit, an unexpected origin,
or a mismatched release tag / AGNOS version. It does not use an installer URL.

## One command from the home computer (recommended)

From a local clone that contains this file:

```bash
bash tools/mycrv_v31/deploy_remote.sh <COMMA_IP> <EXACT_RC_COMMIT_SHA>
```

This streams `deploy.sh` over SSH, waits for SSH to return after reboot, and
runs `verify.sh` on the device. A lost SSH connection without the explicit
`DEPLOY_READY` marker is a failure, not proof of a successful reboot.

Alternatively, after SSH into comma, run the published GitHub **source script**
with the exact SHA (this is not an installer URL):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Acceptork/dragonpilot/my-crv-v3.1-rc1/tools/mycrv_v31/deploy.sh) <EXACT_RC_COMMIT_SHA>
```

Then, after reconnecting from a separate terminal, run:

```bash
ssh comma@<COMMA_IP> 'bash /data/mycrv_v31_backup/verify.sh <EXACT_RC_COMMIT_SHA>'
```

The script creates `/data/mycrv_v31_backup/<UTC timestamp>/` and a stable
`/data/mycrv_v31_backup/rollback.sh`. It saves the original branch and exact
commit, creates a backup Git branch, fetches the annotated release tag,
verifies the requested SHA, checks protected files, builds, syncs, and reboots.
On a pre-reboot error after checkout, it attempts to return to the original
branch. It never uses `git clean`, never overwrites a dirty working tree, and
does not delete routes, SSH keys, Params, or `/persist`.

## One command to restore v2

After SSH into the parked, offroad device:

```bash
bash /data/mycrv_v31_backup/rollback.sh
```

Rollback checks the saved backup branch and exact v2 SHA, builds v2, and
reboots. If a build fails, it stays on the v2 source checkout and does not
reboot. The rollback metadata and backup branch remain available for audit.
