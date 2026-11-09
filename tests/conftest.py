"""Test setup.

The repo root *is* the package (so it can be dropped into ``libs/logger`` as a
submodule), and ``tests`` is a subpackage of it. Tests therefore use relative
imports (``from .. import logger``) and don't depend on the checkout folder name.
"""

import logging

import pytest
from loguru import logger


@pytest.fixture(autouse=True)
def _isolate_logging(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    yield
    logger.remove()  # also closes log files, so Windows can delete tmp_path
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
