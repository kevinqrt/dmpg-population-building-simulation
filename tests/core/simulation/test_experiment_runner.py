import unittest
import pandas as pd
from unittest.mock import MagicMock, patch

from src.core.simulation.experiments.experiment import ScenarioParameter, Scenario, ExperimentRunner
from src.core.simulation.experiments.parameter_manager import ParameterizedModel, parameterize_model


class TestScenarioParameter(unittest.TestCase):
    """Test cases for the ScenarioParameter class."""

    def test_init_default_description(self):
        """Test initialization with default description."""
        param = ScenarioParameter('arrival_rate', 0.5)
        self.assertEqual(param.name, 'arrival_rate')
        self.assertEqual(param.value, 0.5)
        self.assertEqual(param.description, 'Parameter arrival_rate')

    def test_init_custom_description(self):
        """Test initialization with custom description."""
        param = ScenarioParameter('service_time', 3.0, 'Service time in minutes')
        self.assertEqual(param.name, 'service_time')
        self.assertEqual(param.value, 3.0)
        self.assertEqual(param.description, 'Service time in minutes')

    def test_repr(self):
        """Test string representation."""
        param = ScenarioParameter('arrival_rate', 0.5)
        self.assertEqual(repr(param), 'ScenarioParameter(arrival_rate=0.5)')

    def test_various_value_types(self):
        """Test parameter with various value types."""
        # Integer value
        param = ScenarioParameter('capacity', 2)
        self.assertEqual(param.value, 2)

        # String value
        param = ScenarioParameter('queue_type', 'FIFO')
        self.assertEqual(param.value, 'FIFO')

        # List value
        param = ScenarioParameter('server_list', ['Server1', 'Server2'])
        self.assertEqual(param.value, ['Server1', 'Server2'])

        # Dictionary value
        param = ScenarioParameter('config', {'max': 10, 'min': 5})
        self.assertEqual(param.value, {'max': 10, 'min': 5})


class TestScenario(unittest.TestCase):
    """Test cases for the Scenario class."""

    def test_init_empty(self):
        """Test initialization without parameters."""
        scenario = Scenario('Baseline')
        self.assertEqual(scenario.name, 'Baseline')
        self.assertEqual(scenario.parameters, {})
        self.assertEqual(scenario.description, 'Scenario Baseline')
        self.assertEqual(scenario.results, {})

    def test_init_with_parameters(self):
        """Test initialization with parameters."""
        params = {
            'arrival_rate': 0.8,
            'service_time': 5.0,
            'capacity': 2
        }
        scenario = Scenario('HighDemand', params, 'High demand configuration')

        self.assertEqual(scenario.name, 'HighDemand')
        self.assertEqual(len(scenario.parameters), 3)
        self.assertEqual(scenario.description, 'High demand configuration')

        # Check parameter conversion
        for name, value in params.items():
            self.assertIn(name, scenario.parameters)
            self.assertIsInstance(scenario.parameters[name], ScenarioParameter)
            self.assertEqual(scenario.parameters[name].value, value)

    def test_add_parameter(self):
        """Test adding parameters dynamically."""
        scenario = Scenario('Test')

        # Add parameter without description
        scenario.add_parameter('param1', 100)
        self.assertIn('param1', scenario.parameters)
        self.assertEqual(scenario.parameters['param1'].value, 100)

        # Add parameter with description
        scenario.add_parameter('param2', 'value', 'Test parameter')
        self.assertIn('param2', scenario.parameters)
        self.assertEqual(scenario.parameters['param2'].value, 'value')
        self.assertEqual(scenario.parameters['param2'].description, 'Test parameter')

    def test_get_parameter_value(self):
        """Test getting parameter values."""
        scenario = Scenario('Test', {'param1': 10, 'param2': 'test'})

        # Get existing parameters
        self.assertEqual(scenario.get_parameter_value('param1'), 10)
        self.assertEqual(scenario.get_parameter_value('param2'), 'test')

        # Get non-existent parameter with default
        self.assertEqual(scenario.get_parameter_value('param3', 99), 99)

        # Get non-existent parameter without default
        self.assertIsNone(scenario.get_parameter_value('param3'))

    def test_repr(self):
        """Test string representation."""
        scenario = Scenario('Test', {'p1': 1, 'p2': 2})
        repr_str = repr(scenario)

        # Check that it contains the scenario name and parameters
        self.assertIn('Test', repr_str)
        self.assertIn('p1=1', repr_str)
        self.assertIn('p2=2', repr_str)


class TestExperimentRunner(unittest.TestCase):
    """Test cases for the ExperimentRunner class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model_builder = MagicMock()

        self.runner = ExperimentRunner(
            name="Test Experiment",
            model_builder=self.mock_model_builder,
            tracked_statistics=[
                ('Server', 'ATM', 'ScheduledUtilization', 'Utilization'),
                ('Server', 'ATM', 'AvgTimeInQueue', 'Queue Time'),
                ('Sink', 'Exit', 'AvgTimeInSystem', 'System Time')
            ],
            global_parameters={'simulation_seed': 42},
            parameter_display_names={
                'arrival_rate': 'Arrival Rate',
                'ATM.capacity': 'Number of ATMs'
            }
        )

    def test_init(self):
        """Test ExperimentRunner initialization."""
        self.assertEqual(self.runner.name, "Test Experiment")
        self.assertEqual(self.runner.model_builder, self.mock_model_builder)
        self.assertEqual(len(self.runner.tracked_statistics), 3)
        self.assertEqual(self.runner.global_parameters, {'simulation_seed': 42})
        self.assertIn('arrival_rate', self.runner.parameter_display_names)
        self.assertEqual(len(self.runner.scenarios), 0)
        self.assertTrue(self.runner.results.empty)
        self.assertIsNone(self.runner.start_time)
        self.assertIsNone(self.runner.end_time)

    def test_add_scenario(self):
        """Test adding scenarios."""
        scenario1 = Scenario('Baseline', {'arrival_rate': 0.5})
        scenario2 = Scenario('HighDemand', {'arrival_rate': 0.8})

        self.runner.add_scenario(scenario1)
        self.assertEqual(len(self.runner.scenarios), 1)
        self.assertEqual(self.runner.scenarios[0], scenario1)

        self.runner.add_scenario(scenario2)
        self.assertEqual(len(self.runner.scenarios), 2)
        self.assertEqual(self.runner.scenarios[1], scenario2)

    def test_create_scenario(self):
        """Test creating scenarios directly."""
        # Create scenario without parameters
        scenario1 = self.runner.create_scenario('Empty')
        self.assertIsInstance(scenario1, Scenario)
        self.assertEqual(scenario1.name, 'Empty')
        self.assertEqual(len(self.runner.scenarios), 1)

        # Create scenario with parameters and description
        scenario2 = self.runner.create_scenario(
            'Complex',
            {'arrival_rate': 0.7, 'capacity': 3},
            'Complex scenario with multiple parameters'
        )
        self.assertEqual(scenario2.name, 'Complex')
        self.assertEqual(len(scenario2.parameters), 2)
        self.assertEqual(scenario2.description, 'Complex scenario with multiple parameters')
        self.assertEqual(len(self.runner.scenarios), 2)

    def test_standardize_results(self):
        """Test DataFrame standardization."""
        # Empty DataFrame
        empty_df = pd.DataFrame()
        result = self.runner.standardize_results(empty_df)
        self.assertTrue(result.empty)

        # DataFrame with required columns
        df = pd.DataFrame({
            'Type': ['Server', 'Server', 'Sink'],
            'Name': ['ATM', 'ATM', 'Exit'],
            'Stat': ['ScheduledUtilization', 'AvgTimeInQueue', 'AvgTimeInSystem'],
            'Average': [0.75, 2.5, 10.0]
        })
        result = self.runner.standardize_results(df)
        self.assertIsInstance(result.index, pd.MultiIndex)
        self.assertEqual(result.index.names, ['Type', 'Name', 'Stat'])

        # DataFrame already with MultiIndex
        multi_df = df.set_index(['Type', 'Name', 'Stat'])
        result = self.runner.standardize_results(multi_df)
        self.assertIsInstance(result.index, pd.MultiIndex)

        # DataFrame without required columns
        bad_df = pd.DataFrame({'Value': [1, 2, 3]})
        result = self.runner.standardize_results(bad_df)
        self.assertTrue(result.equals(bad_df))

    def test_build_model_with_parameters(self):
        """Test model building with parameter merging."""
        scenario = Scenario('Test', {'arrival_rate': 0.6, 'capacity': 2})

        # Mock environment
        mock_env = MagicMock()

        # Call build model
        self.runner._build_model_with_parameters(mock_env, scenario)

        # Verify model builder was called with merged parameters
        self.mock_model_builder.assert_called_once()
        call_args = self.mock_model_builder.call_args

        # Should be called with env and parameters
        self.assertEqual(call_args[0][0], mock_env)
        params = call_args[0][1]

        # Should contain both global and scenario parameters
        self.assertEqual(params['simulation_seed'], 42)  # Global
        self.assertEqual(params['arrival_rate'], 0.6)    # Scenario
        self.assertEqual(params['capacity'], 2)          # Scenario

    @patch('src.core.simulation.experiments.experiment.ReplicationRunner')
    @patch('src.core.simulation.experiments.experiment.ParameterizedModel')
    def test_run_scenario(self, mock_param_model_class, mock_replication_runner_class):
        """Test running a single scenario."""
        # Mock ParameterizedModel
        mock_param_model = MagicMock()
        mock_param_model_class.return_value = mock_param_model

        # Mock the ReplicationRunner instance
        mock_runner = MagicMock()
        mock_replication_runner_class.return_value = mock_runner

        # Mock pivot table result
        mock_pivot = pd.DataFrame({
            'Type': ['Server'],
            'Name': ['ATM'],
            'Stat': ['ScheduledUtilization'],
            'Average': [0.75],
            'Minimum': [0.70],
            'Maximum': [0.80],
            'Half-Width': [0.05]
        })
        mock_pivot = mock_pivot.set_index(['Type', 'Name', 'Stat'])
        mock_runner.run.return_value = mock_pivot
        mock_runner.detailed_replication_data = [{'test': 'data'}]

        # Create scenario
        scenario = Scenario('TestScenario', {'arrival_rate': 0.5})

        # Run scenario
        result = self.runner._run_scenario(
            scenario,
            steps=1000,
            replications=10,
            warm_up=100,
            multiprocessing=False,
            store_replication_data=True
        )

        # Verify ParameterizedModel was created with correct parameters
        mock_param_model_class.assert_called_once()
        call_args = mock_param_model_class.call_args
        self.assertEqual(call_args[0][0], self.runner.model_builder)
        # Check that parameters include both global and scenario-specific
        params = call_args[0][1]
        self.assertEqual(params['arrival_rate'], 0.5)
        self.assertEqual(params['simulation_seed'], 42)  # Global parameter

        # Verify ReplicationRunner was created and run
        mock_replication_runner_class.assert_called_once()
        mock_runner.run.assert_called_once_with(new_database=True)

        # Verify results
        self.assertFalse(result.empty)
        self.assertIn('Scenario', result.columns)
        self.assertEqual(result['Scenario'].iloc[0], 'TestScenario')

        # Verify replication data was stored
        self.assertIn('TestScenario', self.runner.replication_data)
        self.assertEqual(self.runner.replication_data['TestScenario'], [{'test': 'data'}])

    @patch('src.core.simulation.experiments.experiment.ExperimentRunner._run_scenario')
    def test_run_all(self, mock_run_scenario):
        """Test running all scenarios."""
        # Create scenarios
        self.runner.create_scenario('Scenario1', {'param': 1})
        self.runner.create_scenario('Scenario2', {'param': 2})

        # Mock _run_scenario results
        mock_run_scenario.side_effect = [
            pd.DataFrame({'Scenario': ['Scenario1'], 'Result': [1]}),
            pd.DataFrame({'Scenario': ['Scenario2'], 'Result': [2]})
        ]

        # Run all scenarios
        result = self.runner.run_all(
            steps=1000,
            replications=5,
            warm_up=100,
            multiprocessing=True,
            store_replication_data=False
        )

        # Verify both scenarios were run
        self.assertEqual(mock_run_scenario.call_count, 2)

        # Verify results were combined
        self.assertEqual(len(result), 2)
        self.assertIsNotNone(self.runner.start_time)
        self.assertIsNotNone(self.runner.end_time)

        # Check that the correct arguments were passed
        # _run_scenario is called with (scenario, steps, replications, warm_up, multiprocessing, store_replication_data)
        for i, call in enumerate(mock_run_scenario.call_args_list):
            args, kwargs = call
            # Check positional arguments
            self.assertEqual(args[0], self.runner.scenarios[i])  # scenario
            self.assertEqual(args[1], 1000)   # steps
            self.assertEqual(args[2], 5)      # replications
            self.assertEqual(args[3], 100)    # warm_up
            self.assertEqual(args[4], True)   # multiprocessing
            self.assertEqual(args[5], False)  # store_replication_data

    def test_run_all_no_scenarios(self):
        """Test error when running with no scenarios."""
        with self.assertRaises(ValueError) as context:
            self.runner.run_all(steps=1000, replications=5)
        self.assertIn('No scenarios defined', str(context.exception))

    def test_filter_results_with_multiindex(self):
        """Test filtering results with MultiIndex data."""
        # Create test scenarios with results
        scenario1 = Scenario('Baseline')
        scenario2 = Scenario('HighDemand')

        # Create MultiIndex results for each scenario
        index = pd.MultiIndex.from_tuples([
            ('Server', 'ATM', 'ScheduledUtilization'),
            ('Server', 'ATM', 'AvgTimeInQueue'),
            ('Sink', 'Exit', 'AvgTimeInSystem')
        ], names=['Type', 'Name', 'Stat'])

        scenario1.results = pd.DataFrame({
            'Average': [0.75, 2.5, 10.0],
            'Minimum': [0.70, 2.0, 9.0],
            'Maximum': [0.80, 3.0, 11.0],
            'Half-Width': [0.05, 0.5, 1.0]
        }, index=index)

        scenario2.results = pd.DataFrame({
            'Average': [0.85, 5.0, 15.0],
            'Minimum': [0.80, 4.5, 14.0],
            'Maximum': [0.90, 5.5, 16.0],
            'Half-Width': [0.05, 0.5, 1.0]
        }, index=index)

        scenario1.parameters = {'arrival_rate': ScenarioParameter('arrival_rate', 0.5)}
        scenario2.parameters = {'arrival_rate': ScenarioParameter('arrival_rate', 0.8)}

        self.runner.scenarios = [scenario1, scenario2]

        # Test filtering
        filtered = self.runner.filter_results('Server', 'ATM', 'ScheduledUtilization')

        self.assertEqual(len(filtered), 2)
        self.assertIn('Average', filtered.columns)
        self.assertIn('Scenario', filtered.columns)

        # Check values
        baseline = filtered[filtered['Scenario'] == 'Baseline']
        highdemand = filtered[filtered['Scenario'] == 'HighDemand']

        self.assertEqual(baseline['Average'].iloc[0], 0.75)
        self.assertEqual(highdemand['Average'].iloc[0], 0.85)

    @patch('src.core.visualization.visualization_helpers.get_comparison_data')
    def test_get_comparison_data(self, mock_get_comparison):
        """Test that get_comparison_data delegates to helper."""
        mock_get_comparison.return_value = pd.DataFrame({'test': [1, 2, 3]})

        result = self.runner.get_comparison_data('Server', 'ATM', 'Utilization')

        mock_get_comparison.assert_called_once_with(
            self.runner, 'Server', 'ATM', 'Utilization'
        )
        self.assertTrue(result.equals(pd.DataFrame({'test': [1, 2, 3]})))

    @patch('builtins.print')
    @patch('src.core.simulation.experiments.experiment.tabulate')
    def test_display_summary_table(self, mock_tabulate, mock_print):
        """Test summary table display."""
        # Create scenarios
        self.runner.create_scenario('Baseline', {'arrival_rate': 0.5})
        self.runner.create_scenario('HighDemand', {'arrival_rate': 0.8})

        # Mock get_comparison_data
        def mock_comparison(comp_type, comp_name, stat):
            if stat == 'ScheduledUtilization':
                return pd.DataFrame({
                    'Scenario': ['Baseline', 'HighDemand'],
                    'Average': [0.75, 0.85]
                })
            elif stat == 'AvgTimeInQueue':
                return pd.DataFrame({
                    'Scenario': ['Baseline', 'HighDemand'],
                    'Average': [2.5, 5.0]
                })
            else:
                return pd.DataFrame({
                    'Scenario': ['Baseline', 'HighDemand'],
                    'Average': [10.0, 15.0]
                })

        with patch.object(self.runner, 'get_comparison_data', side_effect=mock_comparison):
            self.runner.display_summary_table(precision=2)

        # Verify tabulate was called
        mock_tabulate.assert_called_once()

        # Check headers include display names
        call_args = mock_tabulate.call_args
        headers = call_args[1]['headers']
        self.assertIn('Arrival Rate', headers)  # Parameter display name
        self.assertIn('Utilization', headers)    # Statistic display name
        self.assertIn('Queue Time', headers)     # Statistic display name

    def test_get_multi_statistic_data(self):
        """Test getting multiple statistics for comparison."""
        # Mock get_comparison_data
        def mock_comparison(comp_type, comp_name, stat):
            if stat == 'ScheduledUtilization':
                return pd.DataFrame({
                    'Scenario': ['Baseline', 'HighDemand'],
                    'Average': [0.75, 0.85],
                    'Param_arrival_rate': [0.5, 0.8]
                })
            elif stat == 'AvgTimeInQueue':
                return pd.DataFrame({
                    'Scenario': ['Baseline', 'HighDemand'],
                    'Average': [2.5, 5.0],
                    'Param_arrival_rate': [0.5, 0.8]
                })
            else:
                return pd.DataFrame()

        with patch.object(self.runner, 'get_comparison_data', side_effect=mock_comparison):
            result = self.runner.get_multi_statistic_data(
                'Server', 'ATM',
                ['ScheduledUtilization', 'AvgTimeInQueue']
            )

        # Check structure
        self.assertEqual(len(result), 2)
        self.assertIn('Scenario', result.columns)
        self.assertIn('ScheduledUtilization', result.columns)
        self.assertIn('AvgTimeInQueue', result.columns)

        # Check values
        baseline = result[result['Scenario'] == 'Baseline']
        self.assertEqual(baseline['ScheduledUtilization'].iloc[0], 0.75)
        self.assertEqual(baseline['AvgTimeInQueue'].iloc[0], 2.5)


class TestParameterizedModel(unittest.TestCase):
    """Test cases for ParameterizedModel class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model_func = MagicMock()
        self.parameters = {
            'arrival_rate': 0.5,
            'Server1.capacity': 2,
            'Server2:processing_time': 5.0
        }

    @patch('src.core.components.model.Model')
    def test_parameterized_model_call(self, mock_model_class):
        """Test calling ParameterizedModel."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Create parameterized model
        param_model = ParameterizedModel(self.mock_model_func, self.parameters)

        # Mock environment
        mock_env = MagicMock()

        # Call the model
        with patch('inspect.signature') as mock_signature:
            # Mock that the function accepts parameters
            mock_param = MagicMock()
            mock_param.parameters = {'parameters': None}
            mock_signature.return_value = mock_param

            result = param_model(mock_env)

        # Verify model was reset
        mock_model.reset_simulation.assert_called_once()

        # Verify model function was called
        self.mock_model_func.assert_called_once_with(mock_env, self.parameters)

        # Verify result
        self.assertEqual(result, mock_model)

    def test_parameterize_model_decorator(self):
        """Test the parameterize_model decorator."""
        # Function that accepts parameters
        @parameterize_model
        def model_with_params(env, parameters=None):
            return f"Called with {parameters}"

        # Function that doesn't accept parameters
        @parameterize_model
        def model_without_params(env):
            return "Called without parameters"

        mock_env = MagicMock()

        # Test with parameters
        result = model_with_params(mock_env, {'test': 123})
        self.assertEqual(result, "Called with {'test': 123}")

        # Test without parameters
        result = model_with_params(mock_env)
        self.assertEqual(result, "Called with None")

        # Test function that doesn't accept parameters
        result = model_without_params(mock_env)
        self.assertEqual(result, "Called without parameters")


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for complete experiment workflows."""

    @patch('src.core.simulation.experiments.experiment.ReplicationRunner')
    @patch('src.core.simulation.experiments.experiment.ParameterizedModel')
    def test_complete_experiment_workflow(self, mock_param_model_class, mock_replication_class):
        """Test a complete experiment from setup to results."""
        # Mock model builder
        def model_builder(env, parameters=None):
            return MagicMock()

        # Create experiment
        experiment = ExperimentRunner(
            name="Integration Test",
            model_builder=model_builder,
            tracked_statistics=[
                ('Server', 'Server1', 'Utilization', 'Server 1 Util'),
                ('Entity', 'Entity', 'AvgTimeInSystem', 'Avg Time')
            ],
            parameter_display_names={
                'rate': 'Arrival Rate',
                'capacity': 'System Capacity'
            }
        )

        # Add scenarios
        experiment.create_scenario('Low', {'rate': 0.3, 'capacity': 1})
        experiment.create_scenario('Medium', {'rate': 0.5, 'capacity': 2})
        experiment.create_scenario('High', {'rate': 0.8, 'capacity': 3})

        # Mock ParameterizedModel
        mock_param_model = MagicMock()
        mock_param_model_class.return_value = mock_param_model

        # Mock replication runner
        mock_runner = MagicMock()
        mock_replication_class.return_value = mock_runner

        # Mock different results for each scenario
        results = [
            pd.DataFrame({  # Low
                'Average': [0.5, 5.0],
                'Minimum': [0.4, 4.0],
                'Maximum': [0.6, 6.0],
                'Half-Width': [0.1, 1.0]
            }, index=pd.MultiIndex.from_tuples([
                ('Server', 'Server1', 'Utilization'),
                ('Entity', 'Entity', 'AvgTimeInSystem')
            ])),
            pd.DataFrame({  # Medium
                'Average': [0.7, 8.0],
                'Minimum': [0.6, 7.0],
                'Maximum': [0.8, 9.0],
                'Half-Width': [0.1, 1.0]
            }, index=pd.MultiIndex.from_tuples([
                ('Server', 'Server1', 'Utilization'),
                ('Entity', 'Entity', 'AvgTimeInSystem')
            ])),
            pd.DataFrame({  # High
                'Average': [0.9, 15.0],
                'Minimum': [0.85, 12.0],
                'Maximum': [0.95, 18.0],
                'Half-Width': [0.05, 3.0]
            }, index=pd.MultiIndex.from_tuples([
                ('Server', 'Server1', 'Utilization'),
                ('Entity', 'Entity', 'AvgTimeInSystem')
            ]))
        ]

        mock_runner.run.side_effect = results
        mock_runner.detailed_replication_data = [{'mock': 'data'}]

        # Run experiment
        experiment.run_all(
            steps=1000,
            replications=10,
            warm_up=100,
            multiprocessing=True
        )

        # Verify ParameterizedModel was created for each scenario
        self.assertEqual(mock_param_model_class.call_count, 3)

        # Verify all scenarios were run with ReplicationRunner
        self.assertEqual(mock_replication_class.call_count, 3)


if __name__ == '__main__':
    unittest.main()
