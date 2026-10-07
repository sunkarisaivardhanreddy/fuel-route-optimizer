import math
from typing import Iterable


EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_MILES * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cumulative_distances(coords):
    result = [0.0]
    for a, b in zip(coords, coords[1:]):
        result.append(result[-1] + haversine_miles(a[1], a[0], b[1], b[0]))
    return result


def nearest_route_position(lat, lon, coords, cumulative, stride=5):
    """Fast coarse-to-fine nearest point search.

    Coordinates are [lon, lat]. We first search every `stride`th point, then
    inspect a small neighborhood. This avoids O(stations * route_points)
    work while retaining route-order accuracy for fuel-stop selection.
    """
    if not coords:
        return None

    sample_indices = range(0, len(coords), stride)
    best_idx = min(
        sample_indices,
        key=lambda i: haversine_miles(lat, lon, coords[i][1], coords[i][0]),
    )
    lo = max(0, best_idx - stride)
    hi = min(len(coords), best_idx + stride + 1)
    best_idx = min(
        range(lo, hi),
        key=lambda i: haversine_miles(lat, lon, coords[i][1], coords[i][0]),
    )
    distance = haversine_miles(lat, lon, coords[best_idx][1], coords[best_idx][0])
    return cumulative[best_idx], distance


def normalize_longitude_delta(delta):
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360
    return delta
