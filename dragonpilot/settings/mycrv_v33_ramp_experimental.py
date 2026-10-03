from dragonpilot.settings import tr

ITEMS = [
  {
    'key': 'dp_exp_ramp',
    'type': 'toggle_item',
    'title': lambda: tr('匝道追速實驗'),
    'description': lambda: tr('預設關閉，僅供可控場地。上坡且模型正加速度偏小時有限追速；前車接近、停止或危險訊號立即禁止。\nParam: dp_exp_ramp'),
    'flags': 'PERSISTENT',
    'param_type': 'BOOL',
    'default': '0',
    'section': '實驗功能',
  },
]
