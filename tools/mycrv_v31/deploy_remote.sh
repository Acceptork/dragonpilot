#!/usr/bin/env bash
# Optional host-side single command: deploy, wait for SSH after reboot, verify.
set -Eeuo pipefail

[[ $# -eq 2 && $2 =~ ^[0-9a-f]{40}$ ]] || { echo 'Usage: deploy_remote.sh <comma IP> <exact RC SHA>' >&2; exit 2; }
DEVICE_IP=$1
TARGET_SHA=$2
case "$DEVICE_IP" in *[!0-9A-Za-z.:_-]*|'') echo 'invalid device address' >&2; exit 2 ;; esac
SSH_TARGET=comma@$DEVICE_IP
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
umask 077
LOG_DIR=${MYCRV_DEPLOY_LOG_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/mycrv_v31}
mkdir -p "$LOG_DIR"
LOG=$LOG_DIR/deploy-$(date -u +%Y%m%dT%H%M%SZ)-${TARGET_SHA:0:12}-$$.log
printf 'Deployment transcript: %s\n' "$LOG"

echo "Deploying $TARGET_SHA to $SSH_TARGET. The device must be parked and offroad."
PRE_BOOT_ID=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_TARGET" 'cat /proc/sys/kernel/random/boot_id')
[[ $PRE_BOOT_ID =~ ^[0-9a-f-]{36}$ ]] || { echo 'could not read a valid pre-deploy boot ID' >&2; exit 1; }
printf 'pre_boot_id=%s\n' "$PRE_BOOT_ID" >> "$LOG"
set +e
ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_TARGET" "bash -s -- $TARGET_SHA" < "$SCRIPT_DIR/deploy.sh" 2>&1 | tee -a "$LOG"
DEPLOY_STATUS=${PIPESTATUS[0]}
set -e
if ! grep -Fq "DEPLOY_READY $TARGET_SHA" "$LOG"; then
  echo "deploy did not reach its reboot point (SSH status $DEPLOY_STATUS)" >&2
  exit 1
fi

# A reboot may close SSH with 255. The marker is printed before sudo reboot,
# so only a changed kernel boot ID proves that a new boot occurred.
for attempt in $(seq 1 90); do
  sleep 5
  POST_BOOT_ID=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$SSH_TARGET" 'cat /proc/sys/kernel/random/boot_id' 2>/dev/null) || continue
  if [[ $POST_BOOT_ID =~ ^[0-9a-f-]{36}$ && $POST_BOOT_ID != "$PRE_BOOT_ID" ]]; then
    echo "SSH returned after a verified new boot (attempt $attempt)."
    printf 'post_boot_id=%s\n' "$POST_BOOT_ID" >> "$LOG"
    ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_TARGET" "bash /data/mycrv_v31_backup/verify.sh $TARGET_SHA" 2>&1 | tee -a "$LOG"
    exit $?
  fi
done
echo 'No changed boot ID was observed within 7.5 minutes; deployment is unverified' >&2
exit 1
