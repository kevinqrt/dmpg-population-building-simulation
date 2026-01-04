import pandas as pd
from peewee import fn, IntegrityError
from typing import Union
from tabulate import tabulate
import logging

from database.base.database_config import initialize_db
from database.base.models import run_simulation_table
from src.core.components.entity import EntityManager
import database.base.table_config as tc


def store_run_simulation(data):
    """
    Store the simulation data in the run_simulation_table.

    :param: data (List[Dict]): Simulation data with keys 'Type', 'Name', 'Stat', and 'Value'.
    """

    simulation_id = count_run_simulation()

    for entry in data:
        entry_value = entry['Value'] if entry['Value'] is not None else tc.DEFAULT_VALUE_IF_NONE
        try:
            run_simulation_table.create(
                simulation_id=simulation_id,
                type=entry[tc.TYPE_COL],
                name=entry[tc.NAME_COL],
                stat=entry[tc.STAT_COL],
                value=entry_value,
            )
        except IntegrityError as e:
            logging.error(f"Error saving to database: {e}")

    EntityManager.destroy_all_entities()


def count_run_simulation():
    """
    Count simulations and return the next simulation ID.

    :return: int: The next simulation_id to use.
    """
    max_id = run_simulation_table.select(fn.MAX(run_simulation_table.simulation_id)).scalar()
    return (max_id or 0) + 1


def create_pivot_run_simulation():
    """
    Generate a pivot table from the database with improved console output formatting.

    - Adds column headers at the top of the table.
    - Avoids printing redundant values in consecutive rows for the same column.

    :return: pandas.DataFrame: Pivot table created from the `run_simulation_table` data.
    """
    query = run_simulation_table.select(
        run_simulation_table.type.alias(tc.TYPE_COL),
        run_simulation_table.name.alias(tc.NAME_COL),
        run_simulation_table.stat.alias(tc.STAT_COL),
        run_simulation_table.value.alias(tc.VALUE_COL)
    ).where(run_simulation_table.simulation_id == current_simulation_id())

    data = pd.DataFrame(list(query.dicts()))

    if data.empty:
        logging.info("No data available in the database to generate a pivot table.")
        return None

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)

    pivot_table = data.pivot_table(
        index=tc.PIVOT_INDEX_COLUMNS,
        values=tc.VALUE_COL,
        aggfunc='mean'
    )

    previous_row = {tc.TYPE_COL: None, tc.NAME_COL: None, tc.STAT_COL: None}

    # Iterate over the rows for formatted console output
    tabulate_data = []
    for row in data.itertuples(index=False):

        if previous_row[tc.TYPE_COL] is not None and getattr(row, tc.TYPE_COL) != previous_row[tc.TYPE_COL]:
            tabulate_data.append(["__DIVIDER__"])

        row_data = []

        for col in [tc.TYPE_COL, tc.NAME_COL, tc.STAT_COL]:
            value = getattr(row, col)
            row_data.append(value if value != previous_row[col] else "")

        # append time units
        suffix = " min" if any(key in row.Stat for key in tc.TIME_KEYWORDS) else ""
        value_formatted = f"{round(row.Value, 4)}{suffix}" if pd.notnull(row.Value) else ""
        row_data.append(value_formatted)

        tabulate_data.append(row_data)

        previous_row[tc.TYPE_COL] = row.Type
        previous_row[tc.NAME_COL] = row.Name
        previous_row[tc.STAT_COL] = row.Stat

    # Create table
    raw_table = tabulate(tabulate_data, headers=tc.SIMULATION_HEADERS, tablefmt=tc.TABLE_FORMAT, colalign=tc.COLUMN_ALIGN_SIMULATION)

    lines = raw_table.splitlines()
    dividing_lines = tc.inject_dividers(lines)

    final_table = "\n".join(dividing_lines)

    # Output
    #print(f"\nSimulation ID: {current_simulation_id()}")
    #print("\n" + final_table)

    return pivot_table


def current_simulation_id():
    initialize_db()
    max_id = run_simulation_table.select(fn.MAX(run_simulation_table.simulation_id)).scalar()
    return max_id


def filter_simulations(simulation_ids: Union[int, list[int]] = current_simulation_id(), type: str = None, name: str = None, stat: str = None) -> pd.DataFrame:
    """
    Filter data for one or multiple simulations by IDs and optionally by type, name, and stat.

    :param simulation_ids: int or list[int] - Single simulation ID or list of simulation IDs to filter.
    :param type: str (optional) - Filter for the type of data (e.g., 'Entity', 'Server', etc.).
    :param name: str (optional) - Filter for the name of the entity or server.
    :param stat: str (optional) - Filter for the specific statistic to retrieve.
    :return: pd.DataFrame - A pandas DataFrame containing the filtered results.
    """
    # Ensure sim_ids is a list for consistency
    if isinstance(simulation_ids, int):
        simulation_ids = [simulation_ids]

    # Build the base query
    query = run_simulation_table.select(
        run_simulation_table.simulation_id.alias(tc.SIM_ID_COL),
        run_simulation_table.type.alias(tc.TYPE_COL),
        run_simulation_table.name.alias(tc.NAME_COL),
        run_simulation_table.stat.alias(tc.STAT_COL),
        run_simulation_table.value.alias(tc.VALUE_COL)
    ).where(run_simulation_table.simulation_id.in_(simulation_ids))

    # Add additional filters if provided
    if type:
        query = query.where(run_simulation_table.type == type)
    if name:
        query = query.where(run_simulation_table.name == name)
    if stat:
        query = query.where(run_simulation_table.stat == stat)

    data = pd.DataFrame(list(query.dicts()))

    # Initialize variables for tracking redundant values
    previous_row = {tc.SIM_ID_COL: None, tc.TYPE_COL: None, tc.NAME_COL: None, tc.STAT_COL: None}

    # Iterate over the rows for formatted console output
    tabulate_data = []
    for row in data.itertuples(index=False):
        # List comprehension to handle redundant value removal
        row_data = [
                       getattr(row, col) if getattr(row, col) != previous_row[col] else ""
                       for col in [tc.SIM_ID_COL, tc.TYPE_COL, tc.NAME_COL, tc.STAT_COL]
                   ] + [getattr(row, tc.VALUE_COL)]

        tabulate_data.append(row_data)

        # Update the previous row tracker
        previous_row[tc.SIM_ID_COL] = getattr(row, tc.SIM_ID_COL)
        previous_row[tc.TYPE_COL] = getattr(row, tc.TYPE_COL)
        previous_row[tc.NAME_COL] = getattr(row, tc.NAME_COL)
        previous_row[tc.STAT_COL] = getattr(row, tc.STAT_COL)

    # tabulated_table = tabulate(tabulate_data, headers=tc.FILTER_SIMULATION_HEADERS, tablefmt=tc.TABLE_FORMAT, colalign=tc.COLUMN_ALIGN_FILTER_SIMULATION)

    # print(f"\nSimulation ID: {simulation_ids}")
    # print(tabulated_table)

    return data
