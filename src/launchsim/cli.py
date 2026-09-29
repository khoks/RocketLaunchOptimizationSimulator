"""Command-line interface: the only module that prints to stdout or reads YAML.

Output is ASCII only so it renders on a cp1252 console. Configuration and file-system
errors (unreadable or non-UTF-8 files, bad names, an unwritable results root) are
printed as one ``error:`` line without a traceback and exit 1; success exits 0; argparse
usage errors (no command, an unknown option) exit 2 with the usage text, as argparse
does. Anything else (a bug in the simulator) keeps its traceback.

    launchsim run   <experiment.yaml> [--results-root DIR] [--variant NAME] [--no-plots]
    launchsim sweep <experiment.yaml> [--results-root DIR] [--no-plots]
    launchsim --version

``--results-root`` defaults to ``<repo root>/results`` (the repository holding the
experiment file, found by its pyproject.toml), so the layout is the same from any cwd.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path, PureWindowsPath
from typing import Any

import yaml

from launchsim import __version__, sim
from launchsim.config import ResolvedExperiment, resolve_experiment

REPO_MARKER = "pyproject.toml"
RESULTS_DIR_NAME = "results"
RESULTS_ROOT_HELP = (
    "Root of the results tree (default: <repo root>/results, where the repo root is the "
    "nearest ancestor of the experiment file with a pyproject.toml, else ./results)."
)


class CliError(Exception):
    """A user-facing error: printed as one message, exit code 1."""


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for ``launchsim run`` and ``launchsim sweep``."""
    parser = argparse.ArgumentParser(
        prog="launchsim", description="Ground-powered launch-assist simulator."
    )
    parser.add_argument("--version", action="version", version=f"launchsim {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run one experiment: the pad baseline and every variant.")
    run.add_argument("experiment", help="Path to an experiment YAML file.")
    run.add_argument("--results-root", default=None, help=RESULTS_ROOT_HELP)
    run.add_argument("--variant", default=None, help="Run only this variant (plus the baseline).")
    run.add_argument("--no-plots", action="store_true", help="Skip PNG plots.")

    sweep = sub.add_parser("sweep", help="Run every sweep declared in an experiment.")
    sweep.add_argument("experiment", help="Path to an experiment YAML file.")
    sweep.add_argument("--results-root", default=None, help=RESULTS_ROOT_HELP)
    sweep.add_argument("--no-plots", action="store_true", help="Skip PNG plots.")
    return parser


def _configure_stdout() -> None:
    """Never crash on a console that cannot encode a character.

    say() already emits ASCII, so this only guards output the CLI does not route through
    it (argparse). It is deliberately process-wide and idempotent: main() is the console
    entry point, and an in-process caller (tests, a notebook) only loses the ability to
    raise UnicodeEncodeError on its own prints.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(errors="replace")


def say(text: str) -> None:
    """Print one line, escaping anything outside ASCII (paths, messages)."""
    print(text.encode("ascii", "backslashreplace").decode("ascii"))


def find_repo_root(start: Path) -> Path | None:
    """The nearest ancestor of ``start`` (inclusive) containing pyproject.toml, or None."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / REPO_MARKER).is_file():
            return candidate
    return None


def load_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML mapping (UTF-8, yaml.safe_load; merge keys are expanded by PyYAML)."""
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise CliError(f"file not found: {path}") from exc
    except OSError as exc:  # a directory, a permission problem, an unreadable file
        raise CliError(f"cannot read {path}: {exc}") from exc
    except UnicodeDecodeError as exc:  # saved as ANSI/cp1252 with a degree sign, say
        raise CliError(
            f"{path} is not UTF-8 (byte {exc.start}: {exc.reason}); save the file as UTF-8"
        ) from exc
    except yaml.YAMLError as exc:
        raise CliError(f"cannot parse YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CliError(f"{path}: expected a YAML mapping at the top level")
    return data


def is_rooted(path: str) -> bool:
    """True for a path that must not be joined onto another: absolute on this platform,
    ``~``-prefixed, POSIX-rooted (``/x`` or ``\\x``, which Windows reports as relative
    but a config author means as absolute), or carrying a Windows drive (``C:...``)."""
    return (
        path.startswith(("/", "\\", "~"))
        or Path(path).is_absolute()
        or bool(PureWindowsPath(path).drive)
    )


def is_drive_relative(path: str) -> bool:
    """True for ``C:x``: a drive without a root. Windows resolves it against a hidden
    per-drive current directory, so which file it names depends on shell history."""
    win = PureWindowsPath(path)
    return bool(win.drive) and not win.root


def resolve_vehicle_path(experiment_path: Path, vehicle: str) -> Path:
    """Locate the vehicle file: relative to the experiment file's directory first, then to
    the repository root (the nearest ancestor with pyproject.toml). Rooted paths
    (absolute, ``~/...`` or ``/...``) are used as given; a missing one is an error, and so
    is a drive-relative ``C:x`` path."""
    if is_drive_relative(vehicle):
        raise CliError(
            f"vehicle path {vehicle!r} is drive-relative and ambiguous; use an absolute path"
        )
    if is_rooted(vehicle):
        candidate = Path(vehicle).expanduser()
        if candidate.is_file():
            return candidate
        raise CliError(f"vehicle file not found: {candidate}")
    candidate = Path(vehicle)
    tried = [experiment_path.parent / candidate]
    repo_root = find_repo_root(experiment_path.parent)
    if repo_root is not None:
        tried.append(repo_root / candidate)
    for path in tried:
        if path.is_file():
            return path
    raise CliError(f"vehicle file {vehicle!r} not found; tried " + ", ".join(str(p) for p in tried))


def load_experiment(experiment_path: Path) -> ResolvedExperiment:
    """Read and validate an experiment file and its vehicle; raises CliError on any problem."""
    exp_dict = load_yaml(experiment_path)
    vehicle = exp_dict.get("vehicle")
    if not isinstance(vehicle, str):
        raise CliError(f"{experiment_path}: 'vehicle' must be a path string")
    vehicle_dict = load_yaml(resolve_vehicle_path(experiment_path, vehicle))
    try:
        resolved = resolve_experiment(exp_dict, vehicle_dict)
        sim.check_result_names(resolved)  # names become directories: reject before writing
    except ValueError as exc:  # pydantic ValidationError, ConfigPathError, InvalidNameError
        raise CliError(f"invalid configuration in {experiment_path}:\n{exc}") from exc
    return resolved


def repo_root_or_cwd(experiment_path: Path) -> Path:
    """The repository holding the experiment file (nearest pyproject.toml), else cwd."""
    root = find_repo_root(experiment_path.parent)
    return Path.cwd() if root is None else root


def results_root(args: argparse.Namespace, experiment_path: Path) -> Path:
    """``--results-root`` as given, else ``<repo root>/results`` (see repo_root_or_cwd)."""
    if args.results_root is not None:
        return Path(args.results_root)
    return repo_root_or_cwd(experiment_path) / RESULTS_DIR_NAME


def command_run(args: argparse.Namespace) -> int:
    """Run an experiment (baseline + variants) and print the results directory."""
    experiment_path = Path(args.experiment)
    resolved = load_experiment(experiment_path)
    if args.variant is not None and args.variant not in resolved.variants:
        raise CliError(
            f"variant {args.variant!r} not in experiment {resolved.experiment.name!r}: "
            f"{sorted(resolved.variants)}"
        )
    er, out_dir = sim.run_experiment(
        resolved,
        results_root(args, experiment_path),
        plots=not args.no_plots,
        only_variant=args.variant,
        repo_root=repo_root_or_cwd(experiment_path),
    )
    say(f"results: {out_dir}")
    for name, rr in er.runs.items():
        tag = " (baseline)" if name == er.baseline.name else ""
        flags = f" flags: {', '.join(rr.result.flags)}" if rr.result.flags else ""
        say(f"  {name}{tag}: {rr.result.status}{flags}")
    return 0


def command_sweep(args: argparse.Namespace) -> int:
    """Run every sweep of an experiment and print the results directory."""
    experiment_path = Path(args.experiment)
    resolved = load_experiment(experiment_path)
    sweeps, out_dir = sim.run_sweep(
        resolved,
        results_root(args, experiment_path),
        plots=not args.no_plots,
        repo_root=repo_root_or_cwd(experiment_path),
    )
    say(f"results: {out_dir}")
    if not sweeps:
        say("  no sweeps declared")
    for sweep in sweeps:
        statuses = sorted({rr.result.status for rr in sweep.results})
        say(
            f"  sweep_{sweep.sweep_index}: {sweep.of} x {len(sweep.results)} points "
            f"over {', '.join(sweep.axes)}: {', '.join(statuses)}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the process exit code: 0 on success, 1 for a configuration or
    file-system error (CliError, OSError), printed as one ``error:`` line. argparse
    raises SystemExit(2) for a usage error and SystemExit(0) for ``--version``."""
    _configure_stdout()
    args = build_parser().parse_args(argv)
    commands = {"run": command_run, "sweep": command_sweep}
    try:
        return commands[args.command](args)
    except CliError as exc:
        say(f"error: {exc}")
        return 1
    except OSError as exc:  # unwritable results root, a root that is a file, ...
        say(f"error: {type(exc).__name__}: {exc}")
        return 1
