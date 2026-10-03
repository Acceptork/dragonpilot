import pytest
from openpilot.selfdrive.controls.lib.free_cruise_v32 import FreeCruiseRecovery

def run(name,base=0.2):
  g=FreeCruiseRecovery(); out=[]
  for i in range(100):out.append(g.update(base+i*0.01,1.2,20/3.6,name,True))
  return out

def test_order():
  r,s,a=(run(n) for n in ['relaxed','standard','aggressive'])
  assert sum(r)<sum(s)<sum(a)

@pytest.mark.parametrize('name',['relaxed','standard','aggressive'])
@pytest.mark.parametrize('base',[-3.,-0.2,0.,0.3])
def test_veto_identity(name,base):
  g=FreeCruiseRecovery()
  for _ in range(100):g.update(.3,1.,5.,name,True)
  assert g.update(base,1.,5.,name,False)==base
  assert not g.active

@pytest.mark.parametrize('gap',[0.,0.2,-1.])
def test_approach_identity(gap):
  assert FreeCruiseRecovery().update(.2,1.,gap,'aggressive',True)==.2

def test_no_negative_weakening_and_bounded():
  g=FreeCruiseRecovery()
  for _ in range(100):
    value=g.update(.2,.25,5.,'aggressive',True)
    assert .2<=value<=.25
  assert g.update(-2.,1.,5.,'aggressive',True)==-2.
