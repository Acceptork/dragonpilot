#!/usr/bin/env python3
"""Preview closed-course flag presets; changes require an explicit pinned local-device apply."""
import argparse
import json
import platform
import re
import subprocess
from pathlib import Path

FLAGS = {
  'early_stop': '提前減速實驗', 'taper': '平順停車實驗', 'restart': '自動跟車起步',
  'lca': '低速變換車道', 'overtake': '超車預加速', 'ramp': '匝道追速實驗',
  'lead_memory': '前車短暫記憶', 'personality': '巡航回復性格實驗',
}
PROFILES = {
  'ALL_OFF': (),
  'PROFILE_A_STOP': ('early_stop', 'taper', 'restart'),
  'PROFILE_B_LCA': ('lca',),
  'PROFILE_C_PERFORMANCE': ('ramp', 'personality'),
  'PROFILE_D_OVERTAKE': ('lca', 'overtake'),
}


def values(profile):
  return {'dp_exp_' + name: name in PROFILES[profile] for name in FLAGS}


def apply_profile(params, profile):
  desired = values(profile)
  if not params.get_bool('IsOffroad'):
    raise RuntimeError('必須停車且 IsOffroad=1，未改動任何開關')
  try:
    # Clear previous profile before enabling selected features; never retain unrelated experiments.
    for key in desired:
      params.put_bool(key, False)
    for key, enabled in desired.items():
      if not params.get_bool('IsOffroad'):
        raise RuntimeError('車輛離開 offroad，取消設定')
      if enabled:
        params.put_bool(key, True)
    if not params.get_bool('IsOffroad') or any(params.get_bool(k) != v for k,v in desired.items()):
      raise RuntimeError('設定後狀態不符')
  except Exception as original:
    failures=[]
    for key in desired:
      try:
        params.put_bool(key, False)
      except Exception:
        failures.append(key)
    if failures:
      raise RuntimeError('設定失敗且無法完整關閉：' + ','.join(failures)) from original
    raise
  return desired


def main():
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('profile',choices=PROFILES)
  parser.add_argument('--apply',action='store_true')
  parser.add_argument('--sha',help='Required exact current experimental commit when applying')
  args=parser.parse_args()
  if not args.apply:
    print(json.dumps(dict(profile=args.profile,flags=values(args.profile),execution='NOT_RUN',
      requirement='CLOSED_COURSE_REQUIRED',overtake_stage2='BLOCKED_NO_VALIDATED_PROVIDER'),indent=2,ensure_ascii=False))
    return
  if not args.sha or not re.fullmatch('[0-9a-f]{40}',args.sha):
    parser.error('--apply requires exact --sha')
  if platform.machine()!='aarch64' or not Path('/VERSION').is_file():
    raise RuntimeError('本機只可預覽；套用需在實際 comma 裝置停車時進行')
  root=Path('/data/openpilot')
  actual=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
  if actual!=args.sha or subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip():
    raise RuntimeError('目前版本或 working tree 不符；未更改設定')
  from openpilot.common.params import Params
  print(json.dumps(apply_profile(Params(),args.profile),indent=2))


if __name__=='__main__':
  main()
