"""Regression of the recorded payload capacities of experiments/silo_screening_2d.yaml
(a record, not validation; SP1 step 5, docs/phases/SP1-fuel-offload-planar.md sections
5.12 and 7).

SP1 step 5 extracted the body of ``SearchContext.evaluate`` into
``SearchContext.evaluate_planner`` and ``SearchContext.solve_delta`` (which
``joint_root_crosscheck`` now shares). That is a refactor of validated code, so the
shipped experiment's pad and silo_cold are re-run here exactly as ``launchsim run``
runs them (the experiment and vehicle YAML read, ``config.resolve_experiment``,
``sim.run_resolved`` at the shipped budget) and must reproduce the payload capacities
recorded at full precision in tests/data/silo_screening_2d_record.json (copied by SP1
step 1 from the untracked metrics.json of results/silo_screening_2d/20260930T175743Z,
git 7ad381f) within PAYLOAD_TOL_KG, not merely the one-decimal figures of the tracked
summary.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from launchsim import sim
from launchsim.cli import load_yaml, resolve_vehicle_path
from launchsim.config import resolve_experiment

RECORD_PATH = Path(__file__).parent / "data" / "silo_screening_2d_record.json"
"""Full-precision P* of the shipped silo_screening_2d run."""
PAYLOAD_TOL_KG = 0.002
"""Tolerance [kg] on each reproduced P* (the phase file's step 5 gate)."""


def _record() -> dict[str, Any]:
    with RECORD_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.slow
@pytest.mark.parametrize("name", ["pad", "silo_cold"])
def test_recorded_payload_capacity_reproduces(repo_root: Path, name: str) -> None:
    """The run name of the shipped experiment, resolved from its YAML files and run by
    ``sim.run_resolved``: the search ends ok, the recorded run inserts, and P* equals the
    record within PAYLOAD_TOL_KG (the step-5 refactor guard)."""
    rec = _record()
    exp_path = repo_root / rec["experiment"]
    exp_dict = load_yaml(exp_path)
    vehicle_path = resolve_vehicle_path(exp_path, exp_dict["vehicle"])
    assert vehicle_path.resolve() == (repo_root / rec["vehicle"]).resolve()
    resolved = resolve_experiment(exp_dict, load_yaml(vehicle_path))
    run = sim.run_resolved(resolved.runs[name])
    search = run.result.search
    assert search is not None and search.status == "ok"
    assert search.final is not None and search.final.recorded.status == "inserted"
    assert run.result.metrics["search_budget_id"] == rec["search_budget_id"]
    assert abs(search.payload_kg - rec["payload_kg"][name]) <= PAYLOAD_TOL_KG
