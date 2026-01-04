import sys
import simpy
from dmpg_logs.trace_logging.setup_logging import setup_logging
from examples.dmpg.population_building_simulation import config
from examples.dmpg.population_building_simulation import helpers
from examples.dmpg.population_building_simulation.components.building_model import Building
from examples.dmpg.population_building_simulation.db import db
from examples.dmpg.population_building_simulation.world_builder import WorldBuilder
from src.core.components.date_time import DateTime
from src.core.components.model import Model
from src.core.simulation.simulation import run_simulation
from examples.dmpg.population_building_simulation.components.birth_source import BirthSource
from examples.dmpg.population_building_simulation.components.death_sink import DeathSink


def setup_city_model(env: simpy.Environment) -> None:
    """
    Build the city simulation model.

    Architecture:
    - Houses (Storage): Hold citizens, put workers in workplace queues
    - Workplaces (Server): Pull workers during operating hours, process (work), send home
    - Pull System: StorageManager coordinates worker queues between houses and workplaces
    """

    # Register tally statistics
    Model().add_tally_statistic(config.STAT_WORK_TIME)
    Model().add_tally_statistic(config.STAT_COMMUTES)
    Model().add_tally_statistic(config.STAT_COMMUTE_DISTANCE)
    Model().add_tally_statistic(config.STAT_BIRTHS)
    Model().add_tally_statistic(config.STAT_DEATHS)
    Model().add_tally_statistic("death_age")

    world = WorldBuilder(env)
    world.build_storage_queues()


    # Create and distribute population
    houses = world.get_houses()
    Model().add_state("population", config.CITY_POPULATION)
    Model().add_state("humans", [])
    world.build_workplaces()
    age_groups, workers_count = world.populate(houses)

    # Create DeathSink for handling deaths
    death_sink = DeathSink(env, name="DeathSink")

    # Create BirthSource with DeathSink for daily births/deaths
    BirthSource(env, name="BirthSource", houses=houses, death_sink=death_sink)

    # Store demographics for later reporting
    Model().add_state("demographics", age_groups)
    Model().add_state("worker_count", workers_count)


def main() -> None:
    setup_logging(log_puffer=True, log_gps=True)

    db.connect()
    db.create_tables([Building], safe=True)

    sys.stdout = open("population_building_simulation_output.txt", "w")

    """Run the city population simulation."""
    print("\n" + "=" * 70)
    print("CITY POPULATION SIMULATION")
    print("=" * 70)


    run_simulation(
        model=setup_city_model,
        steps=DateTime.map_time_to_steps(days=config.SIMULATION_DAYS),
    )

    helpers.print_results()


if __name__ == "__main__":
    main()
