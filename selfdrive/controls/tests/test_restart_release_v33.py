import pytest
from openpilot.selfdrive.controls.lib.restart_release_v33 import RestartRelease


def call(s, base=-2., **kwargs):
  args = dict(base=base, stopping=True, enabled=True, active=True, driver_override=False)
  args.update(kwargs)
  return s.update(**args)


@pytest.mark.parametrize('target', [0., 1.091041922569275, 1.3240478038787842])
def test_recorded_release_boundary(target):
  s = RestartRelease()
  previous = call(s)['after']
  for _ in range(200):
    r = call(s, target, stopping=False)
    assert r['after'] <= target
    assert r['after'] - previous <= .020000000001
    previous = r['after']
  assert r['after'] == target


@pytest.mark.parametrize('field,value', [('enabled',False),('active',False),('driver_override',True)])
def test_handoff_is_immediate(field, value):
  s = RestartRelease()
  call(s)
  assert call(s, .5, stopping=False, **{field:value})['after'] == .5
  assert call(s, .7, stopping=False)['after'] == .7


def test_stronger_brake_and_restop_priority():
  s = RestartRelease()
  call(s)
  call(s, 1., stopping=False)
  assert call(s, -3., stopping=False)['after'] == -3.
  assert call(s, -3.5, stopping=True)['after'] == -3.5


def test_no_previous_stop_no_effect():
  s = RestartRelease()
  assert call(s, -.4, stopping=False)['after'] == -.4
  assert call(s, 1., stopping=False)['after'] == 1.

def test_restop_during_release_preserves_stricter_command():
  s = RestartRelease()
  call(s, -.8438952946662903)
  previous = call(s, 1.1142265796661377, stopping=False)['after']
  previous = call(s, 1.1142265796661377, stopping=False)['after']
  result = call(s, -.008, stopping=True)
  assert result['after'] <= previous + .020000000001
  assert result['after'] <= -.008
  assert call(s, -3., stopping=True)['after'] == -3.
