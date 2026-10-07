"""The 2-D launch scene: its data payload and its standalone page (I/O: reads one results
directory and the display files under configs/display/; writes only the page, never
inside a results tree).

``scene_payload`` builds, for one to run_data.MAX_RUNS runs of a planar_2d results
directory (results/<experiment>/<timestamp>), everything the scene page draws, as plain
JSON-ready data (SP2 step A2, docs/phases/inputs/2026-10-05-SP2-design.md section 4.4):

- per run, the recorded series on the scene's time grid, a SELECTION of the run's own
  CSV rows and never a resample (D-SP2-16, display.select_rows): time after release to
  TIME_DECIMALS (the event rows and the row of the series' peak q always among them),
  altitude, Earth-fixed downrange, Earth-relative speed, the unwrapped
  pitch and the drawn (held) angle, the plume fraction (``thrust_vac_N`` over the stage's
  full vacuum thrust from the run's own vehicle block), the step series (stage index,
  phase, fairing on, thrust on), the track series over the push (null outside it), q and
  Mach (null inside the vented shaft), the run's recorded max-Q (``max_q``: metrics.json's
  ``max_q_pa`` and ``max_q_time_s``, the planar metrics' refined peak, already after
  release; None when the record has none), the felt axial acceleration (``felt_axial_g`` as
  recorded, in g), the two tank series (display.tank_levels, 0.1 kg) and their fills
  against the full-load tanks of the fill-reference block;
- the events with the mass before and after each drop (run_data.with_drop_masses),
  labelled by name and stage, each at its matched row's time; a pad's liftoff and ramp
  end synthesised from the metrics and marked so; events at one time grouped;
- the assist geometry and push settings (metric first, config fallback for directories
  from before SP1), the requested and achieved ramp start, the startup;
- the separated bodies (the spent stage from the staging event, the fairing from its
  drop) on a display-only vacuum coast (display.vacuum_coast) clipped at the run's last
  time, with each body's own apex, impact time, speed and downrange, and the body's own
  measured screen gap from the recorded COAST_STAGING rows (display.coast_gap_m);
- the run's role (run_data.run_source, offload_role), its label (the replay's, except
  that an offload case's recorded run is labelled by kind: solved, imposed or a penalty
  row with its assumed dry mass, ``scene_run_label``), whether it is a yardstick
  (replay.is_yardstick: drawn dashed), its note (for an offload run the replay page's
  own wording, replay.replay_offload_note: the one note source of D-SP2-23, two
  decimals, a paired pad said to fly its own payload capacity, a penalty row's assumed
  dry mass, a fixed case's P* - P_ref reading, a net-of-pad-control quotation, a failed
  verification and the flags), its offload flags one by one (``offload_flags``) and the
  load-time check verdicts (display.tank_checks plus the rebuilt-mass check and the row
  selection's convergence, ``selection_check``) and, for a pushed run, what structural
  mass its record charges for the push (``structure_note``: a captured frame's footer
  carries it);
- at the top level: the directory's identity and git record as metrics.json holds it
  (``hash``; ``dirty`` true, false, or null when git status itself failed and the state
  is unknown, never read as clean; ``error``, git's reason), its label, the vehicle, the
  display geometry (the matching display file, else the generic shape with the reason),
  R_E and omega_p from constants, the camera and tolerance constants, the page's drawing
  constant that the display-only text quotes (PLUME_OF_STACK), the display-only list
  (design 4.9), the caveats (every line replay.caveats gives the same selection, so the
  scene's model caveats are a superset of the replay page's, plus the directory's
  ``offload.caveats`` word for word when an offload run is shown), the exploratory mark
  (replay.EXPLORATORY_CAVEAT for an exploratory directory, else None: the one string the
  page's banner, strip, footer and in-canvas tag use), the provenance footer and the
  caveat line every captured frame carries (``frame_caveat``: the model, each vehicle's
  calibration, where the full list is).

With no run selection the payload shows D-SP2-28's default pair (``default_pair``): the
baseline on the left; on the right the first solved stage-1 offload case, else the first
assisted variant that is not a yardstick, else the baseline alone. Whatever the selection,
the payload's ``default_pair`` (``opening_pair``) is that rule applied to the runs it holds,
filled to two from them in selection order when the rule finds fewer, the panels the page
opens with (step A3b; a ``#runs`` hash overrides it).

A run with an empty time series (a failed search writes none) is left out with a
one-line reason under ``excluded``; a 1-D directory, a sweep directory or sweep point, a
directory with FAILED.txt or one without summary.md is refused with a SceneError (a
run_data.RunDataError). Everything on disk is read through run_data (never results_io,
sim, compare or a reader of this module's own); replay is imported for its caveat list
(through ``replay_data``) and exploratory mark, its offload note and the pieces of it
the label and flags reuse (``penalty_added_kg``, ``penalty_mass_text``,
``verification_reading``, ``pad_control_record``, ``has_flags``), its label and status
helpers (``run_label``, ``is_vertical``, ``is_exploratory``, ``is_yardstick``,
``INSERTED``), ``source_text`` and ``embed_json``.
``scene_json`` encodes the payload as strict ASCII JSON with '<' escaped, for the
``__SCENE_DATA__`` token of the scene template.

The page (SP2 step A3, design section 4.5): ``render_page`` replaces the one token of
the package template templates/scene.html (read through importlib.resources, as
replay.load_template reads its own) with ``scene_json`` of the payload and changes
nothing else; ``write_scene_page`` writes it under run_data's shared output-path rule
(default ./<experiment>_<timestamp>_scene.html, refused inside any results tree, the
folder must exist). The page draws, plays and exposes the state hook
``window.launchsimScene``; it makes no request (its Content-Security-Policy allows the
one inline script by its sha256, inline styles and data: images only). site/build.py
must not insert elements into, or patch the script of, a scene page: frame it from an
outer page with an iframe; the meta CSP blocks same-origin images and links, and the
script-src hash pins the script.

Units: SI and radians in every computation; the payload carries metres, seconds,
kilograms, newtons, watts, pascals and DEGREES for angles (converted here through
units.py). Frames as display.py states them: recorded Earth-fixed altitude and downrange,
the planar inertial frame for the coast, a y-up screen for the drawn angle.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from launchsim import display, replay, run_data
from launchsim.config import OFFLOAD_GROSS_MODES, TrackConfig, VehicleConfig
from launchsim.constants import R_EARTH_M
from launchsim.metrics import TRACK_COLUMNS
from launchsim.metrics_planar import RAMP_START_METRICS, RAMP_START_REQUEST_METRICS
from launchsim.phases.planar import COAST_STAGING, FAIRING_EVENT
from launchsim.phases.trace import ASSIST_KIND
from launchsim.search import OK_STATUS
from launchsim.units import deg_to_rad, from_g, kg_to_t, rad_to_deg, t_to_kg, to_g

if TYPE_CHECKING:
    # The frame type only: every file is read through run_data, never with pandas here.
    import pandas as pd


class SceneError(run_data.RunDataError):
    """A user-facing scene problem (a wrong results directory, run selection or display
    file): the CLI prints it as one error line. A run_data.RunDataError, so the shared
    readers raise it when the scene calls them."""


# ------------------------------------------------------------------ names and constants

SCENE_WORDING = "the scene shows"
"""Subject and verb of the scene's refusals in the shared checks."""
SUMMARY_FILE = "summary.md"
"""The last file results_io writes into a results directory (results_io.SUMMARY_FILE's
name); a directory without it was not written out completely."""
FAILED_MARKER = "FAILED.txt"
"""The marker results_io leaves in a directory whose run raised (results_io.FAILED_MARKER;
spelled here because this module never imports results_io)."""
SWEEP_BASELINE_DIR = "baseline"
"""Folder a sweep directory holds beside its summary.md (no metrics.json at the top)."""
SCENE_CONFIG_FILE = "scene.yaml"
"""The scene settings file under the display directory (display.SceneDisplayConfig)."""
DISPLAY_FILE_SUFFIX = ".yaml"
"""Suffix of every display file under the display directory."""
DEFAULT_DISPLAY_DIR = Path("configs") / "display"
"""Where the display files live, relative to the repository root."""
SCENE_DATA_TOKEN = "__SCENE_DATA__"
"""The scene template's placeholder for the embedded JSON (step A3)."""
SCENE_TEMPLATE = ("templates", "scene.html")
"""The page template, package data of launchsim (importlib.resources path parts)."""
SCENE_MARKER = "Written by launchsim scene"
"""The template's own marker (its style comment); never the replay page's, so the site
build does not frame a scene page as a replay page."""
SCENE_SUFFIXES = (".html", ".htm")
"""Extensions a scene page may be written with (any letter case)."""
SCENE_STEM = "scene"
"""Quantity part of the default file name <experiment>_<timestamp>_scene.html."""

SCENE_COLUMNS = (
    *run_data.PLANAR_BASE_COLUMNS,
    "stage",
    "speed_inertial_mps",
    "gamma_rel_rad",
    "pitch_rad",
    "thrust_vac_N",
    "mach",
    *TRACK_COLUMNS,
)
"""timeseries.csv columns the scene reads (a planar_2d run writes all of them): the
shared base columns, the stage, the inertial speed and flight-path angle, the pitch, the
vacuum thrust, the Mach number and the six track columns."""

TIME_DECIMALS = 6
"""Decimals [s] of every sample and event time in the payload: 1 kg of stage-1 flow is
0.37 ms, so 3 decimals (the replay's) would cost up to 2 kg of the 1 kg mass budget
(survey 09 section 5)."""
ALT_DECIMALS = 1
"""Decimals [m] of the altitude samples (0.1 m against a 1 m floor)."""
DOWNRANGE_DECIMALS = 1
"""Decimals [m] of the downrange samples."""
SPEED_DECIMALS = 2
"""Decimals [m/s] of the speed samples."""
ANGLE_DECIMALS = 3
"""Decimals [deg] of the pitch and drawn-angle samples (0.001 deg against 0.5 deg)."""
PLUME_DECIMALS = 3
"""Decimals [-] of the plume fraction (0.001 against 0.02)."""
TANK_DECIMALS = 1
"""Decimals [kg] of the two tank series: 0.1 kg, so rounding uses at most 0.1 kg of the
1 kg mass budget (the replay's 1 kg rounding would use up to 0.94 kg of it)."""
FILL_DECIMALS = 6
"""Decimals [-] of the fill series (1e-6 of the full load, far inside FILL_START_TOL)."""
TRACK_DECIMALS = 3
"""Decimals of the track series (s_m [m], forces [N], power [W], normal loads [g])."""
Q_DECIMALS = 1
"""Decimals [Pa] of the dynamic-pressure samples."""
MACH_DECIMALS = 4
"""Decimals [-] of the Mach samples."""
G_DECIMALS = 3
"""Decimals [g] of the felt axial acceleration samples (``felt_axial_g``)."""
MASS_DECIMALS = 3
"""Decimals [kg] of the scalar masses in the payload (events, loads, payload)."""
COAST_DECIMALS = 2
"""Decimals [m, m/s] of the separated bodies' path samples."""
GAP_DECIMALS = 3
"""Decimals [m] of a separated body's measured gap from the vehicle's recorded staging
coast (display.coast_gap_m): a millimetre, the figures the display-only text quotes."""
DRIFT_DECIMALS = 16
"""Decimals [-] of the coast's invariant drifts: they are about 1e-13 relative, so 16
decimals keeps them readable as numbers instead of rounding them to 0."""
EMPTY_SERIES_WORDING = "is empty (a failed search writes no trajectory)"
"""How run_data.read_series_frame ends its refusal of a time series with a header and no
rows; the scene reads every series through that function and recognises this one
refusal to leave the run out instead of failing (the empty-series test pins the match)."""
NO_ASSIST_MODEL = "none"
"""assist.model of a pad run."""
RAMP_STARTUP = "ramp"
"""startup kind whose end has no row when the ramp ends in or at the end of the hold (a
pad, or a hot start held before the push): the planner samples the hold in closed form
with no event rules (the engine is lit and the mass burns), so it logs no ramp_end."""
LIFTOFF_EVENT = "liftoff"
"""Event name of a pad's liftoff: logged by the planner only when the hold is extended
past release, synthesised at the release row otherwise (design 4.4)."""
RAMP_END_EVENT = "ramp_end"
"""Event name of the end of the stage-1 startup ramp: logged on the track or in flight,
synthesised for a run whose ramp ends in or at the end of the hold (a pad, or a hot start
held before the push)."""
RELEASE_EVENT = "release"
"""Event name of the release (a pad's liftoff instant when the hold is not extended)."""
STAGE1_BODY = "spent_stage1"
"""Body name of the spent first stage in the payload."""
FAIRING_BODY = "fairing_halves"
"""Body name of the fairing halves in the payload (both halves follow one path)."""
SOURCE_DEFAULT = "default"
"""``assist_settings`` source of a value that is the schema's default (config.py
TrackConfig), neither recorded in the run nor computed from other values."""
SELECTION_CHECK_UNIT = "fraction of the tolerance"
"""Unit of the row-selection check item (``selection_check``): a residual over its row's
tolerance."""
OFFLOAD_NET_MODE_WORDS: Mapping[str, str] = {"stage2": "stage 2", "both": "both stages"}
"""How a run label names the offload mode of a solve quoted net of the pad control (a mode
outside config.OFFLOAD_GROSS_MODES; D-SP1-10): scene_run_label. A mode not listed is
named as recorded."""

PLUME_OF_STACK = 0.35
"""Length of the drawn plume at full vacuum thrust, as a fraction of the drawn stack (a
drawing choice, not a model value): carried in the payload as ``drawing.plume_of_stack``
so the page draws it and DISPLAY_ONLY quotes it from this one number."""

FOOTER_TEXT = (
    "The vehicle's path, thrust and mass are replayed from the recorded time series. The "
    "spent stage, fairing halves, carriage after release and unpowered attitude are "
    "display-only reconstructions and are not model output."
)
"""The provenance footer of every scene page (design 4.4)."""

FRAME_MODEL_TEXT = (
    "Model, not a forecast: a planar 2-D point mass; guidance is sweep-optimized, not "
    "optimal control, and the engines never throttle."
)
"""The model clause of ``frame_caveat`` (replay.model_caveat's limits, in brief)."""

FRAME_MORE_TEXT = "Every caveat: the scene page's 'Read before quoting' list."
"""The last clause of ``frame_caveat``: where the full list is."""

DISPLAY_ONLY: tuple[str, ...] = (
    "Every shape and length: the model has a reference area and a point mass; the "
    "vehicle's shape and the widths and sizes of the shaft, rings, carriage, rails, mount "
    "and clamps come from configs/display, and the other proportions from the page's "
    "drawing constants (the plume's length, "
    f"{PLUME_OF_STACK:.0%} of the drawn stack at full vacuum thrust scaled by the thrust "
    "fraction, and its width; the tank margins; the fairing outline and the payload stub; "
    "the trench width; the clamp spacing; the ring depth), not from the model (the shaft "
    "depth and the rail length are the run's own stroke and braking distance, the shaft "
    "drawn on down to the carriage's bottom at push start). alt_m is drawn at the "
    "rocket's base.",
    "The body attitude: the model has a thrust direction, not a body axis. While the "
    "engines are off outside the hold and the track (an unpowered coast, a fall-back) the "
    "drawn attitude is held at the last screen angle the model defines (thrust on, in the "
    "hold, on the track); the instant steps at the kick and at stage-2 ignition are the "
    "model's and are shown as recorded.",
    "The spent stage and the fairing halves: a drag-free two-body coast from the recorded "
    "separation state, listed under the event list with each body's own computed impact "
    "time, speed and downrange, drag-free (no re-entry drag, so not a landing "
    "prediction); the model has no spent stage. Each spent stage shown carries its own "
    "measured gap from the vehicle's recorded staging-coast rows (staging_coast_gap_m: the "
    "largest screen distance, the coast evaluated at the row times). Measured on 2026-10-05 "
    "over the 55 run folders with a staging coast in the six complete planar directories "
    "under results/: 0.197 and 0.089 m for pad and silo_cold of "
    "results/silo_screening_2d/20260930T175743Z over their 11 s coasts, 0.608 m at most "
    "(silo_cold_s1__pad of results/silo_offload_2d_readme/20261003T112956Z, staging at "
    "62.8 km in denser air; 0.416 m for pad__aero_bound of the screening directory and for "
    "the aref_fairing calibration case, both with the larger reference area), below one "
    "pixel at that camera scale (hundreds of metres per pixel), so the gap drawn then is a "
    "drawing choice; the gap grows with the drag the coast ignores, so a run that stages "
    "lower sits further from it and nothing bounds it for a run not yet flown. Both "
    "fairing halves follow one path; a body still in flight when the run ends is drawn "
    "stopped there.",
    "The plume inside the shaft and the carriage beneath lit engines: the model has a vented "
    "shaft and one impingement fraction that moves only track forces and drive energy; no "
    "back-pressure, heating or exhaust on the carriage.",
    "The carriage after release and where it brakes: the model gives a braking distance "
    "only. A failed ignition falls back along the obstacle-free path: the model has no "
    "contact with the carriage, the mouth or the shaft.",
    "One propellant level per stage: a level drawn as a height takes volume fraction equal "
    "to mass fraction and one tank per stage; tanks read empty at depletion, since no "
    "residual or reserve is modelled.",
    "The pad's liftoff marker (the model logs release; a pad whose hold is not extended "
    "lifts off at release) and the ramp-end marker of a run whose ramp ends in or at the "
    "end of the hold (a pad, or a hot start held before the push: the ignition time plus "
    "the ramp length; the planner samples the hold in closed form, so no row is logged) "
    "are synthesised from the metrics; the marker that replaces the rocket when its body "
    "is under the pixel threshold is a position only.",
)
"""What the scene shows that the model does not support (design 4.9), as data for the
page, the manual and the gallery entry."""


# ------------------------------------------------------------------ directory and display files


def check_scene_run_dir(run_dir: Path) -> dict[str, Any]:
    """metrics.json of a complete planar_2d results directory. Raises SceneError, in this
    order, for a missing directory; one with FAILED_MARKER (the run raised); a sweep
    directory (summary.md over a baseline/ folder and sweep points, no metrics.json at
    the top); what run_data.check_run_dir refuses (no metrics.json, a sweep point or
    single-run folder, a vertical_1d directory); one without SUMMARY_FILE (not written
    out completely)."""
    if not run_dir.is_dir():
        raise SceneError(f"run directory not found: {run_dir}")
    if (run_dir / FAILED_MARKER).is_file():
        raise SceneError(
            f"{run_dir} has {FAILED_MARKER}: the run raised before it was written out; "
            "there is nothing to show"
        )
    if not (run_dir / run_data.METRICS_FILE).is_file() and (run_dir / SWEEP_BASELINE_DIR).is_dir():
        raise SceneError(
            f"{run_dir} is a sweep directory (summary.md over {SWEEP_BASELINE_DIR}/ and sweep "
            f"points, no metrics.json); {SCENE_WORDING} one experiment results directory "
            "(results/<experiment>/<timestamp>)"
        )
    metrics = run_data.check_run_dir(run_dir, error=SceneError, wording=SCENE_WORDING)
    if not (run_dir / SUMMARY_FILE).is_file():
        raise SceneError(
            f"{run_dir} has no {SUMMARY_FILE}: the run was not written out completely; "
            f"{SCENE_WORDING} complete results directories only"
        )
    return metrics


def _one_line(exc: BaseException) -> str:
    """The text of an exception on one line (pydantic's spans several)."""
    return " ".join(str(exc).split())


def load_scene_config(display_dir: Path) -> display.SceneDisplayConfig:
    """The SceneDisplayConfig of <display_dir>/scene.yaml; raises SceneError when the file
    is missing or does not validate (one line)."""
    path = display_dir / SCENE_CONFIG_FILE
    data = run_data.read_yaml(path, error=SceneError)
    if not data:
        raise SceneError(f"no {SCENE_CONFIG_FILE} under {display_dir}")
    try:
        return display.SceneDisplayConfig.model_validate(data)
    except ValueError as exc:  # pydantic's ValidationError is a ValueError
        raise SceneError(f"{path} does not validate: {_one_line(exc)}") from exc


def load_display_configs(display_dir: Path) -> list[display.VehicleDisplayConfig]:
    """Every vehicle display file under ``display_dir`` (``*.yaml`` but scene.yaml), in
    name order; raises SceneError for one that cannot be read or parsed ('cannot read')
    or does not validate (one line each)."""
    out: list[display.VehicleDisplayConfig] = []
    if not display_dir.is_dir():
        return out
    for path in sorted(display_dir.glob(f"*{DISPLAY_FILE_SUFFIX}")):
        if path.name == SCENE_CONFIG_FILE:
            continue
        data = run_data.read_yaml(path, error=SceneError)
        try:
            out.append(display.VehicleDisplayConfig.model_validate(data))
        except ValueError as exc:
            raise SceneError(f"{path} does not validate: {_one_line(exc)}") from exc
    return out


def reference_area_m2(block: Mapping[str, Any]) -> float | None:
    """``aero.reference_area_m2.value`` [m^2] of a raw vehicle block, or None when the
    block has no aero section (a 1-D vehicle)."""
    aero = run_data.as_mapping(block.get("aero"))
    return run_data.finite(run_data.as_mapping(aero.get("reference_area_m2")).get("value"))


def display_geometry_for(
    vehicle_name: str,
    block: Mapping[str, Any],
    configs: Sequence[display.VehicleDisplayConfig],
    scene_cfg: display.SceneDisplayConfig,
    display_dir: Path,
) -> display.DisplayGeometry:
    """The DisplayGeometry of the vehicle named ``vehicle_name``: the first display file
    whose ``applies_to`` lists it, else the generic shape (display.generic_geometry) from
    the raw vehicle ``block``'s reference area, with the reason. Raises SceneError when
    neither a display file nor a reference area exists."""
    for cfg in configs:
        if vehicle_name in cfg.applies_to:
            return cfg.geometry()
    area = reference_area_m2(block)
    reason = (
        f"no display file under {display_dir.as_posix()} lists vehicle {vehicle_name!r}; "
        "generic shape from its reference area"
    )
    if area is None:
        raise SceneError(
            f"vehicle {vehicle_name!r} has no display file under {display_dir} and no "
            "aero.reference_area_m2 to size a generic shape from"
        )
    return display.generic_geometry(area, scene_cfg.generic, reason)


# ------------------------------------------------------------------ small helpers


def _round(value: float | None, decimals: int) -> float | None:
    """``value`` rounded (None for None, NaN or infinity; a negative zero made 0.0)."""
    return run_data.finite(value, decimals)


def _series(values: np.ndarray, decimals: int) -> list[float | None]:
    """A float array as a list of rounded floats, None where a value is not finite."""
    return [_round(float(v), decimals) for v in values]


def _metric(m: Mapping[str, Any], key: str) -> float | None:
    """A finite metric value, or None."""
    return run_data.finite(m.get(key))


def site_omega_p(run_cfg: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    """(omega_p [rad/s], the site as data) of a run block's ``site``: latitude and
    azimuth [deg] converted here, ``include_rotation`` as written (display.planar_omega_p).
    Raises SceneError when the block has no finite ``site.latitude_deg`` or
    ``site.azimuth_deg``, or no boolean ``site.include_rotation`` (config.py's
    PlanarSiteConfig makes all three explicit in every planar_2d run block, so a block
    without one is not one this module knows): the scene never defaults any part of a
    site, since omega_p places the inertial frame of every separated body."""
    site = run_data.as_mapping(run_cfg.get("site"))
    lat = run_data.finite(site.get("latitude_deg"))
    az = run_data.finite(site.get("azimuth_deg"))
    if lat is None or az is None:
        raise SceneError(
            "run block has no finite site.latitude_deg / site.azimuth_deg; the scene needs "
            "the site to place the inertial frame of the separated bodies"
        )
    rotation = site.get("include_rotation")
    if not isinstance(rotation, bool):
        raise SceneError(
            "run block has no boolean site.include_rotation; the scene needs it for "
            "omega_p and never defaults it"
        )
    omega = display.planar_omega_p(float(deg_to_rad(lat)), float(deg_to_rad(az)), rotation)
    return omega, {"latitude_deg": lat, "azimuth_deg": az, "include_rotation": rotation}


def run_rows(frame: pd.DataFrame) -> display.RunRows:
    """The display.RunRows of a time-series frame as written (run_data.read_series_frame):
    every numeric column cast to float (silo_failed's constant columns read back as
    integers), the text columns as tuples."""

    def col(name: str) -> np.ndarray:
        return frame[name].to_numpy(dtype=float)

    return display.RunRows(
        t_s=col("t_s"),
        t_rel_s=col("t_rel_release_s"),
        phase=tuple(frame["phase"].astype(str)),
        stage=tuple(frame["stage"].astype(str)),
        alt_m=col("alt_m"),
        downrange_m=col("downrange_m"),
        speed_rel_mps=col("speed_rel_mps"),
        pitch_rad=col("pitch_rad"),
        m_kg=col("m_kg"),
        thrust_vac_N=col("thrust_vac_N"),
    )


# ------------------------------------------------------------------ assist geometry and push


def assist_settings(assist: Mapping[str, Any], m: Mapping[str, Any]) -> dict[str, Any] | None:
    """The assist geometry and push settings of one run as data, or None for a pad
    (assist.model none or absent): each value with where it came from under
    ``sources``: 'metric' (the run's metrics record), 'config' (the resolved run block),
    'derived' (computed here from other values) or 'default' (the schema's default in
    config.py, for a track block written without ``angle_deg`` or ``exit_altitude_m``:
    neither recorded nor computed). Metric first, the resolved config as the fallback for
    directories from before SP1 (which lack stroke_m, net_accel_* and the ramp-start
    keys), derived values last: a = v^2 / (2 L), v = sqrt(2 a L), the
    braking distance v^2 / (2 a_brake), the facility length as stroke plus braking, the
    track start altitude as exit altitude less stroke x sin(track angle). SI, with the
    acceleration also in g (units.to_g) and the track angle in degrees as the config
    writes it."""
    model = str(assist.get("model", NO_ASSIST_MODEL))
    if model == NO_ASSIST_MODEL:
        return None
    sources: dict[str, str] = {}

    def pick(key: str, metric_key: str, config_value: float | None) -> float | None:
        value = _metric(m, metric_key)
        if value is not None:
            sources[key] = "metric"
            return value
        if config_value is not None:
            sources[key] = "config"
        return config_value

    track = run_data.as_mapping(assist.get("track"))
    stroke = pick("stroke_m", "stroke_m", run_data.finite(assist.get("stroke_m")))
    accel_g_cfg = run_data.finite(assist.get("net_accel_g"))
    accel = pick(
        "net_accel_mps2",
        "net_accel_mps2",
        None if accel_g_cfg is None else float(from_g(accel_g_cfg)),
    )
    exit_speed = pick(
        "exit_speed_mps", "exit_speed_mps", run_data.finite(assist.get("exit_speed_mps"))
    )
    if accel is None and exit_speed is not None and stroke:
        accel = exit_speed * exit_speed / (2.0 * stroke)
        sources["net_accel_mps2"] = "derived"
    if exit_speed is None and accel is not None and stroke is not None:
        exit_speed = math.sqrt(max(0.0, 2.0 * accel * stroke))
        sources["exit_speed_mps"] = "derived"
    angle_deg = run_data.finite(track.get("angle_deg"))
    if angle_deg is None:
        angle_deg = TrackConfig().angle_deg  # the schema's default: a vertical silo
        sources["track_angle_deg"] = SOURCE_DEFAULT
    else:
        sources["track_angle_deg"] = "config"
    exit_alt = run_data.finite(track.get("exit_altitude_m"))
    if exit_alt is None:
        exit_alt = TrackConfig().exit_altitude_m  # the schema's default
        sources["exit_altitude_m"] = SOURCE_DEFAULT
    else:
        sources["exit_altitude_m"] = "config"
    brake_g = run_data.finite(assist.get("brake_decel_g"))
    if brake_g is not None:
        sources["brake_decel_g"] = "config"
    braking = pick("braking_distance_m", "braking_distance_m", None)
    if braking is None and exit_speed is not None and brake_g:
        braking = exit_speed * exit_speed / (2.0 * float(from_g(brake_g)))
        sources["braking_distance_m"] = "derived"
    facility = pick("facility_length_m", "facility_length_m", None)
    if facility is None and stroke is not None and braking is not None:
        facility = stroke + braking
        sources["facility_length_m"] = "derived"
    carriage_t = run_data.finite(assist.get("carriage_mass_t"))
    carriage = pick(
        "carriage_mass_kg",
        "carriage_mass_kg",
        None if carriage_t is None else float(t_to_kg(carriage_t)),
    )
    start_alt = pick("track_start_altitude_m", "track_start_altitude_m", None)
    if start_alt is None and stroke is not None:
        start_alt = exit_alt - stroke * math.sin(float(deg_to_rad(angle_deg)))
        sources["track_start_altitude_m"] = "derived"
    push_time = pick("push_time_s", "push_time_s", None)
    if push_time is None and accel and exit_speed is not None:
        push_time = exit_speed / accel
        sources["push_time_s"] = "derived"
    for key in ("drive_efficiency", "exhaust_impingement_fraction"):
        if run_data.finite(assist.get(key)) is not None:
            sources[key] = "config"
    shaft = assist.get("shaft")
    if shaft is not None:
        sources["shaft"] = "config"
    return {
        "model": model,
        "stroke_m": stroke,
        "net_accel_mps2": accel,
        "net_accel_g": None if accel is None else float(to_g(accel)),
        "exit_speed_mps": exit_speed,
        "exit_altitude_m": exit_alt,
        "track_angle_deg": angle_deg,
        "track_start_altitude_m": start_alt,
        "braking_distance_m": braking,
        "brake_decel_g": brake_g,
        "facility_length_m": facility,
        "carriage_mass_kg": carriage,
        "push_time_s": push_time,
        "drive_efficiency": run_data.finite(assist.get("drive_efficiency")),
        "exhaust_impingement_fraction": run_data.finite(assist.get("exhaust_impingement_fraction")),
        "shaft": None if shaft is None else str(shaft),
        "sources": sources,
    }


def ramp_start(
    m: Mapping[str, Any], events: Sequence[run_data.EventRow], stage1: str
) -> dict[str, Any]:
    """The requested and achieved ramp start of stage 1 as data: ``requested`` from the
    RAMP_START_REQUEST_METRICS when the run states a non-time trigger (None otherwise);
    ``achieved`` from the RAMP_START_METRICS, else (a directory from before SP1) from the
    stage-1 ``ignition`` event row (time after release [s], altitude [m], Earth-relative
    speed [m/s], phase), else None (a failed ignition). ``source`` names which."""
    requested = {k: m.get(k) for k in RAMP_START_REQUEST_METRICS if m.get(k) is not None}
    achieved: dict[str, Any] | None = None
    source = None
    if any(m.get(k) is not None for k in RAMP_START_METRICS):
        achieved = {k: m.get(k) for k in RAMP_START_METRICS}
        source = "metrics"
    else:
        lit = [e for e in events if e.name == run_data.IGNITION_EVENT and e.stage == stage1]
        if lit:
            e = lit[0]
            achieved = {
                "ramp_start_t_rel_release_s": e.t_rel_s,
                "ramp_start_alt_m": run_data.finite(e.alt_m),
                "ramp_start_depth_m": None,
                "ramp_start_height_m": None,
                "ramp_start_speed_mps": run_data.finite(e.speed_rel_mps),
                "ramp_start_phase": e.phase,
            }
            source = "stage-1 ignition event row"
    return {"requested": requested or None, "achieved": achieved, "source": source}


# ------------------------------------------------------------------ events


def event_label(event: run_data.EventRow, name: str | None = None) -> str:
    """'<name> (<stage>)' of an event row (``name`` in place of the row's own for a
    synthesised event), or the name alone when the stage is unknown."""
    label_name = event.name if name is None else name
    return label_name if event.stage is None else f"{label_name} ({event.stage})"


def _event_payload(
    match: display.EventMatch,
    rows: display.RunRows,
    sample_of_row: Mapping[int, int],
    *,
    synthetic: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """One event as data: its time from the matched row (TIME_DECIMALS), its state, the
    mass before and after, what was dropped, whether the planner recorded it, the index of
    its last row's sample in the selected series (None when unmatched) and, for a
    synthesised event, the sentence that says how it was made."""
    e = match.event
    label_name = e.name if name is None else name
    t = rows.t_rel_s[match.index] if match.index is not None else e.t_rel_s
    last = match.last_index
    return {
        "name": label_name,
        "stage": e.stage,
        "phase": e.phase,
        "label": event_label(e, name),
        "t": _round(float(t), TIME_DECIMALS),
        "row_matched": match.index is not None,
        "sample": None if last is None else sample_of_row.get(last),
        "alt_m": _round(e.alt_m, ALT_DECIMALS),
        "downrange_m": _round(e.downrange_m, DOWNRANGE_DECIMALS),
        "speed_rel_mps": _round(e.speed_rel_mps, SPEED_DECIMALS),
        "m_before_kg": _round(e.m_before_kg, MASS_DECIMALS),
        "m_after_kg": _round(e.m_after_kg, MASS_DECIMALS),
        "dropped": e.dropped,
        "recorded": e.recorded and synthetic is None,
        "synthetic": synthetic is not None,
        "synthetic_from": synthetic,
    }


def synthetic_events(
    matches: Sequence[display.EventMatch],
    rows: display.RunRows,
    m: Mapping[str, Any],
    assisted: bool,
) -> list[tuple[display.EventMatch, str, str]]:
    """The events the planner logs no row for, each as (match, name, how): ``liftoff`` at
    the release row of a pad without a liftoff row (the planner extends the hold, and
    logs liftoff, only when the thrust at release is below the weight, whatever the ramp
    has reached by then; an ``assisted`` run leaves the carriage at release and gets no
    liftoff), and ``ramp_end`` at t_ign + t_startup for any run whose stage 1 has a ramp
    startup and no ramp_end row (matched to the row at that time within
    display.EVENT_TIME_TOL_S, else unmatched): a pad, or a hot start whose ramp ends in
    or at the end of the hold before the push (silo_hot_full: lit 2 s before the push in
    HOLD, the ramp ending at push start). The planner samples the hold in closed form
    with no event rules, so it logs no row there. A ramp lit on the track or in flight
    has its row and gets nothing."""
    names = {mt.event.name for mt in matches}
    out: list[tuple[display.EventMatch, str, str]] = []
    release = next((mt for mt in matches if mt.event.name == RELEASE_EVENT), None)
    if not assisted and release is not None and LIFTOFF_EVENT not in names:
        out.append(
            (
                release,
                LIFTOFF_EVENT,
                "synthesised at the release row: the planner logs liftoff only when the hold "
                "is extended past release (metrics hold_extension_s), so a pad whose thrust "
                "already exceeds its weight at release lifts off at release",
            )
        )
    t_ign = _metric(m, "t_ign_rel_release_s_stage1")
    t_ramp = _metric(m, "t_startup_s_stage1")
    if (
        RAMP_END_EVENT not in names
        and m.get("startup_kind_stage1") == RAMP_STARTUP
        and t_ign is not None
        and t_ramp is not None
        and release is not None
    ):
        t_end = t_ign + t_ramp
        t_abs = t_end + (release.event.t_s - release.event.t_rel_s)
        row = run_data.EventRow(
            t_s=t_abs,
            t_rel_s=t_end,
            name=RAMP_END_EVENT,
            phase=None,
            stage=release.event.stage,
            alt_m=math.nan,
            downrange_m=math.nan,
            speed_rel_mps=math.nan,
            speed_inertial_mps=math.nan,
            gamma_rel_rad=math.nan,
            m_kg=math.nan,
            recorded=False,
        )
        (match,) = display.match_events(rows.t_s, [row])
        if match.index is not None:
            k = match.last_index
            row = run_data.EventRow(
                t_s=t_abs,
                t_rel_s=float(rows.t_rel_s[k]),  # type: ignore[index]
                name=RAMP_END_EVENT,
                phase=rows.phase[k],  # type: ignore[index]
                stage=rows.stage[k],  # type: ignore[index]
                alt_m=float(rows.alt_m[k]),  # type: ignore[index]
                downrange_m=float(rows.downrange_m[k]),  # type: ignore[index]
                speed_rel_mps=float(rows.speed_rel_mps[k]),  # type: ignore[index]
                speed_inertial_mps=math.nan,
                gamma_rel_rad=math.nan,
                m_kg=float(rows.m_kg[k]),  # type: ignore[index]
                m_before_kg=float(rows.m_kg[k]),  # type: ignore[index]
                m_after_kg=float(rows.m_kg[k]),  # type: ignore[index]
                recorded=False,
            )
            match = display.EventMatch(row, match.index, match.count)
        out.append(
            (
                match,
                RAMP_END_EVENT,
                "synthesised from the metrics t_ign_rel_release_s_stage1 + t_startup_s_stage1: "
                "the ramp ends in or at the end of the hold (a pad, or a hot start held "
                "before the push), which the planner samples in closed form with no event "
                "rules (the engine is lit and the mass burns), so no ramp_end row is logged",
            )
        )
    return out


# ------------------------------------------------------------------ separated bodies


def body_payload(
    name: str,
    match: display.EventMatch,
    rows: display.RunRows,
    held_angle_rad: np.ndarray,
    omega_p: float,
    t_last_s: float,
) -> dict[str, Any] | None:
    """One separated body as data: its vacuum coast (display.vacuum_coast) from the
    separation state rebuilt at its event row (display.separation_state), the path
    clipped at the run's last time ``t_last_s`` [s after release] with each sample's time
    on the release clock, the body's own apex and impact (whether inside the run or
    not), the mass that left (m_before - m_after), the held screen angle [deg] at
    separation (the vehicle's drawn angle on the row before the map), the invariant
    drifts, and the body's own measured gap from the vehicle's recorded path
    (``staging_coast_gap_m``, display.coast_gap_m: the largest screen distance between
    the coast, evaluated exactly at the row times, and the recorded COAST_STAGING rows
    at or after the separation, over ``staging_coast_rows`` rows; None when no such row
    follows, as for a fairing dropped under thrust). None when the event row lacks a
    state or is unmatched."""
    e = match.event
    state_ok = all(
        math.isfinite(v) for v in (e.alt_m, e.downrange_m, e.speed_rel_mps, e.gamma_rel_rad)
    )
    if match.index is None or not state_ok:
        return None
    t0 = float(rows.t_rel_s[match.index])
    state = display.separation_state(
        e.alt_m, e.downrange_m, e.speed_rel_mps, e.gamma_rel_rad, t0, omega_p
    )
    clip = max(0.0, t_last_s - t0)
    coast = display.vacuum_coast(state, e.downrange_m, omega_p, clip_s=clip)
    impact = coast.impact_t_s
    coast_rows = [
        i for i, p in enumerate(rows.phase) if p == COAST_STAGING and rows.t_rel_s[i] >= t0
    ]
    gap = (
        display.coast_gap_m(
            state,
            e.downrange_m,
            omega_p,
            rows.t_rel_s[coast_rows] - t0,
            rows.alt_m[coast_rows],
            rows.downrange_m[coast_rows],
        )
        if coast_rows
        else math.nan
    )
    dropped_kg = (
        None
        if e.m_before_kg is None or e.m_after_kg is None
        else _round(e.m_before_kg - e.m_after_kg, MASS_DECIMALS)
    )
    return {
        "name": name,
        "from_event": e.name,
        "dropped": e.dropped,
        "mass_kg": dropped_kg,
        "t_separation": _round(t0, TIME_DECIMALS),
        "screen_angle_deg": _round(float(rad_to_deg(held_angle_rad[match.index])), ANGLE_DECIMALS),
        "speed_inertial_mps": _round(state.speed_inertial_mps, SPEED_DECIMALS),
        "path": {
            "t": _series(coast.t_s + t0, TIME_DECIMALS),
            "alt_m": _series(coast.alt_m, COAST_DECIMALS),
            "downrange_m": _series(coast.downrange_m, COAST_DECIMALS),
            "speed_mps": _series(coast.speed_rel_mps, COAST_DECIMALS),
        },
        "clipped_at_run_end": impact is None or impact > clip,
        "apex": {
            "t": _round(coast.apex_t_s + t0, TIME_DECIMALS),
            "alt_m": _round(coast.apex_alt_m, COAST_DECIMALS),
            "within_run": coast.apex_t_s <= clip,
        },
        "impact": None
        if impact is None
        else {
            "t": _round(impact + t0, TIME_DECIMALS),
            "speed_mps": _round(coast.impact_speed_rel_mps, COAST_DECIMALS),
            "downrange_m": _round(coast.impact_downrange_m, COAST_DECIMALS),
            "within_run": impact <= clip,
        },
        "energy_drift_rel": _round(coast.energy_drift_rel, DRIFT_DECIMALS),
        "h_drift_rel": _round(coast.h_drift_rel, DRIFT_DECIMALS),
        "staging_coast_gap_m": _round(gap, GAP_DECIMALS),
        "staging_coast_rows": len(coast_rows),
        "note": "display-only drag-free coast; not model output",
    }


# ------------------------------------------------------------------ one run


def _fill_reference(
    source: Mapping[str, Any], config: Mapping[str, Any], block: Mapping[str, Any]
) -> tuple[Mapping[str, Any], str]:
    """(the fill-reference vehicle block, its description): the experiment's top-level
    vehicle block for runs, bound runs and offload runs; the entry's own block for a case
    (design 4.4, review 01 finding 2); the run's own block when the file has no top-level
    block."""
    if source["role"] == run_data.ROLE_CASE:
        return block, "the case's own vehicle block (full tanks at its own loads)"
    top = run_data.as_mapping(config.get("vehicle"))
    if top:
        return top, "the experiment's vehicle block (full loads)"
    return block, "the run's own vehicle block (no experiment-level block in the file)"


def _offload_fractions(
    source: Mapping[str, Any], metrics: Mapping[str, Any], name: str
) -> tuple[float | None, float | None]:
    """The per-stage offload fractions of an offload case's recorded run or paired pad
    (its case record's ``stage1_fraction`` and ``stage2_fraction``), (None, None) for
    every other run (the blocks' loads then give the expected start fill)."""
    if source["role"] != run_data.ROLE_OFFLOAD:
        return (None, None)
    role = run_data.offload_role(run_data.as_mapping(metrics.get("offload")), name)
    if role is None or role[0] == run_data.OFFLOAD_PAD_CONTROL:
        return (None, None)
    record = role[1]
    return (
        run_data.finite(record.get("stage1_fraction")),
        run_data.finite(record.get("stage2_fraction")),
    )


def scene_run_label(
    name: str, role: str, baseline: bool, kind: str | None, record: Mapping[str, Any] | None
) -> str:
    """The run's label on the scene page: replay.run_label's, except for an offload case's
    recorded run (``kind`` run_data.OFFLOAD_CASE with its case ``record``), labelled by
    what its offload is instead of '(offload)' alone: '(offload penalty row: assumed +8.1 t
    of stage-1 dry mass)' for a penalty row (replay.penalty_added_kg and
    penalty_mass_text), '(offload, solved)' for a solve that ended ok, '(offload, solve
    status <status>)' for one that did not, '(offload, imposed)' for a fixed case. A solve
    quoted net of the pad control (a mode outside OFFLOAD_GROSS_MODES) adds what it is
    ('(offload, solved, stage 2: a property of the vehicle model)', criterion 7), and a
    solve with a stage-2 pre-offload adds it ('(offload, solved, plus 2.00 t imposed on
    stage 2)'), so the selector and the header never show such a run as the stage-1
    headline. A scene-side label: the replay page's labels are unchanged."""
    label = replay.run_label(name, role, baseline, kind)
    if baseline or kind != run_data.OFFLOAD_CASE or record is None:
        return label
    added = replay.penalty_added_kg(record)
    if added is not None:
        what = f"offload penalty row: assumed {replay.penalty_mass_text(added)}"
    elif record.get("kind") == run_data.OFFLOAD_SOLVED_KIND:
        status = record.get("status")
        what = "offload, solved" if status == OK_STATUS else f"offload, solve status {status}"
        mode = record.get("mode")
        if mode is not None and mode not in OFFLOAD_GROSS_MODES:
            words = OFFLOAD_NET_MODE_WORDS.get(str(mode), str(mode))
            what += f", {words}: a property of the vehicle model"
        imposed_kg = run_data.finite(record.get("stage2_preoffload_kg"))
        if imposed_kg is not None and imposed_kg > 0.0:
            what += f", plus {float(kg_to_t(imposed_kg)):.2f} t imposed on stage 2"
    else:
        what = "offload, imposed"
    return f"{name} ({what})"


def offload_flags(offload: Mapping[str, Any], name: str) -> list[str]:
    """The flags of run ``name`` of metrics.json's ``offload`` block, one item each, for
    the page's flag line: for an offload case's recorded run a failed verification first
    ('verification failed (+15.36 kg against 2.6 kg): the gross removal is a flagged lower
    bound', replay.verification_reading), then, for a stage-2 or both-stage solve quoted
    net of a pad control that carries flags, that the net figure subtracts a flagged pad
    control, then the case record's own ``flags``; for a pad control its record's
    ``flags``; [] for a paired pad (the case's verdicts belong to the case's run) and for
    every run outside the block. The note (replay.replay_offload_note) says the same in
    one sentence; this list names each flag."""
    role = run_data.offload_role(offload, name)
    if role is None or role[0] == run_data.OFFLOAD_PAIRED_PAD:
        return []
    kind, record = role
    out: list[str] = []
    if kind == run_data.OFFLOAD_CASE:
        verification = run_data.as_mapping(record.get("verification"))
        if verification.get("passed") is False:
            size, reading, _ = replay.verification_reading(verification)
            out.append(f"verification failed{size}: {reading}")
        mode = record.get("mode")
        if (
            record.get("kind") == run_data.OFFLOAD_SOLVED_KIND
            and mode not in (None, *OFFLOAD_GROSS_MODES)
            and run_data.finite(record.get("quoted_offload_kg")) is not None
        ):
            control = replay.pad_control_record(offload, mode)
            if control is not None and replay.has_flags(control):
                n = len(control["flags"])
                out.append(
                    f"the net figure subtracts a flagged pad control ({n} flag"
                    f"{'' if n == 1 else 's'}) and is uncertain both ways"
                )
    if replay.has_flags(record):
        out.extend(str(flag) for flag in record["flags"])
    return out


def selection_check(selection: display.RowSelection) -> display.CheckResult:
    """The row selection's convergence as a load-time check item (exit criterion 5):
    passed when every CSV row of every interpolated field lies within
    display.SELECTION_HALF of its tolerance under linear interpolation of the selected
    rows (``selection.converged``), failed when display.SELECTION_MAX_PASSES insertion
    passes did not get there, so the run still loads and is flagged in its CheckReport.
    ``worst`` is the largest residual over its row's tolerance across the fields (a
    fraction of the tolerance), the detail naming that field and its time [s after
    release]."""
    field, worst = max(selection.worst.items(), key=lambda item: item[1].frac)
    return display.CheckResult(
        name="every CSV row within half tolerance under interpolation (criterion 5)",
        passed=bool(selection.converged),
        worst=float(worst.frac),
        tolerance=display.SELECTION_HALF,
        unit=SELECTION_CHECK_UNIT,
        detail=(
            f"worst {field}: {worst.abs:.4g} ({worst.frac:.3f} of its tolerance) at t = "
            f"{worst.t_s:.6f} s after release; {selection.passes} insertion pass(es), "
            f"{len(selection.indices)} rows selected"
            + ("" if selection.converged else "; the selection did not converge")
        ),
    )


def run_payload(
    run_dir: Path,
    name: str,
    frame: pd.DataFrame,
    metrics: Mapping[str, Any],
    config: Mapping[str, Any],
    baseline: str,
) -> dict[str, Any]:
    """The payload of one run (the module docstring lists its fields), built from its
    time-series ``frame`` (run_data.read_series_frame with SCENE_COLUMNS, read once by
    the caller, which leaves out a run whose series is empty), its events.csv, its
    metrics record and its run and vehicle blocks. Raises SceneError for a run
    metrics.json does not describe or an incomplete vehicle block."""
    source = run_data.run_source(metrics, config, name, error=SceneError, wording=SCENE_WORDING)
    m = source["metrics"]
    run_cfg = source["config"]
    rows = run_rows(frame)
    block = run_data.run_vehicle_block(config, name)
    masses = run_data.vehicle_masses(block, error=SceneError)
    vehicle = VehicleConfig.model_validate(dict(block)).to_vehicle()
    ref_block, ref_text = _fill_reference(source, config, block)
    reference = run_data.vehicle_masses(ref_block, error=SceneError)
    payload_kg = _metric(m, "payload_kg")
    payload_source = "the run's metrics record (payload_kg)"
    if payload_kg is None:
        payload_kg = masses.payload_kg
        payload_source = "the vehicle block's payload_mass_t (the metric is null)"

    offset = run_data.release_offset_s(frame)
    recorded = run_data.read_events(run_dir / name / run_data.EVENTS_FILE, offset, error=SceneError)
    events = run_data.with_drop_masses(recorded, masses, m.get("fairing_drop"))
    fairing_form = run_data.fairing_case(events, None, masses)
    levels = display.tank_levels(rows, masses, payload_kg, events, reference, fairing_form)
    checks = display.tank_checks(
        rows,
        levels,
        masses,
        events,
        liftoff_mass_kg=_metric(m, "liftoff_mass_kg"),
        recorded_m_res_kg=_metric(m, "recorded_m_res_kg"),
        offload_fractions=_offload_fractions(source, metrics, name),
    )
    full_thrust = np.array([s.thrust_vac_total_N for s in vehicle.stages], dtype=float)
    plume = rows.thrust_vac_N / full_thrust[levels.stage_index]
    defined = display.attitude_defined(rows.phase, levels.thrust_on)
    held = display.held_screen_angle_rad(rows.pitch_rad, rows.downrange_m, defined)

    matches = display.match_events(rows.t_s, events)
    event_rows = [
        i for mt in matches if mt.index is not None for i in range(mt.index, mt.index + mt.count)
    ]
    q_all = frame["q_pa"].to_numpy(dtype=float)
    if np.isfinite(q_all).any():
        # the time series' peak q row is kept, so the drawn path passes through the recorded
        # peak row beside the page's max-Q mark (the run's metrics max-Q, ``max_q``)
        event_rows.append(int(np.nanargmax(q_all)))
    max_q_pa = _metric(m, "max_q_pa")
    max_q_t = _metric(m, "max_q_time_s")
    prop1, prop2 = levels.prop_kg
    fields = [
        display.SelectionField("alt_m", rows.alt_m, display.ALT_TOL_MIN_M, display.ALT_TOL_REL),
        display.SelectionField(
            "downrange_m", rows.downrange_m, display.DOWNRANGE_TOL_MIN_M, display.DOWNRANGE_TOL_REL
        ),
        display.SelectionField("pitch_rad", rows.pitch_rad, display.PITCH_TOL_RAD),
        display.SelectionField("screen_angle_rad", held, display.PITCH_TOL_RAD),
        display.SelectionField("plume", plume, display.PLUME_TOL),
        display.SelectionField("prop1_kg", prop1, display.MASS_TOL_KG),
        display.SelectionField("prop2_kg", prop2, display.MASS_TOL_KG),
    ]
    selection = display.select_rows(rows.t_rel_s, fields, event_rows)
    sel = selection.indices
    residual = display.rebuilt_mass_residual_kg(
        rows, levels, masses, sel, time_decimals=TIME_DECIMALS, tank_decimals=TANK_DECIMALS
    )
    worst_i = int(np.argmax(residual))
    mass_item = display.CheckResult(
        name=(
            f"rebuilt stack mass within {display.MASS_TOL_KG:g} kg at every CSV row "
            "(interpolation and rounding)"
        ),
        passed=bool(residual[worst_i] <= display.MASS_TOL_KG),
        worst=float(residual[worst_i]),
        tolerance=display.MASS_TOL_KG,
        unit="kg",
        detail=(
            f"largest |rebuilt - m_kg| {residual[worst_i]:.4f} kg at t = "
            f"{rows.t_rel_s[worst_i]:.6f} s after release over {len(rows)} rows, "
            f"{len(sel)} selected"
        ),
    )
    checks = display.CheckReport((*checks.items, mass_item, selection_check(selection)))
    sample_of_row = {int(i): k for k, i in enumerate(sel)}

    assist_cfg = run_data.as_mapping(run_cfg.get("assist"))
    assist = assist_settings(assist_cfg, m)
    assisted = assist is not None
    omega_p, site = site_omega_p(run_cfg)
    status = str(m.get("status", "unknown"))
    inserted = status == replay.INSERTED
    t_last = float(rows.t_rel_s[-1])

    event_items = [_event_payload(mt, rows, sample_of_row) for mt in matches]
    for mt, ev_name, how in synthetic_events(matches, rows, m, assisted):
        event_items.append(_event_payload(mt, rows, sample_of_row, synthetic=how, name=ev_name))
    event_items.sort(key=lambda ev: ev["t"] if ev["t"] is not None else math.inf)
    groups: dict[float | None, list[str]] = {}
    for ev in event_items:
        groups.setdefault(ev["t"], []).append(ev["label"])
    event_groups = [{"t": t, "labels": labels} for t, labels in groups.items()]

    bodies: list[dict[str, Any]] = []
    for mt in matches:
        if mt.event.dropped is None:
            continue
        body_name = FAIRING_BODY if mt.event.dropped == FAIRING_EVENT else STAGE1_BODY
        body = body_payload(body_name, mt, rows, held, omega_p, t_last)
        if body is not None:
            bodies.append(body)

    in_push = np.array([p == ASSIST_KIND for p in rows.phase], dtype=bool)
    track: dict[str, list[float | None]] = {}
    for column in TRACK_COLUMNS:
        values = frame[column].to_numpy(dtype=float)[sel]
        values = np.where(in_push[sel], values, np.nan)
        track[column] = _series(values, TRACK_DECIMALS)

    kind = None
    case_record = None
    note = str(source["note"])
    offload_note = None
    flags: list[str] = []
    if source["role"] == run_data.ROLE_OFFLOAD:
        # The replay page's note, not run_data.offload_note (the animation's one-decimal
        # legend): one note source for both pages (D-SP2-23, design 4.3).
        offload = run_data.as_mapping(metrics.get("offload"))
        role = run_data.offload_role(offload, name)
        kind = None if role is None else role[0]
        case_record = None if role is None else role[1]
        offload_note = replay.replay_offload_note(offload, name, baseline)
        note = offload_note
        flags = offload_flags(offload, name)

    return {
        "key": name,
        "label": scene_run_label(name, source["role"], name == baseline, kind, case_record),
        "role": source["role"],
        "offload_kind": kind,
        "note": note,
        "offload_note": offload_note,
        "flags": flags,
        "structure_note": structure_note(
            case_record if kind == run_data.OFFLOAD_CASE else None, assisted
        ),
        "yardstick": replay.is_yardstick(dict(m)),
        "compared_to": source["compared_to"],
        "baseline": name == baseline,
        "status": status,
        "inserted": inserted,
        "assisted": assisted,
        "vertical": assisted and replay.is_vertical(assist_cfg),
        "vehicle": str(block.get("name", "unknown vehicle")),
        "payload_kg": _round(payload_kg, MASS_DECIMALS),
        "payload_source": payload_source,
        "site": site,
        "omega_p_rads": omega_p,
        "t": _series(rows.t_rel_s[sel], TIME_DECIMALS),
        "alt_m": _series(rows.alt_m[sel], ALT_DECIMALS),
        "downrange_m": _series(rows.downrange_m[sel], DOWNRANGE_DECIMALS),
        "speed_mps": _series(rows.speed_rel_mps[sel], SPEED_DECIMALS),
        "pitch_deg": _series(np.asarray(rad_to_deg(rows.pitch_rad[sel])), ANGLE_DECIMALS),
        "screen_angle_deg": _series(np.asarray(rad_to_deg(held[sel])), ANGLE_DECIMALS),
        "attitude_defined": [bool(v) for v in defined[sel]],
        "plume": _series(plume[sel], PLUME_DECIMALS),
        "stage": [int(v) for v in levels.stage_index[sel]],
        "phase": [rows.phase[int(i)] for i in sel],
        "fairing_on": [bool(v) for v in levels.fairing_on[sel]],
        "thrust_on": [bool(v) for v in levels.thrust_on[sel]],
        "q_pa": _series(frame["q_pa"].to_numpy(dtype=float)[sel], Q_DECIMALS),
        "max_q": (
            None
            if max_q_pa is None or max_q_t is None
            else {"t": _round(max_q_t, TIME_DECIMALS), "q_pa": _round(max_q_pa, Q_DECIMALS)}
        ),
        "mach": _series(frame["mach"].to_numpy(dtype=float)[sel], MACH_DECIMALS),
        "felt_g": _series(frame["felt_axial_g"].to_numpy(dtype=float)[sel], G_DECIMALS),
        "track": track,
        "prop1_kg": _series(prop1[sel], TANK_DECIMALS),
        "prop2_kg": _series(prop2[sel], TANK_DECIMALS),
        "fill1": _series(levels.fill[0][sel], FILL_DECIMALS),
        "fill2": _series(levels.fill[1][sel], FILL_DECIMALS),
        "tanks": {
            "stage_names": list(masses.stage_names),
            "load_kg": [_round(v, MASS_DECIMALS) for v in levels.load_kg],
            "full_kg": [_round(v, MASS_DECIMALS) for v in levels.full_kg],
            "start_fill": [_round(float(f[0]), FILL_DECIMALS) for f in levels.fill],
            "offload_fraction": [_round(v, FILL_DECIMALS) for v in levels.offload_fraction],
            "not_loaded_kg": [_round(v, MASS_DECIMALS) for v in levels.not_loaded_kg],
            "fill_reference": ref_text,
            "fairing_form": levels.fairing_form,
        },
        "masses": {
            "stage_dry_kg": [_round(v, MASS_DECIMALS) for v in masses.stage_dry_kg],
            "stage_propellant_kg": [_round(v, MASS_DECIMALS) for v in masses.stage_propellant_kg],
            "fairing_kg": _round(masses.fairing_kg, MASS_DECIMALS),
            "payload_kg": _round(payload_kg, MASS_DECIMALS),
            "liftoff_kg": _round(float(rows.m_kg[0]), MASS_DECIMALS),
        },
        "thrust_full_N": [float(v) for v in full_thrust],
        "startup": {
            "kind_stage1": m.get("startup_kind_stage1"),
            "t_startup_s_stage1": _metric(m, "t_startup_s_stage1"),
            "t_ign_rel_release_s_stage1": _metric(m, "t_ign_rel_release_s_stage1"),
            "t_ign_rel_release_s_stage2": _metric(m, "t_ign_rel_release_s_stage2"),
        },
        "assist": assist,
        "ramp_start": ramp_start(m, events, masses.stage_names[0]),
        "events": event_items,
        "event_groups": event_groups,
        "bodies": bodies,
        "end": {
            "t": _round(t_last, TIME_DECIMALS),
            "status": status,
            "label": "In orbit" if inserted else f"Ended: {status}",
        },
        "checks": checks.as_dict(),
        "selection": selection.as_dict(),
        "rows": len(rows),
    }


# ------------------------------------------------------------------ the payload


def git_record(git: Mapping[str, Any]) -> dict[str, Any]:
    """The git record of metrics.json as recorded (results_io.git_info): ``hash`` (the
    commit, 'unborn' or 'no-git'; 'unknown' when absent), ``dirty`` (True or False as
    written, None when it is not a boolean: git status failed or timed out, so the state
    is unknown and must never read as clean) and ``error`` (git's reason, or None)."""
    dirty = git.get("dirty")
    error = git.get("error")
    return {
        "hash": str(git.get("hash", "unknown")),
        "dirty": dirty if isinstance(dirty, bool) else None,
        "error": None if error is None else str(error),
    }


def _solved_stage1_run(metrics: Mapping[str, Any], available: Sequence[str]) -> str | None:
    """The run of the first solved stage-1 offload case in ``offload.cases`` order: kind
    run_data.OFFLOAD_SOLVED_KIND, a mode in config.OFFLOAD_GROSS_MODES (stage 1, the
    headline), status ok, and a run folder in ``available``; None when there is none."""
    cases = run_data.as_mapping(metrics.get("offload")).get("cases")
    for item in cases if isinstance(cases, list) else []:
        record = run_data.as_mapping(item)
        run = record.get("run")
        if (
            record.get("kind") == run_data.OFFLOAD_SOLVED_KIND
            and record.get("mode") in OFFLOAD_GROSS_MODES
            and record.get("status") == OK_STATUS
            and run in available
        ):
            return str(run)
    return None


def _assisted_variant(
    metrics: Mapping[str, Any], config: Mapping[str, Any], available: Sequence[str]
) -> str | None:
    """The first variant of metrics.json's ``runs`` (summary order, the baseline left
    out) with a run folder in ``available`` whose run block is assisted (assist.model
    not none) and which is not a yardstick (replay.is_yardstick: an instant step startup
    no engine reaches); None when there is none."""
    baseline = metrics.get("baseline")
    entries = run_data.as_mapping(config.get("runs"))
    for name, record in run_data.as_mapping(metrics.get("runs")).items():
        if name == baseline or name not in available:
            continue
        run_cfg, _ = run_data.entry_config(entries.get(name))
        model = run_data.as_mapping(run_cfg.get("assist")).get("model", NO_ASSIST_MODEL)
        if model != NO_ASSIST_MODEL and not replay.is_yardstick(run_data.as_mapping(record)):
            return str(name)
    return None


def default_pair(
    metrics: Mapping[str, Any], config: Mapping[str, Any], available: Sequence[str]
) -> list[str]:
    """D-SP2-28's default selection of a results directory (the scene's, not the
    replay's): the baseline on the left; on the right the run of the first solved
    stage-1 offload case, else the first assisted variant that is not a yardstick, else
    nothing (the baseline alone: one full-width panel). Only runs in ``available`` (the
    run folders with a time series, run_data.run_names) are chosen; a directory whose
    baseline has no folder starts from the right-hand run, and one with neither from its
    first available run. Pure: metrics.json and resolved_config.yaml as read."""
    baseline = metrics.get("baseline")
    left = [str(baseline)] if baseline in available else []
    right = _solved_stage1_run(metrics, available) or _assisted_variant(metrics, config, available)
    names = left + ([right] if right is not None and right not in left else [])
    return names or list(available[:1])


def frame_caveat(vehicles: Sequence[str]) -> str:
    """The caveat line every captured frame of the scene carries under its provenance
    footer (a video frame travels without the page's caveat list; D-SP2-36): the model in
    brief (FRAME_MODEL_TEXT), each vehicle's calibration as the replay page words it
    (replay.calibration_caveat: its gap, inside or outside the gate, the findings note)
    and where the full list is (FRAME_MORE_TEXT). ``vehicles``: the vehicle names of the
    runs the payload holds, each once in order. Pure."""
    calibration = [replay.calibration_caveat(v) for v in dict.fromkeys(vehicles)]
    return " ".join([FRAME_MODEL_TEXT, *calibration, FRAME_MORE_TEXT])


def structure_note(case_record: Mapping[str, Any] | None, assisted: bool) -> str | None:
    """What structural mass a run's record charges for the push, for a captured frame's
    footer: None for a run with no push (``assisted`` false); for a penalty row (an
    offload case whose ``offload.cases`` record, ``case_record`` as run_data.offload_role
    finds it for the run, charges an assumed stage-1 dry mass: replay.penalty_added_kg)
    that assumed mass, 'an assumption, not a sized structure'; else (``case_record`` None,
    or a case without a penalty) that none is charged (replay.structure_caveat's wording,
    per run). Pure. Fix round 1 of A6v: the record is the one ``run_payload`` found, not
    looked up again from a run_source without ``offload_kind`` (which named every penalty
    row as uncharged)."""
    if not assisted:
        return None
    added = None if case_record is None else replay.penalty_added_kg(case_record)
    if added is None:
        return "no structural mass is charged for the push"
    return (
        f"an assumed {replay.penalty_mass_text(added)} is charged for the push: an "
        "assumption, not a sized structure"
    )


def opening_pair(
    metrics: Mapping[str, Any], config: Mapping[str, Any], kept: Sequence[str]
) -> list[str]:
    """The two panels a scene page opens with (its ``default_pair``), from the runs the
    payload holds (``kept``, in selection order): D-SP2-28's rule (``default_pair``) on
    them, filled to two from ``kept`` in order when the rule finds fewer (a selection
    without the baseline, or with no assisted variant), so an explicit selection of two
    or more runs always opens two panels; one run when ``kept`` holds one. Pure."""
    pair = default_pair(metrics, config, kept)
    return pair + [n for n in kept if n not in pair][: max(0, 2 - len(pair))]


def scene_payload(
    run_dir: Path, runs: Sequence[str] | None, *, display_dir: Path
) -> dict[str, Any]:
    """The scene payload of the selected ``runs`` (None: D-SP2-28's default pair,
    ``default_pair``) of the planar results directory ``run_dir`` with the display files
    of ``display_dir`` (the module docstring lists every field). Raises SceneError for a
    refused directory (``check_scene_run_dir``), a bad selection (run_data.select_runs), a
    display file that does not validate, or a selection in which no run has a time
    series; a run with an empty time series is left out under ``excluded`` with its
    reason."""
    metrics = check_scene_run_dir(run_dir)
    config = run_data.read_yaml(run_dir / run_data.CONFIG_FILE, error=SceneError)
    if runs is None:
        _, available = run_data.run_names(run_dir)
        runs = default_pair(metrics, config, available)
    names = run_data.select_runs(run_dir, runs, what="scene", error=SceneError)
    scene_cfg = load_scene_config(display_dir)
    configs = load_display_configs(display_dir)
    baseline = str(metrics.get("baseline"))
    base_cfg, _ = run_data.entry_config(run_data.as_mapping(config.get("runs")).get(baseline))
    top_block = run_data.as_mapping(config.get("vehicle"))
    vehicle_name = str(top_block.get("name", "unknown vehicle"))

    excluded: list[dict[str, str]] = []
    frames: dict[str, pd.DataFrame] = {}
    for name in names:
        try:
            frames[name] = run_data.read_series_frame(
                run_dir, name, SCENE_COLUMNS, error=SceneError
            )
        except SceneError as exc:
            if not str(exc).endswith(EMPTY_SERIES_WORDING):
                raise
            excluded.append(
                {
                    "run": name,
                    "reason": f"{name} has an empty time series (a failed search or guidance "
                    "writes no trajectory); left out of the scene",
                }
            )
    if not frames:
        raise SceneError(
            f"none of the selected runs ({', '.join(names)}) has a time series to show in {run_dir}"
        )

    records = [
        run_payload(run_dir, name, frame, metrics, config, baseline)
        for name, frame in frames.items()
    ]
    kept = list(frames)
    geometry = display_geometry_for(vehicle_name, top_block, configs, scene_cfg, display_dir)
    for record in records:
        if record["vehicle"] != vehicle_name:
            own = run_data.run_vehicle_block(config, record["key"])
            record["geometry"] = display_geometry_for(
                record["vehicle"], own, configs, scene_cfg, display_dir
            ).as_dict()
        else:
            record["geometry"] = None

    caveats = list(replay.replay_data(run_dir, kept)["meta"]["caveats"])
    offload_caveats: list[str] = []
    if any(r["role"] == run_data.ROLE_OFFLOAD for r in records):
        raw = run_data.as_mapping(metrics.get("offload")).get("caveats")
        offload_caveats = [str(c) for c in raw] if isinstance(raw, list) else []
    omega_p, site = site_omega_p(base_cfg)
    git = run_data.as_mapping(metrics.get("git"))
    experiment, timestamp = run_data.run_identity(run_dir)
    label = metrics.get("label")
    return {
        "experiment": experiment,
        "timestamp": timestamp,
        "source": replay.source_text(run_dir),
        "git": git_record(git),
        "label": None if label is None else str(label),
        "exploratory": replay.is_exploratory(metrics),
        "exploratory_caveat": (
            replay.EXPLORATORY_CAVEAT if replay.is_exploratory(metrics) else None
        ),
        "model": str(metrics.get("model")),
        "baseline": baseline,
        "default_pair": opening_pair(metrics, config, kept),
        "vehicle": vehicle_name,
        "display": geometry.as_dict(),
        "constants": {"R_E_m": R_EARTH_M, "omega_p_rads": omega_p, "site": site},
        "camera": {
            **scene_cfg.camera.values(),
            **scene_cfg.values(),
            "provenance": {**scene_cfg.camera.provenance(), **scene_cfg.provenance()},
        },
        "tolerances": {
            "alt_rel": display.ALT_TOL_REL,
            "alt_min_m": display.ALT_TOL_MIN_M,
            "downrange_rel": display.DOWNRANGE_TOL_REL,
            "downrange_min_m": display.DOWNRANGE_TOL_MIN_M,
            "pitch_deg": float(rad_to_deg(display.PITCH_TOL_RAD)),
            "plume": display.PLUME_TOL,
            "mass_kg": display.MASS_TOL_KG,
            "event_time_s": display.EVENT_TIME_TOL_S,
            "fill_start": display.FILL_START_TOL,
            "tank_step_kg": display.TANK_STEP_TOL_KG,
            "selection_half": display.SELECTION_HALF,
            "time_decimals": TIME_DECIMALS,
            "tank_decimals": TANK_DECIMALS,
        },
        "drawing": {"plume_of_stack": PLUME_OF_STACK},
        "display_only": list(DISPLAY_ONLY),
        "caveats": caveats + offload_caveats,
        "offload_caveats": offload_caveats,
        "footer": FOOTER_TEXT,
        "frame_caveat": frame_caveat([r["vehicle"] for r in records]),
        "excluded": excluded,
        "runs": records,
    }


def scene_json(payload: Mapping[str, Any]) -> str:
    """The payload as compact ASCII JSON safe inside a <script> element: no NaN or
    Infinity (ValueError otherwise) and every '<' escaped (replay.embed_json, the one
    encoder of both pages)."""
    return replay.embed_json(dict(payload))


# ------------------------------------------------------------------ the page


def load_template() -> str:
    """The scene page template (package data launchsim/templates/scene.html), as text,
    read through importlib.resources as replay.load_template reads its own. The bytes are
    decoded here (UTF-8; the template is ASCII) because this module reads no results file
    itself: tests/test_scene.py keeps every file reader of a results directory in
    run_data, and a package resource is not one."""
    path = resources.files("launchsim").joinpath(*SCENE_TEMPLATE)
    return path.read_bytes().decode("utf-8")


def render_page(payload: Mapping[str, Any]) -> str:
    """The standalone scene page: the template with its one SCENE_DATA_TOKEN replaced by
    ``scene_json(payload)`` and nothing else changed (no other server-side string enters
    the HTML). Raises RuntimeError when the template does not hold the token exactly
    once, ValueError for a payload with NaN or infinity."""
    template = load_template()
    if template.count(SCENE_DATA_TOKEN) != 1:
        raise RuntimeError(f"scene template must hold {SCENE_DATA_TOKEN} exactly once")
    return template.replace(SCENE_DATA_TOKEN, scene_json(payload))


def default_scene_path(run_dir: Path, cwd: Path) -> Path:
    """<cwd>/<experiment>_<timestamp>_scene.html; when ``cwd`` is inside a results tree
    (the run's own or any folder named results) the file goes next to the outermost such
    tree instead (run_data.default_output_path, the shared rule of D-SP2-14)."""
    experiment, timestamp = run_data.run_identity(run_dir)
    name = run_data.plot_stem(f"{experiment}_{timestamp}", SCENE_STEM) + SCENE_SUFFIXES[0]
    return run_data.default_output_path(run_dir, cwd, name)


def check_scene_out(out_path: Path, run_dir: Path) -> None:
    """Raise SceneError for an output that is not .html (or .htm), lies inside a results
    tree (run_data.protected_tree: the run's own or any folder named results, in any
    letter case), or whose folder does not exist, in that order (run_data.check_output)."""
    run_data.check_output(
        out_path,
        run_dir,
        suffixes=SCENE_SUFFIXES,
        suffix_text=SCENE_SUFFIXES[0],
        what="page",
        error=SceneError,
    )


def write_scene_page(
    run_dir: Path,
    runs: Sequence[str] | None,
    out: Path | None,
    *,
    cwd: Path,
    display_dir: Path,
) -> Path:
    """Write the scene page of the selected ``runs`` (None: D-SP2-28's default pair) of
    the planar results directory ``run_dir`` to ``out`` (None: ``default_scene_path``
    under ``cwd``) as UTF-8 text with LF line ends, and return the path written.
    Validates the directory, the runs and the display files (``scene_payload``), then the
    output path (``check_scene_out``), before anything is written; raises SceneError."""
    payload = scene_payload(run_dir, runs, display_dir=display_dir)
    out_path = default_scene_path(run_dir, cwd) if out is None else out
    check_scene_out(out_path, run_dir)
    page = render_page(payload)
    out_path.write_text(page, encoding="utf-8", newline="\n")
    return out_path


__all__ = [
    "DEFAULT_DISPLAY_DIR",
    "DISPLAY_ONLY",
    "DRIFT_DECIMALS",
    "EMPTY_SERIES_WORDING",
    "FAILED_MARKER",
    "FOOTER_TEXT",
    "FRAME_MODEL_TEXT",
    "FRAME_MORE_TEXT",
    "G_DECIMALS",
    "PLUME_OF_STACK",
    "SCENE_COLUMNS",
    "SCENE_CONFIG_FILE",
    "SCENE_DATA_TOKEN",
    "SCENE_MARKER",
    "SCENE_STEM",
    "SCENE_SUFFIXES",
    "SCENE_TEMPLATE",
    "SCENE_WORDING",
    "SELECTION_CHECK_UNIT",
    "SOURCE_DEFAULT",
    "SUMMARY_FILE",
    "TANK_DECIMALS",
    "TIME_DECIMALS",
    "SceneError",
    "assist_settings",
    "body_payload",
    "check_scene_out",
    "check_scene_run_dir",
    "default_pair",
    "default_scene_path",
    "display_geometry_for",
    "event_label",
    "frame_caveat",
    "git_record",
    "load_display_configs",
    "load_scene_config",
    "load_template",
    "offload_flags",
    "opening_pair",
    "ramp_start",
    "render_page",
    "run_payload",
    "run_rows",
    "scene_json",
    "scene_payload",
    "scene_run_label",
    "selection_check",
    "site_omega_p",
    "structure_note",
    "synthetic_events",
    "write_scene_page",
]
