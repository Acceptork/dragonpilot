#!/bin/sh
set -eu

cd /data/openpilot
if [ -n "$(git status --porcelain)" ]; then
  echo 'Rollback stopped: /data/openpilot has uncommitted changes.' >&2
  exit 1
fi
if ! git rev-parse --verify 'refs/tags/my-crv-before-long-tune^{commit}' >/dev/null 2>&1; then
  echo 'Rollback stopped: my-crv-before-long-tune tag is missing locally.' >&2
  exit 1
fi

git switch -C my-crv my-crv-before-long-tune
sudo reboot
