"""Default-OFF dispatch; physical steering authority remains in controlsd/Honda."""
from cereal import car
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.controls.lib.desire_helper_baseline_v33 import *
from openpilot.selfdrive.controls.lib.desire_helper_baseline_v33 import DesireHelper as Baseline
from openpilot.selfdrive.controls.lib.desire_helper_experimental_v33 import DesireHelper as Experimental


class DesireHelper:
  def __init__(self, *args, **kwargs):
    self.params = Params()
    self.args = args
    self.kwargs = kwargs
    self.enabled = False
    self.impl = Baseline(*args, **kwargs)
    self.frame = 0
    self.previous_state = None

  def __getattr__(self, key):
    return getattr(self.impl, key)

  def update(self, carstate, lateral_active, lane_change_prob, left_edge_detected, right_edge_detected, cancel=False):
    enabled = self.params.get_bool('dp_exp_lca')
    cancel = cancel or any(e.type == car.CarState.ButtonEvent.Type.cancel and e.pressed for e in getattr(carstate, 'buttonEvents', []))
    if enabled != self.enabled:
      # Discard any confirmation or held maneuver when the live switch changes.
      self.impl = Experimental() if enabled else Baseline(*self.args, **self.kwargs)
      self.enabled = enabled
    if enabled:
      self.impl.update(carstate, lateral_active, lane_change_prob, left_edge_detected, right_edge_detected, cancel)
    else:
      self.impl.update(carstate, lateral_active, lane_change_prob, left_edge_detected, right_edge_detected)
    self.frame += 1
    current = (enabled, str(self.impl.lane_change_state), bool(lateral_active))
    if current != self.previous_state or (enabled and self.frame % 10 == 0):
      token = getattr(self.impl, 'token', None)
      cloudlog.event('MYCRV_EXPERIMENTAL_LCA', feature='lca', enabled=enabled,
        active=enabled and lateral_active and not self.impl.aborting and self.impl.lane_change_state in (LaneChangeState.laneChangeStarting, LaneChangeState.laneChangeFinishing),
        reason=str(self.impl.lane_change_state), lateral_active=bool(lateral_active),
        vEgo=float(carstate.vEgo), vCruise=float(getattr(carstate, 'vCruise', 0.)),
        confirmation=vars(token) if token is not None else None,
        left_edge=bool(left_edge_detected), right_edge=bool(right_edge_detected),
        limitation='此車型無可靠盲點資料，變換車道前請自行確認後方安全。')
    self.previous_state = current
