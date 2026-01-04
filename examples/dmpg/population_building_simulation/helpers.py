import math
from typing import Any
from pyparsing import Path
import requests
from examples.dmpg.population_building_simulation import config
from examples.dmpg.population_building_simulation.components.building_model import Building
from src.core.components.model import Model
from src.core.components.work_schedule import WorkScheduleDay, WorkScheduleWeek


def create_work_schedule() -> WorkScheduleWeek:
    """Create a weekly work schedule (6am - 6pm every day)."""

    def _create_workday() -> WorkScheduleDay:
        day = WorkScheduleDay()
        day.set_time(config.WORK_START_HOUR, 0, config.WORK_END_HOUR, 0)
        return day

    return WorkScheduleWeek(
        monday=_create_workday(),
        tuesday=_create_workday(),
        wednesday=_create_workday(),
        thursday=_create_workday(),
        friday=_create_workday(),
        saturday=_create_workday(),
        sunday=_create_workday(),
    )

def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate the great-circle distance between two points on the Earth
    specified in decimal degrees using the Haversine formula.

    :param lat1: Latitude of point 1
    :param lon1: Longitude of point 1
    :param lat2: Latitude of point 2
    :param lon2: Longitude of point 2
    :return: Distance in kilometers
    """
    # Earth radius in kilometers
    R = 6371.0

    # Convert degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
    
def get_osm_population_from_api_or_cached_file(city_name: str) -> int:
    """
    Fetches population data for a city from the Overpass API, only if stored file not found.
    """

    file_path = Path(__file__).resolve().parent / "interfaces" / f"population_{city_name}.txt"
    
    # Check cached file first
    if file_path.is_file():
        with open(file_path, "r", encoding="utf-8") as f:
            population = int(f.read().strip())
        return population

    # Fetch from Overpass API
    url = "https://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json][timeout:50];

    area
      ["ISO3166-1"="DE"]
      ["boundary"="administrative"]
      ->.germany;

    relation
      ["name"="{city_name}"]
      ["boundary"="administrative"]
      (area.germany)
      ->.cityRel;

    .cityRel out tags;
    """

    response = requests.get(url, params={"data": overpass_query})
    if response.status_code != 200:
        raise RuntimeError(
            f"Overpass API request failed with {response.status_code}"
        )

    data = response.json()

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        population = tags.get("population")
        if population:
            try:
                population = int(population.replace(" ", ""))
                with open(Path(__file__).resolve().parent / "interfaces" / f"population_{city_name}.txt", "w", encoding="utf-8") as f:
                    f.write(str(population))
                return population
            except ValueError:
                return None
    return None

def print_results() -> None:
    """Print simulation results in a readable format."""
    print("\n" + "=" * 70)
    print("CITY POPULATION SIMULATION - RESULTS")
    print("=" * 70)

    # Configuration
    print(f"\n{'CONFIGURATION':-^70}")
    print(f"  Simulation Duration:    {config.SIMULATION_DAYS} days")
    print(f"  Start Population:       {config.CITY_POPULATION:,}")
    print("  Final Population:      ", Model().get_state("population"))
    print(f"  Number of Living Houses:       {len(Building.get_living_buildings()):,}")
    print(f"  Number of Workplaces:   {len(Building.get_workplace_buildings()):,}")

    print(
        f"  Work Hours:             {config.WORK_START_HOUR}:00 - {config.WORK_END_HOUR}:00"
    )
    print(
        f"  Shift Duration:         {config.WORK_DURATION_MIN // 60}-{config.WORK_DURATION_MAX // 60} hours"
    )

    # Demographics
    demographics: Any = Model().get_state("demographics")
    worker_count: Any = Model().get_state("worker_count")

    print(f"\n{'DEMOGRAPHICS':-^70}")
    print(
        f"  Children (0-17):        {demographics['children']:,} ({demographics['children'] / config.CITY_POPULATION * 100:.1f}%)"
    )
    print(
        f"  Working Age (18-64):    {demographics['working_age']:,} ({demographics['working_age'] / config.CITY_POPULATION * 100:.1f}%)"
    )
    print(
        f"  Retired (65+):          {demographics['retired']:,} ({demographics['retired'] / config.CITY_POPULATION * 100:.1f}%)"
    )
    print(f"  Active Workers:         {worker_count:,}")

    # Birth/Death statistics
    print(f"\n{'POPULATION DYNAMICS':-^70}")
    birth_stats = Model().get_tally_statistics(config.STAT_BIRTHS)
    death_stats = Model().get_tally_statistics(config.STAT_DEATHS)

    total_births = sum(birth_stats.values) if birth_stats and birth_stats.values else 0
    total_deaths = sum(death_stats.values) if death_stats and death_stats.values else 0
    net_change = total_births - total_deaths

    print(f"  Total Births:           {total_births:,}")
    print(f"  Total Deaths:           {total_deaths:,}")
    print(f"  Net Population Change:  {net_change:+,}")

    births_per_day = total_births / config.SIMULATION_DAYS
    deaths_per_day = total_deaths / config.SIMULATION_DAYS

    print(f"  Births per Day:         {births_per_day:.2f}")
    print(f"  Deaths per Day:         {deaths_per_day:.2f}")
    print("  Youngest Death:        ", int(Model().get_tally_statistics("death_age").calculate_statistics()[0]))
    print("  Oldest Death:          ", int(Model().get_tally_statistics("death_age").calculate_statistics()[1]))
    print("  Avg Death:             ", round(Model().get_tally_statistics("death_age").calculate_statistics()[2], 1))

    # Workplace statistics
    print(f"\n{'WORKPLACE STATISTICS':-^70}")
    total_shifts = 0
    shifts_list: list[int] = []
    for building in Building.get_workplace_buildings():
        workplace = Model().get_component_by_name(f"Workplace({str(building)})")
        if workplace:
            shifts = int(workplace.total_entities_processed_pivot_table)
            total_shifts += shifts
            shifts_list.append(shifts)

    # Show individual workplaces only if <= 10, otherwise show summary
    if len(Building.get_workplace_buildings()) <= 10:
        for i, shifts in enumerate(shifts_list):
            print(f"  Workplace_{i}:            {shifts:,} shifts completed")
        print(f"  {'-' * 40}")
    else:
        # Summary for large number of workplaces
        avg_per_workplace = sum(shifts_list) / len(shifts_list) if shifts_list else 0
        min_shifts = min(shifts_list) if shifts_list else 0
        max_shifts = max(shifts_list) if shifts_list else 0
        print(f"  Workplaces:             {len(Building.get_workplace_buildings()):,}")
        print(
            f"  Shifts per Workplace:   {avg_per_workplace:.1f} avg ({min_shifts}-{max_shifts} range)"
        )
        print(f"  {'-' * 40}")

    avg_shifts_per_day = (
        total_shifts / config.SIMULATION_DAYS if config.SIMULATION_DAYS > 0 else 0
    )
    print(f"  Total Shifts:           {total_shifts:,}")
    print(f"  Average Shifts/Day:     {avg_shifts_per_day:.1f}")

    # Work time statistics
    print(f"\n{'WORK TIME STATISTICS':-^70}")
    work_stats = Model().get_tally_statistics(config.STAT_WORK_TIME)
    if work_stats:
        min_val, max_val, avg_val = work_stats.calculate_statistics()
        if avg_val is not None:
            print(
                f"  Average Shift Duration: {avg_val:.1f} min ({avg_val / 60:.1f} hours)"
            )
            print(
                f"  Shortest Shift:         {min_val:.1f} min ({min_val / 60:.1f} hours)"
            )
            print(
                f"  Longest Shift:          {max_val:.1f} min ({max_val / 60:.1f} hours)"
            )
        else:
            print("  No work time data recorded")

    # Commute statistics
    commute_stats = Model().get_tally_statistics(config.STAT_COMMUTES)
    if commute_stats:
        min_c, max_c, avg_c = commute_stats.calculate_statistics()
        total_commutes = (
            commute_stats.get_count()
            if hasattr(commute_stats, "get_count")
            else total_shifts
        )
        if total_commutes:
            commutes_per_day = total_commutes / config.SIMULATION_DAYS
            print(f"\n{'COMMUTE STATISTICS':-^70}")
            print(f"  Total Commutes:         {total_commutes:,}")
            print(f"  Commutes per Day:       {commutes_per_day:.1f}")
            if worker_count > 0:
                commutes_per_worker = total_commutes / worker_count
                print(
                    f"  Avg Commutes/Worker:    {commutes_per_worker:.1f} (over {config.SIMULATION_DAYS} days)"
                )

    commute_distance = Model().get_tally_statistics(config.STAT_COMMUTE_DISTANCE)
    if not commute_distance:
        print("Keine Pendelstatistiken vorhanden.")
        return

    min_d, max_d, avg_d = commute_distance.calculate_statistics()
    print(f"\n{'INITIAL STATE STATISTICS – COMMUTING DISTANCE HOME TO WORK':-^70}")
    print(f"  Min.:         {min_d:.2f} km")
    print(f"  Max.:         {max_d:.2f} km")
    print(f"  Average:      {avg_d:.2f} km")

    print("\n" + "=" * 70)

