from dataclasses import dataclass


@dataclass
class Flash:
    lat: float
    lon: float
    time: float  # seconds since Unix epoch
