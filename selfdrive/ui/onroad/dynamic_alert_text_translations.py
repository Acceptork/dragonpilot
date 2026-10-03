"""Exact-format display translation for dynamic selfdrived alerts.

This module never changes the producer's alert text or safety metadata. An
unrecognised string is displayed verbatim. Numeric values and units are copied
from the incoming message; no unit conversion or interpretation is performed.
"""

import re

from openpilot.system.ui.lib.multilang import tr, tr_noop


_INTEGER = r"-?(?:0|[1-9]\d*)"
_DECIMAL_ONE = rf"(?:{_INTEGER}\.\d|nan|-?inf)"
_NUMBER = rf"(?:{_INTEGER}(?:\.\d+)?|nan|-?inf)"
_SPEED = rf"{_INTEGER} (?:km/h|mph)"

# Each regex must match the complete string produced by one events.py callback.
# The msgid is a placeholder template extracted by update_translations.
_FORMATS = (
  (re.compile(rf"Drive above (?P<speed>{_SPEED}) to engage"), tr_noop("Drive above {speed} to engage")),
  (re.compile(rf"Steer Assist Unavailable Below (?P<speed>{_SPEED})"), tr_noop("Steer Assist Unavailable Below {speed}")),
  (re.compile(rf"Calibrating: (?P<percent>{_INTEGER})%"), tr_noop("Calibrating: {percent}%")),
  (re.compile(rf"Recalibrating: (?P<percent>{_INTEGER})%"), tr_noop("Recalibrating: {percent}%")),
  (re.compile(rf"Drive Above (?P<speed>{_SPEED})"), tr_noop("Drive Above {speed}")),
  (re.compile(rf"(?P<percent>{_INTEGER})% full"), tr_noop("{percent}% full")),
  (re.compile(rf"Speed Error: (?P<error>{_DECIMAL_ONE}) m/s"), tr_noop("Speed Error: {error} m/s")),
  (re.compile(rf"Remount Device \(Pitch: (?P<pitch>{_DECIMAL_ONE})°, Yaw: (?P<yaw>{_DECIMAL_ONE})°\)"),
   tr_noop("Remount Device (Pitch: {pitch}°, Yaw: {yaw}°)")),
  (re.compile(rf"Angle offset too high \(Offset: (?P<offset>{_DECIMAL_ONE})°\)"),
   tr_noop("Angle offset too high (Offset: {offset}°)")),
  (re.compile(rf"Steering rack geometry may be off \(Ratio: (?P<ratio>{_DECIMAL_ONE})\)"),
   tr_noop("Steering rack geometry may be off (Ratio: {ratio})")),
  (re.compile(rf"Check tires, pressure, or alignment \(Factor: (?P<factor>{_DECIMAL_ONE})\)"),
   tr_noop("Check tires, pressure, or alignment (Factor: {factor})")),
  (re.compile(rf"(?P<percent>{_NUMBER})% used"), tr_noop("{percent}% used")),
  (re.compile(rf"(?P<percent>{_DECIMAL_ONE})% frames dropped"), tr_noop("{percent}% frames dropped")),
  (re.compile(rf"Gas: (?P<gas>{_INTEGER})%, Steer: (?P<steer>{_INTEGER})%"),
   tr_noop("Gas: {gas}%, Steer: {steer}%")),
  (re.compile(r"Driving Personality: (?P<personality>Relaxed|Standard|Aggressive)"),
   tr_noop("Driving Personality: {personality}")),
)

_AUDIO_FEEDBACK = re.compile(rf"(?P<seconds>{_INTEGER}) second(?P<plural>s?) remaining\. Press again to save early\.")
_AUDIO_FEEDBACK_MSGID = tr_noop("{seconds} seconds remaining. Press again to save early.")

# The camera names come from camera_malfunction_alert's fixed source tuple.
_CAMERA_NAMES = (
  tr_noop("roadCamera"),
  tr_noop("driverCamera"),
  tr_noop("wideRoadCamera"),
)

DYNAMIC_ALERT_MSGIDS = frozenset(template for _, template in _FORMATS) | {_AUDIO_FEEDBACK_MSGID, *_CAMERA_NAMES}


def _translate_template(template: str, values: dict[str, str], original: str) -> str:
  translated = tr(template)
  return translated.format_map(values) if translated != template else original


def translate_dynamic_alert_text(text: str) -> str:
  audio = _AUDIO_FEEDBACK.fullmatch(text)
  if audio is not None:
    values = audio.groupdict()
    if bool(values["plural"]) == (int(values["seconds"]) != 1):
      return _translate_template(_AUDIO_FEEDBACK_MSGID, {"seconds": values["seconds"]}, text)
    return text

  for pattern, template in _FORMATS:
    match = pattern.fullmatch(text)
    if match is None:
      continue
    values = match.groupdict()
    if "personality" in values:
      values["personality"] = tr(values["personality"])
    return _translate_template(template, values, text)

  names = text.split(", ")
  if names and all(name in _CAMERA_NAMES for name in names):
    # Only accept the producer's fixed camera order, with no repeated entries.
    indexes = [_CAMERA_NAMES.index(name) for name in names]
    if indexes == sorted(set(indexes)):
      translated = [tr(name) for name in names]
      if all(value != name for value, name in zip(translated, names, strict=True)):
        return ", ".join(translated)

  return text
