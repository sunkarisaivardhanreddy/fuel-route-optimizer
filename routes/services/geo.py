from functools import lru_cache
import requests
from django.conf import settings


class GeocodingError(Exception):
    pass


@lru_cache(maxsize=256)
def geocode_place(place: str) -> dict:
    """Geocode a user-supplied US place/address. Results are process-cached."""
    url = f"{settings.GEOCODER_BASE_URL}/search"
    params = {
        "q": f"{place}, USA",
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "us",
    }
    headers = {"User-Agent": settings.GEOCODER_USER_AGENT}
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=settings.GEOCODER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise GeocodingError("Unable to contact the geocoding service.") from exc

    if not data:
        raise GeocodingError(f"Could not geocode location: {place}")

    return {
        "query": place,
        "display_name": data[0].get("display_name", place),
        "lat": float(data[0]["lat"]),
        "lng": float(data[0]["lon"]),
    }
