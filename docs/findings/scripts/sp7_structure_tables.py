"""SP7 step S7a: the sizing-only tables of docs/findings/RQ1-structural-2d.md.

What it computes (the pre-registration, docs/phases/inputs/2026-10-15-SP7-preregistration.md,
section 5, "Beside the sweeps", and section 7's method; D-SP7-31's sizing-only rule): no
offload is solved and no trajectory is flown except file A's pad baseline
(experiments/silo_structure_2d.yaml), whose flight is the structural envelope; its P* is
checked against run A's recorded P_ref. Every dm is a first-order station sizing
(D-SP7-01), never a measurement; every x* this script prints is an estimate (the coupled
placement on SP1's penalty curve), never a solved offload, and is labelled so.

1. The central structure's dm by element against the felt load n = 1.2 to 7.0 g0 in steps
   of 0.1 g0 at the fixed exit speed 76.70717046013364 m/s (a = n g0 - g_eff, stroke
   L = v_e^2 / (2 a); a cold, vertical, massless-carriage constant_accel push, the
   headline's dynamic factor and its ramped plateau charged), at SP1's headline offload
   (x = 41,262.908 kg) and at x = 0 (the full-load stack, the adverse bound).
2. Each element's break-even n (the smallest n with a positive increment, by bisection to
   0.001 g0) and the stroke it implies, at both offloads.
3. The central case's element split and governing modes at run A's solved x* (a sizing at
   that offload, checked against the run's recorded element masses).
4. The physics band's estimated ends at each sweep point (section 7's method: the case's
   own transform, the coupled placement on SP1's curve shifted to the point's uncharged
   x0; "the headline's sets", design 4.2.6), with the central case's estimate beside the
   solved x* of sweep A; the same for file A's other pushes (the hot starts and the 200 m
   silo).

Reads (never writes) run A, sweep A and SP1's sweep index under results/; writes
docs/findings/RQ1-structural-2d-tables.md and its data, docs/findings/
RQ1-structural-2d-tables.json (read by sp7_structure_figures.py). Run from the repository
root: ``uv run python docs/findings/scripts/sp7_structure_tables.py`` (about 1.5 to 3 min:
the pad flight and a few hundred sizings); ``--markdown-only`` re-renders the markdown from
the JSON without flying or sizing anything.
"""

from __future__ import annotations

import csv
import dataclasses
import json
import math
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from launchsim import cli, sim
from launchsim.config import ResolvedExperiment, ResolvedOffloadCase
from launchsim.constants import G0_MPS2
from launchsim.structure import (
    SP1_PENALTY_CURVE,
    STAGE2_DM_WEIGHT,
    PenaltyCurve,
    SizingSummary,
    coupled_placement,
)

REPO = Path(__file__).resolve().parents[3]
SCRIPT = "docs/findings/scripts/sp7_structure_tables.py"
FILE_A = REPO / "experiments" / "silo_structure_2d.yaml"
RUN_A = REPO / "results" / "silo_structure_2d" / "20261016T171513Z"
SWEEP_A = REPO / "results" / "silo_structure_2d" / "20261016T171522Z"
SP1_SWEEPS = REPO / "results" / "silo_offload_2d" / "20261003T112949Z"
OUT_MD = REPO / "docs" / "findings" / "RQ1-structural-2d-tables.md"
OUT_JSON = REPO / "docs" / "findings" / "RQ1-structural-2d-tables.json"
CODE_PATHS = ("src", "configs", "experiments", "pyproject.toml", "uv.lock")
"""The paths whose content must equal the run's commit (pre-registration section 12)."""

X_HEADLINE_KG = 41262.90803733282
"""SP1's uncharged headline x* [kg] (pre-registration section 9; SP1_PENALTY_CURVE's x(0))."""
V_EXIT_MPS = 76.70717046013364
"""The fixed exit speed of sweep 2 and of the felt-load table [m/s] (pre-registration 5)."""
N_GRID_TENTHS = range(12, 71)
"""The felt-load grid in tenths of g0: 1.2 to 7.0 g0 in steps of 0.1 g0."""
BISECT_TOL_G = 0.001
"""Bisection bracket width of a break-even n [g0] (pre-registration section 5)."""
N_FLOOR_ABOVE_REST_G = 0.001
"""The lowest felt load the break-even search tries, above the push's resting load
g_eff/g0 [g0]: a drive that only just lifts the stack (a > 0)."""
PAD_TOL_KG = 0.002
"""The flown pad's P* must equal run A's P_ref within this [kg] (section 9)."""
REPRO_TOL_KG = 0.002
"""A run's uncharged x* reproduces SP1's within this [kg] (section 9)."""
BAND_SET_CASES = {
    "phys_hi": "silo_cold_s1_st_phys_hi",
    "phys_lo": "silo_cold_s1_st_phys_lo",
    "phys_lo_scaled": "silo_cold_s1_st_phys_lo_scaled",
}
"""The headline's physics-band cases whose structure settings are placed at other pushes."""
SWEEP_CASES = {
    1: ("silo_cold_s1", "silo_cold_s1_st"),
    2: ("silo_cold_200m_s1", "silo_cold_200m_s1_st"),
}
"""Each sweep's uncharged and central structural case (sweeps[].offload)."""
OTHER_PUSHES = (
    ("silo_hot_full", "silo_hot_full_s1", "silo_hot_full_s1_st"),
    ("silo_hot_ramp_on_track", "silo_hot_ramp_s1", "silo_hot_ramp_s1_st"),
    ("silo_cold_200m", "silo_cold_200m_s1", "silo_cold_200m_s1_st"),
)
"""File A's pushes other than the headline's: (variant, uncharged case, central case)."""
TABLE_BASE_CASE = "silo_cold_200m_s1_st"
"""The central case whose transform the felt-load table re-pushes (the fixed-exit-speed
variant; the same vehicle, geometry and envelope as the headline's)."""
ELEMENT_WORDS = {
    "aft_skirt": "aft skirt",
    "load_ring": "load ring",
    "thrust_structure": "thrust structure",
    "rp1_aft_dome": "RP-1 aft dome",
    "rp1_barrel": "RP-1 barrel",
    "common_dome": "common dome",
    "lox_barrel": "LOX barrel",
    "forward_dome": "forward dome",
    "transfer_tube": "transfer tube",
    "interstage": "interstage",
}
"""The element names as the findings note writes them."""
ROW_WORDS = {"dm": "any element (dm > 0)", "stage2_sized": "stage 2 sized (upper stack)"}
"""The break-even table's two rows that are not elements."""
STATUS_EVERY_PUSH = "charged at every push tried (down to the floor)"
"""A break-even search's status when the element is charged already at the floor."""


# ----------------------------------------------------------------------------- helpers


def git(*args: str) -> str:
    """The stripped stdout of a git command in the repository (empty on failure)."""
    proc = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=False
    )
    return proc.stdout.strip()


def code_same_as(commit: str) -> bool:
    """Whether the working tree's CODE_PATHS equal ``commit``'s (``git diff --quiet``)."""
    proc = subprocess.run(
        ["git", "diff", "--quiet", commit, "--", *CODE_PATHS], cwd=REPO, check=False
    )
    return proc.returncode == 0


def read_json(path: Path) -> dict[str, Any]:
    """A JSON file as a dict (read-only)."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_index(path: Path) -> list[dict[str, str]]:
    """A sweep_index.csv as rows (read-only)."""
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def element_key(stage: str, element: str) -> str:
    """'stage1.aft_skirt' from a stage role and an element name."""
    return f"{stage}.{element}"


def element_words(key: str) -> str:
    """'stage-1 aft skirt' from 'stage1.aft_skirt'."""
    stage, element = key.split(".")
    return f"{stage.replace('stage', 'stage-')} {ELEMENT_WORDS.get(element, element)}"


def kg(value: float | None, digits: int = 1) -> str:
    """A mass in kg with thousands separators ('n/a' for None)."""
    return "n/a" if value is None else f"{value:,.{digits}f}"


def tonnes(value_kg: float) -> str:
    """A mass in t to two decimals."""
    return f"{value_kg / 1000.0:,.2f}"


# ------------------------------------------------------------------------ the push at n


def felt_accel_mps2(n_g: float, g_eff_mps2: float) -> float:
    """The net drive acceleration a = n g0 - g_eff [m/s^2] of a vertical push felt at n
    [g0] (the push's felt load is (a + g_eff)/g0 on a vertical track)."""
    return n_g * G0_MPS2 - g_eff_mps2


def with_push(tr: sim.StructureTransform, accel_mps2: float) -> sim.StructureTransform:
    """The transform ``tr`` re-pushed at the net acceleration accel_mps2 [m/s^2] to the
    fixed exit speed V_EXIT_MPS: the stroke L = v_e^2 / (2 a), the track's exit altitude
    kept (the start moved down by L sin phi). Pure: the geometry, envelope and vehicle
    stay the transform's."""
    length = V_EXIT_MPS**2 / (2.0 * accel_mps2)
    track = tr.track
    sin_phi = math.sin(track.phi_rad)
    exit_alt = track.start_altitude_m + track.length_m * sin_phi
    new_track = dataclasses.replace(
        track, length_m=length, start_altitude_m=exit_alt - length * sin_phi
    )
    new_assist = dataclasses.replace(
        tr.assist, net_accel_mps2=accel_mps2, exit_speed_input_mps=V_EXIT_MPS
    )
    return dataclasses.replace(tr, assist=new_assist, track=new_track)


def sizing_record(sizing: sim.StructureSizing) -> dict[str, Any]:
    """The numbers this script keeps of one converged sizing: the push (n_q, DLF, n_peak
    [g0], F_peak [N]), dm by stage [kg], whether stage 2 was sized, each element's kg
    (factor applied) with its governing push and envelope modes, station and z [m]."""
    inc = sizing.increment
    req = inc.requirement
    elements = {}
    for e in inc.elements:
        elements[element_key(e.stage, e.element)] = {
            "kg": float(sizing.factor * e.kg),
            "push_mode": e.push_mode,
            "envelope_mode": e.envelope_mode,
            "station_index": None if e.station_index is None else int(e.station_index),
            "z_m": None if e.z_m is None else float(e.z_m),
            "closed_form": e.closed_form,
        }
    return {
        "n_q_g": req.n_quasi_g,
        "dlf": req.dlf,
        "n_peak_g": req.n_peak_g,
        "F_peak_N": req.f_peak_N,
        "ramp_cost_rel": req.ramp_cost_rel,
        "dm_stage1_kg": sizing.dm_stage1_kg,
        "dm_stage2_kg": sizing.dm_stage2_kg,
        "dm_kg": sizing.total_kg,
        "stage2_sized": inc.stage2_sized,
        "iterations": sizing.iterations,
        "capped": sizing.capped,
        "factor": sizing.factor,
        "elements": elements,
    }


class FeltSizer:
    """Converged sizings of the central structure at a felt load n [g0] and offload x
    [kg], memoized (each is a fixed point of 5-6 sizings)."""

    def __init__(self, base: sim.StructureTransform) -> None:
        """base: the central case's transform (its envelope, geometry and vehicle)."""
        self.base = base
        self.g_eff = base.g_eff_mps2
        self.memo: dict[tuple[float, float], dict[str, Any]] = {}

    def at(self, n_g: float, offload_kg: float) -> dict[str, Any]:
        """The sizing_record of the push felt at n_g [g0] at offload offload_kg [kg]."""
        key = (n_g, offload_kg)
        if key not in self.memo:
            accel = felt_accel_mps2(n_g, self.g_eff)
            tr = with_push(self.base, accel)
            rec = sizing_record(tr.sizing_at(offload_kg))
            rec.update(
                n_g=n_g,
                accel_mps2=accel,
                stroke_m=V_EXIT_MPS**2 / (2.0 * accel),
                offload_kg=offload_kg,
            )
            self.memo[key] = rec
        return self.memo[key]


def charged(rec: dict[str, Any], what: str) -> bool:
    """Whether ``what`` is charged in a sizing record: an element key (its kg above 0),
    'dm' (the total above 0) or 'stage2_sized' (the upper stack exceeded)."""
    if what == "dm":
        return rec["dm_kg"] > 0.0
    if what == "stage2_sized":
        return bool(rec["stage2_sized"])
    return rec["elements"][what]["kg"] > 0.0


def break_even(sizer: FeltSizer, grid: Sequence[float], offload_kg: float, what: str) -> dict:
    """The smallest felt load n [g0] at which ``what`` (``charged``) turns on at offload
    offload_kg [kg]: scanned over ``grid``, then bisected to BISECT_TOL_G between the last
    uncharged and the first charged point (below the grid down to the resting load plus
    N_FLOOR_ABOVE_REST_G). Returns the bracket, the break-even n (the bracket's charged
    end), its stroke, the push there and the element's modes there; ``monotone`` False
    when the grid shows the element charged and then uncharged again."""
    states = [charged(sizer.at(n, offload_kg), what) for n in grid]
    out: dict[str, Any] = {"what": what, "offload_kg": offload_kg}
    if not any(states):
        out.update(status="not charged in the range", n_be_g=None, monotone=True)
        return out
    first = states.index(True)
    out["monotone"] = all(states[first:])
    floor = sizer.g_eff / G0_MPS2 + N_FLOOR_ABOVE_REST_G
    if first == 0 and charged(sizer.at(floor, offload_kg), what):
        rec = sizer.at(floor, offload_kg)
        out.update(
            status=STATUS_EVERY_PUSH,
            n_be_g=None,
            n_floor_g=floor,
            stroke_floor_m=rec["stroke_m"],
            kg_at_floor=_amount(rec, what),
        )
    else:
        lo, hi = (floor, grid[0]) if first == 0 else (grid[first - 1], grid[first])
        while hi - lo > BISECT_TOL_G:
            mid = 0.5 * (lo + hi)
            if charged(sizer.at(mid, offload_kg), what):
                hi = mid
            else:
                lo = mid
        rec = sizer.at(hi, offload_kg)
        out.update(
            status="ok",
            n_lo_g=lo,
            n_be_g=hi,
            stroke_m=rec["stroke_m"],
            accel_mps2=rec["accel_mps2"],
            n_q_g=rec["n_q_g"],
            n_peak_g=rec["n_peak_g"],
            F_peak_N=rec["F_peak_N"],
            amount_at_be=_amount(rec, what),
        )
    if what in rec["elements"]:
        el = rec["elements"][what]
        out.update(push_mode=el["push_mode"], envelope_mode=el["envelope_mode"])
    return out


def _amount(rec: dict[str, Any], what: str) -> float | None:
    """The charged amount behind ``charged`` [kg] (None for the stage-2 flag)."""
    if what == "dm":
        return rec["dm_kg"]
    if what == "stage2_sized":
        return rec["dm_stage2_kg"]
    return rec["elements"][what]["kg"]


# ------------------------------------------------------------------------- placements


def shifted_curve(x0_kg: float) -> PenaltyCurve:
    """SP1's penalty curve shifted to the uncharged offload x0 [kg] (section 7's method:
    X_case(dm) = x0 + (X(dm) - 41,262.908 kg), SP1's slope)."""
    d = x0_kg - SP1_PENALTY_CURVE.uncharged_kg
    if d == 0.0:
        return SP1_PENALTY_CURVE
    return PenaltyCurve(
        dm_kg=SP1_PENALTY_CURVE.dm_kg,
        x_kg=tuple(x + d for x in SP1_PENALTY_CURVE.x_kg),
        source=f"SP1's curve shifted by {d:+.6f} kg",
    )


def summary_at(tr: sim.StructureTransform) -> Callable[[float], SizingSummary]:
    """x [kg] -> the SizingSummary of the transform's converged sizing at offload x."""
    memo: dict[float, SizingSummary] = {}

    def f(x: float) -> SizingSummary:
        if x not in memo:
            s = tr.sizing_at(x)
            memo[x] = SizingSummary(s.dm_stage1_kg, s.dm_stage2_kg, s.increment.stage2_sized)
        return memo[x]

    return f


def place(tr: sim.StructureTransform, x0_kg: float) -> dict[str, Any]:
    """Section 7's estimate of a structural case: the coupled placement on SP1's curve
    shifted to x0 [kg] (stage 2 at STAGE2_DM_WEIGHT), the naive placement (dm sized at x0
    read off the curve), dm by stage at the placed x (at x = 0 for no offload) and the
    push there."""
    f = summary_at(tr)
    curve = shifted_curve(x0_kg)
    p = coupled_placement(f, curve, stage2_weight=STAGE2_DM_WEIGHT)
    at = tr.sizing_at(p.x_kg)
    s0 = f(x0_kg)
    naive = max(0.0, curve.x_at(s0.dm_stage1_kg + STAGE2_DM_WEIGHT * s0.dm_stage2_kg))
    zero = tr.sizing_at(0.0)
    req = at.increment.requirement
    return {
        "x0_kg": x0_kg,
        "x_kg": p.x_kg,
        "no_offload": p.no_offload,
        "converged": p.converged,
        "extrapolated": p.extrapolated,
        "dm_stage1_kg": at.dm_stage1_kg,
        "dm_stage2_kg": at.dm_stage2_kg,
        "naive_x_kg": naive,
        "dm_x0_kg": zero.total_kg,
        "dm_eq_x0_kg": zero.dm_stage1_kg + STAGE2_DM_WEIGHT * zero.dm_stage2_kg,
        "zero_crossing_dm_eq_kg": curve.dm_at(0.0),
        "n_q_g": req.n_quasi_g,
        "n_peak_g": req.n_peak_g,
        "F_peak_N": req.f_peak_N,
        "factor": at.factor,
    }


def with_settings(case: ResolvedOffloadCase, settings_of: ResolvedOffloadCase) -> Any:
    """``case`` (a point's or variant's central case) carrying another case's structure
    settings (the headline's physics-band end: "the headline's sets")."""
    return dataclasses.replace(case, structure=settings_of.structure)


# ----------------------------------------------------------------------------- runs


def fly_pad(resolved: ResolvedExperiment, p_ref_kg: float) -> tuple[Any, float, float]:
    """Fly file A's pad baseline (its payload search); refuse a P* off run A's P_ref by
    more than PAD_TOL_KG. Returns (the RunResult, P* [kg], wall time [s])."""
    t0 = time.perf_counter()
    pad = sim.run_resolved(resolved.baseline)
    wall = time.perf_counter() - t0
    p_star = float(pad.result.metrics["payload_kg"])
    if abs(p_star - p_ref_kg) > PAD_TOL_KG:
        raise SystemExit(f"the flown pad's P* {p_star!r} kg is off run A's P_ref {p_ref_kg!r} kg")
    return pad, p_star, wall


def case_named(resolved: ResolvedExperiment, name: str) -> ResolvedOffloadCase:
    """File A's offload case called ``name``."""
    assert resolved.offload is not None
    return next(c for c in resolved.offload.cases if c.name == name)


def grid_row(rec: dict[str, Any]) -> dict[str, Any]:
    """A felt-table row as written: the sizing record with each element reduced to its
    kg (the modes are kept for the break-even values and the solved central case only)."""
    row = {k: v for k, v in rec.items() if k != "elements"}
    row["elements"] = {k: {"kg": el["kg"]} for k, el in rec["elements"].items()}
    return row


def felt_tables(sizer: FeltSizer, grid: Sequence[float]) -> dict[str, Any]:
    """Sections 2 to 4's numbers: the grid at both offloads and every break-even."""
    out: dict[str, Any] = {"grid_g": list(grid), "offloads": {}}
    for label, x in (("headline", X_HEADLINE_KG), ("full_load", 0.0)):
        rows = [grid_row(sizer.at(n, x)) for n in grid]
        keys = list(rows[0]["elements"])
        be = {k: break_even(sizer, grid, x, k) for k in keys}
        be["dm"] = break_even(sizer, grid, x, "dm")
        be["stage2_sized"] = break_even(sizer, grid, x, "stage2_sized")
        out["offloads"][label] = {"offload_kg": x, "rows": rows, "break_even": be}
    return out


def sweep2_strokes(sizer: FeltSizer, resolved: ResolvedExperiment) -> list[dict[str, Any]]:
    """The felt load n [g0] of each of sweep 2's strokes on the table's axis (a = v_e^2 /
    (2 L), n = (a + g_eff)/g0), for the basis line and the figure's marks."""
    rows = []
    for point in resolved.sweeps[1]:
        stroke = float(point.overrides["assist.stroke_m"])
        accel = V_EXIT_MPS**2 / (2.0 * stroke)
        n = (accel + sizer.g_eff) / G0_MPS2
        rows.append({"stroke_m": stroke, "n_g": n})
    return rows


def cross_check(
    sizer: FeltSizer, resolved: ResolvedExperiment, pad: Any, p_ref: float
) -> list[dict[str, Any]]:
    """At sweep 2's four strokes: dm by the table's route (the base transform re-pushed
    at a = v_e^2 / (2 L)) against the sweep point's own transform (its resolved run), at
    both offloads [kg]; they should agree to rounding."""
    out = []
    _, st_name = SWEEP_CASES[2]
    for point in resolved.sweeps[1]:
        stroke = float(point.overrides["assist.stroke_m"])
        accel = V_EXIT_MPS**2 / (2.0 * stroke)
        table_tr = with_push(sizer.base, accel)
        case = next(c for c in point.offload if c.name.endswith(st_name))
        own_tr = sim.offload_structure_transform(case, pad, p_ref)
        for x in (X_HEADLINE_KG, 0.0):
            a, b = table_tr.sizing_at(x).total_kg, own_tr.sizing_at(x).total_kg
            out.append({"stroke_m": stroke, "offload_kg": x, "table_kg": a, "point_kg": b})
    return out


def solved_central(run_a: dict[str, Any], base: sim.StructureTransform) -> dict[str, Any]:
    """The central case at run A's solved x* (a sizing at that offload), with each
    element's recorded mass beside and the largest difference [kg]."""
    rec = next(c for c in run_a["offload"]["cases"] if c["name"] == "silo_cold_s1_st")
    x = float(rec["offload_kg"])
    out = sizing_record(base.sizing_at(x))
    recorded = rec["structure_elements"]
    out["offload_kg"] = x
    out["recorded_elements_kg"] = recorded
    out["recorded_dm_kg"] = rec["structure_dm_kg"]
    out["max_abs_diff_kg"] = max(
        abs(out["elements"][k]["kg"] - float(v)) for k, v in recorded.items()
    )
    out["governing_recorded"] = rec["structure_governing"]
    return out


def sweep_bands(
    resolved: ResolvedExperiment, pad: Any, p_ref: float, sweep_rows: dict[int, list]
) -> list[dict[str, Any]]:
    """Section 7's estimates at every sweep point: the central case and the headline's
    physics-band sets, placed on SP1's curve shifted to SP1's uncharged x0 at that point,
    with sweep A's uncharged and solved central x* and dm beside."""
    sp1 = {k: read_index(SP1_SWEEPS / f"sweep_{k}" / "sweep_index.csv") for k in (1, 2)}
    sets = {tag: case_named(resolved, name) for tag, name in BAND_SET_CASES.items()}
    out = []
    for k, points in enumerate(resolved.sweeps, start=1):
        un, st = SWEEP_CASES[k]
        for point in points:
            stroke = float(point.overrides["assist.stroke_m"])
            sp1_row = next(r for r in sp1[k] if float(r["assist.stroke_m"]) == stroke)
            run_row = next(r for r in sweep_rows[k] if float(r["assist.stroke_m"]) == stroke)
            x0_sp1 = float(sp1_row[f"{un}.offload_kg"])
            case = next(c for c in point.offload if c.name.endswith(st) and c.structure)
            row: dict[str, Any] = {
                "sweep": k,
                "stroke_m": stroke,
                "exit_speed_mps": float(run_row["exit_speed_mps"]),
                "x0_sp1_kg": x0_sp1,
                "x0_run_kg": float(run_row[f"{un}.offload_kg"]),
                "solved_status": run_row[f"{st}.status"],
                "solved_x_kg": float(run_row[f"{st}.offload_kg"]),
                "solved_dm_kg": float(run_row[f"{st}.structure_dm_kg"]),
                "solved_dm_stage2_kg": float(run_row[f"{st}.structure_dm_stage2_kg"]),
                "solved_n_peak_g": float(run_row[f"{st}.structure_n_peak_g"]),
            }
            row["central"] = place(sim.offload_structure_transform(case, pad, p_ref), x0_sp1)
            for tag, set_case in sets.items():
                tr = sim.offload_structure_transform(with_settings(case, set_case), pad, p_ref)
                row[tag] = place(tr, x0_sp1)
            out.append(row)
            print(
                f"  sweep {k} L {stroke:5.0f} m: central est {row['central']['x_kg']:10.1f} "
                f"solved {row['solved_x_kg']:10.1f}; band {row['phys_hi']['x_kg']:.0f} / "
                f"{row['phys_lo']['x_kg']:.0f} / {row['phys_lo_scaled']['x_kg']:.0f} kg"
            )
    return out


def other_bands(
    resolved: ResolvedExperiment, pad: Any, p_ref: float, run_a: dict[str, Any]
) -> list[dict[str, Any]]:
    """The same estimates for file A's other pushes, x0 the run's own uncharged x*."""
    cases = {c["name"]: c for c in run_a["offload"]["cases"]}
    sets = {tag: case_named(resolved, name) for tag, name in BAND_SET_CASES.items()}
    out = []
    for variant, un, st in OTHER_PUSHES:
        x0 = float(cases[un]["offload_kg"])
        case = case_named(resolved, st)
        row: dict[str, Any] = {
            "variant": variant,
            "case": st,
            "x0_run_kg": x0,
            "solved_status": cases[st]["status"],
            "solved_x_kg": float(cases[st]["offload_kg"]),
            "solved_dm_kg": cases[st].get("structure_dm_kg"),
        }
        row["central"] = place(sim.offload_structure_transform(case, pad, p_ref), x0)
        for tag, set_case in sets.items():
            tr = sim.offload_structure_transform(with_settings(case, set_case), pad, p_ref)
            row[tag] = place(tr, x0)
        out.append(row)
    return out


# ---------------------------------------------------------------------------- markdown


def mode(value: str | None) -> str:
    """A mode name as recorded, 'n/a' for none (the ring and the relation rows)."""
    return "n/a" if value is None else str(value)


def x_cell(p: dict[str, Any]) -> str:
    """An estimate's x* cell: 'x kg (y% of 41.26 t; z% of its own x0)' or, for no
    offload, 'no offload (dm_eq(0) d kg > crossing c kg)'."""
    if p["no_offload"]:
        return (
            f"no offload (dm_eq(0) {kg(p['dm_eq_x0_kg'])} > crossing "
            f"{kg(p['zero_crossing_dm_eq_kg'])})"
        )
    own = "" if p["x0_kg"] == X_HEADLINE_KG else f"; {100.0 * p['x_kg'] / p['x0_kg']:.1f}% own"
    return f"{kg(p['x_kg'])} ({100.0 * p['x_kg'] / X_HEADLINE_KG:.1f}%{own})"


def dm_cell(p: dict[str, Any]) -> str:
    """'dm1 + dm2' at the estimate's x (x = 0 for no offload) [kg]."""
    return f"{kg(p['dm_stage1_kg'])} + {kg(p['dm_stage2_kg'])}"


def solved_cell(status: str, x_kg: float) -> str:
    """A solved x* cell from a results file: 'x kg' or 'no offload (no_offload)'."""
    if status == "no_offload":
        return "no offload"
    return kg(x_kg) if status == "ok" else f"{kg(x_kg)} ({status})"


def be_cell(be: dict[str, Any]) -> str:
    """A break-even cell: 'n (L m)' or the status."""
    if be["status"] == "ok":
        return f"{be['n_be_g']:.3f} ({be['stroke_m']:,.1f} m)"
    if be["status"] == STATUS_EVERY_PUSH:
        return (
            f"every push tried: already {kg(be['kg_at_floor'])} kg at "
            f"{be['n_floor_g']:.4f} (L {be['stroke_floor_m'] / 1000.0:,.0f} km)"
        )
    return "not charged up to 7.0"


def table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """A markdown table's lines."""
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out


def element_columns(felt: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(the element keys charged somewhere in either felt table, the others)."""
    keys = list(felt["offloads"]["headline"]["rows"][0]["elements"])
    used = [
        k
        for k in keys
        if any(r["elements"][k]["kg"] > 0.0 for o in felt["offloads"].values() for r in o["rows"])
    ]
    return used, [k for k in keys if k not in used]


def short(key: str) -> str:
    """'s1 aft skirt' for a table header."""
    stage, element = key.split(".")
    return f"{stage.replace('stage', 's')} {ELEMENT_WORDS.get(element, element)}"


def md_basis(data: dict[str, Any], unused: Sequence[str]) -> list[str]:
    """The header and section 1."""
    prov = data["provenance"]
    pad_diff = prov["pad_payload_kg"] - prov["p_ref_kg"]
    strokes = ", ".join(
        f"{s['stroke_m']:g} m at n = {s['n_g']:.4f}" for s in data["sweep2_strokes"]
    )
    return [
        "# RQ1 (structural, 2-D): sizing-only tables (generated)",
        "",
        f"Generated by `{SCRIPT}` on {prov['generated_utc']} at commit {prov['head']} "
        f"(code under {', '.join(CODE_PATHS)} identical to the run's commit "
        f"{prov['run_commit']}: {'yes' if prov['code_same_as_run'] else 'NO'}). Do not "
        "edit by hand: re-run the script (its data: RQ1-structural-2d-tables.json). Read "
        "with docs/findings/RQ1-structural-2d.md.",
        "",
        "**Sizing only** (D-SP7-31): no offload is solved here and no trajectory is flown "
        "except file A's pad baseline, whose flight is the structural envelope. Every dm "
        "is a first-order station sizing (D-SP7-01), not a measurement and not a detailed "
        "structural design. Every x* labelled an estimate (sections 6 and 7) comes from the "
        "coupled placement on SP1's penalty curve (the pre-registration's section 7 "
        "method) and is never a solved offload; solved values quoted beside come from the "
        "results files named there.",
        "",
        "## 1. Basis",
        "",
        "- Experiment: experiments/silo_structure_2d.yaml (file A) and its central "
        "structure (configs/structures/generic_f9_class_2d.yaml, sha256 "
        f"{prov['structure_sha256']}).",
        f"- Pad baseline flown afresh: P* {prov['pad_payload_kg']!r} kg against run A's "
        f"P_ref {prov['p_ref_kg']!r} kg (difference {pad_diff:+.6f} kg; results/"
        "silo_structure_2d/20261016T171513Z/metrics.json, offload.reference_payload_kg); "
        f"its flight took {prov['pad_wall_s']:.1f} s.",
        "- The push (sections 2 to 4): constant_accel, cold (no thrust on the track), "
        f"vertical, massless carriage, exit speed v_e = {V_EXIT_MPS!r} m/s; the felt load "
        f"n = (a + g_eff)/g0, so a = n g0 - g_eff with g_eff = {prov['g_eff_mps2']:.6f} "
        f"m/s^2 (the push's resting load g_eff/g0 = {prov['g_eff_mps2'] / G0_MPS2:.5f} g0), "
        "and the stroke L = v_e^2 / (2 a). The central structure's dynamic factor "
        "(rise_time: t_r 0.5 s, f 5 Hz, DLF 1.1273) and its ramped plateau (n_q above n: "
        "the plateau a drive ramping over t_r needs for the same L and v_e) are charged as "
        f"in the run. Sweep 2's strokes sit at {strokes} g0.",
        f"- Offloads: SP1's headline x = {X_HEADLINE_KG!r} kg and x = 0 (the full-load "
        "stack, the adverse bound), side by side as section 5 of the pre-registration "
        "registers. The stack a structural x* leaves is heavier than SP1's headline one, "
        "so at x = 41.26 t dm is understated and each break-even n overstated, both for "
        "the assist.",
        "- The table's route (the central case's transform re-pushed at each a) checked "
        "against sweep 2's own point transforms at its four strokes: the same dm to "
        f"{prov['cross_check_max_abs_kg']:.1e} kg at both offloads.",
        "- Elements never charged anywhere in the range at either offload: "
        f"{', '.join(element_words(k) for k in unused)} (the thrust structure is not in "
        "the load path on entry aft_ring).",
        "",
    ]


def md_felt(data: dict[str, Any], used: Sequence[str]) -> list[str]:
    """Sections 2 and 3: the push and dm, and dm by element, against n."""
    felt = data["felt"]
    head = felt["offloads"]["headline"]["rows"]
    full = felt["offloads"]["full_load"]["rows"]
    rows = [
        [
            f"{h['n_g']:.1f}",
            f"{h['accel_mps2']:.3f}",
            f"{h['stroke_m']:,.1f}",
            f"{h['n_q_g']:.3f}",
            f"{h['n_peak_g']:.3f}",
            f"{h['F_peak_N'] / 1e6:.2f}",
            kg(h["dm_stage1_kg"]),
            kg(h["dm_stage2_kg"]),
            f"{z['F_peak_N'] / 1e6:.2f}",
            kg(z["dm_stage1_kg"]),
            kg(z["dm_stage2_kg"]),
        ]
        for h, z in zip(head, full, strict=True)
    ]
    out = [
        "## 2. The push and dm against the felt load",
        "",
        "n: the felt load of the constant_accel push [g0]; a: its net acceleration "
        "[m/s^2]; L: the stroke [m]; n_q: the ramped plateau [g0]; n_peak: n_q under the "
        "dynamic factor [g0] (the same at both offloads); F_peak: the peak interface force "
        "[MN]; dm1 (the stage-1 elements and the interstage, D-SP7-36) and dm2 [kg], at "
        f"x = {tonnes(X_HEADLINE_KG)} t and at x = 0.",
        "",
        *table(
            [
                "n",
                "a",
                "L",
                "n_q",
                "n_peak",
                "F_peak (41.26 t)",
                "dm1 (41.26 t)",
                "dm2 (41.26 t)",
                "F_peak (x = 0)",
                "dm1 (x = 0)",
                "dm2 (x = 0)",
            ],
            rows,
        ),
        "",
    ]
    for label, part, title in (
        ("headline", "a", f"x = {kg(X_HEADLINE_KG, 3)} kg (SP1's headline offload)"),
        ("full_load", "b", "x = 0 (the full-load stack)"),
    ):
        block = felt["offloads"][label]["rows"]
        erows = [[f"{r['n_g']:.1f}"] + [kg(r["elements"][k]["kg"]) for k in used] for r in block]
        out += [
            f"## 3{part}. dm by element [kg], {title}",
            "",
            "s1 = stage 1, s2 = stage 2 (the interstage is charged to stage 1, D-SP7-36); "
            "stage 2 and the interstage are sized only where the push's peak load on the "
            "upper stack exceeds the pad envelope's (D-SP7-11).",
            "",
            *table(["n"] + [short(k) for k in used], erows),
            "",
        ]
    return out


def md_break_even(data: dict[str, Any], used: Sequence[str]) -> list[str]:
    """Section 4: the break-even n of each element at both offloads."""
    felt = data["felt"]
    be_h = felt["offloads"]["headline"]["break_even"]
    be_0 = felt["offloads"]["full_load"]["break_even"]
    rows = []
    for k in [*used, "dm", "stage2_sized"]:
        name = ROW_WORDS[k] if k in ROW_WORDS else element_words(k)
        modes = "n/a"
        for be in (be_h, be_0):
            if "push_mode" in be[k]:
                modes = f"{mode(be[k]['push_mode'])} / {mode(be[k]['envelope_mode'])}"
                break
        mono = "" if be_h[k]["monotone"] and be_0[k]["monotone"] else " (not monotone)"
        rows.append([name + mono, be_cell(be_h[k]), be_cell(be_0[k]), modes])
    return [
        "## 4. Break-even felt load per element",
        "",
        "The smallest felt load n [g0] at which the element's increment is positive, "
        f"bisected to {BISECT_TOL_G} g0 between the last uncharged and the first charged "
        "point of the grid, with the stroke it implies at v_e (L [m]); below 1.2 g0 the "
        "search goes down to the push's resting load plus "
        f"{N_FLOOR_ABOVE_REST_G} g0 (a drive that only just lifts the stack, its stroke "
        "hundreds of km at this exit speed). 'Every push tried': the element is charged "
        "already there, so it has no break-even (the load ring is new hardware sized in "
        "closed form with no envelope credit; at x = 0 the aft skirt carries more than "
        "the pad envelope gives it at any push). The modes are the element's governing "
        "push and envelope modes at the break-even (at x = 41.26 t where it has one).",
        "",
        *table(
            [
                "element",
                f"x = {tonnes(X_HEADLINE_KG)} t: n [g0] (L)",
                "x = 0: n [g0] (L)",
                "push / envelope mode at onset",
            ],
            rows,
        ),
        "",
    ]


def md_solved_central(data: dict[str, Any]) -> list[str]:
    """Section 5: the central case's elements at run A's solved x*."""
    sc = data["solved_central"]
    rows = [
        [
            element_words(k),
            kg(el["kg"]),
            kg(float(sc["recorded_elements_kg"][k])),
            f"{100.0 * el['kg'] / sc['dm_kg']:.1f}%",
            mode(el["push_mode"]),
            mode(el["envelope_mode"]),
            "" if el["station_index"] is None else str(el["station_index"]),
            "" if el["z_m"] is None else f"{el['z_m']:.2f}",
        ]
        for k, el in sc["elements"].items()
        if el["kg"] > 0.0
    ]
    return [
        f"## 5. The central case at run A's solved x* ({kg(sc['offload_kg'])} kg)",
        "",
        "A sizing at the solved offload (results/silo_structure_2d/20261016T171513Z/"
        "metrics.json, case silo_cold_s1_st, offload_kg) against the pad flown here; the "
        "recorded column is that case's structure_elements (largest difference "
        f"{sc['max_abs_diff_kg']:.1e} kg; dm {kg(sc['dm_kg'])} kg here, "
        f"{kg(sc['recorded_dm_kg'])} kg recorded). The modes are those at the element's "
        "governing station (its largest increment): the push's and the pad envelope's "
        "there; z above the stage-1 load ring [m]; the ring and the domes have no station "
        f"index. The push: n_q {sc['n_q_g']:.4f}, DLF {sc['dlf']:.4f}, n_peak "
        f"{sc['n_peak_g']:.4f} g0, F_peak {sc['F_peak_N'] / 1e6:.3f} MN.",
        "",
        *table(
            [
                "element",
                "dm here [kg]",
                "recorded [kg]",
                "share of dm",
                "push mode",
                "envelope mode",
                "station",
                "z [m]",
            ],
            rows,
        ),
        "",
    ]


def md_sweeps(data: dict[str, Any]) -> list[str]:
    """Section 6: the central estimate against the solve, and the band ends, per point."""
    bands = data["sweep_bands"]
    rows_c = []
    rows_b = []
    for r in bands:
        c = r["central"]
        solved = solved_cell(r["solved_status"], r["solved_x_kg"])
        diff = (
            "n/a"
            if c["no_offload"] or r["solved_status"] != "ok"
            else f"{c['x_kg'] - r['solved_x_kg']:+,.1f}"
        )
        rows_c.append(
            [
                str(r["sweep"]),
                f"{r['stroke_m']:g}",
                f"{r['exit_speed_mps']:.2f}",
                f"{c['n_q_g']:.3f} / {c['n_peak_g']:.3f}",
                kg(r["x0_sp1_kg"]),
                f"{r['x0_run_kg'] - r['x0_sp1_kg']:+.4f}",
                x_cell(c),
                dm_cell(c),
                solved,
                f"{kg(r['solved_dm_kg'] - r['solved_dm_stage2_kg'])} + "
                f"{kg(r['solved_dm_stage2_kg'])}",
                diff,
            ]
        )
        rows_b.append(
            [str(r["sweep"]), f"{r['stroke_m']:g}"]
            + [
                f"{x_cell(r[t])}; dm {dm_cell(r[t])}"
                for t in ("phys_hi", "phys_lo", "phys_lo_scaled")
            ]
        )
    factor = bands[0]["phys_lo_scaled"]["factor"]
    return [
        "## 6. The sweep points: the central estimate and the physics band's estimated ends",
        "",
        "Section 7's method, sizing only: each case's own transform (the point's push, the "
        "pad's envelope at P_ref), the coupled placement x = max(0, X(dm1(x) + w dm2(x))) "
        f"with w = {STAGE2_DM_WEIGHT:.3f} on SP1's penalty curve (0, 2, 4 and 8.1 t of "
        "added stage-1 dry mass to 41,262.908, 32,285.203, 22,875.961 and 1,980.477 kg, "
        "linear between the rows, extrapolated along the last segment at -5.096 kg/kg) "
        "shifted to the point's uncharged x0 (SP1's sweep index, results/silo_offload_2d/"
        "20261003T112949Z/sweep_<k>/sweep_index.csv; the run's own uncharged x* differs "
        "by the column shown). Biases (section 7): a chord between the curve's rows "
        "places x low (against the assist), the extrapolated last segment high (for it); "
        "the shift for x0 below 41.26 t favours the assist and, for x0 above it, places x "
        "low if the slope keeps flattening. dm1 + dm2 [kg] at the estimate's x (at x = 0 "
        "for no offload, where dm_eq(0) = dm1 + w dm2 at x = 0 is compared with the "
        "shifted curve's zero crossing). %: of SP1's 41,262.9 kg, then of the point's own "
        "x0.",
        "",
        "### 6a. The central case: estimate against sweep A's solve",
        "",
        "Solved: results/silo_structure_2d/20261016T171522Z/sweep_<k>/sweep_index.csv "
        "(`<case>.offload_kg`, `.structure_dm_kg`, `.structure_dm_stage2_kg`). The last "
        "column is the placement's error on a solved case (estimate - solved).",
        "",
        *table(
            [
                "sweep",
                "L [m]",
                "exit [m/s]",
                "n_q / n_peak",
                "x0 SP1 [kg]",
                "run - SP1 [kg]",
                "estimate [kg]",
                "dm at estimate",
                "solved [kg]",
                "dm at solved",
                "estimate - solved [kg]",
            ],
            rows_c,
        ),
        "",
        "### 6b. The physics band's estimated ends (the headline's sets)",
        "",
        "The band ends are the headline's frozen sets placed at the point's push (design "
        '4.2.6, "the headline\'s sets"): sizing-only estimates, never flown at a sweep '
        "point. phys_hi is the adverse end (its plausibility factor is 1); phys_lo is the "
        "low-mass end unscaled and scaled by the plausibility rule's factor "
        f"{factor:.4f} (D-SP7-33, D-SP7-41), which multiplies the case's whole dm.",
        "",
        *table(
            [
                "sweep",
                "L [m]",
                "phys_hi estimate [kg]",
                "phys_lo (unscaled) estimate [kg]",
                "phys_lo scaled estimate [kg]",
            ],
            rows_b,
        ),
        "",
    ]


def md_others(data: dict[str, Any]) -> list[str]:
    """Section 7: the same at file A's other pushes."""
    rows_c = []
    rows_b = []
    for r in data["other_bands"]:
        c = r["central"]
        rows_c.append(
            [
                r["case"],
                kg(r["x0_run_kg"]),
                x_cell(c),
                dm_cell(c),
                solved_cell(r["solved_status"], r["solved_x_kg"]),
                kg(r["solved_dm_kg"]),
                f"{c['x_kg'] - r['solved_x_kg']:+,.1f}",
            ]
        )
        rows_b.append(
            [r["case"]]
            + [
                f"{x_cell(r[t])}; dm {dm_cell(r[t])}"
                for t in ("phys_hi", "phys_lo", "phys_lo_scaled")
            ]
        )
    return [
        "## 7. The same at file A's other pushes",
        "",
        "As section 6, with x0 the run's own uncharged x* of the same variant (results/"
        "silo_structure_2d/20261016T171513Z/metrics.json: silo_hot_full_s1, "
        "silo_hot_ramp_s1, silo_cold_200m_s1). silo_hot_full had no SP1 offload, so the "
        "pre-registration's section 7 placed it on an estimated x0 of 39,506 kg; here it "
        "is placed on the run's solved one. The solved columns are the run's "
        "silo_hot_full_s1_st, silo_hot_ramp_s1_st and silo_cold_200m_s1_st (offload_kg, "
        "structure_dm_kg).",
        "",
        *table(
            [
                "case",
                "x0 run [kg]",
                "central estimate [kg]",
                "dm at estimate",
                "solved [kg]",
                "dm at solved [kg]",
                "estimate - solved [kg]",
            ],
            rows_c,
        ),
        "",
        *table(
            [
                "case",
                "phys_hi estimate [kg]",
                "phys_lo (unscaled) estimate [kg]",
                "phys_lo scaled estimate [kg]",
            ],
            rows_b,
        ),
        "",
    ]


def markdown(data: dict[str, Any]) -> str:
    """The generated note (sections 1 to 7)."""
    used, unused = element_columns(data["felt"])
    lines = [
        *md_basis(data, unused),
        *md_felt(data, used),
        *md_break_even(data, used),
        *md_solved_central(data),
        *md_sweeps(data),
        *md_others(data),
    ]
    return "\n".join(lines).rstrip("\n")


# ---------------------------------------------------------------------------------- main


def main(argv: Sequence[str]) -> int:
    """Compute every table, write the markdown and its JSON, print a short log. With
    ``--markdown-only``, re-render the markdown from the JSON this script last wrote
    (nothing is flown or sized)."""
    if "--markdown-only" in argv:
        data = read_json(OUT_JSON)
        OUT_MD.write_text(markdown(data) + "\n", encoding="utf-8", newline="\n")
        print(f"re-rendered {OUT_MD.relative_to(REPO).as_posix()} from its JSON")
        return 0
    t_start = time.perf_counter()
    run_a = read_json(RUN_A / "metrics.json")
    p_ref = float(run_a["offload"]["reference_payload_kg"])
    run_commit = str(run_a["git"]["hash"])
    if SP1_PENALTY_CURVE.uncharged_kg != X_HEADLINE_KG:
        raise SystemExit("SP1's penalty curve no longer starts at the registered headline")
    resolved = cli.load_experiment(FILE_A)
    assert resolved.structure is not None
    print(f"pad: flying file A's baseline (P_ref {p_ref!r} kg) ...")
    pad, p_star, pad_wall = fly_pad(resolved, p_ref)
    print(f"pad: P* {p_star!r} kg in {pad_wall:.1f} s")
    base = sim.offload_structure_transform(case_named(resolved, TABLE_BASE_CASE), pad, p_ref)
    if base.assist.exit_speed_input_mps != V_EXIT_MPS:
        raise SystemExit("the base variant's exit speed is not the registered 76.707... m/s")
    sizer = FeltSizer(base)
    grid = [t / 10.0 for t in N_GRID_TENTHS]
    print("felt-load tables and break-even values ...")
    felt = felt_tables(sizer, grid)
    print(f"  {len(sizer.memo)} sizings so far")
    checks = cross_check(sizer, resolved, pad, p_ref)
    print("central case at run A's solved x* ...")
    sc = solved_central(
        run_a, sim.offload_structure_transform(case_named(resolved, "silo_cold_s1_st"), pad, p_ref)
    )
    print(f"  largest element difference against the record {sc['max_abs_diff_kg']:.3e} kg")
    sweep_rows = {k: read_index(SWEEP_A / f"sweep_{k}" / "sweep_index.csv") for k in (1, 2)}
    print("sweep points ...")
    bands = sweep_bands(resolved, pad, p_ref, sweep_rows)
    for r in bands:
        if abs(r["x0_run_kg"] - r["x0_sp1_kg"]) > REPRO_TOL_KG:
            print(f"  NOTE: sweep {r['sweep']} L {r['stroke_m']:g}: run's x0 off SP1's")
    others = other_bands(resolved, pad, p_ref, run_a)
    data = {
        "provenance": {
            "script": SCRIPT,
            "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "head": git("rev-parse", "--short=12", "HEAD"),
            "run_commit": run_commit,
            "code_same_as_run": code_same_as(run_commit),
            "structure_sha256": resolved.structure.file.sha256,
            "p_ref_kg": p_ref,
            "pad_payload_kg": p_star,
            "pad_wall_s": pad_wall,
            "g_eff_mps2": base.g_eff_mps2,
            "v_exit_mps": V_EXIT_MPS,
            "x_headline_kg": X_HEADLINE_KG,
            "stage2_weight": STAGE2_DM_WEIGHT,
            "cross_check_max_abs_kg": max(abs(c["table_kg"] - c["point_kg"]) for c in checks),
            "sizings": len(sizer.memo),
            "wall_s": time.perf_counter() - t_start,
            "sources": {
                "run_a": str(RUN_A.relative_to(REPO).as_posix()),
                "sweep_a": str(SWEEP_A.relative_to(REPO).as_posix()),
                "sp1_sweeps": str(SP1_SWEEPS.relative_to(REPO).as_posix()),
            },
        },
        "felt": felt,
        "sweep2_strokes": sweep2_strokes(sizer, resolved),
        "cross_check": checks,
        "solved_central": sc,
        "sweep_bands": bands,
        "other_bands": others,
    }
    OUT_JSON.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")
    OUT_MD.write_text(markdown(data) + "\n", encoding="utf-8", newline="\n")
    print(
        f"wrote {OUT_MD.relative_to(REPO).as_posix()} and {OUT_JSON.relative_to(REPO).as_posix()}"
    )
    print(f"done in {time.perf_counter() - t_start:.1f} s ({len(sizer.memo)} felt-table sizings)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
