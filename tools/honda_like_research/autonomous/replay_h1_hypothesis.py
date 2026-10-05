"""Native fixed-input planner/MPC replay, all locally available requested rlogs.
No device connection; results are not a vehicle dynamics or full controlsd replay.
"""
import sys, pathlib, json, math, collections, traceback, argparse, os, importlib.util
BASE=pathlib.Path(os.environ.get('OPENPILOT_RESEARCH_TREE',pathlib.Path(__file__).resolve().parents[3]))
sys.path[:0]=[str(BASE),str(BASE/'opendbc_repo')]
import numpy as np
from types import SimpleNamespace
from tools.lib.logreader import LogReader
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from opendbc.can.dbc import DBC
from opendbc.can.parser import get_raw_value
spec=importlib.util.spec_from_file_location('baseline_planner',os.environ['RECOVERY_BASELINE_SOURCE'])
baseline_module=importlib.util.module_from_spec(spec);sys.modules['baseline_planner']=baseline_module;spec.loader.exec_module(baseline_module)
BaselinePlanner=baseline_module.LongitudinalPlanner


class SM(dict):pass
keys=['carState','carControl','controlsState','selfdriveState','radarState','modelV2','liveParameters']
D=pathlib.Path(os.environ['RECOVERY_REPLAY_OUTPUT']);D.mkdir(parents=True,exist_ok=True)
from self_train_ratio_policy import policy as make_policy
events=json.loads(pathlib.Path(os.environ['RECOVERY_EVENT_MANIFEST']).read_text())['events']
db=DBC('honda_civic_hatchback_ex_2017_can_generated')
messages={a:m for a,m in db.addr_to_msg.items() if m.name in ('ACC_CONTROL','ACC_HUD','POWERTRAIN_DATA','BRAKE_MODULE')}
def decode(dat,msg):
 out={}
 for s in msg.sigs.values():
  if s.name not in ('ACCEL_COMMAND','GAS_COMMAND','BRAKE_REQUEST','CONTROL_ON','STANDSTILL','ACC_STATUS','CRUISE_SPEED','BRAKE_PRESSED'):continue
  raw=get_raw_value(dat,s)
  if s.is_signed and raw&(1<<(s.size-1)):raw-=1<<s.size
  out[s.name]=raw*s.factor+s.offset
 return out
def predicted_ay(m,v):
 # Model orientation rate is yaw-rate over predicted trajectory, not traffic semantics.
 z=list(m.orientationRate.z);vx=list(m.velocity.x)
 if len(z)!=33 or len(vx)!=33 or not all(math.isfinite(x) for x in z+vx):return float('nan')
 return max(abs(z[i])*max(v,vx[i]) for i in range(1,17))
def plain(x):
 if isinstance(x,np.generic):return x.item()
 raise TypeError(str(type(x)))
routes=sorted(p for p in pathlib.Path(os.environ['RECOVERY_INPUT_ROOT']).iterdir() if p.is_dir())
summary={}
for route in routes:
 paths=sorted(route.glob('*/rlog.zst'),key=lambda p:int(p.parent.name.rsplit('--',1)[-1]))
 if not paths:continue
 legacy=os.environ.get('AUTONOMOUS_SAVE_TRAJECTORY')=='1'
 sm=SM();sm.valid={};sm.logMonoTime={};cp=None;params={};plans=None;policy=None;last_model=None;start=None;previous_seg=None
 counts=collections.Counter();errors=[];can={};sent={};records=[];last_plan=None;recorded={}
 dest=D/'native';dest.mkdir(exist_ok=True)
 fout=(dest/(route.name+'.jsonl')).open('w')
 for path in paths:
  seg=int(path.parent.name.rsplit('--',1)[-1])
  if previous_seg is not None and seg!=previous_seg+1:sm=SM();sm.valid={};sm.logMonoTime={};plans=None;last_model=None;can={};sent={}
  previous_seg=seg;segment_rows=[];services=collections.Counter()
  try:
   for msg in LogReader(str(path),sort_by_time=True):
    k=msg.which();t=msg.logMonoTime/1e9;services[k]+=1
    if k=='initData':
     params={e.key:e.value==b'1' for e in msg.initData.params.entries}
    if k=='carParams':cp=msg.carParams
    if k=='longitudinalPlan':
     lp=msg.longitudinalPlan;last_plan=dict(t=t,aTarget=float(lp.aTarget),shouldStop=bool(lp.shouldStop),FCW=bool(lp.fcw),source=str(lp.longitudinalPlanSource))
     recorded[int(lp.modelMonoTime)]=last_plan
    if k in ('can','sendcan'):
     target=can if k=='can' else sent
     for frame in getattr(msg,k):
      if frame.address in messages:
       target[str(frame.src)+':'+messages[frame.address].name]=dict(t=t,values=decode(frame.dat,messages[frame.address]))
    if k not in keys:continue
    sm[k]=getattr(msg,k);sm.valid[k]=bool(msg.valid);sm.logMonoTime[k]=msg.logMonoTime
    if k!='modelV2' or cp is None or not all(x in sm for x in keys):continue
    if last_model is not None and not 0<t-last_model<.15:plans=None
    last_model=t
    if plans is None:
     plans=[klass(cp,init_v=sm['carState'].vEgo,init_a=sm['carState'].aEgo) for klass in (BaselinePlanner,LongitudinalPlanner,LongitudinalPlanner,LongitudinalPlanner)]
     for candidate,ratio in zip(plans[1:],(.10,.15,.20)):candidate.recovery=make_policy(ratio)
     # The actual production settings are preserved in both variants. No UI change.
     for p in plans:p.v33_params=SimpleNamespace(get_bool=lambda key:params.get(key,False))
     start=t
    dp_flags=sum(bit for key,bit in [('dp_lon_acm',1),('dp_lon_aem',2),('dp_lon_apm',4)] if params.get(key,False))
    plans[0].update(sm,dp_flags=dp_flags)
    p=plans[0];cs=sm['carState'];cc=sm['carControl'];md=sm['modelV2'];rs=sm['radarState'];tr=p.diagnostic_trace
    ages={s:(msg.logMonoTime-sm.logMonoTime[s])/1e9 for s in keys}
    # liveParameters is legitimately slower; remaining control/model services <=300ms.
    valid=all(sm.valid.values()) and all(0<=age<(1.5 if s=='liveParameters' else .3) for s,age in ages.items()) and bool(cs.canValid)
    pitch=float(cc.orientationNED[1]) if len(cc.orientationNED)==3 else float('nan')
    ay=abs(float(sm['controlsState'].curvature))*float(cs.vEgo)**2;pay=predicted_ay(md,float(cs.vEgo))
    stop=bool(p.output_should_stop or md.action.shouldStop)
    for candidate in plans[1:]:candidate.update(sm,dp_flags=dp_flags)
    pc=plans[2]
    recovery=pc.diagnostic_trace['recovery']
    proposed=recovery['after'];state=recovery['state'];reason=recovery['reason']
    window=[e['id'] for e in events if e['route']==route.name and -12<=t-e['t']<=8]
    if t-start<15:counts['warmup_frames']+=1
    row=dict(route=route.name,segment=seg,t=t,model_ns=int(msg.logMonoTime),warmup=t-start<15,op_config=bool(cp.openpilotLongitudinalControl),longActive=bool(cc.longActive),cruiseEnabled=bool(cs.cruiseState.enabled),valid=valid,ages=ages,state=state,reason=reason,event_ids=window,cluster=float(cs.vEgoCluster),v=float(cs.vEgo),vc=float(cs.vCruise),a=float(cs.aEgo),gas=bool(cs.gasPressed),brake=bool(cs.brakePressed),steering=float(cs.steeringAngleDeg),pitch=pitch,ay=ay,predicted_ay=pay,lead0=rs.leadOne.to_dict(),lead1=rs.leadTwo.to_dict(),e2e=float(tr['e2e']),proposed_e2e=float(proposed),mpc=float(tr['mpc']),existing=float(p.output_a_target),candidate=float(pc.output_a_target),existing_source=str(p.mpc.source),candidate_source=str(pc.mpc.source),shouldStop=bool(p.output_should_stop),candidate_shouldStop=bool(pc.output_should_stop),fcw=bool(p.fcw),candidate_fcw=bool(pc.fcw),hardBrake=bool(md.meta.hardBrakePredicted),modelStop=bool(md.action.shouldStop),allowThrottle=bool(p.allow_throttle),longState=str(sm['controlsState'].longControlState),actAccel=float(cc.actuators.accel),actGas=float(cc.actuators.gas),actBrake=float(cc.actuators.brake),actState=str(cc.actuators.longControlState),solver=int(p.mpc.solution_status),candidate_solver=int(pc.mpc.solution_status),cap=list(map(float,tr['accel_limits'])),can={k:v for k,v in can.items() if 0<=t-v['t']<.3},sendcan={k:v for k,v in sent.items() if 0<=t-v['t']<.3},flags={k:v for k,v in params.items() if k.startswith('dp_exp_')},experiments=tr.get('experiments'),candidate_experiments=pc.diagnostic_trace.get('experiments'),model_endpoint=float(md.velocity.x[-1]) if len(md.velocity.x) else None)
    if window or legacy:row['model_trajectory']={s:getattr(md,s).to_dict() for s in ('position','velocity','acceleration','orientationRate')}
    row.update(recovery=recovery,curvature=float(sm['controlsState'].curvature),experimentalMode=bool(sm['selfdriveState'].experimentalMode),forceDecel=bool(sm['controlsState'].forceDecel),cruise_cap=tr['cruise_max'],turn_cap=tr['turn_max'],candidate_cap=list(map(float,pc.diagnostic_trace['accel_limits'])))
    row['variants']={str(ratio):dict(target=float(q.output_a_target),stop=bool(q.output_should_stop),fcw=bool(q.fcw),solver=int(q.mpc.solution_status),recovery=q.diagnostic_trace['recovery']) for ratio,q in zip((.10,.15,.20),plans[1:])}
    row['trace_geometry']={key:tr.get(key) for key in ('actual_curvature','cruise_max','turn_max','pre_clip','post_clip')}
    row['live_geometry']=dict(angleOffsetDeg=float(sm['liveParameters'].angleOffsetDeg),steerRatio=float(sm['liveParameters'].steerRatio),stiffnessFactor=float(sm['liveParameters'].stiffnessFactor),roll=float(sm['liveParameters'].roll),cpSteerRatio=float(cp.steerRatio),wheelbase=float(cp.wheelbase))
    segment_rows.append(row);counts['frames']+=1
   for row in segment_rows:
    row['recorded_plan']=recorded.get(row['model_ns']);row['baseline_error']=row['existing']-row['recorded_plan']['aTarget'] if row['recorded_plan'] else None
    fout.write(json.dumps(row,default=plain,allow_nan=True)+'\n')
   fout.flush();counts['segments']+=1
   print(route.name,seg,'frames',len(segment_rows),'total',counts['frames'],flush=True)
  except Exception:
   errors.append(dict(segment=seg,error=traceback.format_exc()));plans=None
   print('ERROR',route.name,seg,errors[-1]['error'],flush=True)
  summary[route.name]={'counts':dict(counts),'errors':errors,'last_segment':seg}
  (dest/'progress.json').write_text(json.dumps(summary,indent=2))
 fout.close()
print('COMPLETE',json.dumps(summary),flush=True)
