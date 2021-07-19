"""
Compare OSM stops to NVBW provided stops.
"""
import argparse
import geojson

import sys
import spatialite
import sqlite3
import traceback

from osm_stop_matcher.StatisticsUpdater import StatisticsUpdater
from osm_stop_matcher.MatchPicker import MatchPicker
from osm_stop_matcher.NvbwStopsImporter import NvbwStopsImporter
from osm_stop_matcher.StopMatcher import StopMatcher
from osm_stop_matcher.MatchResultValidator import MatchResultValidator
from osm_stop_matcher.OsmStopsImporter import OsmStopsImporter
        
import logging

# TODO
# introduce some more deterministics choosing ambigous candidates as winning match
# label matches for which an equally rated candidate exists as ambigous
# label current ambigous match as matched_parent_stop_only
# pre/succ currently only works for (bus) platforms...
def main(osmfile, stops_file):
    logging.basicConfig(filename='matching.log', filemode='w', level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    logger = logging.getLogger('compare_stops')
    db = spatialite.connect('stops.db')
    db.execute("PRAGMA case_sensitive_like=ON")
    db.row_factory = sqlite3.Row

    if stops_file:
        NvbwStopsImporter(db).import_stops(stops_file)
        logger.info("Imported %s stops", stopsprovider)
    
    if osmfile:
        OsmStopsImporter(db, osm_file = osmfile)
        print("Imported osm file")

    StopMatcher(db).match_stops()
    print("Matched and exported candidates")
    MatchPicker(db).pick_matches()
    MatchResultValidator(db).check_assertions()
    StatisticsUpdater(db).update_match_statistics()
    
    db.close()

    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', dest='osmfile', required=False, help='OpenStreetMap pbf file')
    parser.add_argument('-s', dest='stopsfile', required=False, help='Stops file')
    args = parser.parse_args()

    exit(main(args.osmfile, args.stopsfile))