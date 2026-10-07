Place the supplied assessment CSV here as:

    data/fuel-prices.csv

Then run:

    python manage.py migrate
    python manage.py import_fuel_prices data/fuel-prices.csv --geocode

The repository ZIP generated for this assessment intentionally does not commit the SQLite
database or geocoder output. This keeps the Git repository reproducible and avoids checking
generated third-party geocoding data into source control.
