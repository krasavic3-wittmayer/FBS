speed_of_sound = 343  # Speed of sound in meters per second

def delay(distance):
    delay = (distance**2 + 2000**2)**0.5 / speed_of_sound
    return delay