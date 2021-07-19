# GTFS/NVBW OSM Stop Comparison
This project provides some scripts to compare officially provided stops from Nahverkerkehrsgesellschaft Baden-Württemberg (NVBW) or DELIF e.V. with stops extracted from OpenStreetMap.

Note: Theses scripts currently rely on the specific file format of the NVBW or zHV Haltestellen file but might one day be generalized to a further input sources, e.g. GTFS-feeds.

## Prerequisites

To compare transit stops with osm data, you need
* an OSM pbf file covering the transit area, e.g.
  http://download.geofabrik.de/europe/germany/baden-wuerttemberg-latest.osm.pbf
* a stops file, e.g. curl --output zhv.zip https://de.data.public-transport.earth/zhv.zip
* a gtfs file e.g. curl --output gtfs-germany.zip https://de.data.public-transport.earth/gtfs-germany.zip



## How to run
```
> pip install -r requirements.txt
> python3 compare_stops.py  -o <path to baden-wuerttemberg-latest.osm.pbf> -s <nvbw stopsfile>
```

### Compare DELFI eV stops to OSM
```
> pip install -r requirements.txt
> python3 compare_stops.py  -o <path to germany-latest.osm.pbf> -s <zVV stopsfile> -p DELFI
```


This script will create a spatialite database, import the official stops and the osm stops, calculate probable match candidates and finally pick the most probable matches.
