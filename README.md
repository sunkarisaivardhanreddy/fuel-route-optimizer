# Fuel Route Optimizer — Django Backend Assessment

A production-minded Django REST API that:

1. Accepts US start and finish locations.
2. Geocodes the two user-supplied locations.
3. Calls OSRM **once** to obtain the driving route and GeoJSON geometry.
4. Finds fuel stations close to that route using the supplied fuel-price dataset.
5. Selects cost-effective refueling stops subject to a 500-mile maximum range.
6. Assumes 10 MPG and reports gallons used and total fuel cost.
7. Includes a small Leaflet UI for a visual demonstration.

## Why this design?

The assessment specifically asks to minimize calls to the free routing API. The runtime path is designed around **one OSRM route request**. Fuel stations are not routed individually; they are positioned against the returned route geometry locally.

The supplied CSV has 8,151 stations. Because it does not contain latitude/longitude, a one-time management command uses the US Census Geocoder's batch endpoint. The Census API supports up to 10,000 addresses per batch, so the entire assessment dataset fits into one batch.

At runtime, the two user locations are geocoded with Nominatim and the route is obtained with OSRM. Geocoding responses and route responses are process-cached.

## Important assumption

The assessment specifies a maximum range of 500 miles and 10 MPG, but does not state starting fuel. This project assumes the vehicle **starts with a full 50-gallon tank** (500-mile range). You can override it per request with `initial_fuel_gallons`.

Fuel already in the vehicle is not counted as money spent. Only fuel purchased during the trip is included in `total_money_spent`.

## Stack

- Python 3.13
- Django 6.1.2
- Django REST Framework
- SQLite for zero-setup local development
- OSRM / OpenStreetMap for routing
- US Census Geocoder for one-time station geocoding
- Nominatim / OpenStreetMap for user location geocoding
- Leaflet for the included demo map
- Esri World Street Map tiles for the included demo basemap

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Configure environment

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Replace the example User-Agent contact information with your own contact details before using a public Nominatim service.

### 4. Add the supplied CSV

Copy the assessment attachment to:

```text
data/fuel-prices.csv
```

### 5. Initialize and import

```bash
python manage.py migrate
python manage.py import_fuel_prices data/fuel-prices.csv --geocode
```

The `--geocode` flag submits the stations as one Census batch. It is intentionally a setup-time operation, not part of an API request.

Check readiness:

```bash
python manage.py runserver
```

Then:

```text
GET http://127.0.0.1:8000/health/
```

A ready database should report a positive `geocoded` count.

## API

### POST `/api/v1/routes/optimize/`

Request:

```json
{
  "start": "New York, NY",
  "finish": "Chicago, IL"
}
```

Optional:

```json
{
  "start": "Dallas, TX",
  "finish": "Denver, CO",
  "initial_fuel_gallons": 50
}
```

The response contains:

- route distance and duration
- GeoJSON LineString for the route
- start/finish coordinates
- selected fuel stations
- station prices
- gallons purchased at each stop
- per-stop cost
- total gallons used
- total money spent
- number of candidate stations considered
- routing API call count
- attribution

### Example curl

```bash
curl -X POST http://127.0.0.1:8000/api/v1/routes/optimize/ \
  -H "Content-Type: application/json" \
  -d "{\"start\":\"New York, NY\",\"finish\":\"Chicago, IL\"}"
```

## Map demo

Open:

```text
http://127.0.0.1:8000/
```

The page uses Leaflet with an Esri World Street Map basemap and displays:

- the OSRM route
- start/end markers
- recommended fuel stops
- fuel price and purchase information

The API remains the primary deliverable.

## Optimization algorithm

The route geometry is converted into cumulative route-mile positions. Stations are projected to the nearest route point using a coarse-to-fine Haversine search.

A station is considered a candidate when it lies within `STATION_CORRIDOR_MILES` of the route.

For fuel selection, the implementation uses the standard fixed-route refueling greedy strategy:

- If the destination can be reached with the current fuel, stop buying.
- If a cheaper station is reachable, buy only enough to reach a cheaper station.
- Otherwise, fill the tank and select the cheapest reachable candidate.
- A station can only be selected if the vehicle can physically reach it with its current fuel.

This avoids calling the routing API for every fuel station. The route is computed once; all station selection after that is local.

## Performance

The important API-call budget is:

- 2 geocoding requests for uncached start/finish places
- 1 OSRM route request
- 0 routing calls for individual fuel stations

The expensive station work is local and runs against at most the imported dataset. Route geocoding is cached in-process, and the OSRM call is cached in-process by coordinates.

For production, the natural next step would be Redis-backed caching and PostGIS for spatial station queries.

## Tests

```bash
pytest
```

The tests cover:

- routes that need no stop
- cheaper-station selection
- impossible fuel gaps
- health endpoint
- validation
- geocoded station readiness

## Docker

```bash
docker compose up --build
```

The application will be available at:

```text
http://localhost:8000/
```

You still need to run the CSV import/geocoding step inside the container:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py import_fuel_prices data/fuel-prices.csv --geocode
```

## Postman

Import:

```text
postman/Fuel Route Optimizer.postman_collection.json
```

The collection contains health and optimize requests.

## External services / attribution

- OSRM is an open-source routing engine using OpenStreetMap data.
- Nominatim is used only for direct user-triggered location geocoding and should be used according to its public service policy.
- US Census Geocoder is used for one-time batch station geocoding.
- Fuel prices are from the assessment-provided CSV.

For a public deployment, use a dedicated/hosted geocoder and routing provider or operate your own services rather than depending on public infrastructure.

## Submission checklist

- [x] Django backend
- [x] REST API
- [x] 500-mile vehicle range
- [x] 10 MPG calculation
- [x] Multiple fuel stops
- [x] Cost-aware optimization
- [x] Route GeoJSON
- [x] One OSRM route request per uncached route
- [x] Fuel-price CSV importer
- [x] Batch station geocoding
- [x] Tests
- [x] Docker setup
- [x] Postman collection
- [x] Demo map
- [x] Loom script
