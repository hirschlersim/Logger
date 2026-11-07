from __future__ import annotations

import os
import sys

from loguru import logger
from tqdm import tqdm

__all__ = ["setup_logging"]

_DEFAULT_LEVEL = "INFO"
_SEP = " | "
_FILE_FORMAT = _SEP.join(
    [
        "{time:YYYY-MM-DD HH:mm:ss.SSS}",
        "{level: <8}",
        "{name}:{function}:{line}",
        "{message}",
    ]
)


def setup_logging(
    level: str | int | None = None,
    *,
    log_file: str | os.PathLike[str] | None = None,
    file_level: str | int = "DEBUG",
    rotation: str | int | None = "10 MB",
    retention: str | int | None = "7 days",
    colorize: bool | None = None,
) -> None:
    """Install a tqdm-safe console sink and, optionally, a rotating log file.

    Safe to call repeatedly: each call fully replaces the previous setup. Add your
    own sinks with ``logger.add()`` *after* calling this, or they will be removed.

    Args:
        level: Console level. Falls back to the ``LOG_LEVEL`` env var, then ``INFO``.
            At ``DEBUG`` or lower the console also shows ``file:line``.
        log_file: Also write to this file. Missing parent folders are created.
        file_level: Level for the log file.
        rotation: When to start a new file, in Loguru syntax ("10 MB", "1 day", ...).
        retention: How long to keep rotated files ("7 days", or a count like 5).
        colorize: Force colours on or off. By default they are on when stdout is a
            terminal and the ``NO_COLOR`` env var is not set.
    """
    # Resolve everything before touching handlers, so bad input leaves the
    # current setup intact.
    env_warning = None
    if level is not None:
        console_no = _level_no(level)
    else:
        env_value = os.environ.get("LOG_LEVEL") or _DEFAULT_LEVEL
        try:
            console_no = _level_no(env_value)
        except ValueError:
            console_no = _level_no(_DEFAULT_LEVEL)
            env_warning = (
                f"Ignoring unknown LOG_LEVEL={env_value!r}, using {_DEFAULT_LEVEL}"
            )
    file_no = _level_no(file_level)
    if colorize is None:
        colorize = _auto_colorize()

    logger.remove()
    logger.add(
        _tqdm_sink,
        level=console_no,
        format=_console_format(show_location=console_no <= logger.level("DEBUG").no),
        colorize=colorize,
    )
    if log_file is not None:
        logger.add(
            log_file,
            level=file_no,
            format=_FILE_FORMAT,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            colorize=False,
        )

    if env_warning:
        logger.warning(env_warning)


# ---------------------------------------------------------------------- #
# Private
# ---------------------------------------------------------------------- #


def _tqdm_sink(message: str) -> None:
    # tqdm.write clears and redraws active progress bars around the message.
    tqdm.write(message, end="")


def _console_format(show_location: bool) -> str:
    parts = ["<green>{time:HH:mm:ss.SSS}</green>", "<level>{level: <8}</level>"]
    if show_location:
        parts.append("<dim>{file}:{line}</dim>")
    parts.append("<level>{message}</level>")
    return _SEP.join(parts)


def _level_no(level: str | int) -> int:
    if isinstance(level, int):
        return level
    try:
        return logger.level(level.strip().upper()).no
    except ValueError:
        raise ValueError(f"Unknown log level {level!r}") from None


def _auto_colorize() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    try:
        return sys.stdout is not None and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False
