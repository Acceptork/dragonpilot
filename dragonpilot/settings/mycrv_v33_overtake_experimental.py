from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_exp_overtake',
    'type': 'toggle_item',
    'title': lambda: tr('超車預加速'),
    'description': lambda: tr('預設關閉，僅供可控場地。方向燈後需新同方向施力與變道開始；僅在原前車安全約束內小幅預加速。Stage 2 尚未啟用。\nParam: dp_exp_overtake'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '0',
    'section': '實驗功能',
  },
]
