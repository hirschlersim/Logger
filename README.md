# logger

A small [Loguru](https://github.com/Delgan/loguru) setup with [tqdm](https://github.com/tqdm/tqdm)-safe output, meant to be used as a git submodule at `libs/logger` in other projects.

- Log lines never break up progress bars.
- Optional log file with rotation and retention.
- Standard-library `logging` (used by requests, urllib3, ...) goes through the same output.
- Level from the code or the `LOG_LEVEL` environment variable.
- `timed()` to log how long a block took, and `Progress` bars.

## Add it to a project

```powershell
git submodule add https://github.com/hirschlersim/logger.git libs/logger
uv add loguru tqdm          # a submodule does not bring its dependencies along
git commit -m "Add logger submodule"
```

Run your code from the project root (`uv run main.py`, `python -m app`) so `libs` is importable. An empty `libs/__init__.py` is optional, but it keeps linters and IDEs happy.

If the project uses pytest, point it at your own tests so it doesn't also run this repo's tests:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

## Use it

```python
from libs.logger import Progress, logger, setup_logging, timed

setup_logging("DEBUG", log_file="logs/app.log")

logger.info("Starting")

with timed("load data"):
    ...

with Progress(total=100, desc="Processing") as bar:
    for _ in range(100):
        bar.inc()
```

`logger` is Loguru's own logger, so all of Loguru works (`logger.exception`, `logger.bind`, `@logger.catch`, ...) and your IDE gets full autocompletion.

On import, a console sink at `LOG_LEVEL` (or `INFO`) is installed, so logging works without calling `setup_logging()`. Standard-library `logging` is only taken over when you call `setup_logging()` yourself.

### `setup_logging()` options

| Argument | Default | Meaning |
| --- | --- | --- |
| `level` | `LOG_LEVEL` env var, else `"INFO"` | Console level. At `DEBUG` or lower, lines also show `file:line`. |
| `log_file` | `None` | Also write to this file. Missing folders are created. |
| `file_level` | `"DEBUG"` | Level for the log file. |
| `rotation` | `"10 MB"` | When to start a new file (`"1 day"`, `"00:00"`, ...). |
| `retention` | `"7 days"` | How long to keep old files (or a count, like `5`). |
| `colorize` | auto | Colours on when stdout is a terminal and `NO_COLOR` is unset. |
| `intercept_stdlib` | `True` | Route standard-library `logging` through Loguru. Replaces the root logger's handlers. |

Calling `setup_logging()` again replaces the previous setup completely (it removes *all* Loguru handlers). Add your own sinks with `logger.add()` after calling it.

An invalid `level` argument raises `ValueError`. An invalid `LOG_LEVEL` value logs a warning and falls back to `INFO`.

### Environment variables

| Variable | Effect |
| --- | --- |
| `LOG_LEVEL` | Console level when no `level` argument is given (`DEBUG`, `info`, `TRACE`, ...). |
| `NO_COLOR` | Any non-empty value turns off colours (unless `colorize=True` is passed). |

### `timed`

```python
with timed("load data"):  # INFO | load data took 1.23 s
    ...

with timed("query", level="DEBUG") as t:
    ...
print(t.elapsed)  # seconds, as a float
```

If the block raises, it logs `<label> failed after ...` and the exception propagates.

## Updating and editing

In a project that uses this as a submodule:

```powershell
git submodule update --init                # after cloning (or clone with --recurse-submodules)
git submodule update --remote libs/logger  # move to the latest commit on main
git -C libs/logger checkout v0.1.0         # or pin a specific tag
git commit -am "Bump logger"               # the project records which commit it uses
```

To change the logger from inside a project, run `git switch main` in `libs/logger` first. A submodule checkout is not on a branch. Commit and push there, then commit the new pointer in the project.

## Development

```powershell
uv sync
uv run pytest
uvx ruff check .
uvx ruff format --check .
uvx pyright
```

The repo root is the package itself, which is what lets it sit directly in `libs/logger`. `tests/` is a subpackage, so the tests use relative imports (`from .. import logger`).

Tag releases (`git tag v0.2.0`, `git push --tags`) so projects can pin a known-good version.

## License

[MIT](LICENSE)
