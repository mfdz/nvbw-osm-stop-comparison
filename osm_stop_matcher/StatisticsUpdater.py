import logging

class StatisticsUpdater():
	def __init__(self, db):
		self.db = db
		self.logger = logging.getLogger('osm_stop_matcher.StatisticsUpdater')

	def update_match_statistics(self):
		self.logger.info('Update statistics')
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

		self.db.execute("""UPDATE osm_stops SET match_state = 'MATCHED' 
			                WHERE node_id IN (SELECT osm_id FROM matches)""")
		self.db.execute("""UPDATE osm_stops SET match_state='MATCHED_THOUGH_NAMES_DIFFER' 
			                WHERE node_id IN (SELECT osm_id FROM matches WHERE name_distance < 0.3 AND rating > 0.002)""")
		self.db.execute("""UPDATE osm_stops SET match_state='MATCHED_THOUGH_OSM_NO_NAME' 
			                WHERE name IS NULL AND node_id  IN (SELECT osm_id FROM matches m )""")
		self.db.execute("""UPDATE osm_stops SET match_state='MATCHED_THOUGH_DISTANT' 
			                WHERE node_id IN (SELECT osm_id FROM matches m WHERE distance > 200 AND rating > 0.002)""")
		self.db.execute("""UPDATE osm_stops SET match_state = 'NO_MATCH' 
			                WHERE node_id NOT IN (SELECT osm_id FROM matches)""")
		self.logger.info('Updates statistics')
		
		self.db.commit()