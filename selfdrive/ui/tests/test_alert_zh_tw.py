"""Display-only Traditional Chinese translation checks for selfdrived alerts."""

import ast
import importlib
from pathlib import Path
import re
import time
from types import SimpleNamespace

import pytest

from openpilot.common.basedir import BASEDIR
from openpilot.selfdrive.ui.onroad.alert_text_translations import ALERT_TEXT_MSGIDS, translate_alert_text
from openpilot.selfdrive.ui.translations.potools import extract_strings
from openpilot.system.ui.lib.multilang import load_translations, multilang


ROOT = Path(BASEDIR)
EVENTS = ROOT / "selfdrive/selfdrived/events.py"
ALERT_KEYS = ROOT / "selfdrive/ui/onroad/alert_text_translations.py"
CATALOG = ROOT / "selfdrive/ui/translations/app_zh-CHT.po"


@pytest.fixture
def traditional_chinese():
  prior = multilang.language
  multilang._language = "zh-CHT"
  multilang.setup()
  yield
  multilang._language = prior
  multilang.setup()


def direct_alert_literals():
  tree = ast.parse(EVENTS.read_text(encoding="utf-8"), filename=str(EVENTS))
  literals = set()
  for node in ast.walk(tree):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or not node.func.id.endswith("Alert"):
      continue
    values = list(node.args[:2]) + [kw.value for kw in node.keywords if kw.arg in ("alert_text_1", "alert_text_2")]
    for value in values:
      if isinstance(value, ast.Constant) and isinstance(value.value, str) and re.search("[A-Za-z]", value.value):
        literals.add(value.value)
  return literals


def test_every_direct_alert_literal_has_marker_and_translation():
  direct = direct_alert_literals()
  extracted = {entry.msgid for entry in extract_strings([str(ALERT_KEYS.relative_to(ROOT))], str(ROOT))}
  translations, _ = load_translations(CATALOG)
  assert len(direct) == 119
  assert direct <= ALERT_TEXT_MSGIDS
  assert ALERT_TEXT_MSGIDS == extracted
  assert all(translations.get(key) for key in ALERT_TEXT_MSGIDS)


def test_soft_disable_helper_alert_literals_have_translation():
  tree = ast.parse(EVENTS.read_text(encoding="utf-8"), filename=str(EVENTS))
  helper_names = {"soft_disable_alert", "user_soft_disable_alert"}
  literals = {node.args[0].value for node in ast.walk(tree)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in helper_names and node.args
              and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)}
  translations, _ = load_translations(CATALOG)
  assert len(literals) == 29
  assert literals <= ALERT_TEXT_MSGIDS
  assert all(translations.get(key) for key in literals)


@pytest.mark.parametrize(("source", "expected"), [
  ("BRAKE!", "立刻煞車！"),
  ("AEB: Risk of Collision", "AEB：有碰撞風險"),
  ("Stock AEB: Risk of Collision", "原車 AEB：有碰撞風險"),
  ("Emergency Braking: Risk of Collision", "緊急煞車：有碰撞風險"),
  ("Bookmark Saved", "已標記事件"),
  ("Steer Left to Start Lane Change Once Safe", "確認安全後，向左操作方向盤變換車道"),
  ("Car Detected in Blindspot", "盲點偵測到車輛"),
])
def test_critical_and_requested_alerts_translate_at_runtime(traditional_chinese, source, expected):
  assert translate_alert_text(source) == expected


def test_dynamic_alert_is_not_guessed_or_rewritten(traditional_chinese):
  text = "Speed Error: 1.2 m/s"
  assert translate_alert_text(text) == text


class FakeSM:
  updated = {"selfdriveState": True}
  recv_frame = {"selfdriveState": 10}

  def __init__(self, state):
    self.state = state

  def __getitem__(self, key):
    assert key == "selfdriveState"
    return self.state


@pytest.mark.parametrize("module_name", [
  "openpilot.selfdrive.ui.onroad.alert_renderer",
  "openpilot.selfdrive.ui.mici.onroad.alert_renderer",
])
@pytest.mark.parametrize(("text1", "text2"), [
  ("BRAKE!", "Emergency Braking: Risk of Collision"),
  ("AEB: Risk of Collision", "Stock AEB: Risk of Collision"),
  ("Bookmark Saved", ""),
  ("Steer Left to Start Lane Change Once Safe", "Confirm Lane Change"),
])
def test_both_renderers_translate_only_display_text(traditional_chinese, monkeypatch, module_name, text1, text2):
  module = importlib.import_module(module_name)
  monkeypatch.setattr(module, "ui_state", SimpleNamespace(started_frame=0, started_time=0))
  state = SimpleNamespace(alertText1=text1, alertText2=text2,
                          alertSize=SimpleNamespace(raw=3), alertStatus=SimpleNamespace(raw=2),
                          alertHudVisual=0, alertType="test/warning")
  renderer = module.AlertRenderer.__new__(module.AlertRenderer)
  rendered = renderer.get_alert(FakeSM(state))
  assert rendered is not None
  assert rendered.text1 == translate_alert_text(text1)
  assert rendered.text2 == translate_alert_text(text2)
  assert rendered.size == 3 and rendered.status == 2
  if hasattr(rendered, "alert_type"):
    assert rendered.alert_type == "test/warning"
  assert state.alertText1 == text1 and state.alertText2 == text2


@pytest.mark.parametrize("module_name", [
  "openpilot.selfdrive.ui.onroad.alert_renderer",
  "openpilot.selfdrive.ui.mici.onroad.alert_renderer",
])
@pytest.mark.parametrize("alert_name", ["ALERT_STARTUP_PENDING", "ALERT_CRITICAL_TIMEOUT", "ALERT_CRITICAL_REBOOT"])
def test_predefined_alerts_follow_runtime_language_switch(monkeypatch, module_name, alert_name):
  module = importlib.import_module(module_name)
  original = getattr(module, alert_name)
  assert original.text1 in ("openpilot Unavailable", "TAKE CONTROL IMMEDIATELY", "System Unresponsive")
  prior = multilang.language
  try:
    multilang._language = "zh-CHT"
    multilang.setup()
    def displayed_alert():
      now = time.monotonic()
      is_startup = alert_name == "ALERT_STARTUP_PENDING"
      elapsed = 6 if alert_name == "ALERT_CRITICAL_TIMEOUT" else 20
      monkeypatch.setattr(module, "TICI", True)
      monkeypatch.setattr(module, "ui_state", SimpleNamespace(started_frame=1, started_time=now - 6))
      sm = FakeSM(SimpleNamespace(enabled=True, alertSize=0))
      sm.updated = {"selfdriveState": False}
      sm.recv_frame = {"selfdriveState": 0 if is_startup else 10}
      sm.recv_time = {"selfdriveState": now - elapsed}
      return module.AlertRenderer.__new__(module.AlertRenderer).get_alert(sm)

    localized = displayed_alert()
    assert localized.text1 == translate_alert_text(original.text1)
    assert localized.text2 == translate_alert_text(original.text2)
    assert localized.text1 != original.text1
    assert localized.size == original.size and localized.status == original.status
    multilang._language = "en-US"
    multilang.setup()
    english = displayed_alert()
    assert english.text1 == original.text1 and english.text2 == original.text2
  finally:
    multilang._language = prior
    multilang.setup()
