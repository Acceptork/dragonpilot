import json
from cereal import car, log
from openpilot.selfdrive.ui.departure_runtime import DepartureRuntime, current_cue, CUE_KEY


class Params:
  def __init__(self):
    self.values={'dp_departure_lead_alert': True, 'dp_departure_signal_alert': True}
    self.writes=[]
  def get_bool(self,key):
    return bool(self.values.get(key,False))
  def get(self,key):
    return self.values.get(key)
  def put_nonblocking(self,key,value):
    self.values[key]=value
    self.writes.append((key,value))


class NativeSM(dict):
  def __init__(self,t):
    super().__init__(carState=car.CarState.new_message(vEgo=0.,canValid=True,gearShifter='drive'),
      modelV2=log.ModelDataV2.new_message(),radarState=log.RadarState.new_message(),
      deviceState=log.DeviceState.new_message(started=True),
      selfdriveState=log.SelfdriveState.new_message(enabled=False,active=False),
      carControl=car.CarControl.new_message(longActive=False,latActive=False))
    self.valid={key:True for key in self}
    self.recv_time={key:t for key in self}
    self.updated={key:True for key in self}
    self['modelV2'].velocity.x=[0.]*33


def test_actual_native_messages_acc_off_and_no_mutation():
  params=Params()
  runtime=DepartureRuntime(params)
  events=[]
  for i in range(120):
    t=i*.05
    sm=NativeSM(t)
    lead=sm['radarState'].leadOne
    lead.status=True
    lead.dRel=10.+max(0.,t-2)
    lead.vRel=1. if t>2 else 0.
    lead.modelProb=.95
    # SubMaster supplies readers. Reading absent pointers on a builder initializes them.
    for key in list(sm):
      sm[key]=sm[key].as_reader()
    before={key:value.to_dict() for key,value in sm.items()}
    event=runtime.update(sm,t)
    assert before=={key:value.to_dict() for key,value in sm.items()}
    if event:
      events.append(event)
      assert current_cue(params,t,True)=='前車已起步'
  assert len(events)==1
  assert all(key==CUE_KEY for key,_ in params.writes)
  assert current_cue(params,events[0]['expires_at'],True) is None


def test_old_future_invalid_disabled_and_offroad_cues_hidden():
  params=Params()
  params.values[CUE_KEY]=json.dumps(dict(kind='possible_proceed',issued_at=10.,expires_at=13.,text='綠燈'))
  assert current_cue(params,11.,True)=='前方可能已可通行'
  assert current_cue(params,9.,True) is None
  assert current_cue(params,11.,False) is None
  params.values['dp_departure_signal_alert']=False
  assert current_cue(params,11.,True) is None
  params.values[CUE_KEY]='not json'
  assert current_cue(params,11.,True) is None


def test_stale_inputs_prevent_arm_and_offroad_clears_cue():
  params=Params()
  runtime=DepartureRuntime(params)
  for i in range(120):
    t=i*.05
    sm=NativeSM(t)
    sm.recv_time['radarState']=t-1
    assert runtime.update(sm,t) is None
  sm=NativeSM(7.)
  sm['deviceState'].started=False
  assert runtime.update(sm,7.) is None
  assert params.writes[-1]==(CUE_KEY,'')
