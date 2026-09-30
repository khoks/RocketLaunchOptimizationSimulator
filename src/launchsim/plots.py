"""Plot writers of a run (moved from sim.py; I/O: writes PNG files).

``write_plots`` draws one PNG per panel of ``plot_panels`` (PLOT_PANELS, plus
PLOT_TRACK_PANELS for a run with a track phase) against the time since release, from
the run's time series (SI columns; the unit is in each axis label). A planar_2d run
gets ``write_planar_plots`` instead: PLANAR_PLOT_PANELS (altitude against downrange,
|v_rel| and |v_in|, gamma_rel and pitch in degrees, q and Mach, mass and thrust, felt
g, the cumulative losses), plus the track panels. Figures are built from
matplotlib.figure.Figure and saved through the Agg canvas that PNG output selects, so
no pyplot state and no global backend switch is involved. ``sim`` re-exports every
name.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from launchsim.config import PLANAR_2D
from launchsim.phases import ASSIST_KIND
from launchsim.units import m_to_km, rad_to_deg

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


PLOT_STEM_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def plot_stem(prefix: str, quantity: str) -> str:
    """File stem ``<prefix>_<quantity>`` with every run of characters outside
    ``[A-Za-z0-9_.-]`` replaced by ``_`` (a name such as ``F/N`` becomes ``F_N``)."""
    return PLOT_STEM_UNSAFE.sub("_", f"{prefix}_{quantity}")


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
