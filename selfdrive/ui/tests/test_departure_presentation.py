import importlib
import json
from types import SimpleNamespace
import pytest
from cereal import car, log
from openpilot.selfdrive.ui.departure_runtime import CUE_KEY
from openpilot.selfdrive.ui.soundd import Soundd


@pytest.mark.parametrize('module_name',['openpilot.selfdrive.ui.onroad.alert_renderer','openpilot.selfdrive.ui.mici.onroad.alert_renderer'])
def test_cue_on_actual_renderer_and_existing_alert_priority(monkeypatch,module_name):
  module=importlib.import_module(module_name)
  params=SimpleNamespace(get=lambda key:json.dumps(dict(kind='lead_departure',issued_at=10.,expires_at=13.)),get_bool=lambda key:True)
  monkeypatch.setattr(module,'ui_state',SimpleNamespace(params=params,started=True,started_frame=1,started_time=0.))
  monkeypatch.setattr(module.time,'monotonic',lambda:11.)
  ss=log.SelfdriveState.new_message()
  class SM(dict):
    pass
  sm=SM(selfdriveState=ss)
  sm.updated={'selfdriveState':True}
  sm.recv_frame={'selfdriveState':2}
  renderer=object.__new__(module.AlertRenderer)
  assert renderer.get_alert(sm).text1=='前車已起步'
  ss.alertSize='full'
  ss.alertStatus='critical'
  ss.alertText1='BRAKE!'
  assert renderer.get_alert(sm).text1!='前車已起步'


@pytest.mark.parametrize('current,incoming,timeout,expected',[
  ('none','none',False,True),('warningImmediate','none',False,False),
  ('none','warningImmediate',False,False),('engage','none',False,False),('none','none',True,False)])
def test_audio_cue_never_replaces_existing_warning(current,incoming,timeout,expected):
  alert=car.CarControl.HUDControl.AudibleAlert
  sound=object.__new__(Soundd)
  sound.departure_runtime=SimpleNamespace(update=lambda sm,t:dict(kind='lead_departure'))
  sound.current_alert=getattr(alert,current)
  sound.selfdrive_timeout_alert=timeout
  played=[]
  sound.update_alert=played.append
  sm={'selfdriveState':log.SelfdriveState.new_message(alertSound=incoming)}
  sound.get_departure_alert(sm)
  assert played==([alert.prompt] if expected else [])
