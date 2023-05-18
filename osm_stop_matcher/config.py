# Below this (empircally found) value, only very few associations are probable matches 
RATING_BELOW_CANDIDATES_ARE_IGNORED = 0.04

# To avoid combinatorial explosition when calculating best match combination per stop, 
# we only consider the best candidate per osm_stop if a certain number of candidates is exceeded
MAX_CANDIDATE_COUNT_PER_STOP_BEFORE_ONLY_BEST_PER_QUAY_ARE_CONSIDERED = 50

MINIMUM_NAME_SIMILARITY = 0.3
MAXIMUM_DISTANCE = 400
UNKNOWN_MODE_RATING = 0.7
SIMPLE_MATCH_PICKER = False