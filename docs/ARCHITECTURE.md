# Architecture

```text
                    ┌────────────────────┐
                    │  POST /optimize/   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │   DRF serializer   │
                    └─────────┬──────────┘
                              │
             ┌────────────────▼────────────────┐
             │          planner.py             │
             └───────┬─────────────────┬──────┘
                     │                 │
              geocode start/end       OSRM
                     │             one route call
                     │                 │
                     └────────┬────────┘
                              ▼
                       Route GeoJSON
                              │
                              ▼
                 Local station candidates
                              │
                              ▼
                    Fuel optimization
                              │
                              ▼
                       JSON response
```

## Runtime call budget

The route request performs:

1. Start geocoding — cached.
2. Finish geocoding — cached.
3. One OSRM route request — cached.
4. Zero station routing calls.

The station dataset is local SQLite data. Station coordinates are populated once by the setup command.
