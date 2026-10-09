"""Command-line interface: the only module that prints to stdout or reads configuration
YAML (``animate`` hands a results directory to plots.write_ascent_animation, which reads
that directory's metrics.json and resolved_config.yaml).

Output is ASCII only so it renders on a cp1252 console. Configuration and file-system
errors (unreadable or non-UTF-8 files, bad names, an unwritable results root) are
printed as one ``error:`` line without a traceback and exit 1; success exits 0; argparse
usage errors (no command, an unknown option) exit 2 with the usage text, as argparse
does. Anything else (a bug in the simulator) keeps its traceback.

    launchsim run   <experiment.yaml> [--results-root DIR] [--variant NAME] [--no-plots]
                    [--no-sensitivity] [--no-offload]
    launchsim sweep <experiment.yaml> [--results-root DIR] [--no-plots] [--no-offload]
    launchsim animate <run_dir> [--runs NAME [NAME ...]] [--out PATH] [--fps N]
                      [--seconds S] [--width PX]
    launchsim replay <run_dir> [--runs NAME [NAME ...]] [--out PATH]
    launchsim scene <run_dir> [--runs NAME [NAME ...]] [--out PATH] [--display PATH]
    launchsim app [--port N] [--results-root PATH] [--open]
    launchsim --version

``--results-root`` defaults to ``<repo root>/results`` (the repository holding the
experiment file, found by its pyproject.toml), so the layout is the same from any cwd.

``animate`` replays planar_2d runs of one results directory (results/<experiment>/
<timestamp>) as an .mp4 (ffmpeg) or .gif (Pillow); the default output is
./<experiment>_<timestamp>_animation.mp4 (.gif without ffmpeg), never inside results/.

``replay`` writes the same kind of selection as one self-contained interactive HTML page
(replay.write_replay_page: scrub, play, telemetry, metrics and caveats); the default
output is ./<experiment>_<timestamp>_replay.html, never inside results/.

``scene`` writes the 2-D launch scene of planar_2d runs as one standalone HTML page
(scene.write_scene_page: a true-scale cross-section of the site with a fixed-scale
close-up of the vehicle, telemetry, events and caveats; it makes no request); the
default output is ./<experiment>_<timestamp>_scene.html, never inside results/. The
display files come from ``--display`` or else configs/display of the repository found
above the working directory, then above the installed package.

``app`` serves the local app on http://127.0.0.1:<port>/ (127.0.0.1 only; port 8765 by
default, 0 picks a free one; a busy port is one ``error:`` line and exit 1, never another
port) until Ctrl+C (or Ctrl+Break on Windows), which stops the server, marks a running
launch FAILED and exits 0. Launches are exploratory and go to <results root>/app/; the
default results root is <repo root>/results, the repository being the nearest one above
the working directory, else above the installed package, that holds
experiments/silo_offload_2d.yaml. ``--open`` opens the page in a new browser tab. ffmpeg
is resolved once at start (video.find_ffmpeg; the start lines print its absolute path or
why the MP4 export is off); videos go to the working directory, never into results/.
"""

from __future__ import annotations

import argparse
import contextlib
import signal
import sys
import webbrowser
from collections.abc import Iterator
from pathlib import Path, PureWindowsPath
from typing import Any

import yaml

from launchsim import __version__, app, plots, replay, run_data, scene, sim, video
from launchsim.compare import CHECK_NA
from launchsim.config import (
    OFFLOAD_GROSS_MODES,
    ResolvedExperiment,
    StructureConfig,
    resolve_experiment,
)
from launchsim.results_io import OFFLOAD_QUOTED_FAILED, OFFLOAD_QUOTED_NO_CONTROL
from launchsim.units import kg_to_t, rad_to_deg, to_percent

REPO_MARKER = "pyproject.toml"
RESULTS_DIR_NAME = "results"
RESULTS_ROOT_HELP = (
    "Root of the results tree (default: <repo root>/results, where the repo root is the "
    "nearest ancestor of the experiment file with a pyproject.toml, else ./results)."
)


class CliError(Exception):
    """A user-facing error: printed as one message, exit code 1."""


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for ``launchsim run``, ``sweep``, ``animate``, ``replay``
    and ``scene``."""
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
    run.add_argument(
        "--no-sensitivity",
        action="store_true",
        help="Skip the sensitivity cases (the +/- parameter re-runs), the offload block's "
        "sensitivity arms included.",
    )
    run.add_argument(
        "--no-offload",
        action="store_true",
        help="Skip the experiment's offload block (planar_2d: the propellant saved at fixed "
        "payload); the summary says it was skipped.",
    )

    sweep = sub.add_parser("sweep", help="Run every sweep declared in an experiment.")
    sweep.add_argument("experiment", help="Path to an experiment YAML file.")
    sweep.add_argument("--results-root", default=None, help=RESULTS_ROOT_HELP)
    sweep.add_argument("--no-plots", action="store_true", help="Skip PNG plots.")
    sweep.add_argument(
        "--no-offload",
        action="store_true",
        help="Skip the offload cases a sweep names (no offload columns in sweep_index.csv).",
    )

    animate = sub.add_parser(
        "animate",
        help="Replay planar_2d runs of one results directory as an .mp4 or .gif.",
    )
    animate.add_argument(
        "run_dir", help="A results directory of a planar_2d run: results/<experiment>/<timestamp>."
    )
    animate.add_argument(
        "--runs",
        nargs="+",
        default=None,
        metavar="NAME",
        help="Runs to show (default: the baseline plus up to three variants, summary order).",
    )
    animate.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="Output file; the extension picks the format: .mp4 (needs ffmpeg) or .gif. "
        "Default: ./<experiment>_<timestamp>_animation.mp4 (.gif without ffmpeg), "
        "never inside results/.",
    )
    animate.add_argument(
        "--fps",
        type=int,
        default=plots.ANIMATION_DEFAULT_FPS,
        metavar="N",
        help="Frames per second (default: %(default)s; a .gif plays at 1000/delay fps, "
        "its frame delays being whole 10 ms steps, at most 50 fps).",
    )
    animate.add_argument(
        "--seconds",
        type=float,
        default=plots.ANIMATION_DEFAULT_SECONDS,
        metavar="S",
        help="Video length [s] (default: %(default)s).",
    )
    animate.add_argument(
        "--width",
        type=int,
        default=plots.ANIMATION_DEFAULT_WIDTH_PX,
        metavar="PX",
        help="Frame width [px], even; the frame is 16:9 (default: %(default)s).",
    )

    rep = sub.add_parser(
        "replay",
        help="Write an interactive HTML replay of planar_2d runs of one results directory.",
    )
    rep.add_argument(
        "run_dir", help="A results directory of a planar_2d run: results/<experiment>/<timestamp>."
    )
    rep.add_argument(
        "--runs",
        nargs="+",
        default=None,
        metavar="NAME",
        help="Runs to show (default: the baseline plus up to three variants, summary order).",
    )
    rep.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="Output .html file. Default: ./<experiment>_<timestamp>_replay.html, "
        "never inside results/.",
    )

    scn = sub.add_parser(
        "scene",
        help="Write the 2-D launch scene of planar_2d runs of one results directory as a "
        "standalone HTML page.",
    )
    scn.add_argument(
        "run_dir", help="A results directory of a planar_2d run: results/<experiment>/<timestamp>."
    )
    scn.add_argument(
        "--runs",
        nargs="+",
        default=None,
        metavar="NAME",
        help="Runs the page can show (default: the baseline and the first solved stage-1 "
        "offload case, else the first assisted variant that is not a yardstick).",
    )
    scn.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="Output .html file. Default: ./<experiment>_<timestamp>_scene.html, "
        "never inside results/.",
    )
    scn.add_argument(
        "--display",
        default=None,
        metavar="PATH",
        help="Folder of the display files (scene.yaml and one file per vehicle family). "
        "Default: configs/display of the repository above the working directory, else "
        "above the installed package.",
    )

    srv = sub.add_parser(
        "app",
        help="Serve the local app (launch form, results, scene) on 127.0.0.1 until Ctrl+C.",
    )
    srv.add_argument(
        "--port",
        type=int,
        default=app.DEFAULT_PORT,
        metavar="N",
        help="Port on 127.0.0.1 (default: %(default)s; 0 picks a free port). A busy port is "
        "an error, never another port.",
    )
    srv.add_argument(
        "--results-root",
        default=None,
        metavar="PATH",
        help="Root of the results tree the app lists and launches into (<root>/app/). "
        "Default: <repo root>/results.",
    )
    srv.add_argument("--open", action="store_true", help="Open the app page in a new browser tab.")
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
    """Read and validate an experiment file and its vehicle; raises CliError on any
    problem, including a run name unfit for a directory (``sim.check_result_names``)
    and a run refused by the preflight (``sim.check_resolved``: a ramp start the push
    cannot reach, for example), so neither is written and either prints one ``error:``
    line. A calibration case that names its own vehicle file is read through the
    same lookup as the experiment's vehicle (``resolve_vehicle_path``)."""
    exp_dict = load_yaml(experiment_path)
    vehicle = exp_dict.get("vehicle")
    if not isinstance(vehicle, str):
        raise CliError(f"{experiment_path}: 'vehicle' must be a path string")
    vehicle_dict = load_yaml(resolve_vehicle_path(experiment_path, vehicle))

    def load_vehicle(path: str) -> dict[str, Any]:
        return load_yaml(resolve_vehicle_path(experiment_path, path))

    try:
        resolved = resolve_experiment(exp_dict, vehicle_dict, load_vehicle)
        sim.check_result_names(resolved)  # names become directories: reject before writing
        sim.check_resolved(resolved)  # every run's specs build (the preflight)
    except ValueError as exc:  # ValidationError, ConfigPathError, InvalidNameError, preflight
        raise CliError(f"invalid configuration in {experiment_path}:\n{exc}") from exc
    return resolved


def load_structure(path: Path) -> StructureConfig:
    """Read and validate a structure file (configs/structures/<vehicle>.yaml, SP7 step S2;
    design 4.3): the YAML by ``load_yaml``, the model by ``config.StructureConfig``, which
    checks every number's provenance, the ranges and that the central set and each range's
    ends convert. Raises CliError on any problem (a missing or unreadable file, bad YAML, a
    validation error), one ``error:`` line as for an experiment. Passing it to
    ``resolve_experiment`` as a keyword-only loader arrives in step S3."""
    data = load_yaml(path)
    try:
        return StructureConfig.model_validate(data)
    except ValueError as exc:  # pydantic's ValidationError included
        raise CliError(f"invalid structure file {path}:\n{exc}") from exc


def repo_root_or_cwd(experiment_path: Path) -> Path:
    """The repository holding the experiment file (nearest pyproject.toml), else cwd."""
    root = find_repo_root(experiment_path.parent)
    return Path.cwd() if root is None else root


def results_root(args: argparse.Namespace, experiment_path: Path) -> Path:
    """``--results-root`` as given, else ``<repo root>/results`` (see repo_root_or_cwd)."""
    if args.results_root is not None:
        return Path(args.results_root)
    return repo_root_or_cwd(experiment_path) / RESULTS_DIR_NAME


def run_line(name: str, result: sim.Result, baseline: bool) -> str:
    """The console line of one run: its status and flags; a planar run also prints
    P* [kg], gamma*_ref [deg] and max-Q [Pa] (the headline, ASCII only)."""
    tag = " (baseline)" if baseline else ""
    flags = f" flags: {', '.join(result.flags)}" if result.flags else ""
    if result.model != sim.PLANAR_MODEL:
        return f"  {name}{tag}: {result.status}{flags}"
    m = result.metrics
    gamma = m.get("gamma_star_rad")
    gamma_deg = None if gamma is None else float(rad_to_deg(gamma))
    head = (
        f"P* {sim._fmt(m.get('payload_kg'))} kg, gamma* {sim._fmt(gamma_deg)} deg, "
        f"max-Q {sim._fmt(m.get('max_q_pa'))} Pa"
    )
    return f"  {name}{tag}: {result.status} ({head}){flags}"


OFFLOAD_NOT_QUOTED_REASONS: dict[str, str] = {
    OFFLOAD_QUOTED_NO_CONTROL: "no pad-control offload to net it against",
    OFFLOAD_QUOTED_FAILED: "the case's own solve did not end ok",
}
"""The console's short reason for a solve that quotes no offload, by its record's
``quoted_basis`` (``results_io._quoted_offload``)."""


def offload_lines(record: dict[str, Any]) -> list[str]:
    """The console lines of an offload block (ASCII): the skip note, or the reference
    payload and one line per case and per pad control. A stage-1 solve: status, the
    gross offload in tonnes and in % of the stage-1 and total loads, the decomposition
    status. A fixed case: the same, then its figure P* - P_ref [kg]. A stage2 or both
    solve leads with its quoted offload, net of the pad control, labelled a property of
    the vehicle model, the gross tonnes after it (D-SP1-10). A solve that quotes nothing
    says "not quoted" and why (OFFLOAD_NOT_QUOTED_REASONS, from its ``quoted_basis``; a
    failed solve without the vehicle-model label). A pad control: status, x_pad and, for
    stage 1, its consistency verdict."""
    if record.get("skipped"):
        return [f"  offload: {record['skipped']}"]

    def tonnes(kg: Any) -> str:
        return sim._fmt(None if kg is None else float(kg_to_t(kg)))

    def percent(fraction: Any) -> str:
        return sim._fmt(None if fraction is None else float(to_percent(fraction)))

    lines = [f"  offload at P_ref {sim._fmt(record.get('reference_payload_kg'))} kg:"]
    for c in record.get("cases") or []:
        if c.get("skipped"):
            lines.append(f"    {c.get('name')}: {c['skipped']}")
            continue
        gross = tonnes(c.get("total_offload_kg"))
        shares = (
            f"({percent(c.get('stage1_fraction'))} % of stage 1, "
            f"{percent(c.get('total_fraction'))} % of the total)"
        )
        removed = f"{gross} t removed {shares}"
        netted = c.get("mode") not in OFFLOAD_GROSS_MODES
        vehicle_model = ", a property of the vehicle model" if netted else ""
        quoted = c.get("quoted_offload_kg")
        if c.get("kind") != "solve":  # a fixed case: its figure is P* - P_ref
            text = f"{removed}, P* - P_ref {sim._signed(c.get('payload_delta_kg'))} kg"
        elif quoted is None:
            basis = str(c.get("quoted_basis"))
            reason = OFFLOAD_NOT_QUOTED_REASONS.get(basis, basis)
            label = "" if basis == OFFLOAD_QUOTED_FAILED else vehicle_model
            text = f"not quoted ({reason}){label}; gross {removed}"
        elif netted:
            text = f"{tonnes(quoted)} t net of the pad control{vehicle_model}; gross {removed}"
        else:
            text = removed
        lines.append(
            f"    {c.get('name')}: {c.get('status')}, {text}, "
            f"decomposition {c.get('decomposition_status')}"
        )
    for p in record.get("pad_controls") or []:
        verdict = p.get("consistency")
        tail = "" if verdict in (None, CHECK_NA) else f", consistency {verdict}"
        lines.append(
            f"    pad control {p.get('mode')}: {p.get('status')}, x_pad "
            f"{sim._fmt(p.get('offload_kg'))} kg{tail}"
        )
    if record.get("sensitivity"):
        lines.append(f"    sensitivity: {len(record['sensitivity'])} arms")
    return lines


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
        sensitivity=not args.no_sensitivity,
        offload=not args.no_offload,
    )
    say(f"results: {out_dir}")
    for name, rr in er.runs.items():
        say(run_line(name, rr.result, name == er.baseline.name))
    for name, rr in er.cases.items():
        say(run_line(f"case {name}", rr.result, False))
    if er.offload is not None:
        for line in offload_lines(er.offload.record):
            say(line)
    if er.preregistration is not None:
        state = er.preregistration
        if state.get("dirty") is False:
            say(f"  pre-registered inputs clean at {state.get('inputs_commit')}")
        else:
            say(
                "  PREREGISTRATION DIRTY: configs/ or experiments/ not committed;"
                " not a valid calibration record"
            )
    if er.sensitivity:
        say(f"  sensitivity: {len(er.sensitivity)} cases")
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
        offload=not args.no_offload,
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


def command_animate(args: argparse.Namespace) -> int:
    """Write the animation of a planar results directory and print its path."""
    run_dir = Path(args.run_dir)
    try:
        runs, _ = plots.load_animation_runs(run_dir, args.runs)  # validate before rendering
        out = (
            plots.default_animation_path(run_dir, Path.cwd())
            if args.out is None
            else Path(args.out)
        )
        plots.check_animation_out(out, run_dir)
        play_fps = plots.animation_playback_fps(args.fps, out.suffix)
        n_frames = plots.animation_frame_count(play_fps, args.seconds)
        _, _, (width_px, height_px) = plots.frame_geometry(args.width)
        rate = f"{args.fps} fps"
        if play_fps != args.fps:
            rate += f" (a .gif plays at {play_fps:g} fps: its frame delays are 10 ms steps)"
        say(
            f"rendering {', '.join(r.name for r in runs)}: {n_frames} frames at {rate}, "
            f"{width_px}x{height_px} px ..."
        )
        written = plots.write_ascent_animation(
            run_dir,
            args.runs,
            out,
            fps=args.fps,
            seconds=args.seconds,
            width=args.width,
        )
    except plots.AnimationError as exc:
        raise CliError(str(exc)) from exc
    say(f"animation: {written}")
    return 0


def command_replay(args: argparse.Namespace) -> int:
    """Write the interactive replay page of a planar results directory and print its
    path and size."""
    run_dir = Path(args.run_dir)
    try:
        replay.check_replay_run_dir(run_dir)  # a clear error before choosing the output
        out = (
            replay.default_replay_path(run_dir, Path.cwd()) if args.out is None else Path(args.out)
        )
        written = replay.write_replay_page(run_dir, args.runs, out)
    except replay.ReplayError as exc:
        raise CliError(str(exc)) from exc
    say(f"replay: {written} ({written.stat().st_size / 1024:.0f} KiB)")
    return 0


def scene_display_dir(display: str | None) -> Path:
    """The display files' folder: ``--display`` as given, else configs/display
    (scene.DEFAULT_DISPLAY_DIR) of the nearest repository (pyproject.toml) above the
    working directory that has one, else of the repository above the installed package.
    Raises CliError when neither has it."""
    if display is not None:
        return Path(display)
    for start in (Path.cwd(), Path(scene.__file__).resolve().parent):
        root = find_repo_root(start)
        if root is not None and (root / scene.DEFAULT_DISPLAY_DIR).is_dir():
            return root / scene.DEFAULT_DISPLAY_DIR
    raise CliError(
        f"no {scene.DEFAULT_DISPLAY_DIR.as_posix()} folder above the working directory or "
        "the installed package; pass --display PATH"
    )


def command_scene(args: argparse.Namespace) -> int:
    """Write the standalone scene page of a planar results directory and print its path
    and size. The directory is checked first (a clear error before the display files are
    looked for, as ``command_replay`` checks its directory before choosing the output);
    a missing display folder raises CliError unchanged."""
    run_dir = Path(args.run_dir)
    try:
        scene.check_scene_run_dir(run_dir)
        display_dir = scene_display_dir(args.display)
        written = scene.write_scene_page(
            run_dir,
            args.runs,
            None if args.out is None else Path(args.out),
            cwd=Path.cwd(),
            display_dir=display_dir,
        )
    except run_data.RunDataError as exc:  # SceneError and the shared readers' refusals
        raise CliError(str(exc)) from exc
    say(f"scene: {written} ({written.stat().st_size / 1024:.0f} KiB)")
    return 0


MAX_PORT = 65535
"""The largest TCP port."""


def app_repo_root(starts: list[Path] | None = None) -> Path:
    """The repository the app reads its experiments from: the nearest repository
    (pyproject.toml) above the working directory, else above the installed package, that
    holds app.OFFLOAD_EXPERIMENT. Raises CliError (one line) when neither does."""
    for start in starts or [Path.cwd(), Path(app.__file__).resolve().parent]:
        root = find_repo_root(start)
        if root is not None and (root / app.OFFLOAD_EXPERIMENT).is_file():
            return root
    raise CliError(
        f"{app.OFFLOAD_EXPERIMENT.as_posix()} not found in a repository above the working "
        "directory or the installed package: start the app from a checkout of the repository"
    )


INTERRUPT_SIGNALS = tuple(
    getattr(signal, name) for name in ("SIGINT", "SIGBREAK") if hasattr(signal, name)
)
"""The console's stop signals: Ctrl+C, and Ctrl+Break on Windows."""


@contextlib.contextmanager
def interrupts_ignored() -> Iterator[None]:
    """INTERRUPT_SIGNALS ignored inside the block (a second Ctrl+C or Ctrl+Break while the
    app stops does nothing), the previous handlers restored after it. Main thread only."""
    previous: list[tuple[int, Any]] = []
    try:
        for sig in INTERRUPT_SIGNALS:
            previous.append((sig, signal.signal(sig, signal.SIG_IGN)))
        yield
    finally:
        for sig, handler in reversed(previous):
            signal.signal(sig, handler)


def stopping_line() -> str:
    """What the app prints as soon as Ctrl+C or Ctrl+Break arrives."""
    return (
        "launchsim app: stopping; a launch that is writing gets up to "
        f"{app.STOP_WRITING_GRACE_S:g} s to finish (further Ctrl+C is ignored)"
    )


STOPPED_BEFORE_SERVING_LINE = "launchsim app: stopped before it served"
"""What the app prints for a Ctrl+C or Ctrl+Break during its start (before the URL)."""


def video_line(server: app.AppServer) -> str:
    """The start line on the MP4 export: the resolved ffmpeg's absolute path and the folder
    videos go to (the working directory), or why the export is off."""
    if server.video_reason or server.encoder is None:
        return f"  video: MP4 export off ({server.video_reason})"
    return f"  video: ffmpeg {server.encoder.display}; MP4 files go to {server.work_dir}"


def app_server(args: argparse.Namespace) -> tuple[app.AppServer, Path, app.ServerStart]:
    """(the bound server, the results root, the server-start record) of ``launchsim app``:
    check the repository (the experiment files, ``app_repo_root``; the display files the
    scene pages need, scene.DEFAULT_DISPLAY_DIR: CliError at start, not a 500 on every
    scene), record the server start, read the basis, bind (CliError, one line, for a busy
    or reserved port)."""
    repo_root = app_repo_root()
    display = repo_root / scene.DEFAULT_DISPLAY_DIR
    if not display.is_dir():
        raise CliError(
            f"{scene.DEFAULT_DISPLAY_DIR.as_posix()} not found in {repo_root}: the scene pages "
            "need it"
        )
    results = (
        Path(args.results_root) if args.results_root is not None else repo_root / RESULTS_DIR_NAME
    )
    start = app.take_server_start(repo_root)
    try:
        basis = app.load_basis(repo_root, start)
    except app.BasisError as exc:
        raise CliError(str(exc)) from exc
    work_dir = Path.cwd()
    lookup = video.find_ffmpeg(work_dir, repo_root, results)
    try:
        server = app.AppServer(
            port=args.port,
            basis=basis,
            server_start=start,
            results_root=results,
            repo_root=repo_root,
            display_dir=display,
            encoder=lookup.encoder,
            video_reason=lookup.reason,
            work_dir=work_dir,
        )
    except OSError as exc:
        if app.port_unavailable(exc):
            raise CliError(
                f"port {args.port} on {app.BIND_HOST} is in use or reserved (another launchsim "
                "app or another program on that port?); stop it or pass --port N (0 picks a "
                "free one)"
            ) from exc
        raise CliError(
            f"cannot listen on {app.BIND_HOST}:{args.port}: {type(exc).__name__}"
        ) from exc
    return server, results, start


def command_app(args: argparse.Namespace) -> int:
    """Serve the local app until Ctrl+C (or Ctrl+Break, handled as Ctrl+C on Windows from
    the command's first statement): build the server (``app_server``; an interrupt
    during that start prints STOPPED_BEFORE_SERVING_LINE and returns 0, the server closed
    if it was bound), print the start lines, serve (``--open``: the URL opened once in
    the browser). When serving ends by any exception, with further interrupts ignored
    (``interrupts_ignored``), mark a running launch FAILED (``AppServer.stop_active_job``;
    one still in its preflight is marked by the worker once its directory exists) and
    close the server; on an interrupt print ``stopping_line`` first, then one stopped
    line, and return 0; any other exception is raised again (``main`` prints its error
    line)."""
    if not 0 <= args.port <= MAX_PORT:
        raise CliError(f"--port must be 0 to {MAX_PORT} (0 picks a free port)")
    previous = None
    if hasattr(signal, "SIGBREAK"):
        previous = signal.signal(signal.SIGBREAK, signal.default_int_handler)
    built: tuple[app.AppServer, Path, app.ServerStart] | None = None
    try:
        try:
            built = app_server(args)
        except KeyboardInterrupt:
            with interrupts_ignored():
                if built is not None:
                    built[0].close()
                say(STOPPED_BEFORE_SERVING_LINE)
            return 0
        server, results, start = built
        with server:
            try:
                git = start.git
                state = app.tree_state(git.get("dirty"), git.get("hash"))
                say(f"launchsim app: {server.url}   (this machine only)")
                say(f"  results root: {results}")
                say(
                    f"  code: git {git.get('hash', 'no-git')} ({state}) as of server start; a "
                    "launch is refused after a code change: restart the app"
                )
                say("  launches are exploratory, not findings")
                say("  Ctrl+C stops the server; a running launch is stopped and marked FAILED")
                say(video_line(server))
                sys.stdout.flush()
                if args.open:
                    webbrowser.open_new_tab(server.url)
                server.serve_forever(poll_interval=app.SERVE_POLL_S)
            except BaseException as exc:
                interrupted = isinstance(exc, KeyboardInterrupt)
                with interrupts_ignored():
                    if interrupted:
                        say(stopping_line())
                        sys.stdout.flush()
                    server.stop_active_job()
                    server.close()
                if not interrupted:
                    raise
    finally:
        if previous is not None:
            signal.signal(signal.SIGBREAK, previous)
    stopped = server.stopped_dir
    tail = "" if stopped is None else f"; the running launch is marked FAILED in {stopped}"
    say(f"launchsim app: stopped{tail}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the process exit code: 0 on success, 1 for a configuration or
    file-system error (CliError, OSError), printed as one ``error:`` line. argparse
    raises SystemExit(2) for a usage error and SystemExit(0) for ``--version``."""
    _configure_stdout()
    args = build_parser().parse_args(argv)
    commands = {
        "run": command_run,
        "sweep": command_sweep,
        "animate": command_animate,
        "replay": command_replay,
        "scene": command_scene,
        "app": command_app,
    }
    try:
        return commands[args.command](args)
    except CliError as exc:
        say(f"error: {exc}")
        return 1
    except OSError as exc:  # unwritable results root, a root that is a file, ...
        say(f"error: {type(exc).__name__}: {exc}")
        return 1
