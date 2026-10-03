#!/usr/bin/env bash
# Host-only fixture: no real SSH target or reboot is used.
set -Eeuo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/repo/tools/mycrv_v31" "$TMP/bin"
cp "$DIR/deploy_remote.sh" "$DIR/deploy.sh" "$TMP/repo/tools/mycrv_v31/"
git -C "$TMP/repo" init -q
git -C "$TMP/repo" config user.name 'Offline Fixture'
git -C "$TMP/repo" config user.email 'offline@example.invalid'
git -C "$TMP/repo" add tools/mycrv_v31
git -C "$TMP/repo" commit -qm 'Pinned fixture scripts'
SHA=$(git -C "$TMP/repo" rev-parse HEAD)
WRAPPER="$TMP/repo/tools/mycrv_v31/deploy_remote.sh"

cat > "$TMP/bin/ssh" <<'FAKE_SSH'
#!/usr/bin/env bash
set -Eeuo pipefail
command_text=
for arg in "$@"; do command_text=$arg; done
case "$command_text" in
  'cat /proc/sys/kernel/random/boot_id')
    count=0
    [[ -f $FAKE_COUNT_FILE ]] && count=$(cat "$FAKE_COUNT_FILE")
    count=$((count + 1))
    printf '%s\n' "$count" > "$FAKE_COUNT_FILE"
    if [[ $count -gt 1 && $FAKE_BOOT_CASE == changed ]]; then
      echo '00000000-0000-0000-0000-000000000002'
    else
      echo '00000000-0000-0000-0000-000000000001'
    fi
    ;;
  'bash -s -- '*)
    cat > "$FAKE_STREAM_FILE"
    echo "DEPLOY_READY ${command_text##* }; backup /data/mycrv_v31_backup/test; rebooting"
    if [[ $FAKE_BOOT_CASE == reboot_failed ]]; then
      echo 'mycrv deploy: REBOOT_REQUEST_FAILED: fixture reboot denied' >&2
      exit 1
    fi
    exit 255
    ;;
  'bash /data/mycrv_v31_backup/verify.sh '*)
    printf '%s\n' verified > "$FAKE_VERIFY_FILE"
    echo 'POST_REBOOT_OFFROAD_VERIFIED'
    ;;
  *) echo "unexpected mock SSH command: $command_text" >&2; exit 2 ;;
esac
FAKE_SSH
cat > "$TMP/bin/sleep" <<'FAKE_SLEEP'
#!/usr/bin/env bash
exit 0
FAKE_SLEEP
chmod +x "$TMP/bin/ssh" "$TMP/bin/sleep"

export PATH="$TMP/bin:$PATH"
export FAKE_COUNT_FILE="$TMP/count"
export FAKE_VERIFY_FILE="$TMP/verified"
export FAKE_STREAM_FILE="$TMP/streamed.sh"
export MYCRV_DEPLOY_LOG_DIR="$TMP/logs"

export FAKE_BOOT_CASE=unchanged
if bash "$WRAPPER" 192.0.2.4 "$SHA" > "$TMP/unchanged.log" 2>&1; then
  echo 'same boot ID falsely passed deployment verification' >&2
  exit 1
fi
[[ ! -e $FAKE_VERIFY_FILE ]] || { echo 'verify ran before a new boot' >&2; exit 1; }
cmp "$TMP/repo/tools/mycrv_v31/deploy.sh" "$FAKE_STREAM_FILE"
grep -Fq 'No changed boot ID was observed' "$TMP/unchanged.log"

rm -f "$FAKE_COUNT_FILE" "$FAKE_VERIFY_FILE"
export FAKE_BOOT_CASE=changed
bash "$WRAPPER" 192.0.2.4 "$SHA" > "$TMP/changed.log" 2>&1
[[ -e $FAKE_VERIFY_FILE ]] || { echo 'verify did not run after new boot' >&2; exit 1; }
grep -Fq 'SSH returned after a verified new boot' "$TMP/changed.log"

rm -f "$FAKE_COUNT_FILE" "$FAKE_VERIFY_FILE"
export FAKE_BOOT_CASE=reboot_failed
if bash "$WRAPPER" 192.0.2.4 "$SHA" > "$TMP/reboot_failed.log" 2>&1; then
  echo 'explicit reboot failure was accepted' >&2
  exit 1
fi
[[ $(cat "$FAKE_COUNT_FILE") == 1 ]] || { echo 'polled after explicit reboot failure' >&2; exit 1; }
[[ ! -e $FAKE_VERIFY_FILE ]] || { echo 'verified after explicit reboot failure' >&2; exit 1; }
grep -Fq 'device rejected reboot request' "$TMP/reboot_failed.log"

rm -f "$FAKE_COUNT_FILE"
printf '\n# unreviewed local edit\n' >> "$TMP/repo/tools/mycrv_v31/deploy.sh"
if bash "$WRAPPER" 192.0.2.4 "$SHA" > "$TMP/tampered.log" 2>&1; then
  echo 'tampered local deploy script was accepted' >&2
  exit 1
fi
[[ ! -e $FAKE_COUNT_FILE ]] || { echo 'SSH was contacted before local source check' >&2; exit 1; }
grep -Fq 'differs from pinned RC commit' "$TMP/tampered.log"

echo 'host wrapper provenance, boot-ID and reboot-failure fixture tests PASS'
