"""
Framework constants and setup.
This file contains ONLY immutable constants and one-time setup.
All configurable values live in config.py
"""

import logging
import random
import pandas as pd
from matplotlib import pyplot as plt
from src.core.components_abstract.singleton import Singleton
from src.core.utils.logging_utils import add_logging_level

# ============================================================================
# FRAMEWORK CONSTANTS
# ============================================================================
DAYS_PER_WEEK = 7
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60
ENTITY_PROCESSING_LOG_ENTRY = "{:<120} at {}"

# ============================================================================
# RUNTIME STATE
# ============================================================================
COLLECT_ENTITY_TYPE_STATS = False
DURATION_WARM_UP = 0
RANDOM_SEED = 1

# ============================================================================
# ONE-TIME SETUP
# ============================================================================
if not hasattr(logging, 'TRACE'):
    add_logging_level('TRACE', logging.DEBUG + 5)  # between DEBUG and INFO

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.set_loglevel('WARNING')

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('max_seq_item', None)
pd.set_option('display.width', 1000)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def set_duration_warm_up(value):
    global DURATION_WARM_UP
    DURATION_WARM_UP = value


def set_collect_entity_type_stats(value):
    global COLLECT_ENTITY_TYPE_STATS
    COLLECT_ENTITY_TYPE_STATS = value


def set_random_seed(value):
    global RANDOM_SEED
    RANDOM_SEED = value
    random.seed(value)


# ============================================================================
# STATS SINGLETON
# ============================================================================
class Stats(Singleton):
    all_detailed_stats = None
