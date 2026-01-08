from enum import Enum


class AgeGroup(str, Enum):
    CHILDREN = "children"
    WORKING_AGE = "working_age"
    RETIRED = "retired"

class BuildingType(str, Enum):
    RESIDENTIAL = "residential"
    COMPANY = "company"
    
    @property
    def overpass_building_regex(self) -> str:
        """
        Returns the Overpass-compatible regex for the building tag
        corresponding to this BuildingType.
        """

        if self is BuildingType.RESIDENTIAL:
            return r"^(house|detached|semidetached_house|apartments|residential)$"

        if self is BuildingType.COMPANY:
            return r"^(commercial|retail|office|supermarket|industrial|warehouse|factory)$"

        raise ValueError(f"No Overpass regex defined for BuildingType: {self}")
