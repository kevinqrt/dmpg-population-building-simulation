from enum import Enum


class TimeComponent(Enum):
    """
    An Enum representing basic units of time.
    """
    second = 1
    """A second as the fundamental unit of time."""
    minute = 60
    """A minute, represented in seconds."""
    hour = 3600
    """An hour, represented in seconds."""
    day = 86400
    """A day, represented in seconds."""
    week = 604800
    """A week, represented in seconds."""
