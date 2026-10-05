"""Plot writers of a run (moved from sim.py; I/O: writes PNG files).

``write_plots`` draws one PNG per panel of ``plot_panels`` (PLOT_PANELS, plus
PLOT_TRACK_PANELS for a run with a track phase) against the time since release, from
the run's time series (SI columns; the unit is in each axis label). A planar_2d run
gets ``write_planar_plots`` instead: PLANAR_PLOT_PANELS (altitude against downrange,
|v_rel| and |v_in|, gamma_rel and pitch in degrees, q and Mach, mass and thrust, felt
g, the cumulative losses), plus the track panels. Figures are built from
matplotlib.figure.Figure and saved through the Agg canvas that PNG output selects, so
no pyplot state and no global backend switch is involved. ``sim`` re-exports those
writers (not the animation).

``write_ascent_animation`` (the ``launchsim animate`` command) replays planar_2d runs
of one results directory as an .mp4 (ffmpeg) or .gif (Pillow): it only reads the
directory (metrics.json, resolved_config.yaml, <run>/timeseries.csv, <run>/events.csv)
and never writes inside results/. A run of an experiment's offload block (metrics.json
``offload.runs``: an offload case, a paired pad or a pad control) is labelled from that
record, as the replay page reads it (``animation_record``, ``offload_tag``).

The reading it shares with the replay page lives in run_data.py (SP2 step A1): the file
readers, the directory check, run selection, the series and event readers, the offload
roles, the calibration records, ``plot_stem`` and the output-path rule. The names this
module had for them stay importable here, as the same objects or as thin wrappers that
raise AnimationError with animate's wording; ``calibration_caveat`` and the ffmpeg test
stay here.
"""

from __future__ import annotations

import math
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.animation import FFMpegWriter, PillowWriter
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import blended_transform_factory
from numpy.typing import NDArray

from launchsim import run_data
from launchsim.config import PLANAR_2D
from launchsim.offload import NO_OFFLOAD_STATUS
from launchsim.phases import ASSIST_KIND, HOLD_KIND
from launchsim.phases.planar import (
    COAST,
    COAST_PRE_IGN,
    COAST_STAGING,
    GRAVITY_TURN,
    KICK,
    LTG_BURN,
    VERTICAL_RISE,
)
from launchsim.units import kg_to_t, m_to_km, pa_to_kpa, rad_to_deg, to_percent

if TYPE_CHECKING:
    from launchsim.sim import Result


PLOT_SERIES_COLOR = "#2a78d6"
PLOT_GRID_COLOR = "#d8d8d4"
PLOT_LINE_WIDTH = 2.0
PLOT_GRID_LINE_WIDTH = 0.6
PLOT_FIGSIZE_IN = (6.4, 3.6)
PLOT_DPI = 120


# The plotted set per run (write_plots): plots/<run>_<quantity>.png, each a panel
# (quantity, columns, y labels) against the time since release; the track panels only
# when the run has ASSIST rows. One y label: every column shares the axis (same unit);
# one label per column: each column gets its own y axis (a twin axis for the second),
# so quantities with different units (mass and thrust) are never drawn on one scale.
type PlotPanel = tuple[str, tuple[str, ...], tuple[str, ...]]
PLOT_ABSCISSA = "t_rel_release_s"
PLOT_ABSCISSA_LABEL = "t - t_release [s]"
PLOT_PANELS: tuple[PlotPanel, ...] = (
    ("altitude", ("z_m",), ("z [m]",)),
    ("speed", ("v_mps",), ("v [m/s]",)),
    ("mass_thrust", ("m_kg", "thrust_N"), ("m [kg]", "T [N]")),
    ("felt_g", ("accel_felt_g",), ("felt axial acceleration [g0]",)),
)
PLOT_TRACK_PANELS: tuple[PlotPanel, ...] = (
    ("track_forces", ("drive_force_N", "interface_force_N"), ("F_drive, F_int [N]",)),
    ("drive_power", ("drive_power_W",), ("P_drive [W]",)),
)
PLOT_SERIES_COLORS: tuple[str, ...] = (PLOT_SERIES_COLOR, "#d6742a")


PLOT_STEM_UNSAFE = run_data.PLOT_STEM_UNSAFE
plot_stem = run_data.plot_stem
"""run_data.plot_stem and its pattern (the same objects; ``sim`` re-exports them from
here): the file stem ``<prefix>_<quantity>`` with every run of characters outside
``[A-Za-z0-9_.-]`` replaced by ``_``."""


def _plot_text(text: str) -> str:
    """Escape ``$`` so matplotlib does not read the label as mathtext."""
    return text.replace("$", "\\$")


def plot_panels(result: Result) -> list[PlotPanel]:
    """The (quantity, columns, y labels) panels ``write_plots`` draws for a run:
    PLOT_PANELS always, plus PLOT_TRACK_PANELS when the run has ASSIST rows (the track
    columns are NaN everywhere else)."""
    frame = result.timeseries
    panels = list(PLOT_PANELS)
    if "phase" in frame.columns and bool((frame["phase"] == ASSIST_KIND).any()):
        panels += PLOT_TRACK_PANELS
    return panels


def write_plots(result: Result, plots_dir: Path, prefix: str) -> list[Path]:
    """Write plots/<plot_stem(prefix, quantity)>.png for every panel of ``plot_panels``
    (altitude, speed, mass_thrust, felt_g and, on a track, track_forces and
    drive_power), each against the time since release (PLOT_ABSCISSA). A panel with
    two columns and one y label draws both on that axis, labelled (same unit); with
    one y label per column each column gets its own axis, the second a twin y axis on
    the right (mass and thrust: different units, never one scale). Nothing is written
    when the time series is empty or lacks the abscissa; a panel whose columns are all
    missing is skipped.

    Figures are built from matplotlib.figure.Figure and saved through the Agg canvas
    that PNG output selects, so no pyplot state and no global backend switch is needed:
    importing this module leaves a notebook's inline backend alone.
    """
    frame = result.timeseries
    if frame.empty or PLOT_ABSCISSA not in frame.columns:
        return []
    if result.model == PLANAR_2D:
        return write_planar_plots(result, plots_dir, prefix)
    plots_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for quantity, columns, ylabels in plot_panels(result):
        present = [c for c in columns if c in frame.columns]
        if not present:
            continue
        twin = len(ylabels) > 1
        fig = Figure(figsize=PLOT_FIGSIZE_IN, dpi=PLOT_DPI)
        ax = fig.subplots()
        axes = [ax]
        handles: list[Line2D] = []
        for i, (col, color) in enumerate(zip(present, PLOT_SERIES_COLORS, strict=False)):
            target = ax if i == 0 or not twin else ax.twinx()
            if target is not ax:
                axes.append(target)
            (handle,) = target.plot(
                frame[PLOT_ABSCISSA],
                frame[col],
                color=color,
                linewidth=PLOT_LINE_WIDTH,
                label=_plot_text(col),
            )
            handles.append(handle)
            if twin:
                target.set_ylabel(_plot_text(ylabels[columns.index(col)]), color=color)
                target.tick_params(axis="y", colors=color)
        if len(present) > 1:
            ax.legend(handles=handles, frameon=False)
        ax.set_xlabel(PLOT_ABSCISSA_LABEL)
        if not twin:
            ax.set_ylabel(_plot_text(ylabels[0]))
        ax.set_title(_plot_text(f"{prefix}: {quantity}"))
        ax.grid(True, color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for extra in axes[1:]:  # a twin axis keeps its own right spine for its scale
            extra.spines["top"].set_visible(False)
        fig.tight_layout()
        path = plots_dir / f"{plot_stem(prefix, quantity)}.png"
        fig.savefig(path, format="png")
        written.append(path)
    return written


# ---------------------------------------------------------------------- planar plots

PLANAR_SERIES_COLORS: tuple[str, ...] = (PLOT_SERIES_COLOR, "#d6742a", "#3a9e5c", "#8a4fbf")
"""Line colours of a planar panel (up to four series on one axis)."""
DEG_COLUMNS = frozenset({"gamma_rel_rad", "pitch_rad"})
"""Planar columns stored in radians and drawn in degrees (plot labels are one of the two
places degrees appear)."""
KM_COLUMNS = frozenset({"alt_m", "downrange_m"})
"""Planar columns stored in metres and drawn in kilometres."""
type PlanarPanel = tuple[str, str, str, tuple[tuple[str, ...], ...], tuple[str, ...]]
PLANAR_PLOT_PANELS: tuple[PlanarPanel, ...] = (
    ("trajectory", "downrange_m", "downrange [km]", (("alt_m",),), ("altitude [km]",)),
    (
        "speed",
        PLOT_ABSCISSA,
        PLOT_ABSCISSA_LABEL,
        (("speed_rel_mps", "speed_inertial_mps"),),
        ("|v_rel|, |v_in| [m/s]",),
    ),
    (
        "angles",
        PLOT_ABSCISSA,
        PLOT_ABSCISSA_LABEL,
        (("gamma_rel_rad", "pitch_rad"),),
        ("gamma_rel (unwrapped), pitch [deg]",),
    ),
    ("q_mach", PLOT_ABSCISSA, PLOT_ABSCISSA_LABEL, (("q_pa",), ("mach",)), ("q [Pa]", "Mach")),
    (
        "mass_thrust",
        PLOT_ABSCISSA,
        PLOT_ABSCISSA_LABEL,
        (("m_kg",), ("thrust_N",)),
        ("m [kg]", "T [N]"),
    ),
    (
        "felt_g",
        PLOT_ABSCISSA,
        PLOT_ABSCISSA_LABEL,
        (("felt_axial_g", "felt_lateral_g"),),
        ("felt axial, lateral [g0]",),
    ),
    (
        "losses",
        PLOT_ABSCISSA,
        PLOT_ABSCISSA_LABEL,
        (("J_grav_mps", "J_drag_mps", "J_steer_mps", "J_bp_mps"),),
        ("cumulative loss [m/s]",),
    ),
)
"""The planar panels: (quantity, x column, x label, column groups, y labels); each
group shares one y axis (same unit), a second group gets a twin axis on the right."""


def _plot_values(frame: Any, column: str) -> Any:
    """A time-series column in its plot unit: degrees for DEG_COLUMNS, km for
    KM_COLUMNS, SI otherwise."""
    values = frame[column].to_numpy(dtype=float)
    if column in DEG_COLUMNS:
        return rad_to_deg(values)
    if column in KM_COLUMNS:
        return m_to_km(values)
    return values


def planar_plot_panels(result: Result) -> list[PlanarPanel]:
    """The panels ``write_planar_plots`` draws: PLANAR_PLOT_PANELS, plus the track
    panels (as (quantity, abscissa, label, groups, labels)) when the run has ASSIST
    rows."""
    panels = list(PLANAR_PLOT_PANELS)
    frame = result.timeseries
    if "phase" in frame.columns and bool((frame["phase"] == ASSIST_KIND).any()):
        panels += [
            (quantity, PLOT_ABSCISSA, PLOT_ABSCISSA_LABEL, (columns,), (labels[0],))
            for quantity, columns, labels in PLOT_TRACK_PANELS
        ]
    return panels


def write_planar_plots(result: Result, plots_dir: Path, prefix: str) -> list[Path]:
    """Write plots/<plot_stem(prefix, quantity)>.png for every planar panel
    (``planar_plot_panels``): altitude [km] against downrange [km], and the other
    quantities against the time since release; angles in degrees, lengths in km, SI
    otherwise (the unit in each label). Each column group shares an axis; a second
    group gets a twin y axis. Nothing is written for an empty time series (a failed
    search)."""
    frame = result.timeseries
    if frame.empty:
        return []
    plots_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for quantity, x_col, x_label, groups, ylabels in planar_plot_panels(result):
        fig = Figure(figsize=PLOT_FIGSIZE_IN, dpi=PLOT_DPI)
        ax = fig.subplots()
        x = _plot_values(frame, x_col)
        handles: list[Line2D] = []
        colors = iter(PLANAR_SERIES_COLORS)
        for g, (group, ylabel) in enumerate(zip(groups, ylabels, strict=True)):
            target = ax if g == 0 else ax.twinx()
            for col in group:
                (handle,) = target.plot(
                    x,
                    _plot_values(frame, col),
                    color=next(colors),
                    linewidth=PLOT_LINE_WIDTH,
                    label=_plot_text(col),
                )
                handles.append(handle)
            target.set_ylabel(_plot_text(ylabel))
            target.spines["top"].set_visible(False)
        if len(handles) > 1:
            ax.legend(handles=handles, frameon=False)
        ax.set_xlabel(_plot_text(x_label))
        ax.set_title(_plot_text(f"{prefix}: {quantity}"))
        ax.grid(True, color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
        if len(groups) == 1:
            ax.spines["right"].set_visible(False)
        fig.tight_layout()
        path = plots_dir / f"{plot_stem(prefix, quantity)}.png"
        fig.savefig(path, format="png")
        written.append(path)
    return written


# ------------------------------------------------------------------- ascent animation
#
# ``write_ascent_animation`` replays planar_2d runs of one results directory as a video:
# it reads <run>/timeseries.csv, <run>/events.csv, metrics.json and resolved_config.yaml
# (never writing into results/) and draws one frame per video frame through
# matplotlib.animation (FFMpegWriter for .mp4, PillowWriter for .gif).

type FloatArray = NDArray[np.float64]
"""A 1-D float series of an animated run."""


class AnimationError(run_data.RunDataError):
    """A user-facing animation problem (a wrong run directory, run name, output path or
    frame setting, ffmpeg missing for .mp4 or failing while encoding): the CLI prints
    it as one error line. A run_data.RunDataError (so still a ValueError): the shared
    readers raise it when the animation calls them."""


ANIMATION_FORMATS = (".mp4", ".gif")
"""Output extensions ``write_ascent_animation`` accepts; the extension picks the writer."""
ANIMATION_DEFAULT_FPS = 30
ANIMATION_DEFAULT_SECONDS = 20.0
ANIMATION_DEFAULT_WIDTH_PX = 1280
ANIMATION_MIN_WIDTH_PX = 320
ANIMATION_WORDING = "animate draws"
"""Subject and verb of animate's refusal in the shared directory check
(run_data.check_run_dir)."""
ANIMATION_MAX_RUNS = run_data.MAX_RUNS
"""Most runs one animation shows (run_data.MAX_RUNS)."""
ANIMATION_DEFAULT_VARIANTS = run_data.DEFAULT_VARIANTS
"""The default selection: the baseline plus up to this many variants, in summary order
(run_data.DEFAULT_VARIANTS)."""
ANIMATION_FIG_WIDTH_IN = 10.0
"""Design width of the frame [in]: the dpi is width_px / this, so the picture (and every
font relative to it) is the same at any pixel width. 10 in keeps 8 pt text about 7 px
tall at 640 px wide."""
ANIMATION_ASPECT = 9.0 / 16.0
FRAME_PX_EPS = 1e-3
"""Pixels added to the figure size so the float product inches x dpi never truncates to
one pixel less (matplotlib and Agg both truncate)."""
POINTS_PER_INCH = 72.0
"""Typographic points per inch (matplotlib's point), to turn a label step [pt] into
pixels at the frame dpi."""
GIF_DELAY_STEP_MS = 10
"""A GIF stores each frame delay in whole steps of this many milliseconds: Pillow floors
PillowWriter's int(1000 / fps) ms to a step, so a GIF plays at 1000 / (that delay)
frames per second, which is not always the requested fps (12 fps plays at 12.5)."""
GIF_MIN_DELAY_MS = 20
"""Shortest GIF frame delay [ms] that browsers honour (they slow shorter ones to 100 ms)."""
MP4_CRF = 20
"""H.264 constant rate factor of the .mp4 (lower is higher quality; 20 is visually clean
for these line drawings at under 1 MB per 20 s)."""
RESULTS_TREE_NAME = run_data.RESULTS_TREE_NAME
"""Name of the generated results tree; an animation is never written inside one
(run_data.RESULTS_TREE_NAME)."""

TIMELINE_LAUNCH_END_S = 3.0
"""Time after release [s] that ends the launch segment of the timeline: the push, the
pad's hold-down and liftoff play at about real time up to here."""
TIMELINE_KNEE_S = 30.0
"""Time after release [s] that ends the close-up segment; also the right edge of the
launch close-up panel. After it the timeline fast-forwards to the end of the flight."""
TIMELINE_LAUNCH_FRACTION = 0.28
"""Share of the video spent from the start to TIMELINE_LAUNCH_END_S: for the 2.6 s silo
push that is 5.6 s of flight in 5.6 s of a 20 s video, about real time."""
TIMELINE_CLOSEUP_FRACTION = 0.20
"""Share of the video spent from TIMELINE_LAUNCH_END_S to TIMELINE_KNEE_S."""
TIMELINE_HOLD_FRACTION = 0.06
"""Share of the video that holds the final state at the end."""
SLOW_MOTION_BELOW = 0.95
"""A playback speed below this many times real time is labelled slow motion."""

ANIMATION_RUN_STYLES: tuple[tuple[str, str, str], ...] = (
    ("#0072B2", "-", "o"),
    ("#E69F00", "--", "s"),
    ("#009E73", ":", "^"),
    ("#CC79A7", "-.", "D"),
)
"""(colour, line style, marker) per run: Okabe-Ito colours (colour-blind safe), paired
with distinct dashes and marker shapes so the runs also separate in grayscale."""
ANIMATION_RUN_TEXT_COLORS = ("#0072B2", "#9E6A00", "#007A5A", "#A8578A")
"""Text colour per run (its single-run event labels and hold-down note): the run colour,
darkened where needed for at least 4.5:1 contrast on white."""
MARKER_GLYPHS: dict[str, str] = {"o": "\u25cf", "s": "\u25a0", "^": "\u25b2", "D": "\u25c6"}
"""Text glyph of each run marker (DejaVu Sans geometric shapes): event labels name their
run by the marker's shape, which survives grayscale and colour-blind viewing."""
ANIMATION_TEXT_COLOR = "#222222"
ANIMATION_MUTED_COLOR = "#666666"
ANIMATION_FOOTNOTE_COLOR = "#3a3a3a"
ANIMATION_GROUND_COLOR = "#e4e1da"
ANIMATION_HOLD_COLOR = "#cfd8e3"
ANIMATION_LINE_WIDTH = 1.8
ANIMATION_MARKER_SIZE = 7.0
ANIMATION_EVENT_MARKER_SIZE = 4.5
FONT_TITLE_PT = 13.0
FONT_LABEL_PT = 9.0
FONT_TICK_PT = 8.0
FONT_SMALL_PT = 8.0
FONT_EVENT_PT = 7.5
FONT_FOOTNOTE_PT = 9.0
"""The caveat footnote is larger than the other small text: at 640 px it is about 8 px
tall, the size of the tick labels at 1280 px."""
FONT_READOUT_PT = 8.5
ANIMATION_GRID: dict[str, float] = {
    "left": 0.06,
    "right": 0.985,
    "top": 0.855,
    "bottom": 0.2,
    "wspace": 0.15,
}
"""Figure fractions of the panel grid: the title block sits above ``top``, the axis
labels and the three-line footnote below ``bottom``."""
ANIMATION_MAIN_WIDTH_RATIO = 1.6
"""Width of the trajectory panel relative to the right-hand column."""
ANIMATION_CLOSEUP_HEIGHT_RATIO = 1.35
"""Height of the launch close-up relative to the block of three small time panels (2)."""
MAIN_HEADROOM = 1.35
MAIN_HEADROOM_PER_RUN = 0.22
MAIN_HEADROOM_PER_SECOND_LINE = 0.25
"""The trajectory panel's top is MAIN_HEADROOM times the highest altitude, plus
MAIN_HEADROOM_PER_RUN per legend line beyond two (one line per run; a run of the offload
block has two), plus MAIN_HEADROOM_PER_SECOND_LINE per second line (so per run of the
offload block): room for the legend above the path and above the 'cutoff' label at the
path's top right, which the wide two-line legend reaches. A selection without an offload
run has one line per run, so only the first two terms apply to it (its layout is the
Phase 2 one). With 0.25 the legend clears both by 4.7 px or more in every 2- and 3-run
selection with an offload run of results/silo_offload_2d at 1280 and 640 px (0.20: by
2.7 px; 0.10: it overlaps the 'cutoff' label by up to 4 px; 0: by up to 13 px). Not
covered: 4-run selections, with or without an offload run, and 3-run selections without
one, whose legend can still reach the 'cutoff' label (and, at 640 px with four runs, the
path)."""
TITLE_MAX_CHARS = 48
"""A title listing more characters of run names than this reads 'N runs (see legend)'."""
SMALL_PANEL_XMARGIN = 0.015
"""Right margin of the small time panels, as a fraction of the flight: the end markers
are drawn whole."""
READOUT_LINE_H = 0.062
READOUT_X0 = 0.10
READOUT_Y0 = 0.03
"""Readout block in the trajectory panel's axes fractions: line height, left edge of
the text, baseline of the last row."""
READOUT_BOX_PAD = (0.018, 0.012)
"""Padding of the readout box below its last baseline and above its header [axes fraction]."""
READOUT_GROUND_GAP = 0.03
"""Gap between the readout box and the 0 km line [axes fraction]: the box sits in a
ground band below the trajectory, so no path or event label runs under it."""
READOUT_NAME_CHARS = 9
"""Width of the readout's run-name column (a longer name is cut and marked '~')."""
CLOSEUP_LINTHRESH_M = 100.0
"""Linear range [m] of the close-up's symlog altitude axis: the -100 m silo floor and the
first 100 m of climb are linear, higher altitudes logarithmic (a dotted line marks it)."""
CLOSEUP_TOP_M = 5000.0
"""Top of the close-up's altitude axis [m]."""
CLOSEUP_FLOOR_M = -1000.0
"""Bottom of the close-up's altitude axis [m] (deeper when a shaft is deeper than a
quarter of it): the ground band holds the launch event labels."""
CLOSEUP_FLOOR_FACTOR = 4.0
"""A shaft floor alt_min [m] below CLOSEUP_FLOOR_M / this moves the axis bottom to this
times alt_min."""
CALLOUT_T_S = TIMELINE_LAUNCH_END_S
"""Time after release [s] of the left edge of the launch event labels in the ground band
(the events before TIMELINE_LAUNCH_END_S crowd within a few seconds; they are listed
there with leader lines)."""
CALLOUT_FIRST_ROW = 0.8
"""Centre of the first ground-band label below the ground line, in label steps."""

EVENT_LABELS: dict[str, str] = {
    "push_start": "push start",
    "release": "release",
    "ignition": "ignition",
    "liftoff": "liftoff",
    "kick_end": "kick end",
    "staging": "MECO/staging",
    "fairing": "fairing",
    "cutoff": "cutoff",
    "apex": "apex",
    "impact": "impact",
}
"""events.csv names drawn on the animation and their labels; the rest (kick_start,
ramp_end, the propellant event that coincides with staging, end) are not drawn."""

PHASE_LABELS: dict[str, str] = {
    HOLD_KIND: "hold-down",
    ASSIST_KIND: "assist push",
    COAST_PRE_IGN: "coast, unlit",
    VERTICAL_RISE: "vertical rise",
    KICK: "pitch kick",
    GRAVITY_TURN: "gravity turn",
    COAST_STAGING: "staging coast",
    LTG_BURN: "stage-2 LTG",
    COAST: "coast",
}
"""Readout label of each phase of the time series."""

OFFLOAD_CASE = run_data.OFFLOAD_CASE
OFFLOAD_PAIRED_PAD = run_data.OFFLOAD_PAIRED_PAD
OFFLOAD_PAD_CONTROL = run_data.OFFLOAD_PAD_CONTROL
"""What a run of metrics.json's ``offload.runs`` is (``offload_role``): an offload case's
recorded run, the paired pad of a case or a pad control. The run_data constants (moved
there in SP2 step A1) under their names here."""
OFFLOAD_SOLVED_KIND = run_data.OFFLOAD_SOLVED_KIND
"""``kind`` of an offload case whose offload was solved at P_ref, so it flies P_ref (a
``fixed`` case imposes its offload, and its figure is its own P* against P_ref)."""
NEAR_ORBIT_PHASE = "~inserted"
"""Readout phase at the end of a pad control whose recorded run misses P_ref by grams
of residual propellant at the search's resolution (its record's ``resolution_effect``;
summary.md: not a failure), where any other run that did not insert reads 'ended,
<status>'."""
LEGEND_TITLE = "payload capacity P* (sweep-optimized)"
"""Title of the trajectory panel's legend; with an offload run shown it also says what
P_ref is (``legend_title``)."""

CALIBRATION_RECORDS = run_data.CALIBRATION_RECORDS
"""Calibration record per vehicle: run_data.CALIBRATION_RECORDS, the same dict object
(its docstring holds the provenance). ``calibration_caveat`` below reads this module's
name at call time, so a test can put another table in its place."""
CALIBRATION_BAND = run_data.CALIBRATION_BAND
"""Relative payload band of the calibration gate (run_data.CALIBRATION_BAND)."""
CALIBRATION_BAND_EDGE_REL_TOL = run_data.CALIBRATION_BAND_EDGE_REL_TOL
"""Relative tolerance [-] on the band's edges (run_data.CALIBRATION_BAND_EDGE_REL_TOL)."""
CALIBRATION_GATE_VEHICLE = run_data.CALIBRATION_GATE_VEHICLE
"""The pre-registered calibration gate (mass set C), named "Gate vehicle" in the footnote."""
calibration_gap = run_data.calibration_gap
inside_calibration_band = run_data.inside_calibration_band
"""run_data.calibration_gap and run_data.inside_calibration_band (the same objects):
the relative gap of a record [-] and whether it lies inside the gate band."""


@dataclass(frozen=True)
class AnimationEvent:
    """One drawn event of a run: time after release t_s [s], label, altitude [m],
    downrange [m] (planar ascent frame) and Earth-relative speed [m/s] (NaN when
    events.csv has no speed column)."""

    t_s: float
    label: str
    alt_m: float
    downrange_m: float
    speed_rel_mps: float = math.nan


@dataclass(frozen=True)
class OffloadTag:
    """How the animation labels a run of metrics.json's ``offload.runs``
    (``offload_tag``): its kind (OFFLOAD_CASE, OFFLOAD_PAIRED_PAD, OFFLOAD_PAD_CONTROL, or
    'offload' for a run the block records but names in no case or control), the legend
    text after its name, and whether its recorded run ends grams of propellant short of
    orbit by a resolution effect (a pad control: read as a pad control, not a failure)."""

    kind: str
    legend: str
    resolution_effect: bool = False


@dataclass(frozen=True)
class AnimationRun:
    """The series of one planar run the animation draws, on the time after release
    t_s [s]: altitude alt_m [m], downrange_m [m], Earth-relative speed [m/s], felt axial
    acceleration [g0], dynamic pressure q_pa [Pa] (NaN in a vented shaft), mass m_kg [kg]
    and the phase label per row; its drawn events; its payload [kg] and status from
    metrics.json (``runs``, or ``offload.runs`` for a run of the offload block); whether
    it is the experiment's baseline; for a run of the offload block, its OffloadTag."""

    name: str
    t_s: FloatArray
    alt_m: FloatArray
    downrange_m: FloatArray
    speed_rel_mps: FloatArray
    felt_axial_g: FloatArray
    q_pa: FloatArray
    m_kg: FloatArray
    phase: NDArray[np.object_]
    events: tuple[AnimationEvent, ...]
    payload_kg: float | None
    status: str | None
    baseline: bool
    offload: OffloadTag | None = None

    @property
    def t_start_s(self) -> float:
        """First time after release of the series [s]."""
        return float(self.t_s[0])

    @property
    def t_end_s(self) -> float:
        """Last time after release of the series [s]."""
        return float(self.t_s[-1])

    def push_peak_g(self) -> float | None:
        """Peak felt axial acceleration [g0] during the assist push, or None without one."""
        push = self.phase == ASSIST_KIND
        return float(np.nanmax(self.felt_axial_g[push])) if bool(np.any(push)) else None


ANIMATION_COLUMNS = run_data.PLANAR_BASE_COLUMNS
"""timeseries.csv columns the animation reads (a planar_2d run writes all of them):
run_data.PLANAR_BASE_COLUMNS, the same tuple."""

animation_run_names = run_data.run_names
"""run_data.run_names (the same object): (default selection, every animatable run) of a
results directory. Animatable: a subdirectory holding timeseries.csv; metrics.json's run
order (the summary order) comes first, other run directories (bound re-runs) follow,
sorted. The default is the baseline plus up to ANIMATION_DEFAULT_VARIANTS variants, in
summary order."""
offload_role = run_data.offload_role
"""run_data.offload_role (the same object): (kind, record) of a run of metrics.json's
``offload`` block, shared with the replay page's note."""


def check_planar_run_dir(run_dir: Path) -> dict[str, Any]:
    """Return metrics.json of a planar_2d results directory; raise AnimationError for a
    missing directory, a directory without metrics.json, a directory that is not an
    experiment's results directory, or a run of another model (vertical_1d has no
    downrange or altitude-over-a-curved-Earth series to draw).

    The shared check of run_data (run_data.check_run_dir) with animate's wording. A
    deliberate change of SP2 step A1 (D-SP2-14): a directory whose metrics.json has no
    ``runs`` mapping (a sweep point, a single run's folder) is now reported as "not an
    experiment results directory", as replay reports it; before, animate called a
    planar sweep point "a vertical_1d run"."""
    return run_data.check_run_dir(run_dir, error=AnimationError, wording=ANIMATION_WORDING)


def _events(path: Path, offset_s: float) -> tuple[AnimationEvent, ...]:
    """The drawn events of events.csv (EVENT_LABELS), their t_s converted to the time
    after release by subtracting ``offset_s`` (the run's t_s - t_rel_release_s). A
    stage-2 ignition is labelled 'S2 ignition'. A projection of run_data.read_events
    (every row) to the rows drawn, with the recorded values unrounded.

    A reader-side change of SP2 step A1: run_data.read_events requires only the t_s and
    event columns, so an events.csv without alt_m or downrange_m now reads like one
    without speed_rel_mps always did. Its rows are kept, not skipped, with NaN (not
    None) in each missing column, and a marker at NaN draws nothing. Before A1 this
    function read alt_m and downrange_m by attribute and such a file raised."""
    out: list[AnimationEvent] = []
    for row in run_data.read_events(path, offset_s, error=AnimationError):
        if row.name not in EVENT_LABELS:
            continue
        label = EVENT_LABELS[row.name]
        if row.name == "ignition" and row.stage not in (None, "stage1"):
            label = "S2 ignition"
        out.append(
            AnimationEvent(row.t_rel_s, label, row.alt_m, row.downrange_m, row.speed_rel_mps)
        )
    return tuple(out)


def _finite_kg(value: Any) -> float | None:
    """``value`` as a float [kg], or None when it is missing, not a number or not finite."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) else None


def offload_tag(offload: Mapping[str, Any], name: str, record: Mapping[str, Any]) -> OffloadTag:
    """The OffloadTag of run ``name`` of metrics.json's ``offload`` block, whose own
    record (``offload.runs[name]``) is ``record``. Its legend text has two lines (payloads
    P [kg] rounded to 1 kg, offloads in tonnes to 0.1 t; P is the run's recorded payload):
    a solved case 'flies P_ref <P> kg' / 'on <x> t less propellant' (x: the case's
    ``total_offload_kg``); a solved case whose solve found no offload (status
    no_offload: its recorded run is the full-load run, x* = 0, which cannot carry P_ref)
    'flies P_ref <P> kg, no offload' / 'does not reach orbit at P_ref even at full
    load'; a fixed case 'P* <P> kg (<P - P_ref> kg vs P_ref)' / 'on <x> t less
    propellant'; a paired pad 'P* <P> kg (<P - P_ref> kg vs P_ref)' / 'with the same
    offload, no push'; an ok pad control 'flies P_ref <P> kg' / 'on <x_pad> t less
    propellant'; a no_offload pad control 'flies P_ref <P> kg, no offload' / how far short
    of orbit its recorded run ends [kg of propellant, 2 significant figures] when its
    record's ``resolution_effect`` holds ('<m> kg of propellant short of orbit: a
    resolution effect, not a failure'), else 'short of orbit by more than the search
    resolution'. A run without a payload, or one the block names in no case or control,
    gets one line: 'payload n/a (<status>)' or 'payload <P> kg'."""
    role = offload_role(offload, name)
    kind, rec = ("offload", {}) if role is None else role
    payload = _finite_kg(record.get("payload_kg"))
    if payload is None:
        return OffloadTag(kind, f"payload n/a ({record.get('status')})")
    if role is None:
        return OffloadTag(kind, f"payload {payload:,.0f} kg")
    p_ref = _finite_kg(offload.get("reference_payload_kg"))
    vs_ref = "" if p_ref is None else f" ({payload - p_ref:+,.0f} kg vs P_ref)"
    removed = _finite_kg(rec.get("total_offload_kg" if kind == OFFLOAD_CASE else "offload_kg"))
    less = (
        "offload not recorded"
        if removed is None
        else f"on {float(kg_to_t(removed)):.1f} t less propellant"
    )
    near = False
    if kind == OFFLOAD_PAIRED_PAD:
        head, detail = f"P* {payload:,.0f} kg{vs_ref}", "with the same offload, no push"
    elif kind == OFFLOAD_CASE and rec.get("kind") != OFFLOAD_SOLVED_KIND:
        head, detail = f"P* {payload:,.0f} kg{vs_ref}", less
    elif kind == OFFLOAD_CASE and rec.get("status") == NO_OFFLOAD_STATUS:
        head = f"flies P_ref {payload:,.0f} kg, no offload"
        detail = "does not reach orbit at P_ref even at full load"
    elif kind == OFFLOAD_PAD_CONTROL and rec.get("status") == NO_OFFLOAD_STATUS:
        head = f"flies P_ref {payload:,.0f} kg, no offload"
        near = bool(rec.get("resolution_effect"))
        m_res = _finite_kg(rec.get("m_res_kg"))
        short = "grams" if m_res is None else f"{abs(m_res):.2g} kg"
        detail = (
            f"{short} of propellant short of orbit: a resolution effect, not a failure"
            if near
            else "short of orbit by more than the search resolution"
        )
    else:
        head, detail = f"flies P_ref {payload:,.0f} kg", less
    return OffloadTag(kind, f"{head}\n{detail}", near)


def animation_record(
    metrics: Mapping[str, Any], name: str
) -> tuple[dict[str, Any], OffloadTag | None]:
    """(metrics record, OffloadTag or None) of run ``name``: its ``runs`` record and None
    for an experiment run; for a run of the offload block (``offload.runs``, as
    replay.run_source reads it) that record and its ``offload_tag``; ({}, None) for a run
    metrics.json records in neither."""
    runs = run_data.as_mapping(metrics.get("runs"))
    if name in runs:
        return run_data.as_mapping(runs[name]), None
    offload = run_data.as_mapping(metrics.get("offload"))
    offload_runs = run_data.as_mapping(offload.get("runs"))
    if name in offload_runs:
        record = run_data.as_mapping(offload_runs[name])
        return record, offload_tag(offload, name, record)
    return {}, None


def read_animation_run(run_dir: Path, name: str, metrics: dict[str, Any]) -> AnimationRun:
    """Read one planar run of a results directory: <name>/timeseries.csv (the columns of
    ANIMATION_COLUMNS), <name>/events.csv and its metrics.json record
    (``animation_record``: ``runs``, or ``offload.runs`` with its OffloadTag). Raises
    AnimationError when the series lacks planar columns or is empty. The series is read
    as written (run_data.read_series_frame: file order, both rows of a phase boundary),
    not sorted and de-duplicated as the replay page reads it."""
    frame = run_data.read_series_frame(run_dir, name, ANIMATION_COLUMNS, error=AnimationError)
    t = frame["t_rel_release_s"].to_numpy(dtype=float)
    offset_s = run_data.release_offset_s(frame)
    record, tag = animation_record(metrics, name)
    payload = record.get("payload_kg")
    return AnimationRun(
        name=name,
        t_s=t,
        alt_m=frame["alt_m"].to_numpy(dtype=float),
        downrange_m=frame["downrange_m"].to_numpy(dtype=float),
        speed_rel_mps=frame["speed_rel_mps"].to_numpy(dtype=float),
        felt_axial_g=frame["felt_axial_g"].to_numpy(dtype=float),
        q_pa=frame["q_pa"].to_numpy(dtype=float),
        m_kg=frame["m_kg"].to_numpy(dtype=float),
        phase=frame["phase"].astype(str).to_numpy(dtype=object),
        events=_events(run_dir / name / run_data.EVENTS_FILE, offset_s),
        payload_kg=None if payload is None else float(payload),
        status=record.get("status"),
        baseline=name == metrics.get("baseline"),
        offload=tag,
    )


def load_animation_runs(
    run_dir: Path, runs: Sequence[str] | None
) -> tuple[list[AnimationRun], dict[str, Any]]:
    """(the selected runs, metrics.json) of a planar results directory. ``runs`` None
    selects the default (``animation_run_names``); unknown or repeated names, more than
    ANIMATION_MAX_RUNS names, or a non-planar directory raise AnimationError (the
    directory check first, then run_data.select_runs)."""
    metrics = check_planar_run_dir(run_dir)
    names = run_data.select_runs(run_dir, runs, what="animation", error=AnimationError)
    return [read_animation_run(run_dir, n, metrics) for n in names], metrics


def _timeline_knots(t_start_s: float, t_end_s: float) -> tuple[list[float], list[float]]:
    """(flight times after release [s], video fractions) of the corners of the
    piecewise-linear timeline: the launch segment to TIMELINE_LAUNCH_END_S (about real
    time), the close-up segment to TIMELINE_KNEE_S, the fast segment to t_end_s at
    1 - TIMELINE_HOLD_FRACTION, then the hold. A corner at or before t_start_s is
    dropped; a flight that ends by the knee plays at one speed."""
    times, fracs = [t_start_s], [0.0]
    if t_end_s > TIMELINE_KNEE_S:
        corners = (
            (TIMELINE_LAUNCH_END_S, TIMELINE_LAUNCH_FRACTION),
            (TIMELINE_KNEE_S, TIMELINE_LAUNCH_FRACTION + TIMELINE_CLOSEUP_FRACTION),
        )
        for t_corner, frac in corners:
            if t_start_s < t_corner:
                times.append(t_corner)
                fracs.append(frac)
    times.append(t_end_s)
    fracs.append(1.0 - TIMELINE_HOLD_FRACTION)
    return times, fracs


def _check_timeline(t_start_s: float, t_end_s: float, n_frames: int) -> None:
    """Raise AnimationError for fewer than 2 frames or an empty flight."""
    if n_frames < 2:
        raise AnimationError(f"an animation needs at least 2 frames, got {n_frames}")
    if not t_end_s > t_start_s:
        raise AnimationError(f"empty timeline: {t_start_s} s to {t_end_s} s")


def ascent_time_map(t_start_s: float, t_end_s: float, n_frames: int) -> FloatArray:
    """Flight time after release [s] of each of ``n_frames`` video frames on the
    three-speed timeline of ``_timeline_knots`` (launch at about real time, the close-up
    faster, the rest of the flight fast, then a hold of the last state). The result is
    non-decreasing, starts at t_start_s and ends at t_end_s."""
    _check_timeline(t_start_s, t_end_s, n_frames)
    knots_t, knots_f = _timeline_knots(t_start_s, t_end_s)
    times = np.interp(np.linspace(0.0, 1.0, n_frames), knots_f, knots_t)
    times[0], times[-1] = t_start_s, t_end_s
    return times


def playback_speeds(t_start_s: float, t_end_s: float, n_frames: int, fps: float) -> FloatArray:
    """Nominal playback speed of each of ``n_frames`` frames [flight s per video s]: the
    slope of its timeline segment in a video (n_frames - 1) / ``fps`` long (``fps``: the
    rate the file plays at, ``animation_playback_fps``); 0 during the end hold."""
    _check_timeline(t_start_s, t_end_s, n_frames)
    knots_t, knots_f = _timeline_knots(t_start_s, t_end_s)
    video_s = (n_frames - 1) / fps
    slopes = np.diff(knots_t) / (np.diff(knots_f) * video_s)
    u = np.linspace(0.0, 1.0, n_frames)
    segment = np.clip(np.searchsorted(knots_f, u, side="right") - 1, 0, len(slopes) - 1)
    return np.where(u >= knots_f[-1], 0.0, slopes[segment])


def playback_label(speed: float, t_s: float) -> str:
    """The playback note of a frame at flight time ``t_s`` [s after release] played at
    ``speed`` (0: the end hold): the rate to 2 significant figures and the segment
    (slow motion below SLOW_MOTION_BELOW x real time)."""
    if speed <= 0.0:
        return "end of flight: holding the last state"
    rate = f"{speed:.1f}" if speed < 10.0 else f"{speed:.0f}"
    if speed < SLOW_MOTION_BELOW:
        part = "slow motion"
    elif t_s < TIMELINE_LAUNCH_END_S:
        part = "launch"
    elif t_s < TIMELINE_KNEE_S:
        part = f"close-up to T+{TIMELINE_KNEE_S:.0f} s"
    else:
        part = "fast forward"
    return f"playback {rate}x real time ({part})"


def animation_playback_fps(fps: int, suffix: str) -> float:
    """Frames per second an output plays at: ``fps`` for .mp4; for .gif, 1000 / the frame
    delay, the delay being PillowWriter's int(1000 / fps) ms floored to a whole
    GIF_DELAY_STEP_MS. Raises AnimationError for fps < 1 or a GIF delay under
    GIF_MIN_DELAY_MS."""
    if fps < 1:
        raise AnimationError(f"--fps must be >= 1, got {fps}")
    if suffix.lower() != ".gif":
        return float(fps)
    delay_ms = int(1000 / fps) // GIF_DELAY_STEP_MS * GIF_DELAY_STEP_MS
    if delay_ms < GIF_MIN_DELAY_MS:
        raise AnimationError(
            f"a .gif plays at most {1000 // GIF_MIN_DELAY_MS} fps (browsers slow shorter "
            f"frame delays), got --fps {fps}; use .mp4 for more"
        )
    return 1000.0 / delay_ms


def default_animation_path(run_dir: Path, cwd: Path, *, ffmpeg: bool | None = None) -> Path:
    """<cwd>/<experiment>_<timestamp>_animation.mp4, or .gif when ffmpeg is missing
    (``ffmpeg`` None asks matplotlib). When cwd is inside a results tree the file goes
    next to the outermost such tree instead: an animation is never written into
    results/.

    The folder comes from the shared rule (run_data.default_output_path). A deliberate
    change of SP2 step A1 (D-SP2-14, KI-017): a results tree is the run's own tree or
    any folder named results in any letter case, as for replay; before, only the run's
    own tree counted, so from a working directory inside another results folder the
    default landed inside that folder."""
    experiment, timestamp = run_data.run_identity(run_dir)
    have_ffmpeg = FFMpegWriter.isAvailable() if ffmpeg is None else ffmpeg
    suffix = ".mp4" if have_ffmpeg else ".gif"
    name = plot_stem(f"{experiment}_{timestamp}", "animation") + suffix
    return run_data.default_output_path(run_dir, cwd, name)


def check_animation_out(out_path: Path, run_dir: Path) -> None:
    """Raise AnimationError for an output outside ANIMATION_FORMATS, inside a results
    tree (results/ is generated, never hand-edited), a .mp4 without ffmpeg, or a folder
    that does not exist, in that order.

    The extension, tree and folder checks are the shared ones (the three parts of
    run_data.check_output); the ffmpeg test stays here, between the tree and the folder.
    A deliberate change of SP2 step A1 (D-SP2-14, KI-017): the tree check is the stricter
    rule replay uses (run_data.protected_tree): an output is refused inside the run's
    own tree and inside any folder named results in any letter case; before, an output
    in another results folder, or in the outer tree of a nested pair, was accepted."""
    suffix_text = f"{' or '.join(ANIMATION_FORMATS)} (the extension picks the format)"
    run_data.check_output_suffix(out_path, ANIMATION_FORMATS, suffix_text, error=AnimationError)
    run_data.check_outside_results(out_path, run_dir, what="animation", error=AnimationError)
    if out_path.suffix.lower() == ".mp4" and not FFMpegWriter.isAvailable():
        raise AnimationError(
            "writing .mp4 needs ffmpeg on PATH (or matplotlib's animation.ffmpeg_path); "
            "install ffmpeg or ask for a .gif"
        )
    run_data.check_output_folder(out_path, error=AnimationError)


def frame_geometry(width_px: int) -> tuple[tuple[float, float], float, tuple[int, int]]:
    """(figure size [in], dpi, frame size [px]) of a frame ``width_px`` wide: 16:9 at the
    ANIMATION_FIG_WIDTH_IN design width, the height rounded to an even pixel count
    (H.264 in yuv420p needs even sides). Raises AnimationError for an odd width or one
    below ANIMATION_MIN_WIDTH_PX."""
    if width_px < ANIMATION_MIN_WIDTH_PX or width_px % 2:
        raise AnimationError(
            f"--width must be an even number of pixels >= {ANIMATION_MIN_WIDTH_PX}, got {width_px}"
        )
    height_px = 2 * round(width_px * ANIMATION_ASPECT / 2)
    dpi = width_px / ANIMATION_FIG_WIDTH_IN
    size = ((width_px + FRAME_PX_EPS) / dpi, (height_px + FRAME_PX_EPS) / dpi)
    return size, dpi, (width_px, height_px)


def animation_frame_count(fps: float, seconds: float) -> int:
    """Number of frames of a video ``seconds`` long playing at ``fps`` frames per second
    (at least 2); raises AnimationError for fps <= 0 or a length that is not positive."""
    if not fps > 0 or not seconds > 0:
        raise AnimationError(f"--fps must be >= 1 and --seconds > 0 (got {fps}, {seconds})")
    return max(2, round(fps * seconds))


def _state(run: AnimationRun, t_s: float, values: FloatArray) -> float:
    """``values`` of ``run`` interpolated linearly at the time after release ``t_s``;
    held at the first or last sample outside the series."""
    return float(np.interp(t_s, run.t_s, values))


def _phase_at(run: AnimationRun, t_s: float) -> str:
    """Readout label of the run's phase at ``t_s``: before the series starts 'on pad'
    (a run that begins with a hold-down) or 'not started'; the phase of the last row at
    or before ``t_s``; from the series' last time on, 'inserted', NEAR_ORBIT_PHASE for a
    pad control short of orbit by a resolution effect (OffloadTag), or 'ended, <status>'."""
    if t_s < run.t_start_s:
        return "on pad" if str(run.phase[0]) == HOLD_KIND else "not started"
    if t_s >= run.t_end_s:
        if run.status == "inserted":
            return "inserted"
        if run.offload is not None and run.offload.resolution_effect:
            return NEAR_ORBIT_PHASE
        return f"ended, {run.status}"
    i = int(np.clip(np.searchsorted(run.t_s, t_s, side="right") - 1, 0, len(run.t_s) - 1))
    raw = str(run.phase[i])
    return PHASE_LABELS.get(raw, raw.lower())


def _trail(
    run: AnimationRun, t_s: float, x: FloatArray, y: FloatArray
) -> tuple[FloatArray, FloatArray]:
    """The points of (x, y) at or before ``t_s``, closed by the interpolated point at
    ``t_s`` (the moving head of the trail); empty before the series starts."""
    if t_s < run.t_start_s:
        return np.empty(0), np.empty(0)
    n = int(np.searchsorted(run.t_s, t_s, side="right"))
    return np.append(x[:n], _state(run, t_s, x)), np.append(y[:n], _state(run, t_s, y))


def signed(value: float, decimals: int = 1) -> str:
    """``value`` with an explicit sign and ``decimals`` decimals; a value that rounds to
    zero prints as +0.0, never -0.0."""
    text = f"{value:+.{decimals}f}"
    return "+" + text[1:] if float(text) == 0.0 else text


def _fmt_alt(alt_m: float) -> str:
    """Altitude for the readout: metres below 1 km, kilometres above (10 characters)."""
    if abs(float(m_to_km(alt_m))) < 1.0:
        return f"{alt_m:7.0f} m "
    return f"{float(m_to_km(alt_m)):7.1f} km"


def readout_names(names: Sequence[str], width: int = READOUT_NAME_CHARS) -> list[str]:
    """Run names for the readout's name column, at most ``width`` characters: a longer
    name is cut and ends in '~'; names that would read the same after the cut end in
    '~' and their 1-based position instead (e.g. 'silo_ho~3')."""
    out = [n if len(n) <= width else n[: width - 1] + "~" for n in names]
    return [
        s if out.count(s) == 1 else f"{names[k][: width - 1 - len(str(k + 1))]}~{k + 1}"
        for k, s in enumerate(out)
    ]


def _legend_label(run: AnimationRun, base: AnimationRun | None) -> str:
    """Legend entry: name, '(baseline)', P* [kg] and its change against the baseline; for
    a run of the offload block, its name, '(<kind>)' and its OffloadTag text, never a
    change against the baseline (what it measures is propellant at P_ref)."""
    if run.offload is not None:
        return f"{run.name} ({run.offload.kind}): {run.offload.legend}"
    tag = " (baseline)" if run.baseline else ""
    if run.payload_kg is None:
        return f"{run.name}{tag}: P* n/a ({run.status})"
    text = f"{run.name}{tag}: P* {run.payload_kg:,.0f} kg"
    if base is not None and base is not run and base.payload_kg is not None:
        text += f" ({run.payload_kg - base.payload_kg:+,.0f} kg)"
    return text


def legend_title(runs: Sequence[AnimationRun], metrics: Mapping[str, Any]) -> str:
    """The legend title: LEGEND_TITLE, and with a run of the offload block shown, what
    P_ref is: the P* of the offload block's reference baseline (``offload.reference``,
    else the experiment's baseline)."""
    if not any(r.offload is not None for r in runs):
        return LEGEND_TITLE
    offload = run_data.as_mapping(metrics.get("offload"))
    reference = offload.get("reference") or metrics.get("baseline")
    return f"{LEGEND_TITLE}; P_ref = {reference}'s P*"


def calibration_caveat(vehicle_name: str | None) -> str:
    """The footnote's calibration sentence of a vehicle, from CALIBRATION_RECORDS: the
    gap between its calibration P* and the published reference [%] and, for a record
    inside the gate band (``inside_calibration_band``), that it is inside; or a note that
    the vehicle has no calibration record. The gate vehicle (CALIBRATION_GATE_VEHICLE) is
    called "Gate vehicle", any other "This vehicle" (a full vehicle name would push the
    footnote line past the frame's right edge at 1280 px)."""
    record = CALIBRATION_RECORDS.get(vehicle_name or "")
    if record is None:
        return f"Vehicle {vehicle_name}: no calibration record on file."
    model_kg, reference_kg, note = record
    fraction = calibration_gap(model_kg, reference_kg)
    gap = float(to_percent(fraction))
    side = "high" if gap >= 0.0 else "low"
    who = "Gate vehicle" if vehicle_name == CALIBRATION_GATE_VEHICLE else "This vehicle"
    band = ""
    if inside_calibration_band(fraction):
        band = f", inside the +/-{to_percent(CALIBRATION_BAND):.0f}% band"
    return f"{who} calibrates {gap:+.1f}% {side} on payload{band} ({note})."


def animation_caveats(runs: Sequence[AnimationRun], vehicle_name: str | None) -> list[str]:
    """The three footnote lines: the model; its limits and, when a run has an assist
    push, the structural caveat of the push load (the peak felt axial g of the ASSIST
    rows); the vehicle's calibration and the replay disclaimer."""
    first = (
        "Planar 2-D model (rotating spherical Earth, ICAO atmosphere, drag); "
        "sweep-optimized guidance, not optimal control."
    )
    second = "Unthrottled (no max-Q or g limit)"
    peaks = [g for g in (r.push_peak_g() for r in runs) if g is not None]
    if peaks:
        second += f"; no structural mass for the {max(peaks):.1f} g push load"
    third = calibration_caveat(vehicle_name) + " A model replay, not a design result."
    return [first, second + ".", third]


def _readout_top(n_runs: int) -> float:
    """Top of the readout box (a header and one line per run) [axes fraction of the
    trajectory panel]."""
    return READOUT_Y0 + READOUT_LINE_H * (n_runs + 1) - READOUT_BOX_PAD[0] + READOUT_BOX_PAD[1]


def _style_axes(ax: Any) -> None:
    """Shared look of an animation panel: light grid, no top/right spines, small ticks."""
    ax.grid(True, color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(labelsize=FONT_TICK_PT, length=2.5, pad=1.5)


LABEL_MERGE_X = 0.05
LABEL_MERGE_Y = 0.05
"""The same event label of several runs closer than these fractions of the frame width
and height on the trajectory panel is one label listing each run's value."""
LABEL_MERGE_DT_S = 0.5
"""On the close-up (time on x) the same label merges only within this many seconds [s]."""
LABEL_NEAR_X = 0.06
"""Event labels whose points are closer than this fraction of the frame width, and whose
texts would be less than a label step apart vertically, are moved apart."""
LABEL_STACK_PT = 9.0
"""Vertical step [pt] between stacked event labels and between the ground-band labels."""
LABEL_LEFT_BEYOND = 0.7
"""Trajectory-panel events right of this axes fraction are labelled above-left (the
path runs flat there); the others to the right, under the rising path."""


@dataclass(eq=False)
class _LabelGroup:
    """One event label on a panel: the copies of one event (same label) of one or more
    runs at nearly the same point (x, y) in data units, (px_x, px_y) in pixels, drawn as
    one annotation whose text lists each run's value once its event has happened.
    ``members``: (run index, time after release [s], value text or None)."""

    ax: Any
    label: str
    unit: str
    x: float
    y: float
    px_x: float
    px_y: float
    members: list[tuple[int, float, str | None]] = field(default_factory=list)
    artist: Any = None


class _AscentFigure:
    """The animation's figure and its per-frame artists; ``draw_frame`` moves every
    trail, marker, cursor, event and readout to one time after release. Event markers
    and labels are laid out once, from every run's events, and shown as they happen."""

    def __init__(
        self,
        runs: list[AnimationRun],
        metrics: dict[str, Any],
        vehicle: str | None,
        size_in: tuple[float, float],
        dpi: float,
    ) -> None:
        self.runs = runs
        self.fig = Figure(figsize=size_in, dpi=dpi, facecolor="white")
        self.t0 = min(r.t_start_s for r in runs)
        self.t1 = max(r.t_end_s for r in runs)
        self.window = TIMELINE_KNEE_S if self.t1 > TIMELINE_KNEE_S else self.t1
        self.names = readout_names([r.name for r in runs])
        gs = self.fig.add_gridspec(
            1, 2, width_ratios=(ANIMATION_MAIN_WIDTH_RATIO, 1.0), **ANIMATION_GRID
        )
        right = gs[0, 1].subgridspec(
            2, 1, height_ratios=(ANIMATION_CLOSEUP_HEIGHT_RATIO, 2.0), hspace=0.3
        )
        small = right[1].subgridspec(3, 1, hspace=0.2)
        self.ax_main = self.fig.add_subplot(gs[0, 0])
        self.ax_close = self.fig.add_subplot(right[0])
        self.ax_small = [self.fig.add_subplot(small[i]) for i in range(3)]
        for ax in self.ax_small[1:]:
            ax.sharex(self.ax_small[0])
        self._title(metrics)
        self._main_axes(next((r for r in runs if r.baseline), None), legend_title(runs, metrics))
        self._close_axes()
        self._small_axes()
        self._readout_setup()
        self._layout_events()
        self.fig.text(
            ANIMATION_GRID["left"],
            0.012,
            _plot_text("\n".join(animation_caveats(runs, vehicle))),
            fontsize=FONT_FOOTNOTE_PT,
            color=ANIMATION_FOOTNOTE_COLOR,
            va="bottom",
            linespacing=1.3,
        )

    def _style(self, i: int) -> tuple[str, str, str]:
        """(colour, dash, marker) of run ``i``."""
        return ANIMATION_RUN_STYLES[i % len(ANIMATION_RUN_STYLES)]

    def _text_color(self, i: int) -> str:
        """Text colour of run ``i``."""
        return ANIMATION_RUN_TEXT_COLORS[i % len(ANIMATION_RUN_TEXT_COLORS)]

    def _glyph(self, i: int) -> str:
        """Text glyph of run ``i``'s marker shape."""
        return MARKER_GLYPHS[self._style(i)[2]]

    def _head(self, ax: Any, i: int, size: float) -> Any:
        """An empty moving marker of run ``i`` on ``ax``."""
        color, _, marker = self._style(i)
        (head,) = ax.plot(
            [],
            [],
            marker=marker,
            color=color,
            markeredgecolor="black",
            markeredgewidth=0.6,
            markersize=size,
            linestyle="none",
            zorder=10,
        )
        return head

    def _title(self, metrics: dict[str, Any]) -> None:
        """Title, subtitle (experiment, timestamp, git), clock and playback speed."""
        names = " vs ".join(r.name for r in self.runs)
        if len(names) > TITLE_MAX_CHARS:
            names = f"{len(self.runs)} runs (see legend)"
        left = ANIMATION_GRID["left"]
        right = ANIMATION_GRID["right"]
        self.fig.text(
            left,
            0.975,
            _plot_text(f"Ascent replay: {names}"),
            fontsize=FONT_TITLE_PT,
            fontweight="bold",
            color=ANIMATION_TEXT_COLOR,
            va="top",
        )
        git = metrics.get("git", {}) or {}
        sub = (
            f"{metrics.get('experiment', '')} / {metrics.get('timestamp_utc', '')} "
            f"(git {git.get('hash', '?')}); time T is measured from release"
        )
        self.fig.text(
            left,
            0.925,
            _plot_text(sub),
            fontsize=FONT_SMALL_PT,
            color=ANIMATION_MUTED_COLOR,
            va="top",
        )
        self.clock = self.fig.text(
            right,
            0.975,
            "",
            fontsize=FONT_TITLE_PT,
            fontweight="bold",
            color=ANIMATION_TEXT_COLOR,
            va="top",
            ha="right",
            family="monospace",
        )
        self.speed = self.fig.text(
            right,
            0.925,
            "",
            fontsize=FONT_SMALL_PT,
            color=ANIMATION_TEXT_COLOR,
            va="top",
            ha="right",
        )

    def _main_axes(self, base: AnimationRun | None, title: str) -> None:
        """Altitude [km] against downrange [km]: faint full paths, growing trails, moving
        markers, the P* legend under ``title`` (``legend_title``)."""
        ax = self.ax_main
        _style_axes(ax)
        x_max = max(float(np.nanmax(m_to_km(r.downrange_m))) for r in self.runs)
        x_min = min(float(np.nanmin(m_to_km(r.downrange_m))) for r in self.runs)
        y_max = max(float(np.nanmax(m_to_km(r.alt_m))) for r in self.runs)
        span = max(x_max - min(x_min, 0.0), 1e-3)
        ax.set_xlim(min(x_min, 0.0) - 0.01 * span, x_max + 0.03 * span)
        n = len(self.runs)
        labels = [_legend_label(run, base) for run in self.runs]
        second = sum(label.count("\n") for label in labels)
        lines = n + second
        headroom = (
            MAIN_HEADROOM
            + MAIN_HEADROOM_PER_RUN * max(0, lines - 2)
            + MAIN_HEADROOM_PER_SECOND_LINE * second
        )
        top = headroom * y_max if y_max > 0 else 1.0
        ground = _readout_top(n) + READOUT_GROUND_GAP  # axes fraction of 0 km
        bottom = -top * ground / (1.0 - ground)
        ax.set_ylim(bottom, top)
        ax.set_yticks([v for v in MaxNLocator(6).tick_values(0.0, top) if 0.0 <= v <= top])
        ax.axhspan(bottom, 0.0, color=ANIMATION_GROUND_COLOR, zorder=0, linewidth=0)
        ax.axhline(0.0, color=ANIMATION_MUTED_COLOR, linewidth=0.8, zorder=1)
        ax.set_xlabel("downrange [km]", fontsize=FONT_LABEL_PT, labelpad=1.5)
        ax.set_ylabel("altitude [km]", fontsize=FONT_LABEL_PT, labelpad=1.5)
        ax.set_title(
            "Trajectory: altitude vs downrange",
            fontsize=FONT_LABEL_PT,
            loc="left",
            color=ANIMATION_TEXT_COLOR,
            pad=3,
        )
        self.main_trails, self.main_heads = [], []
        for i, run in enumerate(self.runs):
            color, dash, _ = self._style(i)
            dr_km, alt_km = m_to_km(run.downrange_m), m_to_km(run.alt_m)
            ax.plot(dr_km, alt_km, color=color, linewidth=0.8, linestyle=dash, alpha=0.25)
            (trail,) = ax.plot(
                [],
                [],
                color=color,
                linestyle=dash,
                linewidth=ANIMATION_LINE_WIDTH,
                label=_plot_text(labels[i]),
            )
            self.main_trails.append(trail)
            self.main_heads.append(self._head(ax, i, ANIMATION_MARKER_SIZE))
        ax.legend(
            loc="upper left",
            fontsize=FONT_READOUT_PT,
            frameon=True,
            framealpha=0.92,
            edgecolor=PLOT_GRID_COLOR,
            handlelength=2.6,
            borderaxespad=0.4,
            title=_plot_text(title),
            title_fontsize=FONT_SMALL_PT,
        )

    def _close_axes(self) -> None:
        """Altitude [m] (symlog) against the time after release [s] up to the knee: the
        ground band, the shaft below it, the hold-down spans, trails and a cursor."""
        ax = self.ax_close
        _style_axes(ax)
        ax.set_xlim(min(self.t0, 0.0) - 0.5, self.window)
        ax.set_yscale("symlog", linthresh=CLOSEUP_LINTHRESH_M, linscale=1.0)
        alt_min = min(float(np.nanmin(r.alt_m)) for r in self.runs)
        y_lo = min(CLOSEUP_FLOOR_FACTOR * alt_min, CLOSEUP_FLOOR_M)
        ax.set_ylim(y_lo, CLOSEUP_TOP_M)
        ticks = [-CLOSEUP_LINTHRESH_M, 0.0, CLOSEUP_LINTHRESH_M, 10.0 * CLOSEUP_LINTHRESH_M]
        ax.set_yticks(ticks)
        ax.set_yticklabels([f"{v:.0f}" for v in ticks])
        ax.set_title(
            f"Launch close-up, first {self.window:.0f} s (altitude log above 100 m)",
            fontsize=FONT_LABEL_PT,
            loc="left",
            color=ANIMATION_TEXT_COLOR,
            pad=3,
        )
        ax.set_xlabel("T, time after release [s]", fontsize=FONT_LABEL_PT, labelpad=1.0)
        ax.set_ylabel("altitude [m]", fontsize=FONT_LABEL_PT, labelpad=1.0)
        ax.axhspan(y_lo, 0.0, color=ANIMATION_GROUND_COLOR, zorder=0, linewidth=0)
        ax.axhline(0.0, color=ANIMATION_MUTED_COLOR, linewidth=0.8, zorder=1)
        ax.axhline(
            CLOSEUP_LINTHRESH_M,
            color=ANIMATION_MUTED_COLOR,
            linewidth=0.7,
            linestyle=":",
            zorder=1,
        )
        ax.text(
            0.99,
            CLOSEUP_LINTHRESH_M,
            "log scale above",
            transform=blended_transform_factory(ax.transAxes, ax.transData),
            fontsize=FONT_EVENT_PT,
            color=ANIMATION_MUTED_COLOR,
            ha="right",
            va="bottom",
        )
        ax.annotate(
            "below ground" + (": assist shaft" if alt_min < 0.0 else ""),
            (0.99, 0.0),
            xycoords=blended_transform_factory(ax.transAxes, ax.transData),
            xytext=(0.0, -2.0),
            textcoords="offset points",
            fontsize=FONT_EVENT_PT,
            color=ANIMATION_MUTED_COLOR,
            ha="right",
            va="top",
        )
        self._hold_spans()
        self.close_trails, self.close_heads = [], []
        for i in range(len(self.runs)):
            color, dash, _ = self._style(i)
            (trail,) = ax.plot([], [], color=color, linestyle=dash, linewidth=1.6)
            self.close_trails.append(trail)
            self.close_heads.append(self._head(ax, i, ANIMATION_MARKER_SIZE - 1.0))
        self.close_cursor = ax.axvline(self.t0, color=ANIMATION_MUTED_COLOR, linewidth=0.8)

    def _hold_spans(self) -> None:
        """Hatch each run's hold-down span on the close-up, from the ground up, and name it
        with a vertical 'hold-down' note inside the span, in the run's text colour (runs
        with the same span share one note, in the neutral colour)."""
        ax = self.ax_close
        spans: dict[tuple[float, float], list[int]] = {}
        for i, run in enumerate(self.runs):
            held = run.t_s[run.phase == HOLD_KIND]
            if held.size and held[-1] > held[0]:
                spans.setdefault((float(held[0]), float(held[-1])), []).append(i)
                ax.fill_between(
                    [held[0], held[-1]],
                    0.0,
                    CLOSEUP_TOP_M,
                    facecolor=ANIMATION_HOLD_COLOR,
                    edgecolor=self._style(i)[0],
                    hatch="///",
                    linewidth=0,
                    alpha=0.6,
                    zorder=0,
                )
        ground = float(ax.transAxes.inverted().transform(ax.transData.transform((0.0, 0.0)))[1])
        for (start, end), members in spans.items():
            ax.text(
                0.5 * (start + end),
                0.5 * (ground + 1.0),
                "hold-down",
                transform=blended_transform_factory(ax.transData, ax.transAxes),
                rotation=90.0,
                fontsize=FONT_EVENT_PT,
                color=self._text_color(members[0]) if len(members) == 1 else ANIMATION_TEXT_COLOR,
                ha="center",
                va="center",
                zorder=5,
                bbox={"boxstyle": "round,pad=0.12", "facecolor": "white", "lw": 0},
            )

    def _small_axes(self) -> None:
        """|v_rel| [m/s], felt axial [g0] and q [kPa] against the time after release over
        the whole flight, with trails, markers and a cursor."""
        panels = (
            ("|v_rel| [m/s]", "speed_rel_mps", 1.0),
            ("felt axial [g]", "felt_axial_g", 1.0),
            ("q [kPa]", "q_pa", float(pa_to_kpa(1.0))),
        )
        self.small_series: list[tuple[str, float]] = []
        self.small_trails: list[list[Any]] = []
        self.small_heads: list[list[Any]] = []
        self.small_cursors: list[Any] = []
        margin = SMALL_PANEL_XMARGIN * (self.t1 - self.t0)
        for ax, (label, column, scale) in zip(self.ax_small, panels, strict=True):
            _style_axes(ax)
            ax.set_xlim(self.t0, self.t1 + margin)
            top = max(float(np.nanmax(getattr(r, column))) for r in self.runs) * scale
            low = min(0.0, min(float(np.nanmin(getattr(r, column))) for r in self.runs))
            ax.set_ylim(low * scale, 1.15 * top if top > 0 else 1.0)
            ax.set_ylabel(_plot_text(label), fontsize=FONT_SMALL_PT, labelpad=1.0)
            ax.yaxis.set_major_locator(MaxNLocator(3))
            trails, heads = [], []
            for i, run in enumerate(self.runs):
                color, dash, _ = self._style(i)
                values = getattr(run, column) * scale
                ax.plot(run.t_s, values, color=color, linewidth=0.6, linestyle=dash, alpha=0.25)
                (trail,) = ax.plot([], [], color=color, linestyle=dash, linewidth=1.3)
                trails.append(trail)
                heads.append(self._head(ax, i, ANIMATION_MARKER_SIZE - 2.5))
            self.small_series.append((column, scale))
            self.small_trails.append(trails)
            self.small_heads.append(heads)
            self.small_cursors.append(
                ax.axvline(self.t0, color=ANIMATION_MUTED_COLOR, linewidth=0.8)
            )
        for ax in self.ax_small[:-1]:
            ax.tick_params(labelbottom=False)
        self.ax_small[-1].set_xlabel(
            "T, time after release [s]", fontsize=FONT_LABEL_PT, labelpad=1.0
        )

    def _readout_setup(self) -> None:
        """The per-run readout block in the ground band of the trajectory panel."""
        ax = self.ax_main
        n = len(self.runs)
        line_h, x0, y0 = READOUT_LINE_H, READOUT_X0, READOUT_Y0
        ax.add_patch(
            Rectangle(
                (x0 - 0.04, y0 - READOUT_BOX_PAD[0]),
                1.0 - x0 + 0.035,
                _readout_top(n) - (y0 - READOUT_BOX_PAD[0]),
                transform=ax.transAxes,
                facecolor="white",
                edgecolor=PLOT_GRID_COLOR,
                alpha=0.94,
                zorder=6,
            )
        )
        name_col = READOUT_NAME_CHARS + 1
        header = f"{'run':<{name_col}}{'T [s]':>7} {'phase':<14}{'altitude':>10}{'|v_rel|':>10}"
        ax.text(
            x0,
            y0 + line_h * n,
            header + f"{'mass':>8}",
            transform=ax.transAxes,
            family="monospace",
            fontsize=FONT_READOUT_PT - 0.5,
            color=ANIMATION_MUTED_COLOR,
            va="bottom",
            zorder=7,
        )
        self.readouts = []
        for i in range(n):
            color, _, marker = self._style(i)
            y = y0 + line_h * (n - 1 - i)
            ax.plot(
                [x0 - 0.02],
                [y + 0.02],
                marker=marker,
                color=color,
                markeredgecolor="black",
                markeredgewidth=0.5,
                markersize=5.5,
                transform=ax.transAxes,
                zorder=7,
                clip_on=False,
            )
            text = ax.text(
                x0,
                y,
                "",
                transform=ax.transAxes,
                family="monospace",
                fontsize=FONT_READOUT_PT,
                color=ANIMATION_TEXT_COLOR,
                va="bottom",
                zorder=7,
            )
            self.readouts.append(text)

    def _event_value(
        self, run: AnimationRun, ev: AnimationEvent, early: bool
    ) -> tuple[str | None, str]:
        """(value text, unit) an event label shows for one run: the release speed
        [m/s], the push's peak felt axial g at push start, the altitude [km] of an event
        on the trajectory panel; (None, '') otherwise."""
        if ev.label == EVENT_LABELS["release"] and math.isfinite(ev.speed_rel_mps):
            return f"{ev.speed_rel_mps:.1f}", " m/s"
        if ev.label == EVENT_LABELS["push_start"]:
            peak = run.push_peak_g()
            return (None, "") if peak is None else (f"{peak:.1f}", " g")
        if not early:
            return f"{float(m_to_km(ev.alt_m)):.1f}", " km"
        return None, ""

    def _layout_events(self) -> None:
        """Create every run's event markers (hollow, run-styled) and the event labels,
        hidden until their time: events up to the knee on the close-up (T [s], altitude
        [m]), later ones on the trajectory [km]. Copies of one event of several runs
        share one label listing each run's value behind its marker glyph."""
        width, height = self.fig.bbox.width, self.fig.bbox.height
        self.event_marks: list[tuple[float, Any]] = []
        groups: list[_LabelGroup] = []
        for i, run in enumerate(self.runs):
            color, _, marker = self._style(i)
            for ev in run.events:
                early = ev.t_s <= self.window
                ax = self.ax_close if early else self.ax_main
                x = ev.t_s if early else float(m_to_km(ev.downrange_m))
                y = ev.alt_m if early else float(m_to_km(ev.alt_m))
                (mark,) = ax.plot(
                    [x],
                    [y],
                    marker=marker,
                    markersize=ANIMATION_EVENT_MARKER_SIZE,
                    markerfacecolor="white",
                    markeredgecolor=color,
                    markeredgewidth=1.2,
                    linestyle="none",
                    zorder=6,
                    visible=False,
                )
                self.event_marks.append((ev.t_s, mark))
                value, unit = self._event_value(run, ev, early)
                px_x, px_y = (float(v) for v in ax.transData.transform((x, y)))
                group = next(
                    (
                        g
                        for g in groups
                        if g.ax is ax
                        and g.label == ev.label
                        and abs(g.px_y - px_y) < LABEL_MERGE_Y * height
                        and (
                            abs(g.x - x) <= LABEL_MERGE_DT_S
                            if early
                            else abs(g.px_x - px_x) < LABEL_MERGE_X * width
                        )
                    ),
                    None,
                )
                if group is None:
                    group = _LabelGroup(ax, ev.label, unit, x, y, px_x, px_y)
                    groups.append(group)
                group.members.append((i, ev.t_s, value))
        self.label_groups = groups
        self._place_labels(groups)

    def _place_labels(self, groups: list[_LabelGroup]) -> None:
        """Create the label annotations. Close-up events before TIMELINE_LAUNCH_END_S (a
        cluster within a few seconds) are listed in the ground band from CALLOUT_T_S,
        highest point first, with leader lines; other close-up labels sit above-left of
        their point (above the rising curves, behind the moving markers); trajectory
        labels sit right of their point (under the rising path) or, near the right end,
        above-left. A label that would overlap an earlier one on its panel moves a label
        step away from it (to the side of its own point) and gets a leader line."""
        width = self.fig.bbox.width
        step = LABEL_STACK_PT * self.fig.dpi / POINTS_PER_INCH
        callouts = sorted(
            (g for g in groups if g.ax is self.ax_close and g.x < TIMELINE_LAUNCH_END_S),
            key=lambda g: (-g.y, g.x),
        )
        x_px, ground_px = (float(v) for v in self.ax_close.transData.transform((CALLOUT_T_S, 0.0)))
        for k, g in enumerate(callouts):
            row_px = ground_px - (k + CALLOUT_FIRST_ROW) * step
            self._annotate(g, (x_px, row_px), "figure pixels", ("left", "center"), leader=True)
        placed: list[tuple[Any, float, float]] = []
        for g in groups:
            if g in callouts:
                continue
            frac_x = (g.px_x - g.ax.bbox.x0) / g.ax.bbox.width
            right = g.ax is self.ax_main and frac_x <= LABEL_LEFT_BEYOND
            y = g.px_y
            clash = [
                ly
                for a, lx, ly in placed
                if a is g.ax and abs(lx - g.px_x) < LABEL_NEAR_X * width and abs(ly - y) < step
            ]
            while clash:  # move away from the clashing label, on the side of this point
                away = 1.0 if g.px_y >= clash[0] else -1.0
                y = clash[0] + away * step
                clash = [
                    ly
                    for a, lx, ly in placed
                    if a is g.ax
                    and abs(lx - g.px_x) < LABEL_NEAR_X * width
                    and abs(ly - y) < step - 1e-6
                ]
            placed.append((g.ax, g.px_x, y))
            shift_pt = (y - g.px_y) * POINTS_PER_INCH / self.fig.dpi
            leader = abs(shift_pt) > 0.0
            if right:
                self._annotate(g, (10.0, shift_pt), "offset points", ("left", "center"), leader)
            else:
                self._annotate(
                    g, (-5.0, 5.0 + shift_pt), "offset points", ("right", "bottom"), leader
                )

    def _annotate(
        self,
        g: _LabelGroup,
        xytext: tuple[float, float],
        textcoords: str,
        align: tuple[str, str],
        leader: bool,
    ) -> None:
        """The hidden annotation of label group ``g`` (text set per frame): run-coloured
        for a single run's event, neutral when it lists several runs."""
        color = self._text_color(g.members[0][0]) if len(g.members) == 1 else ANIMATION_TEXT_COLOR
        g.artist = g.ax.annotate(
            "",
            (g.x, g.y),
            xytext=xytext,
            textcoords=textcoords,
            ha=align[0],
            va=align[1],
            arrowprops=(
                {
                    "arrowstyle": "-",
                    "color": ANIMATION_MUTED_COLOR,
                    "lw": 0.6,
                    "shrinkA": 1.0,
                    "shrinkB": 2.5,
                }
                if leader
                else None
            ),
            fontsize=FONT_EVENT_PT,
            color=color,
            zorder=7,
            bbox={"boxstyle": "round,pad=0.12", "facecolor": "white", "alpha": 0.85, "lw": 0},
            visible=False,
        )

    def _group_text(self, g: _LabelGroup, shown: list[tuple[int, float, str | None]]) -> str:
        """Text of label group ``g`` with the members that have happened: one run's
        event reads '<glyph> <label> (<value><unit>)'; several runs' copies read
        '<label> (<glyph> <value>  <glyph> <value><unit>)' in run order. The glyph is
        left out when the animation shows one run."""
        many = len(self.runs) > 1
        if len(g.members) == 1:
            i, _, value = shown[0]
            head = f"{self._glyph(i)} {g.label}" if many else g.label
            return head if value is None else f"{head} ({value}{g.unit})"
        if all(value is None for _, _, value in shown):
            return f"{g.label} ({' '.join(self._glyph(i) for i, _, _ in shown)})"
        parts = "  ".join(
            f"{self._glyph(i)} {'n/a' if value is None else value}" for i, _, value in shown
        )
        return f"{g.label} ({parts}{g.unit})"

    def _draw_events(self, t: float) -> None:
        """Show the event markers and labels of the events that have happened by ``t``."""
        for t_ev, mark in self.event_marks:
            mark.set_visible(t_ev <= t)
        for g in self.label_groups:
            shown = [m for m in g.members if m[1] <= t]
            g.artist.set_visible(bool(shown))
            if shown:
                g.artist.set_text(_plot_text(self._group_text(g, shown)))

    def _readout(self, i: int, run: AnimationRun, t: float) -> str:
        """One readout line: name, T [s] (held at the run's end), phase, altitude,
        |v_rel| [m/s], mass [t]."""
        alt = _fmt_alt(_state(run, t, run.alt_m))
        v = _state(run, t, run.speed_rel_mps)
        m_t = float(kg_to_t(_state(run, t, run.m_kg)))
        name = self.names[i]
        return (
            f"{name:<{READOUT_NAME_CHARS + 1}}{signed(min(t, run.t_end_s)):>7} "
            f"{_phase_at(run, t)[:13]:<14}{alt:>10}{v:>6.0f} m/s{m_t:>6.1f} t"
        )

    def draw_frame(self, t: float, speed: float) -> None:
        """Move every artist to the time after release ``t`` [s]; ``speed`` is the
        nominal playback speed (flight s per video s; 0 marks the end hold)."""
        self.clock.set_text(f"T {signed(t)} s")
        self.speed.set_text(playback_label(0.0 if t >= self.t1 else speed, t))
        for i, run in enumerate(self.runs):
            started = t >= run.t_start_s
            dr_km, alt_km = m_to_km(run.downrange_m), m_to_km(run.alt_m)
            self.main_trails[i].set_data(*_trail(run, t, dr_km, alt_km))
            self.main_heads[i].set_data([_state(run, t, dr_km)], [_state(run, t, alt_km)])
            self.main_heads[i].set_visible(started)
            t_head = min(t, run.t_end_s)
            self.close_trails[i].set_data(*_trail(run, t, run.t_s, run.alt_m))
            self.close_heads[i].set_data([t_head], [_state(run, t, run.alt_m)])
            self.close_heads[i].set_visible(started)
            for p, (column, scale) in enumerate(self.small_series):
                values = getattr(run, column) * scale
                self.small_trails[p][i].set_data(*_trail(run, t, run.t_s, values))
                self.small_heads[p][i].set_data([t_head], [_state(run, t, values)])
                self.small_heads[p][i].set_visible(started)
            self.readouts[i].set_text(self._readout(i, run, t))
        self.close_cursor.set_xdata([t, t])
        self.close_cursor.set_visible(t <= self.window)
        for cursor in self.small_cursors:
            cursor.set_xdata([t, t])
        self._draw_events(t)


def write_ascent_animation(
    run_dir: Path,
    runs: Sequence[str] | None,
    out_path: Path | None,
    *,
    fps: int = ANIMATION_DEFAULT_FPS,
    seconds: float = ANIMATION_DEFAULT_SECONDS,
    width: int = ANIMATION_DEFAULT_WIDTH_PX,
) -> Path:
    """Write an animation of planar_2d runs of one results directory; return its path.

    Inputs: ``run_dir``, a results directory results/<experiment>/<timestamp> of a
    planar_2d experiment (metrics.json, resolved_config.yaml, <run>/timeseries.csv and
    <run>/events.csv; read only); ``runs``, run names (None: the baseline plus up to
    three variants, in summary order); ``out_path``, the .mp4 (ffmpeg) or .gif (Pillow)
    to write (None: ``default_animation_path`` in the current directory, never inside
    results/); ``fps`` [frames per video second; a .gif plays at
    ``animation_playback_fps``, its delays being whole 10 ms steps]; ``seconds``, the
    video length [s]; ``width``, the frame width [px] (even; the frame is 16:9).

    Output: the path written. Each frame shows altitude [km] against downrange [km] per
    run (trail, moving marker, events as they happen, labelled with each run's value),
    a launch close-up of altitude [m] against the time after release [s] (an assist
    push below ground, the pad's hold-down), the Earth-relative speed [m/s], felt axial
    acceleration [g0] and dynamic pressure [kPa] against time with a cursor, a per-run
    readout (time after release, phase, altitude, speed, mass), each run's payload
    capacity P* [kg] from metrics.json in the legend (for a run of the offload block, its
    payload and offload from metrics.json ``offload``: ``offload_tag``) and the model's
    caveats in a footnote. Time follows ``ascent_time_map`` (launch at about real time, the close-up
    faster, the rest fast, a short hold at the end) and the current playback speed is
    shown; each run is interpolated on the frame times and a run that ends earlier holds
    its last state. Raises AnimationError for a non-planar directory, unknown runs, a
    bad output or setting, or ffmpeg failing while encoding.
    """
    run_dir = Path(run_dir)
    selected, metrics = load_animation_runs(run_dir, runs)
    out = default_animation_path(run_dir, Path.cwd()) if out_path is None else Path(out_path)
    check_animation_out(out, run_dir)
    play_fps = animation_playback_fps(fps, out.suffix)
    n_frames = animation_frame_count(play_fps, seconds)
    size_in, dpi, _ = frame_geometry(width)
    t0 = min(r.t_start_s for r in selected)
    t1 = max(r.t_end_s for r in selected)
    times = ascent_time_map(t0, t1, n_frames)
    speeds = playback_speeds(t0, t1, n_frames, play_fps)
    config = run_data.read_yaml(run_dir / run_data.CONFIG_FILE)
    vehicle = (config.get("vehicle") or {}).get("name")
    figure = _AscentFigure(selected, metrics, vehicle, size_in, dpi)
    writer: FFMpegWriter | PillowWriter
    if out.suffix.lower() == ".mp4":
        writer = FFMpegWriter(
            fps=fps,
            codec="h264",
            extra_args=["-pix_fmt", "yuv420p", "-crf", str(MP4_CRF), "-movflags", "+faststart"],
        )
    else:
        writer = PillowWriter(fps=fps)
    try:
        with writer.saving(figure.fig, str(out), dpi):
            for t, speed in zip(times, speeds, strict=True):
                figure.draw_frame(float(t), float(speed))
                writer.grab_frame(facecolor="white")
    except (subprocess.CalledProcessError, BrokenPipeError) as exc:
        raise AnimationError(f"ffmpeg failed while writing {out}: {exc}") from exc
    return out
