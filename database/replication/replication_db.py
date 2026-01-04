import pandas as pd
from peewee import fn, IntegrityError
from typing import Union
from tabulate import tabulate
import logging

from database.base.database_config import initialize_db
from database.base.models import run_replications_table
import database.base.table_config as tc


def store_run_replication(flattened_stats):
    """
     Save replication results to the run_replication_table.

     :param: flattened_stats (List[Dict]): Aggregated statistics with keys
            'Type', 'Name', 'Stat', 'Average', 'Minimum', 'Maximum', 'Half-Width'.
     """

    simulation_id = count_run_replication()

    for entry in flattened_stats:
        try:
            run_replications_table.create(
                simulation_id=simulation_id,
                type=entry[tc.TYPE_COL],
                name=entry[tc.NAME_COL],
                stat=entry[tc.STAT_COL],
                average=entry[tc.AVG_COL] or 0.0,
                minimum=entry[tc.MIN_COL] or 0.0,
                maximum=entry[tc.MAX_COL] or 0.0,
                half_width=entry[tc.HALF_WIDTH_COL] or 0.0
            )
        except IntegrityError as e:
            logging.error(f"store_run_replication: Error saving stats to database: {e}")


def count_run_replication():
    """
    Count replication simulations and return the next replication ID.

    :return: int: The next simulation_id for replication.
    """
    max_id = run_replications_table.select(fn.MAX(run_replications_table.simulation_id)).scalar()
    return (max_id or 0) + 1


def create_pivot_run_replication():
    """
    Generates a pivot table from the run_replication_table and logs the output.

    :return: The pivot table as a pandas DataFrame.
    """
    query = run_replications_table.select(
        run_replications_table.type.alias(tc.TYPE_COL),
        run_replications_table.name.alias(tc.NAME_COL),
        run_replications_table.stat.alias(tc.STAT_COL),
        run_replications_table.average.alias(tc.AVG_COL),
        run_replications_table.minimum.alias(tc.MIN_COL),
        run_replications_table.maximum.alias(tc.MAX_COL),
        run_replications_table.half_width.alias(tc.HALF_WIDTH_COL)
    ).where(run_replications_table.simulation_id == current_replication_id())

    data = pd.DataFrame(list(query.dicts()))

    if data.empty:
        logging.info("No data available in the replication database to generate a pivot table.")
        return None

    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', None)

    pivot_table = data.pivot_table(
        index=tc.PIVOT_INDEX_COLUMNS,
        values=[tc.AVG_COL, tc.MIN_COL, tc.MAX_COL, tc.HALF_WIDTH_COL],
        aggfunc='mean'
    )

    # Initialize variables for tracking redundant values
    previous_row = {tc.TYPE_COL: None, tc.NAME_COL: None, tc.STAT_COL: None}

    # Prepare data for tabulate with redundant value removal
    tabulate_data = []
    for _, row in data.iterrows():

        if previous_row[tc.TYPE_COL] is not None and getattr(row, tc.TYPE_COL) != previous_row[tc.TYPE_COL]:
            tabulate_data.append(["__DIVIDER__"])

        suffix = " min" if any(key in row[tc.STAT_COL] for key in tc.TIME_KEYWORDS) else ""

        tabulate_data.append([
            row[tc.TYPE_COL] if row[tc.TYPE_COL] != previous_row[tc.TYPE_COL] else "",
            row[tc.NAME_COL] if row[tc.NAME_COL] != previous_row[tc.NAME_COL] else "",
            row[tc.STAT_COL] if row[tc.STAT_COL] != previous_row[tc.STAT_COL] else "",
            f"{row[tc.AVG_COL]}{suffix}",
            f"{row[tc.MIN_COL]}{suffix}",
            f"{row[tc.MAX_COL]}{suffix}",
            f"{row[tc.HALF_WIDTH_COL]}{suffix}"
        ])

        # Update previous row tracker
        previous_row[tc.TYPE_COL] = row[tc.TYPE_COL]
        previous_row[tc.NAME_COL] = row[tc.NAME_COL]
        previous_row[tc.STAT_COL] = row[tc.STAT_COL]

    # Create table
    raw_table = tabulate(tabulate_data, headers=tc.REPLICATION_HEADERS, tablefmt=tc.TABLE_FORMAT, colalign=tc.COLUMN_ALIGN_REPLICATION)

    lines = raw_table.splitlines()
    dividing_lines = tc.inject_dividers(lines)

    final_table = "\n".join(dividing_lines)

    print(f"\nReplication ID: {current_replication_id()}")
    print(final_table)

    return pivot_table


def current_replication_id():
    initialize_db()
    max_id = run_replications_table.select(fn.MAX(run_replications_table.simulation_id)).scalar()
    return max_id


def filter_replications(rep_ids: Union[int, list[int]] = current_replication_id(), type: str = None, name: str = None, stat: str = None) -> pd.DataFrame:
    """
    Filter data for one or multiple replications by IDs and optionally by type, name, and stat.

    :param rep_ids: int or list[int] - Single replication ID or list of replication IDs to filter.
    :param type: str (optional) - Filter for the type of data (e.g., 'Entity', 'Server', etc.).
    :param name: str (optional) - Filter for the name of the entity or server.
    :param stat: str (optional) - Filter for the specific statistic to retrieve.
    :return: pd.DataFrame - A pandas DataFrame containing the filtered results.
    """
    # Ensure rep_ids is a list for consistency
    if isinstance(rep_ids, int):
        rep_ids = [rep_ids]

    # Build the base query
    query = run_replications_table.select(
        run_replications_table.simulation_id.alias(tc.REP_ID_COL),
        run_replications_table.type.alias(tc.TYPE_COL),
        run_replications_table.name.alias(tc.NAME_COL),
        run_replications_table.stat.alias(tc.STAT_COL),
        run_replications_table.average.alias(tc.AVG_COL),
        run_replications_table.minimum.alias(tc.MIN_COL),
        run_replications_table.maximum.alias(tc.MAX_COL),
        run_replications_table.half_width.alias(tc.HALF_WIDTH_COL)
    ).where(run_replications_table.simulation_id.in_(rep_ids))

    # Add additional filters if provided
    if type:
        query = query.where(run_replications_table.type == type)
    if name:
        query = query.where(run_replications_table.name == name)
    if stat:
        query = query.where(run_replications_table.stat == stat)

    data = pd.DataFrame(list(query.dicts()))

    # Initialize variables for tracking redundant values
    previous_row = {tc.REP_ID_COL: None, tc.TYPE_COL: None, tc.NAME_COL: None, tc.STAT_COL: None}

    # Prepare data for tabulate with redundant value removal
    tabulate_data = []
    for _, row in data.iterrows():
        tabulate_data.append([
            row[tc.REP_ID_COL] if row[tc.REP_ID_COL] != previous_row[tc.REP_ID_COL] else "",
            row[tc.TYPE_COL] if row[tc.TYPE_COL] != previous_row[tc.TYPE_COL] else "",
            row[tc.NAME_COL] if row[tc.NAME_COL] != previous_row[tc.NAME_COL] else "",
            row[tc.STAT_COL] if row[tc.STAT_COL] != previous_row[tc.STAT_COL] else "",
            row[tc.AVG_COL],
            row[tc.MIN_COL],
            row[tc.MAX_COL],
            row[tc.HALF_WIDTH_COL]
        ])
        # Update previous row tracker
        previous_row[tc.REP_ID_COL] = row[tc.REP_ID_COL]
        previous_row[tc.TYPE_COL] = row[tc.TYPE_COL]
        previous_row[tc.NAME_COL] = row[tc.NAME_COL]
        previous_row[tc.STAT_COL] = row[tc.STAT_COL]

    tabulated_table = tabulate(tabulate_data, headers=tc.FILTER_REPLICATION_HEADERS, tablefmt=tc.TABLE_FORMAT, colalign=tc.COLUMN_ALIGN_FILTER_REPLICATION)

    print(f"\nReplication ID: {rep_ids}")
    print(tabulated_table)

    return data
