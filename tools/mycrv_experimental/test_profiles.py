import pytest
from profiles import apply_profile, values, PROFILES


class FakeParams:
  def __init__(self):
    self.data={key:True for key in values('ALL_OFF')}
    self.data['IsOffroad']=True
    self.writes=[]
    self.fail_at=None
    self.drive_at=None
  def get_bool(self,key):
    return self.data[key]
  def put_bool(self,key,value):
    self.writes.append((key,value))
    if len(self.writes)==self.fail_at:
      raise OSError('injected storage failure')
    if len(self.writes)==self.drive_at:
      self.data['IsOffroad']=False
    self.data[key]=value


@pytest.mark.parametrize('profile',PROFILES)
def test_old_profile_cleared_and_no_other_feature_enabled(profile):
  params=FakeParams()
  desired=apply_profile(params,profile)
  assert {k:v for k,v in params.data.items() if k!='IsOffroad'}==desired
  assert all(not value for _,value in params.writes[:8])
  assert all(key.startswith('dp_exp_') for key,_ in params.writes)


def test_onroad_rejected_without_any_write():
  params=FakeParams()
  params.data['IsOffroad']=False
  with pytest.raises(RuntimeError):
    apply_profile(params,'PROFILE_A_STOP')
  assert not params.writes


@pytest.mark.parametrize('fault',['fail_at','drive_at'])
def test_mid_apply_failure_restores_all_off(fault):
  params=FakeParams()
  setattr(params,fault,10)
  with pytest.raises((RuntimeError,OSError)):
    apply_profile(params,'PROFILE_A_STOP')
  assert not any(params.data[key] for key in values('ALL_OFF'))
