"""
Parameter management utility for simulation experiments.
Allows modifying component parameters at runtime based on scenario configuration.
"""
import functools
import inspect
import logging


class ParameterizedModel:
    """
    A picklable class that wraps a model function and applies parameters during component creation.
    """
    def __init__(self, model_func, parameters=None):
        """
        Initialize with a model function and parameters.

        :param model_func: The original model function
        :param parameters: Dictionary of parameters to apply
        """
        self.model_func = model_func
        self.parameters = parameters or {}

    def __call__(self, env):
        """
        Build the model and apply parameters.

        :param env: SimPy environment
        :return: The built model
        """
        from src.core.components.model import Model
        from src.core.components.server import Server
        from src.core.components.source import Source
        from src.core.components.sink import Sink

        # Reset the model
        Model().reset_simulation()

        # Keep track of original methods for cleanup
        component_classes = {'Server': Server, 'Source': Source, 'Sink': Sink}
        original_inits = {cls_name: cls.__init__ for cls_name, cls in component_classes.items()}

        # Parse parameters by component
        component_params = {}
        for param_key, value in self.parameters.items():
            # Handle dot notation (component.param)
            if '.' in param_key:
                parts = param_key.split('.')
                if len(parts) >= 2:
                    component_name = parts[0]
                    param_name = '.'.join(parts[1:])

                    if component_name not in component_params:
                        component_params[component_name] = {}
                    component_params[component_name][param_name] = value

            # Handle colon notation (component:param)
            elif ':' in param_key:
                component_name, param_name = param_key.split(':', 1)

                if component_name not in component_params:
                    component_params[component_name] = {}
                component_params[component_name][param_name] = value

            # Handle direct parameters (not related to components)
            else:
                # These stay in self.parameters for direct usage
                pass

        try:
            # Patch the __init__ methods of all component classes
            for cls_name, cls in component_classes.items():
                original_init = original_inits[cls_name]

                # Create a closure to capture the component_params dictionary
                def create_patched_init(orig_init, params_dict):
                    def patched_init(self, env, name, *args, **kwargs):
                        # Check if we have parameters for this component
                        if name in params_dict:
                            # Apply component-specific parameters
                            for param_name, value in params_dict[name].items():
                                kwargs[param_name] = value
                                logging.info(f"Modified {name} with parameter {param_name}={value}")

                        # Call original __init__
                        orig_init(self, env, name, *args, **kwargs)

                    return patched_init

                # Create and assign the patched init function with access to component_params
                cls.__init__ = create_patched_init(original_init, component_params)

            # Run the model
            if 'parameters' in inspect.signature(self.model_func).parameters:
                # Pass all parameters if the function accepts them
                self.model_func(env, self.parameters)
            else:
                # Otherwise just call with env
                self.model_func(env)

            return Model()

        except Exception as e:
            logging.error(f"Error in parameterized model: {str(e)}")
            raise

        finally:
            # Always restore the original methods
            for cls_name, cls in component_classes.items():
                cls.__init__ = original_inits[cls_name]


def parameterize_model(model_func):
    """
    Decorator to make a model function accept parameters.

    :param model_func: Model building function
    :return: Parameterized model function
    """
    @functools.wraps(model_func)
    def wrapper(env, parameters=None):
        # If the original function accepts parameters, pass them directly
        if 'parameters' in inspect.signature(model_func).parameters:
            return model_func(env, parameters)
        else:
            # Otherwise just call with env
            return model_func(env)

    return wrapper
