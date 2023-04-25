import logging
import math
import ngram
import re

from rtree import index
from haversine import haversine, Unit

from osm_stop_matcher.util import  drop_table_if_exists, backup_table_if_exists

from . import config

class StopMatcher():
	MINIMUM_SUCCESSOR_SIMILARITY = 0.6
	MINIMUM_SUCCESSOR_PREDECESSOR_DISTANCE = 0.11
	
	DIRECTION_PREFIX_PATTERN = '(.*)(eRtg|Ri |>|Ri\.|Rtg|Richt |Fahrtrichtung|Ri-|Ri:|Richtung|Richtg\.|FR )(.*)'
	STOPS_SEPARATOR = '/'
	
	official_matches = {}
	osm_matches = {}
	errors = {}

	def __init__(self, db):
		self.db = db
		self.osm_stops = index.Index()
		self.logger = logging.getLogger('osm_stop_matcher.StopMatcher')	

	def match_stops(self):
		self._match_stops('%', export = True)

	def _match_stops(self, id_pattern = '%', export = False):
		self.logger.info("Loading osm data to index")
		self.load_osm_index()
		self.logger.info("Loaded osm data to index")
		row = 0
		cur = self.db.execute("SELECT * FROM haltestellen_unified where lon IS NOT NULL AND globaleID like ?", [id_pattern])
		stops = cur.fetchall()
		for stop in stops:
			row += 1
			self.match_stop(stop, stop["globaleID"], (float(stop["lat"]),float(stop["lon"])), row)
		
		self.logger.info("Matched stops")
		if export:	
			self.export_match_candidates()
			self.logger.info("Exported candidates")

	def load_osm_index(self):
		cur = self.db.execute("SELECT * FROM osm_stops")
		cnt = 0
		rows = cur.fetchall()
		for stop in rows:
			cnt += 1
			lat = stop["lat"]
			lon = stop["lon"]
			id = stop["osm_id"]
			stop = {
				"id": id,
				"name": stop["name"],
				"network": stop["network"],
				"operator": stop["operator"],
				"lat": lat,
				"lon": lon,
				"mode": stop["mode"],
				"type": stop["type"],
				"ref": stop["ref"],
				"ref_key": stop["ref_key"],
				"next_stops": stop["next_stops"],
				"prev_stops": stop["prev_stops"],
				"assumed_platform": stop["assumed_platform"]
			}
			self.osm_stops.insert(id = cnt, coordinates=(lat, lon, lat, lon), obj= stop)

	def substring_after(self, string , char):
		index = string.find(char)
		if index > -1:
			return string[index+1:]
		else:
			return string

	def compare_stop_names(self, offical_stoplist, osm_stoplist):
		if osm_stoplist is None:
			return 0

		best_value = 0
		for official_stop in re.sub("\(\w*\)", '', offical_stoplist).split(self.STOPS_SEPARATOR):
			for osm_stop in re.sub("\(\w*\)", '', osm_stoplist).split(self.STOPS_SEPARATOR):

				value = ngram.NGram.compare(official_stop, osm_stop, N=1)
				if value > best_value:
					best_value = value

		return best_value

	def rank_successor_matching(self, stop, osm_stop):
		richtung = stop["Name_Steig"]
		ortsteil = stop['Ortsteil']
		gemeinde = stop['Gemeinde']

		if richtung:
			match = re.match(self.DIRECTION_PREFIX_PATTERN, richtung)
			if match:
				richtung = match.group(3).strip()
				richtung = self.normalize_direction(richtung, ortsteil, gemeinde)
				# Note: removing the current stop's city from the successor/predecessor might remove the wrong significant part,
				# e.g. 
				next_stops = self.normalize_direction(osm_stop["next_stops"], ortsteil, gemeinde) if osm_stop["next_stops"] else None
				prev_stops = self.normalize_direction(osm_stop["prev_stops"], ortsteil, gemeinde) if osm_stop["prev_stops"] else None
				similarity_next = self.compare_stop_names(richtung, next_stops)
				similarity_prev = self.compare_stop_names(richtung, prev_stops)
				self.logger.info("Successor ranking for %s (%s, %s): next %s (%.2f) prev %s (%.2f)", richtung, ortsteil, gemeinde, next_stops, similarity_next, prev_stops, similarity_prev)
				if similarity_next >= self.MINIMUM_SUCCESSOR_SIMILARITY and (similarity_next - similarity_prev) >= self.MINIMUM_SUCCESSOR_PREDECESSOR_DISTANCE:
					return 1
				elif similarity_prev >= self.MINIMUM_SUCCESSOR_SIMILARITY and (similarity_prev - similarity_next) >= self.MINIMUM_SUCCESSOR_PREDECESSOR_DISTANCE:
					return -1
				else:
					return 0
		return -0.5

	def normalize_direction(self, dir, ortsteil, gemeinde):
		dir = dir.replace(ortsteil+' ', '') if ortsteil else dir
		dir = dir.replace(gemeinde+' ', '') if gemeinde else dir
		return dir.replace('trasse', 'tr').replace(',', ' ').replace('-', ' ').strip()

	def rank_mode(self, stop, candidate):
		if (candidate["mode"] == stop["mode"] or
			candidate["mode"] == 'trainish' and stop["mode"] in ['train', 'light_rail']):
			return 1
		elif not stop["mode"]:
			# official stop not served, will result in greater malus
			return config.UNSERVED_STOP_RATING
		elif not candidate["mode"]:
			# than OSM mode unknown
			return config.UNKNOWN_MODE_RATING
		else:
			return 0

	def rank_platform(self, stop, candidate):
		ifopt_platform = stop["platform_code"]
		candidate_platform = candidate["assumed_platform"]

		if (ifopt_platform == None or ifopt_platform=='') and (candidate_platform == None or candidate_platform == ''):
			return 0.9
		elif not (ifopt_platform == None or ifopt_platform=='') and (candidate_platform == None or candidate_platform == ''):
			# usually, platform should be tagged in OSM, but especially for bus quais, that might not be the case, so just give small discount
			return 0.85
		elif ifopt_platform == str(candidate_platform):
			return 1.0
		else:
			return 0.0
		
	def normalize_name(self, name):
		if not name:
			return name
		normalized_name = re.sub("\([\w\. ]*\)", '', name)
		normalized_name = re.sub("Bahnhof$|Bhf$|Bf$|Ort$", '', normalized_name)
		normalized_name = re.sub("trasse$", 'tr', normalized_name)
		return normalized_name

	def rate_name_equivalence(self, stop, candidate):
		osm_name = self.normalize_name(candidate["name"])
		name_short = self.normalize_name(stop["Haltestelle"])
		name_long = self.normalize_name(stop["Haltestelle_lang"])

		name_distance_short_name = ngram.NGram.compare(name_short, osm_name, N=1)
		name_distance_long_name = ngram.NGram.compare(name_long, osm_name, N=1)
		if not name_short and not name_long:
			self.logger.info("Stop %s has no name. Use fix name_distance", stop["globaleID"])
			name_distance_short_name = self.MINIMUM_NAME_EQUIVALENCE
			name_distance_long_name = self.MINIMUM_NAME_EQUIVALENCE
		elif not osm_name:
			self.logger.info("OSM stop %s has no name. Use fix name_distance", candidate["id"])
			name_distance_short_name = self.MINIMUM_NAME_EQUIVALENCE
			name_distance_long_name = self.MINIMUM_NAME_EQUIVALENCE
		
		if name_distance_short_name > name_distance_long_name:
			return (name_distance_short_name, stop["Haltestelle"])
		else:
			return (name_distance_long_name, stop["Haltestelle_lang"])

	def rank_candidate(self, stop, candidate, distance):
		osm_name = candidate["name"]
		(name_distance, matched_name) = self.rate_name_equivalence(stop, candidate)
		mode_rating = self.rank_mode(stop, candidate)
		successor_rating = self.rank_successor_matching(stop, candidate)
		platform_rating = self.rank_platform(stop, candidate)

		if candidate["ref"] == stop["globaleID"]:
			# TODO: We currently ignore, that OSM IFOPTS are currently duplicated for some stops...
			rating = 1
		else:
			rating = name_distance / ( 1 + distance / 10.0 )
			# We boost a candidate if steig matches
			# Note: since OSM has some refs wrongly tagged as bus route number...
			
			rating = (rating * (0.5 + 0.5 * platform_rating)) ** (1 - successor_rating * 0.3 - mode_rating * 0.2)

		self.logger.debug("rating: %s name_distance: %s matched_name: %s osm_name: %s platform_rating: %s successor_rating: %s, mode_rating: %s", rating, name_distance, matched_name, osm_name, platform_rating, successor_rating, mode_rating)
		return (rating, name_distance, matched_name, osm_name, platform_rating, successor_rating, mode_rating)

	def rank_candidates(self, stop, stop_id, coords, candidates):
		matches = []
		last_name_distance = 0
		for candidate in candidates:
			self.logger.debug('rank %s', candidate)
			# estimate distance
			distance = haversine(coords, (candidate["lat"],candidate["lon"]), unit=Unit.METERS)
			if distance > config.MAXIMUM_DISTANCE:
				return matches
		   
			# Ignore bahn candidates when looking for bus_stop
			if candidate["mode"] in ['trainish', 'train','light_rail','tram'] and "bus" == stop["mode"]:
				continue
			# Ignore bus candidates when looking for railway stops
			if candidate["mode"] == 'bus' and stop["mode"] in ["tram", "light_rail", "train"]:
				continue
			
			(rating, name_distance, matched_name, osm_name, platform_matches, successor_rating, mode_rating) = self.rank_candidate(stop, candidate, distance)
			#if last_name_distance > name_distance:
			if last_name_distance > name_distance and name_distance < config.MINIMUM_NAME_SIMILARITY:
				self.logger.info("Ignore {} ({})  {} ({}) with distance {} and name similarity {}. Platform matches? {} as name distance low".format(matched_name,stop_id, osm_name, candidate["id"], distance, name_distance,platform_matches))
				continue
			elif rating < 0.001:
				self.logger.info("Ignore {} ({})  {} ({}) as rating {} is low".format(matched_name,stop_id, osm_name, candidate["id"], distance, name_distance,platform_matches))
				continue
			self.logger.info("{} ({}) might match {} ({}) with distance {} and name similarity {}. Platform matches? {}".format(matched_name,stop_id, osm_name, candidate["id"], distance, name_distance,platform_matches))
			
			matches.append({"globalID": stop_id, "match": candidate, "name_distance": name_distance, "distance": distance, "platform_matches": platform_matches, "successor_rating": successor_rating, "rating": rating, "mode_rating": mode_rating})
			last_name_distance = name_distance
		return matches

	def store_matches(self, stop, offical_stop_id, matches):
		self.official_matches[offical_stop_id] = matches
		
		for match in matches:
			osm_id = match["match"]["id"]
			if not osm_id in self.osm_matches:
				 self.osm_matches[osm_id] = []
			self.osm_matches[osm_id].append(match)

	def is_bus_station(self, stop):
		name = stop["Haltestelle"]  if stop["Haltestelle"] else stop["Haltestelle_lang"] 
		return name and ('ahnhof' in name
			or 'ZOB' in name
			or 'Schulzentrum' in name
			or 'Flughafen' in name
			or ' Bf' in name )

	def match_stop(self, stop, stop_id, coords, row):
		no_of_candidates = 15 if self.is_bus_station(stop) else 10

		candidates = list(self.osm_stops.nearest(coords, no_of_candidates, objects='raw'))
		matches = self.rank_candidates(stop, stop_id, coords, candidates)
		if matches:	
			self.store_matches(stop, stop_id, matches)
	
	def export_match_candidates(self):
		drop_table_if_exists(self.db, "candidates")
		self.db.execute('''CREATE TABLE candidates
			 (ifopt_id text, osm_id text, rating real, distance real, name_distance real, platform_matches integer, successor_rating INTEGER, mode_rating real)''')
		for stop_id in self.official_matches:
			matches = self.official_matches[stop_id]
			rows = []
			for match in matches:
				rows.append((
					match["globalID"], 
					match["match"]["id"], 
					match["rating"], 
					match['distance'], 
					match['name_distance'], 
					match['platform_matches'],
					match['successor_rating'],
					match['mode_rating'],
					))
			self.logger.debug("export match candidates ", rows)
			self.db.executemany('INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)', rows)
		self.db.commit()
		self.db.execute('''CREATE INDEX osm_index ON candidates(osm_id, rating DESC)''')
		self.db.execute('''CREATE INDEX ifopt_index ON candidates(ifopt_id, rating DESC)''')
		
		backup_table_if_exists(self.db, "matches", "matches_backup")

		drop_table_if_exists(self.db, "matches")
		self.db.execute("""CREATE TABLE matches AS
					SELECT * FROM candidates WHERE ifopt_id='Non existant'""")

		# Add Spatial columns
		try:
			self.db.execute("SELECT InitSpatialMetaData()")
			self.db.execute("SELECT AddGeometryColumn('osm_stops', 'the_geom', 4326, 'POINT','XY')")
			self.db.execute("SELECT AddGeometryColumn('matches', 'the_geom', 4326, 'LINESTRING','XY')")
			self.db.execute("SELECT AddGeometryColumn('candidates', 'the_geom', 4326, 'LINESTRING','XY')")
		except:
			pass
		self.db.execute("UPDATE osm_stops SET the_geom = MakePoint(lon,lat, 4326)")
		self.db.execute("""UPDATE matches SET the_geom = (
			SELECT LineFromText('LINESTRING('||o.lon||' '||o.lat||', '||n.lon||' '||n.lat||')', 4326) 
			  FROM osm_stops o, haltestellen_unified n  
			 WHERE o.osm_id = matches.osm_id AND matches.ifopt_id = n.globaleID AND n.lat IS NOT NULL)""") 
		self.db.execute("""UPDATE candidates SET the_geom = (
			SELECT LineFromText('LINESTRING('||o.lon||' '||o.lat||', '||n.lon||' '||n.lat||')', 4326) 
			  FROM osm_stops o, haltestellen_unified n  
			 WHERE o.osm_id = candidates.osm_id AND candidates.ifopt_id = n.globaleID AND n.lat IS NOT NULL)""")
		self.db.commit()
