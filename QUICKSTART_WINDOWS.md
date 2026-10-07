# Windows Quick Start

Open Command Prompt in the extracted `fuel_route_optimizer` directory.

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py import_fuel_prices data\fuel-prices.csv --geocode
python manage.py check
python manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

For Postman:

`POST http://127.0.0.1:8000/api/v1/routes/optimize/`

```json
{
  "start": "New York, NY",
  "finish": "Chicago, IL"
}
```

The import command uses the U.S. Census batch geocoder for all supplied stations. The API uses Nominatim for the two user locations and one OSRM request for the driving route.
