import unittest

from database.base.database_config import initialize_db, drop_db
from database.base.models import run_simulation_table, run_replications_table, db
from database.simulation.simulation_db import current_simulation_id, filter_simulations
from database.replication.replication_db import current_replication_id, filter_replications, count_run_replication


class TestCases(unittest.TestCase):

    def test_create_tables(self):
        initialize_db()
        tables = db.get_tables()
        assert 'run_simulation_table' in tables, "Table 'run_simulation_table' not created!"
        assert 'run_replications_table' in tables, "Table 'run_replications_table' not created!"
        print("Tables successfully created.")

    def test_insert_into_run_simulation_table(self):
        drop_db()
        initialize_db()
        run_simulation_table.create(
            type="Server",
            name="Server1",
            stat="AvgTime",
            value=3.14,
            simulation_id=1
        )
        result = run_simulation_table.select().where(run_simulation_table.simulation_id == 1).get()
        assert result.type == "Server"
        assert result.name == "Server1"
        assert result.stat == "AvgTime"
        assert result.value == 3.14
        print("Data successfully inserted into 'run_simulation_table'.")

    def test_insert_into_run_replications_table(self):
        drop_db()
        initialize_db()
        run_replications_table.create(
            type="Entity",
            name="Entity1",
            stat="MaxTime",
            average=4.56,
            minimum=2.34,
            maximum=6.78,
            half_width=0.5,
            simulation_id=2
        )
        result = run_replications_table.select().where(run_replications_table.simulation_id == 2).get()
        assert result.type == "Entity"
        assert result.name == "Entity1"
        assert result.stat == "MaxTime"
        assert result.average == 4.56
        assert result.minimum == 2.34
        assert result.maximum == 6.78
        assert result.half_width == 0.5
        print("Data successfully inserted into 'run_replications_table'.")

    @classmethod
    def setUpClass(cls):
        """
        Set up the database and create the tables for testing.
        """
        # Create tables for testing
        run_simulation_table.create_table()
        run_replications_table.create_table()

    def setUp(self):
        """
        Populate the database with test data before each test.
        """
        # Insert data into run_simulation_table
        run_simulation_table.insert_many([
            {"simulation_id": 1, "type": "Server", "name": "Machine1", "stat": "Idle Time", "value": 10.5},
            {"simulation_id": 1, "type": "Server", "name": "Machine1", "stat": "Processing Time", "value": 20.0},
            {"simulation_id": 1, "type": "Server", "name": "Machine2", "stat": "Idle Time", "value": 5.0},
            {"simulation_id": 2, "type": "Source", "name": "JobSource", "stat": "Entities Created", "value": 50.0},
        ]).execute()

        # Insert data into run_replications_table
        run_replications_table.insert_many([
            {"simulation_id": 1, "type": "Server", "name": "Machine1", "stat": "Idle Time", "average": 10.5,
             "minimum": 8.0, "maximum": 15.0, "half_width": 2.5},
            {"simulation_id": 1, "type": "Server", "name": "Machine1", "stat": "Processing Time", "average": 20.0,
             "minimum": 18.0, "maximum": 22.0, "half_width": 1.0},
            {"simulation_id": 2, "type": "Source", "name": "JobSource", "stat": "Entities Created", "average": 50.0,
             "minimum": 48.0, "maximum": 52.0, "half_width": 1.0},
        ]).execute()

    def tearDown(self):
        """
        Clear the database after each test to ensure isolation.
        """
        run_simulation_table.delete().execute()
        run_replications_table.delete().execute()

    def test_filter_simulations(self):
        """
        Test the `filter_simulations` function.
        """
        data = filter_simulations(simulation_ids=1)
        self.assertEqual(len(data), 3)  # Three entries for Simulation ID 1
        self.assertIn("Machine1", data["Name"].values)

    def test_filter_replications(self):
        """
        Test the `filter_replications` function.
        """
        data = filter_replications(rep_ids=1)
        self.assertEqual(len(data), 2)  # Two entries for Replication ID 1
        self.assertIn("Machine1", data["Name"].values)

    def test_current_simulation_id(self):
        """
        Test the `current_simulation_id` function.
        """
        self.assertEqual(current_simulation_id(), 2)  # Last Simulation ID

    def test_current_replication_id(self):
        """
        Test the `current_replication_id` function.
        """
        self.assertEqual(current_replication_id(), 2)  # Last Replication ID

    def test_count_replication(self):
        """
        Test the `count_replication` function.
        """
        self.assertEqual(count_run_replication(), 3)  # Three replications in the table

    def test_filter_simulations_combined_filters(self):
        """
        Test `filter_simulations` with multiple filters applied.
        """
        data = filter_simulations(simulation_ids=1, type="Server", name="Machine1", stat="Idle Time")
        self.assertEqual(len(data), 1)  # Only one entry should match
        self.assertEqual(data.iloc[0]["Value"], 10.5)

    def test_filter_replications_combined_filters(self):
        """
        Test `filter_replications` with multiple filters applied.
        """
        data = filter_replications(rep_ids=1, type="Server", name="Machine1", stat="Idle Time")
        self.assertEqual(len(data), 1)  # Only one entry should match
        self.assertEqual(data.iloc[0]["Average"], 10.5)

    @classmethod
    def tearDownClass(cls):
        """
        Drop the tables after all tests are completed.
        """
        run_simulation_table.drop_table()
        run_replications_table.drop_table()
