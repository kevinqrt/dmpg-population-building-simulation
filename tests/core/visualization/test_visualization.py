import unittest
import pandas as pd
import matplotlib.pyplot as plt
from unittest.mock import MagicMock, patch

from src.core.visualization.plots import (
    plot_bar_chart, plot_histogram, plot_pie_chart, plot_box_plot,
    plot_violin, plot_scatter, plot_smore_chart
)
from src.core.visualization.visualization_helpers import (
    _apply_common_styling, _get_scenario_colors, _save_figure,
    _get_data_source_type, get_comparison_data, get_replication_data,
    filter_scenarios, filter_components
)
from src.core.global_imports import Stats


class TestVisualizationHelpers(unittest.TestCase):
    """Test cases for visualization helper functions."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')

    def test_apply_common_styling(self):
        """Test applying common styling to axes."""
        fig, ax = plt.subplots()

        params = {
            'title': 'Test Title',
            'title_fontsize': 16,
            'title_fontweight': 'bold',
            'xlabel': 'X Label',
            'ylabel': 'Y Label',
            'label_fontsize': 14,
            'tick_fontsize': 12,
            'grid': True,
            'grid_axis': 'both',
            'grid_alpha': 0.5,
            'grid_linestyle': '-.'
        }

        _apply_common_styling(ax, params)

        # Check title
        self.assertEqual(ax.get_title(), 'Test Title')

        # Check labels
        self.assertEqual(ax.get_xlabel(), 'X Label')
        self.assertEqual(ax.get_ylabel(), 'Y Label')

        # Check grid is enabled
        self.assertTrue(ax.xaxis.get_gridlines()[0].get_visible())
        self.assertTrue(ax.yaxis.get_gridlines()[0].get_visible())

    def test_get_scenario_colors_with_mapping(self):
        """Test getting colors with user-provided mapping."""
        data_source = MagicMock()
        scenarios = ['Baseline', 'HighDemand', 'FastService']

        params = {
            'scenario_colors': {
                'Baseline': 'red',
                'HighDemand': 'blue',
                'FastService': 'green'
            },
            'color_palette': 'colorblind'
        }

        colors = _get_scenario_colors(data_source, scenarios, params)

        self.assertEqual(len(colors), 3)
        self.assertEqual(colors[0], 'red')
        self.assertEqual(colors[1], 'blue')
        self.assertEqual(colors[2], 'green')

    def test_get_scenario_colors_partial_mapping(self):
        """Test getting colors with partial user mapping."""
        data_source = MagicMock()
        scenarios = ['Baseline', 'HighDemand', 'FastService']

        params = {
            'scenario_colors': {
                'Baseline': 'red',
                'FastService': 'green'
            },
            'color_palette': 'colorblind'
        }

        with patch('seaborn.color_palette') as mock_palette:
            mock_palette.return_value = ['blue']  # Color for unmapped scenario
            colors = _get_scenario_colors(data_source, scenarios, params)

        self.assertEqual(len(colors), 3)
        self.assertEqual(colors[0], 'red')
        self.assertEqual(colors[2], 'green')
        # Middle one should be from palette
        self.assertIsNotNone(colors[1])

    def test_get_scenario_colors_auto_generation(self):
        """Test automatic color generation."""
        data_source = MagicMock()
        scenarios = ['S1', 'S2', 'S3', 'S4', 'S5']

        params = {
            'scenario_colors': {},  # Empty mapping
            'color_palette': 'Set2'
        }

        with patch('seaborn.color_palette') as mock_palette:
            mock_palette.return_value = ['c1', 'c2', 'c3', 'c4', 'c5']
            colors = _get_scenario_colors(data_source, scenarios, params)

        mock_palette.assert_called_with('Set2', n_colors=5)
        self.assertEqual(len(colors), 5)
        self.assertEqual(colors, ['c1', 'c2', 'c3', 'c4', 'c5'])

    def test_get_scenario_colors_large_number(self):
        """Test color generation for large number of scenarios."""
        data_source = MagicMock()
        scenarios = [f'S{i}' for i in range(15)]  # 15 scenarios

        params = {'scenario_colors': {}}

        with patch('seaborn.color_palette') as mock_palette:
            mock_palette.return_value = [f'color{i}' for i in range(15)]
            colors = _get_scenario_colors(data_source, scenarios, params)

        # For large numbers, should use 'husl' palette
        mock_palette.assert_called_with('husl', n_colors=15)
        self.assertEqual(len(colors), 15)

    @patch('matplotlib.pyplot.savefig')
    def test_save_figure(self, mock_savefig):
        """Test saving figure."""
        params = {
            'save_path': 'test_plot.png',
            'dpi': 150
        }

        _save_figure(params)

        mock_savefig.assert_called_once_with('test_plot.png', dpi=150, bbox_inches='tight')

    def test_save_figure_no_path(self):
        """Test save_figure with no path specified."""
        params = {}

        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            _save_figure(params)
            mock_savefig.assert_not_called()

    def test_get_data_source_type(self):
        """Test detecting data source type."""
        # The function tries to import classes inside, so we need to mock differently

        # Create mock classes
        class MockExperimentRunner:
            pass

        class MockReplicationRunner:
            pass

        # Test ExperimentRunner
        mock_experiment = MockExperimentRunner()
        result = _get_data_source_type(mock_experiment)
        # Since we can't easily mock the import inside the function,
        # we expect it to check for all_detailed_stats
        self.assertEqual(result, 'unknown')

        # Test with all_detailed_stats (Stats object)
        stats_obj = MagicMock()
        stats_obj.all_detailed_stats = [{'test': 'data'}]
        self.assertEqual(_get_data_source_type(stats_obj), 'replication_stats')

        # Test unknown
        unknown_obj = MagicMock()
        unknown_obj.all_detailed_stats = None
        self.assertEqual(_get_data_source_type(unknown_obj), 'unknown')

    def test_filter_scenarios(self):
        """Test filtering scenarios."""
        # Mock ExperimentRunner with scenarios
        data_source = MagicMock()

        # Create mock scenarios with proper name attributes
        scenario1 = MagicMock()
        scenario1.name = 'Baseline'
        scenario2 = MagicMock()
        scenario2.name = 'HighDemand'
        scenario3 = MagicMock()
        scenario3.name = 'FastService'

        data_source.scenarios = [scenario1, scenario2, scenario3]

        with patch('src.core.visualization.visualization_helpers._get_data_source_type', return_value='experiment'):
            # Test with no filter
            result = filter_scenarios(data_source, None)
            self.assertEqual(result, ['Baseline', 'HighDemand', 'FastService'])

            # Test with filter
            result = filter_scenarios(data_source, ['Baseline', 'FastService'])
            self.assertEqual(result, ['Baseline', 'FastService'])

            # Test with invalid scenarios
            result = filter_scenarios(data_source, ['Invalid', 'Baseline'])
            self.assertEqual(result, ['Baseline'])

            # Test with all invalid scenarios
            with patch('builtins.print'):  # Suppress warning
                result = filter_scenarios(data_source, ['Invalid1', 'Invalid2'])
                self.assertEqual(result, [])

    def test_filter_components(self):
        """Test filtering components."""
        detailed_stats = [
            {
                'Server': [
                    {'Server': 'Server1', 'Utilization': 0.75},
                    {'Server': 'Server2', 'Utilization': 0.80}
                ],
                'Sink': {
                    'Sink1': {'AvgTime': 10},
                    'Sink2': {'AvgTime': 15}
                }
            },
            {
                'Server': [
                    {'Server': 'Server1', 'Utilization': 0.78},
                    {'Server': 'Server3', 'Utilization': 0.65}
                ]
            }
        ]

        # Test servers (list format)
        result = filter_components(detailed_stats, 'Server', None)
        self.assertEqual(sorted(result), ['Server1', 'Server2', 'Server3'])

        result = filter_components(detailed_stats, 'Server', ['Server1', 'Server3'])
        self.assertEqual(sorted(result), ['Server1', 'Server3'])

        # Test sinks (dict format)
        result = filter_components(detailed_stats, 'Sink', None)
        self.assertEqual(sorted(result), ['Sink1', 'Sink2'])

        # Test with invalid components
        with patch('builtins.print'):  # Suppress warning
            result = filter_components(detailed_stats, 'Server', ['Invalid'])
            self.assertEqual(result, [])

    def test_get_replication_data(self):
        """Test extracting replication data."""
        # Test with ExperimentRunner
        experiment = MagicMock()
        experiment.replication_data = {
            'Baseline': [
                {'Server': [{'Server': 'ATM', 'Utilization': 0.75}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.78}]}
            ],
            'HighDemand': [
                {'Server': [{'Server': 'ATM', 'Utilization': 0.85}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.88}]}
            ]
        }

        with patch('src.core.visualization.visualization_helpers._get_data_source_type', return_value='experiment'):
            # Get all data
            values = get_replication_data(experiment, 'Server', 'ATM', 'Utilization')
            self.assertEqual(len(values), 4)
            self.assertIn(0.75, values)
            self.assertIn(0.88, values)

            # Get specific scenario
            values = get_replication_data(experiment, 'Server', 'ATM', 'Utilization', 'Baseline')
            self.assertEqual(len(values), 2)
            self.assertIn(0.75, values)
            self.assertIn(0.78, values)

    def test_get_comparison_data_experiment(self):
        """Test getting comparison data from ExperimentRunner."""
        experiment = MagicMock()
        scenario1 = MagicMock()
        scenario1.name = 'Baseline'
        scenario1.results = pd.DataFrame({
            'Average': [0.75],
            'Minimum': [0.70],
            'Maximum': [0.80],
            'Half-Width': [0.05]
        }, index=pd.MultiIndex.from_tuples([('Server', 'ATM', 'Utilization')]))
        scenario1.parameters = {'rate': MagicMock(value=0.5)}

        scenario2 = MagicMock()
        scenario2.name = 'HighDemand'
        scenario2.results = pd.DataFrame({
            'Average': [0.85],
            'Minimum': [0.80],
            'Maximum': [0.90],
            'Half-Width': [0.05]
        }, index=pd.MultiIndex.from_tuples([('Server', 'ATM', 'Utilization')]))
        scenario2.parameters = {'rate': MagicMock(value=0.8)}

        experiment.scenarios = [scenario1, scenario2]

        with patch('src.core.visualization.visualization_helpers._get_data_source_type', return_value='experiment'):
            result = get_comparison_data(experiment, 'Server', 'ATM', 'Utilization')

        self.assertEqual(len(result), 2)
        self.assertIn('Scenario', result.columns)
        self.assertIn('Average', result.columns)
        self.assertEqual(result['Average'].tolist(), [0.75, 0.85])


class TestBarChart(unittest.TestCase):
    """Test cases for bar chart visualization."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

        # Mock experiment data
        self.mock_experiment = MagicMock()
        self.mock_experiment.scenarios = []

        # Mock comparison data
        self.comparison_data = pd.DataFrame({
            'Scenario': ['Baseline', 'HighDemand', 'FastService'],
            'Average': [0.75, 0.85, 0.65],
            'Half-Width': [0.05, 0.05, 0.03],
            'Minimum': [0.70, 0.80, 0.62],
            'Maximum': [0.80, 0.90, 0.68]
        })

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')
        # Clean up Stats
        if hasattr(Stats, 'all_detailed_stats'):
            Stats.all_detailed_stats = None

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots.filter_scenarios')
    @patch('src.core.visualization.plots.get_comparison_data')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_bar_chart_experiment(self, mock_get_type, mock_get_comparison, mock_filter, mock_show):
        """Test bar chart with ExperimentRunner data."""
        mock_get_type.return_value = 'experiment'
        mock_filter.return_value = ['Baseline', 'HighDemand', 'FastService']
        mock_get_comparison.return_value = self.comparison_data

        plot_params = {
            'title': 'Test Bar Chart',
            'show_values': True,
            'show_error_bars': True,
            'show_minmax': True
        }

        plot_bar_chart(
            self.mock_experiment,
            'Server',
            'ATM',
            'ScheduledUtilization',
            plot_params=plot_params
        )

        mock_filter.assert_called_once_with(self.mock_experiment, None)
        mock_get_comparison.assert_called_once_with(
            self.mock_experiment, 'Server', 'ATM', 'ScheduledUtilization'
        )
        mock_show.assert_called_once()

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_bar_chart_stats(self, mock_get_type, mock_show):
        """Test bar chart with Stats data."""
        mock_get_type.return_value = 'replication_stats'

        # Mock Stats.all_detailed_stats
        Stats.all_detailed_stats = [
            {'Server': [
                {'Server': 'Server1', 'Utilization': 0.75},
                {'Server': 'Server2', 'Utilization': 0.85}
            ]},
            {'Server': [
                {'Server': 'Server1', 'Utilization': 0.78},
                {'Server': 'Server2', 'Utilization': 0.82}
            ]}
        ]

        plot_bar_chart(
            Stats,
            'Server',
            statistic='Utilization',
            plot_params={'title': 'Server Utilization'}
        )

        mock_show.assert_called_once()

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots.filter_scenarios')
    @patch('src.core.visualization.plots.get_comparison_data')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_bar_chart_with_scenario_filter(self, mock_get_type, mock_get_comparison,
                                            mock_filter, mock_show):
        """Test bar chart with scenario filtering."""
        mock_get_type.return_value = 'experiment'
        mock_filter.return_value = ['Baseline', 'HighDemand']

        # Return data that will be filtered
        mock_get_comparison.return_value = self.comparison_data

        plot_bar_chart(
            self.mock_experiment,
            'Server',
            'ATM',
            'Utilization',
            scenarios_to_include=['Baseline', 'HighDemand']
        )

        mock_filter.assert_called_once_with(self.mock_experiment, ['Baseline', 'HighDemand'])
        mock_show.assert_called_once()


class TestHistogram(unittest.TestCase):
    """Test cases for histogram visualization."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

        self.mock_experiment = MagicMock()
        self.mock_experiment.replication_data = {
            'Baseline': [
                {'Server': [{'Server': 'ATM', 'Utilization': 0.75}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.78}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.76}]}
            ],
            'HighDemand': [
                {'Server': [{'Server': 'ATM', 'Utilization': 0.85}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.88}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.86}]}
            ]
        }

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots.get_replication_data')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_histogram_basic(self, mock_get_type, mock_get_rep_data, mock_show):
        """Test basic histogram functionality."""
        mock_get_type.return_value = 'experiment'
        mock_get_rep_data.return_value = [0.75, 0.78, 0.76, 0.85, 0.88, 0.86]

        plot_histogram(
            self.mock_experiment,
            'Server',
            'ATM',
            'Utilization',
            plot_params={'bins': 10, 'kde': True}
        )

        mock_get_rep_data.assert_called_once_with(
            self.mock_experiment, 'Server', 'ATM', 'Utilization', None
        )
        mock_show.assert_called_once()

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots.get_replication_data')
    @patch('src.core.visualization.plots.filter_scenarios')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_histogram_specific_scenario(self, mock_get_type, mock_filter,
                                         mock_get_rep_data, mock_show):
        """Test histogram for specific scenario."""
        mock_get_type.return_value = 'experiment'
        mock_filter.return_value = ['Baseline', 'HighDemand']
        mock_get_rep_data.return_value = [0.75, 0.78, 0.76]

        plot_histogram(
            self.mock_experiment,
            'Server',
            'ATM',
            'Utilization',
            scenario_name='Baseline',
            plot_params={'show_stats': True}
        )

        mock_get_rep_data.assert_called_once_with(
            self.mock_experiment, 'Server', 'ATM', 'Utilization', 'Baseline'
        )
        mock_show.assert_called_once()


class TestPieChart(unittest.TestCase):
    """Test cases for pie chart visualization."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')
        # Clean up Stats
        if hasattr(Stats, 'all_detailed_stats'):
            Stats.all_detailed_stats = None

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots.filter_scenarios')
    @patch('src.core.visualization.plots.get_comparison_data')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_pie_chart_experiment(self, mock_get_type, mock_get_comparison, mock_filter, mock_show):
        """Test pie chart with experiment data."""
        mock_get_type.return_value = 'experiment'
        mock_filter.return_value = ['Baseline', 'HighDemand', 'FastService']

        comparison_data = pd.DataFrame({
            'Scenario': ['Baseline', 'HighDemand', 'FastService'],
            'Average': [100, 150, 75]
        })
        mock_get_comparison.return_value = comparison_data

        mock_experiment = MagicMock()

        plot_pie_chart(
            mock_experiment,
            'Sink',
            'Exit',
            'NumberEntered',
            plot_params={
                'explode': [0.1, 0, 0],
                'shadow': True,
                'autopct': '%1.1f%%'
            }
        )

        mock_filter.assert_called_once_with(mock_experiment, None)
        mock_show.assert_called_once()

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.visualization_helpers.filter_components')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_pie_chart_stats(self, mock_get_type, mock_filter, mock_show):
        """Test pie chart with Stats data."""
        mock_get_type.return_value = 'replication_stats'
        mock_filter.return_value = ['Server1', 'Server2', 'Server3']

        Stats.all_detailed_stats = [
            {'Server': [
                {'Server': 'Server1', 'TotalProcessing': 100},
                {'Server': 'Server2', 'TotalProcessing': 150},
                {'Server': 'Server3', 'TotalProcessing': 75}
            ]}
        ]

        plot_pie_chart(
            Stats,
            'Server',
            statistic='TotalProcessing',
            plot_params={'startangle': 90}
        )

        mock_show.assert_called_once()


class TestBoxPlot(unittest.TestCase):
    """Test cases for box plot visualization."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots.filter_scenarios')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_box_plot_experiment(self, mock_get_type, mock_filter, mock_show):
        """Test box plot with experiment data."""
        mock_get_type.return_value = 'experiment'
        mock_filter.return_value = ['Baseline', 'HighDemand']

        mock_experiment = MagicMock()
        mock_experiment.replication_data = {
            'Baseline': [
                {'Server': [{'Server': 'ATM', 'QueueTime': 2.5}]},
                {'Server': [{'Server': 'ATM', 'QueueTime': 3.0}]},
                {'Server': [{'Server': 'ATM', 'QueueTime': 2.8}]}
            ],
            'HighDemand': [
                {'Server': [{'Server': 'ATM', 'QueueTime': 5.0}]},
                {'Server': [{'Server': 'ATM', 'QueueTime': 6.0}]},
                {'Server': [{'Server': 'ATM', 'QueueTime': 5.5}]}
            ]
        }

        plot_box_plot(
            mock_experiment,
            'Server',
            'ATM',
            'QueueTime',
            plot_params={
                'show_means': True,
                'show_points': True,
                'notch': True
            }
        )

        mock_filter.assert_called_once_with(mock_experiment, None)
        mock_show.assert_called_once()


class TestViolinPlot(unittest.TestCase):
    """Test cases for violin plot visualization."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')
        # Clean up Stats
        if hasattr(Stats, 'all_detailed_stats'):
            Stats.all_detailed_stats = None

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.visualization_helpers.filter_components')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_violin_plot_stats(self, mock_get_type, mock_filter, mock_show):
        """Test violin plot with Stats data."""
        mock_get_type.return_value = 'replication_stats'
        mock_filter.return_value = ['Server1', 'Server2']

        Stats.all_detailed_stats = [
            {'Server': [
                {'Server': 'Server1', 'ProcessTime': 3.0},
                {'Server': 'Server2', 'ProcessTime': 5.0}
            ]},
            {'Server': [
                {'Server': 'Server1', 'ProcessTime': 3.5},
                {'Server': 'Server2', 'ProcessTime': 4.5}
            ]},
            {'Server': [
                {'Server': 'Server1', 'ProcessTime': 3.2},
                {'Server': 'Server2', 'ProcessTime': 5.2}
            ]}
        ]

        plot_violin(
            Stats,
            'Server',
            statistic='ProcessTime',
            plot_params={
                'inner': 'box',
                'show_points': True
            }
        )

        mock_show.assert_called_once()


class TestScatterPlot(unittest.TestCase):
    """Test cases for scatter plot visualization."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_scatter_plot_correlation(self, mock_get_type, mock_show):
        """Test scatter plot showing correlation between two stats."""
        mock_get_type.return_value = 'replication'

        mock_runner = MagicMock()
        mock_runner.detailed_replication_data = [
            {
                'Server': [{'Server': 'ATM', 'Utilization': 0.75, 'QueueTime': 2.5}],
                'Entity': {'AvgTimeInSystem': 10.0}
            },
            {
                'Server': [{'Server': 'ATM', 'Utilization': 0.85, 'QueueTime': 5.0}],
                'Entity': {'AvgTimeInSystem': 15.0}
            },
            {
                'Server': [{'Server': 'ATM', 'Utilization': 0.65, 'QueueTime': 1.5}],
                'Entity': {'AvgTimeInSystem': 7.0}
            }
        ]

        # Also test with entity data
        plot_scatter(
            mock_runner,
            'Server', 'ATM', 'Utilization',
            'Server', 'ATM', 'QueueTime',
            plot_params={
                'show_regression': True,
                'show_correlation': True
            }
        )

        mock_show.assert_called_once()


class TestSmorePlot(unittest.TestCase):
    """Test cases for SMORE plot visualization."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')

    @patch('matplotlib.pyplot.show')
    @patch('src.core.visualization.plots.filter_scenarios')
    @patch('src.core.visualization.plots._get_data_source_type')
    def test_smore_plot_multiple_stats(self, mock_get_type, mock_filter, mock_show):
        """Test SMORE plot with multiple statistics."""
        mock_get_type.return_value = 'experiment'
        mock_filter.return_value = ['Baseline', 'HighDemand']

        mock_experiment = MagicMock()
        mock_experiment.replication_data = {
            'Baseline': [
                {'Server': [{'Server': 'ATM', 'Utilization': 0.75, 'QueueTime': 2.5}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.78, 'QueueTime': 3.0}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.76, 'QueueTime': 2.8}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.74, 'QueueTime': 2.6}]}
            ],
            'HighDemand': [
                {'Server': [{'Server': 'ATM', 'Utilization': 0.85, 'QueueTime': 5.0}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.88, 'QueueTime': 6.0}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.86, 'QueueTime': 5.5}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.87, 'QueueTime': 5.8}]}
            ]
        }

        plot_smore_chart(
            mock_experiment,
            'Server',
            'ATM',
            ['Utilization', 'QueueTime'],
            plot_params={
                'percentiles': (25, 75),
                'confidence_level': 0.95,
                'show_replication_dots': True,
                'show_histogram': False
            }
        )

        mock_filter.assert_called_once_with(mock_experiment, None)
        mock_show.assert_called_once()


class TestIntegrationVisualization(unittest.TestCase):
    """Integration tests for visualization workflows."""

    def setUp(self):
        """Set up test fixtures."""
        plt.close('all')

    def tearDown(self):
        """Clean up after tests."""
        plt.close('all')
        # Clean up Stats
        if hasattr(Stats, 'all_detailed_stats'):
            Stats.all_detailed_stats = None

    @patch('matplotlib.pyplot.show')
    def test_complete_visualization_workflow(self, mock_show):
        """Test a complete visualization workflow with different data sources."""
        # Create mock data structures
        mock_experiment = MagicMock()

        # Create scenarios with proper name attributes
        scenario1 = MagicMock()
        scenario1.name = 'Baseline'
        scenario2 = MagicMock()
        scenario2.name = 'HighDemand'

        mock_experiment.scenarios = [scenario1, scenario2]
        mock_experiment.replication_data = {
            'Baseline': [
                {'Server': [{'Server': 'ATM', 'Utilization': 0.75}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.78}]}
            ],
            'HighDemand': [
                {'Server': [{'Server': 'ATM', 'Utilization': 0.85}]},
                {'Server': [{'Server': 'ATM', 'Utilization': 0.88}]}
            ]
        }

        # Set up Stats data
        Stats.all_detailed_stats = [
            {'Server': [
                {'Server': 'Server1', 'Utilization': 0.75},
                {'Server': 'Server2', 'Utilization': 0.80}
            ]},
            {'Server': [
                {'Server': 'Server1', 'Utilization': 0.78},
                {'Server': 'Server2', 'Utilization': 0.82}
            ]}
        ]

        # Mock comparison data
        comparison_data = pd.DataFrame({
            'Scenario': ['Baseline', 'HighDemand'],
            'Average': [0.765, 0.865],
            'Half-Width': [0.015, 0.015]
        })

        with patch('src.core.visualization.plots._get_data_source_type') as mock_type:
            with patch('src.core.visualization.plots.get_comparison_data',
                       return_value=comparison_data):
                with patch('src.core.visualization.plots.filter_scenarios',
                           return_value=['Baseline', 'HighDemand']):

                    # Test with experiment data
                    mock_type.return_value = 'experiment'
                    plot_bar_chart(mock_experiment, 'Server', 'ATM', 'Utilization')

                    # Test with Stats data
                    mock_type.return_value = 'replication_stats'
                    plot_bar_chart(Stats, 'Server', statistic='Utilization')

        # Verify plots were shown
        self.assertEqual(mock_show.call_count, 2)


if __name__ == '__main__':
    unittest.main()
