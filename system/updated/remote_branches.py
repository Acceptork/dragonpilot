"""Remote branch discovery/validation; never checks out or resets a tree."""
import os
import re
import subprocess
from pathlib import Path


def parse_remote_heads(output: str) -> dict[str, str]:
  heads = {}
  for line in output.splitlines():
    match = re.fullmatch(r'([0-9a-f]{40})\s+refs/heads/(\S+)', line)
    if match:
      heads[match[2]] = match[1]
  return heads


class RemoteBranches:
  def __init__(self, repo: str | Path):
    self.repo = str(repo)

  def git(self, *args: str) -> str:
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    return subprocess.check_output(['git', '-C', self.repo, *args], text=True, stderr=subprocess.PIPE,
                                   timeout=45, env=env).strip()

  def list(self) -> dict[str, str]:
    heads = parse_remote_heads(self.git('ls-remote', '--heads', 'origin'))
    if not heads:
      raise ValueError('No remote branches available')
    return heads

  def verify_fetch(self, branch: str) -> tuple[str, str]:
    if not branch or branch.startswith('-') or any(c.isspace() for c in branch) or branch.startswith('refs/'):
      raise ValueError('Invalid branch name')
    self.git('check-ref-format', 'refs/heads/' + branch)
    advertised = self.list().get(branch)
    if advertised is None:
      raise ValueError('Remote branch does not exist (tags are not branches)')
    # A private validation ref avoids FETCH_HEAD and remote-tracking ref races with updated.
    validation_ref = 'refs/mycrv/branch-selection'
    self.git('fetch', '--no-tags', '--no-recurse-submodules', '--no-write-fetch-head', 'origin',
             '+refs/heads/' + branch + ':' + validation_ref)
    fetched = self.git('rev-parse', validation_ref + '^{commit}')
    if fetched != advertised or self.list().get(branch) != fetched:
      raise ValueError('Remote branch changed during validation; retry')
    return branch, fetched


def selection_labels(branches: dict[str, str], current: str, current_label) -> dict[str, str]:
  return {current_label(b) if b == current else b: b for b in sorted(branches, key=lambda b: (b != current, b))}
