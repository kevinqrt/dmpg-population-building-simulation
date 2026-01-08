"""
Configuration constants and domain assumptions for the population building simulation.
"""

from examples.dmpg.population_building_simulation.helpers import (
    get_osm_population_from_api_or_cached_file,
)


CITY_NAME = "Lingen (Ems)"  # other examples: Lingen (Ems), "Hamburg", "Berlin"
CITY_POPULATION = get_osm_population_from_api_or_cached_file(CITY_NAME)
SIMULATION_DAYS = 30

# Work schedule: 6am - 6pm
WORK_START_HOUR = 6
WORK_END_HOUR = 18

# Work duration: 7-9 hours
WORK_DURATION_MIN = 420  # 7 hours in minutes
WORK_DURATION_MAX = 540  # 9 hours in minutes

# https://www.wegweiser-kommune.de/data-api/rest/report/export/demografiebericht+lingen-ems.pdf
BIRTHS_PER_DAY = 1.5
DEATHS_PER_DAY = 1.75

# =============================================================================
# TALLY STATISTIC NAMES
STAT_WORK_TIME = "work_time"  # Time spent working
STAT_COMMUTES = "daily_commutes"  # Number of commute trips
STAT_COMMUTE_DISTANCE = "commute_distance_km" # Total commute distance in kilometers
STAT_BIRTHS = "births"  # Total births
STAT_DEATHS = "deaths"  # Total deaths
