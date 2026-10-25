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
import re
import subprocess
import textwrap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.animation import FFMpegWriter, PillowWriter
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import Bbox, blended_transform_factory, offset_copy
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
from launchsim.phases.prelude import RELEASE_SPEED_NOT_REACHED
from launchsim.replay import EXPLORATORY_CAVEAT, EXPLORATORY_LABEL, penalty_added_kg
from launchsim.structure import (
    ENTRY_AFT_RING,
    ENTRY_THRUST_STRUCTURE,
    FLAG_RELEASE_UNLOAD,
    STAGE1,
    STAGE2,
)
from launchsim.summary import (
    STRUCTURE_PAYLOAD_RECORD_KIND,
    release_flag_comparison_short,
    structure_axis_departures,
    structure_charged,
    structure_layer_label,
    structure_row_departures,
    structure_run_record,
)
from launchsim.units import (
    kg_to_t,
    m_to_km,
    m_to_mm,
    n_to_mn,
    pa_to_kpa,
    rad_to_deg,
    to_percent,
    w_to_mw,
)

if TYPE_CHECKING:
    from launchsim.sim import Result
    from launchsim.structure import Increment


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
    drive_power), each against the time since release (PLOT_ABSCISSA), and for a
    linear-motor run its force-against-speed figure (``write_drive_curve``, SP7 step
    S4a; no other run gains a file). A panel with
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
    curve = write_drive_curve(result, plots_dir, prefix, "v_mps")
    if curve is not None:
        written.append(curve)
    return written


# ------------------------------------------------- linear-motor drive curve (SP7 S4a)

DRIVE_CURVE_QUANTITY = "drive_curve"
"""The quantity suffix of a linear-motor run's force-against-speed figure:
plots/<run>_drive_curve.png (``write_drive_curve``; SP7 step S4a). Written for a
linear-motor run only (its metrics carry ``push_force_max_N``), never for constant_accel
or a pad, so no existing run's plot list changes."""
DRIVE_CURVE_FIGSIZE_IN = (6.4, 5.0)
DRIVE_CURVE_FORCE_COLOR = PLOT_SERIES_COLOR
DRIVE_CURVE_POWER_COLOR = "#d6742a"
DRIVE_CURVE_LIMIT_COLOR = "#555555"
DRIVE_CURVE_ENVELOPE_COLOR = "#9a9a9a"
DRIVE_CURVE_LIMIT_STYLE = "--"
DRIVE_CURVE_SPEED_STYLE = ":"
DRIVE_CURVE_ENVELOPE_STYLE = "-."
DRIVE_CURVE_LIMIT_WIDTH = 1.2
DRIVE_CURVE_MARKER_SIZE = 3.0
DRIVE_CURVE_LEGEND_FONT = 7.5
DRIVE_CURVE_LEGEND_COLUMNS = 2
DRIVE_CURVE_TITLE_FONT = 10.0
"""The drive-curve figure's style (``drive_curve_figure``; display only, none of them a
model number): DRIVE_CURVE_FIGSIZE_IN its (width, height) [in]; the colours (matplotlib
colour strings) of the force curve (the panels' series colour), the power curve, the
F_max and P_max limit lines and the power-cap envelope P_max / sdot; the matplotlib line
styles of the limit lines, the corner and release speed lines and the envelope;
DRIVE_CURVE_LIMIT_WIDTH the limit lines' width [pt]; DRIVE_CURVE_MARKER_SIZE the sampled
rows' marker size [pt]; DRIVE_CURVE_LEGEND_FONT and DRIVE_CURVE_TITLE_FONT the legend and
title font sizes [pt]; DRIVE_CURVE_LEGEND_COLUMNS the legend's columns (fix round 2,
C2-m4)."""
DRIVE_CURVE_LEGEND_BAND = 0.2
"""Share of the figure's height below the axes kept for the legend (fix round 1, V4: the
legend sits under the axes, so no curve or vertical line runs through it)."""
DRIVE_CURVE_FORCE_HEADROOM = 1.25
"""Top of the force axis as a multiple of F_max (``DRIVE_CURVE_POWER_HEADROOM`` says
why it differs from the power axis's)."""
DRIVE_CURVE_POWER_HEADROOM = 1.6
"""Tops of the force and power axes as multiples of F_max and P_max: distinct, so the two
dashed limit lines never sit at one height on the independently scaled twin axes (fix
round 1, V5); every flown force is <= F_max and every flown power <= P_max (D-SP7-50)."""
DRIVE_CURVE_X_MARGIN = 1.05
"""The speed axis runs to this multiple of the largest speed drawn (the push's, a set
release speed, the corner speed)."""
DRIVE_CURVE_ENVELOPE_POINTS = 200
"""Points of the drawn power-cap curve P_max / sdot above the corner speed."""


def drive_curve_rows(result: Result, speed_column: str) -> tuple[Any, Any, Any] | None:
    """(speed [m/s], drive force [N], drive power [W]) of a linear-motor run's sampled
    ASSIST rows (every sample_dt_s plus every sub-phase end: the rise's end, each watch
    crossing and the release), or None for any other run (no ``push_force_max_N`` in its
    metrics, no ASSIST row, or no ``speed_column``). The speed is the time series' own
    column (``v_mps`` 1-D, ``speed_rel_mps`` planar), which equals the speed along the
    track sdot on the vertical track both release maps require; the force and power are
    the recorded ``drive_force_N`` and ``drive_power_W`` (P = F sdot)."""
    if _finite_number(result.metrics.get("push_force_max_N")) is None:
        return None
    frame = result.timeseries
    if frame.empty or "phase" not in frame.columns or speed_column not in frame.columns:
        return None
    rows = frame[frame["phase"] == ASSIST_KIND]
    if rows.empty:
        return None
    return (
        np.abs(rows[speed_column].to_numpy(dtype=float)),
        rows["drive_force_N"].to_numpy(dtype=float),
        rows["drive_power_W"].to_numpy(dtype=float),
    )


def _finite_number(value: Any) -> float | None:
    """value as a float when it is a finite real number (not a bool), else None."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    x = float(value)
    return x if math.isfinite(x) else None


def drive_curve_figure(result: Result, prefix: str, speed_column: str) -> Figure | None:
    """The force-against-speed figure of a linear-motor run (SP7 step S4a; design 6.1's
    force-against-speed figure): the recorded drive force [MN] (left axis) and drive
    power [MW] (right axis) against the speed along the track [m/s] over the push
    (``drive_curve_rows``), with F_max and P_max as dashed lines on their axes (axis tops
    at DRIVE_CURVE_FORCE_HEADROOM F_max and DRIVE_CURVE_POWER_HEADROOM P_max, so the two
    lines never coincide), the power cap on the force P_max / sdot above the corner
    speed (dash-dot), the corner speed P_max/F_max as a dotted vertical line (where the
    cap meets F_max; the acceleration law's command meets it at P_max / F_cmd), and a
    set release speed as a dashed one, labelled '(not reached)' when the push released at
    the track end below it (the run's ``prelude.RELEASE_SPEED_NOT_REACHED`` flag), 'set
    ... (no release: status <status>)' when the push never released (no
    ``release_trigger``: a stall or a stop on the track; fix round 4, V4-3). The
    title (two lines: the run and its law, then what is drawn) and the legend (under the
    axes) stay inside the figure. Settings from the run's metrics (push_force_max_N,
    push_power_max_W, push_corner_speed_mps, push_control_law, push_release_speed_mps)
    and flags. None for any other run."""
    rows = drive_curve_rows(result, speed_column)
    if rows is None:
        return None
    speed, force, power = rows
    m = result.metrics
    f_max = float(m["push_force_max_N"])
    p_max = _finite_number(m.get("push_power_max_W"))
    corner = _finite_number(m.get("push_corner_speed_mps"))
    v_release = _finite_number(m.get("push_release_speed_mps"))
    law = m.get("push_control_law")
    fig = Figure(figsize=DRIVE_CURVE_FIGSIZE_IN, dpi=PLOT_DPI)
    ax = fig.subplots()
    twin = ax.twinx()
    handles: list[Any] = []
    (h,) = ax.plot(
        speed,
        n_to_mn(force),
        color=DRIVE_CURVE_FORCE_COLOR,
        linewidth=PLOT_LINE_WIDTH,
        marker="o",
        markersize=DRIVE_CURVE_MARKER_SIZE,
        label="drive force F (sampled rows)",
    )
    handles.append(h)
    (h,) = twin.plot(
        speed,
        w_to_mw(power),
        color=DRIVE_CURVE_POWER_COLOR,
        linewidth=PLOT_LINE_WIDTH,
        marker="o",
        markersize=DRIVE_CURVE_MARKER_SIZE,
        label="drive power P = F sdot (sampled rows)",
    )
    handles.append(h)
    handles.append(
        ax.axhline(
            float(n_to_mn(f_max)),
            color=DRIVE_CURVE_FORCE_COLOR,
            linestyle=DRIVE_CURVE_LIMIT_STYLE,
            linewidth=DRIVE_CURVE_LIMIT_WIDTH,
            label=f"F_max = {float(n_to_mn(f_max)):.4g} MN",
        )
    )
    if p_max is not None:
        handles.append(
            twin.axhline(
                float(w_to_mw(p_max)),
                color=DRIVE_CURVE_POWER_COLOR,
                linestyle=DRIVE_CURVE_LIMIT_STYLE,
                linewidth=DRIVE_CURVE_LIMIT_WIDTH,
                label=f"P_max = {float(w_to_mw(p_max)):.5g} MW",
            )
        )
    x_top = max([float(np.max(speed)), *(v for v in (v_release, corner) if v is not None)])
    x_top *= DRIVE_CURVE_X_MARGIN
    if p_max is not None and corner is not None and corner < x_top:
        v_cap = np.linspace(corner, x_top, DRIVE_CURVE_ENVELOPE_POINTS)
        (h,) = ax.plot(
            v_cap,
            n_to_mn(p_max / v_cap),
            color=DRIVE_CURVE_ENVELOPE_COLOR,
            linestyle=DRIVE_CURVE_ENVELOPE_STYLE,
            linewidth=DRIVE_CURVE_LIMIT_WIDTH,
            label="power cap on the force P_max / sdot",
        )
        handles.append(h)
    if corner is not None:
        handles.append(
            ax.axvline(
                corner,
                color=DRIVE_CURVE_LIMIT_COLOR,
                linestyle=DRIVE_CURVE_SPEED_STYLE,
                linewidth=DRIVE_CURVE_LIMIT_WIDTH,
                label=f"corner speed P_max/F_max = {corner:.4g} m/s (cap meets F_max)",
            )
        )
    if v_release is not None:
        missed = any(str(f).startswith(RELEASE_SPEED_NOT_REACHED) for f in result.flags)
        if m.get("release_trigger") is None:  # never released (fix round 4, V4-3)
            label = f"release speed set {v_release:g} m/s (no release: status {result.status})"
        elif missed:
            label = f"release speed {v_release:g} m/s (not reached)"
        else:
            label = f"release speed {v_release:g} m/s"
        handles.append(
            ax.axvline(
                v_release,
                color=DRIVE_CURVE_LIMIT_COLOR,
                linestyle=DRIVE_CURVE_LIMIT_STYLE,
                linewidth=DRIVE_CURVE_LIMIT_WIDTH,
                label=label,
            )
        )
    ax.set_xlabel("speed along the track sdot [m/s]")
    ax.set_ylabel("drive force F [MN]", color=DRIVE_CURVE_FORCE_COLOR)
    twin.set_ylabel("drive power P [MW]", color=DRIVE_CURVE_POWER_COLOR)
    ax.set_xlim(0.0, x_top)
    ax.set_ylim(0.0, float(n_to_mn(f_max)) * DRIVE_CURVE_FORCE_HEADROOM)
    if p_max is not None:
        twin.set_ylim(0.0, float(w_to_mw(p_max)) * DRIVE_CURVE_POWER_HEADROOM)
    else:
        twin.set_ylim(bottom=0.0)
    ax.grid(True, color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
    ax.spines["top"].set_visible(False)
    twin.spines["top"].set_visible(False)
    what = f"{law} law" if isinstance(law, str) else "law unknown"
    ax.set_title(
        _plot_text(f"{prefix} ({what})\nlinear-motor drive force and power against speed"),
        fontsize=DRIVE_CURVE_TITLE_FONT,
    )
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=DRIVE_CURVE_LEGEND_COLUMNS,
        frameon=False,
        fontsize=DRIVE_CURVE_LEGEND_FONT,
    )
    fig.tight_layout(rect=(0.0, DRIVE_CURVE_LEGEND_BAND, 1.0, 1.0))
    return fig


def write_drive_curve(
    result: Result, plots_dir: Path, prefix: str, speed_column: str
) -> Path | None:
    """Write plots/<plot_stem(prefix, DRIVE_CURVE_QUANTITY)>.png, the
    ``drive_curve_figure`` of a linear-motor run, and return its path; None (nothing
    written) for any other run. speed_column: the time series' speed column (``v_mps``
    1-D, ``speed_rel_mps`` planar)."""
    fig = drive_curve_figure(result, prefix, speed_column)
    if fig is None:
        return None
    plots_dir.mkdir(parents=True, exist_ok=True)
    path = plots_dir / f"{plot_stem(prefix, DRIVE_CURVE_QUANTITY)}.png"
    fig.savefig(path, format="png")
    return path


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
    group gets a twin y axis; a linear-motor run adds its force-against-speed figure
    (``write_drive_curve``, SP7 step S4a; no other run gains a file). Nothing is written
    for an empty time series (a failed search)."""
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
    curve = write_drive_curve(result, plots_dir, prefix, "speed_rel_mps")
    if curve is not None:
        written.append(curve)
    return written


# ------------------------------------------------------------ structure figure (SP7 S3b)

STRUCTURE_FIGURE_QUANTITY = "structure"
"""The quantity suffix of a structural run's figure: plots/<run>_structure.png."""
STRUCTURE_FIGSIZE_IN = (9.0, 9.4)
STRUCTURE_HEIGHT_RATIOS = (2.0, 1.25)
"""The top (thickness) and bottom (dm) panels' height ratio."""
STRUCTURE_CAPTION_XY = (0.01, 0.005)
"""The caption's anchor in figure fraction (bottom left)."""
STRUCTURE_CAPTION_GAP = 0.015
"""The gap [figure fraction] between the caption's measured top and the rectangle
tight_layout lays the panels in (``_layout_rect``), so a longer caption (a payload case, a
scaled case, a wrapped line) pushes the panels up instead of running under the dm panel's
axis label."""
STRUCTURE_CAPTION_WRAP_CHARS = 150
"""Each caption line is wrapped at this many characters (``_structure_caption``), the
continuation indented by STRUCTURE_CAPTION_INDENT: at STRUCTURE_FONT_CAPTION_PT on the
9-in figure about 174 characters reach the right edge (measured in S3b's third review), so
no line is clipped there."""
STRUCTURE_CAPTION_INDENT = "    "
STRUCTURE_ENVELOPE_COLOR = "#444444"
STRUCTURE_STAGE_COLORS: dict[str, str] = {STAGE1: PLOT_SERIES_COLOR, STAGE2: "#d6742a"}
STRUCTURE_MODE_MARKERS: dict[str, tuple[str, str]] = {
    "ring_common_z": ("#3a9e5c", "o"),
    "ring_common_y": ("#6b8e23", "p"),
    "ring_improved_z": ("#9c2f6b", "<"),
    "ring_improved_y": ("#a0522d", ">"),
    "plate_limited": ("#d1409a", "X"),
    "monocoque": ("#8c8c00", "D"),
    "membrane": ("#8a4fbf", "s"),
    "combined": ("#c23b3b", "^"),
    "hoop": ("#1f9e9e", "v"),
    "min_gauge": ("#7a4a1f", "P"),
}
"""Colour and marker shape of each governing mode's markers, keyed by the model's mode
name (the Gerard rows and the plate-limited row, monocoque, membrane, combined, hoop, the
minimum gauge), so a mode keeps its colour and shape across every figure of a results
directory; STRUCTURE_MODE_MARKER_UNKNOWN for a name not listed. A palette disjoint from
STRUCTURE_STAGE_COLORS, each mode with its own shape."""
STRUCTURE_MODE_MARKER_UNKNOWN: tuple[str, str] = ("#333333", "*")
STRUCTURE_MARKER_SIZE = 16.0
"""The governing-mode markers' area [pt^2]."""
STRUCTURE_MARKER_SPACING_PX = 20.0
"""The least spacing [px] between two marked stations of a barrel: a denser barrel is
marked at every k-th station (``_marked_stations``), plus every station where the
governing mode switches and both ends, so at least a marker's width of push line shows
between two marks (the markers are about 7 px wide)."""
STRUCTURE_PUSH_LINE_WIDTH = 1.6
STRUCTURE_PUSH_ALPHA = 0.9
STRUCTURE_ENVELOPE_LINE_WIDTH = 1.2
STRUCTURE_POINT_ENVELOPE_PT = 5.5
"""Marker size [pt] of a dome's or the tube's hollow envelope square (drawn on top of the
push point with a thin edge, so it shows when the two values coincide)."""
STRUCTURE_POINT_ENVELOPE_EDGE_PT = 0.9
STRUCTURE_POINT_PUSH_PT = 6.0
"""Marker size [pt] of a dome's or the tube's push point."""
STRUCTURE_POINT_DROP_LINE_WIDTH = 0.8
STRUCTURE_POINT_DROP_ALPHA = 0.7
"""The drop line joining a point element's envelope square to its push point (the stage
colour), so the pair reads as one element."""
STRUCTURE_COINCIDENT_OFFSET_PT = 5.0
"""How far [pt] two point elements at one station height (the aft dome and the tube) are
set apart in z on the page, so neither's square or point hides the other's."""
STRUCTURE_LEGEND_MARKER_PT = 5.0
STRUCTURE_FONT_POINT_LABEL_PT = 6.5
STRUCTURE_FONT_LABEL_PT = 7.5
STRUCTURE_FONT_CAPTION_PT = 7.0
STRUCTURE_FONT_AXIS_PT = 8.5
STRUCTURE_FONT_TITLE_PT = 10.0
STRUCTURE_FONT_INSET_PT = 7.5
STRUCTURE_LABEL_OFFSETS_PT: tuple[tuple[float, float], ...] = (
    (0.0, 7.0),
    (0.0, -7.0),
    (7.0, 7.0),
    (-7.0, 7.0),
    (7.0, -7.0),
    (-7.0, -7.0),
    (9.0, 0.0),
    (-9.0, 0.0),
    (0.0, 16.0),
    (0.0, -16.0),
    (12.0, 16.0),
    (-12.0, 16.0),
    (12.0, -16.0),
    (-12.0, -16.0),
    (0.0, 26.0),
    (0.0, -26.0),
    (16.0, 26.0),
    (-16.0, 26.0),
    (16.0, -26.0),
    (-16.0, -26.0),
)
"""The candidate offsets [pt] of an element label from its anchor, tried in order (above
and below first, then the diagonals and the sides, then farther out); the label is
aligned away from the anchor on the offset's side (``_place_label``)."""
STRUCTURE_BARREL_ANCHOR_FRACTIONS: tuple[float, ...] = (0.5, 0.3, 0.7, 0.15, 0.85)
"""Where along a barrel its label may be anchored, as fractions of its stations, tried in
order with the station of the push's maximum first (``_label_anchors``)."""
STRUCTURE_LABEL_PAD_PX = 4.0
"""The margin [px] around an element label's text taken as its box in the overlap test
(a line within it reads as touching the letters)."""
STRUCTURE_LABEL_FAR_FRACTIONS: tuple[float, ...] = (0.02, 0.26, 0.5, 0.74, 0.98)
"""The axes fractions, in x and in y, of the grid of far positions an element label may
take with a leader line when no offset beside its anchor is clear (``_far_candidates``;
the grid is tried nearest the anchor first)."""
STRUCTURE_LABEL_LEADER: dict[str, Any] = {
    "arrowstyle": "-",
    "linewidth": 0.6,
    "alpha": 0.7,
    "shrinkA": 1.0,
    "shrinkB": 3.0,
}
"""The leader line of an element label that found no clear spot beside its anchor and
sits at one of STRUCTURE_ANNOTATION_CANDIDATES instead (``_place_label``; the colour is
the label's)."""
STRUCTURE_DROP_LINE_SAMPLES = 6
"""How many points along a point element's drop line join the overlap test, so no label
is laid across it."""
STRUCTURE_LABEL_COSTS = (1, 100, 1000)
"""The cost of a label's box covering a drawn station or envelope point, overlapping a
placed label, and leaving its axes or covering the stage-2 inset, so a label over a few
stations is preferred to one over another label, and either to one off the axes."""
STRUCTURE_LEGEND_COLUMNS = 2
"""The legend's columns: two, so its self-contained entries fit the figure's width."""
STRUCTURE_LEGEND_ANCHOR = (0.5, -0.16)
"""The legend's anchor in axes fraction: centred under the top panel."""
STRUCTURE_LEGEND_ENVELOPE = "pad envelope, required wall (at the case's margin and cap)"
"""The legend's entry for the dashed envelope: a margin or a cap row's envelope is its
own (the pad's loads times 1 + margin, or capped), as the caption's envelope line says."""
STRUCTURE_LEGEND_POINT_PUSH = "push at a dome's crown or the tube (stage colour, on a drop line)"
STRUCTURE_LEGEND_POINT_ENVELOPE = "pad envelope at a dome's crown or the tube (hollow square)"
"""The legend's entry for a point element's envelope square: self-contained, since the
legend fills column-major and the entry need not follow the push point's."""
STRUCTURE_ANNOTATION_CANDIDATES: tuple[tuple[float, float, str, str], ...] = (
    (0.98, 0.96, "right", "top"),
    (0.02, 0.96, "left", "top"),
    (0.98, 0.04, "right", "bottom"),
    (0.02, 0.04, "left", "bottom"),
    (0.50, 0.96, "center", "top"),
    (0.50, 0.04, "center", "bottom"),
    (0.98, 0.25, "right", "center"),
    (0.02, 0.25, "left", "center"),
    (0.98, 0.50, "right", "center"),
    (0.02, 0.50, "left", "center"),
    (0.98, 0.75, "right", "center"),
    (0.02, 0.75, "left", "center"),
    (0.50, 0.25, "center", "center"),
    (0.50, 0.50, "center", "center"),
    (0.50, 0.75, "center", "center"),
)
"""Where the governing annotation may sit, in axes fraction with its alignment (the
corners first, then the mid positions): the first candidate whose box covers no drawn
station, no element label and not the stage-2 inset is taken (``_place_annotation``),
else the one with the smallest cost (STRUCTURE_ANNOTATION_COSTS)."""
STRUCTURE_ANNOTATION_COSTS = (1, 100, 1000)
"""The cost of the annotation's box covering a drawn station or envelope point, an
element label, and the stage-2 inset, so a box over a few stations is preferred to one
over a label, and any of them to one over the inset."""
STRUCTURE_ANNOTATION_PAD_PX = 6.0
"""The margin [px] around the annotation's text taken as its box (the rounded patch's
padding) when testing it against the drawn artists."""
STRUCTURE_ANNOTATION_ARROW: dict[str, Any] = {
    "arrowstyle": "->",
    "color": "#222222",
    "linewidth": 0.8,
}
STRUCTURE_TEXT_BOX: dict[str, Any] = {
    "boxstyle": "round,pad=0.3",
    "facecolor": "white",
    "alpha": 0.85,
    "edgecolor": "none",
}
"""The background of the governing annotation, so it stays legible over the grid."""
STRUCTURE_STAGE2_INSET_RECT = (0.56, 0.40, 0.42, 0.55)
"""The stage-2 inset's rectangle in the top panel's axes fraction (top right)."""
STRUCTURE_STAGE2_X_EXTENSION = 0.9
"""How far the top panel's z range is extended beyond stage 1's data, as a fraction of
that range, to leave the right part of the panel to the stage-2 inset (stage 1's data
then occupies the left 1/(1 + extension) of the width, under no inset)."""
STRUCTURE_INSET_FACE_ALPHA = 0.95
STRUCTURE_INSET_X_MARGIN = 0.08
"""The inset's x margins as a fraction of its z range, so an end station's marker and
label stay inside it."""
STRUCTURE_INSET_OBSTACLE_MARGIN = (0.07, 0.07, 0.0, 0.04)
"""How far (left, below, right, above; axes fraction) the stage-2 inset's rectangle is
widened for the annotation's overlap test: its tick labels and title sit there."""
STRUCTURE_BAR_EDGE_WIDTH = 0.5
STRUCTURE_BAR_LABEL_OFFSET_PT = (4.0, 0.0)
STRUCTURE_BAR_HEADROOM = 1.25
"""The dm panel's x range as a multiple of the largest bar, so its label fits."""
STRUCTURE_TITLE_WRAP_CHARS = 90
"""The title's second line (the layer label and set) is wrapped at this many characters,
so the outer sets' long labels never run past the figure's edge."""
STRUCTURE_STAGE2_SIZED_TEXT = (
    "stage 2 sized by this push: its stations drawn in the inset (its own z range, "
    "above stage 1's in the stack frame)"
)
STRUCTURE_STAGE2_NOT_SIZED_TEXT = (
    "stage 2 not sized: the push stays inside the upper stack's envelope, so no stage-2 "
    "station is drawn"
)
STRUCTURE_STAGE2_INSET_TITLE = "stage 2 (sized by this push): its stations"
STRUCTURE_PROFILE_TEXT = (
    "the modelled structural mass of the push load, first-order station sizing; not a measurement"
)


def _num(value: Any, fmt: str) -> str:
    """A number formatted with ``fmt``, or n/a."""
    if value is None or not isinstance(value, int | float) or not math.isfinite(float(value)):
        return "n/a"
    return format(float(value), fmt)


def _sized_at(record: Mapping[str, Any]) -> str:
    """At which offload the record's sizing was taken, for the caption: a structure
    payload case at the full load with payload P_1* (its drawn profile and bars are dm_1,
    sized at P_1*; the run then flew P_2*, named too; or, when that search found no P*,
    that it failed), a no_offload end at x = 0, a solved case at its x* (tonnes), else
    that the record does not state it (a bare structure record, as a test passes)."""
    if record.get("kind") == STRUCTURE_PAYLOAD_RECORD_KIND:
        p1, p2 = record.get("payload_1_kg"), record.get("payload_kg")
        if not isinstance(p2, int | float) or not math.isfinite(float(p2)):
            return (
                f"at the full load with payload P_1* {_num(p1, ',.1f')} kg (dm_1; structure "
                "payload case; its P_2* search failed)"
            )
        return (
            f"at the full load with payload P_1* {_num(p1, ',.1f')} kg (dm_1; the run then "
            f"flew P_2* {_num(p2, ',.1f')} kg; structure payload case)"
        )
    if record.get("status") == NO_OFFLOAD_STATUS:
        return "at x = 0 (the solve ended no_offload)"
    x = record.get("offload_kg")
    if isinstance(x, int | float) and math.isfinite(float(x)):
        return f"at x* = {float(kg_to_t(float(x))):,.3f} t"
    return "at an offload the record does not state"


def _governing_text(record: Mapping[str, Any]) -> str:
    """The caption's governing line: the record's ``structure_governing`` element with its
    push mode, its dm from ``structure_elements`` and, for an element with stations, its
    station and height; a relation element (the thrust structure, the interstage) or the
    ring frame has no station profile and the caption is the only place the figure names
    it."""
    governing = record.get("structure_governing")
    if not isinstance(governing, Mapping):
        return "governing element: none (dm is 0)"
    name = f"{governing.get('stage')}.{governing.get('element')}"
    kg = (record.get("structure_elements") or {}).get(name)
    mode = governing.get("push_mode")
    if governing.get("station_index") is None:
        kind = (
            "the ring frame, closed form"
            if governing.get("element") == "load_ring"
            else "a relation element"
        )
        where = f"{kind}: no station profile, so it is not drawn in the top panel"
    else:
        where = (
            f"station {governing.get('station_index')}, z {_num(governing.get('z_m'), '.2f')} m, "
            "annotated in the top panel"
        )
    return f"governing element: {name} ({mode}; {_num(kg, ',.1f')} kg of dm; {where})"


def _structure_caption(record: Mapping[str, Any], stage2_sized: bool) -> str:
    """The figure's caption from the case record (the run-level structure keys, with the
    case's status, x* and kind when the record is a case record): the set with its layer
    label and the case settings (the summary's band lines carry the sets' label and
    source; the figure asserts nothing about how the set was found), the envelope pad
    with the margin and cap the dashed envelope carries (a margin or cap row's envelope
    is its own), n_peak and F_peak, on a line of its own at which offload the profile was
    sized (``_sized_at``; a payload case's clause is the longest line of the caption,
    review NEW-V-01), dm by stage, the governing element (``_governing_text``), whether
    stage 2 was sized, and, for a plausibility-scaled case, that the profile is the
    unscaled sizing while the bars and dm carry the factor; what the profile is (the
    model's sizing, not a measurement). Each line is wrapped at
    STRUCTURE_CAPTION_WRAP_CHARS with STRUCTURE_CAPTION_INDENT on its continuation, so
    none runs past the figure's edge."""
    dm = record.get("structure_dm_kg")
    dm2 = record.get("structure_dm_stage2_kg")
    dm1 = None if dm is None or dm2 is None else dm - dm2
    cap = record.get("structure_envelope_cap_g")
    cap_text = "no cap" if cap is None else f"cap {cap:g} g0"
    n_peak = record.get("structure_n_peak_g")
    f_peak = record.get("structure_F_peak_N")
    f_peak_mn = None if f_peak is None else float(n_to_mn(float(f_peak)))
    margin_text = f"margin {_num(record.get('structure_margin'), 'g')}"
    parts = [
        f"{structure_layer_label(record)}; {record.get('structure_sizing')}, "
        f"{record.get('structure_dynamic')} (DLF {_num(record.get('structure_dlf'), '.3f')}), "
        f"{record.get('structure_entry')}, {margin_text}, {cap_text}",
        f"pad envelope: {record.get('structure_envelope_pad')}'s own flight (the dashed "
        f"envelope is at {margin_text}, {cap_text}); push at n_peak "
        f"{_num(n_peak, '.3f')} g0, F_peak {_num(f_peak_mn, '.3f')} MN",
        f"sized {_sized_at(record)}",
        f"dm: stage 1 {_num(dm1, ',.1f')} kg, stage 2 {_num(dm2, ',.1f')} kg "
        f"({STRUCTURE_PROFILE_TEXT})",
        _governing_text(record),
        STRUCTURE_STAGE2_SIZED_TEXT if stage2_sized else STRUCTURE_STAGE2_NOT_SIZED_TEXT,
    ]
    if record.get("structure_plausibility_scaled"):
        factor = _num(record.get("structure_plausibility_factor"), ".4f")
        parts.append(
            "the thickness profile is the unscaled sizing; the bars and dm carry the "
            f"plausibility rule's factor {factor} (D-SP7-33)"
        )
    return "\n".join(
        textwrap.fill(
            part, STRUCTURE_CAPTION_WRAP_CHARS, subsequent_indent=STRUCTURE_CAPTION_INDENT
        )
        for part in parts
    )


@dataclass
class _DrawnAxes:
    """What ``_draw_elements`` drew into one axes, for the label and annotation overlap
    tests and the legend: the data points of every station and envelope point (each
    array with the page offset [pt] in z its element is drawn at, ``_display_points``),
    the label texts (placed by ``_label_elements``), the governing annotation (placed
    first by ``_annotate_governing``, so the labels keep off its box), the stages drawn,
    the modes drawn (name -> colour, marker), whether a point element was drawn, and,
    per element, its arrays with that offset (``_mark_modes``)."""

    ax: Any
    points: list[tuple[Any, float]] = field(default_factory=list)
    labels: list[Any] = field(default_factory=list)
    annotations: list[Any] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    modes: dict[str, tuple[str, str]] = field(default_factory=dict)
    point_elements: bool = False
    elements: dict[tuple[str, str], Any] = field(default_factory=dict)


def _pt_to_px(fig: Figure, pt: float) -> float:
    """Points to display pixels at the figure's dpi."""
    return pt * float(fig.dpi) / POINTS_PER_INCH


def _display_points(drawn: _DrawnAxes) -> np.ndarray:
    """Every drawn station and envelope point of ``drawn`` [display px, (n, 2)], each
    element's page offset in z applied (the coincident point elements are set apart on
    the page, not in the data)."""
    if not drawn.points:
        return np.empty((0, 2))
    fig = drawn.ax.figure
    blocks = []
    for data, dx_pt in drawn.points:
        px = drawn.ax.transData.transform(data)
        blocks.append(px + np.array([_pt_to_px(fig, dx_pt), 0.0]))
    return np.concatenate(blocks)


def _z_offsets_pt(elements: Sequence[Any]) -> dict[tuple[str, str], float]:
    """The page offset in z [pt] of each point element (a dome or the tube: one station):
    0 when it shares its station height with no other point element, else the members of
    the group spread STRUCTURE_COINCIDENT_OFFSET_PT apart around it, so the aft dome's
    square and point never hide under the tube's."""
    points = [e for e in elements if np.asarray(e.z_stations_m).shape[0] == 1]
    groups: dict[float, list[Any]] = {}
    for e in points:
        groups.setdefault(round(float(np.asarray(e.z_stations_m)[0]), 6), []).append(e)
    out: dict[tuple[str, str], float] = {}
    for members in groups.values():
        k = len(members)
        for i, e in enumerate(members):
            out[(e.stage, e.element)] = (i - (k - 1) / 2.0) * STRUCTURE_COINCIDENT_OFFSET_PT
    return out


def _marked_stations(z: np.ndarray, modes: Sequence[str], px_per_m: float) -> np.ndarray:
    """The station indices to mark on a barrel: every k-th station with k the least
    integer giving STRUCTURE_MARKER_SPACING_PX between marks at ``px_per_m`` [px per m of
    z], plus every station whose governing mode differs from the previous station's and
    both ends; every station when they are already that far apart."""
    n = z.shape[0]
    if n < 2:
        return np.arange(n)
    dz_px = px_per_m * float(abs(z[-1] - z[0])) / (n - 1)
    k = max(1, math.ceil(STRUCTURE_MARKER_SPACING_PX / dz_px)) if dz_px > 0.0 else 1
    marked = set(range(0, n, k)) | {0, n - 1}
    marked |= {i for i in range(1, n) if modes[i] != modes[i - 1]}
    return np.array(sorted(marked), dtype=int)


def _mode_style(mode: str) -> tuple[str, str]:
    """The (colour, marker) of a governing mode (STRUCTURE_MODE_MARKERS, else unknown)."""
    return STRUCTURE_MODE_MARKERS.get(mode, STRUCTURE_MODE_MARKER_UNKNOWN)


def _z_transform(ax: Any, dx_pt: float) -> Any:
    """The axes' data transform shifted by ``dx_pt`` [pt] in x on the page (the identity
    at 0): how a coincident point element is set apart (``_z_offsets_pt``)."""
    if dx_pt == 0.0:
        return ax.transData
    return offset_copy(ax.transData, fig=ax.figure, x=dx_pt, y=0.0, units="points")


def _draw_elements(drawn: _DrawnAxes, elements: Sequence[Any]) -> None:
    """Draw the required wall thickness [mm] against the station height z [m] of every
    given element with stations into ``drawn.ax``: the pad envelope dashed, the push as a
    line in the stage's colour; a dome or the tube as one push point joined by a drop
    line in the stage colour to the hollow square of its envelope, the square drawn on
    top with a thin edge (two point elements at one station height are set
    STRUCTURE_COINCIDENT_OFFSET_PT apart on the page, ``_z_offsets_pt``; a line drawn
    through that page-offset transform enters no data limit, matplotlib's autoscale reads
    transData lines only, so a point element's data coordinates are added to the limits
    by hand and the axes' z range covers it, review NEW-V-02: the stage-2 inset's range
    had started at its first barrel and left the aft dome and the tube outside). The
    labels are placed afterwards by ``_label_elements`` and the governing-mode markers by
    ``_mark_modes`` (both need the final layout)."""
    ax = drawn.ax
    offsets = _z_offsets_pt(elements)
    for element in elements:
        z = np.asarray(element.z_stations_m, dtype=float)
        env_mm = np.asarray(m_to_mm(np.asarray(element.t_env_m, dtype=float)))
        push_mm = np.asarray(m_to_mm(np.asarray(element.t_push_m, dtype=float)))
        color = STRUCTURE_STAGE_COLORS.get(element.stage, PLOT_SERIES_COLOR)
        point = z.shape[0] == 1
        dx_pt = offsets.get((element.stage, element.element), 0.0)
        transform = _z_transform(ax, dx_pt)
        if point:
            drawn.point_elements = True
            ax.update_datalim(np.column_stack([[z[0], z[0]], [env_mm[0], push_mm[0]]]))
            ax.plot(
                [z[0], z[0]],
                [env_mm[0], push_mm[0]],
                color=color,
                linewidth=STRUCTURE_POINT_DROP_LINE_WIDTH,
                alpha=STRUCTURE_POINT_DROP_ALPHA,
                transform=transform,
                zorder=2,
            )
            ax.plot(
                z,
                push_mm,
                color=color,
                linewidth=0.0,
                alpha=STRUCTURE_PUSH_ALPHA,
                marker="o",
                markersize=STRUCTURE_POINT_PUSH_PT,
                transform=transform,
                zorder=3,
            )
            ax.plot(
                z,
                env_mm,
                color=STRUCTURE_ENVELOPE_COLOR,
                linewidth=0.0,
                marker="s",
                markersize=STRUCTURE_POINT_ENVELOPE_PT,
                markerfacecolor="none",
                markeredgewidth=STRUCTURE_POINT_ENVELOPE_EDGE_PT,
                transform=transform,
                zorder=5,
            )
        else:
            ax.plot(
                z,
                env_mm,
                color=STRUCTURE_ENVELOPE_COLOR,
                linestyle="--",
                linewidth=STRUCTURE_ENVELOPE_LINE_WIDTH,
                zorder=2,
            )
            ax.plot(
                z,
                push_mm,
                color=color,
                linewidth=STRUCTURE_PUSH_LINE_WIDTH,
                alpha=STRUCTURE_PUSH_ALPHA,
                zorder=3,
            )
        if element.stage not in drawn.stages:
            drawn.stages.append(element.stage)
        drawn.elements[(element.stage, element.element)] = (z, env_mm, push_mm, element, dx_pt)
        drawn.points.append((np.column_stack([z, env_mm]), dx_pt))
        drawn.points.append((np.column_stack([z, push_mm]), dx_pt))
        if point:  # the drop line joins the overlap test too
            along = np.linspace(float(env_mm[0]), float(push_mm[0]), STRUCTURE_DROP_LINE_SAMPLES)
            drawn.points.append((np.column_stack([np.full_like(along, z[0]), along]), dx_pt))


def _label_anchors(z: np.ndarray, push_mm: np.ndarray) -> list[tuple[float, float]]:
    """Where an element's label may be anchored [data]: a point element at its push
    point; a barrel at the station of its push's maximum, then at the
    STRUCTURE_BARREL_ANCHOR_FRACTIONS of its stations (each once)."""
    n = z.shape[0]
    if n == 1:
        return [(float(z[0]), float(push_mm[0]))]
    indices = [int(np.argmax(push_mm))]
    indices += [min(n - 1, round(f * (n - 1))) for f in STRUCTURE_BARREL_ANCHOR_FRACTIONS]
    out: list[tuple[float, float]] = []
    for i in dict.fromkeys(indices):
        out.append((float(z[i]), float(push_mm[i])))
    return out


def _offset_alignment(dx: float, dy: float) -> tuple[str, str]:
    """A label's (ha, va) for an offset [pt] from its anchor: aligned away from the
    anchor on the offset's side, centred along a zero component."""
    ha = "center" if dx == 0.0 else ("left" if dx > 0.0 else "right")
    va = "center" if dy == 0.0 else ("bottom" if dy > 0.0 else "top")
    return ha, va


def _far_candidates(ax: Any, anchor_px: np.ndarray) -> list[tuple[float, float, str, str]]:
    """The far positions an element label may take with a leader line, in axes fraction
    with their alignment (towards the inside at an edge), the grid of
    STRUCTURE_LABEL_FAR_FRACTIONS sorted by distance [px] from ``anchor_px`` so the
    nearest clear spot wins and the leader stays short."""
    lo, hi = STRUCTURE_LABEL_FAR_FRACTIONS[0], STRUCTURE_LABEL_FAR_FRACTIONS[-1]
    out = []
    for x in STRUCTURE_LABEL_FAR_FRACTIONS:
        for y in STRUCTURE_LABEL_FAR_FRACTIONS:
            ha = "left" if x == lo else ("right" if x == hi else "center")
            va = "bottom" if y == lo else ("top" if y == hi else "center")
            px = ax.transAxes.transform((x, y))
            out.append((float(np.hypot(*(px - anchor_px))), x, y, ha, va))
    return [(x, y, ha, va) for _d, x, y, ha, va in sorted(out, key=lambda c: c[0])]


def _label_cost(
    box: Bbox, points: np.ndarray, labels: Sequence[Any], ax_box: Bbox, obstacles: Sequence[Any]
) -> int:
    """The cost of an element label's box: the drawn points it covers and the placed
    labels it overlaps (``_overlaps`` at STRUCTURE_LABEL_COSTS) plus the obstacle weight
    when it leaves its axes' box or covers one of ``obstacles`` (the stage-2 inset)."""
    w_point, w_label, w_obstacle = STRUCTURE_LABEL_COSTS
    cost = _overlaps(box, points, labels, obstacles, costs=(w_point, w_label, w_obstacle))
    outside = box.x0 < ax_box.x0 or box.x1 > ax_box.x1 or box.y0 < ax_box.y0 or box.y1 > ax_box.y1
    return cost + (w_obstacle if outside else 0)


def _place_label(
    drawn: _DrawnAxes,
    text: str,
    anchors: Sequence[tuple[float, float]],
    dx_pt: float,
    *,
    fontsize: float,
    color: str,
    points: np.ndarray,
    obstacles: Sequence[Any],
) -> Any:
    """Place one element label in ``drawn.ax``: at the first (anchor, offset) of
    ``anchors`` x STRUCTURE_LABEL_OFFSETS_PT whose text box (padded by
    STRUCTURE_LABEL_PAD_PX) covers no drawn point (the stations, the envelope points and
    the drop lines), overlaps no placed label and not the governing annotation's box,
    stays inside the axes and off the ``obstacles``; when no offset is clear (a crowded
    inset), at the nearest clear far position (``_far_candidates``) with a leader line
    to the first anchor (STRUCTURE_LABEL_LEADER); else at the candidate of the least
    cost (``_label_cost``). ``dx_pt`` is the element's page offset in z. Every rejected
    candidate is removed. Needs the figure's renderer, so it is called after the layout
    is final."""
    ax = drawn.ax
    renderer = _renderer(ax.figure)
    ax_box = ax.get_window_extent(renderer)
    placed = [
        _text_extent(t, renderer).padded(STRUCTURE_LABEL_PAD_PX)
        for t in (*drawn.annotations, *drawn.labels)
    ]
    best: tuple[int, Any] | None = None

    def consider(ann: Any) -> bool:
        """Keep ``ann`` when it beats the best so far (removing the loser); True when
        its box is clear, so the search can stop."""
        nonlocal best
        box = _text_extent(ann, renderer).padded(STRUCTURE_LABEL_PAD_PX)
        cost = _label_cost(box, points, placed, ax_box, obstacles)
        if best is None or cost < best[0]:
            if best is not None:
                best[1].remove()
            best = (cost, ann)
        else:
            ann.remove()
        return cost == 0

    clear = False
    for xy in anchors:
        for dx, dy in STRUCTURE_LABEL_OFFSETS_PT:
            ha, va = _offset_alignment(dx, dy)
            ann = ax.annotate(
                text,
                xy,
                xycoords=_z_transform(ax, dx_pt),
                textcoords="offset points",
                xytext=(dx, dy),
                fontsize=fontsize,
                color=color,
                ha=ha,
                va=va,
            )
            clear = consider(ann)
            if clear:
                break
        if clear:
            break
    if not clear:
        anchor_px = _z_transform(ax, dx_pt).transform(anchors[0])
        for x, y, ha, va in _far_candidates(ax, np.asarray(anchor_px, dtype=float)):
            ann = ax.annotate(
                text,
                anchors[0],
                xycoords=_z_transform(ax, dx_pt),
                textcoords="axes fraction",
                xytext=(x, y),
                fontsize=fontsize,
                color=color,
                ha=ha,
                va=va,
                arrowprops={**STRUCTURE_LABEL_LEADER, "color": color},
            )
            if consider(ann):
                break
    assert best is not None
    drawn.labels.append(best[1])
    return best[1]


def _label_elements(drawn: _DrawnAxes, obstacles: Sequence[Any]) -> None:
    """Label every element drawn into ``drawn.ax`` with ``<stage>.<element>`` in its
    stage's colour (a point element at STRUCTURE_FONT_POINT_LABEL_PT, a barrel at
    STRUCTURE_FONT_LABEL_PT), each placed by ``_place_label`` against every drawn point
    of every element, the labels placed before it, the axes' box and ``obstacles`` (the
    stage-2 inset's box for the top panel), so no label is struck through by another
    element's line, sits on another label or runs out of its axes; once the layout is
    final."""
    points = _display_points(drawn)
    for (stage, element), (z, _env_mm, push_mm, _e, dx_pt) in drawn.elements.items():
        point = z.shape[0] == 1
        _place_label(
            drawn,
            _plot_text(f"{stage}.{element}"),
            _label_anchors(z, push_mm),
            dx_pt,
            fontsize=STRUCTURE_FONT_POINT_LABEL_PT if point else STRUCTURE_FONT_LABEL_PT,
            color=STRUCTURE_STAGE_COLORS.get(stage, PLOT_SERIES_COLOR),
            points=points,
            obstacles=obstacles,
        )


def _mark_modes(drawn: _DrawnAxes) -> None:
    """Mark the push's governing mode at the stations of every element drawn into
    ``drawn.ax`` (STRUCTURE_MODE_MARKERS by mode name), thinned on a dense barrel to
    STRUCTURE_MARKER_SPACING_PX (``_marked_stations``, the mode switches and both ends
    always marked) once the axes' z range is final, so the push line shows between them;
    a point element's marker takes its page offset in z."""
    ax = drawn.ax
    x_lo, x_hi = ax.get_xlim()
    width_px = float(ax.get_window_extent().width)
    px_per_m = width_px / (x_hi - x_lo) if x_hi > x_lo else 0.0
    for z, _env_mm, push_mm, element, dx_pt in drawn.elements.values():
        modes = tuple(element.push_modes)
        marked = _marked_stations(z, modes, px_per_m)
        for mode in dict.fromkeys(modes):
            drawn.modes.setdefault(mode, _mode_style(mode))
            mode_color, marker = drawn.modes[mode]
            mask = np.array([modes[i] == mode for i in marked], dtype=bool)
            if not np.any(mask):
                continue
            ax.scatter(
                z[marked][mask],
                push_mm[marked][mask],
                s=STRUCTURE_MARKER_SIZE,
                color=mode_color,
                marker=marker,
                zorder=4,
                linewidths=0.0,
                transform=_z_transform(ax, dx_pt),
            )


def _with_stations(increment: Increment) -> list[Any]:
    """The increment's elements that carry a station profile (both arrays and the modes)."""
    return [
        e
        for e in increment.elements
        if e.z_stations_m is not None
        and e.t_env_m is not None
        and e.t_push_m is not None
        and e.push_modes is not None
    ]


def _thickness_legend(top: Any, drawn: Sequence[_DrawnAxes]) -> None:
    """The top panel's legend, placed under the panel (outside the plotting area, so it
    never overprints a station), from synthetic handles independent of the order the
    elements were drawn in: the envelope line, the push line per stage drawn, the point
    markers when a dome or the tube was drawn, and one entry per governing mode drawn
    (its colour and shape, STRUCTURE_MODE_MARKERS)."""
    items: list[Any] = [
        Line2D(
            [],
            [],
            color=STRUCTURE_ENVELOPE_COLOR,
            linestyle="--",
            linewidth=STRUCTURE_ENVELOPE_LINE_WIDTH,
        )
    ]
    labels: list[str] = [STRUCTURE_LEGEND_ENVELOPE]
    stages = list(dict.fromkeys(s for d in drawn for s in d.stages))
    for stage in stages:
        color = STRUCTURE_STAGE_COLORS.get(stage, PLOT_SERIES_COLOR)
        items.append(Line2D([], [], color=color, linewidth=STRUCTURE_PUSH_LINE_WIDTH))
        labels.append(f"push: {stage}")
    if any(d.point_elements for d in drawn):
        items.append(
            Line2D(
                [],
                [],
                linestyle="",
                marker="o",
                color=STRUCTURE_ENVELOPE_COLOR,
                markersize=STRUCTURE_POINT_PUSH_PT,
            )
        )
        labels.append(STRUCTURE_LEGEND_POINT_PUSH)
        items.append(
            Line2D(
                [],
                [],
                linestyle="",
                marker="s",
                color=STRUCTURE_ENVELOPE_COLOR,
                markerfacecolor="none",
                markeredgewidth=STRUCTURE_POINT_ENVELOPE_EDGE_PT,
                markersize=STRUCTURE_POINT_ENVELOPE_PT,
            )
        )
        labels.append(STRUCTURE_LEGEND_POINT_ENVELOPE)
    modes: dict[str, tuple[str, str]] = {}
    for d in drawn:
        modes.update(d.modes)
    for mode, (color, marker) in modes.items():
        items.append(
            Line2D(
                [],
                [],
                linestyle="",
                marker=marker,
                color=color,
                markersize=STRUCTURE_LEGEND_MARKER_PT,
            )
        )
        labels.append(f"governing mode: {mode}")
    top.legend(
        items,
        labels,
        frameon=False,
        fontsize=STRUCTURE_FONT_CAPTION_PT,
        ncol=STRUCTURE_LEGEND_COLUMNS,
        loc="upper center",
        bbox_to_anchor=STRUCTURE_LEGEND_ANCHOR,
    )


def _overlaps(
    box: Any,
    points: np.ndarray,
    labels: Sequence[Any],
    obstacles: Sequence[Any],
    *,
    costs: tuple[int, int, int] = STRUCTURE_ANNOTATION_COSTS,
) -> int:
    """The cost of ``box`` (a Bbox [display px]) covering drawn artists: the number of
    ``points`` [display px, (n, 2)] inside it, the ``labels`` (text boxes) and the
    ``obstacles`` (the inset's box) it overlaps, each weighted by ``costs``
    (STRUCTURE_ANNOTATION_COSTS for the governing annotation, STRUCTURE_LABEL_COSTS for
    an element label)."""
    inside = 0
    if points.size:
        inside = int(
            np.count_nonzero(
                (points[:, 0] >= box.x0)
                & (points[:, 0] <= box.x1)
                & (points[:, 1] >= box.y0)
                & (points[:, 1] <= box.y1)
            )
        )
    w_point, w_label, w_obstacle = costs
    return (
        w_point * inside
        + w_label * sum(1 for b in labels if box.overlaps(b))
        + w_obstacle * sum(1 for b in obstacles if box.overlaps(b))
    )


def _place_annotation(
    drawn: _DrawnAxes, text: str, xy: tuple[float, float], obstacles: Sequence[Any]
) -> Any:
    """Annotate ``xy`` [data] of ``drawn.ax`` with ``text`` in a box and a leader arrow,
    at the first STRUCTURE_ANNOTATION_CANDIDATES position whose box (the text's extent
    padded by STRUCTURE_ANNOTATION_PAD_PX) covers no drawn station or envelope point, no
    element label placed so far and none of ``obstacles`` (the stage-2 inset's box), else
    at the one of the least cost (``_overlaps``); every rejected candidate is removed
    and the kept one goes to ``drawn.annotations`` (the element labels, placed after it,
    keep off its box). Needs the figure's renderer (``_renderer``), so it is called
    after the layout is final."""
    ax = drawn.ax
    renderer = _renderer(ax.figure)
    points = _display_points(drawn)
    labels = [_text_extent(t, renderer) for t in drawn.labels]
    best: tuple[int, Any] | None = None
    for x, y, ha, va in STRUCTURE_ANNOTATION_CANDIDATES:
        ann = ax.annotate(
            text,
            xy,
            xytext=(x, y),
            textcoords="axes fraction",
            fontsize=STRUCTURE_FONT_LABEL_PT,
            ha=ha,
            va=va,
            bbox=STRUCTURE_TEXT_BOX,
            arrowprops=STRUCTURE_ANNOTATION_ARROW,
            zorder=5,
        )
        box = _text_extent(ann, renderer).padded(STRUCTURE_ANNOTATION_PAD_PX)
        count = _overlaps(box, points, labels, obstacles)
        if best is None or count < best[0]:
            if best is not None:
                best[1].remove()
            best = (count, ann)
            if count == 0:
                break
        else:
            ann.remove()
    assert best is not None
    drawn.annotations.append(best[1])
    return best[1]


def _text_extent(annotation: Any, renderer: Any) -> Bbox:
    """The extent [display px] of an annotation's text alone: its position resolved for
    the renderer (``update_positions`` sets the text's transform, which ``annotate``
    leaves at the identity until a draw) and its arrow, which reaches the annotated
    point, left out."""
    annotation.update_positions(renderer)
    return Text.get_window_extent(annotation, renderer)


def _renderer(fig: Figure) -> Any:
    """The figure's Agg renderer (attached when the figure has none yet: a Figure built
    outside pyplot has only a base canvas until it is saved)."""
    canvas = fig.canvas
    if not hasattr(canvas, "get_renderer"):
        canvas = FigureCanvasAgg(fig)
    return canvas.get_renderer()


def _annotate_governing(
    drawn: Sequence[_DrawnAxes], record: Mapping[str, Any], obstacles: Sequence[Any]
) -> None:
    """Annotate the record's governing element and station (``structure_governing``) with
    its push and envelope thickness in the axes that drew it (the top panel, or the
    stage-2 inset), placed away from the drawn artists (``_place_annotation``); nothing
    for a relation element without stations (the caption names it,
    ``_governing_text``)."""
    governing = record.get("structure_governing")
    if not isinstance(governing, Mapping) or governing.get("station_index") is None:
        return
    key = (str(governing.get("stage")), str(governing.get("element")))
    holder = next((d for d in drawn if key in d.elements), None)
    if holder is None:
        return
    z, env_mm, push_mm, _element, _dx_pt = holder.elements[key]
    i = int(governing["station_index"])
    zg, tp, te = float(z[i]), float(push_mm[i]), float(env_mm[i])
    text = _plot_text(
        f"governing: {key[0]}.{key[1]}, station {i}, z {zg:.2f} m\n"
        f"{governing.get('push_mode')} over {governing.get('envelope_mode')}: "
        f"push {tp:.2f} mm, envelope {te:.2f} mm"
    )
    _place_annotation(holder, text, (zg, tp), obstacles)


def _dm_axis_label(entry: Any) -> str:
    """The dm panel's axis label: how the elements were sized under the case's load entry
    (``structure_entry``; the rule of ``summary._element_how``, review H-S3B-P3-06): under
    entry aft_ring the thrust structure is not in the load path (its 0 is by construction,
    not a sizing) and the hatched ring frame is new hardware in closed form; under entry
    thrust_structure the thrust structure is sized by its relation and there is no ring
    frame (its 0 is by construction; a zero-width bar shows no hatch); a record without an
    entry (a bare structure record) gets the generic text. Three short lines under the
    unit line, each well inside the panel's width at STRUCTURE_FONT_AXIS_PT (the test
    measures the panel's tight box against the figure)."""
    if entry == ENTRY_AFT_RING:
        how = (
            " the interstage by its relation;\n"
            "the thrust structure not in the load path on entry aft_ring, 0 by construction;\n"
            "hatched: the ring frame, closed form, no envelope credit"
        )
    elif entry == ENTRY_THRUST_STRUCTURE:
        how = (
            "\nthe interstage and the thrust structure by their relations;\n"
            "no ring frame on entry thrust_structure: the ring frame's 0 is by construction"
        )
    else:
        how = (
            "\nthe interstage and the thrust structure by their relations where the entry "
            "loads them;\nhatched: the ring frame, closed form, no envelope credit"
        )
    return f"dm by element [kg]\n(station sizing over the pad envelope;{how})"


def _dm_panel(bottom: Any, record: Mapping[str, Any], title: str) -> None:
    """The bottom panel: dm by element from the record's ``structure_elements`` [kg],
    horizontal bars by stage, the ring frame hatched, every bar labelled with its kg; the
    title carries dm1 + dm2 and, for a plausibility-scaled case, the factor the bars
    carry; the axis label says how the elements were sized under the case's entry
    (``_dm_axis_label``)."""
    elements = record.get("structure_elements") or {}
    names = list(elements)
    values = [float(elements[n]) for n in names]
    y = np.arange(len(names))
    colors = [STRUCTURE_STAGE_COLORS.get(n.split(".")[0], PLOT_SERIES_COLOR) for n in names]
    bars = bottom.barh(
        y, values, color=colors, edgecolor="#222222", linewidth=STRUCTURE_BAR_EDGE_WIDTH
    )
    for bar, name, value in zip(bars, names, values, strict=True):
        if name.endswith(".load_ring"):
            bar.set_hatch("///")
        bottom.annotate(
            f"{value:,.1f} kg",
            (bar.get_width(), bar.get_y() + bar.get_height() / 2.0),
            textcoords="offset points",
            xytext=STRUCTURE_BAR_LABEL_OFFSET_PT,
            va="center",
            fontsize=STRUCTURE_FONT_LABEL_PT,
        )
    bottom.set_yticks(y)
    bottom.set_yticklabels([_plot_text(n) for n in names], fontsize=STRUCTURE_FONT_LABEL_PT)
    bottom.invert_yaxis()
    bottom.set_xlabel(
        _dm_axis_label(record.get("structure_entry")), fontsize=STRUCTURE_FONT_AXIS_PT
    )
    dm = record.get("structure_dm_kg")
    scaled = ""
    if record.get("structure_plausibility_scaled"):
        scaled = (
            f" (x {_num(record.get('structure_plausibility_factor'), '.4f')}, plausibility-scaled)"
        )
    bottom.set_title(
        _plot_text(f"{title}: dm by element (dm1 + dm2 = {_num(dm, ',.1f')} kg){scaled}"),
        fontsize=STRUCTURE_FONT_TITLE_PT,
    )
    bottom.grid(True, axis="x", color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
    for side in ("top", "right"):
        bottom.spines[side].set_visible(False)
    if values:
        bottom.set_xlim(0.0, max(values) * STRUCTURE_BAR_HEADROOM if max(values) > 0.0 else 1.0)


def _style_thickness_axes(ax: Any, fontsize: float | None = None) -> None:
    """The grid and open spines of a thickness axes (the top panel and the inset)."""
    ax.grid(True, color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINE_WIDTH)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if fontsize is not None:
        ax.tick_params(labelsize=fontsize)


def structure_figure(increment: Increment, record: Mapping[str, Any], title: str) -> Figure:
    """The thickness figure of a structural run (SP7 step S3b; design 4.4, "Figures"), two
    panels, built from the sizing's ``structure.Increment`` and the run's case record
    (its structure keys, ``sim.structure_record``, with the case's status, x* and kind;
    the numbers a reviewer checks it against).

    Top (``_draw_elements``, ``_mark_modes``, ``_label_elements``): the required wall
    thickness [mm] along the station height z [m, stack frame] of every stage-1 element
    with stations (the aft skirt, both barrels; a dome or the tube as one labelled push
    point at its crown or bottom, joined by a drop line to the hollow square of its
    envelope, two at one height set apart on the page): the pad envelope dashed in
    STRUCTURE_ENVELOPE_COLOR, the push as a line in the stage's colour, the push's
    governing mode marked by a colour and marker shape fixed per mode name
    (STRUCTURE_MODE_MARKERS), thinned on a dense barrel so the line shows between the
    marks (every mode switch and both ends always marked); every element label placed
    once the layout is final at the first anchor and offset whose box covers no drawn
    point of any element, no placed label, stays inside its axes and off the inset
    (``_place_label``); the legend under the panel from synthetic handles
    (``_thickness_legend``); the governing element and station of the record
    (``structure_governing``) annotated with its push and envelope thickness in a box
    placed where it covers no drawn station, label or inset (``_annotate_governing``).
    Where the push sized stage 2, its elements are drawn in an
    inset at the top right (STRUCTURE_STAGE2_INSET_RECT) with its own z range, the
    panel's z range extended past stage 1's data (STRUCTURE_STAGE2_X_EXTENSION) so the
    inset covers no stage-1 station; otherwise the axis label and the caption say stage
    2 was not sized. The title's second line (the layer label and set) is wrapped
    (STRUCTURE_TITLE_WRAP_CHARS). Bottom (``_dm_panel``): dm by element from the record's
    ``structure_elements`` [kg], horizontal bars by stage, the ring frame hatched (new
    hardware sized in closed form, no envelope credit), every bar labelled with its kg, a
    scaled case's factor in the title. The caption (``_structure_caption``) names the set
    and its layer, the case settings, the envelope pad, n_peak, F_peak, at which offload
    the profile was sized, dm by stage and the governing element. Pure apart from the
    Figure it builds (an Agg canvas is attached to measure the texts).
    """
    fig = Figure(figsize=STRUCTURE_FIGSIZE_IN, dpi=PLOT_DPI)
    FigureCanvasAgg(fig)
    top, bottom = fig.subplots(2, 1, gridspec_kw={"height_ratios": STRUCTURE_HEIGHT_RATIOS})
    elements = _with_stations(increment)
    stage1 = [e for e in elements if e.stage == STAGE1]
    stage2 = [e for e in elements if e.stage != STAGE1]
    main = _DrawnAxes(top)
    _draw_elements(main, stage1)
    drawn = [main]
    inset = None
    if increment.stage2_sized and stage2:
        x_lo, x_hi = top.get_xlim()
        top.set_xlim(x_lo, x_hi + STRUCTURE_STAGE2_X_EXTENSION * (x_hi - x_lo))
        inset = top.inset_axes(STRUCTURE_STAGE2_INSET_RECT)
        inset.patch.set_alpha(STRUCTURE_INSET_FACE_ALPHA)
        inset.margins(x=STRUCTURE_INSET_X_MARGIN)
        sub = _DrawnAxes(inset)
        _draw_elements(sub, stage2)
        inset.set_title(STRUCTURE_STAGE2_INSET_TITLE, fontsize=STRUCTURE_FONT_INSET_PT)
        inset.set_xlabel("z [m]", fontsize=STRUCTURE_FONT_INSET_PT)
        inset.set_ylabel("wall [mm]", fontsize=STRUCTURE_FONT_INSET_PT)
        _style_thickness_axes(inset, STRUCTURE_FONT_INSET_PT)
        drawn.append(sub)
    stage2_note = (
        " (stage 2 in the inset)"
        if inset is not None
        else " (stage 1 only: stage 2 not sized, see the caption)"
    )
    top.set_xlabel(_plot_text(f"station height z above the stage-1 load ring [m]{stage2_note}"))
    top.set_ylabel("required wall thickness [mm]")
    layer = textwrap.fill(structure_layer_label(record), STRUCTURE_TITLE_WRAP_CHARS)
    top.set_title(
        _plot_text(f"{title}: required wall thickness, pad envelope against push\n{layer}"),
        fontsize=STRUCTURE_FONT_TITLE_PT,
    )
    _style_thickness_axes(top)
    _dm_panel(bottom, record, title)
    caption = _structure_caption(record, increment.stage2_sized)
    caption_text = fig.text(
        *STRUCTURE_CAPTION_XY, _plot_text(caption), fontsize=STRUCTURE_FONT_CAPTION_PT, va="bottom"
    )
    for d in drawn:
        _mark_modes(d)
    _thickness_legend(top, drawn)
    fig.tight_layout(rect=_layout_rect(fig, caption_text))
    obstacles = []
    if inset is not None:
        _settle_inset(inset)
        obstacles = [_inset_obstacle(top)]
    _annotate_governing(drawn, record, obstacles)  # first: it has the fewer places to go
    for d in drawn:
        _label_elements(d, obstacles if d is main else [])
    return fig


def _layout_rect(fig: Figure, caption: Any) -> tuple[float, float, float, float]:
    """The figure rectangle tight_layout lays the panels in: the full width, from
    STRUCTURE_CAPTION_GAP above the caption's top (its height measured on the figure's
    renderer, in figure fraction, above STRUCTURE_CAPTION_XY) to the top, so the dm
    panel's axis label clears the caption however many lines it has (review NEW-V-01)."""
    box = caption.get_window_extent(_renderer(fig))
    top_of_caption = STRUCTURE_CAPTION_XY[1] + float(box.height) / float(fig.bbox.height)
    return (0.0, top_of_caption + STRUCTURE_CAPTION_GAP, 1.0, 1.0)


def _settle_inset(inset: Any) -> None:
    """Give the stage-2 inset its final position now: an inset axes is placed by its
    locator at draw time, so until then its data transform and window extent are those
    of the figure it was created in, and the label and annotation overlap tests would
    read stale pixels (``Axes.draw`` applies the locator the same way)."""
    locator = inset.get_axes_locator()
    if locator is not None:
        inset.apply_aspect(locator(inset, _renderer(inset.figure)))


def _inset_obstacle(top: Any) -> Bbox:
    """The stage-2 inset's box [display px] for the annotation's overlap test: its
    rectangle in the top panel's axes fraction (STRUCTURE_STAGE2_INSET_RECT, where the
    inset's locator places it at draw time) widened by STRUCTURE_INSET_OBSTACLE_MARGIN for
    its tick labels and title, transformed by the panel's final transAxes."""
    x0, y0, w, h = STRUCTURE_STAGE2_INSET_RECT
    left, below, right, above = STRUCTURE_INSET_OBSTACLE_MARGIN
    corners = [[x0 - left, y0 - below], [x0 + w + right, y0 + h + above]]
    return Bbox(top.transAxes.transform(corners))


def write_structure_figure(
    increment: Increment, record: Mapping[str, Any], plots_dir: Path, prefix: str
) -> Path:
    """Write plots/<plot_stem(prefix, "structure")>.png, the ``structure_figure`` of a
    structural run (SP7 step S3b: written for every structural case and payload case when
    plots are on, from its case record), and return its path."""
    plots_dir.mkdir(parents=True, exist_ok=True)
    fig = structure_figure(increment, record, prefix)
    path = plots_dir / f"{plot_stem(prefix, STRUCTURE_FIGURE_QUANTITY)}.png"
    fig.savefig(path, format="png")
    return path


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
labels and the footnote below ``bottom`` (three lines, or four with the exploratory line;
a structural line beyond FOOTNOTE_BASE_LINES moves ``bottom`` up, ``_AscentFigure``)."""
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
OFFLOAD_STRUCTURE_PAYLOAD = run_data.OFFLOAD_STRUCTURE_PAYLOAD
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
    (``offload_tag``): its kind (OFFLOAD_CASE, OFFLOAD_PAIRED_PAD, OFFLOAD_PAD_CONTROL,
    OFFLOAD_STRUCTURE_PAYLOAD, or 'offload' for a run the block records but names in no
    case, payload case or control), the legend text after its name, and whether its
    recorded run ends grams of propellant short of orbit by a resolution effect (a pad
    control: read as a pad control, not a failure)."""

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
    it is the experiment's baseline; for a run of the offload block, its OffloadTag and,
    for a penalty row (an offload case whose record charges an assumed stage-1 dry mass
    on its run: replay.penalty_added_kg), that mass [kg] (0.0 when unrecorded), else
    None (A6v fix round 2: the footnote's structural line names what a penalty row
    charges); for a run whose own metrics record charges a modelled structural mass
    (summary.structure_charged, SP7 step S3a) ``modelled`` True and that mass [kg]
    (``structure_dm_kg``, dm1 + dm2; None when unrecorded) and its stage-2 share
    (``structure_dm_stage2_kg``, dm2, the record's own key, as replay's modelled sentence
    reads it, dm1 the difference; None when unrecorded; S3a gate fix), its set (``structure_set``),
    the plausibility rule's factor when the record says the dm carries it
    (``structure_scale_factor``, None otherwise), the names of its fired structure flags
    (``structure_flags_fired``) and, beside a fired release flag that separates a stage-1
    column, D-SP7-39's comparison in short (``structure_release_note``,
    summary.release_flag_comparison_short); fix round 2, H-S3a-P2-04: all read from the
    record, as the mass is; and what its sizing moves off the headline settings
    (``structure_departures``: summary.structure_axis_departures, then
    summary.structure_row_departures; fix round 3, H-S3a-P3-04: a design-axis row on the
    central set never shares the headline case's qualifier; the record read through
    summary.structure_run_record, so a structure payload case's run is not a
    full-load-sizing row: final clean-up, N3a-03); else False, None and empty."""

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
    penalty_added_kg: float | None = None
    modelled: bool = False
    structure_dm_kg: float | None = None
    structure_dm_stage2_kg: float | None = None
    structure_set: str | None = None
    structure_scale_factor: float | None = None
    structure_flags_fired: tuple[str, ...] = ()
    structure_release_note: str | None = None
    structure_departures: tuple[str, ...] = ()

    @property
    def t_start_s(self) -> float:
        """First time after release of the series [s]."""
        return float(self.t_s[0])

    @property
    def t_end_s(self) -> float:
        """Last time after release of the series [s]."""
        return float(self.t_s[-1])

    def push_peak_g(self) -> float | None:
        """Peak felt axial acceleration [g0] during the assist push, or None without one,
        or for a push that never moved: one ASSIST row only, its start (a stalled push, or
        one stopped on the track at t = 0, whose felt g is that of a stack at rest; SP7
        step S4a fix round 4, V4-3)."""
        push = self.phase == ASSIST_KIND
        if int(np.count_nonzero(push)) < 2:
            return None
        return float(np.nanmax(self.felt_axial_g[push]))


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
    resolution'; a structure payload case's run (OFFLOAD_STRUCTURE_PAYLOAD; SP7 step S3a
    fix round 1) 'P* <P> kg (<P - P_ref> kg vs P_ref)' / 'on the full load, carrying its
    modelled structure'. A run without a payload, or one the block names in no case,
    payload case or control, gets one line: 'payload n/a (<status>)' or 'payload <P>
    kg'."""
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
    elif kind == OFFLOAD_STRUCTURE_PAYLOAD:
        head = f"P* {payload:,.0f} kg{vs_ref}"
        detail = "on the full load, carrying its modelled structure"
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
    offload = run_data.as_mapping(metrics.get("offload"))
    role = offload_role(offload, name)
    penalty = penalty_added_kg(role[1]) if role is not None and role[0] == OFFLOAD_CASE else None
    modelled = structure_charged(record)
    dm = record.get("structure_dm_kg") if modelled else None
    dm2 = record.get("structure_dm_stage2_kg") if modelled else None
    factor = record.get("structure_plausibility_factor")
    scaled = modelled and bool(record.get("structure_plausibility_scaled"))
    flags = record.get("structure_flags") if modelled else None
    fired = tuple(
        str(f.get("name"))
        for f in (flags if isinstance(flags, list) else [])
        if isinstance(f, Mapping) and f.get("fired")
    )
    structure_set = record.get("structure_set") if modelled else None
    sized = structure_run_record(record, offload, name)  # a payload case's run: N3a-03
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
        penalty_added_kg=penalty,
        modelled=modelled,
        structure_dm_kg=float(dm) if isinstance(dm, int | float) and math.isfinite(dm) else None,
        structure_dm_stage2_kg=(
            float(dm2) if isinstance(dm2, int | float) and math.isfinite(dm2) else None
        ),
        structure_set=None if structure_set is None else str(structure_set),
        structure_scale_factor=(
            float(factor)
            if scaled and isinstance(factor, int | float) and math.isfinite(factor)
            else None
        ),
        structure_flags_fired=fired,
        structure_release_note=release_flag_comparison_short(record) if modelled else None,
        structure_departures=(
            (*structure_axis_departures(record), *structure_row_departures(sized))
            if modelled
            else ()
        ),
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


STRUCTURE_FOOTNOTE_HEAD = "Structure, per run: "
"""How the footnote's structural line opens when a shown run charges a modelled
structural mass (SP7 step S3a; ``animation_caveats``)."""
FOOTNOTE_LINE_SPACING = 1.3
"""The footnote's line spacing (a multiple of the font size)."""
FOOTNOTE_BASE_LINES = 4
"""The footnote lines the panel grid leaves room for as drawn (the three fixed lines and
the exploratory line); each line beyond them moves the panels' bottom up by one line
(``_AscentFigure``)."""
FOOTNOTE_MEASURE_WIDTH_PX = 1280
"""The frame width the footnote's structural line is wrapped at by default
(``footnote_wrap``; the app's video footer takes the line unwrapped, ``width_px`` None,
and the scene canvas wraps it at the frame's width: fix round 3, S3A-NUM-01). The
footnote is set in points on a figure whose size in inches is fixed and whose dpi scales
with the width (``frame_geometry``), but font hinting differs by dpi, so a line that fits
at one width can overrun at another (measured, fix round 2, N2-03: up to 9 px at 480 and
960 px): ``_AscentFigure`` wraps at the width it draws (``animation_caveats``'
``width_px``)."""
FOOTNOTE_WRAP_MARGIN = 0.01
"""The share of the frame width a wrapped footnote line stops short of the footnote's
right limit (12.8 px at 1280 px): a margin against rounding at the measured width."""
STRUCTURE_FOOTNOTE_TAIL = "first-order sizing, not an assumed penalty"
"""How each modelled run's qualifier in the footnote ends: what the mass is set against,
as every other source words it (fix round 3, H-S3a-P3-01: the mass is a model output on
many assumed coefficients, so the footnote never says it is "not assumed")."""
STRUCTURE_FOOTNOTE_POINTER = (
    "modelled mass by stage: the caveats of summary.md's offload section; structure file "
    "and x* at the physics band's ends: its Structure subsection"
)
"""The clause the footnote's structural line ends with, once per line (S3a gate fix and
its review, R-G1-02 and R-G1-03): where the rest of a modelled run's sizing is read in
summary.md. The offload section's caveats give every structural case's and structure
payload case's mass by stage (the Structure subsection's tables give a case's dm1 and
dm2 but a payload case's dm_0 and dm_1 totals only); the Structure subsection names the
structure file and gives x* (tonnes of offload) of the experiment's cases at the physics
band's ends, 'not flown' at an end no case ran: a different quantity from the band's
sizing-only dm ends at the structure file's headline push (the frozen sets' numbers),
which the replay caveat and the scene frame's per-run note quote with their scope
sentence and which no summary.md prints. The frame states each run's mass (by stage when stage 2
carries any), set, scaling and fired flags and leaves the file's path and those dm ends
off by a choice about vertical space, not width (R-G1-01: the path alone ends 427.5 px
into the 1,260.8 px of a 1280 px footnote line): the path and the dm ends with a
shortened scope sentence take one or two footnote lines more than this pointer on the
tests' selections at 480 and 1280 px (two or three with it kept), and each line past
FOOTNOTE_BASE_LINES moves the panels' bottom up one line (phase file SP7, section 12,
deviation 38). The app's video footer is the footnote's lines with this pointer, not
the full sentence, which an app video frame carries in the scene page's per-run note
(R-G1-04)."""
FOOTNOTE_UNIT_PATTERN = re.compile(r"(g|kg|t)[,.;:)]*")
"""A footnote token that is a bare unit (with trailing punctuation): it is never wrapped
away from the number before it (SP7 step S3a fix round 1, H-S3a-06: '3.0' / 'g')."""
EXPLORATORY_FOOTNOTE = EXPLORATORY_CAVEAT
"""The footnote line prepended for a directory the local app launched (metrics.json
label replay.EXPLORATORY_LABEL; D-SP2-12): the replay page's EXPLORATORY_CAVEAT, the
same string (D-SP2-23: one source per caveat; it ends 1,167 px into the 1,261 px of a
1280 px frame, measured by the test). Step A4 moves the label value to
config.ExperimentLabel and drops this module's import of replay."""


def animation_caveats(
    runs: Sequence[AnimationRun],
    vehicle_name: str | None,
    label: str | None = None,
    width_px: int | None = FOOTNOTE_MEASURE_WIDTH_PX,
) -> list[str]:
    """The footnote lines: the model; its limits and, when a run has an assist push,
    the structural caveat of the push load worded from each run's record, three ways
    (D-SP7-22; SP7 step S3a): no sized structural mass for the peak felt axial g of the
    ASSIST rows of the runs that charge none, when a shown run is a penalty row
    (``AnimationRun.penalty_added_kg``) that the penalty row charges an assumed stage-1
    dry mass (A6v fix round 2: the fixed line and the run's own structure line no longer
    read against each other on a penalty row's frame; one source, D-SP2-23; the clause is
    kept to what the 1280 px footnote line holds, tested, so 'an assumption' is said by
    'assumed' alone), and when a shown run charges a modelled structural mass
    (``AnimationRun.modelled``) that it carries that many kg of modelled structural mass
    (the dm, the modelled increment over the pad envelope, never "a structure" of that
    mass: fix round 1, H-S3a-06) with its set, the plausibility rule's factor when the
    dm carries it and its fired structure flags (with D-SP7-39's comparison beside a
    release flag; fix round 2, H-S3a-P2-04: ``_footnote_qualifier``), a first-order
    sizing, not an assumed penalty (STRUCTURE_FOOTNOTE_TAIL), the mass by stage when the
    record's stage-2 share is above zero (S3a gate fix: '8,900.1 kg (stage 1) and 200.2 kg
    (stage 2) of modelled structural mass', to 0.1 kg as the replay caveat gives it, its
    review's R-G1-05; the total alone otherwise); the vehicle's calibration and the
    replay disclaimer. Three lines, word for word as before, when no
    shown run charges a modelled mass. With one, the structural clauses move to a line of
    their own after the limits line (STRUCTURE_FOOTNOTE_HEAD: the modelled runs first,
    then the penalty rows named with their assumed stage-1 dry mass, which then leaves the
    limits line, then the uncharged pushed runs named, so the "no sized" clause is read
    of them alone and never of a penalty row; fix round 3, H-S3a-P3-02; then, once per
    line, STRUCTURE_FOOTNOTE_POINTER, where in summary.md the mass by stage, the
    structure file and x* at the physics band's ends are read: S3a gate fix), wrapped by
    measured width (``footnote_wrap``) at ``width_px``, the frame's own width when
    ``_AscentFigure`` draws it (fix round 2, N2-03), so every line fits the frame (tested
    at several widths, with the footnote block clear of the panels' axis labels);
    ``width_px`` None leaves the structural line unwrapped, one line, for a caller that
    wraps it itself (the app's video footer, which the scene canvas wraps at the frame's
    own width: fix round 3, S3A-NUM-01, since a line pre-wrapped at 1280 px cost the
    canvas an extra line at every break; the app's video footer is these lines, the
    pointer included). The replay caveat and the scene frame's per-run structure note
    (which an app video frame draws under the video footer, scene.html's
    ``frameFooterLines``) carry the full sentence: the stages, layer, file, the band's
    sizing-only dm ends at the structure file's headline push with their scope sentence
    and the flags' numbers. This footnote, the only caveat of an ``animate`` frame,
    quotes neither the file's path nor those dm ends, by a choice about vertical space,
    not width (the path fits the line; with it and the ends with their scope sentence the
    structural line takes one to three lines more, each moving the panels' bottom up one
    line), and points to summary.md instead, whose Structure subsection gives x* at the
    band's ends, a different quantity (STRUCTURE_FOOTNOTE_POINTER; phase file SP7,
    section 12, deviation 38). ``label``: the directory's metrics.json ``label``;
    EXPLORATORY_LABEL puts EXPLORATORY_FOOTNOTE first, any other value or None adds
    nothing."""
    first = (
        "Planar 2-D model (rotating spherical Earth, ICAO atmosphere, drag); "
        "sweep-optimized guidance, not optimal control."
    )
    second = "Unthrottled (no max-Q or g limit)"
    modelled = [r for r in runs if r.modelled]
    penalty_rows = [r for r in runs if r.penalty_added_kg is not None and not r.modelled]
    structure: list[str] = []
    if modelled:
        structure.append(_footnote_modelled_clause(modelled))
        if penalty_rows:
            verb = "charges" if len(penalty_rows) == 1 else "charge"
            names = _footnote_names([r.name for r in penalty_rows])
            structure.append(f"{names} {verb} an assumed stage-1 dry mass")
        peaks = [
            (r, g)
            for r, g in ((r, r.push_peak_g()) for r in runs if not r.modelled)
            if g and r.penalty_added_kg is None
        ]
        if peaks:
            structure.append(
                f"no sized structural mass for the {max(g for _, g in peaks):.1f} g push load "
                f"of {_footnote_names([r.name for r, _ in peaks])}"
            )
        structure.append(STRUCTURE_FOOTNOTE_POINTER)
    else:
        peaks = [(r, g) for r, g in ((r, r.push_peak_g()) for r in runs) if g]
        if peaks:
            second += (
                f"; no sized structural mass for the {max(g for _, g in peaks):.1f} g push load"
            )
        if len(penalty_rows) == 1:
            second += "; the penalty row charges an assumed stage-1 dry mass"
        elif len(penalty_rows) > 1:
            second += "; the penalty rows charge an assumed stage-1 dry mass"
    third = calibration_caveat(vehicle_name) + " A model replay, not a design result."
    lines = [first, second + "."]
    if structure:
        text = STRUCTURE_FOOTNOTE_HEAD + "; ".join(structure) + "."
        lines += [text] if width_px is None else footnote_wrap(text, width_px)
    lines.append(third)
    if label == EXPLORATORY_LABEL:
        lines.insert(0, EXPLORATORY_FOOTNOTE)
    return lines


def _footnote_qualifier(run: AnimationRun) -> str:
    """The parenthesis after a modelled run's mass in the footnote (fix rounds 2 and 3,
    H-S3a-P2-04 and H-S3a-P3-04): '(set physics_low_mass, scaled x0.846 by the
    plausibility rule; flags fired: structure_release_unload (D-SP7-39: ...) and
    structure_payload_limit; first-order sizing, not an assumed penalty)': the set (when
    recorded) with what its sizing moves off the headline settings ('set central at
    margin 0.05', ``AnimationRun.structure_departures``, so a design-axis row never shares
    the headline case's clause), the plausibility rule's factor when the dm carries it,
    the fired flags by name with the release flag's short comparison, and
    STRUCTURE_FOOTNOTE_TAIL."""
    bits = []
    scale = None
    if run.structure_scale_factor is not None:
        scale = f"scaled x{run.structure_scale_factor:.3g} by the plausibility rule"
    moved = ", ".join(run.structure_departures)
    if run.structure_set is not None:
        head = f"set {run.structure_set}" + (f" at {moved}" if moved else "")
        bits.append(head + ("" if scale is None else f", {scale}"))
    elif moved or scale is not None:
        bits.append(", ".join(b for b in (moved, scale) if b))
    if run.structure_flags_fired:
        names = [
            f"{name} ({run.structure_release_note})"
            if name == FLAG_RELEASE_UNLOAD and run.structure_release_note
            else name
            for name in run.structure_flags_fired
        ]
        bits.append(f"flags fired: {_footnote_names(names)}")
    bits.append(STRUCTURE_FOOTNOTE_TAIL)
    return f"({'; '.join(bits)})"


def _footnote_stage_split(run: AnimationRun) -> str | None:
    """'8,900.1 kg (stage 1) and 200.2 kg (stage 2)': a modelled run's mass by stage in
    the footnote (S3a gate fix), dm1 = dm - dm2 from the record's ``structure_dm_kg`` and
    ``structure_dm_stage2_kg`` as replay's modelled sentence reads them, to 0.1 kg as it
    gives them (summary.modelled_mass_split_text; S3a gate review, R-G1-05: whole kg
    printed a share under 0.5 kg as '0 kg (stage 2)' beside replay's '0.3 kg'), when
    both are recorded and dm2 is above zero; None otherwise (the footnote then gives the
    total alone, as before)."""
    dm, dm2 = run.structure_dm_kg, run.structure_dm_stage2_kg
    if dm is None or dm2 is None or not dm2 > 0.0:
        return None
    return f"{dm - dm2:,.1f} kg (stage 1) and {dm2:,.1f} kg (stage 2)"


def _footnote_modelled_clause(modelled: Sequence[AnimationRun]) -> str:
    """The footnote's clause of the shown runs that charge a modelled structural mass:
    'silo_s1_st carries 9,100 kg of modelled structural mass (set central; first-order
    sizing, not an assumed penalty)' (``_footnote_qualifier``); a run whose stage 2
    carries part of it by stage, 'silo_s1_st carries 8,900.1 kg (stage 1) and 200.2 kg
    (stage 2) of modelled structural mass (...)' (``_footnote_stage_split``; S3a gate
    fix); several runs with one qualifier and no stage split, 'a
    and b carry 9,100 and 9,300 kg of modelled structural mass (...)'; a run whose dm is
    unrecorded 'carries a modelled structural mass of unrecorded size', and among several
    'an unrecorded size' takes its place in the list; runs whose qualifiers differ (a
    set, a scaling, a flag), or among which a run's mass is given by stage (a list of
    stage pairs would not read), get one clause each, joined by '; '."""
    tails = list(dict.fromkeys(_footnote_qualifier(r) for r in modelled))
    split = any(_footnote_stage_split(r) is not None for r in modelled)
    if len(modelled) > 1 and (len(tails) > 1 or split):
        return "; ".join(_footnote_modelled_clause([r]) for r in modelled)
    tail = tails[0]
    names = _footnote_names([r.name for r in modelled])
    if len(modelled) == 1:
        dm = modelled[0].structure_dm_kg
        if dm is None:
            return f"{names} carries a modelled structural mass of unrecorded size {tail}"
        by_stage = _footnote_stage_split(modelled[0])
        mass = f"{dm:,.0f} kg" if by_stage is None else by_stage
        return f"{names} carries {mass} of modelled structural mass {tail}"
    if all(r.structure_dm_kg is not None for r in modelled):
        masses = _footnote_names([f"{r.structure_dm_kg:,.0f}" for r in modelled])
        return f"{names} carry {masses} kg of modelled structural mass {tail}"
    masses = _footnote_names(
        [
            "an unrecorded size" if r.structure_dm_kg is None else f"{r.structure_dm_kg:,.0f} kg"
            for r in modelled
        ]
    )
    return f"{names} carry {masses} of modelled structural mass {tail}"


def _footnote_names(names: Sequence[str]) -> str:
    """'a', 'a and b', 'a, b and c' for the footnote's structural clause."""
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def footnote_tokens(text: str) -> list[str]:
    """The pieces a footnote line may be wrapped between: the words of ``text`` split on
    single spaces, except that a bare unit token (FOOTNOTE_UNIT_PATTERN: 'g', 'kg,', 't.')
    stays glued to the number before it, so '3.0 g' is never split across lines."""
    out: list[str] = []
    for word in text.split(" "):
        if out and FOOTNOTE_UNIT_PATTERN.fullmatch(word) and re.search(r"\d$", out[-1]):
            out[-1] = f"{out[-1]} {word}"
        else:
            out.append(word)
    return out


def footnote_right_px(
    lines: Sequence[str], width_px: int = FOOTNOTE_MEASURE_WIDTH_PX
) -> tuple[list[float], float]:
    """(the right edge of each of ``lines`` drawn as the animation's footnote on a frame
    ``width_px`` wide, the footnote's right limit) [px], measured with the Agg renderer at
    the frame's geometry, the footnote's font size and its left anchor
    (ANIMATION_GRID['left']; the text escaped as the frame escapes it, ``_plot_text``)."""
    size_in, dpi, (frame_w, _frame_h) = frame_geometry(width_px)
    fig = Figure(figsize=size_in, dpi=dpi)
    renderer = FigureCanvasAgg(fig).get_renderer()
    rights = []
    for line in lines:
        artist = fig.text(ANIMATION_GRID["left"], 0.0, _plot_text(line), fontsize=FONT_FOOTNOTE_PT)
        rights.append(float(artist.get_window_extent(renderer=renderer).x1))
        artist.remove()
    return rights, frame_w * ANIMATION_GRID["right"]


def footnote_wrap(text: str, width_px: int = FOOTNOTE_MEASURE_WIDTH_PX) -> list[str]:
    """``text`` wrapped into footnote lines by measured width (SP7 step S3a fix round 1,
    N-S3a-R1-01: a character budget on a proportional font let digit- and wide-glyph
    names run past the frame): greedy over ``footnote_tokens``, each candidate line
    measured by ``footnote_right_px`` on a frame ``width_px`` wide and kept while its
    right edge stays FOOTNOTE_WRAP_MARGIN of the frame width short of the footnote's
    limit; a single token wider than that stands on a line of its own (it cannot be
    split)."""
    tokens = footnote_tokens(text)
    lines: list[str] = []
    current = ""
    for token in tokens:
        candidate = token if not current else f"{current} {token}"
        (right,), limit = footnote_right_px([candidate], width_px)
        if current and right >= limit - FOOTNOTE_WRAP_MARGIN * width_px:
            lines.append(current)
            current = token
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


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
        # the footnote's lines (SP7 step S3a: a modelled run adds a structural line of its
        # own, wrapped at this frame's width, fix round 2, N2-03); beyond the
        # FOOTNOTE_BASE_LINES the grid as drawn leaves room for,
        # the panels' bottom moves up one footnote line per extra line, so the block never
        # reaches the panels' axis labels (tested at 1280 px)
        width_px = round(size_in[0] * dpi - FRAME_PX_EPS)
        self.caveats = animation_caveats(
            runs, vehicle, label=metrics.get("label"), width_px=width_px
        )
        extra = max(0, len(self.caveats) - FOOTNOTE_BASE_LINES)
        per_line = FONT_FOOTNOTE_PT * FOOTNOTE_LINE_SPACING / POINTS_PER_INCH / size_in[1]
        grid = {**ANIMATION_GRID, "bottom": ANIMATION_GRID["bottom"] + extra * per_line}
        gs = self.fig.add_gridspec(1, 2, width_ratios=(ANIMATION_MAIN_WIDTH_RATIO, 1.0), **grid)
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
        self.footnote = self.fig.text(
            ANIMATION_GRID["left"],
            0.012,
            _plot_text("\n".join(self.caveats)),
            fontsize=FONT_FOOTNOTE_PT,
            color=ANIMATION_FOOTNOTE_COLOR,
            va="bottom",
            linespacing=FOOTNOTE_LINE_SPACING,
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
