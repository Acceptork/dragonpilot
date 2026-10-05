"""Exact per-service replay comparison. Only proven wall-time fields omitted."""
import argparse
import collections
import json

WALL_TIME_FIELDS = {'longitudinalPlan': {'solverExecutionTime'}, 'carState': {'cumLagMs'}}

def canonical(row):
  out = dict(row)
  if isinstance(row.get('payload'), dict):
    out['payload'] = {k: v for k, v in row['payload'].items()
                      if k not in WALL_TIME_FIELDS.get(row['type'], set())}
  return out

def compare(a, b):
  result = {}
  for service in sorted({r['type'] for r in a + b}):
    aa = [canonical(r) for r in a if r['type'] == service]
    bb = [canonical(r) for r in b if r['type'] == service]
    result[service] = abs(len(aa)-len(bb)) + sum(x != y for x,y in zip(aa,bb))
  return {'identity': not any(result.values()), 'different_messages': result,
          'counts': [dict(collections.Counter(r['type'] for r in rows)) for rows in (a,b)],
          'normalization': {k: sorted(v) for k,v in WALL_TIME_FIELDS.items()}}

def load(path):
  def reject(value):
    raise ValueError('Non-finite JSON value: '+value)
  with open(path,encoding='utf8') as f:
    return [json.loads(line,parse_constant=reject) for line in f]

if __name__ == '__main__':
  ap=argparse.ArgumentParser()
  ap.add_argument('baseline_a');ap.add_argument('baseline_b')
  args=ap.parse_args()
  result=compare(load(args.baseline_a),load(args.baseline_b))
  print(json.dumps(result,indent=2))
  raise SystemExit(0 if result['identity'] else 1)
