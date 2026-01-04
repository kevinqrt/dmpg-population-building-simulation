import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.experiments.experiment import ExperimentRunner
from src.core.simulation.experiments.parameter_manager import parameterize_model
from src.core.visualization.plots import (plot_bar_chart, plot_histogram, plot_violin, plot_pie_chart,
                                          plot_box_plot, plot_smore_chart, plot_scatter)


@parameterize_model
def setup_atm_model(env, parameters=None):
    """
    Set up a simple ATM simulation model with parameterizable arrival rate,
    service times, and ATM capacity.
    """
    params = parameters or {}

    # Get parameters with defaults
    arrival_rate = params.get('arrival_rate', 0.2)  # 1 customer every 5 minutes on average
    service_time_min = params.get('service_time_min', 3)
    service_time_max = params.get('service_time_max', 7)
    atm_capacity = params.get('ATM.capacity', 1)  # Default ATM capacity

    # Create model components
    source = Source(env, "CustomerArrival",
                    (lambda: random.expovariate(arrival_rate),))

    atm = Server(env, "ATM",
                 (random.uniform, service_time_min, service_time_max),
                 capacity=atm_capacity)

    exit = Sink(env, "Exit")

    # Connect components
    source.connect(atm)
    atm.connect(exit)


def run_visualization_example():

    # Create experiment runner
    experiment = ExperimentRunner(
        name="ATM Service Analysis",
        model_builder=setup_atm_model,
        tracked_statistics=[
            ('Source', 'CustomerArrival', 'NumberCreated', 'Arrived_Customers'),
            ('Server', 'ATM', 'ScheduledUtilization', 'ATM_Util'),
            ('Server', 'ATM', 'TimeInQueue (average)', 'Queue_Time'),
            ('Server', 'ATM', 'EntitiesInQueue (max)', 'Max_Queue_Length'),
            ('Sink', 'Exit', 'NumberEntered', 'Customers_Served'),
            ('Sink', 'Exit', 'TimeInSystem (average)', 'System_Time')
        ],
        parameter_display_names={
            'arrival_rate': 'Arrival_Rate',
            'ATM.capacity': 'ATM_Count',
            'service_time_min': 'Min_Service_Time',
            'service_time_max': 'Max_Service_Time'
        }
    )

    # Create scenarios with systematic parameter variations

    # Standard configuration
    experiment.create_scenario(
        name="Baseline",
        parameters={
            'arrival_rate': 0.2,
            'ATM.capacity': 1,
            'service_time_min': 3,
            'service_time_max': 7
        },
        description="Baseline configuration with 1 ATM"
    )

    # More ATM capacity
    experiment.create_scenario(
        name="TwoATMs",
        parameters={
            'arrival_rate': 0.2,
            'ATM.capacity': 2,
            'service_time_min': 3,
            'service_time_max': 7
        },
        description="Configuration with 2 ATMs"
    )

    # Faster service
    experiment.create_scenario(
        name="FastService",
        parameters={
            'arrival_rate': 0.2,
            'ATM.capacity': 1,
            'service_time_min': 1.5,
            'service_time_max': 3.5
        },
        description="Configuration with faster service time"
    )

    # Higher demand
    experiment.create_scenario(
        name="HighDemand",
        parameters={
            'arrival_rate': 0.4,
            'ATM.capacity': 1,
            'service_time_min': 3,
            'service_time_max': 7
        },
        description="Configuration with higher customer arrival rate"
    )

    # High capacity and high demand
    experiment.create_scenario(
        name="HighCapHighDemand",
        parameters={
            'arrival_rate': 0.4,
            'ATM.capacity': 2,
            'service_time_min': 3,
            'service_time_max': 7
        },
        description="Configuration with high capacity and high demand"
    )

    # Run all scenarios
    experiment.run_all(
        steps=2000,
        replications=20,
        warm_up=500,
        multiprocessing=True
    )

    # Display the summary table
    experiment.display_summary_table()

    # 1. Bar Chart Example - ATM Utilization
    print("\n=== 1. Bar Chart Example - ATM Utilization ===")

    # System time comparison
    plot_bar_chart(
        experiment,
        'Sink',
        'Exit',
        'TimeInSystem (average)',  # Fixed
        plot_params={
            'title': 'Average System Time by Scenario',
            'ylabel': 'System Time (minutes)',
            'show_values': True,
            'value_format': '.2f',
            'scenario_colors': {
                'Baseline': '#1f77b4',
                'TwoATMs': '#ff7f0e',
                'FastService': '#2ca02c',
                'HighDemand': '#d62728',
                'HighCapHighDemand': '#9467bd'
            }
        }
    )

    # Queue length comparison
    plot_bar_chart(
        experiment,
        'Server',
        'ATM',
        'EntitiesInQueue (max)',
        scenarios_to_include=['Baseline', 'HighDemand', 'TwoATMs'],
        plot_params={
            'title': 'Maximum Queue Length Comparison',
            'ylabel': 'Max Queue Length (customers)',
            'show_values': True,
            'show_error_bars': True,
            'bar_alpha': 0.7
        }
    )

    # 2. Pie Chart Example - Customer Service Breakdown
    print("\n=== 2. Pie Chart Example - Customer Service Distribution ===")
    pie_params = {
        'title': 'Distribution of Customers Served Across Scenarios',
        'scenario_colors': {
            'Baseline': '#1f77b4',
            'TwoATMs': '#ff7f0e',
            'FastService': '#2ca02c',
            'HighDemand': '#d62728',
            'HighCapHighDemand': '#9467bd'
        },
        'explode': [0.0, 0.1, 0.0, 0.0, 0.0],  # Explode the second slice (TwoATMs)
        'shadow': True,
        'startangle': 45,
        'autopct': '%1.1f%%',
        'legend': True,
        'legend_loc': 'best'
    }
    plot_pie_chart(experiment, 'Sink', 'Exit', 'NumberEntered', plot_params=pie_params)
    plot_pie_chart(experiment, 'Sink',
                   'Exit',
                   'NumberEntered',
                   scenarios_to_include=['TwoATMs', 'HighCapHighDemand'],
                   plot_params=pie_params)

    # 3. Box Plot Example - Queue Time Distribution
    print("\n=== 3. Box Plot Example - Queue Time Distribution ===")
    box_params = {
        'title': 'Queue Time Distribution Across Scenarios',
        'ylabel': 'Queue Time (minutes)',
        'scenario_colors': {
            'Baseline': '#1f77b4',
            'TwoATMs': '#ff7f0e',
            'FastService': '#2ca02c',
            'HighDemand': '#d62728',
            'HighCapHighDemand': '#9467bd'
        },
        'show_means': True,
        'show_points': True,
        'point_alpha': 0.5,
        'grid': True
    }
    plot_box_plot(experiment, 'Server', 'ATM', 'TimeInQueue (average)', plot_params=box_params)
    plot_box_plot(experiment, 'Server',
                  'ATM',
                  'TimeInQueue (average)',
                  scenarios_to_include=['TwoATMs', 'FastService'],
                  plot_params=box_params)

    # 4. Violin Plot Example - Queue Time Distribution
    print("\n=== 4. Violin Plot Example - Queue Time Distribution ===")
    plot_violin(experiment, 'Server', 'ATM', 'TimeInQueue (average)',
                plot_params={
                    'title': 'Queue Time Distribution by Scenario',
                    'show_points': True
                })
    plot_violin(experiment, 'Server',
                'ATM',
                'TimeInQueue (average)',
                scenarios_to_include=['TwoATMs', 'FastService'],
                plot_params={
                    'title': 'Queue Time Distribution by Scenario',
                    'show_points': True
                })

    # 5. Histogram Example - Utilization Distribution
    print("\n=== 5. Histogram Example - Utilization Distribution ===")

    plot_histogram(experiment, 'Server',
                   'ATM',
                   'ScheduledUtilization',
                   plot_params={
                       'title': 'ATM Utilization Distribution - All Scenarios',
                       'bins': 20,
                       'color_palette': 'Set1',
                       'edgecolor': 'white',
                       'alpha': 0.8,
                       'kde': True,
                       'kde_color': '#D32F2F',  # Alert red
                       'kde_linewidth': 2,
                       'show_stats': True,
                       'stats_loc': (0.02, 0.95)
                   })

    plot_histogram(experiment,
                   'Server',
                   'ATM',
                   'ScheduledUtilization',
                   scenario_name='FastService',
                   plot_params={
                       'title': 'ATM Utilization Distribution - FastService ATM',
                       'bins': 20,
                       'color_palette': 'Set1',
                       'edgecolor': 'white',
                       'alpha': 0.8,
                       'kde': True,
                       'kde_color': '#D32F2F',  # Alert red
                       'kde_linewidth': 2,
                       'show_stats': True,
                       'stats_loc': (0.02, 0.95)
                   })

    # 6. SMORE Chart Example - Multi-metric Analysis
    print("\n=== 6. SMORE Chart Example - Multi-metric Analysis ===")
    plot_smore_chart(
        experiment,
        'Server',
        'ATM',
        ['ScheduledUtilization', 'TimeInQueue (average)'],
        plot_params={
            'percentiles': (10, 90),  # Show 10th-90th percentiles
            'confidence_level': 0.99,  # 99% CI
            'show_replication_dots': True,
            'show_histogram': False,
            'title': 'SMORE Analysis: ATM Performance Metrics'
        }
    )

    plot_smore_chart(
        experiment,
        'Server',
        'ATM',
        ['ScheduledUtilization', 'TimeInQueue (average)'],
        scenarios_to_include=['TwoATMs', 'FastService'],
        plot_params={
            'percentiles': (10, 90),  # Show 10th-90th percentiles
            'confidence_level': 0.99,  # 99% CI
            'show_replication_dots': True,
            'show_histogram': False,
            'title': 'SMORE Analysis: ATM Performance Metrics (Selected Scenarios)'
        }
    )

    plot_smore_chart(
        experiment,
        'Server',
        'ATM',
        ['ScheduledUtilization'],
        scenarios_to_include=['TwoATMs', 'FastService'],
        plot_params={
            'percentiles': (10, 90),  # Show 10th-90th percentiles
            'confidence_level': 0.99,  # 99% CI
            'show_replication_dots': True,
            'show_histogram': False,
            'title': 'SMORE Analysis: ATM Utilization Only'
        }
    )

    # 7. Scatter Plot Examples - Correlation Analysis
    print("\n=== 7. Scatter Plot Examples - Correlation Analysis ===")

    # Example: Compare two statistics for the same component
    plot_scatter(
        experiment,
        'Server', 'ATM', 'ScheduledUtilization',    # x-axis
        'Server', 'ATM', 'TimeInQueue (average)',   # y-axis
        scenarios_to_include=['TwoATMs', 'FastService'],
        plot_params={
            'title': 'ATM: Utilization vs Queue Time Correlation',
            'marker_size': 80,
            'show_regression': True,
            'show_correlation': True
        }
    )

    # Example: Entity vs Server statistics
    plot_scatter(
        experiment,
        'Entity', 'Entity', 'TimeInSystem (average)',   # x-axis
        'Server', 'ATM', 'TimeInQueue (average)',       # y-axis
        scenarios_to_include=['TwoATMs', 'FastService'],
        plot_params={
            'title': 'System Time vs Queue Time Relationship',
            'marker': 's',  # Square markers
            'marker_size': 60
        }
    )

    # 8. Example of saving a plot
    print("\n=== 9. Saving Example ===")
    save_params = {
        'title': 'ATM Utilization (Saved Example)',
        'scenario_colors': {
            'Baseline': 'blue',
            'TwoATMs': 'orange',
            'FastService': 'green',
            'HighDemand': 'red',
            'HighCapHighDemand': 'purple'
        },
        'save_path': 'atm_utilization.png',
        'dpi': 300
    }

    # Saving Example
    plot_bar_chart(experiment, 'Server', 'ATM', 'ScheduledUtilization', plot_params=save_params)
    print("Bar chart saved to 'atm_utilization.png'")

    return experiment


if __name__ == "__main__":
    experiment = run_visualization_example()

    print("\n All experiment visualizations completed")
    print(f"Experiment '{experiment.name}' analyzed {len(experiment.scenarios)} scenarios")
