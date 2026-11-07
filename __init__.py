from loguru import logger

from ._logger import setup_logging
from .progress import Progress

__all__ = ["Progress", "logger", "setup_logging"]

# Install the tqdm-safe console sink at import, so nothing goes through Loguru's
# default handler (which breaks progress bars). The stdlib `logging` module is
# only taken over when you call setup_logging() yourself.
setup_logging(intercept_stdlib=False)
