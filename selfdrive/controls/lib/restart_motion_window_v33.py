"""Bounded noisy-distance motion evidence; does not replace common safety gates."""
from collections import deque
import math


class RestartMotionWindow:
  def __init__(self):
    self.samples = deque()

  def clear(self):
    self.samples.clear()

  def update(self, t, lead, continuous):
    if not continuous or lead is None or not .15 < lead['vr'] < 4.:
      self.clear()
      return False
    if self.samples and not 0 < t - self.samples[-1][0] <= .075:
      self.clear()
    self.samples.append((t, lead['d']))
    while self.samples and t - self.samples[0][0] > .55:
      self.samples.popleft()
    if len(self.samples) < 9 or t - self.samples[0][0] < .4:
      return False
    n = len(self.samples)
    mt = sum(a for a, _ in self.samples) / n
    md = sum(b for _, b in self.samples) / n
    variance_t = sum((a - mt)**2 for a, _ in self.samples)
    slope = sum((a - mt)*(b - md) for a, b in self.samples) / variance_t
    residual = math.sqrt(sum((b - md - slope*(a - mt))**2 for a, b in self.samples) / n)
    return .15 < slope < 4. and residual <= .15
