import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.experiments.experiment import ExperimentRunner
from src.core.simulation.experiments.parameter_manager import parameterize_model
from src.core.visualization.plots import plot_bar_chart, plot_pie_chart, plot_box_plot, plot_violin


@parameterize_model
def setup_atm_model(env, parameters=None):

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


def run_advanced_experiments_with_visuals():

    # Create experiment runner with comprehensive tracking
    experiment = ExperimentRunner(
        name="ATM Service Optimization Study",
        model_builder=setup_atm_model,
        tracked_statistics=[
            ('Source', 'CustomerArrival', 'NumberCreated', 'Customers_Generated'),
            ('Server', 'ATM', 'ScheduledUtilization', 'ATM_Utilization'),
            ('Server', 'ATM', 'TimeInQueue (average)', 'Avg_Queue_Time'),
            ('Server', 'ATM', 'EntitiesInQueue (max)', 'Peak_Queue_Length'),
            ('Server', 'ATM', 'TimeProcessing (average)', 'Avg_Service_Time'),
            ('Server', 'ATM', 'TimeProcessing (total)', 'Total_Service_Time'),
            ('Sink', 'Exit', 'NumberEntered', 'Customers_Served'),
            ('Sink', 'Exit', 'TimeInSystem (average)', 'Avg_System_Time'),
            ('Sink', 'Exit', 'TimeInSystem (max)', 'Max_System_Time')
        ],
        parameter_display_names={
            'arrival_rate': 'Arrival_Rate_per_Min',
            'ATM.capacity': 'Number_of_ATMs',
            'service_time_min': 'Min_Service_Time',
            'service_time_max': 'Max_Service_Time'
        }
    )

    # Create scenarios for parameter study
    scenarios_config = [
        # Low demand scenarios
        ("Low_Demand_1ATM", {'arrival_rate': 0.15, 'ATM.capacity': 1, 'service_time_min': 3, 'service_time_max': 7}),
        ("Low_Demand_2ATM", {'arrival_rate': 0.15, 'ATM.capacity': 2, 'service_time_min': 3, 'service_time_max': 7}),

        # Medium demand scenarios
        ("Medium_Demand_1ATM", {'arrival_rate': 0.25, 'ATM.capacity': 1, 'service_time_min': 3, 'service_time_max': 7}),
        ("Medium_Demand_2ATM", {'arrival_rate': 0.25, 'ATM.capacity': 2, 'service_time_min': 3, 'service_time_max': 7}),
        ("Medium_Demand_3ATM", {'arrival_rate': 0.25, 'ATM.capacity': 3, 'service_time_min': 3, 'service_time_max': 7}),

        # High demand scenarios
        ("High_Demand_1ATM", {'arrival_rate': 0.4, 'ATM.capacity': 1, 'service_time_min': 3, 'service_time_max': 7}),
        ("High_Demand_2ATM", {'arrival_rate': 0.4, 'ATM.capacity': 2, 'service_time_min': 3, 'service_time_max': 7}),
        ("High_Demand_3ATM", {'arrival_rate': 0.4, 'ATM.capacity': 3, 'service_time_min': 3, 'service_time_max': 7}),

        # Fast service scenarios
        ("Fast_Service_1ATM", {'arrival_rate': 0.25, 'ATM.capacity': 1, 'service_time_min': 1.5, 'service_time_max': 3.5}),
        ("Fast_Service_2ATM", {'arrival_rate': 0.25, 'ATM.capacity': 2, 'service_time_min': 1.5, 'service_time_max': 3.5}),
    ]

    # Create all scenarios
    for name, params in scenarios_config:
        experiment.create_scenario(name=name, parameters=params,
                                   description=f"Configuration: {params}")

    print("Running experiment with 10 scenarios...")
    # Run all scenarios with substantial replications for robust statistics
    experiment.run_all(
        steps=3000,
        replications=30,
        warm_up=600,
        multiprocessing=True
    )

    # Display the summary table
    experiment.display_summary_table(precision=3)

    # Define scenario color schemes
    scenario_colors = {
        'Low_Demand_1ATM': '#1f77b4',      # Blue
        'Low_Demand_2ATM': '#aec7e8',      # Light Blue
        'Medium_Demand_1ATM': '#ff7f0e',   # Orange
        'Medium_Demand_2ATM': '#ffbb78',   # Light Orange
        'Medium_Demand_3ATM': '#2ca02c',   # Green
        'High_Demand_1ATM': '#d62728',     # Red
        'High_Demand_2ATM': '#ff9896',     # Light Red
        'High_Demand_3ATM': '#9467bd',     # Purple
        'Fast_Service_1ATM': '#8c564b',    # Brown
        'Fast_Service_2ATM': '#c49c94'     # Light Brown
    }

    # Common  styling
    common_style = {
        'figsize': (12, 8),
        'title_fontsize': 16,
        'title_fontweight': 'bold',
        'label_fontsize': 12,
        'tick_fontsize': 10,
        'grid': True,
        'grid_alpha': 0.2,
        'grid_linestyle': '-',
        'scenario_colors': scenario_colors
    }

    print("\n" + "=" * 100)

    # 1. BAR CHART - ATM Utilization Comparison
    print("\n=== 1. Bar Chart: ATM Utilization Analysis ===")
    bar_params = {
        **common_style,
        'title': 'ATM Utilization Across All Scenarios',
        'ylabel': 'Utilization Rate (%)',
        'xlabel': 'Configuration Scenarios',
        'show_values': True,
        'value_format': '.1f',
        'bar_alpha': 0.85,
        'bar_edgecolor': 'white',
        'bar_linewidth': 1.2,
        'rotation': 45,
        'ha': 'right'
    }
    plot_bar_chart(experiment, 'Server', 'ATM', 'ScheduledUtilization', plot_params=bar_params)

    # 2. PIE CHART - Service Volume Distribution
    print("\n=== 2. Pie Chart: Customer Service Distribution ===")
    pie_params = {
        **common_style,
        'figsize': (10, 10),
        'title': 'Customer Service Volume by Configuration',
        'startangle': 135,
        'explode': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0],  # Highlight best performing scenario
        'shadow': True,
        'autopct': '%1.1f%%',
        'legend': True,
        'legend_loc': 'center left'
    }
    plot_pie_chart(experiment, 'Sink', 'Exit', 'NumberEntered', plot_params=pie_params)

    # 3. BOX PLOT - Variability Analysis
    print("\n=== 3. Box Plot: System Time Variability ===")
    box_params = {
        **common_style,
        'title': 'System Time Variability Across Configurations',
        'ylabel': 'Total System Time (minutes)',
        'xlabel': 'Configuration Scenarios',
        'notch': False,
        'show_means': True,
        'show_points': True,
        'point_alpha': 0.5,
        'rotation': 45,
        'ha': 'right',
        'grid_axis': 'y'
    }
    plot_box_plot(experiment, 'Sink', 'Exit', 'TimeInSystem (average)', plot_params=box_params)

    # 4. VIOLIN PLOT - Distribution Shape Analysis
    print("\n=== 4. Violin Plot: Queue Time Distribution Shapes ===")
    violin_params = {
        **common_style,
        'title': 'Queue Time Distribution Shapes by Scenario',
        'ylabel': 'Average Queue Time (minutes)',
        'xlabel': 'Configuration Scenarios',
        'inner': 'box',
        'show_points': True,
        'rotation': 45,
        'ha': 'right'
    }
    plot_violin(experiment, 'Server', 'ATM', 'TimeInQueue (average)',
                scenarios_to_include=['High_Demand_1ATM', 'High_Demand_2ATM', 'High_Demand_3ATM'],
                plot_params=violin_params)

    return experiment


if __name__ == "__main__":
    experiment = run_advanced_experiments_with_visuals()

    print(f"\nExperiment '{experiment.name}' completed")
    print(f"Analyzed {len(experiment.scenarios)} scenarios with visualizations")
