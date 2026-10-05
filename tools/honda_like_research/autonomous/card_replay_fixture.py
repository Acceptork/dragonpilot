"""Replay-only explicit post-ECU-initialization fixture; never a production patch."""
import os,json,time,hashlib
OUT=None
MODE='post_init'
def main():
  assert os.environ.get('REPLAY')=='1', 'Offline replay fixture only'
  assert OUT is not None
  from opendbc.car.honda.interface import CarInterface
  from openpilot.selfdrive.car import card
  original_init=CarInterface.init
  def initialized_fixture(CP,can_recv,can_send,communication_control=None):
    if MODE=='audit_original':
      count={'recv_calls':0,'CAN_packets_consumed':0,'CAN_frames_consumed':0};digest=hashlib.sha256()
      def traced_recv(*args,**kwargs):
        rows=can_recv(*args,**kwargs);count['recv_calls']+=1;count['CAN_packets_consumed']+=len(rows)
        for packet in rows:
          for msg in packet:
            count['CAN_frames_consumed']+=1;digest.update(str(msg.address).encode()+msg.dat)
        return rows
      start=time.monotonic();original_init(CP,traced_recv,can_send,communication_control)
      with open(OUT,'a') as f:f.write(json.dumps({'fixture':'unmodified_hardware_init_in_offline_replay',**count,'consumed_sha256':digest.hexdigest(),'wall_seconds':time.monotonic()-start})+'\n')
      return
    with open(OUT,'a') as f:
      f.write(json.dumps({'fixture':'post_hardware_initialization','openpilotLongitudinalControl':CP.openpilotLongitudinalControl,
                         'hardware_handshake_validated':False,'CAN_consumed_by_fixture':0,'physical_CAN_sent':0})+'\n')
  CarInterface.init=staticmethod(initialized_fixture)
  card.main()
