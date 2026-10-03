from pathlib import Path

import pytest
import pyray as rl
import time

from openpilot.common.params import Params
from dragonpilot.settings import SETTINGS
from dragonpilot.selfdrive.ui.layouts.settings.dragonpilot import DragonpilotLayout
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, MousePos

CONTROLS = {'dp_exp_'+s for s in ('early_stop','taper','restart','lca','overtake','ramp','lead_memory','personality')}
REMINDERS = {'dp_departure_lead_alert','dp_departure_signal_alert'}


def test_real_registry_contains_all_ten():
  sections = [s for s in SETTINGS if s['title'] == '實驗功能']
  assert len(sections) == 1
  items = sections[0]['settings']
  assert len(items) == 10
  assert {i['key'] for i in items} == CONTROLS | REMINDERS
  for item in items:
    assert callable(item['title']) and callable(item['description'])
    assert item['key'] in item['description']()
    assert item['default'] == ('0' if item['key'] in CONTROLS else '1')
    assert not item.get('condition') and not item.get('depends_on')


def test_traditional_chinese_atlas_contains_all_setting_text():
  from openpilot.selfdrive.assets.fonts.process import _char_sets
  _, _, languages = _char_sets()
  glyphs = set(languages['zh-CHT'])
  for section in SETTINGS:
    if section['title'] != '實驗功能':
      continue
    for item in section['settings']:
      assert {ord(c) for c in item['title']() + item['description']() if not c.isspace()} <= glyphs


def test_widget_navigation_and_param_binding(monkeypatch):
  params = Params()
  monkeypatch.setattr(ui_state, 'params', params)
  monkeypatch.setattr(ui_state, 'update_params', lambda: None)
  # Exercise real widgets and callbacks headlessly; physical rendering is a separate device gate.
  monkeypatch.setattr(gui_app, 'font', lambda *args: rl.Font())
  monkeypatch.setattr(gui_app, 'texture', lambda *args, **kwargs: rl.Texture())
  layout = DragonpilotLayout()
  layout.show_event()
  assert layout._scroller is layout._main_scroller
  layout._set_experiments_open(True)
  assert layout._scroller is layout._experiment_scroller
  for key in sorted(CONTROLS | REMINDERS):
    meta = layout._toggle_metadata[key]
    assert meta['param_name'] == key
    toggle = meta['widget'].action_item.toggle
    original = {k: params.get_bool(k) for k in CONTROLS | REMINDERS}
    for value in (not original[key], original[key]):
      toggle._handle_mouse_release(MousePos(0,0))
      deadline = time.monotonic() + 2
      while params.get_bool(key) != value and time.monotonic() < deadline:
        time.sleep(0.01)
      assert params.get_bool(key) == value
      assert all(params.get_bool(k) == v for k,v in original.items() if k != key)
  # Changing storage externally must be reflected when reopening the page.
  params.put_bool('dp_exp_lca', True, block=True)
  layout._set_experiments_open(False)
  layout._set_experiments_open(True)
  assert layout._toggle_metadata['dp_exp_lca']['widget'].action_item.get_state()
  params.put_bool('dp_exp_lca', False, block=True)
  layout.show_event()
  assert not layout._toggle_metadata['dp_exp_lca']['widget'].action_item.get_state()


@pytest.mark.parametrize('key', sorted(CONTROLS | REMINDERS))
def test_runtime_reader_exists(key):
  root = Path(__file__).resolve().parents[3]
  paths = ['selfdrive/controls/lib/longitudinal_planner.py', 'selfdrive/controls/lib/desire_helper.py',
           'selfdrive/controls/controlsd.py', 'selfdrive/ui/departure_runtime.py']
  assert any(f"get_bool('{key}')" in (root/path).read_text() for path in paths)
