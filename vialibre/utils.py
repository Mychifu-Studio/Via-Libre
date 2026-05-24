from math import exp


def _smoothing_factor(dt, smooth_time):
    if smooth_time <= 0:
        return 1.0
    return 1 - exp(-dt / smooth_time)


def shortest_angle_lerp(current, target, dt, smooth_time):
    delta = (target - current + 180) % 360 - 180
    return current + delta * _smoothing_factor(dt, smooth_time)


def pow_lerp(current, target, dt, smooth_time):
    return current + (target - current) * _smoothing_factor(dt, smooth_time)


def powLerp(current, target, dt, smoothTime):
    return pow_lerp(current, target, dt, smoothTime)
