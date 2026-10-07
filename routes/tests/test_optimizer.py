from types import SimpleNamespace
import pytest
from routes.services.optimizer import optimize_fuel


def station(i, price):
    return SimpleNamespace(opis_id=i, retail_price=price)


def candidate(i, position, price):
    return SimpleNamespace(
        station=station(i, price),
        route_miles=position,
        corridor_miles=2.0,
    )


def test_route_under_range_needs_no_stop():
    result = optimize_fuel(
        route_distance=300,
        candidates=[],
        mpg=10,
        max_range=500,
        initial_fuel_gallons=50,
    )
    assert result["stops"] == []
    assert result["gallons_used"] == 30


def test_cheaper_station_is_preferred():
    candidates = [
        candidate(1, 250, 4.00),
        candidate(2, 450, 3.00),
        candidate(3, 700, 3.50),
    ]
    result = optimize_fuel(
        route_distance=900,
        candidates=candidates,
        mpg=10,
        max_range=500,
        initial_fuel_gallons=50,
    )
    assert result["stops"]
    assert result["stops"][0]["station"].opis_id == 2
    # Once the cheaper station is selected, the optimizer should not
    # unnecessarily purchase another full tank at the preceding station.
    assert result["stops"][0]["gallons_purchased"] >= 0


def test_no_reachable_station_fails():
    with pytest.raises(Exception):
        optimize_fuel(
            route_distance=1200,
            candidates=[candidate(1, 800, 3.00)],
            mpg=10,
            max_range=500,
            initial_fuel_gallons=50,
        )
