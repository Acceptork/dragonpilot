from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_exp_personality',
    'type': 'toggle_item',
    'title': lambda: tr('巡航回復性格實驗'),
    'description': lambda: tr('預設關閉。只在無前車與停止約束的巡航中改變正加速度回復速度；不改追距、MPC 權重或危險煞車。\nParam: dp_exp_personality'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '0',
    'section': '實驗功能',
  },
]
