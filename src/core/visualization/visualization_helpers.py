from typing import List, Dict, Any, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.core.global_imports import Stats


def _apply_common_styling(ax, params: Dict[str, Any]):
    """
    Apply common styling elements to a matplotlib axis.

    :param ax: Matplotlib axis object
    :param params: Dictionary of styling parameters
    """
    # Set title if provided
    title = params.get('title')
    if title:
        ax.set_title(
            title,
            fontsize=params.get('title_fontsize', 14),
            fontweight=params.get('title_fontweight', 'bold')
        )

    # Set axis labels if provided
    xlabel = params.get('xlabel')
    if xlabel:
        ax.set_xlabel(
            xlabel,
            fontsize=params.get('label_fontsize', 12)
        )

    ylabel = params.get('ylabel')
    if ylabel:
        ax.set_ylabel(
            ylabel,
            fontsize=params.get('label_fontsize', 12)
        )

    # Set tick label font size
    tick_fontsize = params.get('tick_fontsize', 10)
    ax.tick_params(axis='both', labelsize=tick_fontsize)

    # Add grid if requested
    if params.get('grid', True):
        ax.grid(
            axis=params.get('grid_axis', 'y'),
            alpha=params.get('grid_alpha', 0.3),
            linestyle=params.get('grid_linestyle', '--')
        )


def _get_scenario_colors(data_source, scenarios, params: Dict[str, Any]) -> List:
    """
    Determine colors for each scenario/component based on provided parameters.

    :param data_source: The data source (ExperimentRunner, ReplicationRunner, etc.)
    :param scenarios: List of scenario names or component names
    :param params: Dictionary of styling parameters
    :return: List of colors corresponding to scenarios/components
    """
    # Use user-provided colors if available
    if 'scenario_colors' in params and params['scenario_colors']:
        # Generate colors based on user-provided mapping
        scenario_colors = params['scenario_colors']

        # If user provided colors, use them
        colors = []
        for s in scenarios:
            if s in scenario_colors:
                colors.append(scenario_colors[s])
            else:
                # Use default color palette for unmapped items
                colors.append(None)  # Will be filled in below

        # Fill in missing colors with palette colors
        if None in colors:
            # Get palette colors for missing entries
            try:
                import seaborn as sns
                palette_name = params.get('color_palette', 'colorblind')
                palette = sns.color_palette(palette_name, n_colors=len([c for c in colors if c is None]))
                palette_idx = 0
                for i, color in enumerate(colors):
                    if color is None:
                        colors[i] = palette[palette_idx]
                        palette_idx += 1
            except (ImportError, ValueError):
                # Fallback to matplotlib colors
                cmap = plt.cm.get_cmap('tab10')
                color_idx = 0
                for i, color in enumerate(colors):
                    if color is None:
                        colors[i] = cmap(color_idx % 10)
                        color_idx += 1

        return colors

    # Auto-generate colors using the specified palette
    try:
        import seaborn as sns
        palette_name = params.get('color_palette', 'colorblind')

        # Use different palettes based on number of items
        if len(scenarios) <= 10:
            # For small numbers, use distinct categorical colors
            if palette_name == 'colorblind':
                palette = sns.color_palette('colorblind', n_colors=len(scenarios))
            else:
                palette = sns.color_palette(palette_name, n_colors=len(scenarios))
        else:
            # For larger numbers, use a continuous palette
            palette = sns.color_palette('husl', n_colors=len(scenarios))

        return list(palette)
    except (ImportError, ValueError):
        # Fallback to matplotlib colors if seaborn not available or palette invalid
        if len(scenarios) <= 10:
            cmap = plt.cm.get_cmap('tab10')
        else:
            cmap = plt.cm.get_cmap('tab20')
        return [cmap(i % 20) for i in range(len(scenarios))]


def _save_figure(params: Dict[str, Any]):
    """
    Save the figure if a save path is provided in params.

    :param params: Dictionary of parameters which may include save settings
    """
    save_path = params.get('save_path')
    if save_path:
        dpi = params.get('dpi', 300)
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"Figure saved to {save_path}")


def _get_data_source_type(data_source) -> str:
    """
    Detect the type of data source.

    :param data_source: The data source to analyze
    :return: String indicating the type ('experiment', 'replication', 'replication_stats', 'unknown')
    """
    # Import here to avoid circular imports
    try:
        from src.core.simulation.experiments.experiment import ExperimentRunner
        from src.core.simulation.replication import ReplicationRunner

        if isinstance(data_source, ExperimentRunner):
            return "experiment"
        elif isinstance(data_source, ReplicationRunner):
            return "replication"
    except ImportError:
        pass

    # Check if it's the Stats class or instance with detailed stats
    if hasattr(data_source, 'all_detailed_stats') and data_source.all_detailed_stats:
        return "replication_stats"
    else:
        return "unknown"


def get_comparison_data(data_source, component_type: str, component_name: str,
                        statistic: str) -> pd.DataFrame:
    """
    Unified function to get comparison data from different data sources.
    Moved from ExperimentRunner since it's primarily used for visualization.

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param component_type: Component type (e.g., 'Server')
    :param component_name: Component name (e.g., 'ATM')
    :param statistic: Statistic name (e.g., 'ScheduledUtilization')
    :return: DataFrame with comparison data
    """

    source_type = _get_data_source_type(data_source)

    if source_type == "experiment":
        # For ExperimentRunner, get data from its scenarios
        filtered_data = []

        # Loop through all scenarios and extract data from the MultiIndex
        for scenario in data_source.scenarios:
            if not hasattr(scenario, 'results') or scenario.results is None or scenario.results.empty:
                continue

            scenario_results = scenario.results

            # Check if we have a MultiIndex in the scenario results
            if isinstance(scenario_results.index, pd.MultiIndex) and len(scenario_results.index.names) >= 3:
                # We have a MultiIndex with Type, Name, Stat
                try:
                    # Create a row for this scenario with the data we need
                    row_data = {
                        'Scenario': scenario.name,
                    }

                    # Try to get values for all the columns we expect
                    for col in ['Average', 'Minimum', 'Maximum', 'Half-Width']:
                        if col in scenario_results.columns:
                            try:
                                value = scenario_results.loc[(component_type, component_name, statistic), col]
                                row_data[col] = value
                            except (KeyError, TypeError):
                                pass

                    for param_name, param in scenario.parameters.items():
                        clean_name = param_name.replace('.', '_').replace(':', '_')
                        row_data[f'Param_{clean_name}'] = param.value

                    if any(key in row_data for key in ['Average', 'Minimum', 'Maximum', 'Half-Width']):
                        filtered_data.append(row_data)

                except Exception as e:
                    print(f"Error accessing data for {component_type}.{component_name}.{statistic} in scenario {scenario.name}: {e}")
            else:
                try:
                    mask = True
                    if 'Type' in scenario_results.columns and component_type is not None:
                        mask = mask & (scenario_results['Type'] == component_type)
                    if 'Name' in scenario_results.columns and component_name is not None:
                        mask = mask & (scenario_results['Name'] == component_name)
                    if 'Stat' in scenario_results.columns and statistic is not None:
                        mask = mask & (scenario_results['Stat'] == statistic)

                    filtered = scenario_results[mask]
                    if not filtered.empty:
                        row_data = filtered.iloc[0].to_dict()
                        filtered_data.append(row_data)
                except Exception as e:
                    print(f"Error filtering scenario {scenario.name}: {e}")

        # Create DataFrame from filtered data
        if filtered_data:
            result = pd.DataFrame(filtered_data)
            # Ensure the DataFrame has a proper index
            if 'Scenario' in result.columns:
                result = result.set_index('Scenario', drop=False)

            # Reorder columns for better readability
            cols = ['Scenario']
            if 'Average' in result.columns:
                cols.append('Average')
            if 'Minimum' in result.columns:
                cols.append('Minimum')
            if 'Maximum' in result.columns:
                cols.append('Maximum')
            if 'Half-Width' in result.columns:
                cols.append('Half-Width')

            # Add parameter columns
            param_cols = [col for col in result.columns if col.startswith('Param_')]
            cols.extend(param_cols)

            # Ensure we only select columns that exist
            cols = [col for col in cols if col in result.columns]

            # Create the comparison DataFrame
            return result[cols].reset_index(drop=True)
        else:
            print(f"No data found for {component_type}.{component_name}.{statistic}")
            return pd.DataFrame()

    elif source_type == "replication" or source_type == "replication_stats":
        # For ReplicationRunner or Stats, create comparison data from detailed stats
        # Get the data source
        if source_type == "replication":
            detailed_stats = data_source.detailed_replication_data
        else:
            detailed_stats = Stats.all_detailed_stats

        if not detailed_stats:
            print(f"No detailed statistics available for {component_type}.{component_name}.{statistic}")
            return pd.DataFrame()

        # Extract values
        values = []
        for rep_data in detailed_stats:
            try:
                # Find the statistic in the detailed data
                if component_type == 'Entity':
                    # Entity stats are stored differently
                    if component_type in rep_data and statistic in rep_data[component_type]:
                        values.append(rep_data[component_type][statistic])
                else:
                    # Find the component in the component type
                    if component_type in rep_data:
                        comp_data = rep_data[component_type]
                        if isinstance(comp_data, list):
                            for comp in comp_data:
                                name_key = 'Server' if 'Server' in comp else 'Name'
                                if comp.get(name_key) == component_name and statistic in comp:
                                    values.append(comp[statistic])
                        elif isinstance(comp_data, dict):
                            if component_name in comp_data and statistic in comp_data[component_name]:
                                values.append(comp_data[component_name][statistic])
                            # Also check direct access for sink/source
                            elif comp_data.get('Name') == component_name and statistic in comp_data:
                                values.append(comp_data[statistic])
            except Exception as e:
                print(f"Error extracting data: {e}")

        if not values:
            print(f"No data found for {component_type}.{component_name}.{statistic}")
            return pd.DataFrame()

        # Calculate statistics
        avg_value = np.mean(values)
        min_value = np.min(values)
        max_value = np.max(values)

        # Calculate confidence interval
        std_dev = np.std(values, ddof=1) if len(values) > 1 else 0
        from scipy.stats import t
        t_val = t.ppf(0.975, len(values) - 1) if len(values) > 1 else 0
        half_width = t_val * (std_dev / np.sqrt(len(values))) if len(values) > 1 else 0

        # Create a DataFrame similar to what ExperimentRunner.get_comparison_data returns
        return pd.DataFrame({
            'Scenario': ["Replication Results"],
            'Average': [avg_value],
            'Minimum': [min_value],
            'Maximum': [max_value],
            'Half-Width': [half_width]
        })

    else:
        print("Unknown data source type. Please provide an ExperimentRunner or ReplicationRunner.")
        return pd.DataFrame()


def get_replication_data(data_source, component_type: str, component_name: str,
                         statistic: str, scenario_name: Optional[str] = None) -> List[float]:
    """
    Get individual replication values for a statistic.

    :param data_source: Either an ExperimentRunner, ReplicationRunner, or Stats object
    :param component_type: Component type (e.g., 'Server')
    :param component_name: Component name (e.g., 'ATM')
    :param statistic: Statistic name (e.g., 'ScheduledUtilization')
    :param scenario_name: Optional scenario name for experiment data
    :return: List of values from individual replications
    """
    source_type = _get_data_source_type(data_source)
    values = []

    if source_type == "experiment":
        # For ExperimentRunner, use replication_data
        if not hasattr(data_source, 'replication_data') or not data_source.replication_data:
            print("No detailed replication data available. Enable store_replication_data in run_all().")
            return []

        # If scenario_name provided, only use that scenario's data
        scenarios_to_process = [scenario_name] if scenario_name else data_source.replication_data.keys()

        for scenario in scenarios_to_process:
            if scenario not in data_source.replication_data:
                continue

            scenario_data = data_source.replication_data[scenario]

            for rep_data in scenario_data:
                try:
                    # Extract values using the same logic as in get_comparison_data
                    if component_type == 'Entity':
                        if component_type in rep_data and statistic in rep_data[component_type]:
                            values.append(rep_data[component_type][statistic])
                    else:
                        if component_type in rep_data:
                            comp_data = rep_data[component_type]
                            if isinstance(comp_data, list):
                                for comp in comp_data:
                                    name_key = 'Server' if 'Server' in comp else 'Name'
                                    if comp.get(name_key) == component_name and statistic in comp:
                                        values.append(comp[statistic])
                            elif isinstance(comp_data, dict):
                                if component_name in comp_data and statistic in comp_data[component_name]:
                                    values.append(comp_data[component_name][statistic])
                                elif comp_data.get('Name') == component_name and statistic in comp_data:
                                    values.append(comp_data[statistic])
                except Exception as e:
                    print(f"Error extracting data: {e}")

    elif source_type == "replication" or source_type == "replication_stats":
        # Get the data source
        if source_type == "replication":
            detailed_stats = data_source.detailed_replication_data
        else:
            detailed_stats = Stats.all_detailed_stats

        if not detailed_stats:
            print(f"No detailed statistics available for {component_type}.{component_name}.{statistic}")
            return []

        # Extract values using the same logic as above
        for rep_data in detailed_stats:
            try:
                if component_type == 'Entity':
                    if component_type in rep_data and statistic in rep_data[component_type]:
                        values.append(rep_data[component_type][statistic])
                else:
                    if component_type in rep_data:
                        comp_data = rep_data[component_type]
                        if isinstance(comp_data, list):
                            for comp in comp_data:
                                name_key = 'Server' if 'Server' in comp else 'Name'
                                if comp.get(name_key) == component_name and statistic in comp:
                                    values.append(comp[statistic])
                        elif isinstance(comp_data, dict):
                            if component_name in comp_data and statistic in comp_data[component_name]:
                                values.append(comp_data[component_name][statistic])
                            elif comp_data.get('Name') == component_name and statistic in comp_data:
                                values.append(comp_data[statistic])
            except Exception as e:
                print(f"Error extracting data: {e}")

    return values


def get_multi_statistic_data(data_source, component_type: str, component_name: str,
                             statistics: List[str]) -> pd.DataFrame:
    """
    Compare multiple statistics for the same component across all scenarios.
    Moved from ExperimentRunner since it's primarily used for visualization.

    :param data_source: The data source (ExperimentRunner, ReplicationRunner, etc.)
    :param component_type: Component type (e.g., 'Server')
    :param component_name: Component name (e.g., 'ATM')
    :param statistics: List of statistics to compare
    :return: DataFrame with comparison of multiple statistics
    """
    result_df = None

    # For each statistic, get its data across all scenarios
    for statistic in statistics:
        stat_comparison = get_comparison_data(data_source, component_type, component_name, statistic)

        if not stat_comparison.empty:
            # Rename 'Average' column to the statistic name for clarity
            stat_comparison = stat_comparison.rename(columns={'Average': statistic})

            # Keep only the statistic and scenario columns
            columns_to_keep = ['Scenario', statistic]
            # Include parameters if they exist
            param_cols = [col for col in stat_comparison.columns if col.startswith('Param_')]
            columns_to_keep.extend(param_cols)

            # Filter to only needed columns
            stat_comparison = stat_comparison[columns_to_keep]

            if result_df is None:
                # For the first statistic, keep all columns
                result_df = stat_comparison
            else:
                # For subsequent statistics, merge on Scenario and parameter columns
                merge_on = ['Scenario'] + param_cols
                result_df = pd.merge(result_df, stat_comparison, on=merge_on, how='outer')

    if result_df is None or result_df.empty:
        print(f"No data found for {component_type}.{component_name} with statistics {statistics}")
        return pd.DataFrame()

    return result_df


def filter_results(data_source, component_type: str = None, component_name: str = None,
                   statistic: str = None) -> pd.DataFrame:
    """
    Filter results based on component type, name, and statistic.
    Moved from ExperimentRunner since it's primarily used for visualization.

    :param data_source: The data source (ExperimentRunner, ReplicationRunner, etc.)
    :param component_type: Component type to filter by (e.g., 'Server')
    :param component_name: Component name to filter by (e.g., 'ATM')
    :param statistic: Statistic name to filter by (e.g., 'ScheduledUtilization')
    :return: Filtered DataFrame
    """
    return get_comparison_data(data_source, component_type, component_name, statistic)


def filter_scenarios(data_source, scenarios_to_include: Optional[List[str]] = None) -> List[str]:
    """
    Filter scenarios based on user selection.

    :param data_source: ExperimentRunner object
    :param scenarios_to_include: List of scenario names to include, or None for all
    :return: List of scenario names to use
    """
    source_type = _get_data_source_type(data_source)

    if source_type != "experiment":
        return []

    # Get all available scenarios
    all_scenarios = []
    if hasattr(data_source, 'scenarios'):
        all_scenarios = [s.name for s in data_source.scenarios]
    elif hasattr(data_source, 'replication_data'):
        all_scenarios = list(data_source.replication_data.keys())

    if not scenarios_to_include:
        # Return all scenarios if none specified
        return all_scenarios

    # Filter to only requested scenarios that exist
    filtered = [s for s in scenarios_to_include if s in all_scenarios]

    if not filtered:
        print(f"Warning: None of the requested scenarios {scenarios_to_include} were found.")
        print(f"Available scenarios: {all_scenarios}")

    return filtered


def filter_components(detailed_stats: List[dict], component_type: str,
                      components_to_include: Optional[List[str]] = None) -> List[str]:
    """
    Filter components based on user selection.

    :param detailed_stats: List of detailed statistics dictionaries
    :param component_type: Type of component (e.g., 'Server')
    :param components_to_include: List of component names to include, or None for all
    :return: List of component names to use
    """
    # Extract all available component names
    all_components = set()

    for rep_data in detailed_stats:
        if component_type in rep_data:
            comp_data = rep_data[component_type]
            if isinstance(comp_data, list):
                for comp in comp_data:
                    name_key = 'Server' if component_type == 'Server' else 'Name'
                    if name_key in comp:
                        all_components.add(comp[name_key])
            elif isinstance(comp_data, dict):
                all_components.update(comp_data.keys())

    all_components = sorted(list(all_components))

    if not components_to_include:
        # Return all components if none specified
        return all_components

    # Filter to only requested components that exist
    filtered = [c for c in components_to_include if c in all_components]

    if not filtered:
        print(f"Warning: None of the requested components {components_to_include} were found.")
        print(f"Available {component_type}s: {all_components}")

    return filtered


def get_filtered_comparison_data(data_source, component_type: str, component_name: str,
                                 statistic: str, scenarios_to_include: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Get comparison data with optional scenario filtering.

    :param data_source: Data source
    :param component_type: Component type
    :param component_name: Component name
    :param statistic: Statistic name
    :param scenarios_to_include: Optional list of scenarios to include
    :return: Filtered DataFrame
    """
    # Get base comparison data
    comparison_data = get_comparison_data(data_source, component_type, component_name, statistic)

    if comparison_data.empty or not scenarios_to_include:
        return comparison_data

    # Filter to only included scenarios
    filtered_data = comparison_data[comparison_data['Scenario'].isin(scenarios_to_include)]

    if filtered_data.empty:
        print(f"Warning: No data found for scenarios {scenarios_to_include}")

    return filtered_data


def _determine_components_to_plot(component_name: Union[str, List[str], None],
                                  detailed_stats: List[dict],
                                  component_type: str) -> List[str]:
    """
    Determine which components to plot based on component_name parameter.

    :param component_name: None (all), str (single), or List[str] (multiple)
    :param detailed_stats: Detailed statistics data
    :param component_type: Type of component (e.g., 'Server')
    :return: List of component names to plot
    """
    if component_name is None:
        # Get all components of this type
        return filter_components(detailed_stats, component_type, None)
    elif isinstance(component_name, str):
        return [component_name]
    else:  # List of strings
        return component_name


def _extract_component_values(detailed_stats: List[dict],
                              components: List[str],
                              component_type: str,
                              statistic: str) -> Dict[str, List[float]]:
    """
    Extract values for specified components and statistic from detailed stats.

    :return: Dictionary mapping component_name -> list of values
    """
    component_values = {}

    for rep_data in detailed_stats:
        try:
            if component_type in rep_data:
                comp_data = rep_data[component_type]

                if isinstance(comp_data, list):
                    # For servers and similar components
                    for comp in comp_data:
                        name_key = 'Server' if component_type == 'Server' else 'Name'
                        comp_name = comp.get(name_key)
                        if comp_name in components and statistic in comp:
                            if comp_name not in component_values:
                                component_values[comp_name] = []
                            component_values[comp_name].append(comp[statistic])

                elif isinstance(comp_data, dict):
                    # For sinks and sources
                    for comp_name, comp_stats in comp_data.items():
                        if comp_name in components and statistic in comp_stats:
                            if comp_name not in component_values:
                                component_values[comp_name] = []
                            component_values[comp_name].append(comp_stats[statistic])

        except Exception as e:
            print(f"Error extracting data: {e}")

    return component_values


def _calculate_component_statistics(component_values: Dict[str, List[float]]) -> List[Dict]:
    """
    Calculate statistics for each component (used by bar charts, tables, etc.).

    :return: List of dictionaries with 'label', 'average', 'half_width', 'minimum', 'maximum'
    """
    bar_data = []

    for comp_name in sorted(component_values.keys()):
        values = component_values[comp_name]
        if values:
            avg_value = np.mean(values)
            min_value = np.min(values)
            max_value = np.max(values)

            # Calculate confidence interval
            if len(values) > 1:
                std_dev = np.std(values, ddof=1)
                from scipy.stats import t
                t_val = t.ppf(0.975, len(values) - 1)
                half_width = t_val * (std_dev / np.sqrt(len(values)))
            else:
                half_width = 0

            bar_data.append({
                'label': comp_name,
                'average': avg_value,
                'half_width': half_width,
                'minimum': min_value,
                'maximum': max_value
            })

    return bar_data


def _generate_plot_title(component_type: str,
                         component_name: Union[str, List[str], None],
                         statistic: str,
                         plot_type: str,
                         source_type: str,
                         scenarios_filtered: bool = False) -> str:
    """Generate appropriate title based on what's being plotted."""

    if source_type == "experiment":
        title = f'{component_type} {component_name}: {statistic} {plot_type}'
        if scenarios_filtered:
            title += ' (Selected Scenarios)'
    else:
        if component_name is None:
            title = f'{component_type}s: {statistic} {plot_type}'
        elif isinstance(component_name, str):
            title = f'{component_type} {component_name}: {statistic} {plot_type}'
        else:  # List
            if len(component_name) == 1:
                title = f'{component_type} {component_name[0]}: {statistic} {plot_type}'
            else:
                title = f'Selected {component_type}s: {statistic} {plot_type}'

    return title


def _get_detailed_stats(data_source, source_type: str) -> List[dict]:
    """
    Get detailed statistics from the data source.

    :param data_source: Data source object
    :param source_type: Type of data source ('replication' or 'replication_stats')
    :return: List of detailed statistics dictionaries
    """
    if source_type == "replication":
        return data_source.detailed_replication_data if hasattr(data_source, 'detailed_replication_data') else []
    else:  # replication_stats
        return Stats.all_detailed_stats if Stats.all_detailed_stats else []
