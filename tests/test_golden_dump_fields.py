"""The field lists of every dataclass the 1-D golden dump reaches (SP7 design D-SP7-27).

Why: the 1-D golden tier (tests/golden_1d_support.py, tests/test_golden_1d.py) can never
be recaptured: ``capture`` refuses unless the guarded sources equal the Phase 1 reference
commit. Its object dumps turn every dataclass into a dict in field order (``plain``), so a
field added to a dataclass the dump converts changes the dump and fails the golden for
good; and the dump reads the rest of its objects by attribute name, so the design forbids
new fields on those too (D-SP7-27: new data rides in new classes built only by the new
features). This fast test pins both lists, so such a change fails here first, with a
readable message, instead of in the golden comparison.

- Converted field by field by ``plain`` (a change alters the dump's bytes):
  ``losses.LossBudget`` (``result_objects``' loss_budget) and ``losses.AssistEnergyBudget``
  (its assist_budget). Their pinned lists also equal the keys of every non-null
  loss_budget and assist_budget in the recorded objects.json files of both golden sets.
- Reached by attribute (``result_objects``, ``run_objects``, ``sensitivity_objects``,
  ``experiment_objects``, ``sweep_objects``): ``sim.Result``, ``sim.RunResult``,
  ``config.ResolvedRun``, ``config.SweepPoint``, ``compare.SensitivityRow`` (whose every
  field the dump writes, in declaration order), ``results_io.ExperimentResult`` and
  ``results_io.SweepResult``.

Everything else the dump writes is a plain value: the metrics, comparisons, overrides and
run dicts are dicts; status and flags strings; the resolved inputs raw YAML dicts.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from launchsim import compare, config, losses, results_io, sim

GOLDEN_DIR = Path(__file__).resolve().parent / "data" / "golden"

DUMPED_BY_FIELD: dict[type, tuple[str, ...]] = {
    losses.LossBudget: (
        "dv_vac",
        "gravity",
        "gravity_alt",
        "drag",
        "steering",
        "back_pressure",
        "speed_start",
        "speed_end",
    ),
    losses.AssistEnergyBudget: (
        "work_drive",
        "work_thrust",
        "delta_mech",
        "massflow_term",
        "dissipated",
    ),
}
"""The dataclasses ``plain`` converts field by field, with their fields in order."""

REACHED_BY_ATTRIBUTE: dict[type, tuple[str, ...]] = {
    sim.Result: (
        "metrics",
        "timeseries",
        "loss_budget",
        "assist_budget",
        "assumptions",
        "phases",
        "status",
        "flags",
        "events",
        "model",
        "search",
        "closure",
        "trace",
    ),
    sim.RunResult: ("name", "resolved", "result"),
    config.ResolvedRun: ("name", "run", "vehicle", "run_dict", "vehicle_dict"),
    config.SweepPoint: (
        "sweep_index",
        "point_index",
        "of",
        "overrides",
        "run",
        "paired_baseline",
        "offload",
    ),
    compare.SensitivityRow: (
        "of",
        "param",
        "fraction",
        "value_yaml_units",
        "value_si",
        "value_si_unit",
        "result",
        "comparison",
        "baseline_perturbed",
        "comparison_perturbed",
    ),
    results_io.ExperimentResult: (
        "experiment_name",
        "vehicle_name",
        "baseline",
        "variants",
        "comparison",
        "git",
        "timestamp_utc",
        "comparison_basis",
        "sensitivity",
        "sensitivity_note",
        "model",
        "label",
        "bounds",
        "cases",
        "search_budget_id",
        "preregistration",
        "offload",
    ),
    results_io.SweepResult: (
        "sweep_index",
        "of",
        "axes",
        "points",
        "results",
        "comparisons",
        "run_dirs",
        "paired",
        "offload",
        "offload_runs",
    ),
}
"""The dataclasses the dump reads by attribute, with their fields in order."""


def _names(cls: type) -> tuple[str, ...]:
    """The dataclass's field names in declaration order."""
    return tuple(f.name for f in dataclasses.fields(cls))


def test_dataclasses_dumped_field_by_field_keep_their_fields() -> None:
    """LossBudget and AssistEnergyBudget keep exactly their fields, in order, and stay
    frozen."""
    for cls, fields in DUMPED_BY_FIELD.items():
        assert _names(cls) == fields, cls.__qualname__
        assert cls.__dataclass_params__.frozen, cls.__qualname__  # type: ignore[attr-defined]


def test_dataclasses_reached_by_attribute_keep_their_fields() -> None:
    """Result, RunResult, ResolvedRun, SweepPoint, SensitivityRow, ExperimentResult and
    SweepResult keep exactly their fields, in order (D-SP7-27)."""
    for cls, fields in REACHED_BY_ATTRIBUTE.items():
        assert _names(cls) == fields, cls.__qualname__


def _budgets(tree: Any, key: str) -> list[dict[str, Any]]:
    """Every non-null mapping stored under ``key`` anywhere in a JSON tree."""
    found: list[dict[str, Any]] = []
    if isinstance(tree, dict):
        for k, v in tree.items():
            if k == key and isinstance(v, dict):
                found.append(v)
            else:
                found += _budgets(v, key)
    elif isinstance(tree, list):
        for v in tree:
            found += _budgets(v, key)
    return found


def test_pinned_budget_fields_are_the_recorded_golden_keys() -> None:
    """The pinned field lists equal the keys, in order, of every non-null loss_budget and
    assist_budget in the golden sets' objects.json files (both sets, run and sweep)."""
    files = sorted(GOLDEN_DIR.rglob("objects.json"))
    assert len(files) >= 3, files
    seen = {"loss_budget": 0, "assist_budget": 0}
    expected = {
        "loss_budget": DUMPED_BY_FIELD[losses.LossBudget],
        "assist_budget": DUMPED_BY_FIELD[losses.AssistEnergyBudget],
    }
    for path in files:
        tree = json.loads(path.read_text(encoding="utf-8"))
        for key, fields in expected.items():
            for budget in _budgets(tree, key):
                assert tuple(budget) == fields, (path.name, key)
                seen[key] += 1
    assert seen["loss_budget"] > 0 and seen["assist_budget"] > 0, seen
