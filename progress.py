from __future__ import annotations

from typing import Self

from tqdm import tqdm

from . import logger


class Progress:
    def __init__(self, total: int, desc: str = "") -> None:
        self.total = total
        self.terminated = False
        self.colors = ["green", "yellow", "red"]
        self.col_index = 0

        self._bar = tqdm(
            total=total,
            desc=desc,
            colour=self.colors[self.col_index],
            bar_format=("{desc} {percentage:3.0f}% - {bar} - {n_fmt}/{total_fmt}"),
        )

    # ------------------------------------------------------------------ #
    # Public
    # ------------------------------------------------------------------ #

    def inc(self) -> None:
        self.add(1)

    def add(self, amount: int) -> None:
        self._update(self._bar.n + amount)

    def set(self, current: int) -> None:
        self._update(current)

    def close(self) -> None:
        if not self.terminated:
            self._bar.close()
            self.terminated = True

    # ------------------------------------------------------------------ #
    # Private
    # ------------------------------------------------------------------ #

    def _update(self, n: int) -> None:
        if self.terminated:
            logger.warning("Progressbar was already closed")
            return

        self._bar.total = max(n, self._bar.total)

        if n > self.total:
            self.total *= 2
            self.col_index = min(self.col_index + 1, len(self.colors) - 1)
            self._bar.colour = self.colors[self.col_index]

        self._bar.n = n
        self._bar.refresh()

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
