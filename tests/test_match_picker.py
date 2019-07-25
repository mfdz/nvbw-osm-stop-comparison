import unittest

from osm_stop_matcher.MatchPicker import best_unique_matches

class CandidatePickerTest(unittest.TestCase):
	osm1 = {
		"id": 1,
		"lat": 9,
		"lon": 47,
		"tags": {},
		"type": None,
		"ref": None,
		"ref_key": None,
		"assumed_steig": None } 
	osm2 = {
		"id": 2,
		"lat": 9.1,
		"lon": 47.1,
		"tags": {},
		"type": None,
		"ref": None,
		"ref_key": None,
		"assumed_steig": None } 


	def test_one_agency_matching_two_osm__picks_best(self):
		candidates = {
			"A": [{"ifopt_id": "A", "osm_id": 1, "name_distance": 1, "distance": 10, "platform_matches": False, "rating": 0.5},
				{"ifopt_id": "A", "osm_id": 2, "name_distance": 1, "distance": 20, "platform_matches": False, "rating": 0.4},
				]
				}
		agency_stops = ["A"]

		(rating, matches) = best_unique_matches(candidates)

		self.assertEqual(rating, 0.5)

	def test_two_agency_matching_same_osm__picks_best(self):
		candidates = {
			"A": [{"ifopt_id": "A", "osm_id": 1, "name_distance": 1, "distance": 10, "platform_matches": False, "rating": 0.5},],
			"B": [{"ifopt_id": "B", "osm_id": 1, "name_distance": 1, "distance": 10, "platform_matches": False, "rating": 0.4},]
			}

		(rating, matches) = best_unique_matches(candidates)

		self.assertEqual(rating, 0.5)

	def test_two_agency_matching_two_osm_each__picks_best(self):
		candidates = {
			"A": [{"ifopt_id": "A", "osm_id": 1, "name_distance": 1, "distance": 10, "platform_matches": False, "rating": 0.5},
				  {"ifopt_id": "A", "osm_id": 2, "name_distance": 1, "distance": 10, "platform_matches": False, "rating": 0.4},],
			"B": [{"ifopt_id": "B", "osm_id": 1, "name_distance": 1, "distance": 10, "platform_matches": False, "rating": 0.4},
				{"ifopt_id": "B", "osm_id": 2, "name_distance": 1, "distance": 10, "platform_matches": False, "rating": 0.5},]
			}

		(rating, matches) = best_unique_matches(candidates)

		self.assertEqual(rating, 1.0)

	def test_no_candidate__picks_none(self):
		candidates = {
			}

		(rating, matches) = best_unique_matches(candidates)

		self.assertEqual(rating, 0.0)


if __name__ == '__main__':
	unittest.main()