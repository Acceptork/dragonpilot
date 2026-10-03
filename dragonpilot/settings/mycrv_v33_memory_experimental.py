from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_exp_lead_memory',
    'type': 'toggle_item',
    'title': lambda: tr('前車短暫記憶'),
    'description': lambda: tr('預設關閉。短暫失去可靠前車時保守保持；逾時仍不明確時不主動補油，請接管或關閉。不能偵測模型從未看到的機車。\nParam: dp_exp_lead_memory'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '0',
    'section': '實驗功能',
  },
]
