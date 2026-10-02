"""Optional, read-only longitudinal telemetry overlay for UI Debug Mode."""

import math
import time

import pyray as rl

from openpilot.system.ui.lib.multilang import tr


REQUIRED_SERVICES = ("carState", "longitudinalPlan", "carControl", "radarState")


def valid_cruise_speed(cluster_speed, cruise_speed) -> float | None:
  # CarState uses 0, -1 and 255 as unset values on different paths.
  for speed in (cluster_speed, cruise_speed):
    if isinstance(speed, (int, float)) and math.isfinite(speed) and 0 < speed < 255:
      return speed
  return None


def enum_key(value, numeric_names: tuple[str, ...]) -> str:
  raw = str(getattr(value, "name", value)).rsplit(".", 1)[-1]
  if raw.isdigit() and int(raw) < len(numeric_names):
    return numeric_names[int(raw)]
  return raw


def plan_source_text(value) -> str:
  # These are the values defined by cereal/log.capnp LongitudinalPlanSource.
  key = enum_key(value, ("cruise", "lead0", "lead1", "lead2", "e2e"))
  labels = {
    "cruise": tr("Cruise"),
    "lead0": tr("Lead 1"),
    "lead1": tr("Lead 2"),
    "lead2": tr("Lead 3"),
    "e2e": tr("End-to-end model"),
  }
  return labels.get(key, f'{tr("Unknown")} ({value})')


def long_control_state_text(value) -> str:
  # These are the values defined by cereal/car.capnp LongControlState.
  key = enum_key(value, ("off", "pid", "stopping", "starting"))
  labels = {
    "off": tr("Off"),
    "pid": tr("PID control"),
    "stopping": tr("Stopping"),
    "starting": tr("Starting"),
  }
  return labels.get(key, f'{tr("Unknown")} ({value})')


def build_longitudinal_debug_lines(sm) -> tuple[str, ...]:
  """Format observed messages only; these lines are never control decisions."""
  if not all(sm.seen[s] and sm.alive[s] and sm.valid[s] for s in REQUIRED_SERVICES):
    return (tr("Longitudinal data unavailable"),)

  cs = sm["carState"]
  plan = sm["longitudinalPlan"]
  cc = sm["carControl"]
  lead = sm["radarState"].leadOne
  cruise = valid_cruise_speed(cs.vCruiseCluster, cs.vCruise)
  cruise_text = "--" if cruise is None else f"{cruise:.0f}"
  lead_text = (f'{tr("Lead")} {lead.dRel:.1f} m / {tr("Relative")} {lead.vRel:+.1f} m/s'
               if lead.status else tr("No lead"))

  return (
    tr("Longitudinal Debug"),
    f'{tr("Speed")} {cs.vEgo * 3.6:.1f} / {tr("Set")} {cruise_text} km/h',
    f'{tr("Target")} {plan.aTarget:+.2f} / {tr("Command")} {cc.actuators.accel:+.2f} m/s²',
    lead_text,
    f'{tr("Throttle allowed")} {int(plan.allowThrottle)} / {tr("Stop intent")} {int(plan.shouldStop)}',
    f'{tr("Source")} {plan_source_text(plan.longitudinalPlanSource)} / {tr("State")} {long_control_state_text(cc.actuators.longControlState)} / {tr("Long active")} {int(cc.longActive)}',
  )


class LongitudinalDebugOverlay:
  def __init__(self):
    from openpilot.system.ui.lib.application import FontWeight, gui_app
    self._font = gui_app.font(FontWeight.MEDIUM)
    self._last_update = 0.0
    self._lines: tuple[str, ...] = ()

  def render(self, rect: rl.Rectangle, sm) -> None:
    now = time.monotonic()
    if now - self._last_update >= 0.1 or not self._lines:
      self._lines = build_longitudinal_debug_lines(sm)
      self._last_update = now
    lines = self._lines
    font_size, line_height, padding = 25, 32, 17
    width = min(930, rect.width - 40)
    height = len(lines) * line_height + 2 * padding
    box = rl.Rectangle(rect.x + 20, rect.y + rect.height - height - 20, width, height)
    rl.draw_rectangle_rounded(box, 0.08, 8, rl.Color(0, 0, 0, 175))
    for index, line in enumerate(lines):
      pos = rl.Vector2(box.x + padding, box.y + padding + index * line_height)
      rl.draw_text_ex(self._font, line, pos, font_size, 0, rl.WHITE)
