import pandas as pd

# global
DECIMAL_PLACES = ".4f"
TABLE_FORMAT = "github"
DEFAULT_WAIT_TIMEOUT = 1
DEFAULT_VALUE_IF_NONE = 0.0
PIVOT_INDEX_COLUMNS = ['Type', 'Name', 'Stat']

# simulation
SIMULATION_HEADERS = ["Type", "Name", "Stat", "Value"]
FILTER_SIMULATION_HEADERS = ["Sim ID", "Type", "Name", "Stat", "Value"]
TIME_KEYWORDS = ["TimeInSystem", "TimeProcessing", "TimeInQueue", "TravelTime", "StarvingTime"]
COLUMN_ALIGN_SIMULATION = ["left", "left", "left", "right"]
COLUMN_ALIGN_FILTER_SIMULATION = ["left", "left", "left", "left", "right"]
TYPE_COL = "Type"
NAME_COL = "Name"
STAT_COL = "Stat"
VALUE_COL = "Value"
SIM_ID_COL = "Simulation_ID"

# replication
REPLICATION_HEADERS = ["Type", "Name", "Stat", "Average", "Minimum", "Maximum", "Half-Width"]
FILTER_REPLICATION_HEADERS = ["Rep ID", "Type", "Name", "Stat", "Average", "Minimum", "Maximum", "Half-Width"]
COLUMN_ALIGN_REPLICATION = ["left", "left", "left", "right", "right", "right", "right"]
COLUMN_ALIGN_FILTER_REPLICATION = ["left", "left", "left", "left", "right", "right", "right", "right"]
AVG_COL = "Average"
MIN_COL = "Minimum"
MAX_COL = "Maximum"
HALF_WIDTH_COL = "Half-Width"
REP_ID_COL = "Replication_ID"


# append time-units
class DisplayFormatter:
    @staticmethod
    def append_time_unit(stat: str, value: float) -> str:
        """Fügt bei Zeitbezogenen Statistiken ein 'min' an."""
        suffix = " min" if any(key in stat for key in TIME_KEYWORDS) else ""
        return f"{round(value, 4)}{suffix}" if pd.notnull(value) else ""


def inject_dividers(lines: list[str], divider_placeholder: str = "__DIVIDER__") -> list[str]:
    """
    Replaces placeholder lines (e.g., '__DIVIDER__') with a full-width horizontal rule
    based on the existing table layout (like tabulate github-style headers).

    :param lines: List of string lines from a tabulated table.
    :param divider_placeholder: The placeholder string that should be replaced.
    :return: List of lines with horizontal rules inserted.
    """
    # Find a line that consists of only '-' and '|' (i.e., the header line)
    full_line = next((line for line in lines if set(line.strip()) <= {"-", "|"}), None)
    fallback_line = "-" * max(len(line) for line in lines)
    full_rule = full_line if full_line else fallback_line

    # Replace all placeholders with the rule
    return [full_rule if divider_placeholder in line else line for line in lines]
