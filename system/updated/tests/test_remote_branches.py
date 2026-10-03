import subprocess
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openpilot.system.updated.remote_branches import RemoteBranches, parse_remote_heads, selection_labels

NAMES = ['my-crv-experimental', 'my-crv-latest', 'my-crv-v3.2-rc-candidate', 'my-crv-v2-baseline', 'pre-build', 'future-branch']


def test_dynamic_heads_and_current_label():
  output = ''.join(f'{i+1:040x}\trefs/heads/{b}\n' for i, b in enumerate(NAMES))
  output += 'a'*40+'\trefs/tags/archive/pre-build\n'+'b'*40+'\tHEAD\n'
  branches = parse_remote_heads(output)
  assert list(branches) == NAMES
  labels = selection_labels(branches, NAMES[0], lambda b: b+' (current)')
  assert next(iter(labels)) == NAMES[0]+' (current)'
  assert labels[NAMES[0]+' (current)'] == NAMES[0]


@pytest.fixture
def git_repo(tmp_path):
  source = tmp_path/'source'
  source.mkdir()
  def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()
  git(source, 'init', '-q')
  git(source, '-c', 'user.name=Test', '-c', 'user.email=test@example.test', 'commit', '--allow-empty', '-qm', 'base')
  sha = git(source, 'rev-parse', 'HEAD')
  for name in NAMES:
    git(source, 'branch', name, sha)
  git(source, 'tag', 'archive/example', sha)
  clone = tmp_path/'clone'
  subprocess.check_call(['git', 'clone', '-q', str(source), str(clone)])
  return RemoteBranches(clone), sha, git


@pytest.mark.parametrize('branch', NAMES)
def test_fetch_verified_never_changes_checkout(git_repo, branch):
  remote, sha, git = git_repo
  before = git(remote.repo, 'symbolic-ref', 'HEAD'), git(remote.repo, 'rev-parse', 'HEAD'), git(remote.repo, 'status', '--porcelain')
  assert remote.verify_fetch(branch) == (branch, sha)
  after = git(remote.repo, 'symbolic-ref', 'HEAD'), git(remote.repo, 'rev-parse', 'HEAD'), git(remote.repo, 'status', '--porcelain')
  assert before == after


@pytest.mark.parametrize('branch', ['', '--upload-pack=bad', 'bad name', '../bad', 'refs/tags/archive/example', 'archive/example', 'missing'])
def test_reject_invalid_or_tag(git_repo, branch):
  remote, _, git = git_repo
  before = git(remote.repo, 'rev-parse', 'HEAD')
  with pytest.raises((ValueError, subprocess.CalledProcessError)):
    remote.verify_fetch(branch)
  assert git(remote.repo, 'rev-parse', 'HEAD') == before


def test_remote_changes_mid_fetch(mocker):
  remote = RemoteBranches('/unused')
  mocker.patch.object(remote, 'list', side_effect=[{'x': 'a'*40}, {'x': 'b'*40}])
  mocker.patch.object(remote, 'git', side_effect=['', '', 'a'*40])
  with pytest.raises(ValueError, match='changed'):
    remote.verify_fetch('x')


def test_network_failure_preserves_checkout(git_repo):
  remote, _, git = git_repo
  before = git(remote.repo, 'rev-parse', 'HEAD')
  git(remote.repo, 'remote', 'set-url', 'origin', '/nonexistent-mycrv-origin')
  with pytest.raises(subprocess.CalledProcessError):
    remote.verify_fetch('my-crv-latest')
  assert git(remote.repo, 'rev-parse', 'HEAD') == before


@pytest.mark.parametrize('outcome', ['offline', 'onroad', 'busy', 'success'])
def test_ui_commits_target_only_after_verified_result(mocker, outcome):
  from openpilot.selfdrive.ui.layouts.settings import software
  params = Mock()
  params.get.side_effect = lambda key: 'downloading...' if key == 'UpdaterState' and outcome == 'busy' else 'idle'
  mocker.patch.object(software, 'ui_state', SimpleNamespace(params=params, is_offroad=lambda: outcome != 'onroad'))
  signal = mocker.patch.object(software.os, 'system')
  future = Future()
  if outcome == 'offline':
    future.set_exception(subprocess.TimeoutExpired('git', 45))
  else:
    future.set_result(('my-crv-latest', 'a'*40))
  obj = SimpleNamespace(_branch_future=future, _branch_operation='select', _branch_btn=Mock(), _branch_error=Mock())
  software.SoftwareLayout._finish_branch_job(obj)
  if outcome == 'success':
    params.put.assert_called_once_with('UpdaterTargetBranch', 'my-crv-latest', block=True)
    signal.assert_called_once()
  else:
    params.put.assert_not_called()
    signal.assert_not_called()
    obj._branch_error.assert_called_once()
