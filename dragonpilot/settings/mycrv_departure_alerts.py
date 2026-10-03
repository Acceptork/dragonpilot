from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_departure_lead_alert',
    'type': 'toggle_item',
    'title': lambda: tr('前車起步提醒'),
    'description': lambda: tr('本車停妥且前車持續起步確認後，駕駛連續 4 秒未起步才提供畫面與提示音。ACC 未啟用仍可使用；不會解除煞車或自動加速。\nParam: dp_departure_lead_alert'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '1',
    'section': '實驗功能',
  },
  {
    'key': 'dp_departure_signal_alert',
    'type': 'toggle_item',
    'title': lambda: tr('號誌通行提醒'),
    'description': lambda: tr('模型前進軌跡持續成立且駕駛連續 4 秒未起步才提示「前方可能已可通行」。此功能並非紅綠燈辨識，請自行確認號誌及路況；不會控制車輛。\nParam: dp_departure_signal_alert'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '1',
    'section': '實驗功能',
  },
  {
    'key': 'dp_departure_alert_cue',
    'flags': 'CLEAR_ON_MANAGER_START',
    'param_type': 'STRING',
  },
]
