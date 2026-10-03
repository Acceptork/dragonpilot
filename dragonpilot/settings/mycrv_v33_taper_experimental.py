from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_exp_taper',
    'type': 'toggle_item',
    'title': lambda: tr('平順停車實驗'),
    'description': lambda: tr('預設關閉。僅供可控場地。接近停止時維持制動並建立穩定 hold；距離或坡度不可靠時禁止收煞。發現滑動立即踩煞車接管。\nParam: dp_exp_taper'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '0',
    'section': '實驗功能',
  },
]
