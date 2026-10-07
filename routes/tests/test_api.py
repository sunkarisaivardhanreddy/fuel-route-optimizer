import pytest
from rest_framework.test import APIClient
from routes.models import FuelStation


@pytest.mark.django_db
def test_health():
    client = APIClient()
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.data["status"] == "ok"


@pytest.mark.django_db
def test_validation():
    client = APIClient()
    response = client.post(
        "/api/v1/routes/optimize/",
        {"start": "New York, NY"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_health_reports_station_counts():
    FuelStation.objects.create(
        opis_id=1, name="Test", city="Chicago", state="IL",
        retail_price=3.2, latitude=41.8, longitude=-87.6
    )
    response = APIClient().get("/health/")
    assert response.data["fuel_stations"]["total"] == 1
    assert response.data["fuel_stations"]["geocoded"] == 1
