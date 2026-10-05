"""Bounded, best-effort R20 telemetry. No I/O on the control thread.

Raw sendcan is already recorded in rlog. Decoded commands here are timestamped
observations, not a claim that a command was caused by this model frame.
"""
from collections import deque
import math
import os
from pathlib import Path
import queue
import threading


class RecoveryLogger:
  def __init__(self, enabled=None):
    self.enabled = (Path('/TICI').exists() and os.environ.get('REPLAY') != '1') if enabled is None else enabled
    self.queue = queue.Queue(maxsize=32)
    self.dropped = 0
    self.previous_active = False
    self.event_id = None
    self.enter_reason = None
    if self.enabled:
      threading.Thread(target=self._worker, name='r20-telemetry', daemon=True).start()

  def observe(self, sm, recovery, trace, final, stop, fcw):
    if not self.enabled:
      return
    try:
      active = bool(recovery['active'])
      if not active and not self.previous_active:
        return
      timestamp = int(sm.logMonoTime['modelV2'])
      kind = 'ENTER' if active and not self.previous_active else 'EXIT' if not active else 'SAMPLE'
      if kind == 'ENTER':
        self.event_id = f'R20_{timestamp}'
        self.enter_reason = recovery['reason']
      self.previous_active = active
      cs, cc = sm['carState'], sm['carControl']
      pitch = float(cc.orientationNED[1]) if len(cc.orientationNED)==3 else None
      leads = [sm['radarState'].leadOne.to_dict(), sm['radarState'].leadTwo.to_dict()]
      row = dict(event='R20_RECOVERY', kind=kind, event_id=self.event_id, model_timestamp_ns=timestamp,
        timestamp=timestamp/1e9, vEgo=float(cs.vEgo), vEgoCluster=float(cs.vEgoCluster),
        vCruise=float(cs.vCruise), speed_deficit_kph=float(cs.vCruise-cs.vEgoCluster*3.6),
        e2e_accel=float(trace['e2e']), MPC_accel=float(trace['mpc']),
        baseline_selected_accel=float(recovery['before']), R20_selected_accel=float(recovery['after']),
        final_aTarget=float(final), aEgo=float(cs.aEgo), lead0=leads[0], lead1=leads[1],
        shouldStop=bool(stop), FCW=bool(fcw), hardBrake=bool(sm['modelV2'].meta.hardBrakePredicted),
        curvature=float(sm['controlsState'].curvature), turn_cap=float(trace['turn_max']), pitch=pitch,
        driver_gas=bool(cs.gasPressed), driver_brake=bool(cs.brakePressed), longActive=bool(cc.longActive),
        recovery_active=active, recovery_state=recovery['state'], recovery_enter_reason=self.enter_reason,
        recovery_exit_reason=recovery['reason'] if kind=='EXIT' else None,
        safety_veto_reason=recovery['reason'] if kind=='EXIT' else None,
        downstream_veto=bool(recovery.get('downstream_veto',False)), dropped_samples=self.dropped)
      self.queue.put_nowait(row)
    except Exception:
      # Telemetry failures and queue pressure must not affect control authority.
      self.dropped += 1

  @staticmethod
  def _finite(value):
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,dict):return {k:RecoveryLogger._finite(v) for k,v in value.items()}
    if isinstance(value,list):return [RecoveryLogger._finite(v) for v in value]
    return value

  def _worker(self):
    import cereal.messaging as messaging
    from openpilot.common.swaglog import cloudlog
    from opendbc.can.dbc import DBC
    from opendbc.can.parser import get_raw_value
    commands = deque(maxlen=256)
    sock = None
    try:
      db = DBC('honda_civic_hatchback_ex_2017_can_generated')
      messages = {addr:msg for addr,msg in db.addr_to_msg.items() if msg.name=='ACC_CONTROL'}
      sock = messaging.sub_sock('sendcan', timeout=0)
      cloudlog.event('R20_LOGGER_READY', schema=1, queue_capacity=32, raw_commands='rlog.sendcan')
      while True:
        try:
          row = self.queue.get(timeout=.1)
        except queue.Empty:
          row = None
        for _ in range(64):
          packet = messaging.recv_one_or_none(sock)
          if packet is None:break
          for frame in packet.sendcan:
            msg=messages.get(frame.address)
            if msg is None:continue
            values={}
            for sig in msg.sigs.values():
              if sig.name not in ('GAS_COMMAND','ACCEL_COMMAND','BRAKE_REQUEST'):continue
              raw=get_raw_value(frame.dat,sig)
              if sig.is_signed and raw&(1<<(sig.size-1)):raw-=1<<sig.size
              values[sig.name]=raw*sig.factor+sig.offset
            commands.append((int(packet.logMonoTime),int(frame.src),values))
        if row is None:continue
        command=next((v for v in reversed(commands) if v[0]<=row['model_timestamp_ns']),None)
        age=(row['model_timestamp_ns']-command[0])/1e9 if command else None
        fresh=command is not None and 0<=age<=.2
        row.update(command_timestamp_ns=command[0] if command else None,command_age_s=age,
                   command_bus=command[1] if command else None,command_valid=fresh,
                   **(command[2] if fresh else dict(GAS_COMMAND=None,ACCEL_COMMAND=None,BRAKE_REQUEST=None)))
        event=row.pop('event')
        cloudlog.event(event,**self._finite(row))
    except Exception:
      self.dropped += 1
      # This is a telemetry thread only. Existing rlog still retains sendcan.
      try:cloudlog.exception('R20_LOGGER_UNAVAILABLE')
      except Exception:pass
