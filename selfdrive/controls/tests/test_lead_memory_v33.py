import pytest
from openpilot.selfdrive.controls.lib.lead_memory_v33 import LeadMemory

def lead(d=15., index=0):
  return dict(d=d, vr=-1., y=0., std=.1, prob=.99, measured=True, path_ok=True, index=index)

def seed(s):
  s.update(0., [lead()], 10., True)
  s.update(.05, [lead(14.95)], 10., True)

@pytest.mark.parametrize('horizon', [.2, .3, .5])
def test_predict_and_expire_unknown(horizon):
  s = LeadMemory(horizon)
  seed(s)
  a = s.update(.1, [], 10., True)
  b = s.update(.15, [], 10., True)
  assert a['active'] and b['active']
  assert b['memory']['d'] < a['memory']['d']
  assert s.update(.05 + horizon + .01, [], 10., True)['unknown']

def test_new_closer_immediate():
  s = LeadMemory()
  seed(s)
  r = s.update(.1, [lead(5., 1)], 10., True)
  assert not r['active'] and r['reason'] == 'new_closer_lead_immediate_priority'

def test_index_reassociation():
  s = LeadMemory()
  seed(s)
  r = s.update(.1, [lead(14.9, 1)], 10., True)
  assert r['reason'] == 'index_reassociation'
  assert s.update(.15, [], 10., True)['active']

def test_geometry_releases_memory_not_clear():
  s = LeadMemory()
  seed(s)
  r = s.update(.1, [], 10., False)
  assert not r['active'] and r['unknown']

def test_never_seen_is_perception_limitation():
  s = LeadMemory()
  assert s.update(0., [], 10., True)['reason'].startswith('PERCEPTION_LIMITATION')

def test_farther_lead_does_not_replace_unknown_closer():
  s = LeadMemory()
  seed(s)
  r = s.update(.1, [lead(25., 1)], 10., True)
  assert r['active'] and r['memory']['d'] < 15.
