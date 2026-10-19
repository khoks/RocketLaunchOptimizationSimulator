"""SP7 step S7a: the derived figures of docs/findings/RQ1-structural-2d.md.

Draws, from the step's three results directories (read-only: never writes under
results/) and from the sizing-only tables' data that sp7_structure_tables.py writes
(docs/findings/RQ1-structural-2d-tables.json), these PNGs in docs/findings/:

- RQ1-structural-2d-derived_headline_rows.png: the headline table as a chart: SP1's
  uncharged x* and its three assumed penalty rows (as run A reproduced them), every
  structural row of run A with the physics band and the outer envelope as ranges, the
  other pushes beside their own uncharged x*, file C's central beside its own uncharged
  x*, 50% of SP1's 41.26 t marked; no-offload rows with their delta-v shortfall and the
  payload deficit of their payload case.
- RQ1-structural-2d-derived_sweep1_exit_speed.png: sweep 1's x* against the exit speed,
  uncharged and with the central structure, 0 marked.
- RQ1-structural-2d-derived_sweep2_depth.png: sweep 2's x* against the stroke and against
  the felt load, uncharged and with the central structure.
- RQ1-structural-2d-derived_elements.png: the central case's dm by element at its solved
  x*, with each element's governing push and envelope modes.
- RQ1-structural-2d-derived_dm_vs_felt_load.png: sizing only (no flight): the central
  structure's dm against the felt load at the fixed exit speed, by element group, at
  SP1's headline offload, with the x = 0 total beside.

It also copies (byte for byte, never redrawn) run A's and run C's own structure figures
of the headline case and of three rows into docs/findings/ with the RQ1-structural-2d-
prefix, as SP1 copied its RQ1-2d-*.png. Every plotted number comes from a named results
file or the tables' data; each figure's footer names its sources and caveats. Run from
the repository root after the tables script:
``uv run python docs/findings/scripts/sp7_structure_figures.py``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import blended_transform_factory

from launchsim.plots import PLOT_DPI
from launchsim.units import kg_to_t

REPO = Path(__file__).resolve().parents[3]
RUN_A = REPO / "results" / "silo_structure_2d" / "20261016T171513Z"
SWEEP_A = REPO / "results" / "silo_structure_2d" / "20261016T171522Z"
RUN_C = REPO / "results" / "silo_structure_2d_readme" / "20261016T171529Z"
TABLES_JSON = REPO / "docs" / "findings" / "RQ1-structural-2d-tables.json"
OUT_DIR = REPO / "docs" / "findings"
PREFIX = "RQ1-structural-2d-"

COPIES: tuple[tuple[Path, str], ...] = (
    (RUN_A / "plots" / "silo_cold_s1_st_structure.png", "silo_cold_s1_st_structure.png"),
    (RUN_A / "plots" / "silo_cold_s1_st_step_structure.png", "silo_cold_s1_st_step_structure.png"),
    (
        RUN_A / "plots" / "silo_cold_s1_st_phys_hi_structure.png",
        "silo_cold_s1_st_phys_hi_structure.png",
    ),
    (RUN_A / "plots" / "silo_cold_s1_st_ts_structure.png", "silo_cold_s1_st_ts_structure.png"),
    (RUN_C / "plots" / "silo_cold_s1_st_structure.png", "readme_silo_cold_s1_st_structure.png"),
)
"""The run's own figures copied unchanged: (source, name after PREFIX)."""

# The look: SP1's derived figures (RQ1-2d-derived_*.png) and plots.py's (a light surface,
# hairline grid, no top or right spines), the dataviz palette's first slots in fixed order.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
MAGENTA = "#e87ba4"
GREY = "#898781"
"""Slots 1-5 (blue, orange, aqua, yellow, magenta) pass the dataviz validator's adjacent
checks on the light surface; aqua, yellow and magenta sit below 3:1 contrast there, so
every figure that uses them carries a legend and direct labels or its table."""
FIG_W_IN = 9.0
FONT = 8.5
FONT_SMALL = 7.5
FONT_FOOT = 7.0
FOOT_WRAP = 150
FONT_ROW = 7.0
ROW_TEXT_WRAP = 62
"""The headline chart's right-hand text column: font [pt] and wrap width [characters]."""
MARKER = 7.0
RING = 1.4
GATE_CAVEAT = (
    "Gate vehicle (generic_f9_class_2d, calibrates +14.3% high on payload, "
    "docs/findings/CAL-f9-leo-2d); sweep-optimized guidance, unthrottled, planar; x* = the "
    "solved stage-1 propellant offload at P_ref (26,054.4 kg, the pad's own P*), tanks "
    "partly filled; prescribed constant_accel drive, massless carriage, vented shaft, no "
    "exhaust in the shaft modelled."
)
STRUCTURE_CAVEAT = (
    "Modelled rows: a first-order station sizing of the push load for the offloaded "
    "stack (D-SP7-01), not a detailed structural design: central coefficients, an assumed "
    "real-drive rise time of 0.5 s that the constant_accel trajectory does not fly (its "
    "plateau cost charged), the pad's own unthrottled flight as the envelope, zero margin; "
    "the instant release (flagged, not sized) is not charged."
)


# ----------------------------------------------------------------------------- reading


def read_json(path: Path) -> dict[str, Any]:
    """A JSON file as a dict (read-only)."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_index(path: Path) -> list[dict[str, str]]:
    """A sweep_index.csv as rows (read-only)."""
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def cases_by_name(metrics: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """A run's offload case records by name."""
    return {c["name"]: c for c in metrics["offload"]["cases"]}


SETTING_KEYS = (
    "of",
    "structure_set",
    "structure_dynamic",
    "structure_entry",
    "structure_margin",
    "structure_envelope_cap_g",
    "structure_plausibility_scaled",
)
"""The settings a no-offload row and its payload case share (the sizing basis aside)."""


def payload_case_for(case: Mapping[str, Any], metrics: Mapping[str, Any]) -> dict | None:
    """The structure payload case flown at a case's settings (the same variant, set,
    dynamic mode, entry, margin, cap, overrides and scaling; the sizing basis aside), as
    the summary's no-offload line pairs them; None when there is none."""
    for p in metrics["offload"].get("structure_payload_cases", []):
        if all(p.get(k) == case.get(k) for k in SETTING_KEYS) and (
            p.get("structure_overrides") or {}
        ) == (case.get("structure_overrides") or {}):
            return p
    return None


def no_offload_text(case: Mapping[str, Any], metrics: Mapping[str, Any]) -> str:
    """'no offload (s m/s short at x = 0; payload deficit d kg, residual r kg)' for a
    no_offload row (the solve's dv_shortfall_mps; the payload case's payload_delta_kg,
    its two-pass P_2* - P_ref, and, when its unconverged flag fired, its
    residual_estimate_kg), or 'payload deficit not flown' without a payload case."""
    short = case["solve"].get("dv_shortfall_mps")
    parts = [] if short is None else [f"{short:,.0f} m/s short at x = 0"]
    p = payload_case_for(case, metrics)
    if p is None:
        parts.append("payload deficit not flown")
    else:
        deficit = f"payload deficit {p['payload_delta_kg']:+,.0f} kg"
        if p.get("unconverged"):
            deficit += f", residual {p['residual_estimate_kg']:.2f} kg"
        parts.append(deficit)
    return f"no offload ({'; '.join(parts)})"


def dm_t(case: Mapping[str, Any]) -> str:
    """'dm 6.31 t' (stage 1 + stage 2 at x*; at x = 0 for no offload) or with the split."""
    dm = float(case["structure_dm_kg"])
    dm2 = float(case.get("structure_dm_stage2_kg") or 0.0)
    if dm2 > 0.0:
        return f"dm {kg_to_t(dm - dm2):.2f} + {kg_to_t(dm2):.2f} t"
    return f"dm {kg_to_t(dm):.2f} t"


# ----------------------------------------------------------------------------- drawing


def new_figure(height_in: float) -> Figure:
    """A figure on the chart surface (no pyplot state; saved through the Agg canvas)."""
    fig = Figure(figsize=(FIG_W_IN, height_in), dpi=PLOT_DPI, facecolor=SURFACE)
    FigureCanvasAgg(fig)
    return fig


def style_axes(ax: Any) -> None:
    """Hairline grid, no top or right spine, muted baseline and ticks."""
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
    ax.tick_params(colors=INK2, labelsize=FONT, length=3)


UNIT_TOKEN = re.compile(r"(kg|t|m|g0|m/s|MN|%|s)[,;:.)]*")
"""A bare unit word that stays on the line of the number before it."""


def wrap_glued(text: str, width: int) -> list[str]:
    """Greedy word wrap of ``text`` at ``width`` characters that never splits a number
    from its unit ('-7,804 kg' stays on one line)."""
    tokens: list[str] = []
    for word in text.split():
        if tokens and UNIT_TOKEN.fullmatch(word) and re.search(r"\d\)?$", tokens[-1]):
            tokens[-1] = f"{tokens[-1]} {word}"
        else:
            tokens.append(word)
    lines: list[str] = []
    line = ""
    for token in tokens:
        candidate = token if not line else f"{line} {token}"
        if line and len(candidate) > width:
            lines.append(line)
            line = token
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def footer(fig: Figure, paragraphs: Sequence[str]) -> float:
    """Write the caveat footer at the bottom left; returns its height as a figure
    fraction (the axes are placed above it)."""
    lines: list[str] = []
    for p in paragraphs:
        lines += wrap_glued(p, FOOT_WRAP)
    fig.text(
        0.012,
        0.012,
        "\n".join(lines),
        fontsize=FONT_FOOT,
        color=INK2,
        va="bottom",
        linespacing=1.35,
    )
    line_in = FONT_FOOT * 1.35 / 72.0
    return (len(lines) * line_in + 0.12) / fig.get_figheight()


def title(fig: Figure, text: str, sub: str | None = None) -> None:
    """The figure's title (and an optional subtitle) at the top left."""
    fig.text(0.012, 0.985, text, fontsize=11, color=INK, va="top")
    if sub:
        fig.text(0.012, 0.952, sub, fontsize=FONT_SMALL, color=INK2, va="top")


def save(fig: Figure, name: str) -> Path:
    """Save docs/findings/<PREFIX><name> and return its path."""
    path = OUT_DIR / f"{PREFIX}{name}"
    fig.savefig(path, dpi=PLOT_DPI, facecolor=SURFACE)
    return path


def dot(ax: Any, x: float, y: float, color: str, *, hollow: bool = False, marker: str = "o"):
    """A marker with a surface ring (filled) or a hollow one."""
    ax.plot(
        [x],
        [y],
        marker=marker,
        markersize=MARKER,
        markerfacecolor=SURFACE if hollow else color,
        markeredgecolor=color if hollow else SURFACE,
        markeredgewidth=1.6 if hollow else RING,
        linestyle="none",
        zorder=5,
    )


# ------------------------------------------------------------------- 1. headline rows


@dataclass
class Row:
    """One row of the headline chart: label; kind ('penalty', 'modelled', 'range' or
    'group'); x [kg] (None: no offload); text beside it; for a range its two ends and the
    unscaled end; for another push its own uncharged x [kg] and a 50% tick [kg]."""

    label: str
    kind: str
    x_kg: float | None = None
    text: str = ""
    lo_kg: float | None = None
    hi_kg: float | None = None
    mid_kg: float | None = None
    color: str = BLUE
    uncharged_kg: float | None = None
    half_kg: float | None = None


def x_of(case: Mapping[str, Any]) -> float | None:
    """A case's solved x* [kg], None for no offload."""
    return None if case["status"] == "no_offload" else float(case["offload_kg"])


def modelled_text(case: Mapping[str, Any], metrics: Mapping[str, Any]) -> str:
    """'11.42 t (27.7%; dm 6.31 t)' or the no-offload text with dm at x = 0."""
    x = x_of(case)
    if x is None:
        return f"{no_offload_text(case, metrics)}; {dm_t(case)} at x = 0"
    return f"{kg_to_t(x):.2f} t ({100.0 * x / HEADLINE_KG:.1f}%; {dm_t(case)})"


HEADLINE_KG = 41262.90803733282
"""SP1's uncharged headline x* [kg] (pre-registration section 9), the reading rules' base."""


def headline_rows(a: Mapping[str, Any], c: Mapping[str, Any]) -> list[Row]:
    """The rows of the headline chart, from run A's and run C's case records."""
    ca, cc = cases_by_name(a), cases_by_name(c)

    def penalty(name: str, label: str) -> Row:
        x = float(ca[name]["offload_kg"])
        return Row(label, "penalty", x, f"{kg_to_t(x):.2f} t ({100.0 * x / HEADLINE_KG:.1f}%)")

    def modelled(name: str, label: str) -> Row:
        return Row(label, "modelled", x_of(ca[name]), modelled_text(ca[name], a))

    def band(lo: str, hi: str, mid: str | None, label: str, color: str) -> Row:
        lo_x, hi_x = x_of(ca[lo]), x_of(ca[hi])
        lo_t = no_offload_text(ca[lo], a) if lo_x is None else f"{kg_to_t(lo_x):.2f} t"
        hi_t = no_offload_text(ca[hi], a) if hi_x is None else f"{kg_to_t(hi_x):.2f} t"
        text = f"{lo_t} to {hi_t}"
        mid_x = None if mid is None else x_of(ca[mid])
        if mid_x is not None:
            text += f" ({kg_to_t(mid_x):.2f} t unscaled)"
        return Row(label, "range", None, text, lo_x, hi_x, mid_x, color)

    def other(name: str, un: str, label: str, cases: Mapping[str, Any], m: Mapping) -> Row:
        u = float(cases[un]["offload_kg"])
        r = Row(label, "modelled", x_of(cases[name]), "", uncharged_kg=u)
        x = x_of(cases[name])
        own = "" if x is None else f"; {100.0 * x / u:.1f}% of its own {kg_to_t(u):.2f} t"
        r.text = (
            modelled_text(cases[name], m)
            if x is None
            else f"{kg_to_t(x):.2f} t ({dm_t(cases[name])}{own})"
        )
        return r

    rows = [
        Row("SP1's rows as run A reproduced them (assumed penalty, not sized structure)", "group"),
        penalty("silo_cold_s1", "uncharged (silo_cold_s1)"),
        penalty("silo_cold_s1_dry+2t", "+2.0 t stage-1 dry mass, assumed"),
        penalty("silo_cold_s1_dry+4t", "+4.0 t stage-1 dry mass, assumed"),
        penalty("silo_cold_s1_dry+8.1t", "+8.1 t stage-1 dry mass, assumed"),
        Row("Modelled structure at the headline push (3 g0, 100 m, cold start)", "group"),
        modelled("silo_cold_s1_st", "central (silo_cold_s1_st)"),
        band(
            "silo_cold_s1_st_phys_hi",
            "silo_cold_s1_st_phys_lo_scaled",
            "silo_cold_s1_st_phys_lo",
            "physics band (phys_hi to phys_lo scaled)",
            BLUE,
        ),
        band(
            "silo_cold_s1_st_outer_hi",
            "silo_cold_s1_st_outer_lo",
            None,
            "outer envelope (outer_hi to outer_lo)",
            ORANGE,
        ),
        modelled("silo_cold_s1_st_qs", "quasi-static push, DLF 1 (_qs)"),
        modelled("silo_cold_s1_st_step", "step push, DLF 2 (_step)"),
        modelled("silo_cold_s1_st_full", "sized for the full load (_full)"),
        modelled("silo_cold_s1_st_ts", "entry through the thrust structure (_ts)"),
        modelled("silo_cold_s1_st_m10", "10% margin on the envelope (_m10)"),
        modelled("silo_cold_s1_st_m25", "25% margin on the envelope (_m25)"),
        modelled("silo_cold_s1_st_cap45", "envelope capped at 4.5 g0 (_cap45)"),
        modelled("silo_cold_s1_st_cap40", "envelope capped at 4.0 g0 (_cap40)"),
        Row("Other pushes, central structure (hollow: the row's own uncharged x*)", "group"),
        other(
            "silo_hot_full_s1_st", "silo_hot_full_s1", "hot start, full thrust on the track", ca, a
        ),
        other("silo_hot_ramp_s1_st", "silo_hot_ramp_s1", "hot start, ramp on the track", ca, a),
        other("silo_cold_200m_s1_st", "silo_cold_200m_s1", "200 m at 1.5 g0 (felt 2.5 g0)", ca, a),
        Row("README-loads fork (file C), read against its own uncharged x*", "group"),
        other("silo_cold_s1_st", "silo_cold_s1", "central on the fork (tick: its 50%)", cc, c),
    ]
    rows[-1].half_kg = 0.5 * float(cc["silo_cold_s1"]["offload_kg"])
    return rows


def legend_handles(items: Sequence[tuple[str, str, str]]) -> list[Any]:
    """Legend handles from (kind, colour, label): 'square' and 'dot' filled markers,
    'hollow' a hollow dot, 'line' a line with a dot, 'patch' a range swatch."""
    out: list[Any] = []
    for kind, color, label in items:
        if kind == "patch":
            out.append(Patch(facecolor=color, alpha=0.3, label=label))
            continue
        out.append(
            Line2D(
                [],
                [],
                marker="s" if kind == "square" else "o",
                color=color,
                markerfacecolor=SURFACE if kind == "hollow" else color,
                markeredgecolor=color if kind == "hollow" else SURFACE,
                markeredgewidth=1.6 if kind == "hollow" else RING,
                markersize=MARKER,
                ls="-" if kind in ("line", "line_square") else "none",
                lw=2.0,
                label=label,
            )
        )
    return out


def draw_row(ax: Any, y: float, r: Row) -> None:
    """One row's marks: a square (SP1's rows), a range with its ends (hollow at no
    offload) and the unscaled end as a bar, or a solved dot (hollow at no offload) with
    the row's own uncharged x* hollow and grey and joined to it, and a 50% tick."""
    if r.kind == "penalty":
        dot(ax, kg_to_t(r.x_kg or 0.0), y, GREY, marker="s")
        return
    if r.kind == "range":
        lo = 0.0 if r.lo_kg is None else kg_to_t(r.lo_kg)
        hi = 0.0 if r.hi_kg is None else kg_to_t(r.hi_kg)
        ax.fill_between([lo, hi], y - 0.2, y + 0.2, color=r.color, alpha=0.18, lw=0, zorder=3)
        dot(ax, lo, y, r.color, hollow=r.lo_kg is None)
        dot(ax, hi, y, r.color, hollow=r.hi_kg is None)
        if r.mid_kg is not None:
            m = kg_to_t(r.mid_kg)
            ax.plot([m, m], [y - 0.25, y + 0.25], color=r.color, lw=2.0, zorder=4)
        return
    x = 0.0 if r.x_kg is None else kg_to_t(r.x_kg)
    if r.uncharged_kg is not None:
        u = kg_to_t(r.uncharged_kg)
        ax.plot([x, u], [y, y], color=MUTED, lw=1.0, zorder=3)
        dot(ax, u, y, GREY, hollow=True)
    if r.half_kg is not None:
        h = kg_to_t(r.half_kg)
        ax.plot([h, h], [y - 0.28, y + 0.28], color=INK2, lw=1.4, zorder=4)
    dot(ax, x, y, BLUE, hollow=r.x_kg is None)


def figure_headline(a: Mapping[str, Any], c: Mapping[str, Any]) -> Path:
    """The headline table as a chart (see the module docstring): row labels on the left,
    the marks in the middle, each row's numbers in a text column on the right."""
    rows = headline_rows(a, c)
    fig = new_figure(10.8)
    title(
        fig,
        "Stage-1 offload with the push load's structure charged (run A; file C last)",
        "x* at P_ref against SP1's uncharged 41.26 t and its assumed penalty rows; both "
        "ends of a range are solved cases",
    )
    foot = footer(
        fig,
        [
            "Sources: results/silo_structure_2d/20261016T171513Z/metrics.json and "
            "results/silo_structure_2d_readme/20261016T171529Z/metrics.json (offload.cases: "
            "offload_kg, status, structure_dm_kg, structure_dm_stage2_kg, "
            "solve.dv_shortfall_mps; offload.structure_payload_cases: payload_delta_kg, "
            "residual_estimate_kg). %: of SP1's uncharged 41,262.9 kg. dm: the modelled "
            "stage-1 (+ stage-2) mass at x* (at x = 0 for no offload). A no-offload row: "
            "the solve's delta-v shortfall of P_ref at x = 0, and its payload deficit, the "
            "payload case's P_2* - P_ref after two passes at the same settings (full-load "
            "sizing), with that case's residual estimate where its unconverged flag fired. "
            "The band's low-mass end is the plausibility-scaled case (factor 0.739 on its "
            "whole dm, D-SP7-41; the bar: the unscaled end).",
            GATE_CAVEAT,
            STRUCTURE_CAVEAT,
        ],
    )
    top = 0.862
    bottom = foot + 0.05
    left, width = 0.30, 0.30
    ax = fig.add_axes((left, bottom, width, top - bottom))
    style_axes(ax)
    n = len(rows)
    ys = list(range(n, 0, -1))
    ax.set_ylim(0.4, n + 0.6)
    ax.set_xlim(-1.5, 48.0)
    half = kg_to_t(0.5 * HEADLINE_KG)
    ax.axvline(half, color=INK2, linewidth=1.0, linestyle=(0, (4, 3)), zorder=2)
    ax.axvline(kg_to_t(HEADLINE_KG), color=MUTED, linewidth=1.0, linestyle=(0, (1, 2)), zorder=2)
    ax.axvline(0.0, color=BASELINE, linewidth=1.2, zorder=2)
    for x, text, ha in (
        (half, "50%: 20.63 t", "center"),
        (kg_to_t(HEADLINE_KG), "41.26 t", "center"),
    ):
        ax.text(
            x,
            1.005,
            text,
            transform=ax.get_xaxis_transform(),
            ha=ha,
            va="bottom",
            fontsize=FONT_SMALL,
            color=INK2,
        )
    row_text = blended_transform_factory(fig.transFigure, ax.transData)
    for y, r in zip(ys, rows, strict=True):
        if r.kind == "group":
            fig.text(
                0.012,
                y,
                r.label,
                transform=row_text,
                fontsize=FONT_SMALL,
                fontweight="bold",
                color=INK,
                va="center",
                bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.0},
            )
            continue
        draw_row(ax, y, r)
        fig.text(
            left + width + 0.012,
            y,
            "\n".join(wrap_glued(r.text, ROW_TEXT_WRAP)),
            transform=row_text,
            fontsize=FONT_ROW,
            color=INK,
            va="center",
            linespacing=1.15,
        )
    ax.set_yticks([y for y, r in zip(ys, rows, strict=True) if r.kind != "group"])
    ax.set_yticklabels([r.label for r in rows if r.kind != "group"], fontsize=FONT_SMALL)
    ax.tick_params(axis="y", length=0)
    ax.grid(False, axis="y")
    ax.set_xlabel("stage-1 propellant offload x* at P_ref [t]", fontsize=FONT, color=INK)
    fig.legend(
        handles=legend_handles(
            (
                ("square", GREY, "SP1's uncharged and assumed penalty rows"),
                ("dot", BLUE, "modelled structure: solved x*"),
                ("hollow", BLUE, "no offload (x* = 0)"),
                ("patch", BLUE, "physics band"),
                ("patch", ORANGE, "outer envelope"),
                ("hollow", GREY, "the row's own uncharged x*"),
            )
        ),
        loc="upper left",
        bbox_to_anchor=(0.012, 0.935),
        ncols=3,
        fontsize=FONT_SMALL,
        frameon=False,
        columnspacing=1.6,
        handletextpad=0.5,
    )
    return save(fig, "derived_headline_rows.png")


# --------------------------------------------------------------------------- 2. sweep 1


def sweep_points(k: int, un: str, st: str) -> list[dict[str, Any]]:
    """Sweep k's points from sweep A's index: stroke, exit speed, the uncharged and the
    structural status and x* [kg], the structural dm and its stage-2 part [kg], the
    point run's peak felt load on the track [g0] (its metrics.json)."""
    out = []
    for r in read_index(SWEEP_A / f"sweep_{k}" / "sweep_index.csv"):
        point = read_json(SWEEP_A / r["run_dir"] / "metrics.json")
        out.append(
            {
                "stroke_m": float(r["assist.stroke_m"]),
                "exit_mps": float(r["exit_speed_mps"]),
                "un_status": r[f"{un}.status"],
                "un_kg": float(r[f"{un}.offload_kg"]),
                "st_status": r[f"{st}.status"],
                "st_kg": float(r[f"{st}.offload_kg"]),
                "dm_kg": float(r[f"{st}.structure_dm_kg"]),
                "dm2_kg": float(r[f"{st}.structure_dm_stage2_kg"]),
                "felt_g": float(point["metrics"]["felt_g_track_peak"]),
                "kick_unconstrained": r["unconstrained_kick"] == "True",
            }
        )
    return out


def draw_pair(ax: Any, xs: Sequence[float], pts: Sequence[Mapping[str, Any]]) -> None:
    """The uncharged and the structural x* [t] of a sweep's points against xs: lines with
    markers; a no-offload point hollow at 0, and the segment from it to the next
    offloading point dotted (nothing is measured between the points)."""
    un = [kg_to_t(p["un_kg"]) for p in pts]
    st = [kg_to_t(p["st_kg"]) for p in pts]
    ax.plot(xs, un, color=GREY, lw=2.0, zorder=3, solid_capstyle="round")
    for x, y in zip(xs, un, strict=True):
        dot(ax, x, y, GREY, marker="s")
    for i in range(len(pts) - 1):
        dashed = pts[i]["st_status"] == "no_offload" or pts[i + 1]["st_status"] == "no_offload"
        ax.plot(
            xs[i : i + 2],
            st[i : i + 2],
            color=BLUE,
            lw=2.0,
            ls=(0, (1, 2)) if dashed else "-",
            zorder=3,
            solid_capstyle="round",
        )
    for x, y, p in zip(xs, st, pts, strict=True):
        dot(ax, x, y, BLUE, hollow=p["st_status"] == "no_offload")
    ax.axhline(0.0, color=BASELINE, lw=1.2, zorder=2)


def figure_sweep1() -> Path:
    """Sweep 1: x* against the exit speed, uncharged and with the central structure."""
    pts = sweep_points(1, "silo_cold_s1", "silo_cold_s1_st")
    fig = new_figure(5.6)
    title(
        fig,
        "Sweep 1: stage-1 offload against exit speed, with and without the structure",
        "silo_cold at 3 g0 net (felt about 4.0 g0), stroke 25 to 300 m; the central "
        "structure re-sized at every offload",
    )
    foot = footer(
        fig,
        [
            "Source: results/silo_structure_2d/20261016T171522Z/sweep_1/sweep_index.csv "
            "(silo_cold_s1.offload_kg, silo_cold_s1_st.offload_kg, .status, "
            ".structure_dm_kg). No offload: x* = 0, the modelled structure costs more offload "
            "than the push gives at that point (the sweep records no shortfall; payload "
            "deficit not flown). Dotted: between a no-offload point and the next, nothing is "
            "measured. At 25 and 50 m the coast slows below the kick speed before ignition "
            "(a vertical rise first); the 300 m point's kick comes above 120 m/s, an upper "
            "bound.",
            GATE_CAVEAT,
            STRUCTURE_CAVEAT,
        ],
    )
    ax = fig.add_axes((0.085, foot + 0.09, 0.89, 0.86 - foot - 0.09))
    style_axes(ax)
    xs = [p["exit_mps"] for p in pts]
    draw_pair(ax, xs, pts)
    for x, p in zip(xs, pts, strict=True):
        st = kg_to_t(p["st_kg"])
        if p["st_status"] == "no_offload":
            ax.annotate(
                f"no offload\n(dm {kg_to_t(p['dm_kg']):.2f} t at x = 0)",
                (x, 0.0),
                xytext=(0, -11),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=FONT_SMALL,
                color=INK,
            )
        else:
            ax.annotate(
                f"{st:.2f} t",
                (x, st),
                xytext=(8, -4),
                textcoords="offset points",
                ha="left",
                va="top",
                fontsize=FONT_SMALL,
                color=INK,
            )
        un = kg_to_t(p["un_kg"])
        tag = f"{p['stroke_m']:g} m"
        if p["kick_unconstrained"]:
            tag += " (upper bound)"
        ax.annotate(
            f"{un:.2f} t, {tag}",
            (x, un),
            xytext=(-6, 8),
            textcoords="offset points",
            ha="right" if x > 120 else "center",
            va="bottom",
            fontsize=FONT_SMALL,
            color=INK2,
        )
    ax.set_xlim(30, 140)
    ax.set_ylim(-16, 76)
    ax.set_yticks([0, 10, 20, 30, 40, 50, 60, 70])
    ax.set_xlabel("release (exit) speed [m/s]", fontsize=FONT, color=INK)
    ax.set_ylabel("stage-1 propellant offload at P_ref [t]", fontsize=FONT, color=INK)
    handles = [
        Line2D(
            [],
            [],
            color=GREY,
            marker="s",
            markeredgecolor=SURFACE,
            markersize=MARKER,
            lw=2,
            label="uncharged (silo_cold_s1)",
        ),
        Line2D(
            [],
            [],
            color=BLUE,
            marker="o",
            markeredgecolor=SURFACE,
            markersize=MARKER,
            lw=2,
            label="central structure (silo_cold_s1_st)",
        ),
        Line2D(
            [],
            [],
            color=BLUE,
            marker="o",
            markerfacecolor=SURFACE,
            markersize=MARKER,
            markeredgewidth=1.6,
            ls="none",
            label="no offload (x* = 0)",
        ),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=FONT_SMALL, frameon=False)
    return save(fig, "derived_sweep1_exit_speed.png")


# --------------------------------------------------------------------------- 3. sweep 2


def figure_sweep2() -> Path:
    """Sweep 2: x* against the stroke and the felt load at the fixed exit speed."""
    pts = sweep_points(2, "silo_cold_200m_s1", "silo_cold_200m_s1_st")
    fig = new_figure(5.4)
    title(
        fig,
        "Sweep 2: stage-1 offload against silo depth at a fixed exit speed (76.71 m/s)",
        "silo_cold_200m's push at 6, 3, 1.5 and 1 g0 net (stroke 50 to 300 m); the same "
        "points against the stroke (left) and against the felt load (right)",
    )
    foot = footer(
        fig,
        [
            "Sources: results/silo_structure_2d/20261016T171522Z/sweep_2/sweep_index.csv "
            "(silo_cold_200m_s1.offload_kg, silo_cold_200m_s1_st.offload_kg, .status, "
            ".structure_dm_kg, .structure_dm_stage2_kg) and each point's metrics.json "
            "(felt_g_track_peak, the push's felt load). The uncharged offload is the same at "
            "every point (the flight after release does not see the stroke). No offload: x* "
            "= 0 (the sweep records no shortfall; payload deficit not flown); at 50 m the "
            "push also sizes stage 2 and the interstage.",
            GATE_CAVEAT,
            STRUCTURE_CAVEAT,
        ],
    )
    bottom = foot + 0.10
    height = 0.82 - bottom
    ax_l = fig.add_axes((0.085, bottom, 0.42, height))
    ax_r = fig.add_axes((0.565, bottom, 0.42, height), sharey=ax_l)
    for ax, key, xlabel in (
        (ax_l, "stroke_m", "stroke L [m] (facility L + 60 m)"),
        (ax_r, "felt_g", "felt load of the push on the track [g0] (falls to the right)"),
    ):
        style_axes(ax)
        xs = [p[key] for p in pts]
        draw_pair(ax, xs, pts)
        for x, p in zip(xs, pts, strict=True):
            if p["st_status"] == "no_offload":
                text = f"no offload\n(dm {kg_to_t(p['dm_kg'] - p['dm2_kg']):.2f}"
                if p["dm2_kg"] > 0.0:
                    text += f" + {kg_to_t(p['dm2_kg']):.2f} t,\nstage 2 sized)"
                else:
                    text += " t)"
                ax.annotate(
                    text,
                    (x, 0.0),
                    xytext=(-4, -9),
                    textcoords="offset points",
                    ha="left",
                    va="top",
                    fontsize=FONT_SMALL,
                    color=INK,
                )
            else:
                st = kg_to_t(p["st_kg"])
                last = p is pts[-1]
                ax.annotate(
                    f"{st:.2f} t",
                    (x, st),
                    xytext=(-6, 6) if last else (8, -4),
                    textcoords="offset points",
                    ha="right" if last else "left",
                    va="bottom" if last else "top",
                    fontsize=FONT_SMALL,
                    color=INK,
                )
        ax.set_xlabel(xlabel, fontsize=FONT, color=INK)
    ax_l.set_xlim(25, 325)
    ax_r.set_xlim(7.6, 1.4)
    ax_r.tick_params(labelleft=False)
    ax_l.set_ylim(-22, 50)
    ax_l.set_yticks([0, 10, 20, 30, 40, 50])
    ax_l.set_ylabel("stage-1 propellant offload at P_ref [t]", fontsize=FONT, color=INK)
    ax_l.annotate(
        f"uncharged {kg_to_t(pts[0]['un_kg']):.2f} t at every point",
        (175, kg_to_t(pts[0]["un_kg"])),
        xytext=(0, 6),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=FONT_SMALL,
        color=INK2,
    )
    handles = [
        Line2D(
            [],
            [],
            color=GREY,
            marker="s",
            markeredgecolor=SURFACE,
            markersize=MARKER,
            lw=2,
            label="uncharged (silo_cold_200m_s1)",
        ),
        Line2D(
            [],
            [],
            color=BLUE,
            marker="o",
            markeredgecolor=SURFACE,
            markersize=MARKER,
            lw=2,
            label="central structure (silo_cold_200m_s1_st)",
        ),
        Line2D(
            [],
            [],
            color=BLUE,
            marker="o",
            markerfacecolor=SURFACE,
            markersize=MARKER,
            markeredgewidth=1.6,
            ls="none",
            label="no offload (x* = 0)",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.08, 0.925),
        ncols=3,
        fontsize=FONT_SMALL,
        frameon=False,
    )
    return save(fig, "derived_sweep2_depth.png")


# ------------------------------------------------------------------------- 4. elements

MODE_WORDS = {
    "ring_common_z": "stiffened buckling",
    "ring_bending": "ring bending",
    "membrane": "membrane",
    "min_gauge": "minimum gauge",
    "combined": "combined stress",
    "monocoque": "monocoque buckling",
    "hoop": "hoop",
    "relation": "its mass relation",
}
"""The governing modes in short words (the footer gives the record's names)."""
ELEMENT_WORDS = {
    "aft_skirt": "aft skirt",
    "load_ring": "load ring",
    "rp1_aft_dome": "RP-1 aft dome",
    "rp1_barrel": "RP-1 barrel",
    "common_dome": "common dome",
    "lox_barrel": "LOX barrel",
    "transfer_tube": "transfer tube",
    "interstage": "interstage",
    "forward_dome": "forward dome",
    "thrust_structure": "thrust structure",
}
LOAD_ENTRY = ("stage1.aft_skirt", "stage1.load_ring")
"""The load entry's elements (design 4.2: the skirt and the ring frame)."""


def words(key: str) -> str:
    """'stage-1 aft skirt' from 'stage1.aft_skirt'."""
    stage, element = key.split(".")
    return f"{stage.replace('stage', 'stage-')} {ELEMENT_WORDS.get(element, element)}"


def figure_elements(a: Mapping[str, Any], tables: Mapping[str, Any]) -> Path:
    """The central case's dm by element at its solved x*, with each element's modes."""
    case = cases_by_name(a)["silo_cold_s1_st"]
    recorded = {k: float(v) for k, v in case["structure_elements"].items()}
    sc = tables["solved_central"]
    if sc["offload_kg"] != case["offload_kg"] or sc["max_abs_diff_kg"] > 1e-6:
        raise SystemExit("the tables' central sizing does not reproduce run A's elements")
    total = float(case["structure_dm_kg"])
    items = sorted(((k, v) for k, v in recorded.items() if v > 0.0), key=lambda kv: kv[1])
    zero = [k for k, v in recorded.items() if v <= 0.0]
    entry = sum(v for k, v in recorded.items() if k in LOAD_ENTRY)
    fig = new_figure(5.2)
    title(
        fig,
        f"Where the modelled {total:,.0f} kg goes: silo_cold_s1_st at its solved x* "
        f"({kg_to_t(float(case['offload_kg'])):.2f} t)",
        f"by element, with the mode that governs the push and the pad envelope at each "
        f"element's governing station; the load entry (skirt and ring) is "
        f"{100.0 * entry / total:.0f}% of dm",
    )
    foot = footer(
        fig,
        [
            "Sources: results/silo_structure_2d/20261016T171513Z/metrics.json, case "
            "silo_cold_s1_st (structure_elements, structure_dm_kg, offload_kg; the push at "
            f"n_q {case['structure_n_q_g']:.3f} g0, DLF {case['structure_dlf']:.4f}, n_peak "
            f"{case['structure_n_peak_g']:.3f} g0, F_peak "
            f"{case['structure_F_peak_N'] / 1e6:.2f} MN); the modes from "
            "docs/findings/RQ1-structural-2d-tables.json (sp7_structure_tables.py's sizing "
            "at the same offload, equal to the recorded element masses to "
            f"{sc['max_abs_diff_kg']:.1e} kg). Zero here: "
            f"{', '.join(words(k) for k in zero)}. The load ring is new hardware sized in "
            "closed form with no envelope credit; every other element is the positive part "
            "of the push's requirement over the pad envelope's, station by station, times "
            "its non-optimum factor. Modes (the record's names): stiffened buckling = the "
            "Gerard ring + common Z row (ring_common_z), monocoque buckling = SP-8007 with the "
            "pressure increment (monocoque), combined stress (combined), membrane, hoop, "
            "minimum gauge (min_gauge), ring bending (ring_bending, the ring's closed form).",
            GATE_CAVEAT,
            STRUCTURE_CAVEAT,
        ],
    )
    ax = fig.add_axes((0.20, foot + 0.09, 0.78, 0.85 - foot - 0.09))
    style_axes(ax)
    ys = list(range(len(items)))
    for y, (k, v) in zip(ys, items, strict=True):
        color = BLUE if k in LOAD_ENTRY else ORANGE
        ax.barh(y, v, height=0.42, color=color, edgecolor=SURFACE, linewidth=0, zorder=3)
        el = sc["elements"][k]
        push = MODE_WORDS.get(str(el["push_mode"]), str(el["push_mode"]))
        env = el["envelope_mode"]
        env_t = "none (new hardware)" if env is None else MODE_WORDS.get(str(env), str(env))
        ax.text(
            v + 25.0,
            y,
            f"{v:,.1f} kg ({100.0 * v / total:.1f}%): push {push}, envelope {env_t}",
            va="center",
            fontsize=FONT_SMALL,
            color=INK,
            zorder=6,
        )
    ax.set_yticks(ys)
    ax.set_yticklabels([words(k) for k, _ in items], fontsize=FONT_SMALL)
    ax.tick_params(axis="y", length=0)
    ax.grid(False, axis="y")
    ax.set_xlim(0, 5200)
    ax.set_xlabel("dm by element at x* [kg]", fontsize=FONT, color=INK)
    handles = [
        Patch(facecolor=BLUE, label="load entry (aft skirt, load ring)"),
        Patch(facecolor=ORANGE, label="tank barrels, domes and the transfer tube"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=FONT_SMALL, frameon=False)
    return save(fig, "derived_elements.png")


# ------------------------------------------------------------------ 5. dm vs felt load

GROUPS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("load entry (aft skirt, load ring)", ("stage1.aft_skirt", "stage1.load_ring"), BLUE),
    (
        "domes and transfer tube (stage 1)",
        ("stage1.rp1_aft_dome", "stage1.common_dome", "stage1.transfer_tube"),
        ORANGE,
    ),
    ("RP-1 barrel (stage 1)", ("stage1.rp1_barrel",), AQUA),
    ("LOX barrel (stage 1)", ("stage1.lox_barrel",), YELLOW),
    (
        "upper stack (interstage and stage 2)",
        (
            "stage1.interstage",
            "stage2.rp1_aft_dome",
            "stage2.rp1_barrel",
            "stage2.common_dome",
            "stage2.lox_barrel",
        ),
        MAGENTA,
    ),
)
"""The stacked groups, bottom up, in the palette's fixed slot order."""


def figure_felt(tables: Mapping[str, Any]) -> Path:
    """Sizing only: dm by element group against the felt load at the fixed exit speed."""
    felt = tables["felt"]
    head = felt["offloads"]["headline"]
    full = felt["offloads"]["full_load"]
    ns = [r["n_g"] for r in head["rows"]]
    covered = {k for _, keys, _ in GROUPS for k in keys}
    stray = [
        k
        for r in head["rows"] + full["rows"]
        for k, el in r["elements"].items()
        if el["kg"] > 0.0 and k not in covered
    ]
    if stray:
        raise SystemExit(f"elements outside the figure's groups: {sorted(set(stray))}")
    fig = new_figure(5.8)
    title(
        fig,
        "Sizing only: the central structure's dm against the push's felt load",
        "constant_accel to the fixed exit speed 76.71 m/s (stroke L = v^2 / 2a), at SP1's "
        "headline offload 41.26 t (stacked) and at x = 0 (line); no trajectory flown",
    )
    be = head["break_even"]
    foot = footer(
        fig,
        [
            "Source: docs/findings/RQ1-structural-2d-tables.json (sp7_structure_tables.py: "
            "the central case's transform on file A's pad flown afresh, re-pushed at each "
            "felt load n = (a + g_eff)/g0 from 1.2 to 7.0 g0; tables in "
            "RQ1-structural-2d-tables.md). Break-even felt load at 41.26 t (the smallest n "
            f"with a positive increment): RP-1 barrel {be['stage1.rp1_barrel']['n_be_g']:.3f}, "
            f"LOX barrel {be['stage1.lox_barrel']['n_be_g']:.3f}, the upper stack "
            f"{be['stage2_sized']['n_be_g']:.3f} g0; the load ring is charged at every push. "
            "At 41.26 t the stack is lighter than at any structural x*, so dm is understated "
            "there (for the assist); x = 0 is the adverse bound. A first-order station "
            "sizing (D-SP7-01), not a measurement.",
            GATE_CAVEAT,
        ],
    )
    ax = fig.add_axes((0.085, foot + 0.09, 0.60, 0.85 - foot - 0.09))
    style_axes(ax)
    base = [0.0] * len(ns)
    for label, keys, color in GROUPS:
        layer = [sum(r["elements"][k]["kg"] for k in keys) for r in head["rows"]]
        top = [b + v for b, v in zip(base, layer, strict=True)]
        ax.fill_between(
            ns,
            [kg_to_t(b) for b in base],
            [kg_to_t(t) for t in top],
            color=color,
            alpha=0.85,
            lw=0,
            zorder=3,
            label=label,
        )
        ax.plot(ns, [kg_to_t(t) for t in top], color=SURFACE, lw=1.2, zorder=4)
        base = top
    ax.plot(
        ns,
        [kg_to_t(r["dm_kg"]) for r in full["rows"]],
        color=INK,
        lw=1.6,
        ls=(0, (4, 2)),
        zorder=5,
        label="total at x = 0 (the full-load stack)",
    )
    for s in tables["sweep2_strokes"]:
        ax.axvline(s["n_g"], color=INK2, lw=0.8, alpha=0.8, zorder=4.5)
        right = s["n_g"] > 6.5
        ax.text(
            s["n_g"],
            0.995,
            f"{s['stroke_m']:g} m " if right else f" {s['stroke_m']:g} m",
            transform=ax.get_xaxis_transform(),
            ha="right" if right else "left",
            va="top",
            fontsize=FONT_SMALL,
            color=INK2,
        )
    ax.set_xlim(1.2, 7.0)
    ax.set_ylim(0, 17.5)
    ax.set_xlabel(
        "felt load of the push n [g0] (sweep 2's strokes marked)", fontsize=FONT, color=INK
    )
    ax.set_ylabel("modelled dm [t]", fontsize=FONT, color=INK)
    handles, labels = ax.get_legend_handles_labels()
    order = [*range(len(GROUPS) - 1, -1, -1), len(GROUPS)]
    ax.legend(
        [handles[i] for i in order],
        [labels[i] for i in order],
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        fontsize=FONT_SMALL,
        frameon=True,
        facecolor=SURFACE,
        edgecolor=GRID,
    )
    return save(fig, "derived_dm_vs_felt_load.png")


# ----------------------------------------------------------------------------- copies


def sha256(path: Path) -> str:
    """The sha256 hex of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_figures() -> list[Path]:
    """Copy COPIES into docs/findings/ byte for byte (checked by sha256)."""
    out = []
    for src, name in COPIES:
        dst = OUT_DIR / f"{PREFIX}{name}"
        shutil.copyfile(src, dst)
        if sha256(src) != sha256(dst):
            raise SystemExit(f"the copy of {src} differs from its source")
        out.append(dst)
    return out


def main() -> int:
    """Draw every derived figure, copy the run's own figures, list what was written."""
    a = read_json(RUN_A / "metrics.json")
    c = read_json(RUN_C / "metrics.json")
    tables = read_json(TABLES_JSON)
    written = [
        figure_headline(a, c),
        figure_sweep1(),
        figure_sweep2(),
        figure_elements(a, tables),
        figure_felt(tables),
        *copy_figures(),
    ]
    for path in written:
        print(path.relative_to(REPO).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
