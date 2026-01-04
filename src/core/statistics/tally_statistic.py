from typing import Optional, Tuple, Union


class TallyStatistic:
    """
    A class to track and calculate statistics for the number of times an entity has been processed.

    Attributes:
        values (list): A list to store the number of times each entity has been processed.
    """
    def __init__(self):
        """
        Initializes a TallyStatistic instance with an empty list.
        """
        self.values = []

    def record(self, value: Union[int, float]):
        """
        Records the number of times an entity has been processed.

        :param value: The number of times an entity has been processed.
        """
        self.values.append(value)

    def calculate_statistics(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculates the minimum, maximum, and average number of times entities have been processed.

        :return: A tuple containing the minimum, maximum, and average values.
                 Returns (None, None, None) if no data is recorded.
        """
        if not self.values:
            return None, None, None
        else:
            min_value = min(self.values)
            max_value = max(self.values)
            avg_value = sum(self.values) / len(self.values)
            return min_value, max_value, avg_value

    def __repr__(self) -> str:
        min_value, max_value, avg_value = self.calculate_statistics()
        return f"min: {min_value}, max: {max_value}, avg: {avg_value}"
