import pytest
from unittest.mock import PropertyMock

from openpilot.common.params import Params
from openpilot.system.updated.updated import Updater


@pytest.mark.parametrize(("device_type", "branch", "expected"), [
  ("tizi", "release3", "release-tizi"),
  ("tizi", "release3-staging", "release-tizi-staging"),
  ("mici", "release3", "release-mici"),
  ("mici", "release3-staging", "release-mici-staging"),
])
def test_target_branch_migration_from_current_branch(mocker, device_type, branch, expected):
  params = Params()
  params.remove("UpdaterTargetBranch")

  mocker.patch("openpilot.system.updated.updated.HARDWARE.get_device_type", return_value=device_type)
  mocker.patch.object(Updater, "get_branch", return_value=branch)

  assert Updater().target_branch == expected


@pytest.mark.parametrize(("device_type", "branch", "expected"), [
  ("tizi", "release3", "release-tizi"),
  ("tizi", "release3-staging", "release-tizi-staging"),
  ("mici", "release3", "release-mici"),
  ("mici", "release3-staging", "release-mici-staging"),
])
def test_target_branch_migration_from_param(mocker, device_type, branch, expected):
  params = Params()
  params.put("UpdaterTargetBranch", branch, block=True)

  mocker.patch("openpilot.system.updated.updated.HARDWARE.get_device_type", return_value=device_type)

  try:
    assert Updater().target_branch == expected
  finally:
    params.remove("UpdaterTargetBranch")


@pytest.mark.parametrize("remote_has_target", [False, True])
def test_check_for_update_skips_non_branch_output_and_handles_local_branch(mocker, remote_has_target):
  target = "my-crv-long-tune-v1"
  target_sha = "a" * 40
  remote_output = "From https://example.test/repo.git\n" + f"{'b' * 40}\trefs/heads/my-crv\n"
  if remote_has_target:
    remote_output += f"{target_sha}\trefs/heads/{target}\n"

  def fake_run(cmd, cwd=None):
    if cmd == ["git", "ls-remote", "origin", "HEAD"]:
      return f"{'b' * 40}\tHEAD\n"
    assert cmd == ["git", "ls-remote", "--heads", "origin"]
    return remote_output

  mocker.patch("openpilot.system.updated.updated.run", side_effect=fake_run)
  mocker.patch("openpilot.system.updated.updated.setup_git_options")
  mocker.patch.object(Updater, "target_branch", new_callable=PropertyMock, return_value=target)
  mocker.patch.object(Updater, "get_branch", return_value=target)
  mocker.patch.object(Updater, "get_commit_hash", return_value="c" * 40)
  mocker.patch("openpilot.system.updated.updated.os.path.isdir", return_value=True)

  updater = Updater()
  updater.check_for_update()
  assert updater.branches["my-crv"] == "b" * 40
  assert (target in updater.branches) == remote_has_target
  assert updater.update_available == remote_has_target
