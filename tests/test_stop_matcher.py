import unittest

from osm_stop_matcher.StopMatcher import StopMatcher
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
class StopMatcherTest(unittest.TestCase):
	
	def _do_test_rate_platform(self, official_platform_code, osm_assumed_platform_code, expected):
		
		stop = {
			'platform_code': official_platform_code
		}
		osm_stop = {
			'assumed_platform': osm_assumed_platform_code
		}
		matcher = StopMatcher(None)
		actual = matcher.rate_platform(stop, osm_stop)
		self.assertEqual(actual, expected)

	def _do_test_rate_successor(self, gemeinde, ortsteil, name_steig, next_stops, prev_stops, result):
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
		rating = matcher.rate_successor_matching(stop, osm_stop)
		self.assertEqual(rating, result)

	def test_rate_platform(self):
		self._do_test_rate_platform("2", "1", 0.0)
		self._do_test_rate_platform("", "", 0.9)

	def test_rate_successor(self):
		self._do_test_rate_successor("Stuttgart", "", "Ri Stuttgart Niebuhrweg", "Wollinstraße", "Niebuhrweg", -1)
		self._do_test_rate_successor("Stuttgart", "Stuttgart", "Ri Stuttgart Thingstraße", "Am Ochsenwald", "Thingstraße", -1)
		self._do_test_rate_successor("Stuttgart", "Stuttgart", "Ri Stuttgart Am Ochsenwald", "Thingstraße", "Am Ochsenwald", -1)
		self._do_test_rate_successor("Stuttgart", "", "Ri Stuttgart Wurmlinger Straße/Stuttgart Leinfeldener Straße", "Leinfeldener Straße/Wurmlinger Straße", "Reutlinger Straße", 1)
		self._do_test_rate_successor("Stuttgart", "", "Ri Stuttgart Wurmlinger Straße/Stuttgart Leinfeldener Straße", "Leinfeldener Straße/Wurmlinger Straße", "Filderbahnstraße/Rembrandtstraße/Reutlinger Straße", 1)
		self._do_test_rate_successor("Pforzheim", "", "Ri 1.CfR Stadion/Hohlohstraße", "Wohnlichstraße", "1.CfR Stadion", -1)
		self._do_test_rate_successor("Idstein", "Idstein-Wörsdorf ", "Ri Idstein Bahnhof", "Idstein", "Bad Camberg", 0)
		self._do_test_rate_successor("Idstein", "Idstein-Wörsdorf ", "Ri Idstein Bahnhof", "Bad Camberg", "Idstein", 0)
		self._do_test_rate_successor("Crailsheim", "Alexandersreut ", "Ri Jagstheim Burgbergsiedlung/Jagstheim Degenbachsee/Weipertshofen Siedlung", "Ingersheim Bildstraße", "Degenbachsee", -1)

# Execute e.g. via python3 -m unittest tests/test_stop_matcher.py
if __name__ == '__main__':
	unittest.main()