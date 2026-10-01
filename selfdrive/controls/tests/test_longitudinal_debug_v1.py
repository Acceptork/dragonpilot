import csv
from types import SimpleNamespace as Msg

from openpilot.selfdrive.controls.longitudinal_debug import FIELDS, RotatingLongCsv, sample


def test_csv_rotates_and_keeps_only_newest_files(tmp_path):
  writer = RotatingLongCsv(tmp_path, max_file_bytes=500, max_files=3)
  for i in range(50):
    writer.write([i] * len(FIELDS))
  writer.close()

  files = sorted(tmp_path.glob('long-*.csv'))
  assert len(files) == 3
  assert all(file.stat().st_size <= 500 for file in files)
  for file in files:
    with file.open(newline='', encoding='utf-8') as stream:
      rows = list(csv.reader(stream))
    assert tuple(rows[0]) == FIELDS
    assert len(rows) > 1


def test_sample_has_requested_fields_without_location_or_media():
  sm = {
    'carState': Msg(vEgo=20.0, aEgo=0.1, vCruise=90.0, vCruiseCluster=90.0),
    'carControl': Msg(actuators=Msg(accel=0.4), orientationNED=[0.0, 0.02, 0.0]),
    'controlsState': Msg(longControlState='pid', upAccelCmd=0.0, uiAccelCmd=0.0, ufAccelCmd=0.4),
    'longitudinalPlan': Msg(aTarget=0.4, allowThrottle=True, longitudinalPlanSource='cruise'),
    'radarState': Msg(leadOne=Msg(status=False), leadTwo=Msg(status=False)),
    'selfdriveState': Msg(personality='standard', experimentalMode=False),
    'modelV2': Msg(meta=Msg(disengagePredictions=Msg(gasPressProbs=[0.2, 0.1]))),
  }
  data = dict(zip(FIELDS, sample(sm), strict=True))
  assert data['gasPressProb'] == 0.1
  assert data['aTarget'] == 0.4
  assert data['pitch'] == 0.02
  assert data['longitudinalPlanSource'] == 'cruise'
  assert data['personality'] == 'standard'
  assert not any('gps' in field.lower() or 'image' in field.lower() or 'audio' in field.lower() for field in FIELDS)
