from peewee import Model, SqliteDatabase, MySQLDatabase
from peewee import IntegerField, CharField, FloatField, AutoField, DateField, TimeField
import logging
import src.core.config as cfg
from datetime import date, datetime
from peewee import DateTimeField

logging.basicConfig(level=logging.INFO)
global credentials

# Use config system for database setting
if cfg.in_memory_db:
    db = SqliteDatabase(":memory:")
else:
    # Check if we have MySQL configuration in the config
    db_config = cfg.logging.get('database', {})

    if 'mysql' in db_config:
        credentials = db_config['mysql']
        db = MySQLDatabase(credentials["name"],
                           user=credentials["user"],
                           password=credentials["password"],
                           host=credentials["host"],
                           port=credentials.get("port", 3306))
    else:
        # Default to SQLite file if no MySQL config
        db = SqliteDatabase('simulation.db')


class BaseModel(Model):
    class Meta:
        database = db


class run_simulation_table(BaseModel):
    id = AutoField()
    type = CharField(null=False)
    name = CharField(null=False)
    stat = CharField(null=False)
    value = FloatField(default=0.0, null=False)
    simulation_id = IntegerField()
    date = DateField(default=date.today)
    time = TimeField(default=datetime.now().time)


class run_replications_table(BaseModel):
    id = AutoField()
    type = CharField(null=False)
    name = CharField(null=False)
    stat = CharField(null=False)
    average = FloatField(default=0.0, null=False)
    minimum = FloatField(default=0.0, null=False)
    maximum = FloatField(default=0.0, null=False)
    half_width = FloatField(default=0.0, null=False)
    simulation_id = IntegerField(null=False)


class entity_type_stats_table(BaseModel):
    id = AutoField()
    simulation_id = IntegerField()
    component_type = CharField()
    component_name = CharField()
    stat = CharField()
    entity_type = CharField()
    value = FloatField(default=0.0)


class entity_type_stats_table_replications(BaseModel):
    simulation_id = IntegerField()
    replication_id = IntegerField()
    component_type = CharField()
    component_name = CharField()
    stat = CharField()
    entity_type = CharField()
    value = FloatField()
    timestamp = DateTimeField(default=datetime.now())
