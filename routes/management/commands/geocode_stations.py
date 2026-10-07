import csv
import io
import time
import requests
from datetime import datetime, timezone
from django.core.management.base import BaseCommand, CommandError
from routes.models import FuelStation

CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    "User-Agent": "FuelRouteOptimizer/1.0 (backend assessment demo)"
}
NOMINATIM_MIN_INTERVAL = 1.05


def _submit_batch(stations):
    """Submit postal-style addresses to the Census batch geocoder."""
    out = io.StringIO()
    writer = csv.writer(out)
    for s in stations:
        writer.writerow([s.opis_id, s.address, s.city, s.state, ""])

    try:
        response = requests.post(
            CENSUS_URL,
            params={"benchmark": "4"},
            files={
                "addressFile": (
                    "stations.csv",
                    out.getvalue().encode("utf-8"),
                    "text/csv",
                )
            },
            timeout=180,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CommandError(f"Census batch geocoding failed: {exc}") from exc

    return list(csv.reader(io.StringIO(response.text)))


def _apply_census_results(rows):
    matched_ids = set()
    failed_ids = set()
    for row in rows:
        if len(row) < 7:
            continue
        try:
            opis_id = int(row[0])
        except (ValueError, TypeError):
            continue

        status = row[2].strip()
        if status != "Match":
            failed_ids.add(opis_id)
            continue

        try:
            lon = float(row[5])
            lat = float(row[6])
        except (ValueError, IndexError):
            failed_ids.add(opis_id)
            continue

        FuelStation.objects.filter(opis_id=opis_id).update(
            longitude=lon,
            latitude=lat,
            geocode_source="US Census Geocoder",
            geocoded_at=datetime.now(timezone.utc),
        )
        matched_ids.add(opis_id)

    return matched_ids, failed_ids


def _nominatim_search(query, last_request_at):
    """One deliberately rate-limited Nominatim request."""
    elapsed = time.monotonic() - last_request_at
    if elapsed < NOMINATIM_MIN_INTERVAL:
        time.sleep(NOMINATIM_MIN_INTERVAL - elapsed)

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "us",
            },
            headers=NOMINATIM_HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None, time.monotonic()

    if not data:
        return None, time.monotonic()

    try:
        return (float(data[0]["lat"]), float(data[0]["lon"])), time.monotonic()
    except (KeyError, TypeError, ValueError):
        return None, time.monotonic()


def _nominatim_fallback(stations, stdout):
    """Geocode Census misses using Nominatim, with city/state caching.

    The supplied truck-stop CSV frequently stores highway-exit descriptions
    instead of USPS street addresses. Nominatim can resolve many of those
    highway/city/state descriptions, while city/state is used as a final
    approximate fallback. Results are cached by query and requests are kept
    to one thread and just over one request/second per Nominatim policy.
    """
    cache = {}
    last_request_at = 0.0
    matched = set()
    failed = set()

    total = len(stations)
    for index, station in enumerate(stations, start=1):
        full_query = f"{station.address}, {station.city}, {station.state}, USA"
        city_query = f"{station.city}, {station.state}, USA"

        location = cache.get(full_query)
        if location is None and full_query not in cache:
            location, last_request_at = _nominatim_search(full_query, last_request_at)
            cache[full_query] = location

        # A highway-exit description may not be searchable. Fall back to the
        # city center, which is still much better than leaving the station
        # unusable and is cached when multiple stations share a city.
        if location is None:
            location = cache.get(city_query)
            if location is None and city_query not in cache:
                location, last_request_at = _nominatim_search(city_query, last_request_at)
                cache[city_query] = location

        if location is None:
            failed.add(station.opis_id)
            continue

        lat, lon = location
        FuelStation.objects.filter(opis_id=station.opis_id).update(
            longitude=lon,
            latitude=lat,
            geocode_source="Nominatim/OSM",
            geocoded_at=datetime.now(timezone.utc),
        )
        matched.add(station.opis_id)

        if index % 25 == 0 or index == total:
            stdout.write(f"Fallback geocoding progress: {index}/{total} processed.")

    return matched, failed


def geocode_all(stdout, keep_existing=False):
    qs = FuelStation.objects.all().order_by("id")
    if keep_existing:
        qs = qs.filter(latitude__isnull=True) | qs.filter(longitude__isnull=True)
    stations = list(qs)
    if not stations:
        stdout.write("No stations need geocoding.")
        return

    # Census requires a street address in its batch format. The assessment CSV
    # often contains highway-exit descriptions, so Census is used first and
    # Nominatim handles the remaining stations.
    rows = _submit_batch(stations)
    census_matched, census_failed = _apply_census_results(rows)
    stdout.write(
        f"Census pass: {len(census_matched)} matched; "
        f"{len(census_failed)} need fallback geocoding."
    )

    fallback_stations = [s for s in stations if s.opis_id in census_failed]
    nominatim_matched, nominatim_failed = _nominatim_fallback(
        fallback_stations, stdout
    ) if fallback_stations else (set(), set())

    matched_ids = census_matched | nominatim_matched
    failed_ids = nominatim_failed
    stdout.write(
        f"Geocoding complete: {len(matched_ids)} matched, "
        f"{len(failed_ids)} unmatched."
    )


class Command(BaseCommand):
    help = "Batch geocode imported fuel prices using Census, then Nominatim for truck-stop fallback addresses."

    def add_arguments(self, parser):
        parser.add_argument("--keep-existing-coordinates", action="store_true")

    def handle(self, *args, **options):
        geocode_all(self.stdout, options["keep_existing_coordinates"])
