#!/usr/bin/env bash
# Disposable Git / fake-device fixture. Rewrites only fixture path constants;
# production files and any physical device remain untouched.
set -Eeuo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TMP=$(mktemp -d)
cleanup() {
  local status=$?
  if [[ $status -ne 0 ]]; then
    for log in "$TMP"/*.log; do
      [[ -f $log ]] || continue
      printf '\n--- %s ---\n' "$log" >&2
      cat "$log" >&2
    done
  fi
  rm -rf "$TMP"
  exit "$status"
}
trap cleanup EXIT
REPO=$TMP/device/openpilot
BACKUP=$TMP/device/backups
PARAM=$TMP/device/IsOffroad
VERSION=$TMP/device/VERSION
ORIGIN=$TMP/origin.git
mkdir -p "$REPO" "$TMP/bin"
printf '1\n' > "$PARAM"
printf 'fixture-agnos\n' > "$VERSION"
git -C "$REPO" init -q
git -C "$REPO" config user.name 'Offline Fixture'
git -C "$REPO" config user.email 'offline@example.invalid'
printf 'export AGNOS_VERSION="fixture-agnos"\n' > "$REPO/launch_env.sh"
printf '#!/bin/sh\n' > "$REPO/launch_chffrplus.sh"
git -C "$REPO" add launch_env.sh launch_chffrplus.sh
git -C "$REPO" commit -qm 'Fake deployed v2'
git -C "$REPO" branch -M my-crv-long-tune-v2
BASE_SHA=$(git -C "$REPO" rev-parse HEAD)

export FIXTURE_SOURCE_DIR=$DIR FIXTURE_REPO=$REPO FIXTURE_BACKUP=$BACKUP
export FIXTURE_PARAM=$PARAM FIXTURE_VERSION=$VERSION FIXTURE_ORIGIN=$ORIGIN FIXTURE_BASE_SHA=$BASE_SHA
python3 - <<'PY'
from pathlib import Path
import os

src = Path(os.environ['FIXTURE_SOURCE_DIR'])
dst = Path(os.environ['FIXTURE_REPO']) / 'tools/mycrv_v31'
dst.mkdir(parents=True)
base = os.environ['FIXTURE_BASE_SHA']
replacements = {
  'BASE_SHA=a1e028371cdfe87471f694c87fc3d17060f969c4': f'BASE_SHA={base}',
  'V3_SHA=a201e6cb75296bb1700dadf9268d857a9a597016': f'V3_SHA={base}',
  'OPENPILOT_DIR=/data/openpilot': f"OPENPILOT_DIR={os.environ['FIXTURE_REPO']}",
  'BACKUP_ROOT=/data/mycrv_v31_backup': f"BACKUP_ROOT={os.environ['FIXTURE_BACKUP']}",
  '/data/params/d/IsOffroad': os.environ['FIXTURE_PARAM'],
  '/VERSION': os.environ['FIXTURE_VERSION'],
  'git@github.com:Acceptork/dragonpilot.git) ;;':
    f"git@github.com:Acceptork/dragonpilot.git|{os.environ['FIXTURE_ORIGIN']}) ;;",
}
for name in ('deploy.sh', 'rollback.sh', 'verify.sh', 'verify_runtime.py'):
  text = (src / name).read_text()
  if name in ('deploy.sh', 'rollback.sh'):
    for old, new in replacements.items():
      text = text.replace(old, new)
  (dst / name).write_text(text, newline='\n')
PY
mkdir -p "$REPO/selfdrive/car/tests"
printf '# reviewed cruise helper\n' > "$REPO/selfdrive/car/cruise.py"
printf '# reviewed RESUME tests\n' > "$REPO/selfdrive/car/tests/test_resume_v31.py"
git -C "$REPO" add tools selfdrive
git -C "$REPO" commit -qm 'Valid RC with exact RESUME paths'
VALID_SHA=$(git -C "$REPO" rev-parse HEAD)
cp "$REPO/tools/mycrv_v31/deploy.sh" "$TMP/run_deploy.sh"
git init -q --bare "$ORIGIN"
git -C "$REPO" remote add origin "$ORIGIN"

cat > "$TMP/bin/uname" <<'FAKE_UNAME'
#!/usr/bin/env bash
[[ ${1:-} == -m ]] && { echo aarch64; exit 0; }
exec /usr/bin/uname "$@"
FAKE_UNAME
cat > "$TMP/bin/scons" <<'FAKE_SCONS'
#!/usr/bin/env bash
set -Eeuo pipefail
if [[ ${FAKE_DIRTY_V2:-0} == 1 && $(git branch --show-current) == my-crv-long-tune-v2 ]]; then
  printf 'fixture build output\n' > fixture-generated-file.txt
fi
exit 0
FAKE_SCONS
cat > "$TMP/bin/sudo" <<'FAKE_SUDO'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_REBOOT_LOG"
exit 1
FAKE_SUDO
chmod +x "$TMP/bin/uname" "$TMP/bin/scons" "$TMP/bin/sudo"
export PATH="$TMP/bin:$PATH" FAKE_REBOOT_LOG=$TMP/reboots

tag_to() {
  local kind=$1 commit=$2
  git -C "$REPO" tag -d my-crv-v3.1-rc1 >/dev/null 2>&1 || true
  if [[ $kind == annotated ]]; then
    git -C "$REPO" tag -a my-crv-v3.1-rc1 "$commit" -m 'Fixture release'
  else
    git -C "$REPO" tag my-crv-v3.1-rc1 "$commit"
  fi
  git -C "$REPO" push -q -f origin refs/tags/my-crv-v3.1-rc1
}
run_from_v2() {
  local sha=$1 output=$2
  git -C "$REPO" switch -q -C my-crv-long-tune-v2 "$BASE_SHA"
  if bash "$TMP/run_deploy.sh" "$sha" > "$output" 2>&1; then
    echo 'deployment unexpectedly succeeded in fake device' >&2
    exit 1
  fi
}

# A lightweight tag is refused before any backup directory is created.
tag_to lightweight "$VALID_SHA"
run_from_v2 "$VALID_SHA" "$TMP/lightweight.log"
grep -Fq 'release tag is not annotated' "$TMP/lightweight.log" || { cat "$TMP/lightweight.log" >&2; exit 1; }
[[ ! -e $BACKUP ]] || { echo 'backup created for lightweight tag' >&2; exit 1; }

# An annotated tag to a different commit cannot silently override the caller's
# exact SHA, even when both commits exist in the local Git object store.
tag_to annotated "$VALID_SHA"
run_from_v2 "$BASE_SHA" "$TMP/wrong-sha.log"
grep -Fq 'not requested' "$TMP/wrong-sha.log"
[[ ! -e $BACKUP ]] || { echo 'backup created for wrong tag SHA' >&2; exit 1; }

# A syntactically invalid rollback script must fail before backup, too.
git -C "$REPO" switch -q -C fixture-candidate "$VALID_SHA"
printf 'if [[ \n' >> "$REPO/tools/mycrv_v31/rollback.sh"
git -C "$REPO" add tools/mycrv_v31/rollback.sh
git -C "$REPO" commit -qm 'Fixture invalid rollback'
BAD_ROLLBACK_SHA=$(git -C "$REPO" rev-parse HEAD)
tag_to annotated "$BAD_ROLLBACK_SHA"
run_from_v2 "$BAD_ROLLBACK_SHA" "$TMP/invalid-rollback.log"
grep -Fq 'release has invalid rollback.sh syntax' "$TMP/invalid-rollback.log"
[[ ! -e $BACKUP ]] || { echo 'backup created before rollback preflight' >&2; exit 1; }

# The installed post-reboot verifier is also parsed before backup creation.
git -C "$REPO" switch -q -C fixture-candidate "$VALID_SHA"
printf 'if [[ \n' >> "$REPO/tools/mycrv_v31/verify.sh"
git -C "$REPO" add tools/mycrv_v31/verify.sh
git -C "$REPO" commit -qm 'Fixture invalid verify'
BAD_VERIFY_SHA=$(git -C "$REPO" rev-parse HEAD)
tag_to annotated "$BAD_VERIFY_SHA"
run_from_v2 "$BAD_VERIFY_SHA" "$TMP/invalid-verify.log"
grep -Fq 'release has invalid verify.sh syntax' "$TMP/invalid-verify.log"
[[ ! -e $BACKUP ]] || { echo 'backup created before verify preflight' >&2; exit 1; }

# Adjacent car code may not piggyback on the exact two reviewed RESUME paths.
git -C "$REPO" switch -q -C fixture-candidate "$VALID_SHA"
printf '# unreviewed nearby file\n' > "$REPO/selfdrive/car/nearby.py"
git -C "$REPO" add selfdrive/car/nearby.py
git -C "$REPO" commit -qm 'Fixture unreviewed adjacent path'
UNREVIEWED_SHA=$(git -C "$REPO" rev-parse HEAD)
tag_to annotated "$UNREVIEWED_SHA"
run_from_v2 "$UNREVIEWED_SHA" "$TMP/unreviewed.log"
grep -Fq 'release changes an unreviewed path: selfdrive/car/nearby.py' "$TMP/unreviewed.log"
[[ ! -e $BACKUP ]] || { echo 'backup created before path preflight' >&2; exit 1; }

git -C "$REPO" switch -q -C fixture-candidate "$VALID_SHA"
printf '# unreviewed nearby test\n' > "$REPO/selfdrive/car/tests/test_neighbor.py"
git -C "$REPO" add selfdrive/car/tests/test_neighbor.py
git -C "$REPO" commit -qm 'Fixture unreviewed adjacent test'
UNREVIEWED_TEST_SHA=$(git -C "$REPO" rev-parse HEAD)
tag_to annotated "$UNREVIEWED_TEST_SHA"
run_from_v2 "$UNREVIEWED_TEST_SHA" "$TMP/unreviewed-test.log"
grep -Fq 'release changes an unreviewed path: selfdrive/car/tests/test_neighbor.py' "$TMP/unreviewed-test.log"
[[ ! -e $BACKUP ]] || { echo 'backup created before test-path preflight' >&2; exit 1; }

# Both exact RESUME paths are accepted; fake reboot denial leaves the reviewed
# source checked out and records a distinct reboot failure, with no recovery
# switch under an active shutdown request.
tag_to annotated "$VALID_SHA"
run_from_v2 "$VALID_SHA" "$TMP/reboot-failed.log"
grep -Fq 'REBOOT_REQUEST_FAILED:' "$TMP/reboot-failed.log"
[[ $(git -C "$REPO" rev-parse HEAD) == "$VALID_SHA" ]]
[[ $(git -C "$REPO" branch --show-current) == my-crv-v3.1-rc1 ]]
[[ $(cat "$BACKUP/current") == "$BACKUP/"* ]]
STATE_DIR=$(cat "$BACKUP/current")
grep -Fq 'release_tag_object=' "$STATE_DIR/state.env"
grep -Fxq 'reboot_request=failed' "$STATE_DIR/reboot-result.env"
[[ $(wc -l < "$FAKE_REBOOT_LOG") == 1 ]]

# A successful v2 build that leaves source dirty is preserved for inspection,
# with no reboot and no destructive cleanup or switch over unknown files.
export FAKE_DIRTY_V2=1
if bash "$STATE_DIR/rollback.sh" > "$TMP/rollback-dirty.log" 2>&1; then
  echo 'dirty rollback unexpectedly passed' >&2
  exit 1
fi
grep -Fq 'RECOVERY_BLOCKED: v2 build completed but its checkout is dirty' "$TMP/rollback-dirty.log"
[[ $(git -C "$REPO" rev-parse HEAD) == "$BASE_SHA" ]]
[[ -e $REPO/fixture-generated-file.txt ]]
grep -Fq 'fixture-generated-file.txt' "$STATE_DIR/rollback-dirty-status.log"
grep -Fxq 'rollback_result=build_succeeded_tree_dirty' "$STATE_DIR/rollback-result.env"
[[ $(wc -l < "$FAKE_REBOOT_LOG") == 1 ]]

# In this disposable fixture only, remove generated output and test the
# explicit rollback reboot failure after an otherwise clean v2 build.
rm "$REPO/fixture-generated-file.txt"
git -C "$REPO" switch -q -C my-crv-v3.1-rc1 "$VALID_SHA"
unset FAKE_DIRTY_V2
sleep 1  # avoid reusing the timestamped audit branch name in this fixture
if bash "$STATE_DIR/rollback.sh" > "$TMP/rollback-reboot-failed.log" 2>&1; then
  echo 'rollback reboot denial unexpectedly passed' >&2
  exit 1
fi
grep -Fq 'REBOOT_REQUEST_FAILED:' "$TMP/rollback-reboot-failed.log"
grep -Fxq 'rollback_result=reboot_request_failed' "$STATE_DIR/rollback-result.env"
[[ $(wc -l < "$FAKE_REBOOT_LOG") == 2 ]]

echo 'fake-device tag, recovery preflight, exact path and rollback fixtures PASS'
