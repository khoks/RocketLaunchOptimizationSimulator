"""SP7 step S7b: the derived drive figures of docs/findings/RQ1-structural-2d.md.

Draws, from run B (results/silo_drive_2d/20261103T231946Z, file B of the pre-registration's
part 2; read-only: never writes under results/), these PNGs in docs/findings/:

- RQ1-structural-2d-derived_drive_cases.png: x* of silo_cold and the nine linear-motor
  variants, each uncharged (hollow) and with the central structure (filled), against
  silo_cold_s1_st's x*, 50% of SP1's 41,262.9 kg and SP1's 41,262.9 kg; each row's numbers
  in a text column (the share of 41,262.9 kg, the difference from silo_cold_s1_st, the
  variant's uncharged x*, the structure's offload cost U - X and dm1 + dm2 at x*).
- RQ1-structural-2d-derived_drive_force_power.png: the drive force and the drive power
  against the speed along the track for the ten flown pushes of the central structural
  cases at their x* (each carrying its dm): the acceleration law with silo_cold's
  constant_accel on the left, the force law on the right.
- RQ1-structural-2d-derived_drive_exit_speed.png: each central structural x* against the
  speed at release of the same recorded run at x*, with silo_cold_s1_st's point as the
  origin of the four quadrants that part 2, section 8's "what would undercut" and "what
  would favour" readings name (faster or slower, more or less offload) at the same 100 m
  stroke.

Every plotted number comes from run B's metrics.json (offload.cases: offload_kg, status,
structure_dm_kg, structure_dm_stage2_kg; offload.runs: speed_at_release_mps,
release_position_m, release_trigger, peak_q_alpha, and the drawn caps push_force_max_N and
push_power_max_W) or from the recorded runs' timeseries.csv and events.csv (the ASSIST
rows: speed_rel_mps, which equals the speed along the track on the vertical track,
drive_force_N, drive_power_W and s_m; the power_limit and release events).

These footer facts are read from metrics.json and resolved_config.yaml and checked before
anything is drawn (``read_facts``): the pad's P* against P_ref, every case ok and verified
within 1e-4 P_ref, the release flag on each structural case, every central run peaking in
q-alpha at its kick, one sampling interval, one drive efficiency, no exhaust impingement,
the carriage masses against the records, the sealed bore, silo_cold's 3 g0 and the 100 m
stroke, each variant's drive law against its record, silo_cold_s1_st's charged rise time
(structure_t_r_s) and each linear-motor case's against its flown rise, and each force-law
variant's power ratio r = P_max / (F_max v_e) against its label. The exit-speed figure also
checks, before its words are written, that lm_cmd lies within R of silo_cold_s1_st, that
lm_cmd_taper releases at silo_cold's speed and keeps less beyond R, that each faster exit
keeps less and that sweep 1's longer strokes exit faster and keep more. The exit-speed
figure measures a dot on its drawn axes and refuses to save when that measure names other
near-line points than its footer does. The force and power figure measures which force-law
release dots lie beside lm_fixed_target's, and that each ringed release dot (RINGED) lies
within a quarter of a dot's width of the dot drawn over it on both of its panels; it
refuses to save when either differs from its footer. A figure is refused, not drawn, when
one of these does not hold. The footers also print, read and not
re-checked: the caps (push_force_max_N, push_power_max_W, and the acceleration law's), the
corner speed (push_corner_speed_mps), the sealed column's peak force (piston_force_peak_N),
the power-cap spans, the peak q-alpha (offload.runs and runs.pad peak_q_alpha) and sweep 1's
200 and 300 m points (file A's sweep re-run, sp7_structure_figures.SWEEP_A: its
sweep_1/sweep_index.csv and baseline/metrics.json). Words that describe the model rather
than the run (a uniform adiabat, the kind of cap) are written, not read.

The script prints, each with its source key, every plotted point of the x* figures, each
flown push's row count, drive-force and drive-power maxima and release row (not its every
sample), the power-cap spans and every footer cap.
``--check`` exits 1 when one of these plotted values does not match its record re-read
independently (``check_values``): X and U against quoted_offload_kg; dm1 + dm2 against the
decomposition's xv_dry_mass_delta_kg and dm2 against the sum of the stage-2 elements
(structure_elements); the speed at release against the decomposition's
xv_speed_at_release_mps, the run's exit_speed_mps and the last ASSIST row's speed_rel_mps;
the release position (the stroke when the record has none) against the last ASSIST row's
s_m; the time series' drive-force and drive-power maxima against drive_force_peak_N and
peak_drive_power_W.

The look and the drawing helpers are sp7_structure_figures.py's, and the registered values
(the reading rules' 41,262.9 kg, R, the verification rule, run B's directory) are
sp7_s7b_checks.py's, both imported from this folder unchanged (S7a's script and its outputs
are not touched). Run from the repository root: ``uv run python
docs/findings/scripts/sp7_drive_figures.py [--check]``. Its numbers are figures of recorded
results, never new findings; the note quotes the records.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sp7_s7b_checks as checks
import sp7_structure_figures as s7a
import yaml
from matplotlib.lines import Line2D
from matplotlib.transforms import blended_transform_factory
from sp7_structure_figures import (
    AQUA,
    BASELINE,
    BLUE,
    FONT,
    FONT_ROW,
    FONT_SMALL,
    GREY,
    GRID,
    INK,
    INK2,
    MAGENTA,
    MUTED,
    ORANGE,
    REPO,
    SURFACE,
    YELLOW,
    dot,
    footer,
    new_figure,
    read_json,
    save,
    style_axes,
    title,
    wrap_glued,
)

from launchsim.units import kg_to_t, n_to_mn, t_to_kg, to_percent, w_to_mw

RUN_B: Path = checks.RUN_B
"""Run B's directory (sp7_s7b_checks.RUN_B: file B's registered run; read only)."""
RUN_B_REL = RUN_B.relative_to(REPO).as_posix()
"""RUN_B relative to the repository root, as the footers name it."""
SHARE_BASE_KG = checks.SP1_UNCHARGED_KG
"""SP1's uncharged 41,262.9 kg as part 2, section 8 writes it: the base of every '%' and of
the cases figure's 50% and SP1 lines (sp7_s7b_checks.SP1_UNCHARGED_KG)."""
R_X_KG = checks.R_X_KG
"""Part 2, section 3's resolution of two structural x* [kg] (sp7_s7b_checks.R_X_KG)."""
SPEED_TIE_MPS = checks.SPEED_TIE_MPS
"""Two release speeds within this [m/s] read as equal (sp7_s7b_checks.SPEED_TIE_MPS)."""
NEAR_LINE_KG = 800.0
"""A difference from silo_cold_s1_st's x* beyond R but below this [kg] lies within about a
dot's width (s7a.MARKER plus its edge) of silo_cold's line on the exit-speed figure (21 t of
axis), so its side is read from its label, not its position: the footer names such a point.
``figure_exit_speed`` measures the dot's width in kg on the drawn axes and refuses to save
when that width would name a different set of points."""
GLUE = "\ue000"
"""A private-use character (U+E000, written as an escape) that holds a label to its number
through ``wrap_glued`` ('U' and '41.26 t'); replaced by a space after wrapping (str.split
splits on U+00A0, so a no-break space would not hold)."""
COLD_ACCEL_G = 3.0
"""silo_cold's net acceleration [g0] as VARIANTS' label and part 2, section 4 write it (file
A's constant_accel push)."""
RING_SIZE = 2.0 * s7a.MARKER
"""The marker size of the ring drawn around a dot that another dot hides."""
DM2_KG_IN_TONNES_MIN = 5.0
"""A stage-2 share of dm [kg] at or above which ``dm_words`` prints it in tonnes to two
decimals; below it (it would print 0.00 t) it is printed in kilograms."""
CARRIAGE_ABS_TOL_KG = 1e-9
"""The carriage mass of resolved_config.yaml (t, converted) against the record's [kg]."""
EVENT_T_ABS_TOL_S = 1e-9
"""An events.csv time against the ASSIST row written at that event [s]."""
SPEED_ABS_TOL_MPS = 1e-6
"""The drawn last ASSIST row's speed against the record's speed at release, and the
power_limit event's speed against the corner speed [m/s]."""
CHECK_REL_TOL = 1e-9
"""``check_values``' relative tolerance for a plotted value against its record."""
CHECK_ABS_TOL = 1e-6
"""``check_values``' absolute tolerance (in the value's own SI unit)."""
POWER_RATIO_REL_TOL = 1e-9
"""A force-law variant's r = P_max / (F_max v_e) against its label (VARIANTS)."""
POWER_RATIO_LABELLED = {"lm_fixed_r07": checks.PL_R}
"""The force-law variants whose label names a power ratio r other than 1 (VARIANTS'
'r = 0.7'; sp7_s7b_checks.PL_R); every other force-law variant has r = 1."""
COLD_STRUCTURE_DYNAMIC = "rise_time"
"""silo_cold_s1_st's structure_dynamic: its constant_accel row is charged a rise formula at
an assumed t_r (structure_t_r_s), not the step its trajectory flies."""
SWEEP_1 = 1
"""File A's sweep over the stroke at 3 g0 (sp7_structure_figures.SWEEP_A's sweep_1), whose
200 and 300 m points the exit-speed footer quotes."""
SWEEP_COLD_ST = "silo_cold_s1_st"
"""The structural case of each sweep-1 point (sweep_index.csv '<case>.offload_kg')."""


@dataclass(frozen=True)
class Variant:
    """One of file B's ten variants: its name, its drive law ('constant_accel' for
    silo_cold, else the linear motor's 'acceleration' or 'force', checked against each
    record's push_control_law) and a short form of what it isolates (part 2, section 4)."""

    name: str
    law: str
    isolates: str


VARIANTS: tuple[Variant, ...] = (
    Variant("silo_cold", "constant_accel", "constant_accel 3 g0, 100 m: the basis"),
    Variant("lm_cmd", "acceleration", "acceleration law, ramp flown"),
    Variant("lm_cmd_taper", "acceleration", "+ stop taper (a gentle stop)"),
    Variant("lm_cmd_hot", "acceleration", "+ hot start, ramp ends at release"),
    Variant("lm_fixed", "force", "force law, F_max for the full load"),
    Variant("lm_fixed_target", "force", "+ released at v_e (below the mouth)"),
    Variant("lm_fixed_r07", "force", "power-limited, r = 0.7"),
    Variant("lm_fixed_hot", "force", "+ lit at push start"),
    Variant("lm_fixed_sled22", "force", "+ a 22 t carriage"),
    Variant("lm_fixed_sealed", "force", "+ the sealed shaft (5.24 m bore)"),
)
"""File B's ten variants in the order of part 2, section 4 (silo_cold first: the basis).
The numbers in ``isolates`` (3 g0, 100 m, r = 0.7, 22 t, 5.24 m) are checked by
``read_facts``."""
LEFT_LAWS = ("constant_accel", "acceleration")
"""The drive laws drawn in the force and power figure's left panels (the rest: right)."""
LINE_STYLE: dict[str, tuple[str, Any, float]] = {
    "silo_cold": (INK, (0, (2, 2)), 4.0),
    "lm_cmd": (BLUE, "-", 3.0),
    "lm_cmd_taper": (ORANGE, "-", 3.0),
    "lm_cmd_hot": (AQUA, "-", 3.0),
    "lm_fixed": (BLUE, "-", 3.5),
    "lm_fixed_target": (INK, (0, (2, 2)), 4.0),
    "lm_fixed_r07": (ORANGE, "-", 3.0),
    "lm_fixed_hot": (AQUA, "-", 3.0),
    "lm_fixed_sled22": (YELLOW, "-", 3.0),
    "lm_fixed_sealed": (MAGENTA, "-", 3.0),
}
"""Each flown push's colour, line style and zorder in the force and power figure (two panels
per law, so a colour repeats only across panels). lm_fixed is drawn above the other solid
force-law lines that share its plateau, lm_fixed_target dashed over it (it repeats
lm_fixed's push until its release); silo_cold is dashed over lm_cmd, whose force it nearly
repeats after the rise."""
RINGED = {"silo_cold": "lm_cmd", "lm_fixed": "lm_fixed_target"}
"""The pushes whose release dot another dot hides, each with the push whose dot is drawn
over it (silo_cold's under lm_cmd's, lm_fixed's under lm_fixed_target's): a ring is drawn
around each, and the footer says so. ``figure_force_power`` measures each pair on its drawn
axes (RING_HIDDEN_WITHIN) and refuses to save when one does not hold."""
RING_HIDDEN_WITHIN = 0.25
"""A ringed release dot's centre lies within this fraction of a dot's drawn width (in
both of its panels' axes, ``dot_width_data``) of the centre of the dot drawn over it, so
that dot covers about two thirds or more of it (two equal discs a quarter of a diameter
apart overlap by about 68%)."""
DOT_Z = 5.0
"""A dot's zorder (sp7_structure_figures.dot's)."""
RING_Z = 6.0
"""A ring's zorder: above every dot (DOT_Z and the 5.5 of FORCE_POWER_DOT_ZORDER and
EXIT_SPEED_DOT_ZORDER; ``main`` refuses to draw otherwise)."""
LABEL_Z = 6.0
"""The zorder of the exit-speed figure's labels and their leaders: above every dot."""
POINTS_PER_INCH = 72.0
"""Typographic points per inch (matplotlib's marker sizes are in points)."""
DOT_NEAR_MPS = 2.5
"""Two release dots in the force and power figure's force panel closer than this in speed
[m/s] and than DOT_NEAR_MN in force overlap (a dot is about 3 m/s wide at its scale)."""
DOT_NEAR_MN = 1.5
"""Two release dots in the force and power figure's force panel closer than this in force
[MN] and than DOT_NEAR_MPS in speed overlap (a dot is about 2 MN tall at its scale);
``figure_force_power`` measures the dot on the drawn axes and refuses to save when the
measure names other dots."""
FORCE_POWER_DOT_ZORDER = {"lm_fixed_target": 5.5}
"""Release dots drawn above the others in the force and power figure: lm_fixed_target's
(over lm_fixed_sled22's, which shows as a crescent beside it, and over lm_fixed's)."""
EXIT_SPEED_DOT_ZORDER = {"silo_cold": 5.5}
"""Points drawn above the others in the exit-speed figure: silo_cold_s1_st's, the
quadrants' origin (over lm_fixed_target's, which shows below it, partly under it)."""
EXIT_SPEED_RING = INK
"""The colour of the ring around silo_cold_s1_st's point in the exit-speed figure: ink,
not the points' blue, so that lm_fixed_target's blue point below it stays visible as a
sliver inside the ring rather than reading as the ring's own edge."""


def dot_width_data(fig: Any, ax: Any) -> tuple[float, float]:
    """A dot's drawn width (s7a.MARKER plus its edge, in points) in ``ax``'s x and y data
    units, from the axes' size [in] and limits (set before the call)."""
    pos = ax.get_position()
    width_in = pos.width * fig.get_figwidth()
    height_in = pos.height * fig.get_figheight()
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    dot_in = (s7a.MARKER + s7a.RING) / POINTS_PER_INCH
    return dot_in * (x1 - x0) / width_in, dot_in * (y1 - y0) / height_in


def release_dot(ax: Any, x: float, y: float, color: str, zorder: float) -> None:
    """A filled dot as sp7_structure_figures.dot draws it, at its own zorder."""
    ax.plot(
        [x],
        [y],
        marker="o",
        markersize=s7a.MARKER,
        markerfacecolor=color,
        markeredgecolor=SURFACE,
        markeredgewidth=s7a.RING,
        linestyle="none",
        zorder=zorder,
    )


def ring(ax: Any, x: float, y: float, color: str) -> None:
    """A hollow ring (RING_SIZE, s7a.RING wide) around a dot, above every dot (RING_Z)."""
    ax.plot(
        [x],
        [y],
        marker="o",
        markersize=RING_SIZE,
        markerfacecolor="none",
        markeredgecolor=color,
        markeredgewidth=s7a.RING,
        linestyle="none",
        zorder=RING_Z,
    )


# ----------------------------------------------------------------------------- reading


def cases_by_name(metrics: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Run B's offload case records by name."""
    return {c["name"]: c for c in metrics["offload"]["cases"]}


def read_rows(run: str, name: str) -> list[dict[str, str]]:
    """A recorded run's CSV file (timeseries.csv or events.csv) as rows (read-only)."""
    with (RUN_B / run / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def assist_rows(run: str) -> list[dict[str, float]]:
    """The ASSIST rows of a recorded run's timeseries.csv (samples and event rows, in file
    order): t_s [s], speed_rel_mps [m/s], drive_force_N [N], drive_power_W [W], s_m [m]."""
    keys = ("t_s", "speed_rel_mps", "drive_force_N", "drive_power_W", "s_m")
    return [
        {k: float(row[k]) for k in keys}
        for row in read_rows(run, "timeseries.csv")
        if row["phase"] == "ASSIST"
    ]


def run_config(cfg: Mapping[str, Any], run: str) -> dict[str, Any]:
    """A recorded offload run's resolved run block (resolved_config.yaml offload_runs)."""
    return cfg["offload_runs"][run]["run"]


def recorded_law(run: Mapping[str, Any]) -> str:
    """The drive law a run record names: push_control_law, or the assist model
    ('constant_accel') where the record has none."""
    return run.get("push_control_law") or run["assist_model"]


@dataclass(frozen=True)
class CasePoint:
    """One variant's plotted numbers: U and X [kg] (the uncharged and central x*), dm1 +
    dm2 and dm2 at x* [kg], the speed at release [m/s], the release position [m] (None: the
    record has none, a constant_accel push released at the stroke's end) and trigger, and
    the peak q-alpha [Pa rad] of the central case's recorded run at x*."""

    name: str
    u_kg: float
    x_kg: float
    dm_kg: float
    dm2_kg: float
    v_rel_mps: float
    release_position_m: float | None
    trigger: str | None
    q_alpha_pa_rad: float


def case_points(b: Mapping[str, Any]) -> list[CasePoint]:
    """The ten variants' points from run B's records (refuses a case that is not ok: none
    is; a no_offload case would need its shortfall drawn, which this figure does not do)."""
    cases, runs = cases_by_name(b), b["offload"]["runs"]
    out = []
    for v in VARIANTS:
        un, st = cases[f"{v.name}_s1"], cases[f"{v.name}_s1_st"]
        for c in (un, st):
            if c["status"] != "ok":
                raise SystemExit(f"{c['name']} is {c['status']}: draw its shortfall first")
        r = runs[f"{v.name}_s1_st"]
        position_m = r.get("release_position_m")
        out.append(
            CasePoint(
                v.name,
                float(un["offload_kg"]),
                float(st["offload_kg"]),
                float(st["structure_dm_kg"]),
                float(st.get("structure_dm_stage2_kg") or 0.0),
                float(r["speed_at_release_mps"]),
                None if position_m is None else float(position_m),
                r.get("release_trigger"),
                float(r["peak_q_alpha"]),
            )
        )
    return out


def single(values: Sequence[Any], what: str) -> Any:
    """The one value a sequence holds (refuses two different ones)."""
    if len(set(values)) != 1:
        raise SystemExit(f"{what} differs between the cases: {sorted(set(values))}")
    return values[0]


@dataclass(frozen=True)
class Facts:
    """The footers' facts, each read from run B's records and checked by ``read_facts``:
    the pad's P* [kg] (P_ref, its own); the lowest and highest verification P* - P_ref of
    the twenty cases [kg] and the tolerance 1e-4 P_ref [kg]; the sampling interval [s]; the
    drive efficiency; the linear motor's flown rise time [s]; silo_cold_s1_st's charged
    (assumed) rise time [s]; silo_cold's net acceleration [g0]; the stroke [m]; the
    carriages (variant, mass [kg]) and sealed shafts (variant, bore [m]) where set; the hot
    starts (propellant burned on the track at x*) and those of them under the force law;
    each force-law variant's power ratio r; the structural cases whose release flag
    fired."""

    pad_payload_kg: float
    verify_lo_kg: float
    verify_hi_kg: float
    verify_tol_kg: float
    sample_dt_s: float
    efficiency: float
    rise_time_s: float
    cold_rise_time_s: float
    cold_accel_g: float
    stroke_m: float
    carriages: tuple[tuple[str, float], ...]
    sealed: tuple[tuple[str, float], ...]
    hot: tuple[str, ...]
    hot_force: tuple[str, ...]
    power_ratio: tuple[tuple[str, float], ...]
    release_flag: tuple[str, ...]


def power_ratio(run: Mapping[str, Any], v_e_mps: float) -> float:
    """A force-law push's power ratio r = P_max / (F_max v_e): its corner speed over v_e,
    silo_cold's exit speed (push_power_max_W, push_force_max_N; dimensionless)."""
    return float(run["push_power_max_W"]) / (float(run["push_force_max_N"]) * v_e_mps)


def read_facts(b: Mapping[str, Any], cfg: Mapping[str, Any]) -> Facts:
    """The footers' facts from metrics.json (b) and resolved_config.yaml (cfg); refuses
    (SystemExit) when one of the facts listed in the module docstring does not hold on the
    records it reads (RUN_B is fixed: another directory needs an edit of RUN_B)."""
    cases, runs = cases_by_name(b), b["offload"]["runs"]
    pad_payload_kg = float(b["runs"]["pad"]["payload_kg"])
    p_ref_kg = float(b["offload"]["reference_payload_kg"])
    if abs(pad_payload_kg - p_ref_kg) > checks.PAD_TOL_KG:
        raise SystemExit(f"the pad's P* {pad_payload_kg} is not P_ref {p_ref_kg}")
    tol_kg = checks.VERIFY_REL * p_ref_kg
    deltas_kg = []
    for v in VARIANTS:
        for name in (f"{v.name}_s1", f"{v.name}_s1_st"):
            ver = cases[name]["verification"]
            if not ver.get("passed") or abs(float(ver["delta_kg"])) > tol_kg:
                raise SystemExit(f"{name}: not verified within 1e-4 P_ref ({ver})")
            deltas_kg.append(float(ver["delta_kg"]))
    blocks = {v.name: run_config(cfg, f"{v.name}_s1_st") for v in VARIANTS}
    assists = {n: blk["assist"] for n, blk in blocks.items()}
    dt_s = single([float(blk["integrator"]["sample_dt_s"]) for blk in blocks.values()], "dt")
    eff = single([float(a["drive_efficiency"]) for a in assists.values()], "efficiency")
    imp = single([float(a["exhaust_impingement_fraction"]) for a in assists.values()], "imp")
    stroke_m = single([float(a["stroke_m"]) for a in assists.values()], "stroke")
    if imp != 0.0:
        raise SystemExit(f"exhaust impingement {imp}: the footers say none is modelled")
    v_e_mps = float(runs["silo_cold_s1_st"]["speed_at_release_mps"])
    carriages, sealed, hot, hot_force, ratios, fired = [], [], [], [], [], []
    for v in VARIANTS:
        run, a = runs[f"{v.name}_s1_st"], assists[v.name]
        if recorded_law(run) != v.law:
            raise SystemExit(f"{v.name}: law {recorded_law(run)} against {v.law}")
        if run["peak_q_alpha_phase"] != "KICK":
            raise SystemExit(f"{v.name}_s1_st no longer peaks in q-alpha at its kick")
        mass_kg = t_to_kg(float(a["carriage_mass_t"]))
        if not math.isclose(mass_kg, float(run["carriage_mass_kg"]), abs_tol=CARRIAGE_ABS_TOL_KG):
            raise SystemExit(f"{v.name}: carriage {mass_kg} against {run['carriage_mass_kg']}")
        if mass_kg > 0.0:
            carriages.append((v.name, mass_kg))
        if a.get("shaft") == "sealed":
            sealed.append((v.name, float(a["shaft_bore_m"])))
        if float(run.get("propellant_burned_on_track_kg") or 0.0) > 0.0:
            hot.append(v.name)
            if v.law == "force":
                hot_force.append(v.name)
        if v.law == "force":
            r = power_ratio(run, v_e_mps)
            want = POWER_RATIO_LABELLED.get(v.name, 1.0)
            if not math.isclose(r, want, rel_tol=POWER_RATIO_REL_TOL):
                raise SystemExit(f"{v.name}: r = {r} against its label's {want}")
            ratios.append((v.name, r))
        flags = {f["name"]: f for f in cases[f"{v.name}_s1_st"]["structure_flags"]}
        if flags["structure_release_unload"]["fired"]:
            fired.append(v.name)
    cold = assists["silo_cold"]
    rise_s = single(
        [float(runs[f"{v.name}_s1_st"]["push_rise_time_s"]) for v in VARIANTS[1:]], "rise"
    )
    for v in VARIANTS[1:]:
        if float(cases[f"{v.name}_s1_st"]["structure_t_r_s"]) != rise_s:
            raise SystemExit(f"{v.name}_s1_st is not charged its flown {rise_s} s rise")
    cold_case = cases["silo_cold_s1_st"]
    if cold_case["structure_dynamic"] != COLD_STRUCTURE_DYNAMIC:
        raise SystemExit(f"silo_cold_s1_st is charged {cold_case['structure_dynamic']}")
    bore_m = checks.SEALED_SHAFT["shaft_bore_m"]
    expected = {
        "silo_cold's 3 g0": float(cold["net_accel_g"]) == COLD_ACCEL_G,
        "the 100 m stroke": stroke_m == checks.STROKE_M,
        "lm_fixed_r07's r = 0.7": (POWER_RATIO_LABELLED.keys() <= {n for n, _ in ratios}),
        "lm_fixed_sled22's 22 t": carriages == [("lm_fixed_sled22", checks.CARRIAGE_22T_KG)],
        "lm_fixed_sealed's 5.24 m bore": sealed == [("lm_fixed_sealed", bore_m)],
    }
    for what, ok in expected.items():
        if not ok:
            raise SystemExit(f"{what} (VARIANTS' labels) does not hold on this run")
    return Facts(
        pad_payload_kg,
        min(deltas_kg),
        max(deltas_kg),
        tol_kg,
        dt_s,
        eff,
        rise_s,
        float(cold_case["structure_t_r_s"]),
        float(cold["net_accel_g"]),
        stroke_m,
        tuple(carriages),
        tuple(sealed),
        tuple(hot),
        tuple(hot_force),
        tuple(ratios),
        tuple(fired),
    )


NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
"""A count up to ten in words, as the footers print it."""


def count_words(n: int) -> str:
    """``n`` in words up to ten, else in digits."""
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


def and_join(words: Sequence[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def share(x_kg: float) -> float:
    """x as a percentage of SP1's uncharged 41,262.9 kg (SHARE_BASE_KG) [%]."""
    return float(to_percent(x_kg / SHARE_BASE_KG))


def glue(text: str) -> str:
    """``text`` with its spaces replaced by GLUE, so ``wrap_glued`` keeps it on one line."""
    return text.replace(" ", GLUE)


def dm_words(p: CasePoint) -> str:
    """'dm 6.31 t' or, with stage 2 sized, 'dm 8.87 + 0.13 t' (dm1 + dm2 at x*); a stage-2
    share below DM2_KG_IN_TONNES_MIN (it would print 0.00 t) in kilograms: 'dm 8.00 t +
    0.9 kg'."""
    if p.dm2_kg >= DM2_KG_IN_TONNES_MIN:
        return f"dm {kg_to_t(p.dm_kg - p.dm2_kg):.2f} + {kg_to_t(p.dm2_kg):.2f} t"
    if p.dm2_kg > 0.0:
        return f"dm {kg_to_t(p.dm_kg - p.dm2_kg):.2f} t + {p.dm2_kg:.1f} kg"
    return f"dm {kg_to_t(p.dm_kg):.2f} t"


def against_cold(p: CasePoint, cold: CasePoint) -> str:
    """The difference from silo_cold_s1_st: in tonnes, or within R (part 2, section 3) in
    kilograms with the words 'within R'."""
    d_kg = p.x_kg - cold.x_kg
    if abs(d_kg) <= R_X_KG:
        return f"{d_kg:+.4f} kg against silo_cold_s1_st, within R"
    return f"{kg_to_t(d_kg):+.2f} t against silo_cold_s1_st"


def kick_clause(b: Mapping[str, Any], pts: Sequence[CasePoint]) -> str:
    """The free kick: the central cases' peak q-alpha against the pad's (unconstrained);
    read_facts has checked that every one peaks at its kick."""
    pad_q_alpha_pa_rad = float(b["runs"]["pad"]["peak_q_alpha"])
    lo = min(pts, key=lambda p: p.q_alpha_pa_rad)
    hi = max(pts, key=lambda p: p.q_alpha_pa_rad)
    return (
        "Free kick: every central case's recorded run peaks in q-alpha at its kick, "
        f"{lo.q_alpha_pa_rad:.1f} ({lo.name}) to {hi.q_alpha_pa_rad:.1f} Pa rad ({hi.name}), "
        f"{lo.q_alpha_pa_rad / pad_q_alpha_pa_rad:.2f} to "
        f"{hi.q_alpha_pa_rad / pad_q_alpha_pa_rad:.2f} times the pad's "
        f"{pad_q_alpha_pa_rad:.1f} (offload.runs and runs.pad peak_q_alpha, "
        "peak_q_alpha_phase; derived ratios), with no angle-of-attack aerodynamics, no limit "
        "and no structure charged "
        "for it."
    )


def gate_line(f: Facts) -> str:
    """The gate vehicle's caveats, with the pad's P* (P_ref) from the records."""
    return (
        "Gate vehicle (generic_f9_class_2d, calibrates +14.3% high on payload, "
        "docs/findings/CAL-f9-leo-2d); sweep-optimized guidance, unthrottled, planar; x* = "
        f"the solved stage-1 propellant offload at P_ref ({f.pad_payload_kg:,.1f} kg, the "
        "pad's own P*), tanks partly filled; central structure only (no physics band, no "
        "+/-10% sensitivity arm on file B)."
    )


def drive_line(f: Facts) -> str:
    """The drives' caveats, with the efficiency, the carriage, the shaft and the hot starts
    read from the records."""
    sled, sled_kg = f.carriages[0]
    sealed, bore_m = f.sealed[0]
    hot = and_join(list(f.hot))
    force_hot = (
        f"; on {and_join(list(f.hot_force))} (the force law) impingement 0 also adds the "
        "whole thrust to F_max, which raises the felt load and dm (against the assist), so "
        "the omission's net direction there is not known"
        if f.hot_force
        else ""
    )
    return (
        "Drives: silo_cold a prescribed constant acceleration with no force or power limit; "
        "the linear motor capped by F_max and P_max only (a mechanical power cap at the "
        "carriage; no thermal, current or voltage limit), drive efficiency "
        f"{f.efficiency:g} assumed (it moves only the electricity); a massless carriage "
        f"except {sled}'s {kg_to_t(sled_kg):g} t lumped mass; a vented shaft except "
        f"{sealed}'s sealed column ({bore_m:g} m bore; a uniform adiabat); no exhaust in the "
        f"shaft modelled (impingement 0), which favours the hot starts ({hot}) on "
        f"back-pressure and heating{force_hot}."
    )


def structure_line(f: Facts) -> str:
    """The modelled rows' caveats, with the release flag's count from the records."""
    n = len(f.release_flag)
    total = count_words(len(VARIANTS))
    fired = f"all {total}" if n == len(VARIANTS) else f"{count_words(n)} of the {total}"
    return (
        "Modelled rows: a first-order station sizing of the push load for the offloaded "
        "stack (D-SP7-01), not a detailed structural design: central coefficients; a "
        f"linear-motor push flies its drive's own {f.rise_time_s:g} s rise and is charged "
        "the larger of the rise formula and the flown history's single-mode bound "
        "(D-SP7-52), while silo_cold's constant_accel row charges an assumed "
        f"{f.cold_rise_time_s:g} s real-drive rise its trajectory does not fly (it flies a "
        "step); the pad's own "
        "unthrottled flight as the envelope; zero existing margin (adverse for the assist); "
        "the instant release flagged, not sized (the release flag fires on "
        f"{fired} structural cases)."
    )


# ------------------------------------------------------------------- 1. the drive cases


def figure_cases(b: Mapping[str, Any], f: Facts, pts: Sequence[CasePoint]) -> Path:
    """x* of the ten variants, uncharged (hollow, grey) and central (filled), joined by the
    structure's offload cost, against silo_cold_s1_st's x*, 50% and 41,262.9 kg."""
    fig = new_figure(8.6)
    title(
        fig,
        "File B's drive cases: stage-1 offload uncharged and with the central structure",
        "x* at P_ref of silo_cold and the nine linear-motor variants (run B); filled: the "
        "central structural case, hollow: the same variant uncharged",
    )
    cold = pts[0]
    foot = footer(
        fig,
        [
            f"Source: {RUN_B_REL}/metrics.json (offload.cases: offload_kg, status, "
            "structure_dm_kg, structure_dm_stage2_kg, verification). %: of SP1's uncharged "
            f"{SHARE_BASE_KG:,.1f} kg (the reading rules' base, part 2 of the "
            "pre-registration, section 8); a difference from silo_cold_s1_st within part 2's "
            f"resolution R (about {R_X_KG:g} kg for x*, section 3) reads 'within R'. U - X: "
            "the structure's offload cost (the variant's uncharged x* less its structural "
            "x*; the uncharged push is not the same flight: under the force law its lighter "
            "stack exits faster). dm: dm1 + dm2 at x* (the stage-1 elements with the "
            "interstage, + stage 2 where the push sized it). Every case ok and verified: "
            f"P* - P_ref {f.verify_lo_kg:+.4f} to {f.verify_hi_kg:+.4f} kg against "
            f"{f.verify_tol_kg:.3f} kg (1e-4 P_ref; verification.delta_kg); no case ended "
            "no_offload. " + kick_clause(b, pts),
            gate_line(f),
            drive_line(f),
            structure_line(f),
        ],
    )
    top, bottom = 0.86, foot + 0.05
    left, width = 0.27, 0.36
    ax = fig.add_axes((left, bottom, width, top - bottom))
    style_axes(ax)
    n = len(pts)
    ys = list(range(n, 0, -1))
    ax.set_ylim(0.4, n + 0.6)
    ax.set_xlim(-1.0, 56.0)
    half_t = kg_to_t(0.5 * SHARE_BASE_KG)
    full_t = kg_to_t(SHARE_BASE_KG)
    cold_t = kg_to_t(cold.x_kg)
    ax.axvline(cold_t, color=ORANGE, linewidth=1.0, linestyle=(0, (4, 3)), zorder=2)
    ax.axvline(half_t, color=INK2, linewidth=1.0, linestyle=(0, (4, 3)), zorder=2)
    ax.axvline(full_t, color=MUTED, linewidth=1.0, linestyle=(0, (1, 2)), zorder=2)
    ax.axvline(0.0, color=BASELINE, linewidth=1.2, zorder=2)
    for x_t, text, ha in (
        (cold_t, f"silo_cold_s1_st\n{cold_t:.2f} t", "right"),
        (half_t, f"50%:\n{half_t:.2f} t", "left"),
        (full_t, f"SP1\n{full_t:.2f} t", "center"),
    ):
        ax.text(
            x_t,
            1.005,
            text,
            transform=ax.get_xaxis_transform(),
            ha=ha,
            va="bottom",
            fontsize=FONT_SMALL,
            color=INK2,
            linespacing=1.1,
        )
    for y_sep in (n - 0.5, n - 3.5):
        ax.axhline(y_sep, color=GRID, linewidth=1.0, zorder=1)
    row_text = blended_transform_factory(fig.transFigure, ax.transData)
    for y, v, p in zip(ys, VARIANTS, pts, strict=True):
        x_t, u_t = kg_to_t(p.x_kg), kg_to_t(p.u_kg)
        ax.plot([x_t, u_t], [y, y], color=MUTED, lw=1.0, zorder=3)
        dot(ax, u_t, y, GREY, hollow=True)
        dot(ax, x_t, y, BLUE)
        fig.text(
            0.012,
            y,
            f"{v.name}\n{v.isolates}",
            transform=row_text,
            fontsize=FONT_ROW,
            color=INK,
            va="center",
            linespacing=1.15,
        )
        cost_t = kg_to_t(p.u_kg - p.x_kg)
        text = (
            f"{x_t:.2f} t ({share(p.x_kg):.1f}%); "
            + ("the basis" if v.name == "silo_cold" else against_cold(p, cold))
            + f"; {glue(f'U {u_t:.2f} t,')} {glue(f'U - X {cost_t:.2f} t;')} {dm_words(p)}"
        )
        fig.text(
            left + width + 0.012,
            y,
            "\n".join(wrap_glued(text, 52)).replace(GLUE, " "),
            transform=row_text,
            fontsize=FONT_ROW,
            color=INK,
            va="center",
            linespacing=1.15,
        )
    ax.set_yticks(ys)
    ax.set_yticklabels([""] * n)
    ax.tick_params(axis="y", length=0)
    ax.grid(False, axis="y")
    ax.set_xlabel("stage-1 propellant offload x* at P_ref [t]", fontsize=FONT, color=INK)
    handles = [
        Line2D(
            [],
            [],
            marker="o",
            color=BLUE,
            markerfacecolor=BLUE,
            markeredgecolor=SURFACE,
            markeredgewidth=s7a.RING,
            markersize=s7a.MARKER,
            ls="none",
        ),
        Line2D(
            [],
            [],
            marker="o",
            color=GREY,
            markerfacecolor=SURFACE,
            markeredgecolor=GREY,
            markeredgewidth=1.6,
            markersize=s7a.MARKER,
            ls="none",
        ),
        Line2D([], [], color=MUTED, lw=1.0),
    ]
    fig.legend(
        handles=handles,
        labels=[
            "central structural x* (filled)",
            "the same variant uncharged (hollow)",
            "the structure's offload cost U - X",
        ],
        loc="upper left",
        bbox_to_anchor=(0.012, 0.935),
        ncols=3,
        fontsize=FONT_SMALL,
        frameon=False,
        columnspacing=1.6,
        handletextpad=0.5,
    )
    return save(fig, "derived_drive_cases.png")


# ------------------------------------------------------------ 2. force and power by speed


@dataclass(frozen=True)
class PowerCap:
    """Where a flown push meets its power cap before its release (the recorded power_limit
    event): the speed there [m/s], and the distance [m] and time [s] it then flies to its
    release at P_max (the force falling as P_max / sdot)."""

    name: str
    speed_mps: float
    distance_m: float
    duration_s: float


def power_cap(name: str) -> PowerCap | None:
    """The power_limit event of ``name``'s recorded run at x*, before its release (None when
    the push logs none), with its position read from the ASSIST row at the event's time."""
    run = f"{name}_s1_st"
    events = {
        r["event"]: float(r["t_s"]) for r in read_rows(run, "events.csv") if r["phase"] == "ASSIST"
    }
    if "power_limit" not in events:
        return None
    rows = assist_rows(run)
    at = next(
        r for r in rows if math.isclose(r["t_s"], events["power_limit"], abs_tol=EVENT_T_ABS_TOL_S)
    )
    last = rows[-1]
    if not math.isclose(last["t_s"], events["release"], abs_tol=EVENT_T_ABS_TOL_S):
        raise SystemExit(f"{name}: the last ASSIST row is not the release event")
    return PowerCap(name, at["speed_rel_mps"], last["s_m"] - at["s_m"], last["t_s"] - at["t_s"])


def release_list(pts: Sequence[CasePoint], names: Sequence[str]) -> str:
    """'72.22 (lm_fixed_sealed), 75.27 (lm_fixed_sled22), ... m/s', from the records."""
    by_name = {p.name: p for p in pts}
    return ", ".join(f"{by_name[n].v_rel_mps:.2f} ({n})" for n in names) + " m/s"


def shared_plateau(b: Mapping[str, Any], pts: Sequence[CasePoint]) -> list[str]:
    """The force-law pushes that fly lm_fixed's F_max and P_max, in order of release speed
    (read from the records' push_force_max_N and push_power_max_W)."""
    runs = b["offload"]["runs"]
    ref = runs["lm_fixed_s1_st"]
    names = [
        v.name
        for v in VARIANTS
        if v.law == "force"
        and runs[f"{v.name}_s1_st"]["push_force_max_N"] == ref["push_force_max_N"]
        and runs[f"{v.name}_s1_st"]["push_power_max_W"] == ref["push_power_max_W"]
    ]
    speed_mps = {p.name: p.v_rel_mps for p in pts}
    return sorted(names, key=lambda n: speed_mps[n])


def acceleration_caps(b: Mapping[str, Any]) -> str:
    """The acceleration law's caps, which file B registered and which never bind (E2): each
    distinct pair with its variants; refuses a drive_cap event or a cap bound."""
    runs = b["offload"]["runs"]
    pairs: dict[tuple[float, float], list[str]] = {}
    for v in VARIANTS:
        if v.law != "acceleration":
            continue
        run = runs[f"{v.name}_s1_st"]
        events = {r["event"] for r in read_rows(f"{v.name}_s1_st", "events.csv")}
        if run.get("push_cap_bound") is not False or events & {"drive_cap", "drive_cap_end"}:
            raise SystemExit(f"{v.name}: a cap binds; the footer says none does")
        key = (float(run["push_force_max_N"]), float(run["push_power_max_W"]))
        pairs.setdefault(key, []).append(v.name)
    return "; ".join(
        f"{' and '.join(names)} {n_to_mn(f_n):.2f} MN and {w_to_mw(p_w):,.0f} MW"
        for (f_n, p_w), names in pairs.items()
    )


def figure_force_power(b: Mapping[str, Any], f: Facts, pts: Sequence[CasePoint]) -> Path:
    """Drive force and drive power against the speed along the track, the flown pushes of
    the ten central structural cases at their x*: acceleration law (with silo_cold) left,
    force law right."""
    runs = b["offload"]["runs"]
    lm_fixed = runs["lm_fixed_s1_st"]
    r07 = runs["lm_fixed_r07_s1_st"]
    by_name = {p.name: p for p in pts}
    sled, sled_kg = f.carriages[0]
    sealed = f.sealed[0][0]
    caps = [c for c in (power_cap(v.name) for v in VARIANTS if v.law == "force") if c]
    shared = shared_plateau(b, pts)
    corner_mps = float(lm_fixed["push_corner_speed_mps"])
    ratio = dict(f.power_ratio)
    cap_words = and_join(
        [
            f"{c.name} over its last {c.distance_m:.2f} m ({c.duration_s:.3f} s) from "
            + (
                f"{c.speed_mps:.2f} m/s"
                if math.isclose(c.speed_mps, corner_mps, abs_tol=SPEED_ABS_TOL_MPS)
                else f"its own corner at {c.speed_mps:.2f} m/s"
            )
            for c in caps
        ]
    )
    target = by_name["lm_fixed_target"]
    lm_f = by_name["lm_fixed"]
    cold, cmd = assist_rows("silo_cold_s1_st")[-1], assist_rows("lm_cmd_s1_st")[-1]
    lm_last = assist_rows("lm_fixed_s1_st")[-1]
    force_law = [v.name for v in VARIANTS if v.law == "force"]
    release_mps_mn = {
        n: (r[-1]["speed_rel_mps"], n_to_mn(r[-1]["drive_force_N"]))
        for n, r in ((n, assist_rows(f"{n}_s1_st")) for n in force_law)
    }
    v_t_mps, f_t_mn = release_mps_mn["lm_fixed_target"]
    beside = [
        n
        for n in force_law
        if n not in ("lm_fixed", "lm_fixed_target")
        and abs(release_mps_mn[n][0] - v_t_mps) < DOT_NEAR_MPS
        and abs(release_mps_mn[n][1] - f_t_mn) < DOT_NEAR_MN
    ]
    if not beside:
        raise SystemExit("no force-law release dot lies beside lm_fixed_target's: reword")
    fig = new_figure(8.4)
    title(
        fig,
        "Drive force and power against speed: the flown pushes of the central structural cases",
        "each case's recorded run at its x*, carrying its dm (run B); a dot marks the release; "
        "a ring marks a release that another dot hides",
    )
    foot = footer(
        fig,
        [
            f"Source: {RUN_B_REL}/<case>/timeseries.csv, the ASSIST rows (sampled every "
            f"{f.sample_dt_s:g} s plus the event rows), and events.csv (power_limit, "
            "release) of the ten <variant>_s1_st recorded runs: speed_rel_mps (the speed "
            "along the vertical track), drive_force_N and drive_power_W; the release dot is "
            "the last ASSIST row, at the recorded speed_at_release_mps; and metrics.json "
            "offload.runs (push_force_max_N, push_power_max_W, push_corner_speed_mps, "
            "push_cap_bound, piston_force_peak_N) for the caps, the corner and the column "
            "force. The drive force is "
            "the motor's (or silo_cold's prescribed force) and the power the mechanical "
            "power at the carriage, F sdot; the electricity and the electrical peak are "
            f"these over the assumed efficiency {f.efficiency:g}. Between samples the drawn "
            "lines are straight, so a sampled peak can read low (KI-074; the felt-g and "
            "interface-force maxima the sizing reads are exact). The force on the vehicle "
            f"is not the drive force on {sealed} (less the column force, "
            f"{n_to_mn(float(runs[f'{sealed}_s1_st']['piston_force_peak_N'])):.2f} MN at its "
            f"peak) and on {sled} (the vehicle's share of it with the "
            f"{kg_to_t(sled_kg):g} t carriage); on the hot starts the thrust adds to it. Caps "
            f"drawn: lm_fixed's F_max {n_to_mn(float(lm_fixed['push_force_max_N'])):.2f} MN "
            f"and P_max {w_to_mw(float(lm_fixed['push_power_max_W'])):,.0f} MW (r = "
            f"{ratio['lm_fixed']:.3g}: corner speed {corner_mps:.2f} m/s, r = P_max / (F_max "
            "v_e), derived); lm_fixed_r07's F_max "
            f"{n_to_mn(float(r07['push_force_max_N'])):.2f} MN and P_max "
            f"{w_to_mw(float(r07['push_power_max_W'])):,.0f} MW (r = "
            f"{ratio['lm_fixed_r07']:.3g}) are its own line's plateaus. "
            "The acceleration law's caps (" + acceleration_caps(b) + ") never bind (no "
            f"drive_cap event; E2) and are not drawn. After the {f.rise_time_s:g} s rise "
            f"{count_words(len(shared))} force-law pushes fly lm_fixed's F_max plateau, and "
            "so the same power line F_max sdot below the corner, where their lines coincide "
            "(lm_fixed's drawn above the other solid lines, lm_fixed_target's dashed over "
            "it); they release at "
            + release_list(pts, shared)
            + ". The power cap then binds, the force falling as P_max / sdot (the "
            f"power_limit events): {cap_words}. Rings: lm_fixed's release "
            f"({lm_f.v_rel_mps:.2f} m/s, {n_to_mn(lm_last['drive_force_N']):.2f} MN) lies "
            f"{lm_f.v_rel_mps - target.v_rel_mps:.2f} m/s past lm_fixed_target's "
            f"({target.v_rel_mps:.2f} m/s), so its power-capped end is too short to see at "
            f"this scale; silo_cold's ({n_to_mn(cold['drive_force_N']):.2f} MN) lies under "
            f"lm_cmd's ({n_to_mn(cmd['drive_force_N']):.2f} MN). lm_fixed_target's release "
            "dot is drawn above the other force-law dots, so "
            f"{and_join(beside)}'s ("
            + ", ".join(f"{by_name[n].v_rel_mps:.2f}" for n in beside)
            + " m/s) shows as a crescent beside it.",
            gate_line(f),
            drive_line(f),
        ],
    )
    top, bottom = 0.86, foot + 0.07
    gap_x, gap_y = 0.08, 0.07
    left, right = 0.08, 0.98
    w = (right - left - gap_x) / 2.0
    h = (top - bottom - gap_y) / 2.0
    groups = (
        (
            "acceleration law (and silo_cold's constant_accel)",
            [v.name for v in VARIANTS if v.law in LEFT_LAWS],
        ),
        ("force law", [v.name for v in VARIANTS if v.law not in LEFT_LAWS]),
    )
    f_max_mn = n_to_mn(float(lm_fixed["push_force_max_N"]))
    p_max_mw = w_to_mw(float(lm_fixed["push_power_max_W"]))
    drawn: dict[str, list[tuple[Any, float, float]]] = {}
    for col, (label, names) in enumerate(groups):
        ax_f = fig.add_axes((left + col * (w + gap_x), bottom + h + gap_y, w, h))
        ax_p = fig.add_axes((left + col * (w + gap_x), bottom, w, h))
        for ax in (ax_f, ax_p):
            style_axes(ax)
            ax.set_xlim(0.0, 95.0)
        ax_f.set_title(label, fontsize=FONT, color=INK, loc="left")
        for name in names:
            rows = assist_rows(f"{name}_s1_st")
            color, ls, z = LINE_STYLE[name]
            speed_mps = [r["speed_rel_mps"] for r in rows]
            force_mn = [n_to_mn(r["drive_force_N"]) for r in rows]
            power_mw = [w_to_mw(r["drive_power_W"]) for r in rows]
            ax_f.plot(speed_mps, force_mn, color=color, lw=1.6, ls=ls, label=name, zorder=z)
            ax_p.plot(speed_mps, power_mw, color=color, lw=1.6, ls=ls, label=name, zorder=z)
            drawn[name] = []
            for ax, y in ((ax_f, force_mn[-1]), (ax_p, power_mw[-1])):
                release_dot(ax, speed_mps[-1], y, color, FORCE_POWER_DOT_ZORDER.get(name, DOT_Z))
                drawn[name].append((ax, speed_mps[-1], y))
                if name in RINGED:
                    ring(ax, speed_mps[-1], y, color)
            if not math.isclose(
                speed_mps[-1], by_name[name].v_rel_mps, rel_tol=0.0, abs_tol=SPEED_ABS_TOL_MPS
            ):
                raise SystemExit(f"{name}: the last ASSIST row is not the release")
        if col == 1:
            ax_f.axhline(f_max_mn, color=INK2, lw=0.9, ls=(0, (4, 3)), zorder=2)
            ax_p.axhline(p_max_mw, color=INK2, lw=0.9, ls=(0, (4, 3)), zorder=2)
            ax_f.text(
                12.0,
                f_max_mn - 0.6,
                "lm_fixed's F_max",
                fontsize=FONT_SMALL,
                color=INK2,
                va="top",
            )
            ax_p.text(2.0, p_max_mw + 50.0, "lm_fixed's P_max", fontsize=FONT_SMALL, color=INK2)
            right_force_axes = ax_f
        ax_f.set_ylim(0.0, 31.0)
        ax_p.set_ylim(0.0, 2000.0)
        ax_f.set_ylabel("drive force [MN]", fontsize=FONT, color=INK)
        ax_p.set_ylabel("drive power, mechanical [MW]", fontsize=FONT, color=INK)
        ax_p.set_xlabel("speed along the track [m/s]", fontsize=FONT, color=INK)
        ax_f.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, 0.02),
            fontsize=FONT_SMALL,
            frameon=False,
            ncols=2,
        )
    wx_mps, wy_mn = dot_width_data(fig, right_force_axes)
    measured = [
        n
        for n in force_law
        if n not in ("lm_fixed", "lm_fixed_target")
        and ((release_mps_mn[n][0] - v_t_mps) / wx_mps) ** 2
        + ((release_mps_mn[n][1] - f_t_mn) / wy_mn) ** 2
        < 1.0
    ]
    if measured != beside:
        raise SystemExit(f"the dots beside lm_fixed_target's are {measured}, not {beside}")
    check_rings(fig, drawn)
    return save(fig, "derived_drive_force_power.png")


def check_rings(fig: Any, drawn: Mapping[str, Sequence[tuple[Any, float, float]]]) -> None:
    """Each ringed release dot (RINGED) against the dot drawn over it, on both of its panels
    (``drawn``: each push's (axes, speed [m/s], force [MN] or power [MW]) per panel, force
    first): both in the same axes, the hider drawn above it (a higher zorder, or the same one
    and drawn later), and its centre within RING_HIDDEN_WITHIN of a dot's drawn width of the
    hider's (``dot_width_data``). Refuses to save when one of these does not hold; prints
    the measured distances."""
    order = [v.name for v in VARIANTS]
    for hidden, hider in RINGED.items():
        z_hidden = FORCE_POWER_DOT_ZORDER.get(hidden, DOT_Z)
        z_hider = FORCE_POWER_DOT_ZORDER.get(hider, DOT_Z)
        if z_hider < z_hidden or (z_hider == z_hidden and order.index(hider) < order.index(hidden)):
            raise SystemExit(f"{hider}'s release dot is not drawn over {hidden}'s")
        for panel, ((ax, x, y), (ax_h, x_h, y_h)) in zip(
            ("force", "power"), zip(drawn[hidden], drawn[hider], strict=True), strict=True
        ):
            if ax is not ax_h:
                raise SystemExit(f"{hidden} and {hider} are drawn in different {panel} panels")
            width_mps, height_y = dot_width_data(fig, ax)  # [m/s], [MN] or [MW]
            within = math.hypot((x - x_h) / width_mps, (y - y_h) / height_y)
            print(
                f"force and power figure: {hidden}'s release dot lies {within:.3f} of a dot's "
                f"width from {hider}'s ({panel} panel; derived)"
            )
            if within >= RING_HIDDEN_WITHIN:
                raise SystemExit(
                    f"{hidden}'s {panel} release dot is {within:.2f} dot widths from "
                    f"{hider}'s: it is not hidden, so drop its ring and reword the footer"
                )


# --------------------------------------------------------- 3. x* against the exit speed


LABEL_AT: dict[str, tuple[float, float, str] | None] = {
    "silo_cold": (70.4, 16.2, "left"),
    "lm_cmd": None,
    "lm_cmd_taper": (78.3, 2.5, "left"),
    "lm_cmd_hot": (78.3, 18.3, "left"),
    "lm_fixed": (79.0, 12.4, "left"),
    "lm_fixed_target": (79.0, 10.3, "left"),
    "lm_fixed_r07": (78.3, 5.7, "left"),
    "lm_fixed_hot": (88.8, 8.6, "center"),
    "lm_fixed_sled22": (70.4, 12.5, "left"),
    "lm_fixed_sealed": (70.6, 8.0, "left"),
}
"""Where each point's label sits [m/s, t] and its alignment, with a leader to the point
(chosen by hand so that no two labels meet and silo_cold's two-line label ends left of the
vertical boundary); None: no label of its own (lm_cmd shares silo_cold's point and its
label, which ``figure_exit_speed`` checks)."""
LABEL_RELPOS = {"silo_cold": (1.0, 0.0)}
"""Where a leader leaves its label (a fraction of the label's box; the centre otherwise):
silo_cold's from its lower right corner, so that it passes right of lm_fixed_sled22's
label."""


def dot_width_kg(fig: Any, ax: Any) -> float:
    """A dot's drawn width in the exit-speed axes' y units [kg] (its y axis in t)."""
    return float(t_to_kg(dot_width_data(fig, ax)[1]))


def sweep1_clause(cold: CasePoint, stroke_m: float) -> str:
    """File A's sweep 1 (silo_cold at 3 g0 over the stroke): its longer points
    (s7a.SWEEP1_KICK_STROKES) exit faster than ``cold`` and keep more beyond R, which it
    checks, with the 300 m value's upper-bound tag (unconstrained_kick) and their full-load
    runs' free-kick q-alpha against the sweep's pad (derived ratios)."""
    index = s7a.SWEEP_A / f"sweep_{SWEEP_1}" / "sweep_index.csv"
    rows = [
        r for r in s7a.read_index(index) if float(r["assist.stroke_m"]) in s7a.SWEEP1_KICK_STROKES
    ]
    if len(rows) != len(s7a.SWEEP1_KICK_STROKES):
        raise SystemExit(f"sweep 1 lacks a point at one of {s7a.SWEEP1_KICK_STROKES}")
    pad_q_alpha_pa_rad = float(s7a.read_json(s7a.SWEEP_BASELINE)["metrics"]["peak_q_alpha"])
    points = []
    for r in rows:
        point_stroke_m = float(r["assist.stroke_m"])
        exit_mps = float(r["exit_speed_mps"])
        x_kg = float(r[f"{SWEEP_COLD_ST}.offload_kg"])
        ok = r[f"{SWEEP_COLD_ST}.status"] == "ok"
        if (
            not ok
            or point_stroke_m <= stroke_m
            or exit_mps <= cold.v_rel_mps
            or x_kg <= cold.x_kg + R_X_KG
        ):
            raise SystemExit(
                f"sweep 1's {point_stroke_m:g} m point does not exit faster and keep more"
            )
        bound = ", an upper bound" if r["unconstrained_kick"] == "True" else ""
        points.append(
            f"{kg_to_t(x_kg):.2f} t at {exit_mps:.1f} m/s over {point_stroke_m:g} m{bound}"
        )
    ratios = and_join([f"{float(r['peak_q_alpha']) / pad_q_alpha_pa_rad:.1f}" for r in rows])
    return (
        "On file A's sweep 1 (silo_cold over the stroke) longer strokes exit faster and keep more: "
        f"{and_join(points)}; their full-load runs kick at {ratios} times the pad's q-alpha "
        f"({pad_q_alpha_pa_rad:.1f} Pa rad), unconstrained, and the structural runs' own "
        f"q-alpha is not written ({s7a.SWEEP_A.relative_to(REPO).as_posix()}: "
        f"{index.relative_to(s7a.SWEEP_A).as_posix()} exit_speed_mps, "
        f"{SWEEP_COLD_ST}.offload_kg, unconstrained_kick, peak_q_alpha; "
        f"{s7a.SWEEP_BASELINE.relative_to(s7a.SWEEP_A).as_posix()} peak_q_alpha; derived "
        "ratios; the note's 'The exit-speed axis')."
    )


def figure_exit_speed(b: Mapping[str, Any], f: Facts, pts: Sequence[CasePoint]) -> Path:
    """Each central structural x* against the speed at release of its recorded run at x*,
    silo_cold_s1_st's point as the origin of the four quadrants (drawn above the others and
    ringed). Refuses to draw when a sentence it writes does not hold: a faster exit keeping
    as much or more, lm_cmd not within R of silo_cold_s1_st (they share one point and one
    label), lm_cmd_taper not at silo_cold's speed or not keeping less beyond R, or the dot's
    measured width naming other points near silo_cold's line than NEAR_LINE_KG does."""
    cold, by_name = pts[0], {p.name: p for p in pts}
    faster = [p for p in pts if p.v_rel_mps > cold.v_rel_mps + SPEED_TIE_MPS]
    if not faster or any(p.x_kg >= cold.x_kg - R_X_KG for p in faster):
        raise SystemExit("a faster exit keeps as much or more: rewrite the subtitle")
    tied = [
        p.name
        for p in pts[1:]
        if math.isclose(p.v_rel_mps, cold.v_rel_mps, rel_tol=0.0, abs_tol=SPEED_TIE_MPS)
    ]
    cmd, taper = by_name["lm_cmd"], by_name["lm_cmd_taper"]
    if abs(cmd.x_kg - cold.x_kg) > R_X_KG or "lm_cmd" not in tied:
        raise SystemExit("lm_cmd no longer shares silo_cold_s1_st's point: give it a label")
    if "lm_cmd_taper" not in tied or taper.x_kg >= cold.x_kg - R_X_KG:
        raise SystemExit("lm_cmd_taper is not tied and below silo_cold: reword its clause")
    near = [p for p in pts[1:] if R_X_KG < abs(p.x_kg - cold.x_kg) < NEAR_LINE_KG]
    away = [
        p for p in pts if p.release_position_m is not None and p.release_position_m != f.stroke_m
    ]
    which = {1: "the one faster exit keeps", 2: "both faster exits keep"}.get(
        len(faster), f"all {count_words(len(faster))} faster exits keep"
    )
    fig = new_figure(9.4)
    title(
        fig,
        "Structural offload against the speed at release (central cases, at x*)",
        f"at the same {f.stroke_m:g} m stroke {which} less "
        f"({and_join([p.name for p in faster])});\neach case's x* against the speed its own "
        "push reached at x*, carrying its dm (run B)",
    )
    tie = f"{SPEED_TIE_MPS:.0e}".replace("e-0", "e-")
    near_words = (
        " "
        + and_join(
            [
                f"{p.name} ({abs(p.x_kg - cold.x_kg):.1f} kg, about "
                f"{abs(p.x_kg - cold.x_kg) / R_X_KG:.0f} R, "
                f"{'below' if p.x_kg < cold.x_kg else 'above'}"
                + ("; partly under silo_cold's ringed point" if p.name in tied else "")
                + ")"
                for p in near
            ]
        )
        + " lie beyond R of silo_cold's line but within about a dot's width of it at this "
        "scale, so their side is read from their labels, not their positions."
        if near
        else ""
    )
    away_words = "; ".join(
        f"{p.name}'s at {p.release_position_m:.2f} m up the {f.stroke_m:g} m stroke "
        f"({p.trigger}), whose speed is its release speed, not a mouth speed"
        for p in away
    )
    foot = footer(
        fig,
        [
            f"Source: {RUN_B_REL}/metrics.json (offload.cases offload_kg; offload.runs "
            "<variant>_s1_st speed_at_release_mps, release_position_m, release_trigger). "
            "The quadrants are part 2 of the pre-registration's section 8 readings: a drive "
            "that gains speed over silo_cold and leaves less once charged, or exits slower "
            "and leaves more, undercuts 'every m/s helps'; faster and more beyond R would "
            f"favour it. {and_join(tied)} release at silo_cold's {cold.v_rel_mps:.2f} m/s "
            f"(within {tie} m/s): they lie on the vertical boundary, in no "
            "quadrant; lm_cmd_taper's undercut reading is its own (a gentler stop that costs "
            f"{kg_to_t(cold.x_kg - taper.x_kg):.2f} t of offload at the same exit, the note's "
            "'The drive cases'). silo_cold_s1_st's point, the quadrants' origin, is drawn "
            "above the others and ringed; lm_cmd_s1_st shares it "
            f"({against_cold(cmd, cold)})." + near_words + " "
            f"Every release is at the mouth ({f.stroke_m:g} m) except " + away_words + ". "
            f"Every case here has the same {f.stroke_m:g} m stroke. "
            + sweep1_clause(cold, f.stroke_m)
            + " "
            + kick_clause(b, pts),
            gate_line(f),
            drive_line(f),
            structure_line(f),
        ],
    )
    top, bottom = 0.89, foot + 0.06
    ax = fig.add_axes((0.08, bottom, 0.88, top - bottom))
    style_axes(ax)
    ax.set_xlim(70.0, 92.0)
    ax.set_ylim(0.0, 21.0)
    width_kg = dot_width_kg(fig, ax)
    measured = [p.name for p in pts[1:] if R_X_KG < abs(p.x_kg - cold.x_kg) < width_kg]
    if measured != [p.name for p in near]:
        raise SystemExit(
            f"a dot is {width_kg:.0f} kg wide: it names {measured}, NEAR_LINE_KG "
            f"{[p.name for p in near]}"
        )
    xc, yc = cold.v_rel_mps, kg_to_t(cold.x_kg)
    ax.axvline(xc, color=ORANGE, lw=1.0, ls=(0, (4, 3)), zorder=2)
    ax.axhline(yc, color=ORANGE, lw=1.0, ls=(0, (4, 3)), zorder=2)
    for x, y, text, ha in (
        (91.6, 20.3, "faster and more (would favour)", "right"),
        (91.6, 0.6, "faster and less (undercuts)", "right"),
        (70.4, 20.3, "slower and more (undercuts)", "left"),
        (70.4, 0.6, "slower and less", "left"),
    ):
        ax.text(x, y, text, ha=ha, va="center", fontsize=FONT_SMALL, color=INK2)
    for p in pts:
        x, y = p.v_rel_mps, kg_to_t(p.x_kg)
        release_dot(ax, x, y, BLUE, EXIT_SPEED_DOT_ZORDER.get(p.name, DOT_Z))
        if p.name == "silo_cold":
            ring(ax, x, y, EXIT_SPEED_RING)
        at = LABEL_AT[p.name]
        if at is None:
            continue
        lx, ly, ha = at
        if p.name == "silo_cold":
            label = f"silo_cold and lm_cmd (one point):\n{y:.2f} t at {x:.2f} m/s"
        else:
            label = f"{p.name}: {y:.2f} t at {x:.2f} m/s"
        ax.annotate(
            label,
            xy=(x, y),
            xytext=(lx, ly),
            ha=ha,
            va="center",
            fontsize=FONT_SMALL,
            color=INK,
            linespacing=1.1,
            arrowprops={
                "arrowstyle": "-",
                "color": MUTED,
                "lw": 0.8,
                "shrinkA": 2,
                "shrinkB": 4,
                "relpos": LABEL_RELPOS.get(p.name, (0.5, 0.5)),
            },
            zorder=LABEL_Z,
        )
    ax.set_xlabel("speed at release of the recorded run at x* [m/s]", fontsize=FONT, color=INK)
    ax.set_ylabel("central structural x* at P_ref [t]", fontsize=FONT, color=INK)
    print(f"exit-speed figure: a dot is {width_kg:.1f} kg wide on its axes (derived)")
    return save(fig, "derived_drive_exit_speed.png")


# ------------------------------------------------------------------------- the values


def printed_values(b: Mapping[str, Any], f: Facts, pts: Sequence[CasePoint]) -> list[str]:
    """The plotted points of the x* figures, each flown push's row count, maxima and release
    row, the power-cap spans and every footer cap, with their source keys in each header
    ('quantity = source key [unit]'), for the gate's spot check."""
    lines = [
        "variant | U = offload.cases <v>_s1 offload_kg [kg] | X = <v>_s1_st offload_kg [kg] | "
        "% of 41,262.9 kg (derived) | dm1 + dm2 = structure_dm_kg [kg] | dm2 = "
        "structure_dm_stage2_kg [kg] | offload.runs <v>_s1_st speed_at_release_mps [m/s] | "
        "release_position_m [m] | release_trigger | peak_q_alpha [Pa rad]"
    ]
    for p in pts:
        lines.append(
            f"{p.name} | {p.u_kg:.6f} | {p.x_kg:.6f} | {share(p.x_kg):.4f} | {p.dm_kg:.6f} | "
            f"{p.dm2_kg:.6f} | {p.v_rel_mps:.6f} | {p.release_position_m} | {p.trigger} | "
            f"{p.q_alpha_pa_rad:.3f}"
        )
    lines.append(
        "flown pushes (<v>_s1_st/timeseries.csv ASSIST rows): variant | rows | max "
        "drive_force_N [MN] | max drive_power_W [MW] | last row: speed_rel_mps [m/s], "
        "drive_force_N [MN], drive_power_W [MW], s_m [m]"
    )
    for v in VARIANTS:
        rows = assist_rows(f"{v.name}_s1_st")
        last = rows[-1]
        lines.append(
            f"{v.name} | {len(rows)} | {n_to_mn(max(r['drive_force_N'] for r in rows)):.4f} | "
            f"{w_to_mw(max(r['drive_power_W'] for r in rows)):.2f} | "
            f"{last['speed_rel_mps']:.6f}, {n_to_mn(last['drive_force_N']):.4f}, "
            f"{w_to_mw(last['drive_power_W']):.2f}, {last['s_m']:.4f}"
        )
    lines.append(
        "power cap before the release (<v>_s1_st/events.csv power_limit and the ASSIST rows): "
        "variant | speed_rel_mps there [m/s] | distance to the release [m] | time to it [s]"
    )
    for v in VARIANTS:
        cap = power_cap(v.name) if v.law == "force" else None
        if cap:
            lines.append(
                f"{v.name} | {cap.speed_mps:.6f} | {cap.distance_m:.4f} | {cap.duration_s:.4f}"
            )
    runs, ratio = b["offload"]["runs"], dict(f.power_ratio)
    lines.append(
        "caps (offload.runs <v>_s1_st): variant | push_force_max_N [MN] | push_power_max_W "
        "[MW] | push_corner_speed_mps [m/s] | push_cap_bound | r = P_max / (F_max v_e) "
        "(derived; force law) | piston_force_peak_N [MN]"
    )
    for v in VARIANTS[1:]:
        run = runs[f"{v.name}_s1_st"]
        piston = run.get("piston_force_peak_N")
        lines.append(
            f"{v.name} | {n_to_mn(float(run['push_force_max_N'])):.4f} | "
            f"{w_to_mw(float(run['push_power_max_W'])):.2f} | "
            f"{float(run['push_corner_speed_mps']):.6f} | {run.get('push_cap_bound')} | "
            + (f"{ratio[v.name]:.9f}" if v.name in ratio else "n/a")
            + " | "
            + ("n/a" if piston is None else f"{n_to_mn(float(piston)):.4f}")
        )
    return lines


def check_values(b: Mapping[str, Any], f: Facts, pts: Sequence[CasePoint]) -> list[str]:
    """Each plotted value against its record re-read independently (the list in the module
    docstring); returns the mismatches (empty when all agree)."""
    bad = []
    cases, runs = cases_by_name(b), b["offload"]["runs"]
    for p in pts:
        st, un, r = cases[f"{p.name}_s1_st"], cases[f"{p.name}_s1"], runs[f"{p.name}_s1_st"]
        rows = assist_rows(f"{p.name}_s1_st")
        last = rows[-1]
        stage2 = sum(
            float(kg) for el, kg in st["structure_elements"].items() if el.startswith("stage2.")
        )
        position_m = f.stroke_m if p.release_position_m is None else p.release_position_m
        pairs = (
            ("X", p.x_kg, st["quoted_offload_kg"]),
            ("U", p.u_kg, un["quoted_offload_kg"]),
            ("dm", p.dm_kg, st["decomposition"]["xv_dry_mass_delta_kg"]),
            ("dm2", p.dm2_kg, stage2),
            ("speed", p.v_rel_mps, st["decomposition"]["xv_speed_at_release_mps"]),
            ("exit", p.v_rel_mps, r["exit_speed_mps"]),
            ("last row speed", p.v_rel_mps, last["speed_rel_mps"]),
            ("release position", position_m, last["s_m"]),
            ("peak force", max(rr["drive_force_N"] for rr in rows), r["drive_force_peak_N"]),
            ("peak power", max(rr["drive_power_W"] for rr in rows), r["peak_drive_power_W"]),
        )
        for key, got, want in pairs:
            if not math.isclose(
                float(got), float(want), rel_tol=CHECK_REL_TOL, abs_tol=CHECK_ABS_TOL
            ):
                bad.append(f"{p.name} {key}: plotted {got} against {want}")
    return bad


def main(argv: Sequence[str] | None = None) -> int:
    """Draw the three figures, print the values of ``printed_values``; with --check, exit 1 on any
    mismatch between a plotted value and its record."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="check the plotted values")
    args = parser.parse_args(argv)
    dot_zorders = (DOT_Z, *FORCE_POWER_DOT_ZORDER.values(), *EXIT_SPEED_DOT_ZORDER.values())
    if min(RING_Z, LABEL_Z) <= max(dot_zorders):
        raise SystemExit("a ring or a label would be drawn under a dot: raise RING_Z, LABEL_Z")
    b = read_json(RUN_B / "metrics.json")
    cfg = yaml.safe_load((RUN_B / "resolved_config.yaml").read_text(encoding="utf-8"))
    facts = read_facts(b, cfg)
    pts = case_points(b)
    written = [
        figure_cases(b, facts, pts),
        figure_force_power(b, facts, pts),
        figure_exit_speed(b, facts, pts),
    ]
    for path in written:
        print(path.relative_to(REPO).as_posix())
    for line in printed_values(b, facts, pts):
        print(line)
    if args.check:
        bad = check_values(b, facts, pts)
        for line in bad:
            print("MISMATCH", line)
        print("check:", "PASS" if not bad else f"FAIL ({len(bad)})")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
