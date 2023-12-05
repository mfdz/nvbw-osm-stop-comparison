# GTFS/NVBW OSM Stop Comparison
This project provides some scripts to compare officially provided stops from e or DELFI e.V. with stops extracted from OpenStreetMap.

Currently supported are the following stop sources:
* [stops list Nahverkehrsgesellschaft Baden-Württemberg (NVBW)](https://www.mobidata-bw.de/dataset/haltestellen-baden-wuerttemberg)
* DELFI's zentrales Haltestellenverzeichnis (zHV)
* a GTFS file (Beta, developed for bwgesamt.zip, currently code makes various assumptions regarding the content )

## Prerequisites

### Data
To compare transit stops with osm data, you need
* an OSM pbf file covering the transit area, e.g.
  http://download.geofabrik.de/europe/germany/baden-wuerttemberg-latest.osm.pbf
* a stops file, e.g. curl --output zhv.zip -L https://scraped.data.public-transport.earth/de/zhv.zip
* a gtfs file e.g. curl --output gtfs-germany.zip -L https://data.public-transport.earth/gtfs/de


These can be downloade e.g. with the provided scripts `download_delfi_and_osm_data.sh` or `download_nvbw_and_osm_data.sh`.

### sqlite and spatiallite on Mac
see e.g. https://medium.com/@carusot42/installing-and-loading-spatialite-on-macos-28bf677f0436

```sh
brew install sqlite3 
find /usr/local -path "*sqlite3" | grep -e "sqlite3$" | grep "/bin"
/usr/local/Cellar/sqlite/3.39.2/bin/sqlite3 out/stops-bw.db
```

### Python requirements 
Optionally, you might want to create a python environment to install needed libraries in an isolated environment:

```sh
> makevirtualenv nosc
```

Then, you should install the required python libraries:
```sh
> pip install -r requirements.txt
```


## How to run

The GTFS/NVBW Stops comparison supports three official stop sources for comparison against OSM:
* DELFI's stop register (zHV)
* NVBW's stop register (zHV)
* GTFS feeds

### Compare DELFI eV stops to OSM
```sh
> python3 compare_stops.py -o data/germany-latest.osm.pbf -g data/gtfs-germany.zip -s data/zhv.csv -p DELFI -d out/stops.db
```

or, to just re-run the matching without reload OSM:

```sh
> python3 compare_stops.py -g data/gtfs-germany.zip -s data/zhv.csv -p DELFI -d out/stops.db
```

or, to just re-run the matching without reloading any files, specify mode ( -m ) `match`:

```sh
> python3 compare_stops.py -m match -p DELFI -d out/stops.db
```

### Compare NVBW stops to OSM
```sh
> python3 compare_stops.py -o data/baden-wuerttemberg-latest.osm.pbf -g data/gtfs-bw.zip -s data/zhv-bw.csv -d out/stops-bw.db -p NVBW -l out/matching.nvbw.log
```

### Compare GTFS stops to OSM
The comparison option `GTFS` compares stops provide by a GTFS-Feed to OpenStreetMap.
Note, that we currently apply some very NVBW-feed specific processing to these stops, which should be configurable and extendable for other feeds.

```
> python3 compare_stops.py -o data/baden-wuerttemberg-latest.osm.pbf -g data/gtfs-bw.zip -d out/stops-bw.db -p GTFS 
```

```
> python3 compare_stops.py -o data/baden-wuerttemberg-latest.osm.pbf -g data/gtfs-bw.zip -s data/zhv-bw.csv -d out/stops-bw.db -p NVBW -d out/stops-bw.db
```

This script will create a spatialite database, import the official stops and the osm stops, calculate probable match candidates and finally pick the most probable matches.

## Docker

If you want to use this project via docker, proceed as follows:

Build the docker image via 
`docker build -t mfdz/gtfs-osm-stops-matcher .`

Run the comparison via
`docker run --rm -v $(PWD)/data:/usr/src/app/data -v $(PWD)/out:/usr/src/app/out mfdz/gtfs-osm-stops-matcher python compare_stops.py -o data/germany-latest.osm.pbf -s data/zhv.csv -g data/gtfs-germany.zip -p DELFI`

`docker run --rm -v $(PWD)/data:/usr/src/app/data -v $(PWD)/out:/usr/src/app/out mfdz/gtfs-osm-stops-matcher python compare_stops.py -g data/gtfs-germany.zip -p DELFI`

## Running tests

