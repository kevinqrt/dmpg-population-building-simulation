from pathlib import Path
from peewee import SqliteDatabase

DB_PATH = Path("population_building_simulation.db")

if DB_PATH.exists():
    DB_PATH.unlink()

db = SqliteDatabase(DB_PATH)