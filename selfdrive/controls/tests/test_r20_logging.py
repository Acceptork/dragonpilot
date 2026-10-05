from types import SimpleNamespace as NS
import time
import pytest
from openpilot.selfdrive.controls.lib.r20_logging import RecoveryLogger

class SM(dict):pass
def sample():
  lead=NS(to_dict=lambda:dict(status=False,dRel=0.,vRel=0.))
  sm=SM(carState=NS(vEgo=20.,vEgoCluster=22.,vCruise=100.,aEgo=.1,gasPressed=False,brakePressed=False),
        carControl=NS(orientationNED=[0.,.01,0.],longActive=True),radarState=NS(leadOne=lead,leadTwo=lead),
        controlsState=NS(curvature=.0001),modelV2=NS(meta=NS(hardBrakePredicted=False)))
  sm.logMonoTime={'modelV2':1000000000}
  row=dict(active=True,state='FREE_CRUISE_RECOVERY',reason='bounded_selector_blend',before=.05,after=.3)
  return sm,row,dict(e2e=.05,mpc=1.,turn_max=2.)

def test_enter_sample_exit_markers_and_required_fields():
  logger=RecoveryLogger(enabled=False);logger.enabled=True
  sm,row,trace=sample()
  for active in (True,True,False):
    row['active']=active
    if not active:row['reason']='lead_or_collision_or_memory'
    logger.observe(sm,row,trace,.3,False,False)
  rows=[logger.queue.get_nowait() for _ in range(3)]
  assert [r['kind'] for r in rows]==['ENTER','SAMPLE','EXIT']
  assert len({r['event_id'] for r in rows})==1
  assert rows[-1]['safety_veto_reason']=='lead_or_collision_or_memory'
  assert rows[0]['baseline_selected_accel']==.05 and rows[0]['final_aTarget']==.3

def test_saturated_sink_is_bounded_and_does_not_raise():
  logger=RecoveryLogger(enabled=False);logger.enabled=True
  sm,row,trace=sample()
  for _ in range(1000):logger.observe(sm,row,trace,.3,False,False)
  assert logger.queue.qsize()==32 and logger.dropped==968
  assert row['after']==.3 and sm['carState'].vEgo==20.

def test_incomplete_diagnostic_never_breaks_control():
  logger=RecoveryLogger(enabled=False);logger.enabled=True
  sm,row,trace=sample();logger.observe(sm,row,{},.3,False,False)
  assert logger.dropped==1

def test_can_decoding_timestamp_and_validity(monkeypatch):
  import cereal.messaging as messaging
  from opendbc.can.packer import CANPacker
  from openpilot.common.swaglog import cloudlog
  addr,dat,bus=CANPacker('honda_civic_hatchback_ex_2017_can_generated').make_can_msg('ACC_CONTROL',1,dict(ACCEL_COMMAND=1.25,GAS_COMMAND=500,BRAKE_REQUEST=0))
  packet=messaging.new_message('sendcan',1);packet.logMonoTime=980000000
  packet.sendcan[0].address=addr;packet.sendcan[0].dat=dat;packet.sendcan[0].src=bus
  receive=iter([packet,None]);events=[]
  monkeypatch.setattr(messaging,'sub_sock',lambda *a,**k:object())
  monkeypatch.setattr(messaging,'recv_one_or_none',lambda sock:next(receive,None))
  monkeypatch.setattr(cloudlog,'event',lambda event,**row:events.append((event,row)))
  monkeypatch.setattr(cloudlog,'exception',lambda *a,**k:None)
  logger=RecoveryLogger(enabled=False);logger.enabled=True
  sm,row,trace=sample();logger.observe(sm,row,trace,.3,False,False)
  real_get=logger.queue.get
  def get(*a,**k):
    if logger.queue.empty():raise RuntimeError('end worker test')
    return real_get(*a,**k)
  monkeypatch.setattr(logger.queue,'get',get)
  logger._worker()
  result=next(v for k,v in events if k=='R20_RECOVERY')
  assert result['command_valid'] and result['command_age_s']==pytest.approx(.02)
  assert result['GAS_COMMAND']==500 and result['ACCEL_COMMAND']==pytest.approx(1.25)
  assert result['BRAKE_REQUEST']==0

def test_nonfinite_telemetry_is_explicitly_missing():
  assert RecoveryLogger._finite({'x':float('nan'),'y':[float('inf')]})=={'x':None,'y':[None]}
