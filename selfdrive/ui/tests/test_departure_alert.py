from dataclasses import replace
import pytest
from openpilot.selfdrive.ui.departure_alert import DepartureAlerts, Observation


def observation(t, **values):
  base = Observation(t, True, True, 'drive', 0., False,
    dict(d=10., vr=0., y=0., prob=.95), .3, -.2)
  return replace(base, **values)


def run_departure(machine, **values):
  events = []
  for i in range(120):
    t = i*.05
    moving = max(0., t-2.)
    lead = dict(d=10.+moving, vr=1. if moving else 0., y=0., prob=.95)
    event = machine.update(observation(t, lead=lead, **values))
    if event:
      events.append(event)
  return events


def test_departure_once_without_any_acc_input():
  events = run_departure(DepartureAlerts())
  assert len(events) == 1
  assert events[0]['text'] == '前車已起步'
  assert events[0]['control_effect'] == 'NONE'


@pytest.mark.parametrize('values', [dict(gas=True), dict(speed=.3), dict(gear='reverse'),
  dict(gear='park'), dict(onroad=False), dict(valid=False), dict(hazard=True), dict(closer_obstacle=True)])
def test_common_suppression(values):
  assert not run_departure(DepartureAlerts(), **values)


def test_ten_centimetres_and_jitter_do_not_alert():
  machine = DepartureAlerts()
  for i in range(200):
    t = i*.05
    d = 10. if t<2 else 10.1+(i%2)*.01
    assert machine.update(observation(t, lead=dict(d=d,vr=.4 if t>2 else 0.,y=0.,prob=.95))) is None


def test_discontinuous_new_lead_does_not_depart():
  machine = DepartureAlerts()
  for i in range(120):
    t = i*.05
    d = 10. if t<2 else 20.+t
    assert machine.update(observation(t, lead=dict(d=d,vr=1. if t>=2 else 0.,y=0.,prob=.95))) is None


def test_no_lead_cue_requires_sustained_prior_slowdown():
  machine = DepartureAlerts()
  events=[]
  for i in range(160):
    t=i*.05
    event=machine.update(observation(t,lead=None,endpoint=.3 if t<4 else 5.,desired_accel=-.2 if t<4 else .3))
    if event:
      events.append(event)
  assert len(events)==1
  assert events[0]['text']=='前方可能已可通行'
  assert '綠燈' not in events[0]['text']


def test_positive_trajectory_alone_never_alerts():
  machine=DepartureAlerts()
  for i in range(160):
    assert machine.update(observation(i*.05,lead=None,endpoint=5.,desired_accel=.3)) is None


def test_flags_disable_independently():
  machine=DepartureAlerts()
  for i in range(140):
    t=i*.05
    assert machine.update(observation(t,lead=None,endpoint=.3 if t<4 else 5.,desired_accel=-.2 if t<4 else .3),
                          lead_enabled=True,signal_enabled=False) is None
  machine=DepartureAlerts()
  for i in range(120):
    t=i*.05
    assert machine.update(observation(t,lead=dict(d=10.+max(0,t-2),vr=1. if t>2 else 0.,y=0.,prob=.95)),
                          lead_enabled=False,signal_enabled=True) is None


def test_data_gap_cannot_rearm_same_stop():
  machine=DepartureAlerts()
  assert len(run_departure(machine))==1
  for i in range(120):
    t=30.+i*.05
    assert machine.update(observation(t,lead=dict(d=10.+max(0,t-32),vr=1. if t>32 else 0.,y=0.,prob=.95))) is None
