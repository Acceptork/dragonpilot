#!/usr/bin/env bash
# Read-only post-reboot check. Offroad control processes and live CarParams are
# deliberately reported as pending: manager starts them only when onroad.
set -Eeuo pipefail

[[ $# -eq 1 && $1 =~ ^[0-9a-f]{40}$ ]] || { echo 'Usage: verify.sh <exact expected commit SHA>' >&2; exit 2; }
EXPECTED_SHA=$1
cd /data/openpilot
ACTUAL_SHA=$(git rev-parse HEAD)
[[ $ACTUAL_SHA == "$EXPECTED_SHA" ]] || { echo "wrong commit: $ACTUAL_SHA" >&2; exit 1; }
[[ -z $(git status --porcelain --untracked-files=normal) ]] || { echo 'working tree dirty' >&2; exit 1; }
[[ -r /data/params/d/IsOffroad ]] || { echo 'IsOffroad param unavailable' >&2; exit 1; }
case $(cat /data/params/d/IsOffroad) in
  1) MODE=offroad ;;
  0) MODE=onroad ;;
  *) echo 'IsOffroad param has an invalid value' >&2; exit 1 ;;
esac

PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" python3 tools/mycrv_v31/verify_runtime.py "$MODE"
printf 'POST_REBOOT_%s_VERIFIED %s\n' "${MODE^^}" "$EXPECTED_SHA"
