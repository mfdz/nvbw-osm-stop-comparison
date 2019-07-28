"""
Compare OSM stops to officially provided stops.
"""
import csv
import osmium
import math
import sys
from rtree import index
from haversine import haversine, Unit
import ngram
import spatialite
import sqlite3
import traceback

from osm_stop_matcher.MatchPicker import best_unique_matches

def drop_table_if_exists(db, table):
	try:
		db.execute("DROP TABLE {}".format(table))
	except:
		pass

def xstr(str):
	return None if '' == str else str

class StopsError():
	def __init__(self, id, message):
		self.id = id
		self.message = message

class StopsImporter():
	def __init__(self, connection):
		self.db = connection
		
	def import_stops(self, stops_file):
		drop_table_if_exists(self.db, "haltestellen")
		drop_table_if_exists(self.db, "haltestellen_unified")
		cur = self.db.cursor()
		cur.execute("""CREATE TABLE haltestellen (Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, 
			HalteBeschreibung, globaleID, HalteTyp, gueltigAb, gueltigBis, lon REAL, lat REAL, Name_Bereich, globaleID_Bereich, 
			lon_Bereich REAL, lat_Bereich REAL, Name_Steig, globaleID_Steig, lon_Steig REAL, lat_Steig REAL, 
			Fuss_Verbindung, Fahrrad_Verbindung, Individualverkehr_Verbindung, Bus_Verbindung, Strassenbahn_Verbindung, 
			Schmalspurbahn_Verbindung, Eisenbahn_Verbindung, Faehren_Verbindung, match_state)""") 

		with open(stops_file,'r',encoding='iso-8859-1') as csvfile:
			dr = csv.DictReader(csvfile, delimiter=';', quotechar='"')
			to_db = [(
				xstr(row['Landkreis']), 
				xstr(row['Gemeinde']), 
				xstr(row['Ortsteil']),
				xstr(row['Haltestelle']),
				xstr(row['Haltestelle_lang']),
				xstr(row['HalteBeschreibung']),
				xstr(row['globaleID']),
				xstr(row['HalteTyp']),
				xstr(row['gueltigAb']),
				xstr(row['gueltigBis']),
				float(row['lon']) if row['lon'] else None, 
				float(row['lat']) if row['lat'] else None,
				xstr(row['Name_Bereich']),
				xstr(row['globaleID_Bereich']), 
				float(row['lon_Bereich']) if row['lon_Bereich'] else None, 
				float(row['lat_Bereich']) if row['lat_Bereich'] else None, 
				xstr(row['Name_Steig']),
				xstr(row['globaleID_Steig']),
				float(row['lon_Steig']) if row['lon_Steig'] else None, 
				float(row['lat_Steig']) if row['lat_Steig'] else None, 
				xstr(row['Fuss_Verbindung']),
				xstr(row['Fahrrad_Verbindung']),
				xstr(row['Individualverkehr_Verbindung']),
				xstr(row['Bus_Verbindung']),
				xstr(row['Strassenbahn_Verbindung']),
				xstr(row['Schmalspurbahn_Verbindung']),
				xstr(row['Eisenbahn_Verbindung']),
				xstr(row['Faehren_Verbindung']),
				) for row in dr]

			cur.executemany("""INSERT INTO haltestellen (Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, 
					HalteBeschreibung, globaleID, HalteTyp, gueltigAb, gueltigBis, lon, lat, Name_Bereich, globaleID_Bereich, 
					lon_Bereich, lat_Bereich, Name_Steig, globaleID_Steig, lon_Steig, lat_Steig, 
					Fuss_Verbindung, Fahrrad_Verbindung, Individualverkehr_Verbindung, Bus_Verbindung, Strassenbahn_Verbindung, 
					Schmalspurbahn_Verbindung, Eisenbahn_Verbindung, Faehren_Verbindung) VALUES (?{})""".format(",?"*27), to_db)

			cur.execute("UPDATE haltestellen SET match_state = 'no_x_ride' WHERE Name_Bereich like '%+R%' AND match_state IS NULL")
			cur.execute("UPDATE haltestellen SET match_state = 'no_entry' WHERE Name_Bereich like '%ugang%' OR Name_Steig like '%ugang%' AND match_state IS NULL")
			cur.execute("UPDATE haltestellen SET match_state = 'no_replacement' WHERE (Haltestelle like '%rsatz%' OR Haltestelle like '%SEV%' OR Name_Bereich like '%rsatz%' OR Name_Bereich like '%SEV%' OR Name_Steig like '%rsatz%' OR Name_Steig like '%SEV%' ) AND match_state IS NULL")
			cur.execute("UPDATE haltestellen SET match_state = 'no_extraterritorial' WHERE HalteTyp like '%Netzbereich%' AND match_state IS NULL")
			cur.execute("SELECT InitSpatialMetaData()")
			cur.execute("SELECT AddGeometryColumn('haltestellen', 'the_geom', 4326, 'POINT','XY')")
			cur.execute("UPDATE haltestellen SET the_geom = MakePoint(lon_Steig,lat_Steig, 4326) WHERE lon_Steig is NOT NULL")
			cur.execute("CREATE INDEX id_steig_idx ON haltestellen(globaleID_Steig)")
		
			cur.execute("""CREATE TABLE haltestellen_unified AS
				select Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID, HalteTyp, gueltigAb, gueltigBis, lon, lat, 'Halt' Art , NULL Name_Steig, 
					CASE 
						WHEN Name_Bereich LIKE '%Bus%' THEN 'Bus' 
						WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Bereich LIKE '%Zug%' OR Name_Steig LIKE '%Gl%' THEN 'BAHN'
						ELSE NULL
					END mode, NULL parent, match_state FROM haltestellen where lon_Steig IS NULL AND (match_state IS NULL or match_state='matched') AND globaleID IS NOT NULL
				UNION
				select Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID_Steig, HalteTyp, gueltigAb, gueltigBis, lon_Steig, lat_Steig, 'Steig' Art, Name_Steig, 
				CASE 
						WHEN Name_Bereich LIKE '%Bus%' THEN 'Bus' 
						WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Bereich LIKE '%Zug%' OR Name_Steig LIKE '%Gl%' THEN 'BAHN'
						ELSE NULL
					END mode, globaleID parent, match_state FROM haltestellen where lon_Steig IS NOT NULL AND globaleID_Steig IS NOT NULL
					AND (match_state IS NULL or match_state='matched')
			""")
			cur.execute("DELETE FROM haltestellen_unified WHERE globaleID IN (SELECT parent FROM haltestellen_unified)")
			cur.execute("CREATE INDEX id_idx ON haltestellen_unified(globaleID)")
			cur.execute("SELECT AddGeometryColumn('haltestellen_unified', 'the_geom', 4326, 'POINT','XY')")
			cur.execute("UPDATE haltestellen_unified SET the_geom = MakePoint(lon,lat, 4326) WHERE lon is NOT NULL")

			self.db.commit()

class OsmStopHandler(osmium.SimpleHandler):
	errors = {}
	counter = 0
	official_matches = {}
	osm_matches = {}

	def __init__(self, import_osm, import_haltestellen, stops_file, osm_file):
		super(OsmStopHandler,self).__init__()
		self.osm_stops = index.Index()
		self.db = spatialite.connect('stops.db')
		self.db.execute("PRAGMA case_sensitive_like=ON");
		self.db.row_factory = sqlite3.Row   
		self.rows_to_import = [] 
		self.import_osm = import_osm
		self.import_haltestellen = import_haltestellen
		
		if self.import_haltestellen:
			StopsImporter(self.db).import_stops(stops_file)
		if self.import_osm:
			self.setup_osm_tables()
			self.apply_file(osm_file)
			self.export_osm_stops()
		self.load_osm_index()

	def setup_osm_tables(self):
		drop_table_if_exists(self.db, 'osm_stops')
		self.db.execute('''CREATE TABLE osm_stops
			(node_id INTEGER PRIMARY KEY, name text, network text, operator text, lat real, lon real, mode text, type text, ref text, ref_key text, assumed_platform text)''')
		
		drop_table_if_exists(self.db, 'successor')
		self.db.execute('''CREATE TABLE successor
			(pred_id INTEGER, succ_id INTEGER)''')	

	def add_error(self, id, message):
		if not id in self.errors:
			self.errors[id] = []
		self.errors[id].append(StopsError(id, message))

	def node(self, n):
		tags = n.tags
		stop_type = self.extract_stop_type(tags)
		if stop_type:
			self.counter += 1
			(ref_key, ref) = self.extract_ref(tags)
			assumed_platform = self.extract_steig(tags)
			stop = {
				"id": n.id,
				"lat": n.location.lat,
				"lon": n.location.lon,
				"tags": {tag.k: tag.v for tag in n.tags},
				"mode": self.extract_stop_mode(tags),
				"type": stop_type ,
				"ref": ref,
				"ref_key": ref_key,
				"assumed_platform": assumed_platform
			}

			self.store_osm_stop(stop)

	def load_osm_index(self):
		cur = self.db.execute("SELECT * FROM osm_stops")
		rows = cur.fetchall()
		for stop in rows:
			lat = stop["lat"]
			lon = stop["lon"]
			id = stop["node_id"]
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
				"assumed_platform": stop["assumed_platform"]
			}
			self.osm_stops.insert(id = id, coordinates=(lat, lon, lat, lon), obj= stop)

	def store_osm_stop(self, stop):
		lat = stop["lat"]
		lon = stop["lon"]
		
		self.rows_to_import.append((
			stop["id"], 
			stop["tags"].get("name"), 
			stop["tags"].get("network"), 
			stop["tags"].get("operator"),
			lat,
			lon,
			stop["mode"],
			stop["type"],
			stop["ref"],
			stop["ref_key"],
			stop["assumed_platform"],
			))
				
		if self.counter  % 100 == 0:
			self.store_osm_stops(self.rows_to_import)
			self.rows_to_import = []

	pred = {}
	succ = {}

	def relation(self, r):

		if not r.tags.get("route"): 
			return
			
		predecessor = None
		for m in r.members:
			if "platform" in m.role and m.type == 'n':
				current = m.ref
				if predecessor: 
					if not current in self.pred:
						self.pred[current] = set()
					if not predecessor in self.succ:
						self.succ[predecessor] = set()
					self.pred[current].add(predecessor)
					self.succ[predecessor].add(current)
				predecessor = current

	def normalize_IFOPT(self, ifopt):
		return ifopt.upper().replace("DE:0", "DE:")

	def extract_stop_mode(self, tags):
		ordered_ref_keys= ["bus","train","tram","light_rail",]
		for key in ordered_ref_keys:
			if key in tags and tags[key]=='yes':
				return key

	def extract_stop_type(self, tags):
		if tags.get('public_transport') == 'station':
			return 'station' 
		elif tags.get('highway') == 'bus_stop' or tags.get('railway') == 'stop' or tags.get('railway') == 'tram_stop':
			return 'stop'
		elif tags.get('public_transport') == 'platform':
			return 'platform'
		elif tags.get('railway') == 'halt':
			return 'halt'
		else:
			return None

	def extract_ref(self, tags):
		ordered_ref_keys= ["ref:IFOPT","ref:pt_id"]
		for key in ordered_ref_keys:
			if key in tags:
				return (key, self.normalize_IFOPT(tags[key]))
		return (None, None)

	def extract_steig(self, tags):
		potential_steig_keys= ["ref","local_ref"]
		for key in potential_steig_keys:
			if key in tags and len(tags[key])<3:
				return tags[key]
		return None

	def rank_successor_matching(self, stop, osm_stop):
		destination = stop
		return

	def rank_candidate(self, stop, candidate, distance):
		osm_name = candidate["name"]
		name_distance_short_name = ngram.NGram.compare(stop["Haltestelle"],osm_name,N=1)
		name_distance_long_name = ngram.NGram.compare(stop["Haltestelle_lang"],osm_name,N=1)
		if stop["Haltestelle"] == '' or stop["Haltestelle"] == None :
			print("Stop {} has no name. Use fix name_distance".format(stop["globaleID"]))
			name_distance_short_name = 0.3
		elif osm_name == '' or osm_name == None:
			print("OSM stop n{} has no name. Use fix name_distance".format(candidate["id"]))
			name_distance_short_name = 0.3
		
		(short_name_matched, matched_name) = (False, stop["Haltestelle_lang"]) if name_distance_short_name < name_distance_long_name else (True, stop["Haltestelle"])
		name_distance = max(name_distance_short_name, name_distance_long_name)
		platform_id = stop["globaleID"]
		ifopt_platform = ''.join(filter(str.isdigit, platform_id[platform_id.rfind(":"):])) if platform_id and platform_id.count(':') > 2 else None
		platform_matches = ifopt_platform == str(candidate["assumed_platform"])
		platform_mismatches = not ifopt_platform == None and not candidate["assumed_platform"] == None and not platform_matches
		successor_ranking = self.rank_successor_matching(stop, candidate)
		
		if candidate["ref"] == stop["globaleID"]:
			# TODO: We currently ignore, that OSM IFOPTS are currently duplicated for some stops...
			rating = 1
		else:
			rating = name_distance / ( 1 + distance )
			# We boost a candidate if steig matches
			if platform_matches:
				rating = math.sqrt(rating)
			elif platform_mismatches:
				# Only a small malus, since OSM has some refs wrongly tagged as bus route number...
				rating = rating*0.99

		print("rank_candidate", (rating, name_distance, matched_name, osm_name, platform_matches))
		return (rating, name_distance, matched_name, osm_name, platform_matches)

	def rank_candidates(self, stop, stop_id, coords, candidates):
		matches = []
		last_name_distance = 0
		for candidate in candidates:
			# estimate distance
			distance = haversine(coords, (candidate["lat"],candidate["lon"]), unit=Unit.METERS)
			if distance > 400:
				return matches
		   
			# Ignore bahn candidates when looking for bus_stop
			if candidate["mode"] in ['train','light_rail','tram'] and "Bus" == stop["mode"]:
				continue
			# Ignore bus candidates when looking for railway stops
			if candidate["mode"] == 'bus' and "BAHN" == stop["mode"]:
				continue
			
			(rating, name_distance, matched_name, osm_name, platform_matches) = self.rank_candidate(stop, candidate, distance)
			if last_name_distance > name_distance:
				print ("Ignore {} ({})  {} (n{}) with distance {} and name similarity {}. Platform matches? {} as name distance low".format(matched_name,stop_id, osm_name, candidate["id"], distance, name_distance,platform_matches))
				continue

			print ("{} ({}) might match {} (n{}) with distance {} and name similarity {}. Platform matches? {}".format(matched_name,stop_id, osm_name, candidate["id"], distance, name_distance,platform_matches))
			
			matches.append({"globalID": stop_id, "match": candidate, "name_distance": name_distance, "distance": distance, "platform_matches": platform_matches, "rating": rating})
			last_name_distance = name_distance
		return matches

	def store_matches(self, stop, offical_stop_id, matches):
		self.official_matches[offical_stop_id] = matches
		
		for match in matches:
			osm_id = match["match"]["id"]
			if not osm_id in self.osm_matches:
				 self.osm_matches[osm_id] = []
			self.osm_matches[osm_id].append(match)

	def match_stop(self, stop, stop_id, coords, row):
		# TODO Check coords
		candidates = list(self.osm_stops.nearest(coords, 5, objects='raw'))
		matches = self.rank_candidates(stop, stop_id, coords, candidates)
		if not matches:
			self.add_error("no_osm_match", "No match for row {} ({})".format(row, stop_id))
		else:
			self.store_matches(stop, stop_id, matches)

	
	def match_stops(self):
		row = 0
		#cur = self.db.execute("SELECT * FROM haltestellen_unified where lon IS NOT NULL AND globaleID like 'de:08111:6015%'")
		cur = self.db.execute("SELECT * FROM haltestellen_unified where lon IS NOT NULL")
		stops = cur.fetchall()
		for stop in stops:
			row += 1
			self.match_stop(stop, stop["globaleID"], (float(stop["lat"]),float(stop["lon"])), row)
				
	def export_match_candidates(self):
		drop_table_if_exists(self.db, "candidates")
		self.db.execute('''CREATE TABLE candidates
			 (ifopt_id text, osm_id text, rating real, distance real, name_distance real, platform_matches integer)''')
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
					match['platform_matches']))
			print("export match candidates ", rows)
			self.db.executemany('INSERT INTO candidates VALUES (?,?,?,?,?,?)', rows)
		self.db.commit()
		self.db.execute('''CREATE INDEX osm_index ON candidates(osm_id, rating DESC)''')
		self.db.execute('''CREATE INDEX ifopt_index ON candidates(ifopt_id, rating DESC)''')
		

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
			 WHERE o.node_id = osm_id AND matches.ifopt_id = n.globaleID AND n.lat IS NOT NULL)""") 
		self.db.execute("""UPDATE candidates SET the_geom = (
			SELECT LineFromText('LINESTRING('||o.lon||' '||o.lat||', '||n.lon||' '||n.lat||')', 4326) 
			  FROM osm_stops o, haltestellen_unified n  
			 WHERE o.node_id = osm_id AND candidates.ifopt_id = n.globaleID AND n.lat IS NOT NULL)""")
		self.db.commit()


	def store_osm_stops(self, rows):
		self.db.executemany('INSERT INTO osm_stops VALUES (?,?,?,?,?,?,?,?,?,?,?)', rows)
		self.db.commit()
		
	def store_successors(self, rows):
		rows = []
		for predecessor in self.succ:
			for successor in self.succ[predecessor]:
				rows.append((predecessor, successor))
		self.db.executemany("INSERT INTO successor VALUES (?,?)", rows)
		self.db.commit()

	def prefer_stops_over_halts(self):
		"""We only retain halts where no stop in vicinity and with same name exists"""
		self.db.execute("""DELETE FROM osm_stops 
			                WHERE node_id IN (
								SELECT h.node_id 
								  FROM osm_stops h, osm_stops s
								 WHERE h.type IN ('halt', 'station')
								   AND h.name = s.name 
								   AND s.type IN ('stop', 'platform') 
								   AND s.mode NOT IN ('bus', 'tram')
								   AND s.lat BETWEEN h.lat-0.01 AND h.lat+0.01 
								   AND s.lon BETWEEN h.lon-0.01 AND h.lon+0.01)""")
		self.db.commit()
		

	def export_osm_stops(self):
		self.store_osm_stops(self.rows_to_import)
		self.store_successors(self.pred)
		self.prefer_stops_over_halts()

		
	def done(self):
		self.db.close()



	def pick_matches(self):
		cur = self.db.cursor()
		cur.execute("DELETE FROM matches")
		cur.execute("SELECT * FROM candidates ORDER BY ifopt_id")
		rows = cur.fetchall()
		matches = []
		idx = 0
		ifopt_id_col = 0
		matchset_count = 0	
		while idx < len(rows):
			first = True
			matchset_count += 1
			candidates = {}
			# Collect all matches for same stop
			while idx < len(rows) and (first or (rows[idx-1][ifopt_id_col].find(':',9) > -1  and rows[idx][ifopt_id_col].find(':',9) > -1 and rows[idx][ifopt_id_col][:rows[idx][ifopt_id_col].index(':',9)] == rows[idx-1][ifopt_id_col][:rows[idx-1][ifopt_id_col].index(':',9)])):
				first = False

				if not rows[idx]["ifopt_id"] in candidates:
					candidates[rows[idx]["ifopt_id"]] = []
				candidates[rows[idx]["ifopt_id"]].append(rows[idx])
				if  rows[idx]["ifopt_id"].startswith('de:08111:6015'):
					print("collecting ", matchset_count, " ", idx, " ", rows[idx])
				idx += 1
			# pick best matches
			(rating, matches) = best_unique_matches(candidates)
			self.import_matches(matches)
		self.db.execute("""DELETE FROM matches 
			                WHERE (ifopt_id, osm_id) IN (
			                 SELECT c2.ifopt_id, c2.osm_id 
			                   FROM matches c1, matches c2 
			                  WHERE c1.osm_id = c2.osm_id 
			                    AND c2.rating < c1.rating)""")
		self.db.commit()

	def import_matches(self, matches):
		cur = self.db.cursor()
		cur.executemany("INSERT INTO matches VALUES(?,?,?,?,?,?,?)", matches)
		self.db.commit()

	def check_matched(self, ifopt_id, osm_id):
		cur = self.db.execute("SELECT * FROM matches WHERE ifopt_id=? AND osm_id = ?", [ifopt_id, osm_id])
		if not len(cur.fetchall())>0:
			print("ERROR: Expected match is missing: {}->{}".format(ifopt_id, osm_id))

	def check_not_matched(self, ifopt_id, osm_id):
		cur = self.db.execute("SELECT * FROM matches WHERE ifopt_id=? AND osm_id = ?", [ifopt_id, osm_id])
		if not len(cur.fetchall())==0:
			print("ERROR: Got unexpected match for: {}->{}".format(ifopt_id, osm_id))

	def check_assertions(self):
		self.check_matched('de:08311:30822:0:5', 4391668851)
		# Ensingen Feuerwehrmagazin.  kein Candidat. Mutmaßlich schlechterer Wert für Name Distance?	
		self.check_matched('de:08118:5920:0:3',6158905230)
		# Gutach Freilichtmuseum. rating 0, da NVBW keinen Namen liefert (insgesamt 1395 Halte)
		self.check_matched('de:08317:18733:1:1', 3207442779)

		self.check_matched('de:08231:488:0:1', 1564906436)
		self.check_not_matched('de:08231:488:0:1', 310744136)
		
		# Karl-Abt-Straße even no candidate
		self.check_matched('de:08231:487:0:1',310744136)
		# Rohr ist mit Steigen vorhanden, desh
		self.check_not_matched('de:08111:6001',301614772)
		# Rohe Pestalozzischule
		self.check_matched('de:08111:6015:0:3',271653920) # Albblick
		self.check_not_matched('de:08111:6015:0:3',271654026)
		self.check_matched('de:08111:6015:0:4',271654026) # Waldburgstra
		self.check_not_matched('de:08111:6015:0:4',271653920) # Waldburgstra

	def update_match_statistics(self):
		self.db.execute("""UPDATE haltestellen_unified 
			                  SET match_state='MATCHED' 
			                WHERE globaleID IN (SELECT ifopt_id FROM matches)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_AMBIGOUSLY' 
							WHERE globaleID IN (SELECT ifopt_id FROM matches GROUP BY ifopt_id HAVING count(*)>1)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_NAMES_DIFFER' 
			                WHERE globaleID IN (SELECT ifopt_id FROM matches WHERE name_distance < 0.3 AND rating > 0.002)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_OSM_NO_NAME' 
							WHERE globaleID IN (SELECT ifopt_id FROM matches m, osm_stops o WHERE o.name IS NULL AND m.osm_id = o.node_id)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_DISTANT' 
							WHERE globaleID IN (SELECT ifopt_id FROM matches m WHERE distance > 200 AND rating > 0.002)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='NO_MATCH' 
							WHERE globaleID NOT IN (SELECT ifopt_id FROM matches);""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='NO_MATCH_BUT_OTHER_PLATFORM_MATCHED' 
							WHERE match_state='NO_MATCH' AND PARENT IN (SELECT h.parent FROM matches m, haltestellen_unified h WHERE m.ifopt_id = h.globaleID)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='NO_MATCH_NO_IFOPT' 
							WHERE globaleID IS NULL""")
		self.db.commit()
		
def main(osmfile, stops_file):
	statshandler = OsmStopHandler(import_osm = True, import_haltestellen = True, stops_file = stops_file, osm_file = osmfile)
	
	print("Loaded osm file")
	statshandler.match_stops()
	print("Found candidates")
	statshandler.export_match_candidates()
	print("Exported candidates")
	statshandler.pick_matches()
	statshandler.check_assertions()
	statshandler.update_match_statistics()
	statshandler.done()


	return 0


if __name__ == '__main__':
	if len(sys.argv) != 3:
		print("Usage: python %s <osmfile> <stopsfile>" % sys.argv[0])
		sys.exit(-1)

	exit(main(sys.argv[1], sys.argv[2]))