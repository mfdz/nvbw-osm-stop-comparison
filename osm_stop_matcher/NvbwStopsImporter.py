import csv
import datetime
from .util import xstr, drop_table_if_exists

def reformat_date(date):
	if date:
		return str(datetime.datetime.strptime(date, '%d.%m.%Y').date())

class NvbwStopsImporter():
	def __init__(self, connection):
		self.db = connection
		
	def import_stops(self, stops_file):
		drop_table_if_exists(self.db, "haltestellen")
		cur = self.db.cursor()
		cur.execute("""CREATE TABLE haltestellen (Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, 
			HalteBeschreibung, globaleID, HalteTyp, gueltigAb, gueltigBis, lat REAL, lon REAL, Name_Bereich, globaleID_Bereich,
			gueltigAbBereich, gueltigBisBereich,  
			lat_Bereich REAL, lon_Bereich REAL, Name_Steig, globaleID_Steig, 
			gueltigAbSteig, gueltigBisSteig, lat_Steig REAL, lon_Steig REAL,  
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
				xstr(reformat_date(row['gueltigAb'])),
				xstr(reformat_date(row['gueltigBis'])),
				float(row['lat']) if row['lat'] else None,
				float(row['lon']) if row['lon'] else None, 
				xstr(row['Name_Bereich']),
				xstr(row['globaleID_Bereich']), 
				xstr(reformat_date(row.get('gueltigAbBereich'))),
				xstr(reformat_date(row.get('gueltigBisBereich'))),
				float(row['lat_Bereich']) if row['lat_Bereich'] else None, 
				float(row['lon_Bereich']) if row['lon_Bereich'] else None, 
				xstr(row['Name_Steig']),
				xstr(row['globaleID_Steig']),
				xstr(reformat_date(row.get('gueltigAbSteig'))),
				xstr(reformat_date(row.get('gueltigBisSteig'))),
				float(row['lat_Steig']) if row['lat_Steig'] else None, 
				float(row['lon_Steig']) if row['lon_Steig'] else None, 
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
					HalteBeschreibung, globaleID, HalteTyp, gueltigAb, gueltigBis, lat, lon, Name_Bereich, globaleID_Bereich, 
					gueltigAbBereich, gueltigBisBereich, lat_Bereich, lon_Bereich, Name_Steig, globaleID_Steig, 
					gueltigAbSteig, gueltigBisSteig, lat_Steig, lon_Steig, 
					Fuss_Verbindung, Fahrrad_Verbindung, Individualverkehr_Verbindung, Bus_Verbindung, Strassenbahn_Verbindung, 
					Schmalspurbahn_Verbindung, Eisenbahn_Verbindung, Faehren_Verbindung) VALUES (?{})""".format(",?"*31), to_db)

		# workaround https://github.com/mfdz/nvbw-haltestellen-issues/issues/25
		cur.execute("UPDATE haltestellen SET gueltigBis = NULL WHERE gueltigBis = Date('1970-01-01')")
		cur.execute("UPDATE haltestellen SET gueltigBisSteig = NULL WHERE gueltigBisSteig = Date('1970-01-01')")
		cur.execute("UPDATE haltestellen SET gueltigBisBereich = NULL WHERE gueltigBisBereich = Date('1970-01-01')")
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
		cur.execute("CREATE INDEX id_halt_idx ON haltestellen(globaleID)")
		cur.execute("CREATE INDEX id_steig_idx ON haltestellen(globaleID_Steig)")
		
	def load_haltestellen_unified(self):
		drop_table_if_exists(self.db, "haltestellen_unified")
		cur = self.db.cursor()
		cur.execute("""CREATE TABLE haltestellen_unified AS
			SElECT Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID, HalteTyp, gueltigAb, gueltigBis, lat, lon, 'Halt' Art , NULL Name_Steig, 
				CASE 
					WHEN Name_Bereich LIKE '%Bus%' THEN 'bus'
					WHEN Name_Bereich LIKE '%Stb.%' OR Name_Bereich LIKE '%Stadtbahn%' THEN 'light_rail'
					WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Steig LIKE '%Gl.%' OR Name_Steig LIKE '%Gleis%' THEN 'train'
					ELSE NULL
				END mode, NULL parent, match_state, '' linien FROM haltestellen 
			 WHERE lon_Steig IS NULL AND (match_state IS NULL or match_state='matched') AND globaleID IS NOT NULL
			   AND (gueltigBis IS NULL OR gueltigBis >= Date('now'))
			UNION
			SElECT Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID_Bereich, HalteTyp, gueltigAbBereich, gueltigBisBereich, lat_Bereich, lon_Bereich, 'Bereich' Art , NULL Name_Steig, 
				CASE 
					WHEN Name_Bereich LIKE '%Bus%' THEN 'bus' 
					WHEN Name_Bereich LIKE '%Stb.%' OR Name_Bereich LIKE '%Stadtbahn%'THEN 'light_rail'
					WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Steig LIKE '%Gl.%' OR Name_Steig LIKE '%Gleis%' THEN 'train'
					ELSE NULL
				END mode, globaleID parent, match_state, '' linien FROM haltestellen
			 WHERE lon_Steig IS NULL AND (match_state IS NULL or match_state='matched') AND globaleID_Bereich IS NOT NULL AND lon_Bereich is NOT NULL
			   AND (gueltigBis IS NULL OR gueltigBIS >= Date('now'))
			   AND (gueltigBisBereich IS NULL OR gueltigBisBereich >= Date('now'))
			UNION
			SElECT Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang, HalteBeschreibung, globaleID_Steig, HalteTyp, gueltigAbSteig, gueltigBisSteig, lat_Steig, lon_Steig, 'Steig' Art, Name_Steig, 
			CASE 
					WHEN Name_Steig LIKE '%Straßenbahn%' THEN 'tram' 
					WHEN Name_Bereich LIKE '%Bus%' OR Name_Steig LIKE '%Bus%' OR Name_Steig LIKE '%Bstg%' OR Name_Steig LIKE '%Nachtbus%' THEN 'bus' 
					WHEN Name_Bereich LIKE '%Stb.%' OR Name_Bereich LIKE '%Stadtbahn%' THEN 'light_rail'
					WHEN Name_Bereich LIKE '%Bahn%' OR Name_Bereich LIKE '%Gleis%' OR Name_Steig LIKE '%Gl.%' OR Name_Steig LIKE '%Gleis%' THEN 'train'
					ELSE NULL
				END mode, globaleID parent, match_state, '' linien FROM haltestellen 
			 WHERE lon_Steig IS NOT NULL AND globaleID_Steig IS NOT NULL
			   AND (match_state IS NULL or match_state='matched')
			   AND (gueltigBis IS NULL OR gueltigBIS >= Date('now'))
			   AND (gueltigBisBereich IS NULL OR gueltigBisBereich >= Date('now'))
			   AND (gueltigBisSteig IS NULL OR gueltigBisSteig >= Date('now'))
		""")
		# Lösche alle nicht zum Ein/Aussteigen genutzten Halte
		cur.execute("DELETE FROM haltestellen_unified WHERE HalteTyp in ('Zeitposition','EinAusbringer')")
		cur.execute("DELETE FROM haltestellen_unified WHERE globaleID IN (SELECT parent FROM haltestellen_unified)")
		cur.execute("CREATE INDEX id_idx ON haltestellen_unified(globaleID)")
		cur.execute("SELECT InitSpatialMetaData()")
		cur.execute("SELECT AddGeometryColumn('haltestellen_unified', 'the_geom', 4326, 'POINT','XY')")
		cur.execute("UPDATE haltestellen_unified SET the_geom = MakePoint(lon,lat, 4326) WHERE lon is NOT NULL")
		cur.execute("UPDATE haltestellen_unified SET parent = (SELECT h.globaleId FROM haltestellen h WHERE h.globaleId_Steig=haltestellen_unified.globaleId)")
		self.db.commit()

	def patch_haltestellen_unified(self):
		"""
			Patches haltestellen_unified, i.e. 
		"""
		cur = self.db.cursor()
		cur.execute("""UPDATE haltestellen_unified SET (Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang) =
			(SELECT Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang 
			   FROM haltestellen h WHERE h.globaleID=haltestellen_unified.globaleId)
			WHERE haltestellen_unified.globaleId IN (SELECT globaleID FROM haltestellen)""")
		cur.execute("""UPDATE haltestellen_unified SET (Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang) =
			(SELECT Landkreis, Gemeinde, Ortsteil, Haltestelle, Haltestelle_lang 
			   FROM haltestellen h WHERE h.globaleID_Steig=haltestellen_unified.globaleId)
			WHERE haltestellen_unified.globaleId IN (SELECT globaleID_Steig FROM haltestellen)""")

		self.db.commit()

