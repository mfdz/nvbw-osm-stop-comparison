import csv
import datetime
from .util import to_iso_date_format, xstr, drop_table_if_exists
import logging

logger = logging.getLogger('DelfiStopsImporter')

class DelfiStopsImporter():
	

	def __init__(self, connection):
		self.db = connection
		
	def import_stops(self, stops_file):
		drop_table_if_exists(self.db, "zhv")
		cur = self.db.cursor()
		cur.execute("""CREATE TABLE zhv (SeqNo, Type, DHID, Parent, Name, 
			Latitude REAL, Longitude REAL, MunicipalityCode, Municipality, DistrictCode, District, Description,
			Authority, DelfiName, THID, TariffProvider, LastOperationDate)""")

		with open(stops_file,'r',encoding='utf-8-sig') as csvfile:
			dr = csv.DictReader(csvfile, delimiter=';', quotechar='"')
			to_db = [(
				xstr(row['SeqNo']), 
				xstr(row['Type']), 
				xstr(row['DHID']),
				xstr(row['Parent']),
				xstr(row['Name']),
				float(row['Latitude'].replace(',','.')) if row['Latitude'] else None,
				float(row['Longitude'].replace(',','.')) if row['Longitude'] else None, 
				xstr(row['MunicipalityCode']),
				xstr(row['Municipality']),
				xstr(row['DistrictCode']),
				xstr(row['District']),
				xstr(row['Description']),
				xstr(row['Authority']),
				xstr(row['DelfiName']),
				xstr(row['THID']),
				xstr(row['TariffProvider']),
				# convert '31.12.1999 00:00:00' to '1999-31-12'
				to_iso_date_format(row['LastOperationDate'])
				) for row in dr]
			logger.info("Loaded stops from DELF zHV")
			cur.executemany("""INSERT INTO zhv (SeqNo, Type, DHID, Parent, Name, 
			Latitude, Longitude, MunicipalityCode, Municipality, DistrictCode, District, Description,
			Authority, DelfiName, THID, TariffProvider, LastOperationDate) VALUES (?{})""".format(",?"*16), to_db)
			logger.info("Inserted stops into table zhv")

		cur.execute("SELECT InitSpatialMetaData()")
		cur.execute("SELECT AddGeometryColumn('zhv', 'the_geom', 4326, 'POINT','XY')")
		cur.execute("UPDATE zhv SET the_geom = MakePoint(Longitude,Latitude, 4326) WHERE Longitude is NOT NULL")
		logger.info("Updated zhv.geom")
		cur.execute("CREATE INDEX id_steig_idx ON zhv(DHID)")

	def load_haltestellen_unified(self):
		drop_table_if_exists(self.db, "haltestellen_unified")
		cur = self.db.cursor()
	
		cur.execute("""CREATE TABLE haltestellen_unified AS 
			SELECT s.District Landkreis, s.Municipality Gemeinde, LTRIM(SUBSTR(REPLACE(s.Name,',',' '), 1, instr(REPLACE(s.Name,',',' '),' '))) Ortsteil, LTRIM(SUBSTR(REPLACE(s.Name,',',' '), instr(REPLACE(s.Name,',',' '),' '))) Haltestelle, s.Name Haltestelle_lang, q.description Haltebeschreibung, q.dhid GlobaleId, '' HalteTyp, '' gueltigAb, '' gueltigBis, q.Latitude lat, q.Longitude lon, 'Steig' Art, '' Name_Steig, '' mode, q.parent parent, '' match_state, NULL linien, '' platform_code from zhv s JOIN zhv q ON q.parent=s.dhid WHERE q.type ='Q' AND s.type='S'
			UNION ALL
			SELECT s.District Landkreis, s.Municipality Gemeinde, LTRIM(SUBSTR(REPLACE(s.Name,',',' '), 1, instr(REPLACE(s.Name,',',' '),' '))) Ortsteil, LTRIM(SUBSTR(REPLACE(s.Name,',',' '), instr(REPLACE(s.Name,',',' '),' '))) Haltestelle, s.Name Haltestelle_lang, q.description Haltebeschreibung, q.dhid GlobaleId, '' HalteTyp, '' gueltigAb, '' gueltigBis, q.Latitude lat, q.Longitude lon, 'Steig' Art, '' Name_Steig, '' mode, s.dhid parent, '' match_state, NULL linien, '' platform_code from zhv s JOIN zhv a ON a.parent=s.dhid JOIN zhv q ON q.parent=a.dhid WHERE q.type ='Q' AND a.type='A' AND s.type='S'
			UNION ALL
			SELECT s.District Landkreis, s.Municipality Gemeinde, LTRIM(SUBSTR(REPLACE(s.Name,',',' '), 1, instr(REPLACE(s.Name,',',' '),' '))) Ortsteil, LTRIM(SUBSTR(REPLACE(s.Name,',',' '), instr(REPLACE(s.Name,',',' '),' '))) Haltestelle, s.Name Haltestelle_lang, s.description Haltebeschreibung, s.dhid GlobaleId, '' HalteTyp, '' gueltigAb, '' gueltigBis, s.Latitude lat, s.Longitude lon, 'Halt' Art, '' Name_Steig, '' mode, NULL parent, '' match_state, NULL linien, '' platform_code from zhv s WHERE s.type='S' AND s.dhid NOT IN (SELECT a.parent FROM zhv q JOIN zhv a ON q.parent=a.dhid WHERE q.type='Q')""")
		logger.info("Created table haltestellen_unified")
		# Remove Zugang/Ersatzverkehre (=Unserved?)
		cur.execute("DELETE FROM haltestellen_unified WHERE Haltebeschreibung LIKE '%Zugang%' OR Haltebeschreibung LIKE '%Ersatz%' " )
		cur.execute("CREATE INDEX id_idx ON haltestellen_unified(globaleID)")
		cur.execute("SELECT AddGeometryColumn('haltestellen_unified', 'the_geom', 4326, 'POINT','XY')")
		cur.execute("UPDATE haltestellen_unified SET the_geom = MakePoint(lon,lat, 4326) WHERE lon is NOT NULL")
		logger.info("Updated table haltestellen_unified.geom, .ortsteil and .haltestelle")
		self.db.commit()
		self.patch_names_and_settlement()

	def patch_names_and_settlement(self):
		cur = self.db.cursor()
		cur.execute("""UPDATE haltestellen_unified 
						  SET ortsteil=substr(haltestelle_lang, 0, INSTR(haltestelle_lang, ',')),
						      haltestelle = substr(haltestelle_lang, INSTR(haltestelle_lang, ',')+2)
						WHERE ortsteil in ('Bad ') 
							  AND INSTR(haltestelle_lang, ',')>0 """)
		cur.execute("""UPDATE haltestellen_unified
						  SET ortsteil=substr(haltestelle_lang, 0, instr(substr(haltestelle_lang,5),' ')+4),
						      haltestelle = substr(haltestelle_lang, instr(substr(haltestelle_lang,5),' ')+5)
						WHERE ortsteil in ('Bad ') AND INSTR(haltestelle_lang, ',') = 0 
						  AND instr(substr(haltestelle_lang,5),' ')>0""")

		# For stop names with comma, we use a heuristic to determine, if the settlement is before or after the comma:
		drop_table_if_exists(self.db, "tmp_name_parts_variance")
		cur.execute("""
			CREATE TABLE tmp_name_parts_variance AS 
		    WITH hastellennamen AS
				(SELECT substr(Globaleid, 1,8) kreis, Haltestelle_lang, 
					    substr(Haltestelle_lang, 1,instr(h.haltestelle_lang, ',')-1) vor_komma, 
					    trim(substr(Haltestelle_lang, instr(h.haltestelle_lang, ',')+1)) nach_komma 
				   FROM haltestellen_unified h),
			separierte_hastellennamen AS
				(SELECT *
				   FROM hastellennamen h
				  WHERE instr(h.haltestelle_lang,',')>0)

            SELECT substr(g.kreis,4) ags, g.kreis, anzahl_vor_komma, anzahl_nach_komma, 
		      1000 * anzahl_vor_komma/(anzahl_vor_komma+anzahl_nach_komma) promille_vor_komma, anzahl_mit_komma, anzahl_gesamt, 100*anzahl_mit_komma/anzahl_gesamt prozent_mit_komma
		      FROM (SELECT kreis, count(*) anzahl_gesamt 
		      	      FROM hastellennamen
		      	     GROUP BY kreis) g
			  LEFT OUTER JOIN  
			       (SELECT kreis, count(*) anzahl_mit_komma 
		      	      FROM separierte_hastellennamen 
		      	     GROUP BY kreis) mk
			    ON g.kreis=mk.kreis
			  LEFT OUTER JOIN  
			       (SELECT kreis, count(nach_komma) anzahl_nach_komma 
		      	      FROM (SELECT kreis, nach_komma 
		      	      	     FROM separierte_hastellennamen 
		      	      	    GROUP BY nach_komma, kreis) 
		      	     GROUP BY kreis) nk
			    ON g.kreis=nk.kreis
			  LEFT OUTER JOIN 
			       (SELECT kreis, count(vor_komma) anzahl_vor_komma 
			       	  FROM (SELECT kreis, vor_komma 
			       	  	      FROM separierte_hastellennamen 
			       	  	     GROUP BY  vor_komma, kreis) 
			       	 GROUP BY kreis) vk
		        ON g.kreis=vk.kreis
		      """)
		
		cur.execute("""
			UPDATE haltestellen_unified
			   SET ortsteil = substr(Haltestelle_lang, 1,instr(haltestelle_lang, ',')-1),
				   haltestelle = trim(substr(Haltestelle_lang, instr(haltestelle_lang, ',')+1))
			 WHERE substr(GlobaleId,1,8) IN (SELECT kreis FROM tmp_name_parts_variance WHERE promille_vor_komma < 650) 
			   AND instr(haltestelle_lang,',')>0""")
		cur.execute("""
			UPDATE haltestellen_unified
			   SET haltestelle= substr(Haltestelle_lang, 1,instr(haltestelle_lang, ',')-1),
				   ortsteil = trim(substr(Haltestelle_lang, instr(haltestelle_lang, ',')+1))
			 WHERE substr(GlobaleId,1,8) IN (SELECT kreis FROM tmp_name_parts_variance WHERE promille_vor_komma >= 650) 
			   AND instr(haltestelle_lang,',')>0""")
		self.db.commit()

	def patch_haltestellen_unified(self):
		None
