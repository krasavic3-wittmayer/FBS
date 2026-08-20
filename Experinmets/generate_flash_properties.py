from math import cos, radians, sqrt

from calc_amp import amplitude
from calc_delay import delay
from make_real_flashes import Flash


class Outpost:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon


def distance_km(lat1, lon1, lat2, lon2):
    lat_km = (lat2 - lat1) * 111
    lon_km = (lon2 - lon1) * 111 * cos(
        radians((lat1 + lat2) / 2)
    )

    return sqrt(lat_km**2 + lon_km**2)


def generate_flash_properties(
    flash: Flash,
    outpost: Outpost,
) -> tuple[float, float]:
    """Calculate the amplitude and delay of a lightning flash as observed from an outpost."""

    distance = distance_km(
        flash.lat,
        flash.lon,
        outpost.lat,
        outpost.lon,
    ) * 1000

    flash_delay = delay(distance)
    flash_amplitude = amplitude(distance)

    return flash_amplitude, flash_delay

testpost = Outpost(0, 0)
testflash = Flash(0.1, 0.1, 0)
print(generate_flash_properties(testflash, testpost))