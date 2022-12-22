"""
Compare OSM stops to NVBW or DELFI provided stops.
"""
import argparse
import geojson

import sys
import spatialite
import sqlite3
import traceback

from osm_stop_matcher.StatisticsUpdater import StatisticsUpdater
from osm_stop_matcher.MatchPicker import MatchPicker
from osm_stop_matcher.GtfsImporter import GtfsStopsImporter
from osm_stop_matcher.NvbwStopsImporter import NvbwStopsImporter
from osm_stop_matcher.DelfiStopsImporter import DelfiStopsImporter
from osm_stop_matcher.StopMatcher import StopMatcher
from osm_stop_matcher.MatchResultValidator import MatchResultValidator
from osm_stop_matcher.OsmStopsImporter import OsmStopsImporter
        
import logging

# TODO
# introduce some more deterministics choosing ambigous candidates as winning match
# label matches for which an equally rated candidate exists as ambiguous
# label current ambiguous match as matched_parent_stop_only
# pre/succ currently only works for (bus) platforms...
def main(osmfile, db_file, stops_file, gtfs_file, stopsprovider, logfile):
    logging.basicConfig(filename=logfile, filemode='w', level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    logger = logging.getLogger('compare_stops')
    db = spatialite.connect(db_file)
    db.execute("PRAGMA case_sensitive_like=ON")
    db.row_factory = sqlite3.Row
    logger.info("Starting compare_stops...")

    if gtfs_file:
        logger.info("Start importing gtfs " + gtfs_file)
        importer = GtfsStopsImporter(db)
        importer.import_gtfs(gtfs_file)
        # TODO make config dependent
        importer.patch_gtfs()
        logger.info("Imported gtfs")
        if stopsprovider == 'GTFS':
            importer.load_haltestellen_unified()

    if stops_file:
        if stopsprovider == 'NVBW':
            NvbwStopsImporter(db).import_stops(stops_file)
        elif stopsprovider == 'DELFI': 
            DelfiStopsImporter(db).import_stops(stops_file)
        else:
            logger.error("No importer for stopsprovider %s", stopsprovider)
            return 1
        logger.info("Imported %s stops", stopsprovider)
    
    if osmfile:
        OsmStopsImporter(db, osm_file = osmfile)
        logger.info("Imported osm file")

    if gtfs_file:
        importer.update_name_steig()
        logger.info("Updated quai names")
        importer.update_mode()
        logger.info("Updated mode")
        
    importer.update_platform_code()
    logger.info("Updated platform codes")
    
    StopMatcher(db).match_stops()
    logger.info("Matched and exported candidates")
    MatchPicker(db).pick_matches()
    MatchResultValidator(db).check_assertions()
    StatisticsUpdater(db).update_match_statistics()
    
    db.close()

    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', dest='osmfile', required=False, help='OpenStreetMap pbf file')
    parser.add_argument('-s', dest='stopsfile', required=False, help='Stops file')
    parser.add_argument('-g', dest='gtfs_file', required=False, help='GTFS file')
    parser.add_argument('-p', dest='stopsprovider', required=False, help='Stops provider', default='NVBW')
    parser.add_argument('-d', dest='db_file', required=False, help='sqlite DB out file', default='out/stops.db')
    parser.add_argument('-l', dest='log_file', required=False, help='log file', default='out/matching.log')
    
    args = parser.parse_args()
    print("Launching compare_stops. Progress is logged to " + args.log_file)
    exit(main(args.osmfile, args.db_file, args.stopsfile, args.gtfs_file, args.stopsprovider, args.log_file))
