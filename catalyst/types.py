from typing import NamedTuple


class Location(NamedTuple):
    lat: float
    lon: float


def location_from_string(val: str = None) -> Location:
    if val:
        lat, lon = map(float, val.split(','))
        return Location(lat, lon)
