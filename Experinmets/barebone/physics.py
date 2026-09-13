from math import cos, radians, sqrt

SPEED_OF_SOUND = 343.0  # m/s
MAX_DISTANCE_M = 16_000.0


def distance_km(lat1, lon1, lat2, lon2):
    lat_km = (lat2 - lat1) * 111
    lon_km = (lon2 - lon1) * 111 * cos(radians((lat1 + lat2) / 2))
    return sqrt(lat_km**2 + lon_km**2)


def delay(distance_m):
    return (distance_m**2 + 2000**2) ** 0.5 / SPEED_OF_SOUND


def amplitude(distance_m):
    return max(0.0, 1.0 - distance_m / MAX_DISTANCE_M)
