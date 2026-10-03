from openpilot.selfdrive.controls.lib.eps_shadow_v33 import SteeringReturnCapture

def row(t, desired=.003, actual=.003):
  return dict(t=t, desired_curvature=desired, actual_curvature=actual,
              steer_limited_by_safety=False, rate_limiting=False)

def test_pre_post_capture():
  c = SteeringReturnCapture()
  event = None
  for i in range(600):
    _, e = c.update(row(i * .05, .003 if i < 240 else 0.))
    if e:
      event = e
  assert event and event['complete']
  assert event['trigger'] - event['rows'][0]['t'] >= 9.95
  assert event['rows'][-1]['t'] - event['trigger'] >= 10.

def test_no_event_without_actual_lag():
  c = SteeringReturnCapture()
  for i in range(600):
    _, event = c.update(row(i * .05, .003 if i < 240 else 0., .003 if i < 240 else 0.))
    assert event is None

def test_gap_invalidates_pending():
  c = SteeringReturnCapture()
  for i in range(240):
    c.update(row(i * .05, .003 if i < 100 else 0.))
  assert c.pending
  c.update(row(100., 0., 0.))
  assert c.pending is None
