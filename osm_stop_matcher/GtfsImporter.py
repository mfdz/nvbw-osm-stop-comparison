import argparse
import csv
import datetime
from osm_stop_matcher.util import xstr, drop_table_if_exists
import sqlite3
import spatialite
import zipfile
import io
from contextlib import closing

class GtfsStopsImporter():
    def __init__(self, connection):
        self.db = connection
        
    def import_routes(self, routes_file):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "gtfs_routes")
        cur.execute("CREATE TABLE gtfs_routes (route_id,route_type);")

        reader = csv.DictReader(io.TextIOWrapper(routes_file, 'utf-8'))
        to_db = [(i['route_id'], i['route_type']) for i in reader]

        cur.executemany("INSERT INTO gtfs_routes (route_id,route_type) VALUES (?, ?);", to_db)
        self.db.commit()

    def import_trips(self, trips_file):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "gtfs_trips")
        cur.execute("CREATE TABLE gtfs_trips (trip_id, route_id);")

        reader = csv.DictReader(io.TextIOWrapper(trips_file, 'utf-8'))
        to_db = [(i['trip_id'], i['route_id']) for i in reader]

        cur.executemany("INSERT INTO gtfs_trips (trip_id,route_id) VALUES (?, ?);", to_db)
        self.db.commit()

    def import_stops(self, stops_file):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "gtfs_stops")
        cur.execute("CREATE TABLE gtfs_stops (stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station);")

        reader = csv.DictReader(io.TextIOWrapper(stops_file, 'utf-8'))
        to_db = [(i['stop_id'], i['stop_name'], i['stop_lat']
            , i['stop_lon'], i['location_type'], i['parent_station']) for i in reader]

        cur.executemany("INSERT INTO gtfs_stops (stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station) VALUES (?, ?, ?, ?, ?, ?);", to_db)
        self.db.commit()
        
    def import_stop_times(self, stop_times_file):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "gtfs_stop_times")
        cur.execute("CREATE TABLE gtfs_stop_times (trip_id,stop_id,stop_sequence);")

        reader = csv.DictReader(io.TextIOWrapper(stop_times_file, 'utf-8'))
        to_db = [(i['trip_id'], i['stop_id'], i['stop_sequence']) for i in reader]

        cur.executemany("INSERT INTO gtfs_stop_times (trip_id,stop_id,stop_sequence) VALUES (?, ?, ?);", to_db)
        self.db.commit()
        
    def import_gtfs(self, gtfs_file):
        with zipfile.ZipFile(gtfs_file) as gtfs:
            with gtfs.open('routes.txt', 'r') as routes_file:
                self.import_routes(routes_file)
            with gtfs.open('trips.txt', 'r') as trips_file:
                self.import_trips(trips_file)
            #with gtfs.open('stops.txt', 'r') as stops_file:
            #self.import_stops(stops_file)
            #with gtfs.open('stop_times.txt', 'r') as stop_times_file:
            #self.import_stop_times(stop_times_file)

    def update_name_steig(self):
        cur = self.db.cursor()
        query = """SELECT GROUP_CONCAT(stop_name,'/') ri, stop_id FROM (
            SELECT DISTINCT st_c.stop_id, g_n.stop_name
            FROM gtfs_stop_times st_c
            JOIN gtfs_stop_times st_n ON st_c.stop_sequence+0 = st_n.stop_sequence-1 AND st_c.trip_id=st_n.trip_id
            JOIN gtfs_stops g_n ON g_n.stop_id = st_n.stop_id)
            GROUP BY stop_id
            """
        cur.execute(query)

        while True:
            stops = cur.fetchmany(200)
            if not stops:
                break;
            with closing(self.db.cursor()) as ucur:
                ucur.executemany("UPDATE haltestellen_unified SET Name_Steig = 'Ri '||? WHERE globaleID=?", stops)
        self.db.commit()

    def update_mode(self):
        cur = self.db.cursor()
        query = """UPDATE haltestellen_unified SET mode=
        (SELECT CASE WHEN r.route_type='3' THEN 'bus' WHEN r.route_type='2' THEN 'train' 
                     WHEN r.route_type='0' OR r.route_type='1' THEN 'light_rail' ELSE NULL END FROM gtfs_routes r 
                     JOIN gtfs_trips t ON r.route_id=t.route_id
                     JOIN (SELECT stop_id, min(trip_id) trip_id FROM gtfs_stop_times GROUP BY stop_id) st ON t.trip_id=st.trip_id
                     WHERE st.stop_id = haltestellen_unified.globaleID)"""
        cur.execute(query)

        self.db.commit()  
        
def main(gtfs_file, sqlitedb):
    db = spatialite.connect(sqlitedb)
    db.execute("PRAGMA case_sensitive_like=ON")
    importer = GtfsStopsImporter(db)
    importer.import_gtfs(gtfs_file)
    importer.update_name_steig()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', dest='gtfsfile', required=False, help='Gtfs file')
    args = parser.parse_args()

    exit(main(args.gtfsfile, "stops.db"))