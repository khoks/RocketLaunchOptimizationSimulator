"""Helpers of the app tests (SP2 step A4; tests/test_appform.py, tests/test_app.py),
loaded by path as tests/golden_1d_support.py is.

- the committed experiment and vehicle files as raw dicts (``raw_files``) and three
  bases: the shipped one, read as committed at HEAD (``shipped_basis``: app.load_basis,
  so its names are committed), and two edited in memory, not committed (commit None:
  every variant and case takes its neutral name and nothing is called a reproduction):
  a fixed-guidance one whose launches fly in about a second each (``fixed_basis``:
  gamma* and the LTG pair fixed, a 0.5 s sample step; it cannot carry an offload block)
  and the small searched grid of tests/test_offload_pipeline.py (``searched_basis``:
  gamma* 18-28 deg, the vehicle's payload near the pad's capacity, a 0.5 s sample
  step);
- ``install_fake_sim``: the sim seams of a launch replaced by fakes, a copy of the
  ``fake_sim`` pattern of tests/test_offload_pipeline.py (not imported from it): every
  run, solve, matched run and paired-pad comparison is a cheap fake, so a launch with an
  offload block runs in well under a second;
- ``git_states``: ``sim.git_info`` replaced by a fake that returns given states in turn
  (the server start, then each launch);
- ``run_page_pure``: the app page's pure block (templates/app.html, step A5) run under node
  with a harness, and ``PAGE_BLOCKS_HARNESS``, which flattens the page's results-panel and
  job-card blocks into [tag, text] lines (tests/test_app_page.py and test_app_server.py).

Nothing here writes outside the folders a test hands in.
"""

from __future__ import annotations

import copy
import json
import math
import shutil
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
import yaml

from launchsim import app, appform, config, results_io, sim
from launchsim.offload import X2_LOG as OFFLOAD_X2_LOG
from launchsim.offload import OffloadEval, OffloadResult
from launchsim.vehicle import offload_load_kg

REPO_ROOT = Path(__file__).resolve().parents[1]
OFFLOAD_EXPERIMENT = Path("experiments") / "silo_offload_2d.yaml"
SCREENING_EXPERIMENT = Path("experiments") / "silo_screening_2d.yaml"
VEHICLE = Path("configs") / "vehicles" / "generic_f9_class_2d.yaml"

FIXED_GAMMA_DEG = 20.0
FIXED_LTG = (0.756790, 2.19338e-3)
"""The fixed guidance of tests/test_planar_pipeline.py's fast experiment (gamma* [deg],
the pad's LTG pair a [-], b [1/s])."""
FAST_SAMPLE_DT_S = 0.5
"""The coarse sample step [s] of the test bases (shipped 0.05 s)."""
SMALL_GRID = {
    "gamma_grid_deg": [18.0, 28.0, 2.0],
    "gamma_refine_maxiter": 3,
    "gamma_refine_halfwidth_deg": 1.0,
    "search_rtol": 1.0e-9,
}
"""The small searched budget of tests/test_offload_pipeline.py (search rtol 1e-9:
CLAUDE.md's test rule)."""
NEAR_CAPACITY_PAYLOAD_T = 26.0
"""The vehicle payload [t] of the searched basis: near the pad's capacity, so the payload
brackets close at once."""

P_REF_KG = 26000.0
"""The fake pad's payload capacity P* [kg]."""
VERIFY_EXCESS_KG = 0.5
"""What a fake payload search finds above P_ref [kg]."""
FAKE_SHARE = 0.08
"""Share of its mode's load a fake case solve takes as x* [-]."""
FAKE_ELEC_J = 4.0e9
"""Electrical energy of a fake assisted run [J]."""
CONTROL_LOGS = (
    OffloadEval(OFFLOAD_X2_LOG, 0.0, 0.03, 0.0, None),
    OffloadEval(OFFLOAD_X2_LOG, 2.0, -0.033, 0.0, None),
)
"""Logged evaluations of a fake stage-1 pad control: one bracket of m_res = 0."""


# ------------------------------------------------------------------ the app page under node

NODE = shutil.which("node")
"""node, which runs the app page's pure block (None: those tests are skipped)."""
PAGE_PURE_BEGIN = (
    "// ------------------------------------------------------------------ pure functions: begin"
)
PAGE_PURE_END = (
    "// ------------------------------------------------------------------ pure functions: end"
)
PAGE_BLOCKS_HARNESS = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
function flat(blocks, out) {
  blocks.forEach(b => {
    if (b.t === "box" || b.t === "fold") {
      out.push([b.t + "." + b.cls, b.t === "fold" ? b.summary : ""]);
      flat(b.blocks, out);
      out.push(["/" + b.t, ""]);
    } else if (b.t === "ul") b.items.forEach(i => out.push(["li", i]));
    else if (b.t === "kv") b.rows.forEach(r => out.push(["kv", r[0] + ": " + r[1]]));
    else if (b.t === "details") {
      out.push(["summary", b.summary]);
      b.items.forEach(i => out.push(["li", i]));
    } else if (b.t === "strongs") b.items.forEach(i => out.push(["li", i[0] + " " + i[1]]));
    else out.push([b.t + (b.cls ? "." + b.cls : ""), b.text]);
  });
  return out;
}
const out = {};
out.panels = (input.details || []).map(d => flat(panelBlocks(d), []));
out.jobs = (input.jobs || []).map(j => flat(jobBlocks(j[0], j[1]), []));
out.stages = (input.jobs || []).map(j => {
  const ctx = j[1] || {};
  return stageItems(j[0], ctx.runs || null, ctx.times || null, ctx.mark || null, ctx.items || null);
});
out.now = out.stages.map(s => s.filter(i => i.state === "now").map(nowText));
process.stdout.write(JSON.stringify(out));
"""
"""Run with ``run_page_pure``: {details: [GET /api/results/... records], jobs: [[job,
ctx]]} -> {panels, jobs: [[tag(.class), text]] per record, stages (stageItems with the
ctx's ``runs``, ``times``, ``mark`` and ``items``), now (nowText of each running
stage)}; a box opens with 'box.<class>' and closes with '/box', a fold opens with
'fold.<class>' and its summary and closes with '/fold', a list item is 'li', a key-value
row 'kv'."""


def run_page_pure(harness: str, case: Any, tmp_path: Path) -> Any:
    """The app page's pure block (app.load_app_template, between PAGE_PURE_BEGIN and
    PAGE_PURE_END) with ``harness`` appended, run under node on ``case`` (JSON in a file,
    the script's argv[2]); the harness writes one JSON value to stdout."""
    assert NODE is not None
    template = app.load_app_template()
    start, end = template.index(PAGE_PURE_BEGIN), template.index(PAGE_PURE_END)
    js = tmp_path / "page_pure.js"
    js.write_text(template[start:end] + harness, encoding="utf-8", newline="\n")
    data = tmp_path / "page_case.json"
    data.write_text(json.dumps(case), encoding="utf-8", newline="\n")
    proc = subprocess.run(
        [NODE, str(js), str(data)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


# ------------------------------------------------------------------ files and bases


def raw_files(repo_root: Path = REPO_ROOT) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """The committed offload experiment, screening experiment and gate vehicle as raw
    dicts (yaml.safe_load, as the app loads them)."""
    return tuple(  # type: ignore[return-value]
        yaml.safe_load((repo_root / rel).read_text(encoding="utf-8"))
        for rel in (OFFLOAD_EXPERIMENT, SCREENING_EXPERIMENT, VEHICLE)
    )


def shipped_basis(repo_root: Path = REPO_ROOT) -> appform.Basis:
    """The basis the app loads: the committed files as committed at HEAD
    (``app.load_basis``; read-only git), so ``commit`` is HEAD and committed names are
    kept."""
    head = app.head_commit(repo_root)
    assert head is not None, "the shipped basis is read from a commit: git must give HEAD"
    return app.load_basis(repo_root, app.ServerStart(git={}, head=head))


def _edited(exps: Iterable[dict[str, Any]], search: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Copies of the experiments with the search block updated and the 0.5 s sample step."""
    out = []
    for exp in exps:
        exp = copy.deepcopy(exp)
        exp["search"].update(copy.deepcopy(dict(search)))
        exp["baseline"]["integrator"]["sample_dt_s"] = FAST_SAMPLE_DT_S
        out.append(exp)
    return out


def fixed_basis(repo_root: Path = REPO_ROOT) -> appform.Basis:
    """A basis with fixed guidance (figure_of_merit none, FIXED_GAMMA_DEG and FIXED_LTG)
    and FAST_SAMPLE_DT_S in both experiments: a launch flies each run in about a second;
    it cannot carry an offload block (the config refuses it with fixed guidance). Edited,
    so not committed (commit None): every name is neutral."""
    off, scr, veh = raw_files(repo_root)
    search = {
        "figure_of_merit": "none",
        "fixed_gamma_star_deg": FIXED_GAMMA_DEG,
        "fixed_ltg_a": FIXED_LTG[0],
        "fixed_ltg_b_per_s": FIXED_LTG[1],
    }
    off, scr = _edited((off, scr), search)
    return appform.make_basis(off, scr, veh)


def searched_basis(repo_root: Path = REPO_ROOT) -> appform.Basis:
    """A basis on SMALL_GRID with FAST_SAMPLE_DT_S and the vehicle's payload at
    NEAR_CAPACITY_PAYLOAD_T (a real searched launch takes one to two minutes). Edited, so
    not committed (commit None): every name is neutral."""
    off, scr, veh = raw_files(repo_root)
    off, scr = _edited((off, scr), SMALL_GRID)
    veh = copy.deepcopy(veh)
    veh["payload_mass_t"]["value"] = NEAR_CAPACITY_PAYLOAD_T
    return appform.make_basis(off, scr, veh)


# ------------------------------------------------------------------ fake seams


def _fake_result(
    metrics: dict[str, Any],
    search: Any = None,
    status: str = "inserted",
    flags: Iterable[str] = (),
) -> sim.Result:
    """A planar Result holding only metrics (and a search record), with a run status
    and flags."""
    return sim.Result(
        metrics=dict(metrics),
        timeseries=pd.DataFrame(),
        loss_budget=None,
        assist_budget=None,
        assumptions=[],
        phases=[],
        status=status,  # type: ignore[arg-type]
        flags=list(flags),
        model=config.PLANAR_2D,
        search=search,
    )


def _assisted(resolved: Any) -> bool:
    return resolved.run_dict.get("assist", {}).get("model", "none") != "none"


def fake_rr(resolved: Any, payload_kg: float | None, flags: Iterable[str] = ()) -> sim.RunResult:
    """A RunResult of a resolved run whose payload search found payload_kg (None: the
    search failed, run status search_failed, with its failure kind); an assisted run
    carries FAKE_ELEC_J."""
    status = "search_failed" if payload_kg is None else "ok"
    metrics = {
        "payload_kg": payload_kg,
        "search_status": status,
        "search_failure_kind": "fake" if payload_kg is None else None,
        "electrical_energy_J": FAKE_ELEC_J if _assisted(resolved) else None,
        "run_checks": "ok",
    }
    p_star = math.nan if payload_kg is None else payload_kg
    search = SimpleNamespace(status=status, payload_kg=p_star, flags=())
    run_status = "search_failed" if payload_kg is None else "inserted"
    return sim.RunResult(resolved.name, resolved, _fake_result(metrics, search, run_status, flags))


def _solve_result(
    start: Any,
    mode: str,
    p_ref: float,
    status: str = "ok",
    m_res_kg: float = 0.03,
    evals: tuple[OffloadEval, ...] = (),
) -> OffloadResult:
    """A fake solve on start: ok takes FAKE_SHARE of its mode's load, no_offload x = 0
    with m_res(0) = m_res_kg."""
    load = offload_load_kg(start.to_vehicle(), mode)
    x = FAKE_SHARE * load if status == "ok" else 0.0
    return OffloadResult(
        mode=mode,
        reference_payload_kg=p_ref,
        load_kg=load,
        status=status,
        offload_kg=x,
        root_kg=x,
        gamma_star_rad=0.4,
        m_res_kg=m_res_kg,
        dv_margin_mps=0.001,
        dv_shortfall_mps=math.nan,
        at_offload=None,
        recorded=SimpleNamespace(),
        offloaded_vehicle=None,
        evaluations=evals,
        n_evaluations=len(evals),
        grid=(),
        verification=None,
        flags=(),
    )


def install_fake_sim(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The sim seams of a launch replaced by fakes (the ``fake_sim`` pattern of
    tests/test_offload_pipeline.py): ``run_resolved`` (the baseline at P_REF_KG, every
    other run at P_REF_KG + VERIFY_EXCESS_KG unless ``state.payloads`` names it, None
    being a failed search, with the flags ``state.flags`` names; each call's ResolvedRun
    recorded in ``state.ran``), ``rerun_resolved`` (counted in ``state.reruns``),
    ``matched_run`` (None: no decomposition), ``solve_resolved_offload`` (a case takes
    FAKE_SHARE of its load, or ends ``state.case_status``; the pad's stage-1 control ends
    no_offload by grams), ``offload_run_result`` (with the flags ``state.flags`` names for
    the recorded run), the paired-pad comparison and the
    comparison of the variants (``planar_comparisons``: an empty record per run, since a
    fake run has no trajectory to compare)."""
    state = SimpleNamespace(
        ran=[], solved=[], reruns=0, baseline_name="pad", payloads={}, flags={}, case_status="ok"
    )

    def run_resolved(resolved: Any) -> sim.RunResult:
        state.ran.append(resolved)
        default = P_REF_KG if resolved.name == state.baseline_name else P_REF_KG + VERIFY_EXCESS_KG
        payload = state.payloads.get(resolved.name, default)
        return fake_rr(resolved, payload, state.flags.get(resolved.name, ()))

    def rerun_resolved(resolved: Any, hit: Any) -> sim.RunResult:
        state.reruns += 1
        return run_resolved(resolved)

    def solve(start: Any, mode: str, p_ref: float) -> OffloadResult:
        state.solved.append((start.name, mode, p_ref))
        if start.name == state.baseline_name and mode == "stage1":
            return _solve_result(start, mode, p_ref, "no_offload", -0.0016, CONTROL_LOGS)
        return _solve_result(start, mode, p_ref, state.case_status)

    def offload_run_result(final: Any, res: OffloadResult) -> sim.RunResult:
        metrics = {
            "payload_kg": res.reference_payload_kg,
            "electrical_energy_J": FAKE_ELEC_J if _assisted(final) else None,
            "run_checks": "ok",
        }
        flags = state.flags.get(final.name, ())
        return sim.RunResult(final.name, final, _fake_result(metrics, flags=flags))

    def paired(silo: Any, pad: Any, checks: Any, name: str) -> dict[str, Any]:
        p_silo, p_pad = silo.result.metrics["payload_kg"], pad.result.metrics["payload_kg"]
        return {"payload_delta_kg": p_silo - p_pad, "screening_status": "ok"}

    def comparisons(resolved: Any, baseline: Any, runs: Mapping[str, Any]) -> dict[str, Any]:
        return {name: {} for name in runs}

    monkeypatch.setattr(sim, "run_resolved", run_resolved)
    monkeypatch.setattr(sim, "rerun_resolved", rerun_resolved)
    monkeypatch.setattr(sim, "matched_run", lambda *a, **k: None)
    monkeypatch.setattr(sim, "solve_resolved_offload", solve)
    monkeypatch.setattr(sim, "offload_run_result", offload_run_result)
    monkeypatch.setattr(results_io, "attributed_comparison", paired)
    monkeypatch.setattr(results_io, "planar_comparisons", comparisons)
    return state


def git_states(monkeypatch: pytest.MonkeyPatch, *states: Mapping[str, Any]) -> list[Any]:
    """``sim.git_info`` replaced by a fake returning ``states`` in turn (the last one
    again once they run out); returns the list of the paths it was called with."""
    calls: list[Any] = []

    def git_info(repo_root: Path) -> dict[str, Any]:
        calls.append(repo_root)
        return dict(states[min(len(calls), len(states)) - 1])

    monkeypatch.setattr(sim, "git_info", git_info)
    return calls
