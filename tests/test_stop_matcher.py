import unittest

from osm_stop_matcher.StopMatcher import StopMatcher

class StopMatcherTest(unittest.TestCase):
	

	def _do_test_rank_successor(self, gemeinde, ortsteil, name_steig, next_stops, prev_stops, result):
		stop = {
			"Gemeinde": gemeinde,
			"Ortsteil": ortsteil,
			"Name_Steig": name_steig
		}
		osm_stop = {
			"next_stops": next_stops,
			"prev_stops": prev_stops
		}

		matcher = StopMatcher(None)
		rating = matcher.rank_successor_matching(stop, osm_stop)
		self.assertEqual(rating, result)


	def test_rank_successor(self):
		self._do_test_rank_successor("Stuttgart", "Stuttgart", "Ri Stuttgart Thingstraße", "Am Ochsenwald", "Thingstraße", -1)
		self._do_test_rank_successor("Stuttgart", "Stuttgart", "Ri Stuttgart Am Ochsenwald", "Thingstraße", "Am Ochsenwald", -1)
		self._do_test_rank_successor("Stuttgart", "", "Ri Stuttgart Wurmlinger Straße/Stuttgart Leinfeldener Straße", "Leinfeldener Straße/Wurmlinger Straße", "Filderbahnstraße/Rembrandtstraße/Reutlinger Straße", 1)

# Execute e.g. via python3 -m unittest tests/test_stop_matcher.py
if __name__ == '__main__':
	unittest.main()