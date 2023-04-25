import logging
import math
import argparse
import spatialite
import sqlite3
import sys

from . import config
from .util import drop_table_if_exists

def get_rating(row):
	return row['rating']

def get_total_rating_prod(matches, agency_stops_cnt):
	# All agency stops are matched, calculated rating for this match assembly
	unmatched_cnt = agency_stops_cnt - len(matches)
	# Rank all unmatched with the mininum acceptance value
	product_of_unmatched = pow(config.RATING_BELOW_CANDIDATES_ARE_IGNORED, unmatched_cnt)
	product_of_matches_rating = math.prod(map(lambda m: m['rating'], matches))
	root = pow(product_of_matches_rating*product_of_unmatched, 1.0/agency_stops_cnt)
	return root

def get_total_rating_sum(matches, agency_stops_cnt):
	# All agency stops are matched, calculated rating for this match assembly
	unmatched_cnt = agency_stops_cnt - len(matches)
	# Rank all unmatched with the mininum acceptance value
	product_of_unmatched = config.RATING_BELOW_CANDIDATES_ARE_IGNORED * unmatched_cnt
	product_of_matches_rating = math.fsum(map(lambda m: m['rating'], matches))
	root = (product_of_matches_rating+product_of_unmatched)/agency_stops_cnt
	return root

def best_unique_matches(candidates, agency_stops = [], matches = [], matched_index = 0, already_matched_osm = []):
	if (len(agency_stops) == 0 ):
		agency_stops_set = set()
		cand_count = 0
		for candidate in candidates:
			cand_count += len(candidates[candidate])
			agency_stops_set.add(candidate)
		agency_stops = list(agency_stops_set)
		if cand_count > config.MAX_CANDIDATE_COUNT_PER_STOP_BEFORE_ONLY_BEST_PER_QUAY_ARE_CONSIDERED:
			for candidate in candidates:
				# retain only best candidate to reduce complexity
				if candidates[candidate]: 
					candidates[candidate].sort(reverse = True, key = get_rating)
					candidates[candidate] = [candidates[candidate][0]]
					
	agency_stops_cnt = len(agency_stops)
	if matched_index < agency_stops_cnt:
		stop_candidates = candidates.get(agency_stops[matched_index])
		best_rating = 0
		best_matches = []
		(best_rating, best_matches) = best_unique_matches(candidates, agency_stops, matches.copy(), matched_index+1, already_matched_osm)
		for candidate in stop_candidates:
			candidate_id = candidate["osm_id"]
			if not candidate_id in already_matched_osm:
				(rating, current_matches) = best_unique_matches(candidates, agency_stops, matches.copy()+[candidate], matched_index+1, already_matched_osm+[candidate_id])
				if rating > best_rating:
					best_rating = rating
					best_matches = current_matches
		return (best_rating, best_matches)
	else:
		return (get_total_rating_sum(matches, agency_stops_cnt), matches)

def parent_station_id(ifopt_id):
	return ifopt_id[:ifopt_id.index(':',9)]

def is_quai(ifopt_id):
	return ifopt_id.find(':',9) > -1

class MatchPicker():

	def __init__(self, db):
		self.db = db
		self.logger = logging.getLogger('osm_stop_matcher.MatchPicker')


	def pick_matches(self, log_only=False, stop_id_prefix=''):
		if config.SIMPLE_MATCH_PICKER:
			return self.simple_pick_matches()

		cur = self.db.cursor()
		
		if not log_only:
			cur.execute("DELETE FROM matches")

		cur.execute("SELECT * FROM candidates WHERE rating >= ? AND ifopt_id like ? ORDER BY ifopt_id", [config.RATING_BELOW_CANDIDATES_ARE_IGNORED, stop_id_prefix+'%'])
		rows = cur.fetchall()
		self.logger.info("Picking matches from %d candidates", len(rows))
		matches = []
		idx = 0
		ifopt_id_col = 0
		matchset_count = 0	
		while idx < len(rows):

			first = True
			subset_size = 0
			matchset_count += 1
			candidates = {}
			# Collect all matches for same parent stop (assuming their stop_id have same leading <country>:<district>:<parentid> )
			while idx < len(rows) and (first or (is_quai(rows[idx-1][ifopt_id_col]) and is_quai(rows[idx][ifopt_id_col]) and parent_station_id(rows[idx][ifopt_id_col]) == parent_station_id(rows[idx-1][ifopt_id_col]))):
				first = False
				ifopt_id = rows[idx]["ifopt_id"]

				if not ifopt_id in candidates:
					candidates[ifopt_id] = []
				candidates[ifopt_id].append(rows[idx])

				if log_only:
					self.logger.debug("Evaluate %s, %s, %s", rows[idx]["ifopt_id"], rows[idx]["osm_id"], rows[idx]["rating"])

				subset_size += 1
				idx += 1

			if subset_size < 50:
				# pick best matches
				(rating, matches) = best_unique_matches(candidates)
				if not log_only:
					self.import_matches(matches)
				else:
					for match in matches:
						self.logger.debug("Matched %s, %s, %s", match["ifopt_id"], match["osm_id"], match["rating"])
			else:
				self.logger.debug('Matching bereiche as subset_size too large: %s for %s', subset_size, candidates)
				bereiche = {}
				for ifopt_id in candidates:
					bereich_id = ifopt_id[:ifopt_id.rindex(':')]
					if not bereich_id in bereiche:
						bereiche[bereich_id] = {}
					bereiche[bereich_id][ifopt_id] = candidates[ifopt_id]
				for bereich_id in bereiche:
					(rating, matches) = best_unique_matches(bereiche[bereich_id])
					if not log_only:
						self.import_matches(matches)
					else:
						self.logger.debug("Matched %s", matches)

			if matchset_count % 2500 == 0:
				self.logger.info('Matched %s stops...', matchset_count)

		if not log_only:
			self.logger.info('Imported matches')
			self.db.execute("""DELETE FROM matches 
				                WHERE (ifopt_id, osm_id) IN (
				                 SELECT c2.ifopt_id, c2.osm_id
				                   FROM matches c1, matches c2 
				                  WHERE c1.osm_id = c2.osm_id 
				                    AND c2.rating < c1.rating)""")
			self.logger.info('Deleted worse matches if one osm_stop is associated with multiple agency stops')
			self.db.execute("""DELETE FROM matches AS md WHERE (md.ifopt_id, md.osm_id) IN (
								SELECT mr.ifopt_id, mr.osm_id
								  FROM matches mr, matches mk 
								 WHERE mr.ifopt_id=mk.ifopt_id
								  AND mr.rating < mk.rating
								  AND mr.name_distance != mk.name_distance)""")
			self.logger.info('Deleted matches with worse rating if multiple osm_stop matches same agency stop and name differs. If name is equal, official stop might be not have quaies')
			self.db.commit()

	def simple_pick_matches(self):
		self.logger.info('Simple match picking...')
		cur = self.db.cursor()
		drop_table_if_exists(self.db, "matches")
		cur.execute("""CREATE TABLE matches AS
			SELECT ifopt_id, osm_id, rating, distance, name_distance, platform_matches, successor_rating, mode_rating FROM candidates
			WHERE rating > 0.99
			UNION
			SELECT ifopt_id, osm_id, MAX(rating) rating, distance, name_distance, platform_matches, successor_rating, mode_rating FROM candidates 
			GROUP BY ifopt_id
			UNION
			SELECT ifopt_id, osm_id, MAX(rating) rating, distance, name_distance, platform_matches, successor_rating, mode_rating FROM candidates 
			GROUP BY osm_id""")

		self.db.commit()

	def import_matches(self, matches):
		cur = self.db.cursor()
		cur.executemany("INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?)", matches)
		self.db.commit()

# run e.g. via python3 -m log_only -p 'de:08111:2039:' -d out/stops.db
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', handlers=[
        logging.StreamHandler(sys.stdout)
    ])
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', dest='db_file', required=False, help='sqlite DB out file', default='out/stops.db')
    parser.add_argument('-p', dest='prefix', required=False, help='stop prefix', default='')
    parser.add_argument('-m', dest='mode', required=False, help='mode', default='log_only', choices=['log_only','pick'])
    
    args = parser.parse_args()
    
    db = spatialite.connect(args.db_file)
    db.execute("PRAGMA case_sensitive_like=ON")
    db.row_factory = sqlite3.Row

    MatchPicker(db).pick_matches(mode=="log_only", args.prefix)

    