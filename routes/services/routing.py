from functools import lru_cache
import requests
from django.conf import settings


class RoutingError(Exception):
    pass


@lru_cache(maxsize=128)
def route(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> dict:
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/driving/"
        f"{start_lng},{start_lat};{end_lng},{end_lat}"
    )
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
        "alternatives": "false",
    }
    try:
        response = requests.get(url, params=params, timeout=settings.OSRM_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RoutingError("Unable to contact the routing service.") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError("No drivable route was found between the supplied locations.")

    selected = data["routes"][0]
    return {
        "distance_miles": selected["distance"] / 1609.344,
        "duration_seconds": selected["duration"],
        "geometry": selected["geometry"],
    }
