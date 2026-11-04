from .logger import AppLogger

logger = AppLogger()

from .progress import Progress

__all__ = ["Progress", "logger"]
