"""Driver-confirmed LCA: no helper speed/BSM gates; vehicle latActive remains authoritative."""
from dataclasses import dataclass
from cereal import log
from openpilot.common.realtime import DT_MDL

LaneChangeState=log.LaneChangeState
LaneChangeDirection=log.LaneChangeDirection
LANE_CHANGE_TIME_MAX=10.

@dataclass
class Confirmation:
  direction: str
  epoch: int
  timestamp: float
  consumed: bool=False

class DesireHelper:
  def __init__(self,dp_lat_lca_speed=20,dp_lat_lca_auto_sec=0.):
    self.lca_enabled=True
    self.lane_change_state=LaneChangeState.off
    self.lane_change_direction=LaneChangeDirection.none
    self.lane_change_timer=0.
    self.lane_change_ll_prob=1.
    self.desire=log.Desire.none
    self.keep_pulse_timer=0.
    self.token=None
    self.epoch=0
    self.time=0.
    self.last_active=False
    self.last_direction=LaneChangeDirection.none
    self.last_torque=False
    self.aborting=False

  def invalidate(self):
    self.token=None

  def update(self,carstate,lateral_active,lane_change_prob,left_edge_detected,right_edge_detected,cancel=False):
    self.time+=DT_MDL
    one=carstate.leftBlinker != carstate.rightBlinker
    direction=(LaneChangeDirection.left if carstate.leftBlinker else LaneChangeDirection.right) if one else LaneChangeDirection.none
    torque=one and carstate.steeringPressed and ((carstate.steeringTorque>0 and direction==LaneChangeDirection.left) or
                                                (carstate.steeringTorque<0 and direction==LaneChangeDirection.right))
    fresh=torque and not self.last_torque
    changed=direction!=self.last_direction
    active_edge=lateral_active!=self.last_active
    if active_edge:
      self.epoch+=1; self.invalidate()
    if changed or cancel or not one:self.invalidate()
    timeout=self.lane_change_timer>LANE_CHANGE_TIME_MAX
    edge=(left_edge_detected if direction==LaneChangeDirection.left else right_edge_detected)
    in_maneuver=self.lane_change_state in (LaneChangeState.laneChangeStarting,LaneChangeState.laneChangeFinishing)
    if not lateral_active or not self.lca_enabled:
      self.lane_change_state=LaneChangeState.preLaneChange if one and self.lca_enabled else LaneChangeState.off
      self.lane_change_direction=direction
      self.lane_change_ll_prob=1.;self.aborting=False;self.invalidate()
    elif cancel or timeout or (in_maneuver and (changed or not one or edge or (carstate.steeringPressed and not torque))):
      self.invalidate()
      self.aborting=True
      self.lane_change_state=LaneChangeState.laneChangeFinishing
      self.lane_change_ll_prob=min(1.,self.lane_change_ll_prob+DT_MDL)
      if self.lane_change_ll_prob>=1.:
        self.lane_change_state=LaneChangeState.off;self.lane_change_direction=LaneChangeDirection.none
    elif self.aborting:
      self.lane_change_ll_prob=min(1.,self.lane_change_ll_prob+DT_MDL)
      if self.lane_change_ll_prob>=1.:
        self.aborting=False;self.lane_change_state=LaneChangeState.preLaneChange if one else LaneChangeState.off
        self.lane_change_direction=direction
    elif self.lane_change_state==LaneChangeState.off:
      if one:
        self.lane_change_state=LaneChangeState.preLaneChange
        self.lane_change_direction=direction
    elif self.lane_change_state==LaneChangeState.preLaneChange:
      self.lane_change_direction=direction
      if not one:
        self.lane_change_state=LaneChangeState.off
      elif fresh and not changed and not active_edge and not edge:
        self.token=Confirmation("left" if direction==LaneChangeDirection.left else "right",self.epoch,self.time,True)
        self.lane_change_state=LaneChangeState.laneChangeStarting
    elif self.lane_change_state==LaneChangeState.laneChangeStarting:
      self.lane_change_ll_prob=max(0.,self.lane_change_ll_prob-2*DT_MDL)
      if lane_change_prob<.02 and self.lane_change_ll_prob<.01:
        self.lane_change_state=LaneChangeState.laneChangeFinishing
    elif self.lane_change_state==LaneChangeState.laneChangeFinishing:
      self.lane_change_ll_prob=min(1.,self.lane_change_ll_prob+DT_MDL)
      if self.lane_change_ll_prob>.99:
        self.invalidate()
        self.lane_change_state=LaneChangeState.preLaneChange if one else LaneChangeState.off
        self.lane_change_direction=direction
    self.lane_change_timer=self.lane_change_timer+DT_MDL if self.lane_change_state in (LaneChangeState.laneChangeStarting,LaneChangeState.laneChangeFinishing) else 0.
    self.desire=log.Desire.none
    if not self.aborting and lateral_active and self.lane_change_state in (LaneChangeState.laneChangeStarting,LaneChangeState.laneChangeFinishing):
      self.desire=log.Desire.laneChangeLeft if self.lane_change_direction==LaneChangeDirection.left else log.Desire.laneChangeRight
    self.last_active=lateral_active;self.last_direction=direction;self.last_torque=torque
