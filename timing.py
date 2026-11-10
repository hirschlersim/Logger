from __future__ import annotations

import time
from types import TracebackType
from typing import Self

from loguru import logger

__all__ = ["timed"]


class timed:  # noqa: N801 - lowercase on purpose, like contextlib.suppress
    """Log how long a block took.

    Example::

        with timed("load data"):
            ...
        # 12:00:01.234 | INFO     | load data took 1.23 s

    If the block raises, it logs "<label> failed after ..." and the exception
    propagates. ``.elapsed`` holds the duration in seconds once the block ends.
    """

    def __init__(self, label: str, level: str | int = "INFO") -> None:
        self.label = label
        self.level = level
        self.elapsed: float | None = None
        self._start = 0.0

    def __enter__(self) -> Self:
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.elapsed = time.perf_counter() - self._start
        verb = "failed after" if exc_type is not None else "took"
        # depth=1 attributes the record to the `with` block, not this file.
        logger.opt(depth=1).log(
            self.level, "{} {} {}", self.label, verb, _format_duration(self.elapsed)
        )


def _format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    minutes, rest = divmod(seconds, 60)
    return f"{int(minutes)} min {rest:.1f} s"
