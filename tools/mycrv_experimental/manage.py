#!/usr/bin/env python3
"""Pinned local-device deployment and rollback. Preview unless explicitly --apply.

No SSH, automatic reboot, safety changes, or automatic experiment activation.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

BASELINE = 'a1e028371cdfe87471f694c87fc3d17060f969c4'
RC = '80e190108b86ed3d2fa7634546dc2b1fa88ae69c'
BRANCHES = ('my-crv-v2-baseline', 'my-crv-latest', 'my-crv-experimental')
FLAGS = ('early_stop', 'taper', 'restart', 'lca', 'overtake', 'ramp', 'lead_memory', 'personality')
PROTECTED = ('launch_env.sh', 'launch_chffrplus.sh', 'system/hardware', 'panda', 'opendbc_repo/opendbc/safety')


def exact_sha(value):
  if not re.fullmatch('[0-9a-f]{40}', value):
    raise ValueError('必須指定完整 40 字元 commit SHA')
  return value


class Device:
  def __init__(self):
    self.repo = Path('/data/openpilot')
    self.params = Path('/data/params/d')
    self.backups = Path('/data/mycrv_branch_backups')

  def git(self, *args):
    return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

  def parked(self):
    if (self.params / 'IsOffroad').read_text().strip() != '1':
      raise RuntimeError('必須停車且 IsOffroad=1；保持停車，勿使用控制功能')
    if (self.params / 'IsOnroad').exists() and (self.params / 'IsOnroad').read_text().strip() == '1':
      raise RuntimeError('IsOnroad=1，禁止切換版本')

  def preflight(self):
    if platform.machine() != 'aarch64' or not Path('/VERSION').is_file():
      raise RuntimeError('僅可在實際 comma 裝置上套用；本機僅能預覽')
    self.parked()
    if self.git('rev-parse', '--show-toplevel') != str(self.repo):
      raise RuntimeError('非預期的 Git root')
    if self.git('status', '--porcelain', '--untracked-files=normal'):
      raise RuntimeError('working tree 非乾淨；不覆寫任何檔案')
    if self.git('remote', 'get-url', 'origin') not in (
      'https://github.com/Acceptork/dragonpilot.git', 'git@github.com:Acceptork/dragonpilot.git'):
      raise RuntimeError('origin 不符')
    if not shutil.which('scons'):
      raise RuntimeError('找不到 scons')

  def flags_off(self):
    # Literal known keys; atomic replacement, even when the old version does not register these keys.
    self.parked()
    directory = self.params.resolve(strict=True)
    for name in FLAGS:
      fd, temporary = tempfile.mkstemp(prefix='.mycrv-', dir=directory)
      try:
        with os.fdopen(fd, 'wb') as stream:
          stream.write(b'0')
          stream.flush()
          os.fsync(stream.fileno())
        os.replace(temporary, directory / ('dp_exp_' + name))
      finally:
        if os.path.exists(temporary):
          os.unlink(temporary)
    for name in FLAGS:
      if (directory / ('dp_exp_' + name)).read_bytes() != b'0':
        raise RuntimeError('實驗開關 OFF 驗證失敗')

  def build(self, destination):
    with destination.open('wb') as log:
      subprocess.run(['scons', '-j2'], cwd=self.repo, stdout=log, stderr=subprocess.STDOUT, check=True)

  def check_target(self, target):
    if self.git('cat-file', '-t', target) != 'commit':
      raise RuntimeError('目標非 commit')
    if target != BASELINE:
      self.git('merge-base', '--is-ancestor', RC, target)
    if self.git('diff', '--name-only', BASELINE, target, '--', *PROTECTED):
      raise RuntimeError('目標更改受保護 OS／boot／safety 檔案')
    version = self.git('show', target + ':launch_env.sh')
    match = re.search(r'^\s*export AGNOS_VERSION="([^"]+)"', version, re.MULTILINE)
    if not match or Path('/VERSION').read_text().strip() != match[1]:
      raise RuntimeError('AGNOS 不符；本工具不更新 OS')

  def switch_build(self, target, backup, label):
    self.parked()
    self.git('switch', '--detach', target)
    self.flags_off()
    self.build(backup / (label + '-build.log'))
    self.parked()
    if self.git('rev-parse', 'HEAD') != target or self.git('status', '--porcelain', '--untracked-files=normal'):
      raise RuntimeError('建置後 SHA 或 source tree 不符')

  def deploy(self, branch, target):
    exact_sha(target)
    if branch not in BRANCHES or (branch == 'my-crv-v2-baseline' and target != BASELINE):
      raise ValueError('分支／baseline SHA 不符')
    self.preflight()
    self.git('fetch', '--no-tags', 'origin', 'refs/heads/' + branch)
    if self.git('rev-parse', 'FETCH_HEAD^{commit}') != target:
      raise RuntimeError('遠端 HEAD 不等於指定 SHA，停止，不跟隨新版本')
    self.check_target(target)
    previous = self.git('rev-parse', 'HEAD')
    self.backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup = self.backups / stamp
    backup.mkdir(mode=0o700)
    self.git('branch', 'mycrv-local-backup-' + stamp, previous)
    manifest = dict(previous=previous, target=target, requested_branch=branch,
                    flags='ALL_OFF', state='PREPARED', reboot='NOT_RUN')
    (backup / 'state.json').write_text(json.dumps(manifest, indent=2))
    shutil.copy2(Path(__file__), backup / 'manage.py')
    self.flags_off()
    try:
      self.switch_build(target, backup, 'target')
    except Exception:
      manifest['state'] = 'TARGET_FAILED_RECOVERY_STARTED'
      (backup / 'state.json').write_text(json.dumps(manifest, indent=2))
      try:
        self.switch_build(previous, backup, 'recovery')
        manifest['state'] = 'PREVIOUS_RESTORED_KEEP_PARKED'
      except Exception:
        manifest['state'] = 'RECOVERY_FAILED_KEEP_PARKED'
        raise
      finally:
        (backup / 'state.json').write_text(json.dumps(manifest, indent=2))
      raise
    manifest['state'] = 'BUILT_ALL_OFF_REBOOT_AND_RUNTIME_VERIFICATION_REQUIRED'
    (backup / 'state.json').write_text(json.dumps(manifest, indent=2))
    return backup

  def rollback(self, backup):
    backup = Path(backup).resolve(strict=True)
    if backup.parent != self.backups.resolve(strict=True):
      raise ValueError('backup 必須位於固定備份目錄的直接子目錄')
    manifest = json.loads((backup / 'state.json').read_text())
    previous = exact_sha(manifest['previous'])
    self.preflight()
    self.check_target(previous)
    # Preserve the currently installed SHA too; never destroy an untagged checkout.
    current = self.git('rev-parse', 'HEAD')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    self.git('branch', 'mycrv-before-rollback-' + stamp, current)
    self.flags_off()
    try:
      self.switch_build(previous, backup, 'rollback-' + stamp)
    except Exception:
      (backup / 'rollback-failure.txt').write_text('KEEP_PARKED: rollback build/source verification failed; no reboot requested.\n')
      raise
    return previous


def main():
  p = argparse.ArgumentParser(description=__doc__)
  sub = p.add_subparsers(dest='action', required=True)
  deploy = sub.add_parser('deploy')
  deploy.add_argument('branch', choices=BRANCHES)
  deploy.add_argument('sha', type=exact_sha)
  rollback = sub.add_parser('rollback')
  rollback.add_argument('backup')
  for parser in [deploy, rollback]:
    parser.add_argument('--apply', action='store_true')
  args = p.parse_args()
  if not args.apply:
    print(json.dumps(dict(plan=vars(args), execution='NOT_RUN', flags='ALL_OFF', automatic_reboot=False), ensure_ascii=False))
    return
  device = Device()
  result = device.deploy(args.branch, args.sha) if args.action == 'deploy' else device.rollback(args.backup)
  print('完成本機建置，所有實驗 OFF。尚未重新啟動／驗證執行中版本；保持停車。', result)


if __name__ == '__main__':
  main()
