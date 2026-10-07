from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from .geometry import cumulative_distances, nearest_route_position, haversine_miles


class OptimizationError(Exception):
    pass


@dataclass
class Candidate:
    station: object
    route_miles: float
    corridor_miles: float


def _money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def find_candidates(stations, geometry, corridor_miles):
    coords = geometry["coordinates"]
    cumulative = cumulative_distances(coords)
    candidates = []
    for station in stations:
        if station.latitude is None or station.longitude is None:
            continue
        result = nearest_route_position(
            station.latitude, station.longitude, coords, cumulative, stride=max(1, len(coords) // 200)
        )
        if result is None:
            continue
        route_miles, corridor_distance = result
        if corridor_distance <= corridor_miles:
            candidates.append(Candidate(station, route_miles, corridor_distance))
    candidates.sort(key=lambda c: (c.route_miles, float(c.station.retail_price)))
    return candidates


def optimize_fuel(route_distance, candidates, mpg, max_range, initial_fuel_gallons):
    """Greedy optimal refueling for a fixed route.

    At each stop:
      * if the destination is reachable, buy only enough to finish;
      * otherwise, if a cheaper station exists within one full tank, buy
        enough to reach the first cheaper station;
      * otherwise fill the tank and choose the cheapest reachable station.

    The vehicle begins with `initial_fuel_gallons`; default is a full tank.
    """
    if initial_fuel_gallons > max_range / mpg:
        raise OptimizationError("Initial fuel exceeds the vehicle's maximum tank capacity.")

    # Deduplicate near-identical route positions, retaining the cheapest station.
    unique = []
    for c in candidates:
        if c.route_miles <= 0.5 or c.route_miles >= route_distance - 0.5:
            continue
        if unique and abs(c.route_miles - unique[-1].route_miles) < 1.0:
            if c.station.retail_price < unique[-1].station.retail_price:
                unique[-1] = c
        else:
            unique.append(c)

    capacity = max_range / mpg
    current_pos = 0.0
    fuel = initial_fuel_gallons
    total_cost = 0.0
    stops = []
    used_ids = set()

    while route_distance - current_pos > 1e-6:
        reachable = [
            c for c in unique
            if c.route_miles > current_pos + 1e-6
            and c.route_miles - current_pos <= fuel * mpg + 1e-6
        ]
        destination_reachable = route_distance - current_pos <= fuel * mpg + 1e-6

        if destination_reachable:
            break

        if not reachable:
            raise OptimizationError(
                f"No fuel station is reachable from route mile {current_pos:.1f}. "
                f"Try increasing the station corridor or using a different route."
            )

        # We must reach a station before fuel runs out. If any reachable station
        # is cheaper than the current best, target the first cheaper station.
        # Otherwise fill up and choose the cheapest reachable station.
        current_price = float(
            stops[-1]["price_per_gallon"] if stops else min(
                [c.station.retail_price for c in reachable], default=0
            )
        )

        # Standard fixed-route refueling rule:
        # - If a cheaper station is reachable, target the first cheaper station
        #   and buy only enough to reach it.
        # - Otherwise fill the tank and target the cheapest reachable station.
        cheaper = [
            c for c in reachable
            if float(c.station.retail_price) < current_price
        ]

        if cheaper:
            target = min(cheaper, key=lambda c: c.route_miles)
            target_distance = target.route_miles - current_pos
            required_gallons = target_distance / mpg
            purchase = max(0.0, required_gallons - fuel)
        else:
            target = min(
                reachable,
                key=lambda c: (float(c.station.retail_price), c.route_miles)
            )
            target_distance = target.route_miles - current_pos
            purchase = max(0.0, capacity - fuel)

        if purchase > 0:
            price = float(target.station.retail_price)
            cost = purchase * price
            total_cost += cost
            fuel += purchase
        else:
            cost = 0.0

        # Consume fuel to target.
        fuel -= target_distance / mpg
        current_pos = target.route_miles

        station_id = target.station.opis_id
        if station_id in used_ids:
            raise OptimizationError("Optimizer selected the same station twice.")
        used_ids.add(station_id)

        stops.append({
            "station": target.station,
            "route_miles": round(current_pos, 2),
            "corridor_miles": round(target.corridor_miles, 2),
            "gallons_purchased": round(purchase, 3),
            "price_per_gallon": round(float(target.station.retail_price), 3),
            "cost": round(cost, 2),
            "fuel_after_stop_gallons": round(fuel, 3),
        })

        # Safety against pathological candidate data.
        if len(stops) > 100:
            raise OptimizationError("Too many fuel stops; candidate data may be invalid.")

    total_gallons_used = route_distance / mpg
    if fuel < -1e-6:
        raise OptimizationError("Route requires more fuel than available.")

    return {
        "stops": stops,
        "total_cost": _money(total_cost),
        "gallons_used": round(total_gallons_used, 3),
        "ending_fuel_gallons": round(fuel, 3),
    }
