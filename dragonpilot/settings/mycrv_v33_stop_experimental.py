from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_exp_early_stop',
    'type': 'toggle_item',
    'title': lambda: tr('提前減速實驗'),
    'description': lambda: tr('預設關閉。僅供可控場地逐項驗證；可能因非停車減速而提早煞車。駕駛隨時接管。\nParam: dp_exp_early_stop'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '0',
    'section': '實驗功能',
  },
]
