import csv
from .util import xstr, drop_table_if_exists

class NvbwStopsImporter():
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
			cur.execute("""UPDATE haltestellen SET match_state = 'no_supposed_entry' 
				WHERE lon_Steig IS NULL AND match_state IS NULL AND globaleID_Bereich IS NOT NULL AND lon_Bereich IS NOT NULL 
				  AND CAST(replace(globaleID_Bereich, rtrim(globaleID_Bereich, replace(globaleID_Bereich, ':', '')), '')  AS DECIMAL) >= 10""")
			cur.execute("SELECT InitSpatialMetaData()")
			cur.execute("SELECT AddGeometryColumn('haltestellen', 'the_geom', 4326, 'POINT','XY')")
			cur.execute("UPDATE haltestellen SET the_geom = MakePoint(lon_Steig,lat_Steig, 4326) WHERE lon_Steig is NOT NULL")
			cur.execute("CREATE INDEX id_steig_idx ON haltestellen(globaleID_Steig)")
		
			cur.execute("""CREATE TABLE haltestellen_unified AS
				SElECT Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID, HalteTyp, gueltigAb, gueltigBis, lon, lat, 'Halt' Art , NULL Name_Steig, 
					CASE 
						WHEN Name_Bereich LIKE '%Bus%' THEN 'bus'
						WHEN Name_Bereich LIKE '%Stb.%' OR Name_Bereich LIKE '%Stadtbahn%' THEN 'light_rail'
						WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Steig LIKE '%Gl.%' OR Name_Steig LIKE '%Gleis%' THEN 'train'
						ELSE NULL
					END mode, NULL parent, match_state FROM haltestellen 
				 WHERE lon_Steig IS NULL AND (match_state IS NULL or match_state='matched') AND globaleID IS NOT NULL
				UNION
				SElECT Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID_Bereich, HalteTyp, gueltigAb, gueltigBis, lon_Bereich, lat_Bereich, 'Bereich' Art , NULL Name_Steig, 
					CASE 
						WHEN Name_Bereich LIKE '%Bus%' THEN 'bus' 
						WHEN Name_Bereich LIKE '%Stb.%' OR Name_Bereich LIKE '%Stadtbahn%'THEN 'light_rail'
						WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Steig LIKE '%Gl.%' OR Name_Steig LIKE '%Gleis%' THEN 'train'
						ELSE NULL
					END mode, globaleID parent, match_state FROM haltestellen
				 WHERE lon_Steig IS NULL AND (match_state IS NULL or match_state='matched') AND globaleID_Bereich IS NOT NULL AND lon_Bereich is NOT NULL
				UNION
				SElECT Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID_Steig, HalteTyp, gueltigAb, gueltigBis, lon_Steig, lat_Steig, 'Steig' Art, Name_Steig, 
				CASE 
						WHEN Name_Steig LIKE '%Straßenbahn%' THEN 'tram' 
						WHEN Name_Bereich LIKE '%Bus%' OR Name_Steig LIKE '%Bus%' OR Name_Steig LIKE '%Nachtbus%' THEN 'bus' 
						WHEN Name_Bereich LIKE '%Stb.%' OR Name_Bereich LIKE '%Stadtbahn%' THEN 'light_rail'
						WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Steig LIKE '%Gl.%' OR Name_Steig LIKE '%Gleis%' THEN 'train'
						ELSE NULL
					END mode, globaleID parent, match_state FROM haltestellen 
				 WHERE lon_Steig IS NOT NULL AND globaleID_Steig IS NOT NULL
				   AND (match_state IS NULL or match_state='matched')
			""")
			# Lösche alle nicht zum Ein/Aussteigen genutzten Halte
			cur.execute("DELETE FROM haltestellen_unified WHERE HalteTyp in ('Übergangstarif', 'Zeitposition','EinAusbringer')")
			cur.execute("DELETE FROM haltestellen_unified WHERE globaleID IN (SELECT parent FROM haltestellen_unified)")
			cur.execute("CREATE INDEX id_idx ON haltestellen_unified(globaleID)")
			cur.execute("SELECT AddGeometryColumn('haltestellen_unified', 'the_geom', 4326, 'POINT','XY')")
			cur.execute("UPDATE haltestellen_unified SET the_geom = MakePoint(lon,lat, 4326) WHERE lon is NOT NULL")

			self.db.commit()
