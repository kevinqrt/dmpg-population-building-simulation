from typing import Union, List, Dict, Any, Optional

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from src.core.visualization.visualization_helpers import (
    _apply_common_styling, _get_scenario_colors, _save_figure,
    _get_data_source_type, get_comparison_data, get_replication_data,
    filter_scenarios, _get_detailed_stats, _determine_components_to_plot,
    _extract_component_values, _calculate_component_statistics, _generate_plot_title
)


def plot_bar_chart(data_source: Union[object, object, object],
                   component_type: str, component_name: Union[str, List[str]] = None,
                   statistic: str = None,
                   scenarios_to_include: Optional[List[str]] = None,
                   plot_params: Dict[str, Any] = None):
    """
    Create a bar chart comparing a statistic.

    For ExperimentRunner: Shows one component/statistic across selected scenarios
    For ReplicationRunner/Stats: Shows one statistic across selected components

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param component_type: Component type (e.g., 'Server')
    :param component_name: Component name(s) to include:
                          - None: Plot all components of this type
                          - str: Plot only this specific component
                          - List[str]: Plot only these specific components
    :param statistic: Statistic name (e.g., 'ScheduledUtilization')
    :param scenarios_to_include: Optional list of scenario names to include (experiments only)
    :param plot_params: Dictionary with customization parameters
    """
    # Determine data source type
    source_type = _get_data_source_type(data_source)

    # Initialize params with default values
    params = {
        # Figure settings
        'figsize': (10, 6),
        'title': f'{component_type} {statistic} Comparison',
        'title_fontsize': 14,
        'title_fontweight': 'bold',
        'xlabel': 'Scenario' if source_type == "experiment" else 'Component',
        'ylabel': f'{statistic} Value',
        'label_fontsize': 12,
        'tick_fontsize': 10,
        'rotation': 45,
        'ha': 'right',

        # Bar appearance
        'scenario_colors': {},  # Empty dict means auto-generate colors
        'color_palette': 'colorblind',
        'bar_alpha': 0.7,
        'bar_width': 0.8,
        'bar_edgecolor': None,
        'bar_linewidth': 0,

        # Value labels
        'show_values': True,
        'value_format': '.2f',
        'value_fontsize': 9,
        'value_fontweight': 'bold',
        'value_rotation': 0,
        'value_offset': 0.02,

        # Error bars
        'show_error_bars': True,
        'error_bar_color': 'black',
        'error_bar_alpha': 0.5,
        'error_bar_capsize': 5,

        # Min/Max lines
        'show_minmax': True,
        'minmax_color': 'red',
        'minmax_alpha': 0.5,
        'minmax_linewidth': 1.5,

        # Grid
        'grid': True,
        'grid_axis': 'y',
        'grid_alpha': 0.3,
        'grid_linestyle': '--',

        # Export
        'save_path': None,
        'dpi': 300
    }

    # Collect data based on source type
    bar_data = []

    if source_type == "experiment":
        # For experiments: Show one component across scenarios
        if component_name is None:
            print("Component name is required for experiment bar charts")
            return

        # For experiments, component_name should be a single string
        if isinstance(component_name, list):
            if len(component_name) > 1:
                print("For experiments, only one component can be analyzed at a time")
                return
            component_name = component_name[0]

        # Filter scenarios if specified
        scenarios = filter_scenarios(data_source, scenarios_to_include)
        if not scenarios:
            print("No scenarios to plot")
            return

        # Get comparison data using the existing function
        comparison_data = get_comparison_data(data_source, component_type, component_name, statistic)

        if comparison_data.empty:
            print(f"No data to plot for {component_type}.{component_name}.{statistic}")
            return

        # Filter to selected scenarios
        comparison_data = comparison_data[comparison_data['Scenario'].isin(scenarios)]

        # Convert to list of dictionaries for consistent handling
        for _, row in comparison_data.iterrows():
            bar_data.append({
                'label': row['Scenario'],
                'average': row['Average'],
                'half_width': row.get('Half-Width', 0),
                'minimum': row.get('Minimum', None),
                'maximum': row.get('Maximum', None)
            })

    else:
        # For replications/Stats: Show selected components of the type

        # Get detailed stats
        detailed_stats = _get_detailed_stats(data_source, source_type)
        if not detailed_stats:
            print("No detailed statistics available")
            return

        # Determine components to plot
        components = _determine_components_to_plot(component_name, detailed_stats, component_type)
        if not components:
            print("No components to plot")
            return

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, statistic, "Comparison", source_type
        )

        # Extract component values
        component_values = _extract_component_values(detailed_stats, components, component_type, statistic)

        # Calculate statistics
        bar_data = _calculate_component_statistics(component_values)

    if not bar_data:
        print("No data found for bar chart")
        return

    # Update with user parameters if provided
    if plot_params:
        params.update(plot_params)

    # Create figure with specified size
    plt.figure(figsize=params['figsize'])
    ax = plt.gca()

    # Define x positions
    x_pos = np.arange(len(bar_data))

    # Get labels and values
    labels = [item['label'] for item in bar_data]
    values = [item['average'] for item in bar_data]

    # Get colors for each bar
    colors = _get_scenario_colors(data_source, labels, params)

    # Plot bars with specific colors
    ax.bar(
        x_pos,
        values,
        width=params['bar_width'],
        alpha=params['bar_alpha'],
        color=colors,
        edgecolor=params['bar_edgecolor'],
        linewidth=params['bar_linewidth']
    )

    # Add error bars if requested and available
    if params['show_error_bars']:
        error_values = [item['half_width'] for item in bar_data]
        ax.errorbar(
            x_pos,
            values,
            yerr=error_values,
            fmt='none',
            capsize=params['error_bar_capsize'],
            ecolor=params['error_bar_color'],
            alpha=params['error_bar_alpha']
        )

    # Add min-max lines if requested and available
    if params['show_minmax']:
        for i, item in enumerate(bar_data):
            if item['minimum'] is not None and item['maximum'] is not None:
                ax.vlines(
                    i,
                    item['minimum'],
                    item['maximum'],
                    color=params['minmax_color'],
                    alpha=params['minmax_alpha'],
                    linewidth=params['minmax_linewidth']
                )

    # Add value labels on top of bars if requested
    if params['show_values']:
        max_value = max(values) if values else 0
        for i, v in enumerate(values):
            ax.text(
                i,
                v + max_value * params['value_offset'],  # Offset based on max value
                f"{v:{params['value_format']}}",
                ha='center',
                va='bottom',
                fontweight=params['value_fontweight'],
                fontsize=params['value_fontsize'],
                rotation=params['value_rotation']
            )

    # Set x-tick labels
    ax.set_xticks(x_pos)
    ax.set_xticklabels(
        labels,
        rotation=params['rotation'],
        ha=params['ha'],
        fontsize=params['tick_fontsize']
    )

    # Apply common styling
    _apply_common_styling(ax, params)

    # Adjust layout and margins
    plt.tight_layout()

    # Save if path provided
    _save_figure(params)

    plt.show()


def plot_histogram(data_source: Union[object, object, object],
                   component_type: str, component_name: str,
                   statistic: str,
                   scenario_name: Optional[str] = None,
                   plot_params: Dict[str, Any] = None):
    """
    Create a histogram showing the distribution of a statistic across replications.
    Works with both ExperimentRunner and ReplicationRunner data.

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param component_type: Component type (e.g., 'Server')
    :param component_name: Component name (e.g., 'ATM') - single component only
    :param statistic: Statistic name (e.g., 'ScheduledUtilization')
    :param scenario_name: Optional name of the scenario to show (for experiments)
    :param plot_params: Dictionary with customization parameters
    """
    # Validate component_name is a string
    if not isinstance(component_name, str):
        print("Error: Histogram requires a single component name (string). For multiple components, use separate plots.")
        return

    # Determine data source type
    source_type = _get_data_source_type(data_source)

    # Initialize params with default values
    params = {
        # Figure settings
        'figsize': (10, 6),
        'title': f'Distribution of {component_type} {component_name}: {statistic}',
        'title_fontsize': 14,
        'title_fontweight': 'bold',
        'xlabel': statistic,
        'ylabel': 'Frequency',
        'label_fontsize': 12,
        'tick_fontsize': 10,

        # Histogram appearance
        'bins': 'auto',
        'color': 'blue',
        'edgecolor': 'black',
        'alpha': 0.7,
        'hist_type': 'bars',

        # KDE
        'kde': True,
        'kde_color': 'red',
        'kde_linewidth': 2,

        # Statistics display
        'show_stats': True,
        'stats_loc': (0.02, 0.95),
        'stats_fontsize': 10,

        # Grid
        'grid': True,
        'grid_axis': 'both',
        'grid_alpha': 0.3,
        'grid_linestyle': '--',

        # Export
        'save_path': None,
        'dpi': 300
    }

    # For experiments, validate scenario if specified
    if source_type == "experiment" and scenario_name:
        available_scenarios = filter_scenarios(data_source, None)
        if scenario_name not in available_scenarios:
            print(f"Scenario '{scenario_name}' not found. Available scenarios: {available_scenarios}")
            return

    # Generate title
    params['title'] = _generate_plot_title(
        component_type, component_name, statistic, "Distribution", source_type
    )

    # Add specific scenario name if provided
    if source_type == "experiment" and scenario_name:
        params['title'] += f' ({scenario_name})'
    elif source_type == "experiment" and not scenario_name and hasattr(data_source, 'replication_data'):
        params['title'] += ' (All Scenarios Combined)'

    # Get individual replication values
    values = get_replication_data(data_source, component_type, component_name, statistic, scenario_name)

    if not values:
        print(f"No replication data found for {component_type}.{component_name}.{statistic}")
        if scenario_name:
            print(f"For scenario: {scenario_name}")
        return

    # Update with user parameters if provided
    if plot_params:
        params.update(plot_params)

    # Create figure
    plt.figure(figsize=params['figsize'])
    ax = plt.gca()

    if params['kde']:
        sns.histplot(
            values,
            bins=params['bins'],
            kde=True,
            color=params['color'],
            edgecolor=params['edgecolor'],
            alpha=params['alpha'],
            element=params['hist_type'],
            line_kws={'color': params['kde_color'], 'linewidth': params['kde_linewidth']},
            ax=ax
        )
    else:
        sns.histplot(
            values,
            bins=params['bins'],
            color=params['color'],
            edgecolor=params['edgecolor'],
            alpha=params['alpha'],
            element=params['hist_type'],
            ax=ax
        )

    # Add statistics annotations if requested
    if params['show_stats']:
        mean_val = np.mean(values)
        median_val = np.median(values)
        std_val = np.std(values)
        min_val = np.min(values)
        max_val = np.max(values)

        stats_text = (f"Mean: {mean_val:.4f}\n"
                      f"Median: {median_val:.4f}\n"
                      f"StdDev: {std_val:.4f}\n"
                      f"Min: {min_val:.4f}\n"
                      f"Max: {max_val:.4f}\n"
                      f"Count: {len(values)}")

        ax.annotate(
            stats_text,
            xy=params['stats_loc'],
            xycoords='axes fraction',
            va='top',
            fontsize=params['stats_fontsize'],
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.7)
        )

    # Apply common styling
    _apply_common_styling(ax, params)

    # Adjust layout
    plt.tight_layout()

    # Save if path provided
    _save_figure(params)

    plt.show()


def plot_pie_chart(data_source: Union[object, object, object],
                   component_type: str, component_name: Union[str, List[str]] = None,
                   statistic: str = None,
                   scenarios_to_include: Optional[List[str]] = None,
                   plot_params: Dict[str, Any] = None):
    """
    Create a pie chart showing the relative proportions of a statistic.

    For ExperimentRunner: Shows one component/statistic across selected scenarios
    For ReplicationRunner/Stats: Shows one statistic across selected components

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param component_type: Component type (e.g., 'Server', 'Sink')
    :param component_name: Component name(s) to include:
                          - None: Plot all components of this type
                          - str: Plot only this specific component
                          - List[str]: Plot only these specific components
    :param statistic: Statistic name (e.g., 'NumberEntered', 'TotalTimeProcessing')
    :param scenarios_to_include: Optional list of scenario names to include (experiments only)
    :param plot_params: Dictionary with customization parameters
    """
    # Determine data source type
    source_type = _get_data_source_type(data_source)

    # Initialize params with default values
    params = {
        # Figure settings
        'figsize': (10, 8),
        'title': f'{component_type} {statistic} Distribution',
        'title_fontsize': 14,
        'title_fontweight': 'bold',

        # Pie chart appearance
        'scenario_colors': {},  # Empty dict means auto-generate colors
        'color_palette': 'colorblind',
        'startangle': 90,
        'autopct': '%1.1f%%',
        'explode': None,
        'shadow': False,
        'radius': 1,

        # Value annotations
        'show_values': True,
        'value_format': '.2f',
        'value_fontsize': 9,

        # Legend
        'legend': True,
        'legend_loc': 'best',
        'legend_fontsize': 10,

        # Export
        'save_path': None,
        'dpi': 300
    }

    # Collect data based on source type
    pie_data = {}

    if source_type == "experiment":
        # For experiments: Show distribution across scenarios for one component
        if component_name is None:
            print("Component name is required for experiment pie charts")
            return

        # For experiments, component_name should be a single string
        if isinstance(component_name, list):
            if len(component_name) > 1:
                print("For experiments, only one component can be analyzed at a time")
                return
            component_name = component_name[0]

        # Filter scenarios if specified
        scenarios = filter_scenarios(data_source, scenarios_to_include)
        if not scenarios:
            print("No scenarios to plot")
            return

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, statistic, "Distribution Across Scenarios",
            source_type, bool(scenarios_to_include)
        )

        # Get comparison data for all scenarios
        comparison_data = get_comparison_data(data_source, component_type, component_name, statistic)

        if comparison_data.empty:
            print(f"No data to plot for {component_type}.{component_name}.{statistic}")
            return

        # Filter to selected scenarios
        comparison_data = comparison_data[comparison_data['Scenario'].isin(scenarios)]

        # Extract scenario names and values
        for _, row in comparison_data.iterrows():
            scenario_name = row['Scenario']
            value = row['Average']
            if value and value > 0:  # Only include positive values
                pie_data[scenario_name] = value

    else:
        # Get detailed stats
        detailed_stats = _get_detailed_stats(data_source, source_type)
        if not detailed_stats:
            print("No detailed statistics available")
            return

        # Determine components to plot
        components = _determine_components_to_plot(component_name, detailed_stats, component_type)
        if not components:
            print("No components to plot")
            return

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, statistic, "Distribution", source_type
        )

        # Extract component values
        component_values = _extract_component_values(detailed_stats, components, component_type, statistic)

        # Calculate averages for each component
        for comp_name, values in component_values.items():
            if values:
                avg_value = np.mean(values)
                if avg_value > 0:  # Only include positive values
                    pie_data[comp_name] = avg_value

    if not pie_data:
        print("No positive values found for pie chart")
        return

    # Update with user parameters if provided
    if plot_params:
        params.update(plot_params)

    # Create figure with specified size
    plt.figure(figsize=params['figsize'])
    ax = plt.gca()

    # Get labels and values
    labels = list(pie_data.keys())
    values = list(pie_data.values())

    # Get colors for each slice
    colors = _get_scenario_colors(data_source, labels, params)

    # Process explode parameter
    explode = params['explode']
    if explode is not None:
        if isinstance(explode, dict):
            # Convert from label dictionary to ordered list
            explode = [explode.get(label, 0) for label in labels]
        elif isinstance(explode, list):
            # Adjust length if needed
            if len(explode) != len(labels):
                # If explode list is shorter, pad with zeros
                explode = explode[:len(labels)] + [0] * (len(labels) - len(explode))
                # If explode list is longer, truncate
                explode = explode[:len(labels)]

    # Create the pie chart
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,  # We'll add a legend instead of labels
        colors=colors,
        autopct=params['autopct'],
        startangle=params['startangle'],
        explode=explode,
        shadow=params['shadow'],
        radius=params['radius']
    )

    # Customize autopct text
    for autotext in autotexts:
        autotext.set_fontsize(params['value_fontsize'])
        autotext.set_color('white')
        autotext.set_weight('bold')

    # Add value annotations if requested
    if params['show_values']:
        for i, (wedge, value, label) in enumerate(zip(wedges, values, labels)):
            angle = (wedge.theta2 - wedge.theta1) / 2.0 + wedge.theta1
            # Convert angle from degrees to radians for math functions
            angle_rad = np.deg2rad(angle)

            # Calculate text position (slightly outside the wedge)
            text_radius = params['radius'] * 1.1
            x = text_radius * np.cos(angle_rad)
            y = text_radius * np.sin(angle_rad)

            # Add value text
            ax.text(
                x, y,
                f"{value:{params['value_format']}}",
                ha='center',
                va='center',
                fontsize=params['value_fontsize'],
                fontweight='bold'
            )

    # Add legend if requested
    if params['legend']:
        # Create custom legend entries with both label and value
        legend_labels = [f'{label} ({value:{params["value_format"]}})' for label, value in zip(labels, values)]
        ax.legend(
            wedges,
            legend_labels,
            loc=params['legend_loc'],
            fontsize=params['legend_fontsize']
        )

    # Set title
    ax.set_title(
        params['title'],
        fontsize=params['title_fontsize'],
        fontweight=params['title_fontweight']
    )

    # Set aspect ratio to be equal
    ax.set_aspect('equal')

    # Adjust layout
    plt.tight_layout()

    # Save if path provided
    _save_figure(params)

    plt.show()


def plot_box_plot(data_source: Union[object, object, object],
                  component_type: str, component_name: Union[str, List[str]] = None,
                  statistic: str = None,
                  scenarios_to_include: Optional[List[str]] = None,
                  plot_params: Dict[str, Any] = None):
    """
    Create a box plot showing the distribution of a statistic.

    For ExperimentRunner: Shows one component/statistic across selected scenarios
    For ReplicationRunner/Stats: Shows one statistic across selected components

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param component_type: Component type (e.g., 'Server')
    :param component_name: Component name(s) to include:
                          - None: Plot all components of this type
                          - str: Plot only this specific component
                          - List[str]: Plot only these specific components
    :param statistic: Statistic name (e.g., 'ScheduledUtilization')
    :param scenarios_to_include: Optional list of scenario names to include (experiments only)
    :param plot_params: Dictionary with customization parameters
    """
    # Determine data source type
    source_type = _get_data_source_type(data_source)

    # Initialize params with default values
    params = {
        # Figure settings
        'figsize': (10, 6),
        'title': f'{component_type} {statistic} Distribution',
        'title_fontsize': 14,
        'title_fontweight': 'bold',
        'xlabel': 'Scenario' if source_type == "experiment" else 'Component',
        'ylabel': statistic,
        'label_fontsize': 12,
        'tick_fontsize': 10,
        'rotation': 45,
        'ha': 'right',

        # Box plot appearance
        'scenario_colors': {},  # Empty dict means auto-generate colors
        'color_palette': 'colorblind',
        'box_width': 0.5,
        'notch': False,
        'show_fliers': True,
        'show_means': True,

        # Individual points
        'show_points': True,
        'point_size': 4,
        'point_alpha': 0.3,
        'point_jitter': 0.03,

        # Grid
        'grid': True,
        'grid_axis': 'y',
        'grid_alpha': 0.3,
        'grid_linestyle': '--',

        # Export
        'save_path': None,
        'dpi': 300
    }

    # Collect data based on source type
    box_data = {}

    if source_type == "experiment":
        # For experiments: One component across selected scenarios
        if component_name is None:
            print("Component name is required for experiment box plots")
            return

        # For experiments, component_name should be a single string
        if isinstance(component_name, list):
            if len(component_name) > 1:
                print("For experiments, only one component can be analyzed at a time")
                return
            component_name = component_name[0]

        if not hasattr(data_source, 'replication_data') or not data_source.replication_data:
            print("No detailed replication data available. Enable store_replication_data in run_all().")
            return

        # Filter scenarios if specified
        scenarios = filter_scenarios(data_source, scenarios_to_include)
        if not scenarios:
            print("No scenarios to plot")
            return

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, statistic, "Across Scenarios",
            source_type, bool(scenarios_to_include)
        )

        # Collect data for each scenario
        for scenario_name in scenarios:
            if scenario_name not in data_source.replication_data:
                continue

            scenario_replications = data_source.replication_data[scenario_name]
            values = []

            for rep_data in scenario_replications:
                try:
                    # Extract value for this specific component
                    if component_type == 'Entity':
                        if component_type in rep_data and statistic in rep_data[component_type]:
                            values.append(rep_data[component_type][statistic])
                    else:
                        if component_type in rep_data:
                            comp_data = rep_data[component_type]
                            if isinstance(comp_data, list):
                                for comp in comp_data:
                                    name_key = 'Server' if component_type == 'Server' else 'Name'
                                    if comp.get(name_key) == component_name and statistic in comp:
                                        values.append(comp[statistic])
                            elif isinstance(comp_data, dict):
                                if component_name in comp_data and statistic in comp_data[component_name]:
                                    values.append(comp_data[component_name][statistic])
                except Exception as e:
                    print(f"Error extracting data for scenario {scenario_name}: {e}")

            if values:
                box_data[scenario_name] = values

    else:
        # Get detailed stats
        detailed_stats = _get_detailed_stats(data_source, source_type)
        if not detailed_stats:
            print("No detailed statistics available")
            return

        # Determine components to plot
        components = _determine_components_to_plot(component_name, detailed_stats, component_type)
        if not components:
            print("No components to plot")
            return

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, statistic, "Distribution", source_type
        )

        # Collect values for each component
        for comp_name in components:
            values = []
            for rep_data in detailed_stats:
                try:
                    if component_type in rep_data:
                        comp_data = rep_data[component_type]
                        if isinstance(comp_data, list):
                            for comp in comp_data:
                                name_key = 'Server' if component_type == 'Server' else 'Name'
                                if comp.get(name_key) == comp_name and statistic in comp:
                                    values.append(comp[statistic])
                        elif isinstance(comp_data, dict):
                            if comp_name in comp_data and statistic in comp_data[comp_name]:
                                values.append(comp_data[comp_name][statistic])
                except Exception as e:
                    print(f"Error extracting data for component {comp_name}: {e}")

            if values:
                box_data[comp_name] = values

    if not box_data:
        print("No data found for box plot")
        return

    # Update with user parameters if provided
    if plot_params:
        params.update(plot_params)

    # Create figure
    plt.figure(figsize=params['figsize'])
    ax = plt.gca()

    # Prepare data for boxplot
    labels = list(box_data.keys())
    data_values = [box_data[label] for label in labels]

    # Get colors
    colors = _get_scenario_colors(data_source, labels, params)

    # Create the box plot
    box_parts = ax.boxplot(
        data_values,
        labels=labels,
        patch_artist=True,
        widths=params['box_width'],
        notch=params['notch'],
        showmeans=params['show_means'],
        showfliers=params['show_fliers'],
        meanprops={'marker': 'D', 'markerfacecolor': 'white', 'markeredgecolor': 'black', 'markersize': 6}
    )

    # Customize the appearance of boxes
    for patch, color in zip(box_parts['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
        patch.set_edgecolor('black')
        patch.set_linewidth(1.2)

    # Customize other elements
    for element in ['whiskers', 'caps']:
        for item in box_parts[element]:
            item.set_color('black')
            item.set_linewidth(1.2)

    for median in box_parts['medians']:
        median.set_color('black')
        median.set_linewidth(2)

    # Add individual data points if requested
    if params['show_points']:
        for i, (label, values) in enumerate(box_data.items()):
            # Add jitter to x position
            x = np.random.normal(i + 1, params['point_jitter'], size=len(values))
            ax.scatter(
                x, values,
                color=colors[i % len(colors)],
                alpha=params['point_alpha'],
                s=params['point_size']**2,
                edgecolors='black',
                linewidths=0.5,
                zorder=3
            )

    # Set x-tick labels with rotation
    ax.set_xticklabels(
        labels,
        rotation=params['rotation'],
        ha=params['ha'],
        fontsize=params['tick_fontsize']
    )

    # Apply common styling
    _apply_common_styling(ax, params)

    # Add some padding to y-axis
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min
    ax.set_ylim(y_min - 0.05 * y_range, y_max + 0.05 * y_range)

    # Adjust layout
    plt.tight_layout()

    # Save if path provided
    _save_figure(params)

    plt.show()


def plot_violin(data_source: Union[object, object, object],
                component_type: str, component_name: Union[str, List[str]] = None,
                statistic: str = None,
                scenarios_to_include: Optional[List[str]] = None,
                plot_params: Dict[str, Any] = None):
    """
    Create a violin plot showing the distribution of a statistic.

    For ExperimentRunner: Shows distribution across replications for selected scenarios
    For ReplicationRunner/Stats: Shows distribution across replications for selected components

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param component_type: Component type (e.g., 'Server')
    :param component_name: Component name(s) to include:
                          - None: Plot all components of this type
                          - str: Plot only this specific component
                          - List[str]: Plot only these specific components
    :param statistic: Statistic name (e.g., 'ScheduledUtilization')
    :param scenarios_to_include: Optional list of scenario names to include (experiments only)
    :param plot_params: Dictionary with customization parameters
    """
    # Determine data source type
    source_type = _get_data_source_type(data_source)

    # Initialize params with default values
    params = {
        # Figure settings
        'figsize': (12, 8),
        'title': f'{component_type} {statistic} Distribution',
        'title_fontsize': 14,
        'title_fontweight': 'bold',
        'xlabel': 'Scenario' if source_type == "experiment" else 'Component',
        'ylabel': statistic,
        'label_fontsize': 12,
        'tick_fontsize': 10,
        'rotation': 45,
        'ha': 'right',

        # Violin appearance
        'scenario_colors': {},  # Empty dict means auto-generate colors
        'color_palette': 'colorblind',
        'alpha': 0.7,
        'inner': 'None',  # 'box', 'quartile', 'point', 'stick', None
        'scale': 'width',  # 'width', 'count', 'area'
        'width': 0.8,
        'linewidth': 1.5,

        # Statistical elements
        'show_box': True,
        'box_width': 0.15,
        'show_median': True,
        'show_extrema': True,

        # Additional overlays
        'show_points': False,
        'point_size': 4,
        'point_alpha': 0.5,
        'point_color': 'white',
        'jitter': True,
        'jitter_width': 0.03,

        # Grid
        'grid': True,
        'grid_axis': 'y',
        'grid_alpha': 0.3,
        'grid_linestyle': '--',

        # Export
        'save_path': None,
        'dpi': 300
    }

    # Collect data based on source type
    violin_data = {}

    if source_type == "experiment":
        # For experiments: Show distribution for one component across scenarios
        if component_name is None:
            print("Component name is required for experiment violin plots")
            return

        # For experiments, component_name should be a single string
        if isinstance(component_name, list):
            if len(component_name) > 1:
                print("For experiments, only one component can be analyzed at a time")
                return
            component_name = component_name[0]

        # Filter scenarios if specified
        scenarios = filter_scenarios(data_source, scenarios_to_include)
        if not scenarios:
            print("No scenarios to plot")
            return

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, statistic, "Distribution",
            source_type, bool(scenarios_to_include)
        )

        if not hasattr(data_source, 'replication_data') or not data_source.replication_data:
            print("No detailed replication data available. Enable store_replication_data in run_all().")
            return

        # Collect data for each scenario
        for scenario_name, scenario_replications in data_source.replication_data.items():
            # Skip scenarios not in our filter
            if scenario_name not in scenarios:
                continue

            values = []
            for rep_data in scenario_replications:
                try:
                    # Extract value for this specific component
                    if component_type == 'Entity':
                        if component_type in rep_data and statistic in rep_data[component_type]:
                            values.append(rep_data[component_type][statistic])
                    else:
                        if component_type in rep_data:
                            comp_data = rep_data[component_type]
                            if isinstance(comp_data, list):
                                for comp in comp_data:
                                    name_key = 'Server' if component_type == 'Server' else 'Name'
                                    if comp.get(name_key) == component_name and statistic in comp:
                                        values.append(comp[statistic])
                            elif isinstance(comp_data, dict):
                                if component_name in comp_data and statistic in comp_data[component_name]:
                                    values.append(comp_data[component_name][statistic])
                except Exception as e:
                    print(f"Error extracting data for scenario {scenario_name}: {e}")

            if values:
                violin_data[scenario_name] = values

    else:
        # Get detailed stats
        detailed_stats = _get_detailed_stats(data_source, source_type)
        if not detailed_stats:
            print("No detailed statistics available")
            return

        # Determine components to plot
        components = _determine_components_to_plot(component_name, detailed_stats, component_type)
        if not components:
            print("No components to plot")
            return

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, statistic, "Distribution", source_type
        )

        # Collect values for each component
        for comp_name in components:
            values = []
            for rep_data in detailed_stats:
                try:
                    if component_type in rep_data:
                        comp_data = rep_data[component_type]
                        if isinstance(comp_data, list):
                            for comp in comp_data:
                                name_key = 'Server' if component_type == 'Server' else 'Name'
                                if comp.get(name_key) == comp_name and statistic in comp:
                                    values.append(comp[statistic])
                        elif isinstance(comp_data, dict):
                            if comp_name in comp_data and statistic in comp_data[comp_name]:
                                values.append(comp_data[comp_name][statistic])
                except Exception as e:
                    print(f"Error extracting data for component {comp_name}: {e}")

            if values:
                violin_data[comp_name] = values

    if not violin_data:
        print("No data found for violin plot")
        return

    # Update with user parameters if provided
    if plot_params:
        params.update(plot_params)

    # Create figure
    plt.figure(figsize=params['figsize'])
    ax = plt.gca()

    # Prepare data for violin plot
    labels = list(violin_data.keys())
    data_values = [violin_data[label] for label in labels]
    positions = np.arange(len(labels))

    # Get colors
    colors = _get_scenario_colors(data_source, labels, params)

    # Create violin plot using matplotlib
    violin_parts = ax.violinplot(
        data_values,
        positions=positions,
        widths=params['width'],
        showmeans=params['show_median'],
        showmedians=params['show_median'],
        showextrema=params['show_extrema']
    )

    # Customize violin colors
    for i, pc in enumerate(violin_parts['bodies']):
        pc.set_facecolor(colors[i % len(colors)])
        pc.set_alpha(params['alpha'])
        pc.set_linewidth(params['linewidth'])
        pc.set_edgecolor('black')

    # Customize other violin elements
    for partname in ('cbars', 'cmins', 'cmaxes', 'cmedians', 'cmeans'):
        if partname in violin_parts:
            vp = violin_parts[partname]
            vp.set_edgecolor('black')
            vp.set_linewidth(1.5)

    # Add box plot overlay if requested
    if params['show_box'] and params['inner'] == 'box':
        box_parts = ax.boxplot(
            data_values,
            positions=positions,
            widths=params['box_width'],
            patch_artist=True,
            showfliers=False,
            showmeans=False,
            zorder=10
        )

        # Make boxes transparent
        for patch in box_parts['boxes']:
            patch.set_facecolor('white')
            patch.set_alpha(0.5)
            patch.set_edgecolor('black')
            patch.set_linewidth(1.2)

        # Customize box plot elements
        for element in ['whiskers', 'caps', 'medians']:
            for item in box_parts[element]:
                item.set_color('black')
                item.set_linewidth(1.2)

    # Add individual points if requested
    if params['show_points']:
        for i, (label, values) in enumerate(violin_data.items()):
            if params['jitter']:
                # Add jitter to x position
                x = np.random.normal(i, params['jitter_width'], size=len(values))
            else:
                x = np.full(len(values), i)

            ax.scatter(
                x, values,
                color=params['point_color'],
                alpha=params['point_alpha'],
                s=params['point_size']**2,
                edgecolors='black',
                linewidths=0.5,
                zorder=20
            )

    # Set x-tick labels
    ax.set_xticks(positions)
    ax.set_xticklabels(
        labels,
        rotation=params['rotation'],
        ha=params['ha'],
        fontsize=params['tick_fontsize']
    )

    # Apply common styling
    _apply_common_styling(ax, params)

    # Add some padding to y-axis
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min
    ax.set_ylim(y_min - 0.05 * y_range, y_max + 0.05 * y_range)

    # Adjust layout
    plt.tight_layout()

    # Save if path provided
    _save_figure(params)

    plt.show()


def plot_scatter(data_source: Union[object, object, object],
                 x_component_type: str, x_component_name: str, x_statistic: str,
                 y_component_type: str, y_component_name: str, y_statistic: str,
                 scenarios_to_include: Optional[List[str]] = None,
                 plot_params: Dict[str, Any] = None):
    """
    Create a scatter plot showing correlation between two statistics using replication data.
    Each point represents one replication value.

    For ExperimentRunner: Shows correlation across all replications, optionally filtered by scenarios
    For ReplicationRunner/Stats: Shows correlation across all replications

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param x_component_type: Component type for x-axis (e.g., 'Server')
    :param x_component_name: Component name for x-axis (e.g., 'ATM') - single component only
    :param x_statistic: Statistic name for x-axis (e.g., 'ScheduledUtilization')
    :param y_component_type: Component type for y-axis
    :param y_component_name: Component name for y-axis - single component only
    :param y_statistic: Statistic name for y-axis
    :param scenarios_to_include: Optional list of scenario names to include (experiments only)
    :param plot_params: Dictionary with customization parameters
    """
    # Validate component names are strings
    if not isinstance(x_component_name, str) or not isinstance(y_component_name, str):
        print("Error: Scatter plot requires single component names (strings) for both x and y axes.")
        return

    # Determine data source type
    source_type = _get_data_source_type(data_source)

    # Initialize params with default values
    params = {
        # Figure settings
        'figsize': (10, 8),
        'title': f'{x_statistic} vs {y_statistic}',
        'title_fontsize': 14,
        'title_fontweight': 'bold',
        'xlabel': f'{x_component_type} {x_component_name}: {x_statistic}',
        'ylabel': f'{y_component_type} {y_component_name}: {y_statistic}',
        'label_fontsize': 12,
        'tick_fontsize': 10,

        # Scatter appearance
        'scenario_colors': {},  # Empty dict means auto-generate colors
        'color_palette': 'colorblind',
        'marker': 'o',
        'marker_size': 50,
        'alpha': 0.6,
        'edgecolors': 'black',
        'linewidth': 0.5,

        # Regression line
        'show_regression': True,
        'regression_color': 'red',
        'regression_linewidth': 2,
        'regression_alpha': 0.8,
        'regression_style': '--',

        # Correlation info
        'show_correlation': True,
        'correlation_loc': (0.05, 0.95),
        'correlation_fontsize': 10,

        # Legend
        'show_legend': True,
        'legend_location': 'best',
        'legend_fontsize': 10,

        # Grid
        'grid': True,
        'grid_alpha': 0.3,
        'grid_linestyle': '--',

        # Export
        'save_path': None,
        'dpi': 300
    }

    # Generate custom title for scatter plot
    if x_component_name == y_component_name and x_component_type == y_component_type:
        # Same component, different statistics
        params['title'] = f'{x_component_type} {x_component_name}: {x_statistic} vs {y_statistic}'
    else:
        # Different components or types
        params['title'] = f'{x_component_type} {x_component_name} {x_statistic} vs {y_component_type} {y_component_name} {y_statistic}'

    # Add context based on source type and filtering
    if source_type == "experiment" and scenarios_to_include:
        params['title'] += ' (Selected Scenarios)'

    # Collect paired data points
    scatter_data = []  # List of (x, y, scenario/label) tuples

    if source_type == "experiment":
        # For experiments: collect data from each replication
        if not hasattr(data_source, 'replication_data') or not data_source.replication_data:
            print("No detailed replication data available. Enable store_replication_data in run_all().")
            return

        # Filter scenarios if specified
        scenarios = filter_scenarios(data_source, scenarios_to_include)
        if not scenarios:
            print("No scenarios to plot")
            return

        # Collect data for each scenario and replication
        for scenario_name in scenarios:
            if scenario_name not in data_source.replication_data:
                continue

            scenario_replications = data_source.replication_data[scenario_name]

            for rep_idx, rep_data in enumerate(scenario_replications):
                x_value = None
                y_value = None

                # Extract x value
                if x_component_type == 'Entity':
                    if x_component_type in rep_data and x_statistic in rep_data[x_component_type]:
                        x_value = rep_data[x_component_type][x_statistic]
                else:
                    if x_component_type in rep_data:
                        comp_data = rep_data[x_component_type]
                        if isinstance(comp_data, list):
                            for comp in comp_data:
                                name_key = 'Server' if x_component_type == 'Server' else 'Name'
                                if comp.get(name_key) == x_component_name and x_statistic in comp:
                                    x_value = comp[x_statistic]
                                    break
                        elif isinstance(comp_data, dict):
                            if x_component_name in comp_data and x_statistic in comp_data[x_component_name]:
                                x_value = comp_data[x_component_name][x_statistic]

                # Extract y value
                if y_component_type == 'Entity':
                    if y_component_type in rep_data and y_statistic in rep_data[y_component_type]:
                        y_value = rep_data[y_component_type][y_statistic]
                else:
                    if y_component_type in rep_data:
                        comp_data = rep_data[y_component_type]
                        if isinstance(comp_data, list):
                            for comp in comp_data:
                                name_key = 'Server' if y_component_type == 'Server' else 'Name'
                                if comp.get(name_key) == y_component_name and y_statistic in comp:
                                    y_value = comp[y_statistic]
                                    break
                        elif isinstance(comp_data, dict):
                            if y_component_name in comp_data and y_statistic in comp_data[y_component_name]:
                                y_value = comp_data[y_component_name][y_statistic]

                # Add to scatter data if both values found
                if x_value is not None and y_value is not None:
                    scatter_data.append((x_value, y_value, scenario_name))

    else:
        # Get detailed stats
        detailed_stats = _get_detailed_stats(data_source, source_type)
        if not detailed_stats:
            print("No detailed statistics available")
            return

        # Collect paired values from each replication
        for rep_idx, rep_data in enumerate(detailed_stats):
            x_value = None
            y_value = None

            # Extract x value
            if x_component_type == 'Entity':
                if x_component_type in rep_data and x_statistic in rep_data[x_component_type]:
                    x_value = rep_data[x_component_type][x_statistic]
            else:
                if x_component_type in rep_data:
                    comp_data = rep_data[x_component_type]
                    if isinstance(comp_data, list):
                        for comp in comp_data:
                            name_key = 'Server' if x_component_type == 'Server' else 'Name'
                            if comp.get(name_key) == x_component_name and x_statistic in comp:
                                x_value = comp[x_statistic]
                                break
                    elif isinstance(comp_data, dict):
                        if x_component_name in comp_data and x_statistic in comp_data[x_component_name]:
                            x_value = comp_data[x_component_name][x_statistic]

            # Extract y value
            if y_component_type == 'Entity':
                if y_component_type in rep_data and y_statistic in rep_data[y_component_type]:
                    y_value = rep_data[y_component_type][y_statistic]
            else:
                if y_component_type in rep_data:
                    comp_data = rep_data[y_component_type]
                    if isinstance(comp_data, list):
                        for comp in comp_data:
                            name_key = 'Server' if y_component_type == 'Server' else 'Name'
                            if comp.get(name_key) == y_component_name and y_statistic in comp:
                                y_value = comp[y_statistic]
                                break
                    elif isinstance(comp_data, dict):
                        if y_component_name in comp_data and y_statistic in comp_data[y_component_name]:
                            y_value = comp_data[y_component_name][y_statistic]

            # Add to scatter data if both values found
            if x_value is not None and y_value is not None:
                scatter_data.append((x_value, y_value, f'Rep_{rep_idx}'))

    if not scatter_data:
        print("No paired data found for scatter plot")
        return

    # Update with user parameters if provided
    if plot_params:
        params.update(plot_params)

    # Create figure
    plt.figure(figsize=params['figsize'])
    ax = plt.gca()

    # Separate data by scenario/label for coloring
    if source_type == "experiment":
        # Group by scenario
        scenario_groups = {}
        for x, y, scenario in scatter_data:
            if scenario not in scenario_groups:
                scenario_groups[scenario] = {'x': [], 'y': []}
            scenario_groups[scenario]['x'].append(x)
            scenario_groups[scenario]['y'].append(y)

        # Get colors for scenarios
        scenarios = list(scenario_groups.keys())
        colors = _get_scenario_colors(data_source, scenarios, params)

        # Plot each scenario with its color
        for i, (scenario, data) in enumerate(scenario_groups.items()):
            ax.scatter(
                data['x'], data['y'],
                color=colors[i],
                s=params['marker_size'],
                marker=params['marker'],
                alpha=params['alpha'],
                edgecolors=params['edgecolors'],
                linewidth=params['linewidth'],
                label=scenario
            )
    else:
        # For replications, use a single color or gradient
        x_values = [point[0] for point in scatter_data]
        y_values = [point[1] for point in scatter_data]

        # Use gradient coloring based on replication order
        colors = plt.cm.viridis(np.linspace(0, 1, len(x_values)))

        ax.scatter(
            x_values, y_values,
            c=colors,
            s=params['marker_size'],
            marker=params['marker'],
            alpha=params['alpha'],
            edgecolors=params['edgecolors'],
            linewidth=params['linewidth']
        )

    # Collect all x and y values for regression and correlation
    all_x = np.array([point[0] for point in scatter_data])
    all_y = np.array([point[1] for point in scatter_data])

    # Add regression line if requested
    if params['show_regression'] and len(all_x) > 1:
        # Calculate linear regression
        coeffs = np.polyfit(all_x, all_y, 1)
        regression_line = np.poly1d(coeffs)

        # Create x values for smooth line
        x_range = np.linspace(all_x.min(), all_x.max(), 100)

        # Plot regression line
        ax.plot(
            x_range,
            regression_line(x_range),
            color=params['regression_color'],
            linewidth=params['regression_linewidth'],
            alpha=params['regression_alpha'],
            linestyle=params['regression_style'],
            label=f'y = {coeffs[0]:.3f}x + {coeffs[1]:.3f}'
        )

    # Add correlation coefficient if requested
    if params['show_correlation'] and len(all_x) > 1:
        from scipy.stats import pearsonr, spearmanr

        # Calculate both Pearson and Spearman correlations
        pearson_r, pearson_p = pearsonr(all_x, all_y)
        spearman_r, spearman_p = spearmanr(all_x, all_y)

        correlation_text = (f'Pearson r = {pearson_r:.3f} (p = {pearson_p:.3f})\n'
                            f'Spearman r = {spearman_r:.3f} (p = {spearman_p:.3f})\n'
                            f'n = {len(all_x)} points')

        ax.text(
            params['correlation_loc'][0],
            params['correlation_loc'][1],
            correlation_text,
            transform=ax.transAxes,
            fontsize=params['correlation_fontsize'],
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
        )

    # Add legend if requested
    if params['show_legend'] and source_type == "experiment":
        ax.legend(
            loc=params['legend_location'],
            fontsize=params['legend_fontsize']
        )

    # Apply common styling
    _apply_common_styling(ax, params)

    # Adjust layout
    plt.tight_layout()

    # Save if path provided
    _save_figure(params)

    plt.show()


def plot_smore_chart(data_source: Union[object, object, object],
                     component_type: str, component_name: Union[str, List[str]] = None,
                     statistics: Union[str, List[str]] = None,
                     scenarios_to_include: Optional[List[str]] = None,
                     plot_params: Dict[str, Any] = None):
    """
    Create a SMORE plot (Simio Measure of Risk and Error) showing statistical spread,
    confidence intervals, and replication results for simulation metrics.

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param component_type: Component type (e.g., 'Server')
    :param component_name: Component name(s) to include:
                          - None: Plot all components of this type (for replications/Stats only)
                          - str: Plot only this specific component
                          - List[str]: Plot only these specific components (for replications/Stats only)
    :param statistics: Single statistic or list of statistics to display
    :param scenarios_to_include: Optional list of scenario names to include (experiments only)
    :param plot_params: Dictionary with customization parameters
    """
    # Handle single statistic input
    if isinstance(statistics, str):
        statistics = [statistics]

    if not statistics:
        print("Error: At least one statistic must be specified")
        return

    # Determine data source type
    source_type = _get_data_source_type(data_source)

    # Initialize params with SMORE-specific defaults
    params = {
        # Figure settings
        'figsize': (14, 8),
        'title': f'SMORE Analysis for {component_type}',
        'title_fontsize': 16,
        'title_fontweight': 'bold',
        'xlabel': 'Metric',
        'ylabel': 'Value',
        'label_fontsize': 12,
        'tick_fontsize': 10,
        'rotation': 45,
        'ha': 'right',

        # SMORE-specific parameters
        'percentiles': (25, 75),  # Lower and upper percentiles for box
        'confidence_level': 0.95,  # Confidence interval level
        'show_replication_dots': True,  # Show individual replication values
        'show_histogram': False,  # Show histogram in background
        'show_mean': True,  # Show mean marker
        'show_median': True,  # Show median line
        'show_whiskers': True,  # Show min/max whiskers
        'show_confidence_interval': True,  # Show CI for mean

        # Visual settings
        'box_width': 0.4,
        'box_alpha': 0.6,
        'ci_linewidth': 3,
        'ci_color': 'darkred',
        'mean_marker': 'D',
        'mean_markersize': 10,
        'mean_color': 'red',
        'median_color': 'black',
        'median_linewidth': 2,
        'dot_size': 30,
        'dot_alpha': 0.6,
        'dot_jitter': 0.1,
        'whisker_linewidth': 1.5,
        'whisker_color': 'gray',

        # Colors
        'scenario_colors': {},
        'color_palette': 'Set2',

        # Grid
        'grid': True,
        'grid_axis': 'y',
        'grid_alpha': 0.2,
        'grid_linestyle': '--',

        # Layout
        'group_spacing': 1.0,  # Space between different statistics
        'scenario_spacing': 0.5,  # Space between scenarios within a statistic

        # Export
        'save_path': None,
        'dpi': 300,

        # Custom stat labels
        'stat_labels': {}
    }

    # Collect replication data
    smore_data = {}  # {stat: {scenario/component: [values]}}

    if source_type == "experiment":
        # For experiments: collect data for each statistic and scenario
        if component_name is None:
            print("Component name is required for experiment SMORE plots")
            return

        # For experiments, component_name should be a single string
        if isinstance(component_name, list):
            if len(component_name) > 1:
                print("For experiments, only one component can be analyzed at a time")
                return
            component_name = component_name[0]

        if not hasattr(data_source, 'replication_data') or not data_source.replication_data:
            print("No detailed replication data available. Enable store_replication_data in run_all().")
            return

        # Filter scenarios if specified
        scenarios = filter_scenarios(data_source, scenarios_to_include)
        if not scenarios:
            print("No scenarios to plot")
            return

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, 'Multiple Statistics' if len(statistics) > 1 else statistics[0],
            "SMORE Analysis", source_type, bool(scenarios_to_include)
        )

        for stat in statistics:
            smore_data[stat] = {}

            for scenario_name in scenarios:
                if scenario_name not in data_source.replication_data:
                    continue

                scenario_replications = data_source.replication_data[scenario_name]
                values = []

                for rep_data in scenario_replications:
                    try:
                        if component_type == 'Entity':
                            if component_type in rep_data and stat in rep_data[component_type]:
                                values.append(rep_data[component_type][stat])
                        else:
                            if component_type in rep_data:
                                comp_data = rep_data[component_type]
                                if isinstance(comp_data, list):
                                    for comp in comp_data:
                                        name_key = 'Server' if component_type == 'Server' else 'Name'
                                        if comp.get(name_key) == component_name and stat in comp:
                                            values.append(comp[stat])
                                elif isinstance(comp_data, dict):
                                    if component_name in comp_data and stat in comp_data[component_name]:
                                        values.append(comp_data[component_name][stat])
                    except Exception as e:
                        print(f"Error extracting data: {e}")

                if values:
                    smore_data[stat][scenario_name] = values

    else:
        # Get detailed stats
        detailed_stats = _get_detailed_stats(data_source, source_type)
        if not detailed_stats:
            print("No detailed statistics available")
            return

        # Determine components to plot
        if component_name is None:
            # Get all components of this type
            components = _determine_components_to_plot(None, detailed_stats, component_type)
            if not components:
                print("No components to plot")
                return
        else:
            # Use specified component(s)
            if isinstance(component_name, str):
                components = [component_name]
            else:  # List of strings
                components = component_name

        # Generate title
        params['title'] = _generate_plot_title(
            component_type, component_name, 'Multiple Statistics' if len(statistics) > 1 else statistics[0],
            "SMORE Analysis", source_type
        )

        # For each statistic, collect data for each component
        for stat in statistics:
            smore_data[stat] = {}

            for comp_name in components:
                values = []
                for rep_data in detailed_stats:
                    try:
                        if component_type == 'Entity':
                            if component_type in rep_data and stat in rep_data[component_type]:
                                values.append(rep_data[component_type][stat])
                        else:
                            if component_type in rep_data:
                                comp_data = rep_data[component_type]
                                if isinstance(comp_data, list):
                                    for comp in comp_data:
                                        name_key = 'Server' if component_type == 'Server' else 'Name'
                                        if comp.get(name_key) == comp_name and stat in comp:
                                            values.append(comp[stat])
                                elif isinstance(comp_data, dict):
                                    if comp_name in comp_data and stat in comp_data[comp_name]:
                                        values.append(comp_data[comp_name][stat])
                    except Exception as e:
                        print(f"Error extracting data: {e}")

                if values:
                    smore_data[stat][comp_name] = values

    if not smore_data:
        print("No data found for SMORE plot")
        return

    # Update with user parameters if provided
    if plot_params:
        params.update(plot_params)

    # Create figure
    plt.figure(figsize=params['figsize'])
    ax = plt.gca()

    # Calculate positions
    scenarios_per_stat = [len(scenarios) for scenarios in smore_data.values()]
    max_scenarios = max(scenarios_per_stat) if scenarios_per_stat else 0

    # Position counter
    current_pos = 0
    all_positions = []
    all_labels = []

    # Import required statistics functions
    from scipy import stats as scipy_stats

    # Plot each statistic group
    for stat_idx, (stat_name, scenario_data) in enumerate(smore_data.items()):
        stat_label = params['stat_labels'].get(stat_name, stat_name)

        # Get scenarios and their colors
        scenarios = list(scenario_data.keys())
        colors = _get_scenario_colors(data_source, scenarios, params)

        for scenario_idx, (scenario_name, values) in enumerate(scenario_data.items()):
            if not values:
                continue

            # Calculate statistics
            values_array = np.array(values)
            mean_val = np.mean(values_array)
            median_val = np.median(values_array)
            min_val = np.min(values_array)
            max_val = np.max(values_array)

            # Calculate percentiles
            lower_percentile = np.percentile(values_array, params['percentiles'][0])
            upper_percentile = np.percentile(values_array, params['percentiles'][1])

            # Calculate confidence interval for mean using t-distribution
            n = len(values_array)
            sem = scipy_stats.sem(values_array)
            ci_bounds = scipy_stats.t.interval(
                params['confidence_level'],
                n - 1,
                loc=mean_val,
                scale=sem
            )

            # Position for this bar
            pos = current_pos + scenario_idx * params['scenario_spacing']
            all_positions.append(pos)

            # Label
            if source_type == "experiment" or component_name is None or isinstance(component_name, list):
                label = f"{stat_label}\n{scenario_name}"
            else:
                label = stat_label
            all_labels.append(label)

            # Get color
            color = colors[scenario_idx % len(colors)]

            # 1. Draw box (IQR)
            box_height = upper_percentile - lower_percentile
            box = plt.Rectangle(
                (pos - params['box_width'] / 2, lower_percentile),
                params['box_width'],
                box_height,
                facecolor=color,
                alpha=params['box_alpha'],
                edgecolor='black',
                linewidth=1.5
            )
            ax.add_patch(box)

            # 2. Draw median line
            if params['show_median']:
                ax.hlines(
                    median_val,
                    pos - params['box_width'] / 2,
                    pos + params['box_width'] / 2,
                    colors=params['median_color'],
                    linewidth=params['median_linewidth'],
                    zorder=5
                )

            # 3. Draw mean marker
            if params['show_mean']:
                ax.scatter(
                    pos, mean_val,
                    marker=params['mean_marker'],
                    s=params['mean_markersize']**2,
                    color=params['mean_color'],
                    edgecolor='black',
                    linewidth=1.5,
                    zorder=10
                )

            # 4. Draw whiskers (min/max)
            if params['show_whiskers']:
                # Lower whisker
                ax.vlines(
                    pos, min_val, lower_percentile,
                    colors=params['whisker_color'],
                    linewidth=params['whisker_linewidth'],
                    linestyle='--'
                )
                # Upper whisker
                ax.vlines(
                    pos, upper_percentile, max_val,
                    colors=params['whisker_color'],
                    linewidth=params['whisker_linewidth'],
                    linestyle='--'
                )
                # Min/Max caps
                cap_width = params['box_width'] * 0.3
                ax.hlines(min_val, pos - cap_width / 2, pos + cap_width / 2,
                          colors=params['whisker_color'], linewidth=params['whisker_linewidth'])
                ax.hlines(max_val, pos - cap_width / 2, pos + cap_width / 2,
                          colors=params['whisker_color'], linewidth=params['whisker_linewidth'])

            # 5. Draw confidence interval for mean
            if params['show_confidence_interval']:
                ax.vlines(
                    pos, ci_bounds[0], ci_bounds[1],
                    colors=params['ci_color'],
                    linewidth=params['ci_linewidth'],
                    zorder=8
                )
                # CI caps
                ci_cap_width = params['box_width'] * 0.5
                ax.hlines(ci_bounds[0], pos - ci_cap_width / 2, pos + ci_cap_width / 2,
                          colors=params['ci_color'], linewidth=params['ci_linewidth'])
                ax.hlines(ci_bounds[1], pos - ci_cap_width / 2, pos + ci_cap_width / 2,
                          colors=params['ci_color'], linewidth=params['ci_linewidth'])

            # 6. Draw individual replication dots
            if params['show_replication_dots']:
                # Add jitter to x position
                jitter = np.random.uniform(-params['dot_jitter'], params['dot_jitter'], size=len(values_array))
                x_positions = pos + jitter

                ax.scatter(
                    x_positions, values_array,
                    s=params['dot_size'],
                    color=color,
                    alpha=params['dot_alpha'],
                    edgecolor='black',
                    linewidth=0.5,
                    zorder=3
                )

            # 7. Optional: Add histogram in background
            if params['show_histogram']:
                # Create histogram data
                hist, bins = np.histogram(values_array, bins=10)
                hist = hist / hist.max() * params['box_width'] * 0.8  # Normalize

                # Draw histogram bars
                for i, (h, b) in enumerate(zip(hist, bins[:-1])):
                    rect = plt.Rectangle(
                        (pos - h / 2, b),
                        h,
                        bins[i + 1] - b,
                        facecolor=color,
                        alpha=0.2,
                        zorder=1
                    )
                    ax.add_patch(rect)

        # Move position for next statistic group
        current_pos += max_scenarios * params['scenario_spacing'] + params['group_spacing']

    # Set x-axis
    ax.set_xticks(all_positions)
    ax.set_xticklabels(all_labels, rotation=params['rotation'], ha=params['ha'])

    # Apply common styling
    _apply_common_styling(ax, params)

    # Add legend explaining the components
    legend_elements = []
    from matplotlib.patches import Rectangle
    from matplotlib.lines import Line2D

    legend_elements.append(Rectangle((0, 0), 1, 1, facecolor='gray', alpha=0.6, label='IQR Box'))
    legend_elements.append(Line2D([0], [0], color='black', linewidth=2, label='Median'))
    legend_elements.append(Line2D([0], [0], marker='D', color='w', markerfacecolor='red', markersize=8, label='Mean'))
    legend_elements.append(Line2D([0], [0], color=params['ci_color'], linewidth=3, label=f'{int(params["confidence_level"] * 100)}% CI'))
    legend_elements.append(Line2D([0], [0], color='gray', linestyle='--', label='Min/Max'))

    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

    # Adjust layout
    plt.tight_layout()

    # Save if path provided
    _save_figure(params)

    plt.show()
