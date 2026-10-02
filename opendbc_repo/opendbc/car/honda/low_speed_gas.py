"""Narrow Honda CR-V 5G Bosch gas adjustment for low-speed deceleration."""


def limit_crv5g_bosch_gas(gas: float, accel: float, v_ego: float) -> float:
  # Bosch maps -0.2 < accel < 0 to positive gas without a brake request.
  # Fade it out near a stop when the request is meaningfully negative.
  # Both tapers meet the stock lookup continuously at 0 m/s² and 2 m/s.
  if accel >= 0.0 or v_ego >= 2.0:
    return gas

  speed_weight = min(1.0, max(0.0, (2.0 - v_ego) / 0.5))
  decel_weight = min(1.0, max(0.0, -accel / 0.1))
  return gas * (1.0 - speed_weight * decel_weight)
