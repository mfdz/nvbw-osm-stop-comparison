# Test Trial on Debian Bullseye

This trial is valid on GNU/Debian systems compatible to this version
```
cat /etc/debian_version 
11.7
```

Install dependencies
```
sudo apt update
sudo apt install gdal-bin libsqlite3-mod-spatialite libspatialindex-dev --no-install-recommends
```

Prepare sources.
```
mkdir out
mkdir data
cd data
mv ~/Downloads/zhv.zip .
mv ~/Downloads/gtfs-germany.zip .
mv ~/Downloads/germany-latest.osm.pbf .
unzip zhv.zip 
mv zHV_aktuell_csv.2023-06-05.csv zhv.csv
cd ..
```

Enable virtual Python environment
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Call `nvbw-osm-stop-comparison`
```
python3 compare_stops.py -o data/germany-latest.osm.pbf -g data/gtfs-germany.zip -s data/zhv.csv -p DELFI -d out/stops.db
```

Disable virtual Python environemnt
```
deactivate
```