from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_exp_restart',
    'type': 'toggle_item',
    'title': lambda: tr('自動跟車起步'),
    'description': lambda: tr('預設關閉。可靠同一前車持續移動且通過共同安全條件後，才允許原控制器起步；不以十公分微動起步。\nParam: dp_exp_restart'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '0',
    'section': '實驗功能',
  },
]
