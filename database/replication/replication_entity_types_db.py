import pandas as pd
import numpy as np
import logging
from peewee import IntegrityError
from tabulate import tabulate
from scipy.stats import t, norm

import database.base.table_config as tc
from src.core.utils.helper import round_value
from database.base.models import entity_type_stats_table_replications, run_replications_table
from database.replication.replication_db import current_replication_id
from database.simulation.simulation_db import current_simulation_id
from src.core.components.entity import EntityManager


def store_entity_type_stats_replications(formatted_data: list, replication_id: int):
    simulation_id = current_simulation_id()

    logging.info(EntityManager.entity_types_list)

    rows = []
    for row in formatted_data:
        base = {
            'simulation_id': simulation_id,
            'replication_id': replication_id,
            'component_type': row['Type'],
            'component_name': row['Name'],
            'stat': row['Stat']
        }

        for entity_type in EntityManager.entity_types_list:
            if entity_type in row:
                rows.append({
                    **base,
                    'entity_type': entity_type,
                    'value': round_value(row[entity_type])
                })

    if rows:
        try:
            entity_type_stats_table_replications.insert_many(rows).execute()
        except IntegrityError as e:
            logging.error(f"Entity-Type-Replication-Save-Error: {e}")


def create_table_entity_types_replication(etype_df: pd.DataFrame = None, confidence=0.95):
    sim_id = current_replication_id()

    # run_replication stats from database
    base_query = run_replications_table.select().where(run_replications_table.simulation_id == sim_id)
    base_df = pd.DataFrame(list(base_query.dicts()))

    # Data from database as an option
    if etype_df is None:
        etype_query = entity_type_stats_table_replications.select().where(
            entity_type_stats_table_replications.simulation_id == sim_id)
        etype_df = pd.DataFrame(list(etype_query.dicts()))

    if base_df.empty or etype_df.empty:
        print("No data available.")
        return

    etype_df = pd.melt(
        etype_df,
        id_vars=["Type", "Name", "Stat", "Value"],
        var_name="entity_type",
        value_name="value"
    )

    # Rename
    etype_df.rename(columns={
        "Type": "component_type",
        "Name": "component_name",
        "Stat": "stat"
    }, inplace=True)

    # Aggregiere EntityType-Stats
    def summarize(values, confidence=0.95):
        arr = pd.Series(values)
        n = len(arr)
        avg = arr.mean()
        min_ = arr.min()
        max_ = arr.max()
        std_dev = arr.std(ddof=1)

        if n <= 1:
            hw = 0
        elif n > 30:
            hw = norm.ppf((1 + confidence) / 2) * (std_dev / np.sqrt(n))
        else:
            hw = t.ppf((1 + confidence) / 2, df=n - 1) * (std_dev / np.sqrt(n))

        return avg, min_, max_, hw

    rows = []
    grouped = etype_df.groupby(["component_type", "component_name", "stat", "entity_type"])["value"]
    for (comp_type, comp_name, stat, etype), values in grouped:
        avg, min_, max_, hw = summarize(values, confidence)
        rows.append({
            "type": comp_type,
            "name": comp_name,
            "stat": stat,
            f"{etype}_Average": avg,
            f"{etype}_Min": min_,
            f"{etype}_Max": max_,
            f"{etype}_HalfWidth": hw
        })

    entity_df = pd.DataFrame(rows)

    if not entity_df.empty:
        entity_df = entity_df.groupby(["type", "name", "stat"]).agg('first').reset_index()

    # Merge
    merged = pd.merge(base_df, entity_df, on=["type", "name", "stat"], how="left")

    merged.drop(columns=[col for col in ["id", "simulation_id"] if col in merged.columns], inplace=True)

    # Header
    base_cols = ["type", "name", "stat", "average", "minimum", "maximum", "half_width"]
    etype_cols = [col for col in merged.columns if col not in base_cols]

    headers = ["Type", "Name", "Stat", "Average", "Min", "Max", "Half-Width"] + etype_cols
    colalign = ["left", "left", "left"] + ["right"] * (len(headers) - 3)

    previous_row = {"type": None, "name": None, "stat": None}
    tabulate_data = []

    for row in merged.itertuples(index=False):
        if previous_row["type"] is not None and getattr(row, "type") != previous_row["type"]:
            tabulate_data.append(["__DIVIDER__"])

        r = row._asdict()
        line = [
            r["type"] if r["type"] != previous_row["type"] else "",
            r["name"] if r["name"] != previous_row["name"] else "",
            r["stat"] if r["stat"] != previous_row["stat"] else "",
        ]

        # Format base metrics
        for col in ["average", "minimum", "maximum", "half_width"]:
            val = r.get(col)
            suffix = " min" if any(key in r["stat"] for key in tc.TIME_KEYWORDS) else ""
            line.append(f"{round(val, 4)}{suffix}" if pd.notnull(val) else "")

        # Format entity-type metrics
        for col in etype_cols:
            val = r.get(col)
            suffix = " min" if any(key in r["stat"] for key in tc.TIME_KEYWORDS) else ""
            line.append(f"{round(val, 4)}{suffix}" if pd.notnull(val) else "")

        tabulate_data.append(line)
        previous_row = {"type": r["type"], "name": r["name"], "stat": r["stat"]}

    raw_table = tabulate(tabulate_data, headers=headers, tablefmt=tc.TABLE_FORMAT, colalign=colalign)

    lines = raw_table.splitlines()
    dividing_lines = tc.inject_dividers(lines)

    final_table = "\n".join(dividing_lines)

    print(f"\nReplication ID: {sim_id} — Aggregated Stats + EntityType Columns\n")

    print(final_table)
