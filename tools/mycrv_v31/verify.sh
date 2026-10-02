#!/usr/bin/env bash
# Run via SSH after the device has returned from its reboot.
set -Eeuo pipefail

[[ $# -eq 1 && $1 =~ ^[0-9a-f]{40}$ ]] || { echo 'Usage: verify.sh <exact expected commit SHA>' >&2; exit 2; }
EXPECTED_SHA=$1
cd /data/openpilot
ACTUAL_SHA=$(git rev-parse HEAD)
[[ $ACTUAL_SHA == "$EXPECTED_SHA" ]] || { echo "wrong commit: $ACTUAL_SHA" >&2; exit 1; }
[[ -z $(git status --porcelain --untracked-files=normal) ]] || { echo 'working tree dirty' >&2; exit 1; }

python3 - <<'PY'
import os
import time

patterns = {
  'manager': ('system/manager/manager.py', 'system.manager.manager'),
  'controlsd': ('selfdrive/controls/controlsd.py', 'selfdrive.controls.controlsd'),
  'plannerd': ('selfdrive/controls/plannerd.py', 'selfdrive.controls.plannerd'),
  'pandad': ('selfdrive/boardd/pandad', 'pandad'),
  'ui': ('selfdrive.ui.ui', 'selfdrive/ui/ui', '/ui'),
}

def snapshot():
  found = {name: set() for name in patterns}
  for item in os.listdir('/proc'):
    if not item.isdigit() or int(item) == os.getpid():
      continue
    try:
      cmd = open(f'/proc/{item}/cmdline', 'rb').read().replace(b'\x00', b' ').decode(errors='replace')
    except (FileNotFoundError, PermissionError, ProcessLookupError):
      continue
    for name, needles in patterns.items():
      if any(needle in cmd for needle in needles):
        found[name].add(int(item))
  return found

first = snapshot()
time.sleep(10)
second = snapshot()
bad = []
for name in patterns:
  stable = first[name] & second[name]
  print(f'{name}: first={sorted(first[name])} second={sorted(second[name])} stable={sorted(stable)}')
  if not stable:
    bad.append(name)
if bad:
  raise SystemExit('missing or restarting: ' + ', '.join(bad))

from cereal import car, messaging
from openpilot.common.params import Params
raw = Params().get('CarParams')
if not raw:
  raise SystemExit('CarParams missing')
cp = messaging.log_from_bytes(raw, car.CarParams)
print('fingerprint:', cp.carFingerprint)
print('openpilotLongitudinalControl:', cp.openpilotLongitudinalControl)
if cp.carFingerprint != 'HONDA_CRV_5G':
  raise SystemExit('wrong car fingerprint')
PY

printf 'POST_REBOOT_VERIFIED %s\n' "$EXPECTED_SHA"
