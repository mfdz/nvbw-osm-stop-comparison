import logging
import math

from . import config

def get_rating(row):
	return row['rating']

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
					
	if matched_index < len(agency_stops):
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
		# All agency stops are matched, calculated rating for this match assmebly
		sum = 0
		if matches:
			for match in matches:
				sum += match['rating']
				#sum += match['rating']
		return (sum, matches)

class MatchPicker():

	def __init__(self, db):
		self.db = db
		self.logger = logging.getLogger('osm_stop_matcher.MatchPicker')


	def pick_matches(self):
		cur = self.db.cursor()
		cur.execute("DELETE FROM matches")
		cur.execute("SELECT * FROM candidates WHERE rating >= ? ORDER BY ifopt_id", [config.RATING_BELOW_CANDIDATES_ARE_IGNORED])
		rows = cur.fetchall()
		matches = []
		idx = 0
		ifopt_id_col = 0
		matchset_count = 0	
		while idx < len(rows):
			first = True
			subset_size = 0
			matchset_count += 1
			candidates = {}
			# Collect all matches for same stop
			while idx < len(rows) and (first or (rows[idx-1][ifopt_id_col].find(':',9) > -1  and rows[idx][ifopt_id_col].find(':',9) > -1 and rows[idx][ifopt_id_col][:rows[idx][ifopt_id_col].index(':',9)] == rows[idx-1][ifopt_id_col][:rows[idx-1][ifopt_id_col].index(':',9)])):
				first = False

				if not rows[idx]["ifopt_id"] in candidates:
					candidates[rows[idx]["ifopt_id"]] = []
				candidates[rows[idx]["ifopt_id"]].append(rows[idx])
				subset_size += 1
				idx += 1
			if subset_size < 50:
				# pick best matches
				(rating, matches) = best_unique_matches(candidates)
				self.import_matches(matches)
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
					self.import_matches(matches)

			if matchset_count % 2500 == 0:
				self.logger.info('Matched %s stops...', matchset_count)

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
							  AND mr.name_distance < mk.name_distance)""")
		self.logger.info('Deleted matches with worse name_distance if multiple osm_stop match same agency stop')
		self.db.commit()


	def import_matches(self, matches):
		cur = self.db.cursor()
		cur.executemany("INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?)", matches)
		self.db.commit()