from __future__ import annotations

from math import asin, cos, radians, sin, sqrt


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius_km * c


def format_distance(km: float | None) -> str | None:
    if km is None:
        return None
    if km < 1:
        return f"약 {int(km * 1000)}m"
    return f"약 {km:.1f}km"
