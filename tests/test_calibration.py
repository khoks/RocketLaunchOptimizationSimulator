"""Regression of the labelled calibration (build step 26; CALIBRATION, not validation).

tests/data/calibration_record.json holds the figures of the pre-registered calibration
run results/calibration_f9_2d/20260930T100100Z (inputs frozen at commit c2849b72e01d;
docs/findings/CAL-f9-leo-2d.md). The slow test re-runs, in-process and at the shipped
budget, the whole payload search of the gate pad (mass set C) and of the two other
mass sets (cases readme_loads, set A, and recorded_scope, set B) through the same path
as ``sim.run_planar`` (``sim.planar_setup``, ``sim.search_context``,
``search.run_search``) and checks that P* is reproduced within REL_TOL, and gamma*_ref
within the reporting resolution of amendment 3 (``checks.convergence``,
gamma_resolution_deg = 0.1 deg).

It is a regression reference only. It asserts no calibration band: the published
22.8 t figure is a benchmark to report against, never a target (CLAUDE.md), and a
code change that moves P* must fail here and be explained, not re-fitted.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from launchsim import sim
from launchsim.cli import load_experiment
from launchsim.config import ResolvedRun
from launchsim.search import run_search

RECORD_PATH = Path(__file__).parent / "data" / "calibration_record.json"
"""The calibration record (copied from the run's metrics.json)."""
REL_TOL = 1e-3
"""Relative tolerance [-] on P* (build step 26)."""
MASS_SETS = ("pad", "readme_loads", "recorded_scope")
"""The runs re-flown: the gate pad (set C) and the cases of sets A and B."""


def _record() -> dict[str, Any]:
    with RECORD_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _resolved_run(repo_root: Path, name: str) -> ResolvedRun:
    """The baseline pad or a calibration case of experiments/calibration_f9_2d.yaml."""
    er = load_experiment(repo_root / _record()["experiment"])
    return er.runs[name] if name == er.baseline.name else er.cases[name]


def test_record_matches_the_shipped_experiment(repo_root: Path) -> None:
    """The record names the shipped experiment's baseline as the gate, its three mass
    sets resolve to the recorded vehicle files, and its gate figures are the pad's."""
    rec = _record()
    er = load_experiment(repo_root / rec["experiment"])
    assert er.baseline.name == rec["gate_run"] == rec["mass_sets"]["C"]
    assert set(rec["payload_kg"]) == {er.baseline.name, *er.cases}
    for name in MASS_SETS:
        vehicle_name = _resolved_run(repo_root, name).vehicle.name
        assert Path(rec["vehicles"][name]).stem == vehicle_name
    assert rec["gate_pad"]["payload_kg"] == rec["payload_kg"]["pad"]
    assert rec["gate_pad"]["gamma_star_rad"] == rec["gamma_star_rad"]["pad"]
    assert rec["preregistration"]["dirty"] is False


@pytest.mark.slow
@pytest.mark.parametrize("name", MASS_SETS)
def test_calibration_payload_reproduces(repo_root: Path, name: str) -> None:
    """The payload search of each mass set, re-run at the shipped budget, reproduces the
    recorded P* within REL_TOL and gamma*_ref within gamma_resolution_deg, ends inserted
    and raises no search flag. Measured at the record (build step 26): bit-identical P*
    on all three, about 8 s each."""
    rec = _record()
    rr = _resolved_run(repo_root, name)
    vehicle = rr.to_vehicle()
    setup = sim.planar_setup(rr.run, vehicle)
    record = run_search(sim.search_context(setup, vehicle, rr.run.end))
    assert record.status == "ok"
    assert record.flags == ()
    assert record.final is not None and record.final.recorded.status == "inserted"
    expected = rec["payload_kg"][name]
    assert math.isclose(record.payload_kg, expected, rel_tol=REL_TOL)
    assert rr.run.planar is not None and record.gamma is not None
    resolution = rr.run.planar.checks.convergence.gamma_resolution_rad
    assert abs(record.gamma.gamma_star_rad - rec["gamma_star_rad"][name]) <= resolution
