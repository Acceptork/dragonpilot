from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_exp_lca',
    'type': 'toggle_item',
    'title': lambda: tr('低速變換車道'),
    'description': lambda: tr('預設關閉，僅供可控場地。方向燈後需新的同方向施力確認。此車型無可靠盲點資料，變換車道前請自行確認後方安全。\nParam: dp_exp_lca'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '0',
    'section': '實驗功能',
  },
]
