"""Offline, display-only tests for exact dynamic selfdrived alert formats."""

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from openpilot.common.basedir import BASEDIR
from openpilot.selfdrive.ui.onroad.alert_text_translations import translate_alert_text
from openpilot.selfdrive.ui.onroad.dynamic_alert_text_translations import DYNAMIC_ALERT_MSGIDS
from openpilot.selfdrive.ui.translations.potools import extract_strings
from openpilot.system.ui.lib.multilang import load_translations, multilang


ROOT = Path(BASEDIR)
DYNAMIC_KEYS = ROOT / "selfdrive/ui/onroad/dynamic_alert_text_translations.py"
CATALOG = ROOT / "selfdrive/ui/translations/app_zh-CHT.po"


@pytest.fixture
def traditional_chinese():
  prior = multilang.language
  multilang._language = "zh-CHT"
  multilang.setup()
  yield
  multilang._language = prior
  multilang.setup()


def test_all_dynamic_templates_are_extracted_and_translated():
  extracted = {entry.msgid for entry in extract_strings([str(DYNAMIC_KEYS.relative_to(ROOT))], str(ROOT))}
  translations, _ = load_translations(CATALOG)
  assert len(DYNAMIC_ALERT_MSGIDS) == 19
  assert DYNAMIC_ALERT_MSGIDS == extracted
  assert all(translations.get(key) for key in DYNAMIC_ALERT_MSGIDS)


class FakeSM:
  updated = {"selfdriveState": True}
  recv_frame = {"selfdriveState": 10}

  def __init__(self, state):
    self.state = state

  def __getitem__(self, key):
    assert key == "selfdriveState"
    return self.state


DYNAMIC_CASES = (
  ("below engage km/h", "Drive above 30 km/h to engage", "請加速至 30 km/h 以上再啟用"),
  ("below engage mph", "Drive above 20 mph to engage", "請加速至 20 mph 以上再啟用"),
  ("below steer", "Steer Assist Unavailable Below 15 km/h", "低於 15 km/h 時無法使用轉向輔助"),
  ("calibrating", "Calibrating: 48%", "校正中：48%"),
  ("recalibrating", "Recalibrating: 9%", "重新校正中：9%"),
  ("calibration speed", "Drive Above 25 mph", "請以高於 25 mph 的速度行駛"),
  ("audio singular", "1 second remaining. Press again to save early.", "還剩 1 秒。再次按下可提前儲存。"),
  ("audio plural", "5 seconds remaining. Press again to save early.", "還剩 5 秒。再次按下可提前儲存。"),
  ("storage", "91% full", "儲存空間已使用 91%"),
  ("posenet", "Speed Error: -1.2 m/s", "車速誤差：-1.2 m/s"),
  ("camera names", "roadCamera, wideRoadCamera", "道路攝影機, 廣角道路攝影機"),
  ("calibration angles", "Remount Device (Pitch: -2.1°, Yaw: 1.3°)", "請重新固定裝置（俯仰角：-2.1°，偏航角：1.3°）"),
  ("paramsd angle", "Angle offset too high (Offset: 4.3°)", "轉向偏角過大（偏角：4.3°）"),
  ("paramsd ratio", "Steering rack geometry may be off (Ratio: 18.2)", "轉向機構幾何可能異常（轉向比：18.2）"),
  ("paramsd stiffness", "Check tires, pressure, or alignment (Factor: 0.7)", "請檢查輪胎、胎壓或定位（係數：0.7）"),
  ("overheat numeric", "86 °C", "86 °C"),
  ("memory percent", "72% used", "已使用 72%"),
  ("CPU float percent", "72.5% used", "已使用 72.5%"),
  ("model drop", "4.7% frames dropped", "影格遺失 4.7%"),
  ("joystick", "Gas: 14%, Steer: -3%", "油門：14%，轉向：-3%"),
  ("personality", "Driving Personality: Aggressive", "駕駛風格：積極"),
  ("startup branch", "my-crv-v3.1-rc1", "my-crv-v3.1-rc1"),
  ("process list", "plannerd, controlsd", "plannerd, controlsd"),
  ("service list", "carState, modelV2", "carState, modelV2"),
  ("alertDebug unknown", "Experimental stop at 30m", "Experimental stop at 30m"),
)


@pytest.mark.parametrize("module_name", [
  "openpilot.selfdrive.ui.onroad.alert_renderer",
  "openpilot.selfdrive.ui.mici.onroad.alert_renderer",
])
@pytest.mark.parametrize(("category", "source", "expected"), DYNAMIC_CASES, ids=[case[0] for case in DYNAMIC_CASES])
def test_dynamic_text_on_both_renderers_preserves_metadata(traditional_chinese, monkeypatch, module_name, category, source, expected):
  module = importlib.import_module(module_name)
  monkeypatch.setattr(module, "ui_state", SimpleNamespace(started_frame=0, started_time=0))
  state = SimpleNamespace(alertText1=source, alertText2=source,
                          alertSize=SimpleNamespace(raw=3), alertStatus=SimpleNamespace(raw=2),
                          alertHudVisual=7, alertType="test/critical")
  rendered = module.AlertRenderer.__new__(module.AlertRenderer).get_alert(FakeSM(state))
  assert rendered.text1 == expected and rendered.text2 == expected
  assert rendered.size == 3 and rendered.status == 2
  if hasattr(rendered, "visual_alert"):
    assert rendered.visual_alert == 7 and rendered.alert_type == "test/critical"
  assert state.alertText1 == source and state.alertText2 == source


@pytest.mark.parametrize("source", [
  "Drive above 30 knots to engage",
  "Drive above 30 km/h to engage now",
  "1 seconds remaining. Press again to save early.",
  "2 second remaining. Press again to save early.",
  "Driving Personality: Sport",
  "roadCamera, mysteryCamera",
  "wideRoadCamera, roadCamera",
  "BRAKE?",
])
def test_unknown_or_malformed_text_stays_verbatim(traditional_chinese, source):
  assert translate_alert_text(source) == source


def test_existing_critical_takeover_alert_remains_translated(traditional_chinese):
  assert translate_alert_text("TAKE CONTROL IMMEDIATELY") == "請立刻接手控制"
  assert translate_alert_text("BRAKE!") == "立刻煞車！"
  assert translate_alert_text("Recording Audio Feedback") == "正在錄製語音回報"


def test_dynamic_translation_follows_language_change():
  prior = multilang.language
  try:
    multilang._language = "en-US"
    multilang.setup()
    assert translate_alert_text("Drive above 30 km/h to engage") == "Drive above 30 km/h to engage"
    multilang._language = "zh-CHT"
    multilang.setup()
    assert translate_alert_text("Drive above 30 km/h to engage") == "請加速至 30 km/h 以上再啟用"
  finally:
    multilang._language = prior
    multilang.setup()
