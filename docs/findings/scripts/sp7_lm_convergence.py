"""SP7 step S7b: the linear-motor convergence check (exit criterion 6's linear-motor x*).

This script runs the check registered in docs/phases/inputs/2026-11-03-SP7-preregistration-part2.md
(part 2 of the pre-registration, "the addendum"), section 1 ("The linear-motor convergence
check"), which section 9 lists among the checks that block a citation: "the linear-motor
convergence check of section 1 failing (0.1%): it blocks every linear-motor number until
explained". It is exit criterion 6 of docs/phases/inputs/2026-10-08-SP7-design.md (section
6) for "one linear-motor structural x*", registered so that it is not an extra,
unregistered solve. Its numbers are a check quoted in the findings note's convergence
line, never a finding.

What it does. Case lm_fixed_s1_st of experiments/silo_drive_2d.yaml (file B), read from the
committed file through ``cli.load_experiment``; of its runs only three are used: the pad
baseline, the variant lm_fixed (the case's start: resolved, not flown on its own) and that
case. The case is solved in two chains:

- the shipped budget;
- its tightening by the file's ``checks.convergence`` (``SearchContext.tightened``: every
  search and final tolerance divided by tighten_factor 10, the max-step caps multiplied by
  max_step_factor 0.5; the addendum's words, with one exception: brentq_rtol is not
  divided, and file B sets it at its floor, 4 eps, below which no configuration can go).

Each chain flies its own pad: that pad's P* is the chain's P_ref and its recorded flight is
the chain's structural envelope. Each chain's flown push is flown with that chain's
context. The transform is built as the pipeline builds it (``sim.build_structure_transform``
through sp7_convergence.py's ``_transform``, which keeps a copy of the start run's shipped
SearchContext as the transform's ``push_context``); for the tightened chain that field is
then replaced by the tightened context, the very object the tightened solve's problem
factory uses (``dataclasses.replace(transform, push_context=tightened)``). This is how S4b's
linear-motor convergence test passes it (tests/test_structure_linear_motor.py, fixture
``lm_solves``: ``tight_tr = dataclasses.replace(tr, push_context=tight_ctx)``), because
nothing tightens the push automatically (docs/physics.md, "The flown push of a linear
motor"; ``sim.StructureTransform``'s docstring). The builder's own check, the sizing at x
= 0 flown once when the transform is built, flies with the shipped context in both chains:
it only refuses a push that cannot release and is not used by the solve. The structure's
fixed-point tolerance (``sim.STRUCTURE_FIXED_POINT_TOL_KG``, 1e-6 kg) is unchanged. Each
chain's x* is checked by an independent payload search, at that chain's budget, of the
offloaded vehicle carrying dm at x* (``config.offload_solved_run``), its push flown in that
search with the same chain's context. Each pad flight, solve and verification mirrors what
``launchsim run`` does (``sim.run_planar``, ``sim.solve_resolved_offload`` and the
pipeline's verification); the only difference is the tightened context in the second
chain. Beside the check (never a pass criterion), each solve part flies the push at x*
once more, alone, with its chain's push context, and records its events (whether a
``power_limit`` sub-phase boundary is crossed: KI-071) and its release state.

Among what neither chain tightens (not exhaustive), so that the check does not bound x*'s
dependence on any of it (``_not_tightened``, recorded in report.json as ``not_tightened``
with the values the run used, read from the code and the resolved experiment): the LTG
finite-difference steps, the brackets, the penalties and the false-root guard
(``SearchBudget.tightened``); the gamma* grid, the gamma* refine's iteration cap, the
payload search's backoff cap and brentq_rtol (``SearchBudget.tightened`` leaves them
unchanged); the track-peak scan resolution (``metrics.TRACK_PEAK_SCAN_POINTS``), on which
KI-071's dm step depends; the time-series sampling interval (``integrator.sample_dt_s``),
whose rows give the envelope's load cases; and the structure's fixed-point tolerance and
iteration cap.

The report gives three verdicts, and ``passed`` is their conjunction;
docs/findings/scripts/sp7_s7b_checks.py reads the report (its check 9), recombines the
three from the report's items and checks them against the report's own (its docstring
says which items it recomputes and which it takes as recorded):

- the registered rule (section 1's pass rule): both solves ok, the tightened x* within
  rel_tol 1e-3 (0.1%) of the shipped x*, and the shipped x* equal to run B's
  lm_fixed_s1_st within 0.002 kg (``report --run-b``);
- x* confirmed (section 1: "each chain's x* is checked by an independent payload search
  at its own budget"): both verifications ended ok with |P* - P_ref| <=
  checks.search_final_flag_rel P_ref. A verification that misses is an outcome of the
  check (x* not confirmed), not a departure from its method;
- run as registered (section 1's method): each verification flew the x* and the dm its
  solve found at x*; each chain's own pad, its search ended ok (its P* is the chain's
  P_ref) and flown at the chain's budget (the pad's budget equal to the solve's); in each
  chain, the solve's and the verification's pushes flown with that chain's context
  (untightened in the shipped chain, tightened in the other) and each push context's
  budget equal to its search's; "from the same code as run B" (``git diff --quiet <run
  B's commit> <HEAD> -- src configs experiments pyproject.toml uv.lock tests`` exits 0 for
  HEAD as read when the process loaded its modules and when each part writes its record,
  and those paths clean in the working tree at both readings); and "a committed script"
  (section 1): this script and sp7_convergence.py, their sha256 when the process loaded
  them and when each part writes its record both equal to their blobs at that part's
  HEAD, and the same in every part.

The stations part of criterion 6 is file A's (passed at S7a) and is not repeated here
(section 1): the station model does not depend on the drive.

Output. Everything goes under --out (JSON per part, plus each chain's pickled pad time
series and events, which the later parts read). --out may not lie inside the repository
(refused, as sp7_convergence.py refuses it), so nothing is written under results/, configs/
or elsewhere in the tree, apart from the bytecode caches (__pycache__/, gitignored) that
Python writes for the modules it imports unless bytecode writing is off. results/ is read
only by ``report`` (run B's metrics.json, with --run-b). No plots.

A dry run of the plumbing (S7b's brief allows one on a synthetic case): --experiment and
--case name another experiment file and structural linear-motor case; every part then
records ``registered: false``, the report says it is a dry run, and the checks script
does not evaluate its report. Without them the parts solve the registered case.

Usage, from the repository root. The parts run in this order, each in its own process, so
that each is meant to stay under the brief's ten minutes (the addendum's section 11
estimates 5-10 min for the whole check; S7a's convergence check, the pre-registration
part 1's on file A, took 277.5 s over all its parts: docs/findings/RQ1-structural-2d.md,
"Convergence"). The registered case had not been timed when this script was committed;
each part records its wall time (``wall_s``). ``--part all`` runs every part in one
process:

    uv run python docs/findings/scripts/sp7_lm_convergence.py --out DIR --part shipped-pad
    ... --part shipped-solve, shipped-verify, tightened-pad, tightened-solve,
    tightened-verify, then
    uv run python docs/findings/scripts/sp7_lm_convergence.py --out DIR --part report \
        --run-b results/silo_drive_2d/<timestamp>

It imports helpers from docs/findings/scripts/sp7_convergence.py (S7a's committed check,
on sys.path as this script's own folder) and changes nothing in it.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import pickle
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sp7_convergence as s7a

from launchsim import cli, metrics, sim
from launchsim.compare import reference_payload_kg
from launchsim.config import (
    BRENTQ_MIN_RTOL,
    STRUCTURE_SIZING_FULL_LOAD,
    ConvergenceConfig,
    ResolvedExperiment,
    ResolvedOffloadCase,
    offload_solved_run,
)
from launchsim.offload import planar_problem_factory, solve_offload, verification_from_record
from launchsim.search import SearchContext, run_search
from launchsim.vehicle import with_offload, with_payload

REPO = s7a.REPO
"""The repository root (sp7_convergence.py's, the same tree)."""
EXPERIMENT = REPO / "experiments" / "silo_drive_2d.yaml"
"""File B of the pre-registration's part 2, read from the committed file."""
CASE = "lm_fixed_s1_st"
"""The registered case: lm_fixed's central structural stage-1 solve (section 1)."""
SHIPPED, TIGHTENED = s7a.SHIPPED, s7a.TIGHTENED
"""The two chains."""
REL_TOL = 1e-3
"""The registered pass rule: the tightened x* within 0.1% of the shipped x* (section 1;
the file's checks.convergence.rel_tol, recorded beside)."""
RUN_B_MATCH_KG = 0.002
"""The registered reproduction tolerance of the shipped x* against run B's [kg]."""
CODE_PATHS = ("src", "configs", "experiments", "pyproject.toml", "uv.lock", "tests")
"""The paths "from the same code as run B" compares (section 1; the brief)."""
SCRIPT_PATHS = (
    "docs/findings/scripts/sp7_lm_convergence.py",
    "docs/findings/scripts/sp7_convergence.py",
)
"""The check's own scripts (this file and the S7a helpers it imports), relative to the
repository: section 1's "a committed script", recorded by every part."""
PARTS = (
    "shipped-pad",
    "shipped-solve",
    "shipped-verify",
    "tightened-pad",
    "tightened-solve",
    "tightened-verify",
    "report",
)
"""No stations part: criterion 6's stations part is file A's (section 1)."""
PAD_SEARCH_OK = "ok"
"""A pad's payload search status when it ended with a P* (the chain's P_ref)."""
NOT_TIGHTENED_SCOPE = (
    "among what neither chain tightens (not exhaustive): the check does not bound x*'s "
    "dependence on any of these"
)
"""How report.json's ``not_tightened`` list reads (its ``not_tightened_scope``)."""


@dataclass(frozen=True)
class Target:
    """What the parts solve: the experiment file and the case; registered only for file B's
    lm_fixed_s1_st (anything else is a dry run of the plumbing)."""

    experiment: Path
    case: str

    @property
    def registered(self) -> bool:
        """Whether this is the registered check."""
        return self.experiment.resolve() == EXPERIMENT.resolve() and self.case == CASE

    def items(self) -> dict[str, Any]:
        """The target as plain data (the experiment relative to the repository when inside
        it, else its file name only; its sha256)."""
        path = self.experiment.resolve()
        try:
            shown = path.relative_to(REPO).as_posix()
        except ValueError:
            shown = f"(outside the repository) {path.name}"
        return {
            "experiment": shown,
            "experiment_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "case": self.case,
            "registered": self.registered,
            "dry_run": not self.registered,
        }


# ------------------------------------------------------------------------------- helpers


def _load(target: Target) -> tuple[ResolvedExperiment, ResolvedOffloadCase, ConvergenceConfig]:
    """The experiment resolved as ``launchsim run`` resolves it (``cli.load_experiment``),
    the target case (a structural stage-1 solve) and the shared checks' convergence block."""
    try:
        resolved = cli.load_experiment(target.experiment)
    except cli.CliError as exc:
        raise SystemExit(f"error: {exc}") from exc
    if resolved.offload is None:
        raise SystemExit(f"error: {target.experiment} has no offload block")
    case = next((c for c in resolved.offload.cases if c.name == target.case), None)
    if case is None or case.structure is None or not case.config.solved:
        raise SystemExit(f"error: {target.case} is not a solved structural case")
    planar = resolved.baseline.run.planar
    assert planar is not None
    return resolved, case, planar.checks.convergence


def _check_target(out: Path, target: Target) -> None:
    """Refuse to mix targets in one --out: every part's JSON must name the same experiment
    file (by sha256) and case as this call."""
    mine = target.items()
    for path in sorted(out.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        theirs = data.get("target")
        if theirs is None:
            continue
        if (theirs["experiment_sha256"], theirs["case"]) != (
            mine["experiment_sha256"],
            mine["case"],
        ):
            raise SystemExit(
                f"error: {path.name} was written for {theirs['experiment']} / {theirs['case']}, "
                f"not {mine['experiment']} / {mine['case']}: use another --out"
            )


def _chain_transform(
    chain: str,
    resolved: ResolvedExperiment,
    case: ResolvedOffloadCase,
    pad: dict[str, Any],
    ctx: SearchContext,
) -> sim.StructureTransform:
    """The case's StructureTransform against the chain's pad (sp7_convergence's
    ``_transform``: the pipeline's builder, its push_context a copy of the shipped context),
    with the tightened chain's push_context replaced by ctx, the tightened context its solve
    uses (S4b's convergence test). Refused for a push that is not flown (not a linear
    motor)."""
    transform = s7a._transform(resolved, case, pad)
    if not transform.flies_push or transform.push_context is None:
        raise SystemExit(f"error: {case.name} does not fly a linear-motor push")
    if chain == TIGHTENED:
        transform = dataclasses.replace(transform, push_context=ctx)
    return transform


def _push_items(
    transform: sim.StructureTransform, case: ResolvedOffloadCase, conv: ConvergenceConfig
) -> dict[str, Any]:
    """The transform's push context for the record: its budget and step caps, and whether
    they equal the tightened ones (the case's start context tightened by conv, built
    afresh for the comparison)."""
    assert transform.push_context is not None
    budget = s7a._budget_items(transform.push_context)
    tight = s7a._budget_items(s7a._context(case.start, conv))
    return {"push_budget": budget, "push_context_tightened": budget == tight}


def _not_tightened(resolved: ResolvedExperiment, case: ResolvedOffloadCase) -> list[str]:
    """Among what ``SearchContext.tightened`` and this check leave unchanged in both chains
    (not exhaustive; report.json's ``not_tightened``, read as NOT_TIGHTENED_SCOPE says),
    each with the value the run used: the budget items from the case start's shipped
    context (``SearchBudget.tightened`` copies them unchanged into the tightened one), the
    sampling interval from the pad baseline (both chains' pads fly at it), the rest from
    the code's own constants."""
    budget = s7a._context(case.start, None).budget
    sample_dt_s = resolved.baseline.run.integrator.sample_dt_s
    return [
        "the LTG finite-difference steps, the brackets, the penalties and the false-root guard "
        "(SearchBudget.tightened leaves them unchanged)",
        f"the gamma* grid ({len(budget.gamma_grid_rad)} points), the gamma* refine's "
        f"iteration cap (refine_maxiter {budget.refine_maxiter}) and the payload search's "
        f"backoff cap (payload_backoff_max {budget.payload_backoff_max}) "
        "(SearchBudget.tightened leaves them unchanged)",
        f"brentq_rtol {budget.brentq_rtol!r} (SearchBudget.tightened leaves it unchanged; "
        f"config.BRENTQ_MIN_RTOL, the floor no configuration goes below, is "
        f"{BRENTQ_MIN_RTOL!r})",
        "the track-peak scan resolution (metrics.TRACK_PEAK_SCAN_POINTS, "
        f"{metrics.TRACK_PEAK_SCAN_POINTS} points per sub-phase), on which KI-071's dm step "
        "depends",
        f"the time-series sampling interval (integrator.sample_dt_s, {sample_dt_s!r} s), "
        "whose rows give the envelope's load cases",
        "the structure's fixed-point tolerance (sim.STRUCTURE_FIXED_POINT_TOL_KG, "
        f"{sim.STRUCTURE_FIXED_POINT_TOL_KG:g} kg; section 1) and its iteration cap "
        f"(sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS, {sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS})",
    ]


def _push_at(
    transform: sim.StructureTransform, x_kg: float, sizing: sim.StructureSizing
) -> dict[str, Any]:
    """Beside the check: the push of the stack the sizing at x [kg] reads, flown alone once
    more with the transform's push context (``sim.flown_push_trace``). Under flown sizing
    (the registered case's) that is the stack the solve charges at x: offloaded by x, at
    P_ref, carrying the sizing's dm, as ``StructureTransform.sizing`` builds it. Under
    full_load sizing it is the full-load start vehicle at P_ref carrying the sizing's dm,
    as ``StructureTransform.sizing`` sizes it, whatever x is. Returns its events (name,
    time t_s [s] absolute on the run's clock, phase), its release time
    t_release_s [s] on the same clock, and the release event's values as the planar
    StateView records them in the planar ECI ascent frame after the release mapping
    (alt_m and downrange_m [m]; speed_rel_mps, Earth-relative, and speed_inertial_mps
    [m/s]; gamma_rel_rad [rad], Earth-relative)."""
    assert transform.push_context is not None
    if transform.settings.sizing == STRUCTURE_SIZING_FULL_LOAD:
        base = transform.start_vehicle
    else:
        base = with_offload(transform.start_vehicle, transform.mode, x_kg)
    flown = sim.charge_structure(
        with_payload(base, transform.reference_payload_kg),
        sizing.dm_stage1_kg,
        sizing.dm_stage2_kg,
    )
    trace = sim.flown_push_trace(transform.push_context, flown)
    release = trace.first_event("release")
    return {
        "events": [{"name": e.name, "t_s": e.t_s, "phase": e.phase} for e in trace.events],
        "t_release_s": trace.t_release_s,
        "release_state": None if release is None else dict(release.values),
        "power_limit_logged": any(e.name == "power_limit" for e in trace.events),
    }


def _number(value: Any) -> float | None:
    """A recorded number as a float, None when absent or not finite (a failed solve's x*
    is NaN, written as null)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) else None


def _common(target: Target, part: str, chain: str | None) -> dict[str, Any]:
    """The items every part's JSON starts with."""
    return {"part": part, "chain": chain, "target": target.items()}


def _sha256_or_none(data: bytes | None) -> str | None:
    """The hex sha256 of bytes, None for None."""
    return None if data is None else hashlib.sha256(data).hexdigest()


def _script_sha256s() -> dict[str, str | None]:
    """Each of SCRIPT_PATHS's sha256 on disk now (None for a missing file)."""
    out: dict[str, str | None] = {}
    for relpath in SCRIPT_PATHS:
        path = REPO / relpath
        out[relpath] = _sha256_or_none(path.read_bytes() if path.is_file() else None)
    return out


SCRIPTS_AT_IMPORT = _script_sha256s()
"""Each script's sha256 read just after this process loaded its modules (this module's
body, after its imports): the code this process runs, unless a file changed during the
imports."""
GIT_AT_IMPORT = s7a._git()
"""S7a's git record (HEAD, the code paths' cleanliness in the working tree) read just after
this process loaded its modules: the launchsim code it runs, unless a file changed during
the imports."""


def _git_items() -> dict[str, Any]:
    """S7a's git record read now, when the part writes its record (HEAD and the code paths'
    cleanliness in the working tree), with the same record read when the process loaded
    its modules (``at_import``: GIT_AT_IMPORT); and the check's own scripts: each file's
    sha256 when the process loaded it (``sha256_at_import``) and now (``sha256``), its
    blob's at HEAD now (None when HEAD does not hold it, e.g. not yet committed) and whether
    all three are equal (``as_committed``)."""
    data = s7a._git()
    data["at_import"] = GIT_AT_IMPORT
    now = _script_sha256s()
    scripts: dict[str, dict[str, Any]] = {}
    for relpath in SCRIPT_PATHS:
        proc = subprocess.run(
            ["git", "show", f"HEAD:{relpath}"], cwd=REPO, capture_output=True, check=False
        )
        at_head = _sha256_or_none(proc.stdout if proc.returncode == 0 else None)
        scripts[relpath] = {
            "sha256_at_import": SCRIPTS_AT_IMPORT[relpath],
            "sha256": now[relpath],
            "head_sha256": at_head,
            "as_committed": (
                at_head is not None and now[relpath] == at_head == SCRIPTS_AT_IMPORT[relpath]
            ),
        }
    data["scripts"] = scripts
    return data


# --------------------------------------------------------------------------------- parts


def part_pad(out: Path, chain: str, target: Target) -> dict[str, Any]:
    """Fly a chain's pad baseline as ``sim.run_planar`` flies a searched run (its payload
    search, then the recorded run's Result), at that chain's budget (sp7_convergence.py's
    ``part_pad`` on this target). P_ref is its P* (``compare.reference_payload_kg``).
    Pickles the time series and events (the envelope's input) with P_ref, and writes
    <chain>_pad.json."""
    t0, started = time.perf_counter(), s7a._now()
    resolved, _, conv = _load(target)
    baseline = resolved.baseline
    vehicle = baseline.to_vehicle()
    setup = sim.planar_setup(baseline.run, vehicle)
    ctx = s7a._context(baseline, s7a._conv_for(chain, conv))
    record = run_search(ctx)
    if record.trace is None or record.final is None:
        raise SystemExit(f"error: the {chain} pad search ended {record.status}")
    result = sim.simulate_planar(
        record.trace,
        with_payload(vehicle, record.final.at_final.payload_kg),
        setup,
        sample_dt_s=baseline.run.integrator.sample_dt_s,
        figure_items=sim.search_metrics(record, vehicle.payload_mass_kg),
        search=record,
        run_flags=list(record.flags),
        run_assumptions=sim.planar_run_assumptions(baseline.run, vehicle, setup),
    )
    p_ref_kg = reference_payload_kg(sim.RunResult(baseline.name, baseline, result))
    with (out / f"{chain}_pad.pkl").open("wb") as fh:
        pickle.dump(
            {"timeseries": result.timeseries, "events": result.events, "p_ref_kg": p_ref_kg},
            fh,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    data = {
        **_common(target, f"{chain}-pad", chain),
        "run": baseline.name,
        "status": result.status,
        "search": s7a._search_items(record),
        "p_ref_kg": p_ref_kg,
        "run_checks_failed": result.metrics.get("run_checks_failed"),
        "budget": s7a._budget_items(ctx),
        "git": _git_items(),
        "started_utc": started,
        "ended_utc": s7a._now(),
        "wall_s": time.perf_counter() - t0,
    }
    s7a._write_json(out, f"{chain}_pad.json", data)
    return data


def part_solve(out: Path, chain: str, target: Target) -> dict[str, Any]:
    """Solve the case's stage-1 offload at the chain's P_ref with its transform, as
    ``sim.solve_resolved_offload`` does (no built-in verification), at the chain's budget,
    the push flown with the chain's context. Writes <chain>_solve.json: x*, the solve's
    figures, flags and logged evaluations, the sizing at x* and at x = 0, the solve's
    budget and the push context's (``push_budget``; ``push_budget_equals_budget``), whether
    the push context is tightened, and, beside, the push at x*.
    ``push_context_is_solve_context`` records object identity, not equality: true in the
    tightened chain, whose push context is replaced by the very context the solve uses;
    false in the shipped chain, whose push context is the builder's own build of the same
    start's shipped context (an equal copy: its budget equals the solve's)."""
    t0, started = time.perf_counter(), s7a._now()
    resolved, case, conv = _load(target)
    pad = s7a._load_pad(out, chain)
    ctx = s7a._context(case.start, s7a._conv_for(chain, conv))
    transform = _chain_transform(chain, resolved, case, pad, ctx)
    res = solve_offload(
        planar_problem_factory(ctx),
        case.start.to_vehicle(),
        case.config.mode,
        pad["p_ref_kg"],
        verify=False,
        transform=transform,
    )
    ok_x = math.isfinite(res.offload_kg)
    at_x = transform.sizing_at(res.offload_kg) if ok_x else None
    at_0 = transform.sizing_at(0.0)
    budget = s7a._budget_items(ctx)
    push = _push_items(transform, case, conv)
    data = {
        **_common(target, f"{chain}-solve", chain),
        "case": target.case,
        "p_ref_kg": pad["p_ref_kg"],
        "status": res.status,
        "offload_kg": res.offload_kg,
        "root_kg": res.root_kg,
        "load_kg": res.load_kg,
        "gamma_star_rad": res.gamma_star_rad,
        "m_res_kg": res.m_res_kg,
        "dv_margin_mps": res.dv_margin_mps,
        "dv_shortfall_mps": res.dv_shortfall_mps,
        "n_evaluations": res.n_evaluations,
        "failure_kind": res.failure_kind,
        "failure_message": res.failure_message,
        "flags": list(res.flags),
        "evaluations": [
            {"search": e.search, "offload_kg": e.offload_kg, "m_res_kg": e.m_res_kg}
            for e in res.evaluations
        ],
        "sizing_at_x": None if at_x is None else s7a._sizing_items(at_x),
        "sizing_at_0": s7a._sizing_items(at_0),
        "structure_fixed_point_tol_kg": sim.STRUCTURE_FIXED_POINT_TOL_KG,
        "structure_fixed_point_max_iterations": sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS,
        "track_peak_scan_points": metrics.TRACK_PEAK_SCAN_POINTS,
        "budget": budget,
        **push,
        "push_budget_equals_budget": push["push_budget"] == budget,
        "push_context_is_solve_context": transform.push_context is ctx,
        "push_at_x": None if at_x is None else _push_at(transform, res.offload_kg, at_x),
        "git": _git_items(),
        "started_utc": started,
        "ended_utc": s7a._now(),
        "wall_s": time.perf_counter() - t0,
    }
    s7a._write_json(out, f"{chain}_solve.json", data)
    return data


def part_verify(out: Path, chain: str, target: Target) -> dict[str, Any]:
    """The chain's independent verification, as the pipeline's (``results_io._verified``
    on ``_structural_final``): the payload search, at the chain's budget, of the case's
    start offloaded by x* with dm at x* (sized by the chain's transform, its push flown with
    the chain's context) restated on each stage's dry mass (``config.offload_solved_run``).
    It must end ok with |P* - P_ref| <= the file's search_final_flag_rel x P_ref. Writes
    <chain>_verify.json, with whether its dm equals the solve's at x*, the search's budget
    and its push context's (``push_budget_equals_budget``) and whether the push context is
    tightened."""
    t0, started = time.perf_counter(), s7a._now()
    resolved, case, conv = _load(target)
    pad = s7a._load_pad(out, chain)
    solved = s7a._read_json(out, f"{chain}_solve.json")
    if solved["status"] != "ok":  # nothing to verify: recorded, so the report still runs
        data = {
            **_common(target, f"{chain}-verify", chain),
            "case": target.case,
            "status": "not_run",
            "reason": f"the {chain} solve ended {solved['status']}: nothing to verify",
            "offload_kg": None,
            "dm_kg": None,
            "dm_equals_solve": None,
            "p_ref_kg": pad["p_ref_kg"],
            "payload_kg": None,
            "delta_kg": None,
            "tolerance_kg": None,
            "passed": False,
            "budget": None,
            "push_budget": None,
            "push_budget_equals_budget": None,
            "push_context_tightened": None,
            "git": _git_items(),
            "started_utc": started,
            "ended_utc": s7a._now(),
            "wall_s": time.perf_counter() - t0,
        }
        s7a._write_json(out, f"{chain}_verify.json", data)
        print(f"the {chain} solve ended {solved['status']}: verification not run", flush=True)
        return data
    x_star_kg = float(solved["offload_kg"])
    start_ctx = s7a._context(case.start, s7a._conv_for(chain, conv))
    transform = _chain_transform(chain, resolved, case, pad, start_ctx)
    at_x = transform.sizing_at(x_star_kg)
    assert case.structure is not None
    final = offload_solved_run(
        case.start,
        case.config.mode,
        x_star_kg,
        case.config.name,
        case.start.name,
        structure_dm_kg=(at_x.dm_stage1_kg, at_x.dm_stage2_kg),
        provenance=case.structure.provenance,
    )
    ctx = s7a._context(final, s7a._conv_for(chain, conv))
    record = run_search(ctx)
    planar = resolved.baseline.run.planar
    assert planar is not None
    ver = verification_from_record(record, pad["p_ref_kg"], planar.checks.search_final_flag_rel)
    budget = s7a._budget_items(ctx)
    push = _push_items(transform, case, conv)
    data = {
        **_common(target, f"{chain}-verify", chain),
        "case": target.case,
        "offload_kg": x_star_kg,
        "dm_kg": at_x.total_kg,
        "dm_equals_solve": at_x.total_kg == solved["sizing_at_x"]["dm_kg"],
        "p_ref_kg": pad["p_ref_kg"],
        "status": ver.status,
        "payload_kg": ver.payload_kg,
        "delta_kg": ver.delta_kg,
        "tolerance_kg": ver.tolerance_kg,
        "passed": ver.passed,
        "search_flags": list(record.flags),
        "budget": budget,
        **push,
        "push_budget_equals_budget": push["push_budget"] == budget,
        "git": _git_items(),
        "started_utc": started,
        "ended_utc": s7a._now(),
        "wall_s": time.perf_counter() - t0,
    }
    s7a._write_json(out, f"{chain}_verify.json", data)
    return data


def _git_diff_quiet(base: str, head: str) -> bool | None:
    """Whether ``git diff --quiet base head -- CODE_PATHS`` exits 0 (None on a git
    error)."""
    proc = subprocess.run(
        ["git", "diff", "--quiet", base, head, "--", *CODE_PATHS],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    if proc.returncode in (0, 1):
        return proc.returncode == 0
    return None


def _same_code(parts: dict[str, dict[str, Any]], run_b_commit: str | None) -> dict[str, Any]:
    """ "From the same code as run B": each part's HEAD, read when its process loaded its
    modules and when it wrote its record, against run B's commit over CODE_PATHS (``git
    diff --quiet``), and each part's working tree clean over them at both readings (a part
    with no import-time reading fails)."""
    readings = {
        name: {"at_import": d["git"].get("at_import") or {}, "at_record": d["git"]}
        for name, d in parts.items()
    }
    heads = {
        name: {when: r.get("head") for when, r in pair.items()} for name, pair in readings.items()
    }
    clean = {
        name: {when: r.get("code_paths_clean") is True for when, r in pair.items()}
        for name, pair in readings.items()
    }
    all_clean = all(v for pair in clean.values() for v in pair.values())
    if run_b_commit is None:
        return {"run_b_commit": None, "heads": heads, "code_paths_clean": clean, "passed": False}
    seen = {h for pair in heads.values() for h in pair.values()}
    diff = {h: _git_diff_quiet(run_b_commit, h) for h in sorted(seen - {None})}
    return {
        "run_b_commit": run_b_commit,
        "code_paths": list(CODE_PATHS),
        "heads": heads,
        "diff_quiet": diff,
        "code_paths_clean": clean,
        "passed": None not in seen and all(v is True for v in diff.values()) and all_clean,
    }


def _run_b_items(run_b: Path, case: str) -> dict[str, Any]:
    """Run B's numbers the check is compared with (read only): its git, P_ref and the
    case's x*, dm at x* and verification P*."""
    metrics = json.loads((run_b / "metrics.json").read_text(encoding="utf-8"))
    offload = metrics["offload"]
    rec = next(c for c in offload["cases"] if c["name"] == case)
    try:
        shown = run_b.resolve().relative_to(REPO).as_posix()
    except ValueError:
        shown = f"(outside the repository) {run_b.name}"
    return {
        "dir": shown,
        "git": metrics.get("git"),
        "p_ref_kg": offload["reference_payload_kg"],
        "status": rec["status"],
        "offload_kg": rec["offload_kg"],
        "dm_kg": rec.get("structure_dm_kg"),
        "verification_payload_kg": (rec.get("verification") or {}).get("payload_kg"),
    }


def _chain_items(
    chain: str, pad: dict[str, Any], sol: dict[str, Any], ver: dict[str, Any]
) -> dict[str, Any]:
    """One chain's numbers for the report, with its verification (status, P*, P* - P_ref,
    tolerance, passed; the x* and dm it flew) and its run-as-registered items: the chain's
    own pad, its search ended ok and flown at the chain's budget (the pad's budget equal
    to the solve's); the solve's and the verification's pushes flown with the chain's
    context (tightened exactly in the tightened chain, each push context's budget equal to
    its search's); and the verification flown at the solve's x* with the solve's dm at x*
    (``verification_as_solved``)."""
    push = sol.get("push_at_x") or {}
    tightened = chain == TIGHTENED
    pad_budget = pad.get("budget")
    x_kg = _number(sol["offload_kg"])
    as_solved = (
        x_kg is not None
        and _number(ver.get("offload_kg")) == x_kg
        and ver.get("dm_equals_solve") is True
    )
    solve_push_ok = (
        sol.get("push_context_tightened") is tightened
        and sol.get("push_budget") is not None
        and sol.get("push_budget") == sol.get("budget")
    )
    verify_push_ok = (
        ver.get("push_context_tightened") is tightened
        and ver.get("push_budget") is not None
        and ver.get("push_budget") == ver.get("budget")
    )
    return {
        "p_ref_kg": pad["p_ref_kg"],
        "pad_search_status": pad["search"]["status"],
        "pad_search_ok": pad["search"]["status"] == PAD_SEARCH_OK,
        "pad_budget": pad_budget,
        "pad_budget_equals_solve": pad_budget is not None and pad_budget == sol.get("budget"),
        "offload_kg": sol["offload_kg"],
        "dm_kg": (sol.get("sizing_at_x") or {}).get("dm_kg"),
        "status": sol["status"],
        "n_evaluations": sol["n_evaluations"],
        "solve_flags": sol["flags"],
        "verification_status": ver["status"],
        "verification_payload_kg": ver["payload_kg"],
        "verification_delta_kg": ver["delta_kg"],
        "verification_tolerance_kg": ver["tolerance_kg"],
        "verification_passed": ver["passed"],
        "verification_offload_kg": ver.get("offload_kg"),
        "verification_dm_kg": ver.get("dm_kg"),
        "verification_dm_equals_solve": ver.get("dm_equals_solve"),
        "verification_as_solved": as_solved,
        "budget": sol.get("budget"),
        "push_budget": sol.get("push_budget"),
        "push_context_tightened": sol.get("push_context_tightened"),
        "push_context_is_solve_context": sol.get("push_context_is_solve_context"),
        "verify_budget": ver.get("budget"),
        "verify_push_budget": ver.get("push_budget"),
        "verify_push_context_tightened": ver.get("push_context_tightened"),
        "solve_push_as_registered": solve_push_ok,
        "verify_push_as_registered": verify_push_ok,
        "push_at_x_events": [e["name"] for e in push.get("events") or []],
        "push_at_x_power_limit_logged": push.get("power_limit_logged"),
        "push_at_x_release_state": push.get("release_state"),
    }


def _scripts(parts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Section 1's "a committed script": each part's record of SCRIPT_PATHS (``_git_items``)
    and whether, in every part, each script, as its process loaded it and as it was when
    the part wrote its record, equals its blob at that part's HEAD and has the same sha256
    as in every other part (both readings)."""
    per_part = {name: (d.get("git") or {}).get("scripts") for name, d in parts.items()}
    sha256: dict[str, list[str | None]] = {}
    committed = True
    for relpath in SCRIPT_PATHS:
        records = [(rec or {}).get(relpath) or {} for rec in per_part.values()]
        seen = {r.get(k) for r in records for k in ("sha256_at_import", "sha256")}
        sha256[relpath] = sorted(seen, key=str)
        committed &= all(r.get("as_committed") is True for r in records)
    same = all(len(v) == 1 and v[0] is not None for v in sha256.values())
    return {
        "paths": list(SCRIPT_PATHS),
        "per_part": per_part,
        "sha256": sha256,
        "as_committed_in_every_part": committed,
        "same_in_every_part": same,
        "passed": committed and same,
    }


def _verification_words(chain: dict[str, Any]) -> str:
    """One chain's verification as the verdict line prints it: its status, P* - P_ref [kg]
    against its tolerance [kg] and whether it passed."""
    delta_kg, tol_kg = (
        _number(chain["verification_delta_kg"]),
        _number(chain["verification_tolerance_kg"]),
    )
    if delta_kg is None or tol_kg is None:
        return f"{chain['verification_status']}, passed {chain['verification_passed']}"
    return (
        f"{chain['verification_status']}, P* - P_ref {delta_kg:+.6f} kg against {tol_kg:.4f} kg, "
        f"passed {chain['verification_passed']}"
    )


def _verdict_lines(data: dict[str, Any]) -> list[str]:
    """The report's three verdicts, as printed after its JSON."""
    rule, ver, how = data["registered_rule"], data["verifications"], data["run_as_registered"]
    items = ", ".join(f"{k} {v}" for k, v in how.items() if k != "passed")
    return [
        f"the registered rule (section 1's pass rule): {'PASS' if rule['passed'] else 'FAIL'} "
        f"(both solves ok {rule['both_solves_ok']}, tightened within {REL_TOL:.1%} (relative) "
        f"{rule['tightened_within_rel_tol']}, shipped equal to run B within {RUN_B_MATCH_KG} kg "
        f"{rule['shipped_equals_run_b']})",
        "x* confirmed (section 1: each chain's x* checked by an independent payload search, "
        "ok with |P* - P_ref| <= checks.search_final_flag_rel P_ref): "
        + ("yes" if ver["passed"] else "NO, x* not confirmed")
        + f" (shipped: {_verification_words(data['shipped'])}; tightened: "
        f"{_verification_words(data['tightened'])})",
        f"run as registered (section 1's method): {'yes' if how['passed'] else 'NO'} ({items})",
        f"passed: {data['passed']}"
        + (" (a dry run: not the registered check)" if data["dry_run"] else ""),
    ]


def part_report(out: Path, run_b: Path | None, target: Target) -> dict[str, Any]:
    """Read every part's JSON and give the check's three verdicts: the registered rule
    (both solves ok, the tightened x* within REL_TOL of the shipped one and, with run_b,
    the shipped x* within RUN_B_MATCH_KG of run B's; without run_b it cannot pass), x*
    confirmed (both verifications passed) and run as registered (each verification flew
    its solve's x* and dm, both pads' searches ended ok, each pad flown at its chain's
    budget, every push flown with its chain's context, the same code as run B, the scripts
    as committed). ``passed`` is their conjunction. Writes report.json (with
    ``_not_tightened`` as ``not_tightened``) and prints it, then the three verdicts."""
    resolved, case, conv = _load(target)
    parts = {
        name: s7a._read_json(out, f"{name.replace('-', '_')}.json")
        for name in PARTS
        if name != "report"
    }
    s_pad, t_pad = parts["shipped-pad"], parts["tightened-pad"]
    s_sol, t_sol = parts["shipped-solve"], parts["tightened-solve"]
    s_ver, t_ver = parts["shipped-verify"], parts["tightened-verify"]
    statuses_ok = s_sol["status"] == t_sol["status"] == "ok"
    x_s_kg, x_t_kg = _number(s_sol["offload_kg"]), _number(t_sol["offload_kg"])
    diff_kg: float | None = None
    rel: float | None = None
    if statuses_ok and x_s_kg is not None and x_t_kg is not None and x_s_kg != 0.0:
        diff_kg = x_t_kg - x_s_kg
        rel = diff_kg / x_s_kg
    dm_s_kg = (s_sol.get("sizing_at_x") or {}).get("dm_kg")
    dm_t_kg = (t_sol.get("sizing_at_x") or {}).get("dm_kg")
    shipped = _chain_items(SHIPPED, s_pad, s_sol, s_ver)
    tight = _chain_items(TIGHTENED, t_pad, t_sol, t_ver)
    data: dict[str, Any] = {
        "check": "SP7 S7b: the linear-motor convergence check (pre-registration part 2, "
        "section 1); a check, never a finding",
        **target.items(),
        "convergence": conv.model_dump(),
        "rel_tol": REL_TOL,
        "rel_tol_file": conv.rel_tol,
        "run_b_tol_kg": RUN_B_MATCH_KG,
        "structure_fixed_point_tol_kg": sim.STRUCTURE_FIXED_POINT_TOL_KG,
        "structure_fixed_point_max_iterations": sim.STRUCTURE_FIXED_POINT_MAX_ITERATIONS,
        "track_peak_scan_points": metrics.TRACK_PEAK_SCAN_POINTS,
        "not_tightened_scope": NOT_TIGHTENED_SCOPE,
        "not_tightened": _not_tightened(resolved, case),
        "shipped": shipped,
        "tightened": tight,
        "x_star_difference_kg": diff_kg,
        "x_star_relative_difference": rel,
        "p_ref_difference_kg": t_pad["p_ref_kg"] - s_pad["p_ref_kg"],
        "dm_difference_kg": (
            dm_t_kg - dm_s_kg if dm_s_kg is not None and dm_t_kg is not None else None
        ),
        "wall_s": {name: d["wall_s"] for name, d in parts.items()},
    }
    if run_b is not None:
        b = _run_b_items(run_b, target.case)
        data["run_b"] = b

        def minus(mine: Any, theirs: Any) -> float | None:
            """mine - theirs as numbers, None when either is not a finite number."""
            a, c = _number(mine), _number(theirs)
            return None if a is None or c is None else a - c

        data["shipped_minus_run_b"] = {
            "p_ref_kg": minus(s_pad["p_ref_kg"], b["p_ref_kg"]),
            "offload_kg": minus(x_s_kg, b["offload_kg"]),
            "dm_kg": minus(dm_s_kg, b["dm_kg"]),
            "verification_payload_kg": minus(s_ver["payload_kg"], b["verification_payload_kg"]),
        }
        d_b_kg = data["shipped_minus_run_b"]["offload_kg"]
        shipped_equals_run_b = (
            s_sol["status"] == "ok" and d_b_kg is not None and abs(d_b_kg) <= RUN_B_MATCH_KG
        )
        commit = (b.get("git") or {}).get("hash")
    else:
        data["run_b"] = None
        shipped_equals_run_b = None
        commit = None
    tightened_within = rel is not None and abs(rel) < REL_TOL
    data["registered_rule"] = {
        "both_solves_ok": statuses_ok,
        "tightened_within_rel_tol": tightened_within,
        "shipped_equals_run_b": shipped_equals_run_b,
        "passed": statuses_ok and tightened_within and shipped_equals_run_b is True,
    }
    data["same_code"] = _same_code(parts, commit)
    data["scripts"] = _scripts({**parts, "report": {"git": _git_items()}})
    confirmed = {
        "shipped_passed": s_ver["passed"] is True,
        "tightened_passed": t_ver["passed"] is True,
    }
    data["verifications"] = {**confirmed, "passed": all(confirmed.values())}
    how = {
        "verification_x_and_dm_as_solved": (
            shipped["verification_as_solved"] and tight["verification_as_solved"]
        ),
        "pad_searches_ok": shipped["pad_search_ok"] and tight["pad_search_ok"],
        "pad_budget_equals_solve": (
            shipped["pad_budget_equals_solve"] and tight["pad_budget_equals_solve"]
        ),
        "push_contexts_as_registered": all(
            c[k]
            for c in (shipped, tight)
            for k in ("solve_push_as_registered", "verify_push_as_registered")
        ),
        "same_code": bool(data["same_code"]["passed"]),
        "scripts_as_committed": bool(data["scripts"]["passed"]),
    }
    data["run_as_registered"] = {**how, "passed": all(how.values())}
    data["passed"] = bool(
        data["registered_rule"]["passed"]
        and data["verifications"]["passed"]
        and data["run_as_registered"]["passed"]
    )
    s7a._write_json(out, "report.json", data)
    print(json.dumps(s7a._plain(data), indent=2))
    print("\n".join(_verdict_lines(data)))
    return data


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and run one part, or all of them in order."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--out", type=Path, required=True, help="output directory (outside the repo)"
    )
    parser.add_argument("--part", choices=[*PARTS, "all"], required=True)
    parser.add_argument("--run-b", type=Path, default=None, help="run B's results directory")
    parser.add_argument(
        "--experiment", type=Path, default=EXPERIMENT, help="a dry run's experiment file"
    )
    parser.add_argument("--case", default=CASE, help="a dry run's structural case")
    args = parser.parse_args(argv)
    out = s7a._check_out(args.out)
    target = Target(args.experiment.resolve(), args.case)
    _check_target(out, target)
    if not target.registered:
        shown = target.items()["experiment"]
        print(f"DRY RUN: {shown} / {target.case} is not the registered check", flush=True)
    run_b = None if args.run_b is None else args.run_b.resolve()
    for part in PARTS if args.part == "all" else (args.part,):
        t0 = time.perf_counter()
        print(f"[{s7a._now()}] part {part} started", flush=True)
        if part.endswith("-pad"):
            part_pad(out, part.split("-")[0], target)
        elif part.endswith("-solve"):
            part_solve(out, part.split("-")[0], target)
        elif part.endswith("-verify"):
            part_verify(out, part.split("-")[0], target)
        else:
            part_report(out, run_b, target)
        print(f"[{s7a._now()}] part {part} ended ({time.perf_counter() - t0:.1f} s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
