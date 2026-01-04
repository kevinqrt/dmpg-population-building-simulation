from src.core.global_imports import random
from src.core.components.source import Source
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.simulation.simulation import run_replications

from src.core.visualization.plots import (
    plot_histogram, plot_box_plot, plot_bar_chart,
    plot_pie_chart, plot_smore_chart, plot_violin, plot_scatter
)
from src.core.global_imports import Stats


def setup_model_pcb(env):

    # Create servers, sinks, and sources
    source1 = Source(env, "PCB", (random.expovariate, 1 / 6))

    server1 = Server(env, "Placement", (random.triangular, 3, 5, 4))
    server2 = Server(env, "FinePitchFast", (random.triangular, 8, 10, 9))
    server3 = Server(env, "FinePitchMedium", (random.triangular, 18, 22, 20))
    server4 = Server(env, "FinePitchSlow", (random.triangular, 22, 26, 24))
    server5 = Server(env, "Inspection", (random.uniform, 2, 4))
    server6 = Server(env, "Rework", (random.triangular, 2, 6, 4))

    # Sinks with after_destruction_trigger to record processing count
    sink1 = Sink(env, "GoodParts")
    sink2 = Sink(env, "BadParts")

    # Set up connections with routing probabilities for servers
    source1.connect(server1)

    server1.connect(server2)
    server1.connect(server3)
    server1.connect(server4)
    server2.connect(server5)
    server3.connect(server5)
    server4.connect(server5)
    server6.connect(server1)

    server5.connect(sink1, 66)      # 66% probability to route to GoodParts
    server5.connect(sink2, 8)       # 8% probability to route to BadParts
    server5.connect(server6, 26)    # 26% probability to route to Rework


def create_visualizations():
    """
    Demonstrate the new unified visualization functions with replication data.
    Shows how the same functions work for both experiments and replications!
    """
    print("\n" + "=" * 80)
    print("PCB MANUFACTURING ANALYSIS - REPLICATION VISUALIZATIONS")
    print("=" * 80)

    common_style = {
        'figsize': (10, 6),
        'title_fontsize': 14,
        'title_fontweight': 'bold',
        'label_fontsize': 12,
        'tick_fontsize': 10,
        'grid': True,
        'grid_alpha': 0.3,
        'scenario_colors': '#1f77b4'  # blue
    }

    # 1. HISTOGRAM - System Time Distribution (using Stats object)
    print("\n=== 1. Histogram: System Time Distribution ===")
    hist_params = {
        **common_style,
        'title': 'Distribution of System Times - PCB Manufacturing',
        'xlabel': 'Average Time in System (minutes)',
        'ylabel': 'Frequency',
        'bins': 20,
        'color': '#2E7D32',  # Manufacturing green
        'edgecolor': 'white',
        'alpha': 0.8,
        'kde': True,
        'kde_color': '#D32F2F',  # Alert red
        'kde_linewidth': 2,
        'show_stats': True,
        'stats_loc': (0.02, 0.95)
    }
    plot_histogram(Stats, 'Sink', 'GoodParts', 'TimeInSystem (average)', plot_params=hist_params)

    # 2. BOX PLOT - Server Processing Time Variability
    print("\n=== 2. Box Plot: Server Processing Time Analysis ===")
    box_params = {
        **common_style,
        'title': 'Processing Time Variability',
        'ylabel': 'Average Processing Time (minutes)',
        'xlabel': 'Replication Data',
        'scenario_colors': {
            'Placement': '#FF6F00',    # Manufacturing orange
            'Inspection': '#2196F3',   # Quality blue
            'Rework': '#F44336'        # Alert red
        },
        'notch': False,
        'show_means': True,
        'show_points': True,
        'point_alpha': 0.6,
        'grid_axis': 'y'
    }
    # Shows TimeProcessing (average) for ALL servers
    plot_box_plot(Stats, 'Server', statistic='TimeProcessing (average)', plot_params=box_params)
    plot_box_plot(Stats, 'Server', ['Placement', 'Rework'], statistic='TimeProcessing (average)', plot_params=box_params)

    # 3. BAR CHART - Server Utilization Comparison
    print("\n=== 3. Bar Chart: Server Utilization Analysis ===")
    bar_params = {
        **common_style,
        'title': 'Server Utilization - PCB Manufacturing Line',
        'scenario_colors': {  # Works for components too!
            'Placement': '#1f77b4',
            'FinePitchFast': '#ff7f0e',
            'FinePitchMedium': '#2ca02c',
            'FinePitchSlow': '#d62728',
            'Inspection': '#9467bd',
            'Rework': '#8c564b'
        },
        'ylabel': 'Utilization Rate (%)',
        'xlabel': 'Analysis Results',
        'show_values': True,
        'value_format': '.1f',
        'bar_alpha': 0.8,
        'bar_edgecolor': 'black'
    }
    plot_bar_chart(Stats, 'Server', statistic='ScheduledUtilization', plot_params=bar_params)

    bar_params_auto_colors = {
        'title': 'Server Processing Times',
        'color_palette': 'Set2'  # Use a seaborn palette
    }
    plot_bar_chart(Stats, 'Server', statistic='TimeProcessing (average)', plot_params=bar_params_auto_colors)
    plot_bar_chart(Stats, 'Server', ['FinePitchSlow', 'FinePitchMedium', 'FinePitchFast'],
                   statistic='TimeProcessing (average)', plot_params=bar_params_auto_colors)

    # 4. SMORE CHART - Multi-Server Performance Analysis
    print("\n=== 4. Smore Chart: Multi-Server Performance Comparison ===")

    # Single statistic, single server
    plot_smore_chart(Stats, 'Server', 'Inspection', 'TimeProcessing (average)',
                     plot_params={'show_histogram': True, 'dot_jitter': 0.05})

    # Single statistic, all servers
    plot_smore_chart(Stats, 'Server',
                     statistics='TimeProcessing (average)')

    # Multiple servers, multiple statistics
    plot_smore_chart(Stats, 'Server', ['Placement', 'Inspection'],
                     ['TimeProcessing (average)', 'ScheduledUtilization'])

    # 5. PIE CHART - Quality Output Distribution
    print("\n=== 5. Pie Chart: Quality Output Analysis ===")
    pie_params = {
        **common_style,
        'figsize': (8, 8),
        'title': 'PCB Quality Distribution',
        'explode': [0.0, 0.1],
        'shadow': True,
        'startangle': 45,
        'autopct': '%1.1f%%',
        'legend': True,
        'legend_loc': 'best'
    }
    plot_pie_chart(Stats, 'Sink', statistic='NumberEntered', plot_params=pie_params)
    plot_pie_chart(Stats, 'Server',
                   ['FinePitchSlow', 'FinePitchMedium', 'FinePitchFast'],
                   statistic='NumberExited',
                   plot_params=pie_params)

    # 6. VIOLIN PLOT - Processing Time Distribution
    print("\n=== 6. Violin Plot: Processing Time Distribution ===")
    plot_violin(Stats, 'Server', statistic='TimeProcessing (average)',
                plot_params={
                    'title': 'Processing Time Distribution by Server',
                    'inner': 'box',
                    'scenario_colors': {
                        'Placement': '#1f77b4',
                        'FinePitchFast': '#ff7f0e',
                        'FinePitchMedium': '#2ca02c',
                        'FinePitchSlow': '#d62728',
                        'Inspection': '#9467bd',
                        'Rework': '#8c564b'
                    }
                })

    plot_violin(Stats, 'Server', ['Inspection', 'Rework'], statistic='TimeProcessing (average)')

    # 7. SCATTER PLOT - Performance Correlations
    print("\n=== 7. Scatter Plot: Performance Correlation Analysis ===")
    plot_scatter(
        Stats,
        'Server', 'Inspection', 'ScheduledUtilization',
        'Server', 'Inspection', 'TimeProcessing (average)',
        plot_params={
            'title': 'Inspection Server: Utilization vs Processing Time',
            'alpha': 0.5,
            'marker_size': 30,
            'show_regression': True,
            'show_correlation': True
        }
    )


def main():

    # Run replications for statistical analysis
    print("\n Running multiple replications for statistical analysis...")
    run_replications(
        model=setup_model_pcb,
        steps=1800,
        num_replications=50,
        multiprocessing=True
    )

    # Create visualizations
    print("Creating visualizations")

    create_visualizations()

    print("\n All visualizations completed successfully!")


if __name__ == '__main__':
    main()
