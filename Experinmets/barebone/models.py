from dataclasses import dataclass


@dataclass
class Storm:
    lat: float
    lon: float
    intensity: float
    duration: float
    end_time: float


@dataclass
class Flash:
    lat: float
    lon: float
    time: float


@dataclass
class Outpost:
    lat: float
    lon: float
