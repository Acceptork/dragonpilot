"""Offline-only hypothesis H1: restrict recovery to strong disagreement.

This is not a traffic-light or stop detector. No production import is added.
"""
from dataclasses import replace
from openpilot.selfdrive.controls.lib.recovery_v331 import Recovery

class StrongDisagreementRecovery(Recovery):
  ratio = .15

  def update(self, x):
    veto = x.mpc > 0 and x.e2e > self.ratio * x.mpc
    row = super().update(replace(x, stop=x.stop or veto))
    if veto and row['reason'] == 'stop_or_model_deceleration':
      row['reason'] = 'insufficient_relative_disagreement'
    row['relative_disagreement_limit'] = self.ratio
    return row

def policy(ratio):
  return type('RatioRecovery', (StrongDisagreementRecovery,), {'ratio': ratio})()
