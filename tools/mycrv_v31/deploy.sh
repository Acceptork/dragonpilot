#!/usr/bin/env bash
# my-crv v3.1 on-device deployment. Run only while parked, after RC approval.
set -Eeuo pipefail

BASE_SHA=a1e028371cdfe87471f694c87fc3d17060f969c4
RELEASE_TAG=my-crv-v3.1-rc1
OPENPILOT_DIR=/data/openpilot
BACKUP_ROOT=/data/mycrv_v31_backup

die() { printf 'mycrv deploy: %s\n' "$*" >&2; exit 1; }
usage() { printf 'Usage: bash deploy.sh <exact 40-character RC commit SHA>\n'; }

if [[ "${1:-}" == "--help" ]]; then usage; exit 0; fi
[[ $# -eq 1 ]] || { usage >&2; exit 2; }
TARGET_SHA=$1
[[ $TARGET_SHA =~ ^[0-9a-f]{40}$ ]] || die 'target must be an exact lowercase 40-character commit SHA'

# These checks prevent running this script on a development computer or an onroad device.
[[ $(uname -m) == aarch64 ]] || die 'expected an aarch64 comma device'
[[ -d $OPENPILOT_DIR/.git && -f $OPENPILOT_DIR/launch_chffrplus.sh ]] || die 'not an openpilot Git checkout at /data/openpilot'
[[ -r /data/params/d/IsOffroad && $(cat /data/params/d/IsOffroad) == 1 ]] || die 'vehicle must report IsOffroad=1'
[[ -r /VERSION ]] || die 'device AGNOS version is unavailable'
command -v git >/dev/null || die 'git is unavailable'
command -v scons >/dev/null || die 'scons is unavailable'
command -v sudo >/dev/null || die 'sudo is unavailable'

cd "$OPENPILOT_DIR"
[[ $(git rev-parse --show-toplevel) == "$OPENPILOT_DIR" ]] || die 'unexpected Git root'
[[ -z $(git status --porcelain --untracked-files=normal) ]] || die 'working tree is dirty; no files were changed'
CURRENT_SHA=$(git rev-parse HEAD)
CURRENT_BRANCH=$(git branch --show-current)
[[ $CURRENT_SHA == "$BASE_SHA" && $CURRENT_BRANCH == my-crv-long-tune-v2 ]] || die "expected deployed v2 branch and $BASE_SHA; found $CURRENT_BRANCH $CURRENT_SHA"
REMOTE_URL=$(git remote get-url origin)
case "$REMOTE_URL" in
  https://github.com/Acceptork/dragonpilot.git|git@github.com:Acceptork/dragonpilot.git) ;;
  *) die "unexpected origin: $REMOTE_URL" ;;
esac

# The tag must be published and the caller must pin its exact commit.
git fetch --no-tags origin "refs/tags/$RELEASE_TAG" || die 'release tag could not be fetched'
FETCHED_SHA=$(git rev-parse 'FETCH_HEAD^{commit}')
[[ $FETCHED_SHA == "$TARGET_SHA" ]] || die "release tag resolves to $FETCHED_SHA, not requested $TARGET_SHA"
git cat-file -e "$TARGET_SHA^{commit}" || die 'target commit is unavailable'
git cat-file -e "$TARGET_SHA:tools/mycrv_v31/verify_runtime.py" || die 'release lacks post-reboot verification code'

# No AGNOS, bootloader, partition, panda safety, or vehicle safety-model edits.
if ! git diff --quiet "$BASE_SHA" "$TARGET_SHA" -- \
  launch_env.sh launch_chffrplus.sh system/hardware panda \
  opendbc_repo/opendbc/safety; then
  die 'release changes protected OS, boot, or safety files'
fi
TARGET_AGNOS_VERSION=$(git show "$TARGET_SHA:launch_env.sh" | sed -nE 's/^[[:space:]]*export AGNOS_VERSION="([^"]+)".*/\1/p' | head -n 1)
[[ -n $TARGET_AGNOS_VERSION && $(cat /VERSION) == "$TARGET_AGNOS_VERSION" ]] || die 'device and target AGNOS versions differ; refusing update'

umask 077
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR=$BACKUP_ROOT/$STAMP
[[ ! -e $BACKUP_DIR ]] || die 'backup timestamp already exists; retry later'
mkdir -p "$BACKUP_DIR"
BACKUP_BRANCH=mycrv-v31-backup-$STAMP
git branch "$BACKUP_BRANCH" "$BASE_SHA"
printf 'baseline_sha=%s\nbaseline_branch=%s\nbackup_branch=%s\ntarget_sha=%s\nrelease_tag=%s\ncreated_utc=%s\n' \
  "$BASE_SHA" "$CURRENT_BRANCH" "$BACKUP_BRANCH" "$TARGET_SHA" "$RELEASE_TAG" "$STAMP" > "$BACKUP_DIR/state.env"
git show "$TARGET_SHA:tools/mycrv_v31/rollback.sh" > "$BACKUP_DIR/rollback.sh"
git show "$TARGET_SHA:tools/mycrv_v31/verify.sh" > "$BACKUP_DIR/verify.sh"
bash -n "$BACKUP_DIR/rollback.sh" "$BACKUP_DIR/verify.sh"
chmod 700 "$BACKUP_DIR/rollback.sh" "$BACKUP_DIR/verify.sh"
cp "$BACKUP_DIR/rollback.sh" "$BACKUP_ROOT/rollback.sh"
cp "$BACKUP_DIR/verify.sh" "$BACKUP_ROOT/verify.sh"
printf '%s\n' "$BACKUP_DIR" > "$BACKUP_ROOT/current"

SWITCHED=0
restore_on_exit() {
  local status=$?
  trap - EXIT
  if [[ $status -ne 0 && $SWITCHED == 1 ]]; then
    printf 'deploy failed before reboot; restoring and rebuilding %s\n' "$BASE_SHA" >&2
    if git switch "$CURRENT_BRANCH" && [[ $(git rev-parse HEAD) == "$BASE_SHA" ]]; then
      if scons -j1 > "$BACKUP_DIR/recovery-build.log" 2>&1; then
        printf 'v2 source and build restored; no reboot requested\n' >&2
      else
        printf 'v2 source restored but recovery build FAILED; device must remain parked. See %s\n' \
          "$BACKUP_DIR/recovery-build.log" >&2
        status=1
      fi
    else
      printf 'FAILED to restore v2 checkout; device must remain parked for manual recovery\n' >&2
      status=1
    fi
  fi
  exit "$status"
}
trap restore_on_exit EXIT

git switch -C "$RELEASE_TAG" "$TARGET_SHA"
SWITCHED=1
[[ $(git rev-parse HEAD) == "$TARGET_SHA" ]] || die 'checkout SHA mismatch'
if ! scons -j4 > "$BACKUP_DIR/build.log" 2>&1; then
  printf 'parallel build failed; retrying serially\n' >&2
  scons -j1 >> "$BACKUP_DIR/build.log" 2>&1 || { tail -n 60 "$BACKUP_DIR/build.log" >&2; die 'build failed'; }
fi
[[ -z $(git status --porcelain --untracked-files=normal) ]] || die 'build left tracked or untracked source changes'
[[ $(git rev-parse HEAD) == "$TARGET_SHA" ]] || die 'post-build SHA mismatch'
printf 'DEPLOY_READY %s; backup %s; rebooting\n' "$TARGET_SHA" "$BACKUP_DIR"
sync
sudo reboot
