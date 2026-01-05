from examples.dmpg.population_building_simulation.enums import BuildingType
from examples.dmpg.population_building_simulation.components.building_model import Building


def test_get_osm_houses_from_api():
    """
    Integration test:
    - Executes one real Overpass query
    - Verifies that the call does not raise
    """

    city_name = "Lingen (Ems)"
    building_type = BuildingType.RESIDENTIAL

    Building.get_osm_houses_from_api(
        city_name=city_name,
        building_type=building_type,
    )
    # python -m examples.dmpg.population_building_simulation.tests


if __name__ == "__main__":
    test_get_osm_houses_from_api()