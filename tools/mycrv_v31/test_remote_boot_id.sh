#!/usr/bin/env bash
# Verify that a DEPLOY_READY marker alone cannot pass the host wrapper.
set -Eeuo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
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
    echo "DEPLOY_READY ${command_text##* }; backup /data/mycrv_v31_backup/test; rebooting"
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
export MYCRV_DEPLOY_LOG_DIR="$TMP/logs"
SHA=a1e028371cdfe87471f694c87fc3d17060f969c4

export FAKE_BOOT_CASE=unchanged
if bash "$DIR/deploy_remote.sh" 192.0.2.4 "$SHA" > "$TMP/unchanged.log" 2>&1; then
  echo 'same boot ID falsely passed deployment verification' >&2
  exit 1
fi
[[ ! -e $FAKE_VERIFY_FILE ]] || { echo 'verify ran before a new boot' >&2; exit 1; }
grep -Fq 'No changed boot ID was observed' "$TMP/unchanged.log"

rm -f "$FAKE_COUNT_FILE"
export FAKE_BOOT_CASE=changed
bash "$DIR/deploy_remote.sh" 192.0.2.4 "$SHA" > "$TMP/changed.log" 2>&1
[[ -e $FAKE_VERIFY_FILE ]] || { echo 'verify did not run after new boot' >&2; exit 1; }
grep -Fq 'SSH returned after a verified new boot' "$TMP/changed.log"
echo 'host wrapper boot-ID tests PASS'
