import copy
import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Callable

import pandas as pd
from tabulate import tabulate

from src.core.simulation.experiments.parameter_manager import ParameterizedModel
from src.core.simulation.replication import ReplicationRunner


class ScenarioParameter:
    """
    Represents a parameter that can be varied across different scenarios.
    """
    def __init__(self, name: str, value: Any, description: str = None):
        """
        Initialize a scenario parameter.

        :param name: Name of the parameter
        :param value: Value of the parameter
        :param description: Optional description of the parameter
        """
        self.name = name
        self.value = value
        self.description = description or f"Parameter {name}"

    def __repr__(self) -> str:
        return f"ScenarioParameter({self.name}={self.value})"


class Scenario:
    """
    Represents a single scenario with specific parameter values.
    """
    def __init__(self, name: str, parameters: Dict[str, Any] = None, description: str = None):
        """
        Initialize a scenario.

        :param name: Name of the scenario
        :param parameters: Dictionary of parameter names and values
        :param description: Optional description of the scenario
        """
        self.name = name
        self.parameters = {k: ScenarioParameter(k, v) for k, v in (parameters or {}).items()}
        self.description = description or f"Scenario {name}"
        self.results = {}

    def add_parameter(self, name: str, value: Any, description: str = None) -> None:
        """
        Add a parameter to the scenario.

        :param name: Name of the parameter
        :param value: Value of the parameter
        :param description: Optional description of the parameter
        """
        self.parameters[name] = ScenarioParameter(name, value, description)

    def get_parameter_value(self, name: str, default: Any = None) -> Any:
        """
        Get the value of a parameter.

        :param name: Name of the parameter
        :param default: Default value if parameter doesn't exist
        :return: Parameter value
        """
        return self.parameters[name].value if name in self.parameters else default

    def __repr__(self) -> str:
        param_strs = [f"{k}={v.value}" for k, v in self.parameters.items()]
        return f"Scenario({self.name}, {', '.join(param_strs)})"


class ExperimentRunner:
    """
    Runs multiple scenarios with replications and collects results.
    """
    def __init__(self, name: str, model_builder: Callable,
                 tracked_statistics: List[Tuple[str, str, str, Optional[str]]] = None,
                 global_parameters: Dict[str, Any] = None,
                 parameter_display_names: Dict[str, str] = None):
        """
        Initialize an experiment runner.

        :param name: Name of the experiment
        :param model_builder: Function that builds the model, taking scenario parameters
        :param tracked_statistics: List of statistics to track [(type, name, stat, [display_name])]
                                where display_name is optional and used for table headers
        :param global_parameters: Parameters common to all scenarios
        :param parameter_display_names: Dictionary mapping parameter names to display names
        """
        self.name = name
        self.model_builder = model_builder
        self.tracked_statistics = tracked_statistics or []
        self.global_parameters = global_parameters or {}
        self.scenarios = []
        self.results = pd.DataFrame()
        self.start_time = None
        self.end_time = None
        self.parameter_display_names = parameter_display_names or {}

    def standardize_results(self, results_df):
        """
        Ensure consistent DataFrame structure for results.

        :param results_df: DataFrame to standardize
        :return: Standardized DataFrame
        """
        if results_df.empty:
            return results_df

        # Check if we already have a properly structured MultiIndex
        if isinstance(results_df.index, pd.MultiIndex) and results_df.index.nlevels >= 3:
            # Ensure index names are set
            if results_df.index.names[0] is None:
                results_df.index.names = ['Type', 'Name', 'Stat'] + [
                    f'Level{i}' for i in range(3, results_df.index.nlevels)
                ]
            return results_df

        # Check if we have the required columns to create a MultiIndex
        required_cols = ['Type', 'Name', 'Stat']
        if all(col in results_df.columns for col in required_cols):
            # Convert to MultiIndex
            return results_df.set_index(required_cols)

        # Unable to standardize
        logging.warning("Could not standardize DataFrame structure")
        return results_df

    def add_scenario(self, scenario: Scenario) -> None:
        """
        Add a scenario to the experiment.

        :param scenario: Scenario to add
        """
        self.scenarios.append(scenario)

    def create_scenario(self, name: str, parameters: Dict[str, Any] = None,
                        description: str = None) -> Scenario:
        """
        Create and add a new scenario.

        :param name: Name of the scenario
        :param parameters: Dictionary of parameter names and values
        :param description: Optional description of the scenario
        :return: Created scenario
        """
        scenario = Scenario(name, parameters, description)
        self.scenarios.append(scenario)
        return scenario

    def _build_model_with_parameters(self, env, scenario: Scenario):
        """
        Build a model with the specified parameters.

        :param env: SimPy environment
        :param scenario: Scenario with parameters
        """
        # Combine global and scenario parameters
        all_parameters = copy.deepcopy(self.global_parameters)
        for k, param in scenario.parameters.items():
            all_parameters[k] = param.value

        # Call the model builder with parameters
        return self.model_builder(env, all_parameters)

    def _run_scenario(self, scenario: Scenario, steps: int, replications: int,
                      warm_up: Optional[int] = None, multiprocessing: bool = False,
                      store_replication_data: bool = True) -> pd.DataFrame:
        """
        Run a single scenario with replications.

        :param scenario: Scenario to run
        :param steps: Number of simulation steps
        :param replications: Number of replications
        :param warm_up: Warm-up period
        :param multiprocessing: Whether to use multiprocessing
        :param store_replication_data: Whether to store detailed replication data
        :return: DataFrame with results
        """
        logging.info(f"Running scenario '{scenario.name}' with parameters: {scenario.parameters}")

        try:
            # Convert parameters from ScenarioParameter objects to a plain dictionary
            parameters = {}

            # Add global parameters
            for k, v in self.global_parameters.items():
                parameters[k] = v

            # Add scenario-specific parameters (overriding globals if needed)
            for k, param in scenario.parameters.items():
                parameters[k] = param.value

            # Debug parameter info
            logging.debug(f"Applying parameters: {parameters}")

            # Create a parameterized model
            parameterized_model = ParameterizedModel(self.model_builder, parameters)

            # Run replications
            rep_runner = ReplicationRunner(
                model=parameterized_model,
                steps=steps,
                num_replications=replications,
                warm_up=warm_up,
                multiprocessing=multiprocessing
            )

            # Run and get the pivot table
            pivot_table = rep_runner.run(new_database=True)

            # Store detailed replication data if requested
            if store_replication_data:
                if not hasattr(self, 'replication_data'):
                    self.replication_data = {}
                self.replication_data[scenario.name] = rep_runner.detailed_replication_data

            if pivot_table is None or pivot_table.empty:
                logging.warning(f"No results returned for scenario '{scenario.name}'")
                return pd.DataFrame()

            # Add scenario information to the results
            pivot_df = pd.DataFrame(pivot_table)
            pivot_df['Scenario'] = scenario.name

            # Add parameter values as columns
            for param_name, param in scenario.parameters.items():
                # Clean parameter name for column name
                clean_name = param_name.replace('.', '_').replace(':', '_')
                pivot_df[f'Param_{clean_name}'] = param.value

            # Store the results in the scenario
            scenario.results = pivot_df

            # Log completion
            logging.info(f"Completed scenario '{scenario.name}'")

            return pivot_df

        except Exception as e:
            logging.error(f"Error running scenario '{scenario.name}': {str(e)}")
            logging.debug("Exception details:", exc_info=True)
            # Return empty DataFrame as fallback
            return pd.DataFrame()

    def run_all(self, steps: int, replications: int, warm_up: Optional[int] = None,
                multiprocessing: bool = False, store_replication_data: bool = True) -> pd.DataFrame:
        """
        Run all scenarios and collect results.

        :param steps: Number of simulation steps
        :param replications: Number of replications
        :param warm_up: Warm-up period
        :param multiprocessing: Whether to use multiprocessing
        :param store_replication_data: Whether to store detailed replication data (default: True)
        :return: DataFrame with combined results
        """
        if not self.scenarios:
            raise ValueError("No scenarios defined for the experiment")

        self.start_time = time.time()
        all_results = []
        self.replication_data = {}  # Dictionary to store detailed replication data by scenario

        for i, scenario in enumerate(self.scenarios, 1):
            logging.info(f"Running scenario {i}/{len(self.scenarios)}: {scenario.name}")
            scenario_results = self._run_scenario(
                scenario, steps, replications, warm_up, multiprocessing, store_replication_data
            )
            all_results.append(scenario_results)
            logging.info(f"Completed scenario {i}/{len(self.scenarios)}: {scenario.name}")

        self.end_time = time.time()

        # Combine all results
        if all_results:
            self.results = pd.concat(all_results, ignore_index=True)

        logging.info(f"Experiment '{self.name}' completed in {self.end_time - self.start_time:.2f} seconds")
        return self.results

    def filter_results(self, component_type: str = None, component_name: str = None, statistic: str = None) -> pd.DataFrame:
        """
        Filter results based on component type, name, and statistic using MultiIndex.

        :param component_type: Component type to filter by (e.g., 'Server')
        :param component_name: Component name to filter by (e.g., 'ATM')
        :param statistic: Statistic name to filter by (e.g., 'ScheduledUtilization')
        :return: Filtered DataFrame
        """
        filtered_data = []

        # Loop through all scenarios and extract data from the MultiIndex
        for scenario in self.scenarios:
            if not hasattr(scenario, 'results') or scenario.results is None or scenario.results.empty:
                continue

            scenario_results = scenario.results

            # Check if we have a MultiIndex in the scenario results
            if isinstance(scenario_results.index, pd.MultiIndex) and len(scenario_results.index.names) >= 3:
                # We have a MultiIndex with Type, Name, Stat
                # Access data directly using tuple as index
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
                                logging.debug(f"Could not find {col} for {component_type}.{component_name}.{statistic}")

                    for param_name, param in scenario.parameters.items():
                        clean_name = param_name.replace('.', '_').replace(':', '_')
                        row_data[f'Param_{clean_name}'] = param.value

                    if any(key in row_data for key in ['Average', 'Minimum', 'Maximum', 'Half-Width']):
                        filtered_data.append(row_data)

                except Exception as e:
                    logging.debug(f"Error accessing data for {component_type}.{component_name}.{statistic} in scenario {scenario.name}: {e}")
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
                    logging.debug(f"Error filtering scenario {scenario.name}: {e}")

        # Create DataFrame from filtered data
        if filtered_data:
            return pd.DataFrame(filtered_data)
        else:
            logging.warning(f"No data found for {component_type}.{component_name}.{statistic}")
            return pd.DataFrame()

    def get_comparison_data(self, component_type: str, component_name: str, statistic: str) -> pd.DataFrame:
        """
        Compare a specific statistic across all scenarios.
        This is now a wrapper around the visualization helper function.
        """
        from src.core.visualization.visualization_helpers import get_comparison_data
        return get_comparison_data(self, component_type, component_name, statistic)

    def display_summary_table(self, precision: int = 4):
        """
        Display a professional-looking table of scenario results with perfect alignment
        using the tabulate library.

        :param precision: Number of decimal places for numeric values
        """

        if not self.scenarios:
            print("No scenarios to display")
            return

        # Get parameters and tracked statistics
        param_names = sorted({p for s in self.scenarios for p in s.parameters})
        tracked_stats = self.tracked_statistics or []

        # Prepare headers
        headers = ["ScenarioNr", "Scenario_Name"]

        # Add parameters to headers with custom display names if available
        for param in param_names:
            # Use display name if available, otherwise format the parameter name
            display_name = self.parameter_display_names.get(param, f"Param_{param}")
            headers.append(display_name)

        # Add statistics to headers with custom display names if available
        for stat in tracked_stats:
            # Use display name (4th element) if provided, otherwise format the default name
            display_name = stat[3] if len(stat) > 3 and stat[3] else f"{stat[1]}_{stat[2]}(Avg)"
            headers.append(display_name)

        # Prepare data rows
        rows = []
        for i, scenario in enumerate(self.scenarios, 1):
            row = [i, scenario.name]

            # Add parameters
            for param in param_names:
                value = scenario.parameters.get(param, ScenarioParameter(param, "")).value
                row.append(value)

            # Add statistics
            for stat in tracked_stats:
                comp_type, comp_name, stat_name = stat[0], stat[1], stat[2]
                try:
                    comparison = self.get_comparison_data(comp_type, comp_name, stat_name)
                    if not comparison.empty:
                        scenario_data = comparison[comparison['Scenario'] == scenario.name]
                        if not scenario_data.empty:
                            value = scenario_data['Average'].iloc[0]
                            row.append(value)
                        else:
                            row.append("N/A")
                    else:
                        row.append("N/A")
                except Exception:
                    row.append("N/A")

            rows.append(row)

        # Format numeric values to the specified precision
        formatted_rows = []
        for row in rows:
            formatted_row = []
            for i, value in enumerate(row):
                if i >= 2 + len(param_names) and isinstance(value, (int, float)):
                    # This is a statistic value (not a scenario number or parameter)
                    formatted_row.append(f"{value:.{precision}f}")
                else:
                    formatted_row.append(value)
            formatted_rows.append(formatted_row)

        # Generate the table with tabulate
        table = tabulate(
            formatted_rows,
            headers=headers,
            tablefmt="simple_grid",  # Available: pipe simple_grid grid fancy_grid pretty simple
            numalign="right",  # Right-align numbers
            stralign="left"    # Left-align strings
        )

        # Print the results
        print("\n=== Experiment Dashboard ===")
        print(table)

        # Print summary
        print(f"\nExperiment: {self.name}")
        print(f"Total scenarios: {len(self.scenarios)}")
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            print(f"Execution time: {duration:.2f} seconds")

    def get_multi_statistic_data(self, component_type: str, component_name: str,
                                 statistics: List[str]) -> pd.DataFrame:
        """
        Compare multiple statistics for the same component across all scenarios.

        :param component_type: Component type (e.g., 'Server')
        :param component_name: Component name (e.g., 'ATM')
        :param statistics: List of statistics to compare
        :return: DataFrame with comparison of multiple statistics
        """
        result_df = None

        # For each statistic, get its data across all scenarios
        for statistic in statistics:
            stat_comparison = self.get_comparison_data(component_type, component_name, statistic)

            if not stat_comparison.empty:
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
            logging.warning(f"No data found for {component_type}.{component_name} with statistics {statistics}")
            return pd.DataFrame()

        return result_df
