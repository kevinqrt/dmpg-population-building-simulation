import cProfile
import pstats
from database.base.models import db
from dmpg_logs.trace_logging.setup_logging import setup_logging
from examples.dmpg.population_building_simulation.main import setup_city_model
from examples.dmpg.population_building_simulation import config
from examples.dmpg.population_building_simulation.components.building_model import Building
from src.core.components.date_time import DateTime
from src.core.simulation.simulation import run_simulation


def profile_simulation():
    print("PROFILE SCRIPT IS RUNNING")

    setup_logging(log_puffer=True, log_gps=True)

    if db.is_closed():
        db.connect()

    db.create_tables([Building], safe=True)

    profiler = cProfile.Profile()
    profiler.enable()

    run_simulation(
        model=setup_city_model,
        steps=DateTime.map_time_to_steps(days=config.SIMULATION_DAYS),
    )

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.dump_stats("simulation.prof")
    print("PROFILE WRITTEN")

    if not db.is_closed():
        db.close()



if __name__ == "__main__":
    profile_simulation()
