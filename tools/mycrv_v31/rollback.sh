#!/usr/bin/env bash
# Stable copy is installed at /data/mycrv_v31_backup/rollback.sh by deploy.sh.
set -Eeuo pipefail

BASE_SHA=a1e028371cdfe87471f694c87fc3d17060f969c4
OPENPILOT_DIR=/data/openpilot
BACKUP_ROOT=/data/mycrv_v31_backup
die() { printf 'mycrv rollback: %s\n' "$*" >&2; exit 1; }

[[ $(uname -m) == aarch64 ]] || die 'expected an aarch64 comma device'
[[ -d $OPENPILOT_DIR/.git ]] || die 'openpilot Git checkout missing'
[[ -r /data/params/d/IsOffroad && $(cat /data/params/d/IsOffroad) == 1 ]] || die 'vehicle must report IsOffroad=1'
[[ -r $BACKUP_ROOT/current ]] || die 'deployment backup pointer missing'
BACKUP_DIR=$(cat "$BACKUP_ROOT/current")
case "$BACKUP_DIR" in "$BACKUP_ROOT"/*) ;; *) die 'invalid backup path' ;; esac
[[ -r $BACKUP_DIR/state.env ]] || die 'rollback metadata missing'
grep -Fxq "baseline_sha=$BASE_SHA" "$BACKUP_DIR/state.env" || die 'rollback metadata has another baseline'
BACKUP_BRANCH=$(sed -n 's/^backup_branch=//p' "$BACKUP_DIR/state.env" | head -n 1)
[[ $BACKUP_BRANCH =~ ^mycrv-v31-backup-[0-9]{8}T[0-9]{6}Z$ ]] || die 'invalid backup branch'
TARGET_SHA=$(sed -n 's/^target_sha=//p' "$BACKUP_DIR/state.env" | head -n 1)
[[ $TARGET_SHA =~ ^[0-9a-f]{40}$ ]] || die 'invalid target commit in rollback metadata'

cd "$OPENPILOT_DIR"
[[ $(git rev-parse --show-toplevel) == "$OPENPILOT_DIR" ]] || die 'unexpected Git root'
[[ -z $(git status --porcelain --untracked-files=normal) ]] || die 'working tree is dirty; no files were changed'
[[ $(git rev-parse "$BACKUP_BRANCH^{commit}") == "$BASE_SHA" ]] || die 'backup branch no longer points to v2'
if [[ $(git rev-parse HEAD) == "$BASE_SHA" ]]; then
  printf 'already at v2 %s; no reboot needed\n' "$BASE_SHA"
  exit 0
fi
CURRENT_SHA=$(git rev-parse HEAD)
CURRENT_BRANCH=$(git branch --show-current)
[[ $CURRENT_SHA == "$TARGET_SHA" && $CURRENT_BRANCH == my-crv-v3.1-rc1 ]] || die 'current checkout differs from the recorded release; manual review required'

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
git branch "mycrv-v31-before-rollback-$STAMP" HEAD
git switch -C my-crv-long-tune-v2 "$BASE_SHA"
[[ $(git rev-parse HEAD) == "$BASE_SHA" ]] || die 'v2 checkout SHA mismatch'
if ! scons -j4 > "$BACKUP_DIR/rollback-build.log" 2>&1; then
  if ! scons -j1 >> "$BACKUP_DIR/rollback-build.log" 2>&1; then
    tail -n 60 "$BACKUP_DIR/rollback-build.log" >&2
    printf 'v2 build failed; attempting to restore the previously built RC\n' >&2
    if git switch -C "$CURRENT_BRANCH" "$CURRENT_SHA" && [[ $(git rev-parse HEAD) == "$CURRENT_SHA" ]] &&
       scons -j1 > "$BACKUP_DIR/rollback-recovery-build.log" 2>&1; then
      die 'ROLLBACK_ABORTED: prior RC source/build restored; no reboot requested'
    fi
    die 'RECOVERY_BLOCKED: neither v2 nor RC build completed; keep the device parked and repair manually'
  fi
fi
[[ -z $(git status --porcelain --untracked-files=normal) ]] || die 'v2 build left source changes; no reboot'
printf 'ROLLBACK_READY %s; rebooting\n' "$BASE_SHA"
sync
sudo reboot
