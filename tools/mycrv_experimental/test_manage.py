import json
from pathlib import Path
import subprocess
import sys
import pytest
from manage import Device, BASELINE, RC, exact_sha, FLAGS


class FakeDevice(Device):
  def __init__(self,tmp):
    self.backups=tmp/'backups'
    self.params=tmp/'params'
    self.params.mkdir()
    (self.params/'IsOffroad').write_text('1')
    self.head=BASELINE
    self.remote=RC
    self.calls=[]
    self.fail_build=set()
  def preflight(self): self.parked()
  def check_target(self,target): exact_sha(target)
  def git(self,*args):
    self.calls.append(args)
    if args==('rev-parse','HEAD'): return self.head
    if args==('rev-parse','FETCH_HEAD^{commit}'): return self.remote
    if args[:2]==('switch','--detach'): self.head=args[2]
    return ''
  def build(self,destination):
    destination.write_text('fake build '+self.head)
    if self.head in self.fail_build: raise RuntimeError('injected build failure')


def test_deploy_retains_backup_and_disables_every_experiment(tmp_path):
  d=FakeDevice(tmp_path)
  for name in FLAGS: (d.params/('dp_exp_'+name)).write_text('1')
  backup=d.deploy('my-crv-latest',RC)
  manifest=json.loads((backup/'state.json').read_text())
  assert manifest['previous']==BASELINE and manifest['target']==RC
  assert manifest['state']=='BUILT_ALL_OFF_REBOOT_AND_RUNTIME_VERIFICATION_REQUIRED'
  assert d.head==RC
  assert all((d.params/('dp_exp_'+name)).read_text()=='0' for name in FLAGS)
  assert any(cmd[0]=='branch' and cmd[-1]==BASELINE for cmd in d.calls)
  assert (backup/'manage.py').is_file()
  assert d.rollback(backup)==BASELINE and d.head==BASELINE


def test_failed_build_restores_original_commit_without_enabling_flags(tmp_path):
  d=FakeDevice(tmp_path); d.fail_build={RC}
  with pytest.raises(RuntimeError): d.deploy('my-crv-latest',RC)
  manifest=json.loads(next(d.backups.glob('*/state.json')).read_text())
  assert manifest['state']=='PREVIOUS_RESTORED_KEEP_PARKED'
  assert d.head==BASELINE
  assert all((d.params/('dp_exp_'+name)).read_text()=='0' for name in FLAGS)


def test_both_builds_fail_records_keep_parked(tmp_path):
  d=FakeDevice(tmp_path); d.fail_build={RC,BASELINE}
  with pytest.raises(RuntimeError): d.deploy('my-crv-latest',RC)
  assert json.loads(next(d.backups.glob('*/state.json')).read_text())['state']=='RECOVERY_FAILED_KEEP_PARKED'


@pytest.mark.parametrize('condition',['onroad','wrong_remote','wrong_baseline'])
def test_rejects_before_switch_or_flags(tmp_path,condition):
  d=FakeDevice(tmp_path)
  branch='my-crv-latest'
  if condition=='onroad': (d.params/'IsOffroad').write_text('0')
  if condition=='wrong_remote': d.remote=BASELINE
  if condition=='wrong_baseline': branch='my-crv-v2-baseline'
  with pytest.raises((RuntimeError,ValueError)): d.deploy(branch,RC)
  assert not any(cmd[0]=='switch' for cmd in d.calls)
  assert not list(d.params.glob('dp_exp_*'))


@pytest.mark.parametrize('sha',['HEAD',RC[:7],RC.upper(),'../bad'])
def test_requires_literal_full_sha(sha):
  with pytest.raises(ValueError): exact_sha(sha)


def test_preview_has_no_device_access():
  result=subprocess.run([sys.executable,str(Path(__file__).with_name('manage.py')),'deploy','my-crv-latest',RC],capture_output=True,text=True,check=True)
  assert json.loads(result.stdout)['execution']=='NOT_RUN'


def test_rollback_rejects_untrusted_backup_location(tmp_path):
  d=FakeDevice(tmp_path); d.backups.mkdir()
  other=tmp_path/'other'; other.mkdir()
  with pytest.raises(ValueError): d.rollback(other)
  assert not d.calls
