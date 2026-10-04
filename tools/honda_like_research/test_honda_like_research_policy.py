import math, unittest
from honda_like_research_policy import RecoveryPolicy

class TestPolicy(unittest.TestCase):
  def setUp(self):
    self.model={'cells':[{'key':[4,2,'flat'],'supported':True,'train':{'p50':.8}}]}
    self.args=dict(v=22.,cluster=25.,cruise=100.,e2e=.02,mpc=1.,cap=.9,ay=0.,predicted_ay=0.,stop=False,fcw=False,hard_brake=False,lead=False,driver=False,active=True,allow=True,valid=True,pitch=0.,standstill=False,model_endpoint=23.)
  def run_policy(self, **changes):
    p=RecoveryPolicy(self.model);args=self.args|changes
    return [p.update(t=i*.05,**args) for i in range(60)]
  def test_supported_preselector_bounded(self):
    a=self.run_policy();self.assertGreater(a[-1][0],.02)
    self.assertLessEqual(a[-1][0],.17)
    self.assertTrue(all(y[0]-x[0]<=.007500001 for x,y in zip(a,a[1:])))
  def test_every_safety_veto_identity(self):
    for key,value in [('stop',True),('fcw',True),('hard_brake',True),('lead',True),('driver',True),('active',False),('allow',False),('valid',False),('standstill',True),('blinker',True),('ay',1.),('predicted_ay',1.),('e2e',-.01),('model_endpoint',10.),('pitch',.1),('cruise',92.)]:
      with self.subTest(key=key):
        args=self.args|{key:value};self.assertTrue(all(x[0]==args['e2e'] for x in self.run_policy(**{key:value})))
  def test_invalid_numeric_no_recovery(self):
    for key in ('v','cluster','cruise','mpc','cap','ay','predicted_ay','pitch','model_endpoint'):
      for value in (float('nan'),float('inf')):
        with self.subTest(key=key,value=value):self.assertTrue(all(x[0]==.02 and x[1]=='UNKNOWN' for x in self.run_policy(**{key:value})))
  def test_emergency_cancels_immediately(self):
    p=RecoveryPolicy(self.model)
    for i in range(60):p.update(t=i*.05,**self.args)
    self.assertEqual(p.update(t=3.,**(self.args|{'stop':True,'e2e':-2.}))[0],-2.)
  def test_missing_reference_identity(self):
    self.model={'cells':[]};self.assertTrue(all(x[0]==.02 for x in self.run_policy()))
  def test_lead_clear_and_curve_exit_state(self):
    for constraint,state in [('lead','LEAD_CLEAR_RECOVERY'),('ay','CURVE_EXIT_RECOVERY')]:
      p=RecoveryPolicy(self.model);p.update(t=0.,**self.args)
      p.update(t=.05,**(self.args|{constraint:True if constraint=='lead' else 1.}))
      self.assertEqual(p.update(t=.1,**self.args)[1],state)
  def test_no_green_light_release(self):
    self.assertTrue(all(x[0]==0 for x in self.run_policy(v=0.,cluster=0.,stop=True,standstill=True,e2e=0.)))
if __name__=='__main__':unittest.main()
