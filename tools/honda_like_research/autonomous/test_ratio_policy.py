import math
import pytest
from openpilot.selfdrive.controls.tests.test_recovery_v331 import sample
from self_train_ratio_policy import policy

@pytest.mark.parametrize('ratio',[.1,.15,.2])
def test_bounded_positive_authority_and_immediate_disagreement_exit(ratio):
  p=policy(ratio);previous=.05
  for i in range(100):
    row=p.update(sample(i*.05));p.observe_final(row['after'])
    assert .05<=row['after']<=.75
    assert row['after']-previous<=.0150001
    previous=row['after']
  assert row['active']
  row=p.update(sample(5.,e2e=ratio+.01,base=ratio+.01))
  assert not row['active'] and row['after']==ratio+.01

@pytest.mark.parametrize('ratio',[.1,.15,.2])
def test_configuration_survives_nonfinite_reset(ratio):
  p=policy(ratio)
  assert not p.update(sample(0.,e2e=math.nan))['active']
  for i in range(100):row=p.update(sample(.05*(i+1),e2e=ratio+.01,base=ratio+.01))
  assert p.ratio==ratio and not row['active']

@pytest.mark.parametrize('field,value',[('stop',True),('fcw',True),('hard_brake',True),('memory',True),('lead',True),('valid',False),('driver',True),('forecast_ay',1.)])
def test_original_veto_retains_authority(field,value):
  p=policy(.15)
  for i in range(100):
    row=p.update(sample(.05*i));p.observe_final(row['after'])
  assert row['active']
  row=p.update(sample(5.,**{field:value}))
  assert not row['active'] and row['after']==.05
