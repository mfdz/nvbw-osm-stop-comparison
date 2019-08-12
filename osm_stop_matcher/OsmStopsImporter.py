import logging
import osmium
from osm_stop_matcher.util import  drop_table_if_exists


class OsmStopsImporter(osmium.SimpleHandler):
	counter = 0
	pred = {}
	succ = {}
	stop_areas = {}
	area_for_stop = {}

	def __init__(self, db, osm_file):
		super(OsmStopsImporter,self).__init__()
		self.logger = logging.getLogger('osm_stop_matcher.OsmStopsImporter')
		self.db = db
		self.rows_to_import = [] 
		
		self.setup_osm_tables()
		self.logger.info("Created osm tables")
		self.apply_file(osm_file)
		self.logger.info("Loaded osm data")
		self.export_osm_stops()
		self.logger.info("Exported osm data")
		
		
	def setup_osm_tables(self):
		drop_table_if_exists(self.db, 'osm_stops')
		self.db.execute('''CREATE TABLE osm_stops
			(node_id INTEGER PRIMARY KEY, name TEXT, network TEXT, operator TEXT, railway TEXT, highway TEXT, public_transport TEXT, lat REAL, lon REAL, 
			 mode TEXT, type TEXT, ref TEXT, ref_key TEXT, assumed_platform TEXT)''')
		
		drop_table_if_exists(self.db, 'successor')
		self.db.execute('''CREATE TABLE successor
			(pred_id INTEGER, succ_id INTEGER)''')	

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
	
	def store_osm_stop(self, stop):
		lat = stop["lat"]
		lon = stop["lon"]
		
		self.rows_to_import.append((
			stop["id"], 
			stop["tags"].get("name"), 
			stop["tags"].get("network"), 
			stop["tags"].get("operator"),
			stop["tags"].get("railway"),
			stop["tags"].get("highway"),
			stop["tags"].get("public_transport"),
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

	def relation_route(self, r):
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

	def relation(self, r):
		if r.tags.get("route"): 
			self.relation_route(r)
		elif r.tags.get("public_transport") == "stop_area":
			self.relation_stop_area(r)
		
	def relation_stop_area(self, r):

		(ref_key, ref) = self.extract_ref(r.tags)
		area = {	
			"id": r.id,
			"name": r.tags.get("name"),
			"network": r.tags.get("network"), 
			"operator": r.tags.get("operator"),
			"ref_key": ref_key,
			"ref": ref,
			"mode": self.extract_stop_mode(r.tags)
		}
			
		self.stop_areas[r.id] = area
						
		for m in r.members:
			if m.role in ("platform", "stop") and m.type == 'n':
				current = m.ref
				self.area_for_stop[current] = area	

	def normalize_IFOPT(self, ifopt):
		return ifopt.lower().replace("de:8", "de:08")

	def extract_stop_mode(self, tags):
		ordered_ref_keys= ["bus","train","tram","light_rail",]
		first_occurrence = None
		for key in ordered_ref_keys:
			if key in tags and tags[key]=='yes':
				if first_occurrence:
					return None
				else:
					first_occurrence = key
		return first_occurrence

	def extract_stop_type(self, tags):
		if tags.get('public_transport') == 'station':
			return 'station' 
		elif tags.get('highway') == 'bus_stop' or tags.get('railway') in ['stop','tram_stop'] or (tags.get('public_transport') == 'stop_position' and (not tags.get('bus') == 'yes' or tags.get('ref'))):
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

	def store_osm_stops(self, rows):
		self.db.executemany('INSERT INTO osm_stops VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
		self.db.commit()
		
	def store_successors(self, rows):
		rows = []
		for predecessor in self.succ:
			for successor in self.succ[predecessor]:
				rows.append((predecessor, successor))
		self.db.executemany("INSERT INTO successor VALUES (?,?)", rows)
		self.db.commit()

	def only_keep_more_specific_stops_for_matching(self):
		# We only retain halts where no stop in vicinity and with same name exists.
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
		# We delete stops for buses and trams if there is a platform (currently only nodes) with the same name in the vicinity.
		self.db.execute("""DELETE FROM osm_stops 
			                WHERE node_id IN (
								SELECT h.node_id 
								  FROM osm_stops h, osm_stops s
								 WHERE h.type IN ('stop')
								   AND h.name = s.name 
								   AND s.type IN ('platform') 
								   AND s.mode IN ('bus', 'tram')
								   AND s.mode = h.mode
								   AND s.lat BETWEEN h.lat-0.01 AND h.lat+0.01 
								   AND s.lon BETWEEN h.lon-0.01 AND h.lon+0.01)""")
		self.db.commit()
	
	def add_prev_and_next_stop_names(self):
		self.db.execute("""ALTER TABLE osm_stops ADD COLUMN next_stops TEXT""")
		self.db.execute("""ALTER TABLE osm_stops ADD COLUMN prev_stops TEXT""")

		self.db.execute("""UPDATE osm_stops AS g SET next_stops = 
			(SELECT group_concat(o.name,'/') 
			   FROM successor s, osm_stops o 
			  WHERE g.node_id = s.pred_id AND s.succ_id = o.node_id 
              GROUP BY s.pred_id)""")
		self.db.execute("""UPDATE osm_stops AS g SET prev_stops = 
			(SELECT group_concat(o.name,'/') 
			   FROM successor s, osm_stops o 
			  WHERE g.node_id = s.succ_id AND s.pred_id = o.node_id 
			  GROUP BY s.succ_id)""")
		self.db.commit()

	def update_infos_inherited_from_stop_areas(self):
		cur = self.db.execute("""SELECT node_id FROM osm_stops WHERE name IS NULL""")
		stops = cur.fetchall()
		for stop in stops:
			stop_area = self.area_for_stop.get(stop["node_id"])
			if stop_area:
				self.db.execute("""UPDATE osm_stops SET name =? WHERE node_id=?""", (stop_area.get("name"), stop["node_id"]))
		self.db.commit()

	def add_match_state(self):
		self.db.execute("""ALTER TABLE osm_stops ADD COLUMN match_state TEXT""")
		self.db.commit()

	def export_osm_stops(self):
		self.store_osm_stops(self.rows_to_import)
		self.store_successors(self.pred)
		self.add_prev_and_next_stop_names()
		self.update_infos_inherited_from_stop_areas()
		self.only_keep_more_specific_stops_for_matching()
		self.add_match_state()



