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
