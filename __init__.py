from loguru import logger

from ._logger import setup_logging
from .progress import Progress

__all__ = ["Progress", "logger", "setup_logging"]

# Install the tqdm-safe console sink at import, so nothing goes through Loguru's
# default handler (which breaks progress bars).
setup_logging()
