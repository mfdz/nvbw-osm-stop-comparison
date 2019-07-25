import math

def best_unique_matches(candidates, agency_stops = [], matches = [], matched_index = 0, already_matched_osm = []):
	if (len(agency_stops) == 0 ):
		agency_stops_set = set()
		cand_count = 0
		for candidate in candidates:
			cand_count += len(candidates[candidate])
			agency_stops_set.add(candidate)
		agency_stops = list(agency_stops_set)
		if cand_count > 50:
			print("Ignore ",agency_stops, " as too complex for now")
			return (0, [])
	#print(matched_index, agency_stops)
	if matched_index < len(agency_stops):
		stop_candidates = candidates.get(agency_stops[matched_index])
		best_rating = 0
		best_matches = []
		(best_rating, best_matches) = best_unique_matches(candidates, agency_stops, matches.copy(), matched_index+1, already_matched_osm)
		for candidate in stop_candidates:
			candidate_id = candidate["osm_id"]
			if not candidate_id in already_matched_osm:
				(rating, current_matches) = best_unique_matches(candidates, agency_stops, matches.copy()+[candidate], matched_index+1, already_matched_osm+[candidate_id])
				if rating > best_rating:
					best_rating = rating
					best_matches = current_matches
		return (best_rating, best_matches)
	else:
		# All agency stops are matched, calculated rating for this match assmebly
		sum = 0
		if matches:
			for match in matches:
				sum += match['rating']
				#sum += match['rating']
		return (sum, matches)