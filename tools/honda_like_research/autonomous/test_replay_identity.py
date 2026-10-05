import copy
import unittest
from replay_identity import compare

class IdentityTests(unittest.TestCase):
  def setUp(self):
    self.rows=[{'type':'longitudinalPlan','t':1.,'payload':{'aTarget':.1,'shouldStop':False,'solverExecutionTime':.001}},
               {'type':'carState','t':1.,'payload':{'vEgo':10.,'cumLagMs':-.01}},
               {'type':'sendcan','t':1.,'payload':[{'address':1,'bus':1,'hex':'0011'},{'address':2,'bus':1,'hex':'2233'}]}]
  def test_equal(self):
    self.assertTrue(compare(self.rows,copy.deepcopy(self.rows))['identity'])
  def test_only_wall_measurements(self):
    rows=copy.deepcopy(self.rows)
    rows[0]['payload']['solverExecutionTime']=123.
    rows[1]['payload']['cumLagMs']=123.
    self.assertTrue(compare(self.rows,rows)['identity'])
  def test_no_numeric_tolerance(self):
    rows=copy.deepcopy(self.rows);rows[0]['payload']['aTarget']+=1e-12
    self.assertFalse(compare(self.rows,rows)['identity'])
  def test_stop_change(self):
    rows=copy.deepcopy(self.rows);rows[0]['payload']['shouldStop']=True
    self.assertFalse(compare(self.rows,rows)['identity'])
  def test_timestamp(self):
    rows=copy.deepcopy(self.rows);rows[0]['t']+=.000001
    self.assertFalse(compare(self.rows,rows)['identity'])
  def test_can_byte(self):
    rows=copy.deepcopy(self.rows);rows[2]['payload'][0]['hex']='0010'
    self.assertFalse(compare(self.rows,rows)['identity'])
  def test_can_order(self):
    rows=copy.deepcopy(self.rows);rows[2]['payload'].reverse()
    self.assertFalse(compare(self.rows,rows)['identity'])
  def test_missing_message(self):
    self.assertFalse(compare(self.rows,self.rows[:-1])['identity'])

if __name__=='__main__':unittest.main()
