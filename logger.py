from __future__ import annotations

from typing import Any

from loguru import logger as _loguru_logger
from tqdm import tqdm


class AppLogger:
    """Loguru wrapper with tqdm-compatible logging and progress bars."""

    def __init__(self) -> None:
        self._logger = _loguru_logger

    def configure(self, debug: bool = False, trace: bool = False) -> None:
        """Configure Loguru output and log level."""
        self._logger.remove()

        level = "TRACE" if trace else "DEBUG" if debug else "INFO"

        spacer = " | "
        log_format = ""
        log_format += "<green>{time:HH:mm:ss:ms}</green>" + spacer
        log_format += "<level>{level: <8}</level>" + spacer
        log_format += "<dim>{file}:{line}</dim>" + spacer if debug else ""
        log_format += "<level>{message}</level>"

        self._logger.add(
            lambda message: tqdm.write(message, end=""),
            format=log_format,
            level=level,
            colorize=True,
        )

    def __getattr__(self, name: str) -> Any:
        """Forward info(), debug(), warning(), error(), etc. to Loguru."""
        return getattr(self._logger, name)
