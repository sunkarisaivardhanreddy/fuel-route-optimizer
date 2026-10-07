# 5-minute Loom walkthrough

## 0:00–0:30 — Intro

“Hi, this is my solution for the Backend Django Engineer assessment.

The API accepts a US start and finish location, calculates a driving route, finds cost-effective fuel stops while respecting the vehicle's 500-mile range, and returns the route geometry and total fuel cost.”

## 0:30–1:20 — Architecture

Show the repository:

- `routes/views.py` — HTTP/API layer
- `routes/services/planner.py` — orchestration
- `routes/services/routing.py` — one OSRM call
- `routes/services/optimizer.py` — local fuel optimization
- `routes/models.py` — fuel station storage
- `routes/management/commands/` — CSV import and one-time geocoding

Say:

“The key performance decision is that I don't route from the start to every fuel station. I call OSRM once to get the complete route, then project the locally stored stations onto that geometry.”

## 1:20–2:10 — Data setup

Show:

```bash
python manage.py import_fuel_prices data/fuel-prices.csv --geocode
```

Explain:

“The assessment CSV contains prices and station addresses but no coordinates. I use the US Census Geocoder's batch endpoint once during setup. The runtime API never performs 8,000 individual geocoding calls.”

Then show:

```text
GET /health/
```

## 2:10–3:30 — Postman demo

Run:

```text
POST /api/v1/routes/optimize/
```

with:

```json
{
  "start": "New York, NY",
  "finish": "Chicago, IL"
}
```

Point out:

- distance
- GeoJSON route
- fuel stops
- price per gallon
- gallons purchased
- per-stop cost
- total fuel cost

Explain:

“The optimizer assumes a full 50-gallon starting tank because the assessment gives a 500-mile maximum range and 10 MPG but doesn't specify starting fuel. I expose initial fuel as an optional request parameter.”

## 3:30–4:15 — Algorithm

Show `optimizer.py`.

Explain:

“Stations are sorted by their position along the route. At a station, if a cheaper reachable station exists, we buy only enough fuel to get there. Otherwise we fill the tank and use the cheapest reachable station. This is the standard greedy solution for fixed-route refueling with continuous fuel.”

## 4:15–4:45 — Tests

Run:

```bash
pytest
```

Mention that tests cover the optimizer's key decisions and API validation/readiness.

## 4:45–5:00 — Close

“Overall, the solution keeps the routing API usage to one call per uncached route, keeps fuel optimization local, and returns map-ready GeoJSON so a frontend can render the route and stops directly.”
