"""Extract timestamped R20 markers and samples from local rlogs."""
import argparse
import json
from tools.lib.logreader import LogReader

def main():
  ap=argparse.ArgumentParser(description=__doc__)
  ap.add_argument('logs',nargs='+');ap.add_argument('--output',required=True)
  args=ap.parse_args()
  with open(args.output,'w',encoding='utf8') as out:
    for path in args.logs:
      for message in LogReader(path,sort_by_time=True):
        if message.which()!='logMessage':continue
        try:
          data=json.loads(message.logMessage);row=data.get('msg',data)
          if isinstance(row,str):row=json.loads(row)
          if not isinstance(row,dict) or not row.get('event','').startswith('R20_'):continue
          out.write(json.dumps(dict(log_timestamp_ns=int(message.logMonoTime),**row),ensure_ascii=False)+'\n')
        except (ValueError,TypeError):continue

if __name__=='__main__':main()
