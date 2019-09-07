# NVBW OSM Stop Comparison
This project provides some scripts to compare officially provided stops from Nahverkerkehrsgesellschaft Baden-Württemberg (NVBW) with stops extracted from OpenStreetMap.

Note: Theses scripts currently rely on the specific file format of the NVBW Haltestellen file but might one day be generalized to a further input sources, e.g. GTFS-feeds.

## How to run
```
> pip install -r requirements.txt
> python3 compare_stops.py  <path to baden-wuerttemberg-latest.osm.pbf> <nvbw stopsfile>
```

This script will create a spatialite database, import the nvbw and osm stops, calculate probable match candidates and finally pick the most probable matches.


