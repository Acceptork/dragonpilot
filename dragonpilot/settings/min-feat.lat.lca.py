from dragonpilot.settings import tr

ITEMS = [
  {
    "section": "Lateral",
    "key": "dp_lat_lca_speed",
    "type": "spin_button_item",
    "title": lambda: tr("Driver-Confirmed Lane Change Assist"),
    "description": lambda: tr("Off disables assistance. Any value above zero enables it at all speeds; the number is a legacy setting."),
    "default": "20",
    "min_val": 0,
    "max_val": 100,
    "step": 5,
    "special_value_text": lambda: tr("Off"),
    "flags": "PERSISTENT",
    "param_type": "INT",
  },
]
