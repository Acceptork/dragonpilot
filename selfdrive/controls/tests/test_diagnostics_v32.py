from openpilot.selfdrive.controls.lib.diagnostics_v32 import OvershootEvent,emit_trace
def test_event_rearm_and_no_spam():
  g=OvershootEvent()
  assert sum(g.update(i*.05,95,90,True) for i in range(100))==1
  assert not g.update(5.,90,90,True)
  assert sum(g.update(5.05+i*.05,95,90,True) for i in range(100))==1
def test_invalid_and_gap():
  g=OvershootEvent()
  for i in range(20):assert not g.update(i*.05,95,90,True)
  assert not g.update(5.,95,90,True)
  assert not g.update(5.05,95,255,True)
def test_sink_failure_isolated(monkeypatch):
  monkeypatch.setenv('MYCRV_V32_TRACE_FILE','/nonexistent/v32/trace')
  emit_trace({'t':0.})
