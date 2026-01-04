from pathlib import Path
import yaml
from typing import Union, Dict, Any, Tuple, Callable


# ============================================================================
# PATH RESOLUTION
# ============================================================================
def _find_project_root() -> Path:
    """Find project root by looking for 'config' and 'src' directories."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "config").exists() and (parent / "src").exists():
            return parent
    raise RuntimeError("Cannot find project root (need 'config' and 'src' directories)")


_ROOT = _find_project_root()
_CONFIG_DIR = _ROOT / "config"
_GLOBAL_CONFIG = _CONFIG_DIR / "global_config.yaml"

# ============================================================================
# INTERNAL STATE
# ============================================================================
_state = {}
_original_state = {}


# ============================================================================
# CORE FUNCTIONS
# ============================================================================
def _deep_merge(target: Dict[str, Any], src: Dict[str, Any]) -> None:
    """Deep merge src into target."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            _deep_merge(target[k], v)
        else:
            target[k] = v


def _load_global() -> None:
    """Load the global configuration file."""
    if not _GLOBAL_CONFIG.exists():
        raise FileNotFoundError(f"Global config not found: {_GLOBAL_CONFIG}")

    with _GLOBAL_CONFIG.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    _state.clear()
    _state.update(data)
    _original_state.clear()
    _original_state.update(data)


def apply_overrides(overrides: Union[None, Dict[str, Any], str, Path]) -> None:
    """
    Apply configuration overrides.

    Args:
        overrides: None, dict, path to YAML, or "auto" for auto-detection
    """
    if overrides is None:
        return

    if isinstance(overrides, (str, Path)):
        path = Path(overrides)

        # If relative path, try multiple locations
        if not path.is_absolute():
            search_paths = [
                path,  # Current working directory
                _CONFIG_DIR / path,  # Config directory
                _ROOT / path  # Project root
            ]

            for search_path in search_paths:
                if search_path.exists():
                    path = search_path
                    break

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {overrides}")

        with path.open("r", encoding="utf-8") as f:
            overrides = yaml.safe_load(f) or {}

    # Handle inheritance
    if isinstance(overrides, dict) and "_extends" in overrides:
        base_config = overrides.pop("_extends")
        apply_overrides(base_config)

    _deep_merge(_state, overrides)


def reset_to_global() -> None:
    """Reset configuration to global defaults."""
    _state.clear()
    _state.update(_original_state)


# ============================================================================
# MODEL PARAMETER ACCESS
# ============================================================================
def get_param(path: str, default=None) -> Any:
    """
    Get parameter using dot notation.

    Example:
        cfg.get_param('servers.placement.capacity') → 2
        cfg.get_param('servers.placement.processing_time.params') → [3, 5, 4]
    """
    keys = path.split('.')
    value = _state.get('model_parameters', {})

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default

    return value if value is not None else default


def get_distribution(path: str) -> Tuple[Callable, ...]:
    """
    Convert config distribution to framework tuple format.

    Example config:
        processing_time: {distribution: triangular, params: [3, 5, 4]}

    Returns:
        (random.triangular, 3, 5, 4)
    """
    dist_config = get_param(path)

    if not dist_config or not isinstance(dist_config, dict):
        raise ValueError(f"Invalid distribution config at '{path}': {dist_config}")

    dist_name = dist_config.get('distribution')
    params = dist_config.get('params', [])

    if not dist_name:
        raise ValueError(f"Missing 'distribution' key at '{path}'")

    # Import random module and get distribution function
    import random
    if hasattr(random, dist_name):
        dist_func = getattr(random, dist_name)
    else:
        raise ValueError(f"Unknown distribution: {dist_name}")

    return (dist_func, *params)


def has_param(path: str) -> bool:
    """Check if a parameter exists in the config."""
    return get_param(path) is not None


# ============================================================================
# FRAMEWORK SETTINGS ACCESS
# ============================================================================
def __getattr__(name: str) -> Any:
    """Expose settings as attributes for backward compatibility."""

    # Simulation settings
    if name == "precision":
        return (_state.get("simulation") or {}).get("precision", 2)
    if name == "random_seed":
        return (_state.get("simulation") or {}).get("random_seed", 1)
    if name == "duration_warm_up":
        return (_state.get("simulation") or {}).get("duration_warm_up", 0)

    # Statistics settings
    if name == "collect_entity_type_stats":
        return (_state.get("statistics") or {}).get("collect_entity_type_stats", False)
    if name == "confidence_level":
        return (_state.get("statistics") or {}).get("confidence_level", 0.95)

    # Performance settings
    if name == "max_recycled_entities":
        return (_state.get("performance") or {}).get("max_recycled_entities", 5000)
    if name == "entity_pool_default":
        return (_state.get("performance") or {}).get("entity_pool", {}).get("default", 10000)
    if name == "entity_pool_by_type":
        return (_state.get("performance") or {}).get("entity_pool", {}).get("by_type", {})

    # Database settings
    if name == "in_memory_db":
        return (_state.get("database") or {}).get("in_memory", True)

    # Logging settings
    if name == "logging_level":
        return (_state.get("logging") or {}).get("level", "INFO")
    if name == "logging_format":
        return (_state.get("logging") or {}).get("format", "%(asctime)s %(levelname)s %(message)s")

    # Visualization settings
    if name == "matplotlib_log_level":
        return (_state.get("visualization") or {}).get("matplotlib_log_level", "ERROR")

    raise AttributeError(f"Config has no attribute '{name}'")


def get_entity_pool_size(entity_type: str = "Entity") -> int:
    """Get entity pool size for specific type."""
    by_type = (_state.get("performance") or {}).get("entity_pool", {}).get("by_type", {})
    if entity_type in by_type:
        return by_type[entity_type]
    return (_state.get("performance") or {}).get("entity_pool", {}).get("default", 10000)


# ============================================================================
# INITIALIZATION
# ============================================================================
_load_global()
