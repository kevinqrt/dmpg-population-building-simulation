import pytest

from examples.dmpg.population_building_simulation.enums import BuildingType
from examples.dmpg.population_building_simulation.components.building_model import Building


@pytest.mark.integration
def test_get_osm_houses_from_api_residential_berlin():
    """
    Integration test:
    - Executes one real Overpass query
    - Verifies that the call does not raise
    """

    city_name = "Hamburg"
    building_type = BuildingType.COMPANY

    Building.get_osm_houses_from_api(
        city_name=city_name,
        building_type=building_type,
    )
    # pytest examples/dmpg/population_building_simulation/tests.py


