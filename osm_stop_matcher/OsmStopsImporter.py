import logging
import osmium
import re
import shapely.wkb as wkblib
from shapely.geometry import Point
import sys
from osm_stop_matcher.util import  drop_table_if_exists

# A global factory that creates WKB from a osmium geometry
wkbfab = osmium.geom.WKBFactory()


class OsmStopsImporter(osmium.SimpleHandler):
	counter = 0
	pred = {}
	succ = {}
	stop_areas = {}
	area_for_stop = {}
	platform_nodes = []

	def __init__(self, db, osm_file):
		super(OsmStopsImporter,self).__init__()
		self.logger = logging.getLogger('osm_stop_matcher.OsmStopsImporter')
		self.db = db
		self.rows_to_import = [] 
		self.setup_osm_tables()
		self.logger.info("Created osm tables")
		self.apply_file(osm_file, locations=True)
		self.logger.info("Loaded osm data")
		self.export_osm_stops()
		self.logger.info("Exported osm data")
		
	def setup_osm_tables(self):
		drop_table_if_exists(self.db, 'osm_stops')
		self.db.execute('''CREATE TABLE osm_stops
			(osm_id TEXT PRIMARY KEY, name TEXT, network TEXT, operator TEXT, railway TEXT, highway TEXT, public_transport TEXT, lat REAL, lon REAL, 
			 mode TEXT, type TEXT, ref TEXT, ref_key TEXT, assumed_platform TEXT, empty_name INTEGER)''')
		
		drop_table_if_exists(self.db, 'osm_stop_areas')
		self.db.execute('''CREATE TABLE osm_stop_areas
			(osm_id TEXT PRIMARY KEY, name TEXT, network TEXT, operator TEXT,  
			 mode TEXT, ref TEXT, ref_key TEXT)''')

		drop_table_if_exists(self.db, 'osm_stop_area_members')
		self.db.execute('''CREATE TABLE osm_stop_area_members
			(stop_area_id TEXT, member_id TEXT)''')

		drop_table_if_exists(self.db, 'successor')
		self.db.execute('''CREATE TABLE successor
			(pred_id TEXT, succ_id TEXT)''')

		drop_table_if_exists(self.db, 'platform_nodes')
		self.db.execute('''CREATE TABLE platform_nodes
			(way_id TEXT, node_id TEXT)''')

	def node(self, n):
		stop_type = self.extract_stop_type(n.tags)
		if stop_type:
			self.extract_and_store_stop(stop_type, "n" + str(n.id), n.tags, Point(n.location.lon, n.location.lat))

	def way(self, w):
		stop_type = self.extract_stop_type(w.tags)
		if stop_type:
			try:
				wkb = wkbfab.create_linestring(w)
				line = wkblib.loads(wkb, hex=True)	
				location = line.centroid if line.is_ring else line.interpolate(0.5, normalized = True)
				self.extract_and_store_stop(stop_type, "w" + str(w.id), w.tags, location)
				self.cache_platform_nodes(w)
			except AttributeError as err:
				self.logger.error("Error handling way %s: %s %s", w.id, err, w)
	
	def cache_platform_nodes(self, w):
		way_id = "w" + str(w.id)
		for n in w.nodes:
			self.platform_nodes.append((way_id, "n" + str(n.ref)))

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
			0
			))
				
		if self.counter % 100 == 0:
			self.store_osm_stops(self.rows_to_import)
			self.rows_to_import = []

	def relation(self, r):
		if r.tags.get("route"): 
			self.relation_route(r)
		elif r.tags.get("public_transport") == "stop_area":
			self.relation_stop_area(r)

	def relation_route(self, r):
		predecessor = {}
		current = {}
		for m in r.members:
			if m.role in ["platform", "stop"]:
				current[m.role] = m.type + str(m.ref)
				self.cache_predecessor(current[m.role], predecessor.get(m.role))
				predecessor[m.role] = current[m.role]
	
	def cache_predecessor(self, current, predecessor):
		if not predecessor:
			return

		if not current in self.pred:
			self.pred[current] = set()
		if not predecessor in self.succ:
			self.succ[predecessor] = set()
		self.pred[current].add(predecessor)
		self.succ[predecessor].add(current)
		
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
			if m.role in ("platform", "stop"):
				current = m.type + str(m.ref)
				self.area_for_stop[current] = area

	def store_stop_areas(self):
		areas = []
		for key in self.stop_areas:
			area = self.stop_areas[key]
			areas.append((
				area["id"],
				area["name"],
				area["network"], 
				area["operator"],
				area["mode"],
				area["ref_key"],
				area["ref"],
				))

		self.db.executemany('INSERT INTO osm_stop_areas VALUES (?,?,?,?,?,?,?)', areas)
		self.db.commit()

		rows = []
		for key in self.area_for_stop:
			rows.append((
				str(self.area_for_stop[key]["id"]),
				key
				))

		self.db.executemany('INSERT INTO osm_stop_area_members VALUES (?,?)', rows)
		self.db.commit()

	def extract_stop_type(self, tags):
		if tags.get('public_transport') == 'station':
			return 'station' 
		elif tags.get('railway') in ['stop','tram_stop'] or tags.get('public_transport') == 'stop_position':
			return 'stop'
		elif tags.get('highway') == 'bus_stop' or tags.get('public_transport') == 'platform':
			return 'platform'
		elif tags.get('railway') == 'halt':
			return 'halt'
		else:
			return None

	def extract_and_store_stop(self, stop_type, osm_id, tags, location):	
		self.counter += 1
		(ref_key, ref) = self.extract_ref(tags)
		assumed_platform = self.extract_platform(tags)
		stop = {
			"id": osm_id,
			"lat": location.y,
			"lon": location.x,
			"tags": {tag.k: tag.v for tag in tags},
			"mode": self.extract_stop_mode(tags),
			"type": stop_type ,
			"ref": ref,
			"ref_key": ref_key,
			"assumed_platform": assumed_platform
		}

		self.store_osm_stop(stop)
		if self.counter % 10000 == 0:
			self.logger.info("Imported %s stops", self.counter)


	def normalize_IFOPT(self, ifopt):
		return ifopt.lower().replace("de:8", "de:08")

	def extract_stop_mode(self, tags):
		ordered_ref_keys= ["bus","train","tram","light_rail",]
		first_occurrence = None
		for key in ordered_ref_keys:
			if key in tags and tags[key]=='yes':
				if first_occurrence:
					# if ambigous, rather return nothing than wrong
					if first_occurrence == 'bus':
						return None
					else:
						return 'trainish'
				else:
					first_occurrence = key
		if first_occurrence:
			return first_occurrence
		else:
			if tags.get('highway') == 'bus_stop':
				return 'bus'
			elif tags.get('railway'):
				return 'trainish'

	def extract_ref(self, tags):
		ordered_ref_keys= ["ref:IFOPT","ref:pt_id"]
		for key in ordered_ref_keys:
			if key in tags:
				return (key, self.normalize_IFOPT(tags[key]))
		return (None, None)

	def extract_platform(self, tags):
		potential_platform_keys= ["ref","local_ref"]
		for key in potential_platform_keys:
			if key in tags and len(tags[key])<3:
				return tags[key]
		if tags.get("name"):
			numerics = re.findall("\d+", tags["name"])
			if numerics:
				return numerics[-1]
		return None

	def store_osm_stops(self, rows):
		self.db.executemany('INSERT INTO osm_stops VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
		self.db.commit()
		
	def store_platform_nodes(self):
		self.db.executemany("INSERT INTO platform_nodes VALUES (?,?)", self.platform_nodes)
		self.db.commit()

	def store_successors(self, rows):
		rows = []
		for predecessor in self.succ:
			for successor in self.succ[predecessor]:
				rows.append((predecessor, successor))
		self.db.executemany("INSERT INTO successor VALUES (?,?)", rows)
		self.db.commit()

	def only_keep_more_specific_stops_for_matching(self):
		# We ignore stop positions on platforms like n4983922907, n4983922908, n4983924926, n4983924928 (9 occ in bw)
		self.db.execute("""DELETE FROM osm_stops 
			                WHERE osm_id IN (
			                	SELECT node_id 
			                	  FROM platform_nodes) 
							  AND public_transport = 'stop_position'""")

		# We only retain halts where no stop in vicinity and with same name exists.
		self.db.execute("""DELETE FROM osm_stops 
			                WHERE osm_id IN (
								SELECT h.osm_id 
								  FROM osm_stops h, osm_stops s
								 WHERE h.type IN ('halt', 'station')
								   AND h.name = s.name 
								   AND s.type IN ('stop', 'platform') 
								   AND s.mode NOT IN ('bus', 'tram')
								   AND s.lat BETWEEN h.lat-0.01 AND h.lat+0.01 
								   AND s.lon BETWEEN h.lon-0.01 AND h.lon+0.01)""")

		# We delete PTv1 tram_stops (often tagged in center of tram_stops) if there is at least one equally names stop_positiono in the vicinity.
		self.db.execute("""DELETE FROM osm_stops 
							WHERE osm_id IN (
								SELECT h.osm_id
								  FROM osm_stops h, osm_stops s
								 WHERE h.type IN ('stop')
								   AND h.name = s.name 
								   AND s.type IN ('stop') 
								   AND s.mode IN ('tram')
								   AND s.mode IN ('tram', 'trainish') 
								   AND h.mode IN  ('tram', 'trainish')
								   AND h.railway='tram_stop' AND h.public_transport is NULL
								   AND s.public_transport = 'stop_position'
								   AND s.lat BETWEEN h.lat-0.01 AND h.lat+0.01 
								   AND s.lon BETWEEN h.lon-0.01 AND h.lon+0.01)""")

		# We delete stop_positions for buses if there is a platform with the same name in the vicinity.
		self.db.execute("""DELETE FROM osm_stops 
			                WHERE osm_id IN (
								SELECT h.osm_id 
								  FROM osm_stops h, osm_stops s
								 WHERE h.type IN ('stop')
								   AND h.name = s.name 
								   AND s.type IN ('platform') 
								   AND s.mode IN ('bus')
								   AND s.mode = h.mode
								   AND s.lat BETWEEN h.lat-0.01 AND h.lat+0.01 
								   AND s.lon BETWEEN h.lon-0.01 AND h.lon+0.01)""")

		# We delete platforms for trains/lightrails/trams if there is a stop_position with trains/lightrails in the vicinity.
		self.db.execute("""DELETE FROM osm_stops 
			                WHERE osm_id IN (
								SELECT h.osm_id 
								  FROM osm_stops h, osm_stops s
								 WHERE h.type IN ('platform')
								   AND h.name = s.name 
								   AND s.type IN ('stop') 
								   AND s.mode IN ('light_rail', 'train', 'tram', 'trainish')
								   AND h.mode IN ('light_rail', 'train', 'tram', 'trainish')
								   AND s.lat BETWEEN h.lat-0.01 AND h.lat+0.01 
								   AND s.lon BETWEEN h.lon-0.01 AND h.lon+0.01)""")

		# We delete platforms which have already a bus_stop node, which we assign higher priority 
		# (thinking of a bus_station where multiple bus_stops may be assigned to a single platform..)  
		self.db.execute("""DELETE FROM osm_stops WHERE osm_id IN (
								SELECT way_id FROM platform_nodes p, osm_stops b 
								 WHERE p.node_id=b.osm_id)""")

		# We delete bus stop_positions from stop_areas, where there are also platforms with mdoe bus
		self.db.execute("""DELETE FROM osm_stops AS d 
			                WHERE d.mode = 'bus' AND d.type='stop' AND d.osm_id IN (
			                	SELECT s.osm_id 
			                	  FROM osm_stop_area_members mp, osm_stop_area_members ms, osm_stops p, osm_stops s 
								 WHERE mp.member_id = p.osm_id AND p.mode = 'bus' AND p.type = 'platform'
    							   AND ms.member_id = s.osm_id AND s.mode = 'bus' AND s.type='stop'
								   AND ms.stop_area_id = mp.stop_area_id)""")

		self.db.commit()
	
	def add_prev_and_next_stop_names(self):
		self.db.execute("""ALTER TABLE osm_stops ADD COLUMN next_stops TEXT""")
		self.db.execute("""ALTER TABLE osm_stops ADD COLUMN prev_stops TEXT""")
		self.db.execute("""UPDATE osm_stops AS g SET next_stops = 
			(SELECT group_concat(name,'/') FROM (
				SELECT s.pred_id, o.name
				FROM successor s, osm_stops o
				WHERE g.osm_id = s.pred_id AND s.succ_id = o.osm_id
				GROUP BY s.pred_id, o.name)
			GROUP BY pred_id)""")
		self.db.execute("""UPDATE osm_stops AS g SET prev_stops = 
			(SELECT group_concat(name,'/') FROM (
			  SELECT s.succ_id, o.name
			  FROM successor s, osm_stops o
			  WHERE g.osm_id = s.succ_id AND s.pred_id = o.osm_id
			  GROUP BY s.succ_id, o.name)
			GROUP BY succ_id)""")
		self.db.commit()

	def add_column_empty_name(self):
		self.db.execute("""ALTER TABLE osm_stops ADD COLUMN empty_name INTEGER""")
		self.db.commit()

	def deduce_missing_names_from_close_by_stops(self):
		cur = self.db.execute("""
			SELECT osm_id, name, dist FROM (
				SELECT nn.osm_id, wn.name, MIN(abs(wn.lat-nn.lat)+abs(wn.lon-nn.lon)) dist
				FROM osm_stops nn, osm_stops wn
			WHERE nn.name IS NULL
			  AND nn.lat BETWEEN wn.lat-0.001 AND wn.lat+0.001
			  AND nn.lon BETWEEN wn.lon-0.001 AND wn.lon+0.001
			  AND wn.name IS NOT NULL
			  AND (nn.mode = wn.mode 
			    OR (nn.mode = 'trainish' AND wn.mode IN ('rail', 'tram','light_rail'))
			    OR (wn.mode = 'trainish' AND nn.mode IN ('rail', 'tram','light_rail')))
			GROUP BY nn.osm_id, wn.name)
			ORDER BY osm_id, dist""")
		name_candiates = cur.fetchall()
		current = None
		for stop in name_candiates:
			if current != stop["osm_id"]:
				current = stop["osm_id"]
				self.db.execute("""UPDATE osm_stops SET name =?, empty_name=1 WHERE osm_id=?""", (stop["name"], stop["osm_id"]))
		self.db.commit()

	def update_infos_inherited_from_stop_areas_and_platforms(self):
		self.db.execute("""UPDATE osm_stops AS o SET name = 
			(SELECT pw.name FROM platform_nodes p, osm_stops pw 
			  WHERE o.osm_id=p.node_id AND pw.osm_id = p.way_id)
			WHERE o.name IS NULL""")
		self.db.commit()

		cur = self.db.execute("""SELECT osm_id FROM osm_stops WHERE name IS NULL""")
		stops = cur.fetchall()
		for stop in stops:
			stop_area = self.area_for_stop.get(stop["osm_id"])
			if stop_area:
				self.db.execute("""UPDATE osm_stops SET name =? WHERE osm_id=?""", (stop_area.get("name"), stop["osm_id"]))
		self.db.commit()

	def add_match_state(self):
		self.db.execute("""ALTER TABLE osm_stops ADD COLUMN match_state TEXT""")
		self.db.commit()

	def export_osm_stops(self):
		self.store_osm_stops(self.rows_to_import)
		self.store_platform_nodes()
		self.store_stop_areas()
		self.store_successors(self.pred)
		self.add_prev_and_next_stop_names()
		self.update_infos_inherited_from_stop_areas_and_platforms()
		self.deduce_missing_names_from_close_by_stops()
		self.only_keep_more_specific_stops_for_matching()
		self.add_match_state()
