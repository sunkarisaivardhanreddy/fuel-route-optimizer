from django.urls import path
from .views import HealthView, RouteOptimizeView, MapView

urlpatterns = [
    path("", MapView.as_view(), name="home"),
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/routes/optimize/", RouteOptimizeView.as_view(), name="route-optimize"),
]
