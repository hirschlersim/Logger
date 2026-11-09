import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from .. import Progress, _logger, logger, setup_logging, timed, timing

ANSI = re.compile(r"\x1b\[[0-9;]*m")
TIME = r"\d{2}:\d{2}:\d{2}\.\d{3}"
PACKAGE_DIR = Path(__file__).resolve().parent.parent


def out(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().out


# ---------------------------------------------------------------------- #
# Defaults on import (fresh interpreter, imported like a project would)
# ---------------------------------------------------------------------- #


def run_fresh(code: str, **env: str) -> subprocess.CompletedProcess[str]:
    prelude = (
        "import sys, importlib, logging\n"
        f"sys.path.insert(0, {str(PACKAGE_DIR.parent)!r})\n"
        f"pkg = importlib.import_module({PACKAGE_DIR.name!r})\n"
        "logger = pkg.logger\n"
    )
    base_env = {
        k: v for k, v in os.environ.items() if k not in ("LOG_LEVEL", "NO_COLOR")
    }
    return subprocess.run(
        [sys.executable, "-c", prelude + code],
        capture_output=True,
        text=True,
        env={**base_env, **env},
        check=True,
    )


def test_import_installs_tqdm_safe_console_at_info():
    result = run_fresh('logger.debug("debug-hidden")\nlogger.info("info-shown")\n')
    assert re.fullmatch(rf"{TIME} \| INFO     \| info-shown\n", result.stdout)
    assert result.stderr == ""  # Loguru's default stderr handler is gone


def test_import_honours_log_level_env_var():
    result = run_fresh('logger.debug("debug-shown")\n', LOG_LEVEL="DEBUG")
    assert "debug-shown" in result.stdout


def test_import_leaves_stdlib_logging_alone():
    result = run_fresh("print(len(logging.getLogger().handlers))\n")
    assert result.stdout == "0\n"


# ---------------------------------------------------------------------- #
# Console format
# ---------------------------------------------------------------------- #


def test_console_line_has_milliseconds(capsys):
    setup_logging()
    logger.info("hello")
    assert re.fullmatch(rf"{TIME} \| INFO     \| hello\n", out(capsys))


def test_location_shown_only_at_debug(capsys):
    setup_logging("DEBUG")
    logger.debug("x")
    assert "test_logging.py:" in out(capsys)

    setup_logging("INFO")
    logger.info("x")
    assert "test_logging.py:" not in out(capsys)


def test_setup_is_idempotent(capsys):
    setup_logging()
    setup_logging()
    logger.info("once")
    assert out(capsys).count("once") == 1


# ---------------------------------------------------------------------- #
# Levels
# ---------------------------------------------------------------------- #


def test_level_from_env_var(capsys, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "warning")
    setup_logging()
    logger.info("hidden")
    logger.warning("shown")
    text = out(capsys)
    assert "hidden" not in text
    assert "shown" in text


def test_numeric_level(capsys):
    setup_logging(logging.WARNING)
    logger.info("hidden")
    logger.warning("shown")
    text = out(capsys)
    assert "hidden" not in text
    assert "shown" in text


def test_argument_beats_env_var(capsys, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    setup_logging("debug")
    logger.debug("visible")
    assert "visible" in out(capsys)


def test_unknown_level_argument_raises_and_keeps_old_setup(capsys):
    setup_logging()
    with pytest.raises(ValueError, match="verbose"):
        setup_logging("verbose")
    logger.info("still works")
    assert out(capsys).count("still works") == 1


def test_unknown_env_level_falls_back_to_info(capsys, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "verbose")
    setup_logging()
    logger.debug("debug-hidden")
    logger.info("info-shown")
    text = out(capsys)
    assert "Ignoring unknown LOG_LEVEL='verbose'" in text
    assert "debug-hidden" not in text
    assert "info-shown" in text


# ---------------------------------------------------------------------- #
# Colour
# ---------------------------------------------------------------------- #


def test_no_colour_when_not_a_terminal(capsys):
    setup_logging()  # captured stdout is not a tty
    logger.info("x")
    assert not ANSI.search(out(capsys))


def test_colour_can_be_forced(capsys):
    setup_logging(colorize=True)
    logger.info("x")
    assert ANSI.search(out(capsys))


def test_auto_colour_respects_tty_and_no_color(monkeypatch):
    class FakeTTY:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr(sys, "stdout", FakeTTY())
    assert _logger._auto_colorize() is True
    monkeypatch.setenv("NO_COLOR", "1")
    assert _logger._auto_colorize() is False


def test_auto_colour_off_for_missing_or_closed_stdout(monkeypatch):
    class ClosedStream:
        def isatty(self) -> bool:
            raise ValueError("I/O operation on closed file")

    monkeypatch.setattr(sys, "stdout", None)  # e.g. pythonw.exe
    assert _logger._auto_colorize() is False
    monkeypatch.setattr(sys, "stdout", ClosedStream())
    assert _logger._auto_colorize() is False


# ---------------------------------------------------------------------- #
# File sink
# ---------------------------------------------------------------------- #


def test_file_gets_debug_without_colour(tmp_path, capsys):
    path = tmp_path / "logs" / "app.log"  # folder doesn't exist yet
    setup_logging("INFO", log_file=path, colorize=True)
    logger.debug("debug-line")
    logger.info("info-line")
    logger.remove()  # flush and close

    text = path.read_text(encoding="utf-8")
    assert "debug-line" in text
    assert "info-line" in text
    assert not ANSI.search(text)
    assert re.search(r"\d{4}-\d{2}-\d{2} " + TIME, text)
    assert "test_file_gets_debug_without_colour" in text  # {function}
    assert "debug-line" not in out(capsys)


# ---------------------------------------------------------------------- #
# stdlib logging
# ---------------------------------------------------------------------- #


def test_stdlib_logging_goes_through_loguru(capsys):
    setup_logging("DEBUG")
    logging.getLogger("some.library").warning("from %s", "stdlib")
    text = out(capsys)
    assert "WARNING" in text
    assert "from stdlib" in text
    assert "test_logging.py:" in text  # the caller, not logging/__init__.py


def test_stdlib_root_level_follows_lowest_sink(tmp_path):
    setup_logging("WARNING")
    assert logging.getLogger().level == logging.WARNING
    setup_logging("WARNING", log_file=tmp_path / "app.log", file_level="DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_stdlib_custom_level_number(capsys):
    setup_logging()
    logging.getLogger("some.library").log(35, "custom level")
    text = out(capsys)
    assert "Level 35" in text
    assert "custom level" in text


def test_stdlib_intercept_can_be_turned_off_without_touching_other_handlers():
    setup_logging()
    other = logging.NullHandler()
    logging.getLogger().addHandler(other)
    setup_logging(intercept_stdlib=False)
    handlers = logging.getLogger().handlers
    assert not any(isinstance(h, _logger._InterceptHandler) for h in handlers)
    assert other in handlers


# ---------------------------------------------------------------------- #
# timed
# ---------------------------------------------------------------------- #


def test_timed_logs_duration_at_call_site(capsys):
    setup_logging("DEBUG")
    with timed("load data") as t:
        pass
    text = out(capsys)
    assert re.search(r"load data took \d+\.\d ms", text)
    assert "test_logging.py:" in text  # not timing.py
    assert t.elapsed is not None and t.elapsed >= 0


def test_timed_reports_failure_and_reraises(capsys):
    setup_logging()
    with pytest.raises(RuntimeError), timed("step"):
        raise RuntimeError("boom")
    assert "step failed after" in out(capsys)


def test_timed_level(capsys):
    setup_logging("INFO")
    with timed("quiet", level="DEBUG"):
        pass
    assert "quiet" not in out(capsys)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0.0123, "12.3 ms"), (1.5, "1.50 s"), (125, "2 min 5.0 s")],
)
def test_format_duration(seconds, expected):
    assert timing._format_duration(seconds) == expected


# ---------------------------------------------------------------------- #
# Progress (smoke test only)
# ---------------------------------------------------------------------- #


def test_progress_warns_when_used_after_close(capsys):
    setup_logging()
    with Progress(total=3, desc="work") as bar:
        bar.inc()
    bar.inc()
    assert "already closed" in out(capsys)


def test_progress_set_and_add():
    with Progress(total=10) as bar:
        bar.set(4)
        bar.add(3)
        assert bar._bar.n == 7


def test_progress_overrun_grows_total_and_changes_colour():
    with Progress(total=2) as bar:
        bar.set(3)
        assert bar._bar.n == 3
        assert bar._bar.total == 3
        assert bar.total == 4
        assert bar._bar.colour == "yellow"
