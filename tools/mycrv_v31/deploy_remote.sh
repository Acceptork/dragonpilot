#!/usr/bin/env bash
# Optional host-side single command: deploy, wait for SSH after reboot, verify.
set -Eeuo pipefail

[[ $# -eq 2 && $2 =~ ^[0-9a-f]{40}$ ]] || { echo 'Usage: deploy_remote.sh <comma IP> <exact RC SHA>' >&2; exit 2; }
DEVICE_IP=$1
TARGET_SHA=$2
case "$DEVICE_IP" in *[!0-9A-Za-z.:_-]*|'') echo 'invalid device address' >&2; exit 2 ;; esac
SSH_TARGET=comma@$DEVICE_IP
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

echo "Deploying $TARGET_SHA to $SSH_TARGET. The device must be parked and offroad."
set +e
ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_TARGET" "bash -s -- $TARGET_SHA" < "$SCRIPT_DIR/deploy.sh" 2>&1 | tee "$LOG"
DEPLOY_STATUS=${PIPESTATUS[0]}
set -e
if ! grep -Fq "DEPLOY_READY $TARGET_SHA" "$LOG"; then
  echo "deploy did not reach its reboot point (SSH status $DEPLOY_STATUS)" >&2
  exit 1
fi

# A reboot may close SSH with 255. The marker above proves deployment reached
# the explicit reboot point; the second SSH call checks the booted result.
for attempt in $(seq 1 90); do
  sleep 5
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "$SSH_TARGET" true >/dev/null 2>&1; then
    echo "SSH returned after reboot (attempt $attempt)."
    ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_TARGET" "bash /data/mycrv_v31_backup/verify.sh $TARGET_SHA"
    exit $?
  fi
done
echo 'SSH did not return within 7.5 minutes; run verify.sh when device is reachable' >&2
exit 1
