import argparse
import csv
import datetime
from osm_stop_matcher.util import xstr, drop_table_if_exists
import sqlite3
import spatialite
import zipfile
import io
import logging
from contextlib import closing

logger = logging.getLogger('GtfsStopsImporter')

class GtfsStopsImporter():
    def __init__(self, connection):
        self.db = connection
        
    def import_routes(self, routes_file):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "gtfs_routes")
        cur.execute("CREATE TABLE gtfs_routes (route_id PRIMARY KEY,route_type,route_short_name);")

        reader = csv.DictReader(io.TextIOWrapper(routes_file, 'utf-8'))
        to_db = [(i['route_id'], i['route_type'], i['route_short_name']) for i in reader]

        cur.executemany("INSERT INTO gtfs_routes (route_id,route_type,route_short_name) VALUES (?, ?, ?);", to_db)
        self.db.commit()

    def import_trips(self, trips_file):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "gtfs_trips")
        cur.execute("CREATE TABLE gtfs_trips (trip_id PRIMARY KEY, route_id);")

        reader = csv.DictReader(io.TextIOWrapper(trips_file, 'utf-8'))
        to_db = [(i['trip_id'], i['route_id']) for i in reader]

        cur.executemany("INSERT INTO gtfs_trips (trip_id,route_id) VALUES (?, ?);", to_db)
        self.db.commit()

    def import_stops(self, stops_file):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "gtfs_stops")
        cur.execute("CREATE TABLE gtfs_stops (stop_id PRIMARY KEY,stop_name,stop_lat,stop_lon,location_type,parent_station,platform_code);")

        reader = csv.DictReader(io.TextIOWrapper(stops_file, 'utf-8'))
        to_db = [(i['stop_id'], i['stop_name'], i['stop_lat']
            , i['stop_lon'], i['location_type'], i['parent_station'],
            i['platform_code']) for i in reader]

        cur.executemany("INSERT INTO gtfs_stops (stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station,platform_code) VALUES (?, ?, ?, ?, ?, ?, ?);", to_db)
        self.db.commit()

    def load_haltestellen_unified(self):
        '''
            Initializes haltestellen_unified from GTFS data.
            Note: currently hard coded for baden-württemberg
        '''
        drop_table_if_exists(self.db, "haltestellen_unified")
        cur = self.db.cursor()
        cur.execute("""CREATE TABLE haltestellen_unified AS
            SElECT '' Landkreis, '' Gemeinde, '' Ortsteil, substr(stop_name, instr(stop_name, ' ')+1) Haltestelle, stop_name Haltestelle_lang, '' HalteBeschreibung, stop_id globaleID, '' HalteTyp, NULL gueltigAb, NULL gueltigBis, cast(stop_lat as real) lat, cast(stop_lon as real) lon, 
             CASE WHEN (LENGTH(stop_id)-LENGTH(REPLACE(stop_id, ':','')))=4 THEN 'Steig' ELSE 'Halt' END Art , 
             platform_code Name_Steig, 
              NULL mode, NULL parent, NULL match_state, NULL linien, platform_code FROM gtfs_stops
              where (location_type="0" or location_type="");
            """)

        # Patches for NVBW GTFS
        cur.execute("UPDATE haltestellen_unified set Ortsteil = SUBSTR(Haltestelle_lang, 0, instr(Haltestelle_lang, ' '))")
        
        cur.execute("CREATE INDEX id_idx ON haltestellen_unified(globaleID)")
        cur.execute("SELECT InitSpatialMetaData()")
        cur.execute("SELECT AddGeometryColumn('haltestellen_unified', 'the_geom', 4326, 'POINT','XY')")
        cur.execute("UPDATE haltestellen_unified SET the_geom = MakePoint(lon,lat, 4326) WHERE lon is NOT NULL")
        self.db.commit()
        logger.info("Loaded haltestellen_unified from GTFS")

    def import_stop_times(self, stop_times_file):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "gtfs_stop_times")
        cur.execute("CREATE TABLE gtfs_stop_times (trip_id,stop_id,stop_sequence);")
        cur.execute("CREATE UNIQUE INDEX gst ON gtfs_stop_times(trip_id,stop_id,stop_sequence);")

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
            with gtfs.open('stops.txt', 'r') as stops_file:
                self.import_stops(stops_file)
            with gtfs.open('stop_times.txt', 'r') as stop_times_file:
                self.import_stop_times(stop_times_file)

    def patch_gtfs(self):
        cur = self.db.cursor()
        # stop_names contain platform
        cur.execute("UPDATE gtfs_stops set stop_name = SUBSTR(stop_name, 0, instr(stop_name, ' '||platform_code)) WHERE platform_code != '' AND platform_code IS NOT NULL AND stop_name like '% '||platform_code")
        # Sometimes abbrevation have no space after dot
        cur.execute("UPDATE gtfs_stops set stop_name = REPLACE(stop_name, '.', '. ') WHERE stop_name like '%.%'")
        cur.execute("UPDATE gtfs_stops set stop_name = REPLACE(stop_name, '. -', '.-') WHERE stop_name like '%. -%'")
        # sometimes comma separate city and stop without further whitespace, so we remove them completely 
        cur.execute("UPDATE gtfs_stops set stop_name = REPLACE(stop_name, ',', ' ')")
        cur.execute("UPDATE gtfs_stops set stop_name = REPLACE(stop_name, '  ', ' ') WHERE stop_name like '%  %'")
        cur.execute("UPDATE gtfs_stops set stop_name = TRIM(stop_name) WHERE stop_name like '% '")
        # platform_code contains quai name but shouldn't
        cur.execute("UPDATE gtfs_stops set platform_code = REPLACE(REPLACE(REPLACE(REPLACE(platform_code, 'Steig ', ''), 'Pos ', ''), 'Gleis ', ''), 'BStg ','')")
        self.db.commit()

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
        drop_table_if_exists(self.db, "tmp_stop_modes")
        # when one route_short_name has multiple different modes, use higher valued one (train), since this is usually due to SEV (e.g. RE3 with route_type 3)
        # when still multiple modes at one stop, leave mode as NULL
        cur.execute("""CREATE table tmp_stop_modes AS
            SELECT stop_id, mode
            FROM (
                SELECT stop_id, MAX(mode) AS mode, route_short_name
                FROM (
                    SELECT st.stop_id, r.route_short_name,
                    CASE WHEN r.route_type in ('0', '1', '400','900') THEN 'light_rail' 
                     WHEN r.route_type in ('2', '100', '101', '102','103','106','109') THEN 'train' 
                     WHEN r.route_type in ('3', '700') THEN 'bus'
                     WHEN r.route_type in ('4','1000') THEN 'ferry'
                     WHEN r.route_type in ('5') THEN 'funicular'
                        ELSE NULL END AS mode
                    FROM gtfs_stop_times st
                     JOIN gtfs_trips t ON t.trip_id=st.trip_id
                     JOIN gtfs_routes r ON r.route_id=t.route_id
                    WHERE r.route_short_name NOT LIKE 'SEV%'
                    GROUP BY st.stop_id, r.route_type, r.route_short_name
                ) AS modes_by_route
                GROUP BY stop_id, route_short_name
            ) AS modes_without_sev
            GROUP BY stop_id
            HAVING COUNT(DISTINCT mode) = 1
            """)
        cur.execute("CREATE INDEX tst on tmp_stop_modes(stop_id)")
        query = """UPDATE haltestellen_unified SET mode=
        (SELECT mode
            FROM tmp_stop_modes st
                     WHERE st.stop_id = haltestellen_unified.globaleID)"""
        cur.execute(query)
        drop_table_if_exists(self.db, "tmp_stop_modes")
        self.db.commit()

    def update_linien(self):
        cur = self.db.cursor()
        drop_table_if_exists(self.db, "tmp_stop_routes")
        cur.execute("""CREATE TABLE tmp_stop_routes AS
            SELECT stop_id, group_concat(route_short_name) route_short_names FROM (
            SELECT st.stop_id, r1.route_short_name
            FROM gtfs_stop_times st
             JOIN gtfs_trips t ON t.trip_id=st.trip_id
             JOIN gtfs_routes r1 ON r1.route_id=t.route_id
             JOIN gtfs_stops s ON s.stop_id=st.stop_id
             WHERE r1.route_short_name != ''
             GROUP BY st.stop_id, r1.route_short_name)
             GROUP BY stop_id""")

        cur.execute("CREATE INDEX stop_routes_idx on tmp_stop_routes(stop_id)")

        query = """UPDATE haltestellen_unified SET linien=
                (SELECT route_short_names FROM tmp_stop_routes sr WHERE sr.stop_id=globaleID)"""
        cur.execute(query)
        drop_table_if_exists(self.db, "tmp_stop_routes")
        self.db.commit()

    def update_platform_code(self):
        cur = self.db.cursor()

        query = """UPDATE haltestellen_unified SET platform_code =
                (SELECT platform_code FROM gtfs_stops s WHERE s.stop_id=globaleID)"""
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