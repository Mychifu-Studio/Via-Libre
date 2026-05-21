from math import exp

def shortest_angle_lerp(current, target, dt, smoothTime):
    delta = (target - current + 180) % 360 - 180
    return current + delta * (1 - exp(-dt / smoothTime))

def powLerp(current, target, dt, smoothTime):
    if smoothTime <= 0:
        return target
    return current + (target - current) * (1 - exp(-dt / smoothTime))