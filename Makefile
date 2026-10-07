install:
	pip install -r requirements.txt -r requirements-dev.txt

migrate:
	python manage.py migrate

import-data:
	python manage.py import_fuel_prices data/fuel-prices.csv --geocode

run:
	python manage.py runserver

test:
	pytest

docker-up:
	docker compose up --build
