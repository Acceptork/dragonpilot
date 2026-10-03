from shadows import StopIntentShadow,LeadMemoryShadow,RestartResearch,StopTaperResearch,OvertakeResearch,ramp_research

def test_stop_shadow_timing_and_no_fabricated_stop():
  s=StopIntentShadow()
  states=[s.update(i*.05,10.,2.,-.2,True,True) for i in range(20)]
  assert states[-1]=='SLOWING_SUSPECT' and 'STOP_CONFIRMED' not in states
  assert s.update(1.,0.,0.,-.2,True,True,True,True)=='HOLD'
  assert s.update(3.,10.,2.,-.2,True,True)=='NORMAL'

def test_memory_moves_and_closer_takeover():
  s=LeadMemoryShadow(.5)
  s.update(0,{'d':20.,'vr':-2.,'prob':.9,'std':.2},True,10)
  s.update(.05,{'d':19.9,'vr':-2.,'prob':.9,'std':.2},True,10)
  out=s.update(.2,None,True,10)
  assert out['active'] and out['predicted_dRel']<19.9
  out=s.update(.25,{'d':8.,'vr':-3.,'prob':.9,'std':.2},True,10)
  assert out['reason']=='new_closer_lead_takeover' and not out['active']
  assert not s.update(2,None,True,10)['clear_authorized']

def test_restart_micro_motion_and_stop_veto():
  s=RestartResearch()
  s.update(0,'a',0,.1,False,False,True,False,False)
  for i in range(20):assert s.update(i*.1,'a',.1,.1,False,False,True,False,False)=='HOLD'
  assert s.update(3,'a',1.,.1,True,False,True,False,False)=='HOLD'

def test_stop_taper_requires_geometry_and_holds():
  s=StopTaperResearch()
  assert s.update(1.,None,0.,True,False)['request'] is None
  assert s.update(0.,1.,0.,True,False)['state']=='HOLD'
  assert s.update(0.,1.,0.,False,False)['request']<0

def test_overtake_two_stages_and_veto():
  s=OvertakeResearch()
  kw=dict(starting=True,long_active=True,lat_active=True,gap=12.,lead_valid=True,margin=10.,clear_verified=None,cap=.3)
  assert s.update(0,'left',False,**kw)['preaccel_request']==0
  assert s.update(.05,'left',True,**kw)['state']=='STAGE1'
  assert s.update(.1,'left',True,**kw)['stage2']=='BLOCKED'
  assert s.update(.15,'left',True,**{**kw,'clear_verified':True})['state']=='STAGE2'
  assert s.update(.2,'left',True,fcw=True,**kw)['preaccel_request']==0

def test_ramp_negative_or_closing_never_overridden():
  assert ramp_research(-.2,1.,False,False,True,False,False,True)==-.2
  assert ramp_research(.1,1.,True,False,True,False,False,True)==.1
  assert ramp_research(.1,1.,False,False,True,False,False,True)==.2
