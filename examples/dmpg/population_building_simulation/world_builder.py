from cmath import isnan
import random
from pyparsing import Path
import simpy

from examples.dmpg.population_building_simulation import config, helpers
from examples.dmpg.population_building_simulation.components.human_entity import Human
from examples.dmpg.population_building_simulation.enums import AgeGroup
from examples.dmpg.population_building_simulation.components.house_storage import House
from examples.dmpg.population_building_simulation.components.workplace_server import Workplace
from examples.dmpg.population_building_simulation.components.building_model import Building
from src.core.components.logistic.storage_manager import StorageManager
from src.core.components.model import Model


class WorldBuilder:
    """
    Responsible for constructing all world components (houses, workplaces, population, ...).
    """

    def __init__(self, env: simpy.Environment) -> None:
        self.env = env
        Building.save_in_db(Path(__file__).resolve().parent / "interfaces" / "wohngebaeude_lingen.json", isOSMData=True)
        Building.save_in_db(Path(__file__).resolve().parent / "interfaces" / "unternehmen_lingen.json", isOSMData=False)
        
        self.living_used_buildings: list[Building] = Building.get_living_buildings()
        self.commercial_used_buildings: list[Building] = Building.get_workplace_buildings()
    def get_houses(self) -> list[House]:
        """
        Create house storages for the population. People only live in houses.
        """
        houses: list[House] = []
        for building in self.living_used_buildings:
            house = House(
                env=self.env,
                name=f"LivingHouses({str(building)})",
                capacity=(
                    config.CITY_POPULATION // len(self.living_used_buildings) + 5
                ),  # How many people can live in the house
                building=building,
            )

            houses.append(house)
        return houses

    def populate(self, houses: list[House]) -> tuple[dict[AgeGroup, int], int]:
        """Generate population, assign homes & workplaces, fill houses."""

        workers_count = 0
        age_groups: dict[AgeGroup, int] = {
            AgeGroup.CHILDREN: 0,
            AgeGroup.WORKING_AGE: 0,
            AgeGroup.RETIRED: 0,
        }

        number_buildings = len(self.living_used_buildings)

        for i in range(config.CITY_POPULATION):
            human = Human(f"Human_{i}", self.env.now)
            assert isinstance(
                human, Human
            )  # Required for type checkers: Entity.__new__ may return dynamic types

            house_id = human.assign_home(i, number_buildings)
            # Set home_name to the actual house component name (not the index-based name)
            human.home_name = houses[house_id].name
            age_groups[human.age_group] += 1
            Model().get_state("humans").append(human)

            if human.age_group == AgeGroup.WORKING_AGE:
                # Assign workplace (distribute evenly)
                workplace_idx = workers_count % len(self.commercial_used_buildings)
                human.workplace_name = f"Workplace({str(self.commercial_used_buildings[workplace_idx])})"
                self._record_initial_commute_distance(human)
                workers_count += 1

            # Place in house
            houses[house_id].handle_entity_arrival(human)

        return age_groups, workers_count

    def build_workplaces(self) -> list[Workplace]:
        """
        Create workplaces (pull workers during operating hours)
        """

        work_schedule = helpers.create_work_schedule()
        workplaces: list[Workplace] = []
        for building in self.commercial_used_buildings:
            workplace = Workplace(
                self.env,
                name=f"Workplace({str(building)})",
                processing_time_distribution_with_parameters=(
                    random.uniform,
                    config.WORK_DURATION_MIN,
                    config.WORK_DURATION_MAX,
                ),
                capacity=100,  # Each workplace can handle 100 workers
                building=building,
                storage_queue=f"Workplace({str(building)})",
                work_schedule=work_schedule,
            )
            workplaces.append(workplace)
        return workplaces

    def build_storage_queues(self) -> None:
        """
        Create all storage queues needed in the world.
        """

        # Initialize StorageManager with environment
        StorageManager.env = self.env

        # Workplace queues
        for building in self.commercial_used_buildings:
            StorageManager.add_storage_queue(f"Workplace({str(building)})")

        # Special home queue
        StorageManager.add_storage_queue("stay_home")

    @staticmethod
    def _record_initial_commute_distance(human: Human) -> None:
        # COMMUTE DISTANCE
        if human.home_name and human.workplace_name:
            home: House = Model().get_component_by_name(human.home_name)
            workplace: House = Model().get_component_by_name(human.workplace_name)
            if home and home.building.lat is not None and workplace.building.lat is not None:
                dist = helpers.haversine_distance_km(
                    home.building.lat,
                    home.building.lon,
                    workplace.building.lat,
                    workplace.building.lon,
                )
                if not isnan(dist):
                    Model().record_tally_statistic(
                        config.STAT_COMMUTE_DISTANCE,
                        dist,
                    )
