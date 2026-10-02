import csv
from types import SimpleNamespace as Msg
from cereal import log

from openpilot.selfdrive.controls.longitudinal_debug import FIELDS, RotatingLongCsv, sample


def test_csv_rotates_and_keeps_only_newest_files(tmp_path):
  writer = RotatingLongCsv(tmp_path, max_file_bytes=1600, max_files=3)
  for i in range(120):
    writer.write([i] * len(FIELDS))
  writer.close()

  files = sorted(tmp_path.glob('long-*.csv'))
  assert len(files) == 3
  assert all(file.stat().st_size <= 1600 for file in files)
  for file in files:
    with file.open(newline='', encoding='utf-8') as stream:
      rows = list(csv.reader(stream))
    assert tuple(rows[0]) == FIELDS
    assert len(rows) > 1


def test_sample_has_requested_fields_without_location_or_media():
  sm = {
    'carState': Msg(vEgo=20.0, vEgoRaw=20.1, vEgoCluster=20.2, aEgo=0.1, vCruise=90.0, vCruiseCluster=90.0),
    'carControl': Msg(actuators=Msg(accel=0.4), longActive=False, orientationNED=[0.0, 0.02, 0.0]),
    'controlsState': Msg(longControlState='pid', upAccelCmd=0.0, uiAccelCmd=0.0, ufAccelCmd=0.4),
    'longitudinalPlan': Msg(aTarget=0.4, allowThrottle=True, longitudinalPlanSource='cruise'),
    'radarState': Msg(leadOne=Msg(status=False), leadTwo=Msg(status=False)),
    'selfdriveState': Msg(personality=log.LongitudinalPersonality.standard, experimentalMode=False, enabled=True),
    'modelV2': Msg(meta=Msg(disengagePredictions=Msg(gasPressProbs=[0.2, 0.1]))),
  }
  cp = Msg(pcmCruise=False, openpilotLongitudinalControl=True)
  data = dict(zip(FIELDS, sample(sm, cp, 'decelCruise:down', True, (20.0, 20.1, 20.2), 80.0), strict=True))
  assert data['gasPressProb'] == 0.1
  assert data['aTarget'] == 0.4
  assert data['longActive'] is False
  assert data['pitch'] == 0.02
  assert data['longitudinalPlanSource'] == 'cruise'
  assert data['personality'] == 'standard'
  assert data['selectedPersonality'] == 'standard'
  assert data['tFollow'] == 1.45
  assert data['jerkFactor'] == 1.0
  assert data['throttleOverrideActive'] is True
  assert data['cruiseSpeedError'] == 18.0
  assert data['buttonVEgoRaw'] == 20.1
  assert data['buttonEnable'] is True
  assert data['vCruiseBefore'] == 80.0
  assert not any('gps' in field.lower() or 'image' in field.lower() or 'audio' in field.lower() for field in FIELDS)
