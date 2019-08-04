import osmium
from osm_stop_matcher.util import  drop_table_if_exists


class OsmStopsImporter(osmium.SimpleHandler):
	counter = 0


	def __init__(self, db, osm_file):
		super(OsmStopsImporter,self).__init__()
		self.db = db
		self.rows_to_import = [] 
		
		self.setup_osm_tables()
		self.apply_file(osm_file)
		self.export_osm_stops()
		
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



