class MatchResultValidator():
	def __init__(self, db):
		self.db = db

	def check_matched(self, ifopt_id, osm_id):
		cur = self.db.execute("SELECT * FROM matches WHERE ifopt_id=? AND osm_id = ?", [ifopt_id, osm_id])
		if not len(cur.fetchall())>0:
			print("ERROR: Expected match is missing: {}->{}".format(ifopt_id, osm_id))

	def check_not_matched(self, ifopt_id, osm_id):
		cur = self.db.execute("SELECT * FROM matches WHERE ifopt_id=? AND osm_id = ?", [ifopt_id, osm_id])
		if not len(cur.fetchall())==0:
			print("ERROR: Got unexpected match for: {}->{}".format(ifopt_id, osm_id))

	def check_not_to_match(self, osm_id):
		cur = self.db.execute("SELECT * FROM osm_stops WHERE osm_id=? ", [osm_id])
		if not len(cur.fetchall())==0:
			print("ERROR: Got unexpected osm_stop to match for: {}".format(osm_id))

	def check_assertions(self):
		self.check_matched('de:08311:30822:0:5', 'n4391668851')
		# Ensingen Feuerwehrmagazin.  kein Candidat. Mutmaßlich schlechterer Wert für Name Distance?	
		self.check_matched('de:08118:5920:0:3','n6158905230')
		# Gutach Freilichtmuseum. rating 0, da NVBW keinen Namen liefert (insgesamt 1395 Halte)
		# Nachvollziehbar, aber dass stop_position auf Bus geht nicht...
		self.check_matched('de:08317:18733:1:1', 'n3207442779')

		self.check_matched('de:08231:488:0:1', 'n1564906436')
		self.check_not_matched('de:08231:488:0:1', 'n310744136')
		
		# Karl-Abt-Straße even no candidate
		self.check_matched('de:08231:487:0:1','n310744136')
		# Rohr ist mit Steigen vorhanden, desh
		self.check_not_matched('de:08111:6001','n301614772')
		# Rohe Pestalozzischule
		self.check_matched('de:08111:6015:0:3','n271653920') # Albblick
		self.check_not_matched('de:08111:6015:0:3','n271654026')
		self.check_matched('de:08111:6015:0:4','n271654026') # Waldburgstra
		self.check_not_matched('de:08111:6015:0:4','n271653920') # Waldburgstra
		self.check_not_to_match('n872587831')
		# issue:  Lnie 43 Rtg Rotebühlplatz not recognized as successor
		self.check_matched('de:08111:55:3:4', 'n272067913') # Berliner Platz (Hohe Straße)
		# issue: we do not inherit names for node bus_stops from their platform, so we have to stops instead of one
		self.check_not_to_match('n6551589907') # Rotebühlplatz (bus_stop is part of platform)

		self.check_matched('de:08111:6157:4:2', 'n717575086') # Feuerbach Stadtbahn

		self.check_matched('de:08226:4252:3:2','n3188450069') # Wiesloch Walldorf (mode nvbw nicht erkannt)
