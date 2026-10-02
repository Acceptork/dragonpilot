"""Optional, read-only longitudinal telemetry overlay for UI Debug Mode."""

import time

import pyray as rl

from openpilot.system.ui.lib.multilang import tr


REQUIRED_SERVICES = ("carState", "longitudinalPlan", "carControl", "radarState")


def build_longitudinal_debug_lines(sm) -> tuple[str, ...]:
  """Format observed messages only; these lines are never control decisions."""
  if not all(sm.seen[s] and sm.alive[s] and sm.valid[s] for s in REQUIRED_SERVICES):
    return (tr("Longitudinal data unavailable"),)

  cs = sm["carState"]
  plan = sm["longitudinalPlan"]
  cc = sm["carControl"]
  lead = sm["radarState"].leadOne
  cruise = cs.vCruiseCluster or cs.vCruise
  cruise_text = "--" if not 0 < cruise < 255 else f"{cruise:.0f}"
  lead_text = (f'{tr("Lead")} {lead.dRel:.1f} m / {tr("Relative")} {lead.vRel:+.1f} m/s'
               if lead.status else tr("No lead"))

  return (
    tr("Longitudinal Debug"),
    f'{tr("Speed")} {cs.vEgo * 3.6:.1f} / {tr("Set")} {cruise_text} km/h',
    f'{tr("Target")} {plan.aTarget:+.2f} / {tr("Command")} {cc.actuators.accel:+.2f} m/s²',
    lead_text,
    f'{tr("Throttle allowed")} {int(plan.allowThrottle)} / {tr("Stop intent")} {int(plan.shouldStop)}',
    f'{tr("Source")} {plan.longitudinalPlanSource} / {tr("State")} {cc.actuators.longControlState} / {tr("Long active")} {int(cc.longActive)}',
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
