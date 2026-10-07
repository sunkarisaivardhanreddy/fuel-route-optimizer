from django.conf import settings
from ..models import FuelStation
from .geo import geocode_place, GeocodingError
from .routing import route, RoutingError
from .optimizer import find_candidates, optimize_fuel, OptimizationError


class PlannerError(Exception):
    pass


def plan_route(start_text, finish_text, initial_fuel_gallons=None):
    try:
        start = geocode_place(start_text)
        finish = geocode_place(finish_text)
        route_data = route(start["lat"], start["lng"], finish["lat"], finish["lng"])
    except (GeocodingError, RoutingError) as exc:
        raise PlannerError(str(exc)) from exc

    initial_fuel = (
        settings.INITIAL_FUEL_GALLONS
        if initial_fuel_gallons is None
        else initial_fuel_gallons
    )
    capacity = settings.MAX_RANGE_MILES / settings.FUEL_MPG
    if initial_fuel > capacity:
        raise PlannerError(
            f"initial_fuel_gallons cannot exceed {capacity:.1f} gallons "
            f"for a {settings.MAX_RANGE_MILES:.0f}-mile range at {settings.FUEL_MPG:g} MPG."
        )

    # SQLite holds only stations with successful geocoding. If none are ready,
    # give the developer an actionable setup message.
    stations = list(
        FuelStation.objects.filter(latitude__isnull=False, longitude__isnull=False)
        .only(
            "opis_id", "name", "address", "city", "state",
            "retail_price", "latitude", "longitude"
        )
    )
    if not stations:
        raise PlannerError(
            "No geocoded fuel stations are loaded. Run: "
            "python manage.py import_fuel_prices data/fuel-prices.csv --geocode"
        )

    candidates = find_candidates(
        stations,
        route_data["geometry"],
        settings.STATION_CORRIDOR_MILES,
    )
    if not candidates:
        raise PlannerError(
            "No fuel stations were found within the configured route corridor. "
            "Increase STATION_CORRIDOR_MILES and retry."
        )

    try:
        optimized = optimize_fuel(
            route_data["distance_miles"],
            candidates,
            settings.FUEL_MPG,
            settings.MAX_RANGE_MILES,
            initial_fuel,
        )
    except OptimizationError as exc:
        raise PlannerError(str(exc)) from exc

    stop_payload = []
    for stop in optimized["stops"]:
        s = stop["station"]
        stop_payload.append({
            "station_id": s.opis_id,
            "name": s.name,
            "address": s.address,
            "city": s.city,
            "state": s.state,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "price_per_gallon": stop["price_per_gallon"],
            "route_miles": stop["route_miles"],
            "distance_from_route_miles": stop["corridor_miles"],
            "gallons_purchased": stop["gallons_purchased"],
            "cost": stop["cost"],
            "fuel_after_stop_gallons": stop["fuel_after_stop_gallons"],
        })

    return {
        "start": start,
        "finish": finish,
        "route": {
            "distance_miles": round(route_data["distance_miles"], 2),
            "duration_minutes": round(route_data["duration_seconds"] / 60, 1),
            "geometry": route_data["geometry"],
        },
        "vehicle": {
            "mpg": settings.FUEL_MPG,
            "max_range_miles": settings.MAX_RANGE_MILES,
            "tank_capacity_gallons": capacity,
            "initial_fuel_gallons": initial_fuel,
        },
        "fuel": {
            "gallons_used": optimized["gallons_used"],
            "total_money_spent": optimized["total_cost"],
            "ending_fuel_gallons": optimized["ending_fuel_gallons"],
        },
        "fuel_stops": stop_payload,
        "optimization": {
            "candidate_stations_considered": len(candidates),
            "station_corridor_miles": settings.STATION_CORRIDOR_MILES,
            "routing_api_calls": 1,
        },
        "attribution": {
            "routing": "OSRM / OpenStreetMap",
            "geocoding": "Nominatim / OpenStreetMap",
            "fuel_prices": "Provided assessment CSV",
        },
    }
