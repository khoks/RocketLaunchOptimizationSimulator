"""SP7 step S7a: the convergence check of the structural headline (exit criterion 6).

This script runs the check registered in docs/phases/inputs/2026-10-15-SP7-preregistration.md,
section 1 ("The convergence check"; it blocks the headline per that note's section 9). It
is exit criterion 6 of docs/phases/inputs/2026-10-08-SP7-design.md (section 6): "Tightening
the search tolerances 10x moves the central structural x* ... by < 0.1%; doubling the
stations moves dm by < 0.1 kg". Its numbers are a check quoted in the findings note's
convergence line, never a finding.

What it does:

1. Solve. Case silo_cold_s1_st (the central structural stage-1 case) of
   experiments/silo_structure_2d.yaml, read from the committed file through
   ``cli.load_experiment``. Only three of the file's runs are built: its pad baseline, its
   variant silo_cold (the solve's start: resolved, not flown on its own) and that case. The
   case is solved in two chains:

   - the shipped budget;
   - its tightening by the file's ``checks.convergence`` (``SearchContext.tightened``:
     every search and final tolerance divided by tighten_factor 10, the max-step caps
     multiplied by max_step_factor 0.5).

   Each chain flies its own pad. That pad's P* is the chain's P_ref, and its recorded
   flight is the chain's structural envelope. The structure's fixed-point tolerance
   (``sim.STRUCTURE_FIXED_POINT_TOL_KG``, 1e-6 kg) is unchanged. Each chain's x* is checked
   by an independent payload search, at that chain's budget, of the offloaded vehicle
   carrying dm. Each pad flight, solve and verification mirrors what ``launchsim run``
   does (``sim.run_planar`` and ``sim.solve_resolved_offload``). The only difference is
   the tightened context in the second chain.
   Pass: |x*_tightened - x*_shipped| < rel_tol x x*_shipped, with rel_tol 1e-3 (0.1%).
   The shipped x* must also equal run A's within 0.002 kg; ``report`` compares them when
   given --run-a.

2. Stations (sizing only, no flight). dm of the same case at the shipped x*, sized on the
   shipped pad's envelope at the shipped P_ref, with stations_per_barrel 200 (the committed
   structure file) and 400 (a scratch copy of that file under --out, with only that one
   value changed; nothing is written under configs/).
   Pass: |dm_400 - dm_200| < 0.1 kg.

Output. Everything goes under --out, as JSON per part plus pickled pad time series and
events, which the later parts read. --out may not lie inside the repository, so nothing
is ever written under results/, configs/ or elsewhere in the tree. results/ is read only
by ``report`` (run A's metrics.json, when --run-a is given). No plots.

Usage, from the repository root. The parts run in this order, each in its own process
(each under ten minutes on the development machine); ``--part all`` runs every part in
one process:

    uv run python docs/findings/scripts/sp7_convergence.py --out DIR --part shipped-pad
    ... --part shipped-solve, shipped-verify, stations, tightened-pad, tightened-solve,
    tightened-verify, then
    uv run python docs/findings/scripts/sp7_convergence.py --out DIR --part report \
        --run-a results/silo_structure_2d/<timestamp>
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from launchsim import cli, sim, structure
from launchsim.compare import reference_payload_kg, trajectory_key
from launchsim.config import (
    ConvergenceConfig,
    ResolvedExperiment,
    ResolvedOffloadCase,
    ResolvedRun,
    offload_solved_run,
    resolve_experiment,
)
from launchsim.offload import planar_problem_factory, solve_offload, verification_from_record
from launchsim.phases.planar import PLANAR_MODEL
from launchsim.search import SearchContext, SearchRecord, run_search
from launchsim.vehicle import with_payload

REPO = Path(__file__).resolve().parents[3]
"""The repository root (this file is docs/findings/scripts/sp7_convergence.py)."""
EXPERIMENT = REPO / "experiments" / "silo_structure_2d.yaml"
"""File A of the pre-registration, read from the committed file."""
STRUCTURE_NAME = "configs/structures/generic_f9_class_2d.yaml"
"""The structure file file A's structure block names (frozen at S2's commit 45e39d4)."""
CASE = "silo_cold_s1_st"
"""The central structural stage-1 case: the headline."""
VARIANT = "silo_cold"
"""The case's variant (its start)."""
SHIPPED, TIGHTENED = "shipped", "tightened"
"""The two chains."""
STATIONS_COARSE, STATIONS_FINE = 200, 400
"""stations_per_barrel in the committed file and in the scratch copy."""
STATIONS_KEY_TEXT = "stations_per_barrel: {{value: {n},"
"""The exact text of the stations line's start in the structure file, by count n."""
RUN_A_MATCH_KG = 0.002
"""The registered reproduction tolerance of the shipped x* against run A's [kg]."""
STATIONS_PASS_KG = 0.1
"""Criterion 6's second part: dm moves by less than this with the stations doubled [kg]."""
PARTS = (
    "shipped-pad",
    "shipped-solve",
    "shipped-verify",
    "stations",
    "tightened-pad",
    "tightened-solve",
    "tightened-verify",
    "report",
)


# ------------------------------------------------------------------------------- helpers


def _now() -> str:
    """The current UTC time, ISO 8601 to the second."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _plain(value: Any) -> Any:
    """value with every non-finite float replaced by None (strict JSON)."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    return value


def _write_json(out: Path, name: str, data: dict[str, Any]) -> Path:
    """Write data as indented strict JSON to out/name (UTF-8, LF); floats keep every bit
    (``repr``)."""
    path = out / name
    text = json.dumps(_plain(data), indent=2, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _read_json(out: Path, name: str) -> dict[str, Any]:
    """The JSON a previous part wrote to out/name."""
    path = out / name
    if not path.is_file():
        raise SystemExit(f"error: {path} not found: run the part that writes it first")
    return json.loads(path.read_text(encoding="utf-8"))


def _git() -> dict[str, Any]:
    """HEAD and whether the code paths are clean in the working tree (the run's code)."""

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)

    head = run("rev-parse", "HEAD").stdout.strip()
    paths = ["src", "configs", "experiments", "pyproject.toml", "uv.lock", "tests"]
    dirty = run("status", "--porcelain", "--", *paths).stdout.strip()
    return {"head": head, "code_paths_clean": dirty == "", "code_paths": paths}


def _check_out(out: Path) -> Path:
    """The resolved output directory, created; refused inside the repository."""
    resolved = out.resolve()
    if resolved == REPO or REPO in resolved.parents:
        raise SystemExit(f"error: --out {resolved} lies inside the repository {REPO}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _load() -> tuple[ResolvedExperiment, ResolvedOffloadCase, ConvergenceConfig]:
    """File A resolved as ``launchsim run`` resolves it (``cli.load_experiment``), its
    headline case and the convergence block of its shared checks."""
    resolved = cli.load_experiment(EXPERIMENT)
    if resolved.offload is None:
        raise SystemExit(f"error: {EXPERIMENT} has no offload block")
    case = next(c for c in resolved.offload.cases if c.name == CASE)
    if case.structure is None or case.config.of != VARIANT:
        raise SystemExit(f"error: {CASE} is not a structural case of {VARIANT}")
    planar = resolved.baseline.run.planar
    assert planar is not None
    return resolved, case, planar.checks.convergence


def _context(run: ResolvedRun, conv: ConvergenceConfig | None) -> SearchContext:
    """The SearchContext of a resolved run, built as ``sim.run_planar`` and
    ``sim.offload_problem_factory`` build it (``planar_setup``, ``search_context``),
    tightened by conv when given (``SearchContext.tightened``)."""
    vehicle = run.to_vehicle()
    ctx = sim.search_context(sim.planar_setup(run.run, vehicle), vehicle, run.run.end)
    return ctx if conv is None else ctx.tightened(conv)


def _budget_items(ctx: SearchContext) -> dict[str, Any]:
    """The tolerances and caps a chain flew, for the record."""
    b, s = ctx.budget, ctx.settings
    return {
        "budget_id": b.budget_id,
        "search_rtol": b.search_rtol,
        "final_rtol": b.final_rtol,
        "final_atol_scale": b.final_atol_scale,
        "payload_xtol_kg": b.payload_xtol_kg,
        "final_payload_xtol_kg": b.final_payload_xtol_kg,
        "gamma_xatol_rad": b.gamma_xatol_rad,
        "planar_max_step_s": s.planar_max_step_s,
        "push_steps": s.push_steps,
        "ramp_steps": s.ramp_steps,
        "lag_steps_per_tau": s.lag_steps_per_tau,
    }


def _conv_for(chain: str, conv: ConvergenceConfig) -> ConvergenceConfig | None:
    """conv for the tightened chain, None for the shipped one."""
    return conv if chain == TIGHTENED else None


def _pad_cases(
    resolved: ResolvedExperiment, pad: dict[str, Any], layout: Any
) -> structure.PadLoadSet:
    """The envelope's load cases of a chain's pad flight, as ``sim.offload_pad_load_set``
    builds them: ``sim.structure_pad_cases`` of the flight (it reads the Result's model,
    time series and events only; here a stand-in holding the pickled ones) on the pad's
    vehicle at the chain's P_ref, labelled with the pad's name."""
    baseline = resolved.baseline
    flight = SimpleNamespace(model=PLANAR_MODEL, timeseries=pad["timeseries"], events=pad["events"])
    vehicle = with_payload(baseline.to_vehicle(), pad["p_ref_kg"])
    return structure.pad_load_set(
        sim.structure_pad_cases(flight, vehicle, layout, label=baseline.name)  # type: ignore[arg-type]
    )


def _transform(
    resolved: ResolvedExperiment, case: ResolvedOffloadCase, pad: dict[str, Any]
) -> sim.StructureTransform:
    """The case's StructureTransform against a chain's pad, as
    ``sim.offload_structure_transform`` builds it (the geometry from the variant at its full
    loads, the envelope from that pad's flight, the push of the case's start)."""
    settings = case.structure
    assert settings is not None
    layout = settings.file.config.stack_layout()
    return sim.build_structure_transform(
        settings,
        case.variant.to_vehicle(),
        case.start,
        case.config.mode,
        _pad_cases(resolved, pad, layout),
        pad["p_ref_kg"],
        envelope_pad=resolved.baseline.name,
        envelope_pad_key=trajectory_key(resolved.baseline),
    )


def _load_pad(out: Path, chain: str) -> dict[str, Any]:
    """The pickled pad flight of a chain (this script's own file under --out)."""
    path = out / f"{chain}_pad.pkl"
    if not path.is_file():
        raise SystemExit(f"error: {path} not found: run --part {chain}-pad first")
    with path.open("rb") as fh:
        return pickle.load(fh)


def _sizing_items(s: sim.StructureSizing) -> dict[str, Any]:
    """A sizing as plain data."""
    return {
        "dm_stage1_kg": s.dm_stage1_kg,
        "dm_stage2_kg": s.dm_stage2_kg,
        "dm_kg": s.total_kg,
        "iterations": s.iterations,
        "capped": s.capped,
        "contraction": s.contraction,
        "steps_kg": list(s.steps),
        "factor": s.factor,
    }


def _search_items(record: SearchRecord) -> dict[str, Any]:
    """A payload search's status, P* and flags."""
    return {"status": record.status, "payload_kg": record.payload_kg, "flags": list(record.flags)}


# --------------------------------------------------------------------------------- parts


def part_pad(out: Path, chain: str) -> dict[str, Any]:
    """Fly a chain's pad baseline as ``sim.run_planar`` flies a searched run (its payload
    search, then the recorded run's Result), at that chain's budget. P_ref is its P*
    (``compare.reference_payload_kg``). Pickles the time series and events (the
    envelope's input) with P_ref, and writes <chain>_pad.json."""
    t0, started = time.perf_counter(), _now()
    resolved, _, conv = _load()
    baseline = resolved.baseline
    vehicle = baseline.to_vehicle()
    setup = sim.planar_setup(baseline.run, vehicle)
    ctx = _context(baseline, _conv_for(chain, conv))
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
    p_ref = reference_payload_kg(sim.RunResult(baseline.name, baseline, result))
    with (out / f"{chain}_pad.pkl").open("wb") as fh:
        pickle.dump(
            {"timeseries": result.timeseries, "events": result.events, "p_ref_kg": p_ref},
            fh,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    data = {
        "part": f"{chain}-pad",
        "chain": chain,
        "run": baseline.name,
        "status": result.status,
        "search": _search_items(record),
        "p_ref_kg": p_ref,
        "run_checks_failed": result.metrics.get("run_checks_failed"),
        "budget": _budget_items(ctx),
        "git": _git(),
        "started_utc": started,
        "ended_utc": _now(),
        "wall_s": time.perf_counter() - t0,
    }
    _write_json(out, f"{chain}_pad.json", data)
    return data


def part_solve(out: Path, chain: str) -> dict[str, Any]:
    """Solve the case's stage-1 offload at the chain's P_ref with its transform, as
    ``sim.solve_resolved_offload`` does (no built-in verification), at the chain's
    budget. Writes <chain>_solve.json: x*, the solve's figures, flags and logged
    evaluations, the sizing at x* and at x = 0."""
    t0, started = time.perf_counter(), _now()
    resolved, case, conv = _load()
    pad = _load_pad(out, chain)
    transform = _transform(resolved, case, pad)
    ctx = _context(case.start, _conv_for(chain, conv))
    res = solve_offload(
        planar_problem_factory(ctx),
        case.start.to_vehicle(),
        case.config.mode,
        pad["p_ref_kg"],
        verify=False,
        transform=transform,
    )
    at_x = transform.sizing_at(res.offload_kg) if math.isfinite(res.offload_kg) else None
    data = {
        "part": f"{chain}-solve",
        "chain": chain,
        "case": CASE,
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
        "sizing_at_x": None if at_x is None else _sizing_items(at_x),
        "structure_fixed_point_tol_kg": sim.STRUCTURE_FIXED_POINT_TOL_KG,
        "budget": _budget_items(ctx),
        "git": _git(),
        "started_utc": started,
        "ended_utc": _now(),
        "wall_s": time.perf_counter() - t0,
    }
    _write_json(out, f"{chain}_solve.json", data)
    return data


def part_verify(out: Path, chain: str) -> dict[str, Any]:
    """The chain's independent verification, as the pipeline's (``results_io._verified``
    on ``_structural_final``): the payload search, at the chain's budget, of the case's
    start offloaded by x* with dm at x* restated on each stage's dry mass
    (``config.offload_solved_run``). It must end ok with |P* - P_ref| <= the file's
    search_final_flag_rel x P_ref. Writes <chain>_verify.json."""
    t0, started = time.perf_counter(), _now()
    resolved, case, conv = _load()
    pad = _load_pad(out, chain)
    solved = _read_json(out, f"{chain}_solve.json")
    if solved["status"] != "ok":
        raise SystemExit(f"error: the {chain} solve ended {solved['status']}: nothing to verify")
    x_star = float(solved["offload_kg"])
    transform = _transform(resolved, case, pad)
    at_x = transform.sizing_at(x_star)
    assert case.structure is not None
    final = offload_solved_run(
        case.start,
        case.config.mode,
        x_star,
        case.config.name,
        case.start.name,
        structure_dm_kg=(at_x.dm_stage1_kg, at_x.dm_stage2_kg),
        provenance=case.structure.provenance,
    )
    ctx = _context(final, _conv_for(chain, conv))
    record = run_search(ctx)
    planar = resolved.baseline.run.planar
    assert planar is not None
    ver = verification_from_record(record, pad["p_ref_kg"], planar.checks.search_final_flag_rel)
    data = {
        "part": f"{chain}-verify",
        "chain": chain,
        "case": CASE,
        "offload_kg": x_star,
        "dm_kg": at_x.total_kg,
        "p_ref_kg": pad["p_ref_kg"],
        "status": ver.status,
        "payload_kg": ver.payload_kg,
        "delta_kg": ver.delta_kg,
        "tolerance_kg": ver.tolerance_kg,
        "passed": ver.passed,
        "search_flags": list(record.flags),
        "budget": _budget_items(ctx),
        "git": _git(),
        "started_utc": started,
        "ended_utc": _now(),
        "wall_s": time.perf_counter() - t0,
    }
    _write_json(out, f"{chain}_verify.json", data)
    return data


def _fine_copy(out: Path) -> Path:
    """Write the scratch copy of the committed structure file with stations_per_barrel
    400, under out, and return its path. Exactly one line changes; the copy keeps the
    file's bytes otherwise."""
    text = (REPO / STRUCTURE_NAME).read_bytes().decode("utf-8")
    coarse = STATIONS_KEY_TEXT.format(n=STATIONS_COARSE)
    if text.count(coarse) != 1:
        raise SystemExit(f"error: {STRUCTURE_NAME} does not hold {coarse!r} exactly once")
    fine = text.replace(coarse, STATIONS_KEY_TEXT.format(n=STATIONS_FINE))
    changed = [(a, b) for a, b in zip(text.splitlines(), fine.splitlines(), strict=True) if a != b]
    assert len(changed) == 1
    path = out / f"structure_stations{STATIONS_FINE}.yaml"
    path.write_bytes(fine.encode("utf-8"))
    return path


def _resolve_with(structure_file: Any) -> ResolvedExperiment:
    """File A resolved as ``cli.load_experiment`` resolves it, except that its structure
    block's file is the given StructureFile (no preflight: nothing is flown from it)."""
    exp_dict = cli.load_yaml(EXPERIMENT)
    vehicle_dict = cli.load_yaml(cli.resolve_vehicle_path(EXPERIMENT, exp_dict["vehicle"]))

    def load_vehicle(path: str) -> dict[str, Any]:
        return cli.load_yaml(cli.resolve_vehicle_path(EXPERIMENT, path))

    def load_structure(name: str) -> Any:
        if name != STRUCTURE_NAME:
            raise SystemExit(f"error: file A names {name!r}, not {STRUCTURE_NAME!r}")
        return structure_file

    return resolve_experiment(exp_dict, vehicle_dict, load_vehicle, load_structure=load_structure)


def part_stations(out: Path) -> dict[str, Any]:
    """Sizing only: dm of the case at the shipped x* on the shipped pad's envelope at the
    shipped P_ref, with the committed file's 200 stations per barrel and with the scratch
    copy's 400. Writes stations.json."""
    t0, started = time.perf_counter(), _now()
    resolved, case, _ = _load()
    pad = _load_pad(out, SHIPPED)
    solved = _read_json(out, f"{SHIPPED}_solve.json")
    x_star = float(solved["offload_kg"])
    fine_path = _fine_copy(out)
    fine_file = cli.read_structure_file(fine_path, fine_path.as_posix())
    resolved_fine = _resolve_with(fine_file)
    assert resolved_fine.offload is not None
    case_fine = next(c for c in resolved_fine.offload.cases if c.name == CASE)
    assert case.structure is not None and case_fine.structure is not None
    same_coefficients = repr(case.structure.coefficients) == repr(case_fine.structure.coefficients)
    rows = {}
    for n, rv, cs in ((STATIONS_COARSE, resolved, case), (STATIONS_FINE, resolved_fine, case_fine)):
        assert cs.structure is not None
        layout = cs.structure.file.config.stack_layout()
        if layout.stations_per_barrel != n:
            raise SystemExit(f"error: layout has {layout.stations_per_barrel} stations, not {n}")
        transform = _transform(rv, cs, pad)
        sizing = transform.sizing_at(x_star)
        geo = transform.geometry
        rows[str(n)] = {
            "structure_file": cs.structure.file.path,
            "structure_file_sha256": cs.structure.file.sha256,
            "stations_per_barrel": n,
            "lox_barrel_stations_stage1": len(geo.stage1.lox_barrel.z_m),
            "rp1_barrel_stations_stage1": len(geo.stage1.rp1_barrel.z_m),
            "sizing_at_x": _sizing_items(sizing),
            "elements_kg": {
                f"{e.stage}.{e.element}": sizing.factor * e.kg for e in sizing.increment.elements
            },
        }
    dm_c = rows[str(STATIONS_COARSE)]["sizing_at_x"]["dm_kg"]
    dm_f = rows[str(STATIONS_FINE)]["sizing_at_x"]["dm_kg"]
    data = {
        "part": "stations",
        "case": CASE,
        "offload_kg": x_star,
        "p_ref_kg": pad["p_ref_kg"],
        "same_coefficients": same_coefficients,
        "rows": rows,
        "dm_move_kg": dm_f - dm_c,
        "pass_below_kg": STATIONS_PASS_KG,
        "passed": abs(dm_f - dm_c) < STATIONS_PASS_KG,
        "git": _git(),
        "started_utc": started,
        "ended_utc": _now(),
        "wall_s": time.perf_counter() - t0,
    }
    _write_json(out, "stations.json", data)
    return data


def _run_a_items(run_a: Path) -> dict[str, Any]:
    """Run A's numbers this check is compared with (read only): its P_ref and the case's
    x*, dm at x* and verification P*."""
    metrics = json.loads((run_a / "metrics.json").read_text(encoding="utf-8"))
    offload = metrics["offload"]
    rec = next(c for c in offload["cases"] if c["name"] == CASE)
    return {
        "dir": run_a.as_posix(),
        "git": metrics.get("git"),
        "p_ref_kg": offload["reference_payload_kg"],
        "offload_kg": rec["offload_kg"],
        "dm_kg": rec.get("structure_dm_kg"),
        "verification_payload_kg": (rec.get("verification") or {}).get("payload_kg"),
    }


def part_report(out: Path, run_a: Path | None) -> dict[str, Any]:
    """Read every part's JSON and evaluate the registered checks: the tightened x*
    against the shipped one (rel_tol), the stations move, and, with run_a, the shipped
    chain against run A (0.002 kg). Writes report.json and prints it."""
    _, _, conv = _load()
    s_pad, t_pad = _read_json(out, "shipped_pad.json"), _read_json(out, "tightened_pad.json")
    s_sol, t_sol = _read_json(out, "shipped_solve.json"), _read_json(out, "tightened_solve.json")
    s_ver = _read_json(out, "shipped_verify.json")
    t_ver = _read_json(out, "tightened_verify.json")
    stations = _read_json(out, "stations.json")
    x_s, x_t = float(s_sol["offload_kg"]), float(t_sol["offload_kg"])
    rel = (x_t - x_s) / x_s
    data: dict[str, Any] = {
        "case": CASE,
        "convergence": conv.model_dump(),
        "shipped": {
            "p_ref_kg": s_pad["p_ref_kg"],
            "offload_kg": x_s,
            "dm_kg": s_sol["sizing_at_x"]["dm_kg"],
            "status": s_sol["status"],
            "verification_payload_kg": s_ver["payload_kg"],
            "verification_delta_kg": s_ver["delta_kg"],
            "verification_passed": s_ver["passed"],
        },
        "tightened": {
            "p_ref_kg": t_pad["p_ref_kg"],
            "offload_kg": x_t,
            "dm_kg": t_sol["sizing_at_x"]["dm_kg"],
            "status": t_sol["status"],
            "verification_payload_kg": t_ver["payload_kg"],
            "verification_delta_kg": t_ver["delta_kg"],
            "verification_passed": t_ver["passed"],
        },
        "x_star_difference_kg": x_t - x_s,
        "x_star_relative_difference": rel,
        "p_ref_difference_kg": t_pad["p_ref_kg"] - s_pad["p_ref_kg"],
        "tightened_passed": abs(rel) < conv.rel_tol,
        "stations": {
            "dm_200_kg": stations["rows"][str(STATIONS_COARSE)]["sizing_at_x"]["dm_kg"],
            "dm_400_kg": stations["rows"][str(STATIONS_FINE)]["sizing_at_x"]["dm_kg"],
            "move_kg": stations["dm_move_kg"],
            "passed": stations["passed"],
        },
        "wall_s": {
            name: _read_json(out, f"{name.replace('-', '_')}.json")["wall_s"]
            for name in PARTS
            if name != "report"
        },
    }
    if run_a is not None:
        a = _run_a_items(run_a)
        data["run_a"] = a
        data["shipped_minus_run_a"] = {
            "p_ref_kg": s_pad["p_ref_kg"] - a["p_ref_kg"],
            "offload_kg": x_s - a["offload_kg"],
            "dm_kg": s_sol["sizing_at_x"]["dm_kg"] - a["dm_kg"],
            "verification_payload_kg": s_ver["payload_kg"] - a["verification_payload_kg"],
        }
        data["shipped_equals_run_a"] = abs(x_s - a["offload_kg"]) <= RUN_A_MATCH_KG
    _write_json(out, "report.json", data)
    print(json.dumps(_plain(data), indent=2))
    return data


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and run one part, or all of them in order."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, required=True, help="output directory (outside the repo)"
    )
    parser.add_argument("--part", choices=[*PARTS, "all"], required=True)
    parser.add_argument("--run-a", type=Path, default=None, help="run A's results directory")
    args = parser.parse_args(argv)
    out = _check_out(args.out)
    run_a = None if args.run_a is None else args.run_a.resolve()
    for part in PARTS if args.part == "all" else (args.part,):
        t0 = time.perf_counter()
        print(f"[{_now()}] part {part} started", flush=True)
        if part.endswith("-pad"):
            part_pad(out, part.split("-")[0])
        elif part.endswith("-solve"):
            part_solve(out, part.split("-")[0])
        elif part.endswith("-verify"):
            part_verify(out, part.split("-")[0])
        elif part == "stations":
            part_stations(out)
        else:
            part_report(out, run_a)
        print(f"[{_now()}] part {part} ended ({time.perf_counter() - t0:.1f} s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
