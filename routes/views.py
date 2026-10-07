from django.http import JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import FuelStation
from .serializers import LocationInputSerializer
from .services.planner import plan_route, PlannerError


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        total = FuelStation.objects.count()
        geocoded = FuelStation.objects.filter(latitude__isnull=False, longitude__isnull=False).count()
        return Response({
            "status": "ok",
            "fuel_stations": {
                "total": total,
                "geocoded": geocoded,
                "ready": geocoded > 0,
            }
        })


class RouteOptimizeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LocationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "validation_error", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = plan_route(
                serializer.validated_data["start"],
                serializer.validated_data["finish"],
                serializer.validated_data.get("initial_fuel_gallons"),
            )
        except PlannerError as exc:
            return Response(
                {"error": "planning_error", "message": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(result, status=status.HTTP_200_OK)


class MapView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        html = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Fuel Route Optimizer</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
body{font-family:system-ui,sans-serif;margin:0;padding:20px;max-width:1100px;margin:auto}
form{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
input,button{padding:10px;font-size:15px} input{min-width:260px} button{cursor:pointer}
#map{height:620px;border-radius:10px;margin-top:12px}
#summary{white-space:pre-wrap;background:#f6f6f6;padding:12px;border-radius:8px}
#status{margin-top:8px;color:#555;font-size:14px}
</style>
</head>
<body>
<h1>Fuel Route Optimizer</h1>
<p>The API itself is <code>POST /api/v1/routes/optimize/</code>.</p>
<form id="form">
<input id="start" value="New York, NY" aria-label="Start">
<input id="finish" value="Chicago, IL" aria-label="Finish">
<button>Optimize route</button>
</form>
<div id="summary">Enter two US locations and optimize.</div>
<div id="status" aria-live="polite"></div>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map=L.map('map').setView([39.8,-98.6],4);
L.tileLayer(
 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
 {maxZoom:19, attribution:'Tiles © Esri'}
).addTo(map);
let layer=L.layerGroup().addTo(map);
document.getElementById('form').addEventListener('submit', async (e)=>{
 e.preventDefault(); layer.clearLayers();
 const start=document.getElementById('start').value;
 const finish=document.getElementById('finish').value;
 const box=document.getElementById('summary'); const status=document.getElementById('status'); box.textContent='Loading...'; status.textContent='Geocoding locations and calculating the route...';
 try {
  const r=await fetch('/api/v1/routes/optimize/',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({start,finish})
  });
  const data=await r.json();
  if(!r.ok) throw new Error(data.message||JSON.stringify(data));
  const line=L.geoJSON(data.route.geometry).addTo(layer);
  L.marker([data.start.lat,data.start.lng]).addTo(layer).bindPopup('Start').openPopup();
  L.marker([data.finish.lat,data.finish.lng]).addTo(layer).bindPopup('Finish');
  data.fuel_stops.forEach(s=>L.marker([s.latitude,s.longitude]).addTo(layer)
    .bindPopup(`${s.name}<br>$${s.price_per_gallon}/gal<br>${s.gallons_purchased} gal`));
  map.fitBounds(line.getBounds(),{padding:[20,20]});
  box.textContent=`Distance: ${data.route.distance_miles} miles\nFuel used: ${data.fuel.gallons_used} gal\nFuel cost: $${data.fuel.total_money_spent}\nStops: ${data.fuel_stops.length}\nCandidates: ${data.optimization.candidate_stations_considered}\nRouting API calls: ${data.optimization.routing_api_calls}`; status.textContent='Route optimized successfully.';
 } catch(err){ box.textContent='Error: '+err.message; status.textContent='The request could not be completed.'; }
});
</script>
</body></html>"""
        return HttpResponse(html)
