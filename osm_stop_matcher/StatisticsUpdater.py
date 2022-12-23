import logging
from osm_stop_matcher.util import execute_and_ignore_error_if_exists, create_sequence, nextval

class StatisticsUpdater():

	MATCH_STATE_PER_REGION_QUERY = """
        INSERT INTO match_stats(run_id, district, key, value)
        SELECT ? ,substr(globaleID, 0, instr(substr(globaleID||':',4), ':')+3) district, match_state, count(*) value
           FROM haltestellen_unified h
         OUTER LEFT JOIN MATCHES m ON m.ifopt_id = h.globaleId
         GROUP BY substr(globaleID, 0, instr(substr(globaleID||':',4), ':')+3), match_state
        """

	def __init__(self, db):
		self.db = db
		self.logger = logging.getLogger('osm_stop_matcher.StatisticsUpdater')

	def update_match_statistics(self, metadata):
		self.create_stats_tables_if_not_existant()
		run_id = self.retrive_new_run_id()
		self.store_metadata(run_id, metadata)
		self.update_match_states()
		self.persists_stats(run_id)

	def create_stats_tables_if_not_existant(self):
		execute_and_ignore_error_if_exists(self.db, "CREATE TABLE match_meta_data (run_id INTEGER, key TEXT, value TEXT)")
		execute_and_ignore_error_if_exists(self.db, "CREATE TABLE match_stats (run_id INTEGER, district TEXT, key TEXT, value INTEGER)")
		create_sequence(self.db, 'match_runs_seq')
		
		self.db.commit()

	def retrive_new_run_id(self):
		return nextval(self.db, 'match_runs_seq')

	def store_metadata(self, run_id, metadata):
		
		for key in metadata:
			self.db.execute("INSERT INTO match_meta_data VALUES(?, ?, ?)", (run_id, key, str(metadata[key])))
		self.db.execute("INSERT INTO match_meta_data SELECT ?, key, value FROM match_meta_data WHERE run_id=? AND key NOT IN (SELECT key FROM match_meta_data WHERE run_id=?)", (run_id, run_id-1, run_id))
		self.db.commit()

	def persists_stats(self, run_id):
		self.db.execute(self.MATCH_STATE_PER_REGION_QUERY, (run_id,))
		self.db.commit()

	def update_match_states(self):
		self.logger.info('Update statistics')
		self.db.execute("""UPDATE haltestellen_unified 
			                  SET match_state='MATCHED' 
			                WHERE globaleID IN (SELECT ifopt_id FROM matches)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_NAMES_DIFFER' 
			                WHERE globaleID IN (SELECT ifopt_id FROM matches WHERE name_distance < 0.4)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_NO_NAME' 
							WHERE match_state='MATCHED_THOUGH_NAMES_DIFFER' 
							  AND Haltestelle IS NULL AND Haltestelle_lang IS NULL""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_OSM_NO_NAME' 
							WHERE globaleID IN (SELECT ifopt_id FROM matches m, osm_stops o WHERE (o.name IS NULL OR o.empty_name > 0) AND m.osm_id = o.osm_id)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_DISTANT' 
							WHERE globaleID IN (SELECT ifopt_id FROM matches m WHERE distance > 200)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_IMPROBABLE' 
							WHERE globaleID IN (SELECT ifopt_id FROM matches m WHERE rating < 0.002)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_THOUGH_REVERSED_DIR' 
							WHERE globaleID IN (SELECT ifopt_id FROM matches m WHERE successor_rating =-1)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='MATCHED_AMBIGOUSLY' 
							WHERE globaleID IN (SELECT ifopt_id FROM matches GROUP BY ifopt_id HAVING count(*)>1)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='NO_MATCH' 
							WHERE globaleID NOT IN (SELECT ifopt_id FROM matches);""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='NO_MATCH_AND_SEEMS_UNSERVED' 
							WHERE match_state LIKE 'NO_MATCH%' AND linien IS NULL""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='NO_MATCH_BUT_OTHER_PLATFORM_MATCHED' 
							WHERE match_state='NO_MATCH' AND PARENT IN (SELECT h.parent FROM matches m, haltestellen_unified h WHERE m.ifopt_id = h.globaleID)""")
		self.db.execute("""UPDATE haltestellen_unified SET match_state='NO_MATCH_NO_IFOPT' 
							WHERE globaleID IS NULL""")

		self.db.execute("""UPDATE osm_stops SET match_state = 'MATCHED' 
			                WHERE osm_id IN (SELECT osm_id FROM matches)""")
		self.db.execute("""UPDATE osm_stops SET match_state='MATCHED_THOUGH_NAMES_DIFFER' 
			                WHERE osm_id IN (SELECT osm_id FROM matches WHERE name_distance < 0.4)""")
		self.db.execute("""UPDATE osm_stops SET match_state='MATCHED_THOUGH_OSM_NO_NAME' 
			                WHERE (name IS NULL OR empty_name > 0) AND osm_id  IN (SELECT osm_id FROM matches m )""")
		self.db.execute("""UPDATE osm_stops SET match_state='MATCHED_THOUGH_DISTANT' 
			                WHERE osm_id IN (SELECT osm_id FROM matches m WHERE distance > 200)""")
		self.db.execute("""UPDATE osm_stops SET match_state='MATCHED_THOUGH_IMPROBABLE' 
			                WHERE osm_id IN (SELECT osm_id FROM matches WHERE rating < 0.002)""")
		self.db.execute("""UPDATE osm_stops SET match_state = 'NO_MATCH' 
			                WHERE osm_id NOT IN (SELECT osm_id FROM matches)""")
		self.logger.info('Updated statistics')
		
		self.db.commit()