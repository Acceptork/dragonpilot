#!/usr/bin/env bash
set -Eeuo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BASE_SHA=a1e028371cdfe87471f694c87fc3d17060f969c4

bash "$DIR/deploy.sh" --help >/dev/null
if bash "$DIR/deploy.sh" not-a-sha >/tmp/mycrv-deploy-invalid.out 2>&1; then
  echo 'invalid SHA was accepted' >&2
  exit 1
fi
grep -Fq 'exact lowercase 40-character commit SHA' /tmp/mycrv-deploy-invalid.out
if bash "$DIR/deploy.sh" "$BASE_SHA" >/tmp/mycrv-deploy-platform.out 2>&1; then
  echo 'non-device platform was accepted' >&2
  exit 1
fi
grep -Fq 'expected an aarch64 comma device' /tmp/mycrv-deploy-platform.out
if bash "$DIR/rollback.sh" >/tmp/mycrv-rollback-platform.out 2>&1; then
  echo 'rollback accepted non-device platform' >&2
  exit 1
fi
grep -Fq 'expected an aarch64 comma device' /tmp/mycrv-rollback-platform.out
if bash "$DIR/verify.sh" bad >/tmp/mycrv-verify-invalid.out 2>&1; then
  echo 'verify accepted invalid SHA' >&2
  exit 1
fi
grep -Fq 'exact expected commit SHA' /tmp/mycrv-verify-invalid.out
if bash "$DIR/deploy_remote.sh" bad-name! "$BASE_SHA" >/tmp/mycrv-host-invalid.out 2>&1; then
  echo 'remote wrapper accepted invalid address' >&2
  exit 1
fi
grep -Fq 'invalid device address' /tmp/mycrv-host-invalid.out
echo 'deploy/rollback/verify non-device guard tests PASS'
