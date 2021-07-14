import unittest

from osm_stop_matcher.StopMatcher import StopMatcher

class StopMatcherTest(unittest.TestCase):
	

	def _do_test_rank_successor(self, ortsteil, name_steig, next_stops, prev_stops, result):
		stop = {
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
		self._do_test_rank_successor("Stuttgart", "Ri Stuttgart Thingstraße", "Am Ochsenwald", "Thingstraße", -1)
		self._do_test_rank_successor("Stuttgart", "Ri Stuttgart Am Ochsenwald", "Thingstraße", "Am Ochsenwald/Am Ochsenwald", -1)



if __name__ == '__main__':
	unittest.main()