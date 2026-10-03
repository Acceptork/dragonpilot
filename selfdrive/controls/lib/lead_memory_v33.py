"""Short lead dropout association sidecar. Never turns unknown into clear."""
import math


class LeadMemory:
  def __init__(self, horizon=.3):
    if horizon not in (.2, .3, .5):
      raise ValueError('supported sweep horizons: .2/.3/.5 seconds')
    self.horizon = horizon
    self.last = None
    self.unknown = False
    self.unknown_bound = None
    self.track = 0

  @staticmethod
  def reliable(lead):
    return (lead.get('prob', 0.) >= .8 and all(math.isfinite(lead.get(k, float('nan'))) for k in ('d', 'vr', 'y', 'std'))
            and 0 < lead['d'] <= 35 and abs(lead['vr']) < 25 and abs(lead['y']) < 1.5
            and 0 <= lead['std'] < 1.5 and lead.get('path_ok', False))

  def update(self, t, leads, ego_speed, path_ok):
    measured = sorted([x for x in leads if x.get('measured', False)], key=lambda x: x['d'])
    prior = self.last
    age = t - prior['t'] if prior is not None else None
    predicted = prior['d'] + (prior['v_abs'] - ego_speed) * age if prior is not None else None
    associations = [x for x in measured if self.reliable(x) and prior is not None and 0 < age <= self.horizon
      and abs(x['d'] - predicted) < max(1., 2 * x['std']) and abs(x['vr'] - (prior['v_abs'] - ego_speed)) < 2.
      and abs(x['y'] - prior['y']) < .4]
    closer = measured and ((prior is None and not self.unknown)
      or (prior is not None and measured[0]['d'] < predicted - .5)
      or (self.unknown_bound is not None and measured[0]['d'] < self.unknown_bound - .5))
    chosen = measured[0] if closer else min(associations, key=lambda x: abs(x['d'] - predicted)) if associations else None
    if chosen is not None:
      continuous = bool(associations and chosen in associations)
      if not continuous:
        self.track += 1
      self.last = {**chosen, 't': t, 'v_abs': ego_speed + chosen['vr'], 'confirmed': continuous, 'track': self.track} if self.reliable(chosen) else None
      self.unknown = False
      self.unknown_bound = None
      reason = 'new_closer_lead_immediate_priority' if closer else 'index_reassociation' if chosen.get('index') != prior.get('index') else 'fast_reacquire'
      return dict(active=False, reason=reason, memory=None, unknown=False, age=0., track=self.track)
    if prior is not None:
      uncertainty = prior['std'] + 2. * abs(age) + age * age
      if path_ok and prior['confirmed'] and 0 < age <= self.horizon and predicted > 0 and uncertainty < 1.5:
        self.unknown = True
        return dict(active=True, reason='short_dropout', age=age, uncertainty=uncertainty, track=prior['track'],
          unknown=True, memory={**prior, 'd': max(.1, predicted - uncertainty), 'vr': prior['v_abs'] - ego_speed})
      self.last = None
      self.unknown = True
      self.unknown_bound = predicted
      return dict(active=False, reason='expired_or_geometry_uncertain', age=age, uncertainty=uncertainty,
                  memory=None, unknown=True, track=self.track)
    # An unrelated farther detection cannot silently establish that the missing closer object left.
    if measured and not self.unknown:
      candidate = measured[0]
      if self.reliable(candidate):
        self.track += 1
        self.last = {**candidate, 't': t, 'v_abs': ego_speed + candidate['vr'], 'confirmed': False, 'track': self.track}
    return dict(active=False, reason='UNKNOWN_AWAIT_REACQUIRE' if self.unknown else 'PERCEPTION_LIMITATION_NO_RELIABLE_PRIOR',
                memory=None, unknown=self.unknown, age=None, track=self.track)
