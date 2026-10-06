"""The replay page's caveat wording, built from the run data (SP2 step A1a, D-SP2-23,
KI-029), on the synthetic directory of tests/test_replay.py with its metrics amended:
the drive caveat's closing clauses follow the runs shown (a prescribed drive, each
acceleration named first with its runs and "this drive" only for one, a massless
carriage, a vented shaft, the kick clause only for runs that kicked, the kick verdict
read from each run's peak q-alpha against its comparison partner's, the baseline's or a
bound re-run's paired baseline's, the bias clauses only under the prescribed drive, "the
payload" only for a run that has one); a page of a 22 t sled never says "massless"; the
structure caveat names each pushed run's own load at push start (a held hot start less
its hold burn) and peak felt g, and for a penalty row the assumed stage-1 dry mass its
record charges instead of "No structural mass is charged"; a paired pad is labelled
"paired pad", said to fly its own payload capacity, and the comparison caveat tells a
paired pad (a payload change) from a stage-1 case's recorded run and a pad control
(propellant saved at P_ref), from a stage-2 or both-stage solve (net of the pad control, a
property of the vehicle model) and from a fixed case, whose note gives P* - P_ref with its
reading (D-SP2-27); a stage-2 case names its stage, its net figure, its failed
verification by the sign of its payload gap (a lower bound on the gross removal only for a
gap above P_ref; the net figure uncertain both ways through its flagged control) and its
flags; a solve that found no offload or failed says so instead of "0.00 t (solved)"; a
pad control says what it found; the offload note keeps two decimals; the subtitle names
the baseline only when it is on the page; "leaves" for one run; no percentage is written
into replay.py; replay.html is frozen (D-SP2-21, its sha256); and the exploratory label
of an app run (D-SP2-12) prepends one caveat to the page and the same line as a footnote
to the animation, while a recorded directory (label null or another value) gets neither
and the same runs block."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

import pytest
import yaml
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from test_animate import _make_run_dir as _make_animation_dir
from test_replay import (
    DEPTH_M,
    PUSH_S,
    _embedded,
    _make_run_dir,
    _run_config,
    _run_metrics,
    _write_run,
)

from launchsim import plots, replay, run_data

PAD_Q_ALPHA = 70.0
SILO_Q_ALPHA = 130.0
STEP_Q_ALPHA = 220.0
"""Peak q-alpha [Pa rad] given to the fixture's pad, silo and silo_step (the silo runs
above the pad's, as every recorded silo variant is)."""
SILO_LIFTOFF_KG = 574_000.0
STEP_LIFTOFF_KG = 579_000.0
P_REF_KG = 1000.0
OFFLOAD_KG = 41_262.9
PAIRED_PAD_KG = 958.6
FIXED_OFFLOAD_KG = 20_545.0
FIXED_PAYLOAD_KG = 1030.0
SLED_CARRIAGE_KG = 22_000.0
STAGE2_OFFLOAD_KG = 31_904.3
STAGE2_CONTROL_KG = 513.6
STAGE2_VERIFY_DELTA_KG = 15.36
VERIFY_TOL_KG = 2.6
BOTH_OFFLOAD_KG = 46_168.2
FRONTIER_OFFLOAD_KG = 42_768.5
FRONTIER_PREOFFLOAD_KG = 2000.0
"""The stage-2, both-stage and frontier (2 t of stage 2 imposed first) solves of
results/silo_offload_2d/20261003T112934Z, as docs/findings/RQ1-fuel-offload-2d.md
tabulates them: gross removal, pad control, verification delta against its tolerance."""


def _amend_metrics(run_dir: Path, change: Any) -> None:
    """Load metrics.json, apply ``change(metrics)`` and write it back."""
    path = run_dir / "metrics.json"
    metrics = json.loads(path.read_text(encoding="utf-8"))
    change(metrics)
    path.write_text(json.dumps(metrics), encoding="utf-8")


def _amend_config(run_dir: Path, change: Any) -> None:
    """Load resolved_config.yaml, apply ``change(config)`` and write it back."""
    path = run_dir / "resolved_config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(config)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def _kick_and_loads(metrics: dict[str, Any]) -> None:
    """Give the fixture's runs the metrics A1a's text reads: each run's peak q-alpha
    and kick regime, the pushed runs' liftoff mass and carriage mass (0 for silo, the
    5 t of silo_step's config)."""
    runs = metrics["runs"]
    runs["pad"].update(peak_q_alpha=PAD_Q_ALPHA, kick_regime="after_vertical_rise")
    runs["silo"].update(
        peak_q_alpha=SILO_Q_ALPHA,
        kick_regime="at_first_lit_instant",
        liftoff_mass_kg=SILO_LIFTOFF_KG,
        carriage_mass_kg=0.0,
    )
    runs["silo_step"].update(
        peak_q_alpha=STEP_Q_ALPHA,
        kick_regime="at_first_lit_instant",
        liftoff_mass_kg=STEP_LIFTOFF_KG,
        carriage_mass_kg=5000.0,
    )


def _make_dir(tmp_path: Path) -> Path:
    """tests/test_replay.py's synthetic directory with ``_kick_and_loads`` applied."""
    run_dir = _make_run_dir(tmp_path)
    _amend_metrics(run_dir, _kick_and_loads)
    return run_dir


def _add_offload(run_dir: Path) -> None:
    """Add an offload block to the synthetic directory: the solved stage-1 case silo_s1
    of silo (OFFLOAD_KG, flying P_REF_KG) with its paired pad silo_s1__pad (flying
    PAIRED_PAD_KG), the stage-1 pad control pad__offload_stage1 (a record with the status
    alone), and the fixed case silo_fix (FIXED_OFFLOAD_KG imposed, flying its own
    FIXED_PAYLOAD_KG); each with its run folder and its ``offload_runs`` config entry.
    ``_add_netted_cases`` adds the stage-2, both and frontier solves."""
    for name, assist in (
        ("silo_s1", True),
        ("silo_s1__pad", False),
        ("pad__offload_stage1", False),
        ("silo_fix", True),
    ):
        _write_run(run_dir, name, assist)

    def change(metrics: dict[str, Any]) -> None:
        metrics["offload"] = {
            "reference": "pad",
            "reference_payload_kg": P_REF_KG,
            "cases": [
                {
                    "name": "silo_s1",
                    "run": "silo_s1",
                    "of": "silo",
                    "kind": "solve",
                    "mode": "stage1",
                    "total_offload_kg": OFFLOAD_KG,
                    "stage1_fraction": 0.1004,
                    "stage2_fraction": 0.0,
                    "total_fraction": 0.0796,
                    "payload_kg": P_REF_KG,
                    "paired_pad": {
                        "run": "silo_s1__pad",
                        "payload_kg": PAIRED_PAD_KG,
                        "payload_delta_vs_reference_kg": PAIRED_PAD_KG - P_REF_KG,
                    },
                },
                {
                    "name": "silo_fix",
                    "run": "silo_fix",
                    "of": "silo",
                    "kind": "fixed",
                    "mode": "stage1",
                    "total_offload_kg": FIXED_OFFLOAD_KG,
                    "stage1_fraction": 0.05,
                    "total_fraction": 0.0396,
                    "payload_kg": FIXED_PAYLOAD_KG,
                    "paired_pad": None,
                },
            ],
            "pad_controls": [
                {"mode": "stage1", "run": "pad__offload_stage1", "status": "no_offload"}
            ],
            "runs": {
                "silo_s1": _pushed_offload_run(P_REF_KG, OFFLOAD_KG),
                "silo_s1__pad": _pad_offload_run(PAIRED_PAD_KG),
                "pad__offload_stage1": _pad_offload_run(P_REF_KG),
                "silo_fix": _pushed_offload_run(FIXED_PAYLOAD_KG, FIXED_OFFLOAD_KG),
            },
        }

    _amend_metrics(run_dir, change)

    def config_change(config: dict[str, Any]) -> None:
        config["offload_runs"] = {
            "silo_s1": _run_config(True),
            "silo_s1__pad": _run_config(False),
            "pad__offload_stage1": _run_config(False),
            "silo_fix": _run_config(True),
        }

    _amend_config(run_dir, config_change)


def _pushed_offload_run(payload_kg: float, offload_kg: float) -> dict[str, Any]:
    """The ``offload.runs`` record of a pushed offload run: silo's metrics with the
    payload it flew, its lighter liftoff mass and a massless carriage."""
    record = _run_metrics(True, False)
    record.update(
        payload_kg=payload_kg,
        peak_q_alpha=SILO_Q_ALPHA,
        kick_regime="at_first_lit_instant",
        liftoff_mass_kg=SILO_LIFTOFF_KG - offload_kg,
        carriage_mass_kg=0.0,
    )
    return record


def _pad_offload_run(payload_kg: float) -> dict[str, Any]:
    """The ``offload.runs`` record of a pad run of the offload block (a paired pad or a
    pad control) with the payload it flew."""
    record = _run_metrics(False, False)
    record.update(payload_kg=payload_kg, peak_q_alpha=PAD_Q_ALPHA)
    return record


def _add_netted_cases(run_dir: Path) -> None:
    """Add, after ``_add_offload``, the solves summary.md quotes net of the pad control
    and the frontier case, with the records of results/silo_offload_2d/20261003T112934Z
    (RQ1-fuel-offload-2d, the stage-2 table): silo_s2 (stage 2 only, STAGE2_OFFLOAD_KG
    gross, STAGE2_CONTROL_KG from the pad control, verification failed by
    STAGE2_VERIFY_DELTA_KG against VERIFY_TOL_KG, four flags) with its pad control
    pad__offload_stage2 (status ok, one flag); silo_both (BOTH_OFFLOAD_KG, equal
    fractions, a pad control of 0, verification passed) with pad__offload_both; silo_pre
    (a stage-1 solve with FRONTIER_PREOFFLOAD_KG of stage 2 imposed first)."""
    for name, assist in (
        ("silo_s2", True),
        ("pad__offload_stage2", False),
        ("silo_both", True),
        ("pad__offload_both", False),
        ("silo_pre", True),
    ):
        _write_run(run_dir, name, assist)

    def verification(delta_kg: float) -> dict[str, Any]:
        return {
            "status": "ok",
            "payload_kg": P_REF_KG + delta_kg,
            "delta_kg": delta_kg,
            "tolerance_kg": VERIFY_TOL_KG,
            "passed": abs(delta_kg) <= VERIFY_TOL_KG,
        }

    def change(metrics: dict[str, Any]) -> None:
        offload = metrics["offload"]
        offload["cases"] += [
            {
                "name": "silo_s2",
                "run": "silo_s2",
                "of": "silo",
                "kind": "solve",
                "mode": "stage2",
                "total_offload_kg": STAGE2_OFFLOAD_KG,
                "quoted_offload_kg": STAGE2_OFFLOAD_KG - STAGE2_CONTROL_KG,
                "quoted_basis": "x* net of the pad control's x_pad: a property of the vehicle "
                "model, not of the assist",
                "pad_control_offload_kg": STAGE2_CONTROL_KG,
                "stage1_fraction": 0.0,
                "stage2_fraction": 0.2968,
                "total_fraction": 0.0615,
                "payload_kg": P_REF_KG,
                "paired_pad": None,
                "verification": verification(STAGE2_VERIFY_DELTA_KG),
                "flags": [
                    "offload: P1_backoff",
                    "offload: refine a",
                    "offload: refine b",
                    "offload: offload_verify_mismatch",
                ],
            },
            {
                "name": "silo_both",
                "run": "silo_both",
                "of": "silo",
                "kind": "solve",
                "mode": "both",
                "total_offload_kg": BOTH_OFFLOAD_KG,
                "quoted_offload_kg": BOTH_OFFLOAD_KG,
                "quoted_basis": "x* net of the pad control's x_pad: a property of the vehicle "
                "model, not of the assist",
                "pad_control_offload_kg": 0.0,
                "stage1_fraction": 0.0891,
                "stage2_fraction": 0.0891,
                "total_fraction": 0.0891,
                "payload_kg": P_REF_KG,
                "paired_pad": None,
                "verification": verification(-0.0003),
                "flags": [],
            },
            {
                "name": "silo_pre",
                "run": "silo_pre",
                "of": "silo",
                "kind": "solve",
                "mode": "stage1",
                "total_offload_kg": FRONTIER_OFFLOAD_KG,
                "quoted_offload_kg": FRONTIER_OFFLOAD_KG - FRONTIER_PREOFFLOAD_KG,
                "quoted_basis": "x* at P_ref, gross: stage 1, the headline",
                "pad_control_offload_kg": 0.0,
                "stage2_preoffload_kg": FRONTIER_PREOFFLOAD_KG,
                "stage1_fraction": 0.0992,
                "stage2_fraction": 0.0186,
                "total_fraction": 0.0825,
                "payload_kg": P_REF_KG,
                "paired_pad": None,
                "verification": verification(0.369),
                "flags": [],
            },
        ]
        offload["pad_controls"] += [
            {
                "mode": "stage2",
                "run": "pad__offload_stage2",
                "status": "ok",
                "offload_kg": STAGE2_CONTROL_KG,
                "m_res_kg": 6.1e-6,
                "resolution_effect": False,
                "consistency": "n/a",
                "flags": ["offload: search_vs_final_payload"],
            },
            {
                "mode": "both",
                "run": "pad__offload_both",
                "status": "ok",
                "offload_kg": 0.0,
                "m_res_kg": 0.00057,
                "resolution_effect": False,
                "consistency": "n/a",
                "flags": [],
            },
        ]
        offload["runs"].update(
            silo_s2=_pushed_offload_run(P_REF_KG, STAGE2_OFFLOAD_KG),
            pad__offload_stage2=_pad_offload_run(P_REF_KG),
            silo_both=_pushed_offload_run(P_REF_KG, BOTH_OFFLOAD_KG),
            pad__offload_both=_pad_offload_run(P_REF_KG),
            silo_pre=_pushed_offload_run(P_REF_KG, FRONTIER_OFFLOAD_KG),
        )

    _amend_metrics(run_dir, change)

    def config_change(config: dict[str, Any]) -> None:
        config["offload_runs"].update(
            silo_s2=_run_config(True),
            pad__offload_stage2=_run_config(False),
            silo_both=_run_config(True),
            pad__offload_both=_run_config(False),
            silo_pre=_run_config(True),
        )

    _amend_config(run_dir, config_change)


def _caveats(run_dir: Path, runs: list[str]) -> list[str]:
    return replay.replay_data(run_dir, runs)["meta"]["caveats"]


def _drive(run_dir: Path, runs: list[str]) -> str:
    """The drive caveat of a selection (the only item that names the carriage or the
    shaft)."""
    return next(c for c in _caveats(run_dir, runs) if "carriage" in c or "shaft" in c)


def _kick_sentence(text: str) -> str | None:
    """The sentence of a caveat that starts 'The free kick', or None."""
    match = re.search(r"The free kick .*?Pa rad\)\.", text)
    return None if match is None else match.group(0)


# ---------------------------------------------------------------- the frozen template

REPLAY_TEMPLATE_SHA256 = "1fa6eba6be18c5c2a8d10a3e42880ae556375dcf1508f6feb937aca641916990"
"""sha256 of src/launchsim/templates/replay.html at the start of SP2 (commit a5b8133)."""


def test_replay_template_is_frozen_for_sp2() -> None:
    """D-SP2-21: replay.html is not edited in SP2. The caveat wording moves into
    replay.py's data (this file's tests), the scene page gets its own template, and the
    three drawing patches of site/build.py REPLAY_TEXT_FIXES stay there until a later
    phase edits the template; the sha256 pins it (the standing gate of design section 5)."""
    template = resources.files("launchsim").joinpath(*replay.REPLAY_TEMPLATE)
    assert hashlib.sha256(template.read_bytes()).hexdigest() == REPLAY_TEMPLATE_SHA256


# ---------------------------------------------------------------- the drive caveat


def test_no_percentage_or_fixed_verdict_is_written_into_replay_py() -> None:
    """No string literal of replay.py that can reach a page carries a percentage (the
    0.04%, 0.08% and 0.08% of the shaft-drag estimate stay in the findings note), and the
    two fixed verdicts are gone. Bare string statements (docstrings) are documentation,
    not page text, and are skipped."""
    source = Path(replay.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    documentation = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        if id(node) not in documentation
    ]
    assert literals  # the walk found the page text
    assert not [s for s in literals if re.search(r"\d\s*%", s)]
    assert "Each of these favours" not in source
    assert "fully fuelled" not in source


def test_drive_caveat_closes_with_clauses_built_from_the_runs_shown(tmp_path: Path) -> None:
    """pad, silo (massless, vented) and silo_step (5 t carriage, vented): the per-run
    parts stay; the closing says what the omissions do to the numbers shown, with the
    carriage clause naming silo alone (silo_step has a carriage) and the interface force
    biased only by the missing shaft drag (RQ3: the 22 t carriage leaves it unchanged);
    the kick clause reads both runs' peak q-alpha against the baseline's."""
    run_dir = _make_dir(tmp_path)
    text = _drive(run_dir, ["pad", "silo", "silo_step"])
    assert text.startswith(
        "The drive is a prescribed 3 g push with no force or power limit, the carriage is "
        "massless (silo), the shaft has no air drag and the pitch kick has no aerodynamic "
        "penalty. "
    )
    assert (
        "Under this drive the release speed and the payload do not depend on the carriage "
        "mass or the shaft drag: the massless carriage biases the drive energy and peak power "
        "low (silo), and the missing shaft drag biases the drive energy, peak power and "
        "interface force low."
    ) in text
    assert "carriage biases the drive energy, peak power and interface" not in text
    assert "Each of these favours" not in text and "offload" not in text
    assert _kick_sentence(text) == (
        f"The free kick favours silo and silo_step, whose peak q-alpha is above the baseline "
        f"pad's ({SILO_Q_ALPHA:.1f} and {STEP_Q_ALPHA:.1f} against {PAD_Q_ALPHA:.1f} Pa rad)."
    )
    # silo alone: every per-run part applies to every pushed run, so none names it
    alone = _drive(run_dir, ["pad", "silo"])
    assert "(silo)" not in alone and "the massless carriage biases" in alone


def test_two_prescribed_accelerations_are_named_first_and_not_called_this_drive(
    tmp_path: Path,
) -> None:
    """silo_step pushed at 1.5 g beside silo at 3 g (as silo_cold_200m beside silo_cold in
    the offload directory's default selection): the two drive parts open the sentence
    together, each with its runs, before the carriage, shaft and kick parts; the closing
    says 'these prescribed drives', never 'this drive'. Beside a force-limited run the
    prescribed drives are named."""
    run_dir = _make_dir(tmp_path)
    _amend_metrics(run_dir, lambda m: m["runs"]["silo_step"].update(net_accel_g=1.5))
    text = _drive(run_dir, ["pad", "silo", "silo_step"])
    assert text.startswith(
        "The drive is a prescribed 3 g push with no force or power limit (silo) and a prescribed "
        "1.5 g push with no force or power limit (silo_step), the carriage is massless (silo), "
        "the shaft has no air drag and the pitch kick has no aerodynamic penalty. Under these "
        "prescribed drives the release speed and the payload do not depend on the carriage mass "
        "or the shaft drag: "
    )
    assert "this drive" not in text
    assert text.lower().count("the drive is") == 1  # one drive clause, not one per push
    # a third pushed run under another drive model: the prescribed drives are named
    _write_run(run_dir, "sled", True)

    def add_sled(metrics: dict[str, Any]) -> None:
        metrics["runs"]["sled"] = {
            **_run_metrics(True, False),
            "carriage_mass_kg": SLED_CARRIAGE_KG,
            "peak_q_alpha": SILO_Q_ALPHA,
            "kick_regime": "at_first_lit_instant",
        }
        metrics["comparison"]["sled"] = dict(metrics["comparison"]["silo"])

    _amend_metrics(run_dir, add_sled)

    def sled_config(config: dict[str, Any]) -> None:
        config["runs"]["sled"] = _run_config(True)
        config["runs"]["sled"]["run"]["assist"].update(model="linear_motor", carriage_mass_t=22)

    _amend_config(run_dir, sled_config)
    mixed = _drive(run_dir, ["pad", "silo", "silo_step", "sled"])
    assert mixed.startswith(
        "The drive is a prescribed 3 g push with no force or power limit (silo) and a prescribed "
        "1.5 g push with no force or power limit (silo_step), the carriage is massless (silo), "
        "the shaft has no air drag and the pitch kick has no aerodynamic penalty. Under the "
        "prescribed drives of silo and silo_step the release speed and the payload do not depend "
    )
    assert "For sled (linear_motor drive) the missing shaft drag changes" in mixed


def test_offload_run_shown_adds_the_offload_to_the_invariants(tmp_path: Path) -> None:
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)
    text = _drive(run_dir, ["pad", "silo_s1"])
    assert (
        "Under this drive the release speed, the payload and the offload do not depend on "
        "the carriage mass or the shaft drag"
    ) in text
    assert "the release speed and the payload do not" in _drive(run_dir, ["pad", "silo"])


def test_a_page_of_the_22_t_sled_alone_does_not_say_massless(tmp_path: Path) -> None:
    """The gate of design 4.3: a page whose only pushed run carries a 22 t carriage
    (metric and config agree) has no "massless" anywhere; its drive caveat keeps the
    invariants and the shaft clause, and the interface force is biased by the shaft drag
    only."""
    run_dir = _make_dir(tmp_path)
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].update(carriage_mass_kg=SLED_CARRIAGE_KG))
    _amend_config(run_dir, lambda c: c["runs"]["silo"]["run"]["assist"].update(carriage_mass_t=22))
    page = replay.write_replay_page(run_dir, ["pad", "silo"], tmp_path / "sled.html")
    html = page.read_text(encoding="utf-8")
    assert "massless" not in html
    text = _drive(run_dir, ["pad", "silo"])
    assert text.startswith(
        "The drive is a prescribed 3 g push with no force or power limit, the shaft has no "
        "air drag and the pitch kick has no aerodynamic penalty. Under this drive the release "
        "speed and the payload do not depend on the carriage mass or the shaft drag: the "
        "missing shaft drag biases the drive energy, peak power and interface force low."
    )
    assert "22 t carriage" in replay.replay_data(run_dir, ["pad", "silo"])["runs"][1]["detail"]


def test_carriage_mass_reads_the_metric_first_then_the_config(tmp_path: Path) -> None:
    run_dir = _make_dir(tmp_path)
    # the metric wins over a config key that disagrees
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].update(carriage_mass_kg=SLED_CARRIAGE_KG))
    assert "massless" not in _drive(run_dir, ["pad", "silo"])
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].update(carriage_mass_kg=0.0))
    _amend_config(run_dir, lambda c: c["runs"]["silo"]["run"]["assist"].update(carriage_mass_t=22))
    assert "the carriage is massless" in _drive(run_dir, ["pad", "silo"])
    # no metric (older results): the config key
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].pop("carriage_mass_kg"))
    assert "massless" not in _drive(run_dir, ["pad", "silo"])
    _amend_config(run_dir, lambda c: c["runs"]["silo"]["run"]["assist"].update(carriage_mass_t=0))
    assert "the carriage is massless" in _drive(run_dir, ["pad", "silo"])
    assert replay.carriage_mass_kg({"carriage_mass_t": 22}, {"carriage_mass_kg": 0.0}) == 0.0
    assert replay.carriage_mass_kg({"carriage_mass_t": 22}, {}) == pytest.approx(22_000.0)
    assert replay.carriage_mass_kg({}, {}) is None


def test_kick_clause_says_the_opposite_below_the_baseline_and_omits_a_run_without_a_kick(
    tmp_path: Path,
) -> None:
    """silo's peak q-alpha set below the pad's: the kick does not favour it; beside
    silo_step (above): both are named on their own side; a failed ignition (kick regime
    none, status impact) is left out of the kick sentence, and the sentence is dropped
    when no shown run kicked or the baseline has no peak q-alpha."""
    run_dir = _make_dir(tmp_path)
    below = PAD_Q_ALPHA - 10.0
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].update(peak_q_alpha=below))
    assert _kick_sentence(_drive(run_dir, ["pad", "silo"])) == (
        f"The free kick does not favour silo, whose peak q-alpha is below the baseline pad's "
        f"({below:.1f} against {PAD_Q_ALPHA:.1f} Pa rad)."
    )
    assert _kick_sentence(_drive(run_dir, ["pad", "silo", "silo_step"])) == (
        f"The free kick favours silo_step, whose peak q-alpha is above the baseline pad's "
        f"({STEP_Q_ALPHA:.1f} against {PAD_Q_ALPHA:.1f} Pa rad), and does not favour silo, "
        f"whose peak q-alpha is below it ({below:.1f} Pa rad)."
    )
    # equal to the baseline's: not above, never called below
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].update(peak_q_alpha=PAD_Q_ALPHA))
    sentence = _kick_sentence(_drive(run_dir, ["pad", "silo"]))
    assert sentence is not None and "is not above the baseline pad's" in sentence
    assert "below" not in sentence

    _amend_metrics(run_dir, _fail_silo)
    assert _kick_sentence(_drive(run_dir, ["pad", "silo"])) is None
    sentence = _kick_sentence(_drive(run_dir, ["pad", "silo", "silo_step"]))
    assert sentence is not None and "silo_step" in sentence
    assert re.search(r"\bsilo\b", sentence) is None  # the failed run is not on either side
    # a baseline without the metric: nothing can be said
    _amend_metrics(run_dir, lambda m: m["runs"]["pad"].pop("peak_q_alpha"))
    assert _kick_sentence(_drive(run_dir, ["pad", "silo_step"])) is None


PAIRED_Q_ALPHA = 150.0
"""Peak q-alpha [Pa rad] given to the fixture's paired baseline pad__aero_bound: above
silo__aero_bound's SILO_Q_ALPHA while the experiment baseline's PAD_Q_ALPHA is below it,
so the two partners give opposite verdicts."""


def test_kick_clause_judges_a_bound_re_run_against_its_paired_baseline(tmp_path: Path) -> None:
    """A bound re-run is compared with its paired baseline, which carries the same
    override (the comparison caveat says so), so its kick verdict reads that run's peak
    q-alpha from the bounds record, not the experiment baseline's: with the paired
    baseline's peak above silo__aero_bound's the kick does not favour it, although it
    would against pad; beside silo the two verdicts stand side by side, each naming its
    partner; a paired baseline without the metric drops the bound run from the sentence;
    the paired baseline need not be on the page."""
    run_dir = _make_dir(tmp_path)

    def kicks(metrics: dict[str, Any]) -> None:
        bound = metrics["bounds"][0]
        bound["metrics"].update(peak_q_alpha=SILO_Q_ALPHA, kick_regime="at_first_lit_instant")
        bound["paired_baseline_metrics"].update(peak_q_alpha=PAIRED_Q_ALPHA)

    _amend_metrics(run_dir, kicks)
    assert _kick_sentence(_drive(run_dir, ["pad__aero_bound", "silo__aero_bound"])) == (
        f"The free kick does not favour silo__aero_bound, whose peak q-alpha is below its paired "
        f"baseline pad__aero_bound's ({SILO_Q_ALPHA:.1f} against {PAIRED_Q_ALPHA:.1f} Pa rad)."
    )
    assert _kick_sentence(_drive(run_dir, ["pad", "silo", "silo__aero_bound"])) == (
        f"The free kick favours silo, whose peak q-alpha is above the baseline pad's "
        f"({SILO_Q_ALPHA:.1f} against {PAD_Q_ALPHA:.1f} Pa rad), and does not favour "
        f"silo__aero_bound, whose peak q-alpha is below its paired baseline pad__aero_bound's "
        f"({SILO_Q_ALPHA:.1f} against {PAIRED_Q_ALPHA:.1f} Pa rad)."
    )
    alone = _kick_sentence(_drive(run_dir, ["silo__aero_bound"]))
    assert alone is not None and "its paired baseline pad__aero_bound's" in alone
    assert "the baseline pad's" not in alone
    # the paired baseline's peak below the bound run's: favoured, against that partner
    _amend_metrics(
        run_dir, lambda m: m["bounds"][0]["paired_baseline_metrics"].update(peak_q_alpha=100.0)
    )
    assert _kick_sentence(_drive(run_dir, ["silo__aero_bound"])) == (
        f"The free kick favours silo__aero_bound, whose peak q-alpha is above its paired "
        f"baseline pad__aero_bound's ({SILO_Q_ALPHA:.1f} against 100.0 Pa rad)."
    )
    # no peak q-alpha on the paired baseline: nothing is said about the bound run
    _amend_metrics(run_dir, lambda m: m["bounds"][0]["paired_baseline_metrics"].pop("peak_q_alpha"))
    assert _kick_sentence(_drive(run_dir, ["pad", "silo__aero_bound"])) is None
    sentence = _kick_sentence(_drive(run_dir, ["pad", "silo", "silo__aero_bound"]))
    assert sentence is not None and "aero_bound" not in sentence
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    config = yaml.safe_load((run_dir / "resolved_config.yaml").read_text(encoding="utf-8"))
    source = replay.run_source(metrics, config, "silo__aero_bound")
    partner = replay.kick_partner("silo__aero_bound", source, metrics)
    assert partner == ("pad__aero_bound", True, None)
    assert replay.kick_partner("silo", replay.run_source(metrics, config, "silo"), metrics) == (
        "pad",
        False,
        PAD_Q_ALPHA,
    )
    assert replay.paired_baseline_metrics(metrics, "silo") == {}


def _fail_silo(metrics: dict[str, Any]) -> None:
    """Make the fixture's silo a failed ignition, as the recorded silo_failed is: status
    impact, no kick, peak q-alpha 0, no payload."""
    metrics["runs"]["silo"].update(
        status="impact", kick_regime="none", peak_q_alpha=0.0, kick_t_s=None, payload_kg=None
    )


def test_a_run_that_never_kicked_gets_no_kick_clause_and_no_payload_invariant(
    tmp_path: Path,
) -> None:
    """The failed run alone: the first sentence has no kick clause (its stage 1 never
    lit, so the model's free kick never happened) and the invariant names the release
    speed only (the run has no payload). Beside silo_step the kick clause names
    silo_step, like every other per-run part, and the payload is back."""
    run_dir = _make_dir(tmp_path)
    _amend_metrics(run_dir, _fail_silo)
    alone = _drive(run_dir, ["silo"])
    assert alone == (
        "The drive is a prescribed 3 g push with no force or power limit, the carriage is "
        "massless and the shaft has no air drag. Under this drive the release speed does not "
        "depend on the carriage mass or the shaft drag: the massless carriage biases the drive "
        "energy and peak power low, and the missing shaft drag biases the drive energy, peak "
        "power and interface force low."
    )
    assert "kick" not in alone and "payload" not in alone
    beside = _drive(run_dir, ["pad", "silo", "silo_step"])
    assert "the pitch kick has no aerodynamic penalty (silo_step)." in beside
    assert "Under this drive the release speed and the payload do not depend" in beside
    # every pushed run kicked: the clause names none of them
    assert "no aerodynamic penalty." in _drive(_make_dir(tmp_path / "all"), ["pad", "silo"])


def test_kicked_reads_the_regime_then_the_kick_time() -> None:
    assert replay.kicked({"kick_regime": "after_vertical_rise"})
    assert replay.kicked({"kick_regime": "at_first_lit_instant", "kick_t_s": None})
    assert not replay.kicked({"kick_regime": "none", "kick_t_s": 3.0})
    assert replay.kicked({"kick_t_s": 12.5})  # results written before kick_regime
    assert not replay.kicked({"kick_t_s": None}) and not replay.kicked({})


def test_a_force_limited_drive_gets_no_invariant_and_no_bias_clause(tmp_path: Path) -> None:
    """Under a drive other than constant_accel the release speed does depend on the
    carriage mass and the shaft drag, so neither the invariant sentence nor the bias
    clauses (RQ3-silo-screening-2d establishes the biases for the prescribed drive only)
    are written: the omissions are said to change the release speed and the payload by a
    size not established here. Beside a prescribed push the invariant and the biases are
    scoped to that run; the massless-carriage bias names no run, since the only
    prescribed run is the one it holds for."""
    run_dir = _make_dir(tmp_path)
    _amend_config(
        run_dir, lambda c: c["runs"]["silo"]["run"]["assist"].update(model="linear_motor")
    )
    text = _drive(run_dir, ["pad", "silo"])
    assert text.startswith(
        "The carriage is massless, the shaft has no air drag and the pitch kick has no "
        "aerodynamic penalty. For silo (linear_motor drive) the massless carriage and the "
        "missing shaft drag change the release speed and the payload; their size is not "
        "established here. The free kick favours silo"
    )
    assert "Under" not in text and "prescribed" not in text and "biases" not in text
    mixed = _drive(run_dir, ["pad", "silo", "silo_step"])
    assert (
        "Under the prescribed drive of silo_step the release speed and the payload do not "
        "depend on the carriage mass or the shaft drag: the missing shaft drag biases the drive "
        "energy, peak power and interface force low. For silo (linear_motor drive) the massless "
        "carriage and the missing shaft drag change the release speed and the payload; their "
        "size is not established here."
    ) in mixed
    assert "Under this drive" not in mixed and "massless carriage biases" not in mixed
    # a 22 t carriage under the other drive: only the shaft drag is left out
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].update(carriage_mass_kg=SLED_CARRIAGE_KG))
    text = _drive(run_dir, ["pad", "silo"])
    assert (
        "For silo (linear_motor drive) the missing shaft drag changes the release speed and "
        "the payload; its size is not established here."
    ) in text
    assert "massless" not in text


# ---------------------------------------------------------------- the structure caveat


def test_structure_caveat_names_each_runs_own_load_and_peak_g(tmp_path: Path) -> None:
    run_dir = _make_dir(tmp_path)
    _amend_metrics(run_dir, lambda m: m["runs"]["silo_step"].update(felt_g_track_peak=2.5))
    text = next(c for c in _caveats(run_dir, ["pad", "silo", "silo_step"]) if "structural" in c)
    assert text.startswith(
        "No structural mass is charged for the assist load case: silo (574.0 t at push start) "
        "feels up to 4.0 g and silo_step (579.0 t at push start) up to 2.5 g during the push."
    )
    assert "fully fuelled" not in text and "would cancel the gain" in text
    _amend_metrics(run_dir, lambda m: m["runs"]["silo_step"].update(felt_g_track_peak=4.0))
    text = next(c for c in _caveats(run_dir, ["pad", "silo", "silo_step"]) if "structural" in c)
    assert (
        "silo (574.0 t at push start) and silo_step (579.0 t at push start) feel up to 4.0 g"
    ) in text
    # no liftoff metric (older results): the name alone
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].pop("liftoff_mass_kg"))
    text = next(c for c in _caveats(run_dir, ["pad", "silo"]) if "structural" in c)
    assert "load case: silo feels up to 4.0 g during the push." in text


HOLD_BURN_KG = 2697.5
"""Propellant the recorded hot starts burn while held (pad, silo_hot_full: metrics.json
``hold_propellant_burned_kg`` of results/silo_screening_2d/20260930T175743Z)."""


def test_structure_caveat_gives_the_stack_at_push_start_for_a_held_hot_start(
    tmp_path: Path,
) -> None:
    """A run lit and held at the track start before the push (silo_hot_full) burns
    ``hold_propellant_burned_kg`` before the push begins, so the load it carries up the
    track is the liftoff mass less that burn (571.1 t for the recorded 573.8 t stack), not
    the pre-ignition ``liftoff_mass_kg``; a cold start or a run lit during the push (no
    hold) keeps its liftoff mass, and a zero or missing hold burn changes nothing."""
    run_dir = _make_dir(tmp_path)
    held = {
        "hold_duration_s": 2.6,
        "hold_propellant_burned_kg": HOLD_BURN_KG,
        "t_ign_rel_release_s_stage1": -4.6,
    }
    _amend_metrics(run_dir, lambda m: m["runs"]["silo"].update(held))
    text = next(c for c in _caveats(run_dir, ["pad", "silo", "silo_step"]) if "structural" in c)
    assert text.startswith(
        "No structural mass is charged for the assist load case: silo (571.3 t at push start) "
        "and silo_step (579.0 t at push start) feel up to 4.0 g during the push."
    )
    assert "574.0 t" not in text
    for burn in (0.0, None):
        _amend_metrics(
            run_dir, lambda m, b=burn: m["runs"]["silo"].update(hold_propellant_burned_kg=b)
        )
        text = next(c for c in _caveats(run_dir, ["pad", "silo"]) if "structural" in c)
        assert "silo (574.0 t at push start) feels up to 4.0 g" in text


def test_structure_caveat_names_an_offload_runs_offload(tmp_path: Path) -> None:
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)
    text = next(c for c in _caveats(run_dir, ["pad", "silo_s1"]) if "structural" in c)
    assert text == (
        "No structural mass is charged for the assist load case: silo_s1 (532.7 t at push "
        "start, 41.26 t less propellant) feels up to 4.0 g during the push."
    )


PENALTY_KG = 8100.0
PENALTY_OFFLOAD_KG = 1980.5
SECOND_PENALTY_KG = 2000.0
SECOND_PENALTY_OFFLOAD_KG = 32_285.2
"""The +8.1 t and +2 t penalty rows of results/silo_offload_2d/20261003T112934Z
(RQ1-fuel-offload-2d, 'Structural penalty rows and break-even'): the assumed stage-1 dry
mass each charges on its run and the offload each still carries."""


def _add_penalty_rows(run_dir: Path) -> None:
    """Add, after ``_add_offload``, the penalty rows silo_s1_dry (PENALTY_KG of assumed
    stage-1 dry mass, PENALTY_OFFLOAD_KG removed) and silo_s1_dry2 (SECOND_PENALTY_KG,
    SECOND_PENALTY_OFFLOAD_KG), stage-1 solves of silo flying P_REF_KG, as the shipped
    metrics.json records them (``stage1_dry_mass_added_kg`` and ``assumed_penalty``)."""
    rows = (
        ("silo_s1_dry", PENALTY_KG, PENALTY_OFFLOAD_KG),
        ("silo_s1_dry2", SECOND_PENALTY_KG, SECOND_PENALTY_OFFLOAD_KG),
    )
    for name, _, _ in rows:
        _write_run(run_dir, name, True)

    def change(metrics: dict[str, Any]) -> None:
        offload = metrics["offload"]
        for name, added_kg, removed_kg in rows:
            offload["cases"].append(
                {
                    "name": name,
                    "run": name,
                    "of": "silo",
                    "kind": "solve",
                    "mode": "stage1",
                    "status": "ok",
                    "total_offload_kg": removed_kg,
                    "quoted_offload_kg": removed_kg,
                    "stage1_dry_mass_added_kg": added_kg,
                    "assumed_penalty": True,
                    "stage1_fraction": removed_kg / 410_900.0,
                    "stage2_fraction": 0.0,
                    "total_fraction": removed_kg / 518_400.0,
                    "payload_kg": P_REF_KG,
                    "paired_pad": None,
                    "flags": [],
                }
            )
            record = _pushed_offload_run(P_REF_KG, removed_kg)
            record["liftoff_mass_kg"] += added_kg
            offload["runs"][name] = record

    _amend_metrics(run_dir, change)
    _amend_config(
        run_dir,
        lambda c: c["offload_runs"].update({name: _run_config(True) for name, _, _ in rows}),
    )


def test_structure_caveat_says_what_a_penalty_row_charges(tmp_path: Path) -> None:
    """A penalty row charges an assumed stage-1 dry mass on its run (its record's
    ``stage1_dry_mass_added_kg`` > 0, ``assumed_penalty`` true), so the caveat must not
    open 'No structural mass is charged' for it: it says the assumed mass is charged, an
    assumption and not a sized structure, and that no structural model exists, with the
    run's own load and peak g; the uncharged sentence stays, word for word, for the runs
    without a penalty, and is dropped when every pushed run shown is a penalty row. The
    row's note names the penalty beside how the propellant was taken out."""
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)
    _add_penalty_rows(run_dir)
    both = next(c for c in _caveats(run_dir, ["pad", "silo_s1", "silo_s1_dry"]) if "structur" in c)
    assert both == (
        "No structural mass is charged for the assist load case: silo_s1 (532.7 t at push "
        "start, 41.26 t less propellant) feels up to 4.0 g during the push. An assumed +8.1 t of "
        "stage-1 dry mass is charged on silo_s1_dry (580.1 t at push start, 1.98 t less "
        "propellant, up to 4.0 g during the push): a parametric assumption, not a sized "
        "structure; no structural model exists."
    )
    alone = next(c for c in _caveats(run_dir, ["pad", "silo_s1_dry"]) if "structur" in c)
    assert alone == (
        "An assumed +8.1 t of stage-1 dry mass is charged on silo_s1_dry (580.1 t at push "
        "start, 1.98 t less propellant, up to 4.0 g during the push): a parametric assumption, "
        "not a sized structure; no structural model exists."
    )
    assert "No structural mass" not in alone
    two = next(c for c in _caveats(run_dir, ["silo_s1_dry", "silo_s1_dry2"]) if "structur" in c)
    assert two == (
        "An assumed +8.1 t of stage-1 dry mass is charged on silo_s1_dry (580.1 t at push "
        "start, 1.98 t less propellant, up to 4.0 g during the push) and an assumed +2 t of "
        "stage-1 dry mass on silo_s1_dry2 (543.7 t at push start, 32.29 t less propellant, up "
        "to 4.0 g during the push): parametric assumptions, not sized structures; no "
        "structural model exists."
    )
    detail = replay.replay_data(run_dir, ["pad", "silo_s1_dry"])["runs"][1]["detail"]
    assert detail.startswith(
        "offload case silo_s1_dry of silo: 1.98 t less propellant (solved with an assumed "
        "+8.1 t of stage-1 dry mass; 0.48% of the stage-1 load, 0.38% of all), flying 1,000.0 kg"
    )
    assert "assumed" not in replay.replay_data(run_dir, ["pad", "silo_s1"])["runs"][1]["detail"]
    # the record alone: the mass, a penalty of unrecorded size, no penalty
    assert replay.penalty_added_kg({"stage1_dry_mass_added_kg": 8100.0}) == 8100.0
    unrecorded = {"stage1_dry_mass_added_kg": 0.0, "assumed_penalty": True}
    assert replay.penalty_added_kg(unrecorded) == 0.0
    assert replay.penalty_added_kg({**unrecorded, "assumed_penalty": False}) is None
    assert replay.penalty_added_kg({}) is None
    assert replay.penalty_mass_text(0.0) == "stage-1 dry mass of unrecorded size"
    assert replay.penalty_mass_text(2000.0) == "+2 t of stage-1 dry mass"
    assert replay.penalty_clause({"assumed_penalty": True}) == (
        " with an assumed stage-1 dry mass of unrecorded size"
    )
    assert replay.penalty_clause({"kind": "solve"}) == ""


def test_offload_note_says_when_the_solve_found_no_offload_or_failed() -> None:
    """A solved case whose solve ended no_offload (its recorded run is the one at x = 0)
    or search_failed never reads like a successful solve of 0.00 t: the note gives the
    outcome and the status (and the failure kind when recorded), no amount, shares or
    quoted figure; its flags still count. A fixed case and an ok solve are untouched."""
    base = {"name": "s", "run": "s", "of": "silo", "kind": "solve", "mode": "stage1"}
    none_found = {
        **base,
        "status": "no_offload",
        "total_offload_kg": 0.0,
        "quoted_offload_kg": 0.0,
        "stage1_fraction": 0.0,
        "stage2_fraction": 0.0,
        "total_fraction": 0.0,
        "payload_kg": P_REF_KG,
        "flags": ["offload: x"],
    }
    offload = {"reference_payload_kg": P_REF_KG, "cases": [none_found], "runs": {}}
    note = replay.replay_offload_note(offload, "s", "pad")
    assert note == (
        "offload case s of silo: the solve found no offload (status no_offload), its recorded "
        "run at x = 0 flying 1,000.0 kg against pad's full load at P_ref = 1,000.0 kg, the same "
        "orbit; 1 flag (summary.md, Flags)"
    )
    assert "0.00 t" not in note and "solved" not in note and "0.00%" not in note
    # a stage-2 no_offload beside a pad control: nothing is quoted net of it
    netted = {**none_found, "mode": "stage2", "pad_control_offload_kg": 500.0, "flags": []}
    offload = {
        "reference_payload_kg": P_REF_KG,
        "cases": [netted],
        "pad_controls": [{"mode": "stage2", "run": "p", "offload_kg": 500.0, "flags": ["x"]}],
        "runs": {},
    }
    note = replay.replay_offload_note(offload, "s", "pad")
    assert "net of" not in note and "uncertain" not in note and "found no offload" in note
    failed = {
        **base,
        "status": "search_failed",
        "total_offload_kg": None,
        "quoted_offload_kg": None,
        "quoted_basis": "not quoted: the case's own solve did not end ok, so it has no x* to quote",
        "solve": {"status": "search_failed", "failure_kind": "edge"},
        "payload_kg": None,
        "flags": [],
    }
    offload = {"reference_payload_kg": P_REF_KG, "cases": [failed], "runs": {}}
    assert replay.replay_offload_note(offload, "s", "pad") == (
        "offload case s of silo: the solve failed (status search_failed: edge) against pad's "
        "full load at P_ref = 1,000.0 kg, the same orbit"
    )
    assert replay.solve_outcome({**failed, "solve": None}) == (
        "the solve failed (status search_failed)"
    )
    assert replay.solve_outcome({**base, "status": "odd"}) == (
        "the solve did not end ok (status odd)"
    )
    assert replay.solve_outcome({**base, "status": "ok"}) is None
    assert replay.solve_outcome(base) is None
    assert replay.solve_outcome({**base, "kind": "fixed", "status": "search_failed"}) is None
    # a no_offload case's flown load names no propellant carried less
    run = {"key": "s", "felt_g_track": 4.0}
    source = {"metrics": {"liftoff_mass_kg": 574_000.0}, "offload_kind": run_data.OFFLOAD_CASE}
    block = {"cases": [none_found]}
    assert replay.flown_load_text(run, source, block) == "s (574.0 t at push start)"


# ---------------------------------------------------------------- offload runs


def test_paired_pad_label_note_and_comparison_caveat(tmp_path: Path) -> None:
    """The paired pad is labelled by its kind and said to fly its own payload capacity
    (the recorded payload) against P_ref; the case's note carries two decimals; the pad
    control is labelled too; the comparison caveat tells the three apart."""
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    config = yaml.safe_load((run_dir / "resolved_config.yaml").read_text(encoding="utf-8"))
    kinds = {
        name: replay.run_source(metrics, config, name)["offload_kind"]
        for name in ("pad", "silo_s1", "silo_s1__pad", "pad__offload_stage1", "silo_fix")
    }
    assert kinds == {
        "pad": None,
        "silo_s1": run_data.OFFLOAD_CASE,
        "silo_s1__pad": run_data.OFFLOAD_PAIRED_PAD,
        "pad__offload_stage1": run_data.OFFLOAD_PAD_CONTROL,
        "silo_fix": run_data.OFFLOAD_CASE,
    }
    data = replay.replay_data(run_dir, ["pad", "silo_s1", "silo_s1__pad", "pad__offload_stage1"])
    runs = {r["key"]: r for r in data["runs"]}
    assert runs["silo_s1"]["label"] == "silo_s1 (offload)"
    assert runs["silo_s1__pad"]["label"] == "silo_s1__pad (paired pad)"
    assert runs["pad__offload_stage1"]["label"] == "pad__offload_stage1 (pad control)"
    assert runs["silo_s1__pad"]["detail"].startswith(
        "paired pad of offload case silo_s1: pad with the same 41.26 t stage-1 offload and no "
        "push, flying its own payload capacity, 958.6 kg (41.4 kg short of P_ref = 1,000.0 kg); "
    )
    assert runs["silo_s1__pad"]["payload_kg"] == pytest.approx(PAIRED_PAD_KG)
    assert runs["silo_s1"]["detail"].startswith(
        "offload case silo_s1 of silo: 41.26 t less propellant (solved; 10.04% of the stage-1 "
        "load, 7.96% of all), flying 1,000.0 kg against pad's full load at P_ref = 1,000.0 kg, "
        "the same orbit; "
    )
    assert "41.3 t" not in runs["silo_s1"]["detail"] and "10.0%" not in runs["silo_s1"]["detail"]
    assert "net of" not in runs["silo_s1"]["detail"]  # stage 1 is quoted gross, the headline
    # a control record with the status alone (older results): the status, no amount
    assert runs["pad__offload_stage1"]["detail"].startswith(
        "pad control (stage1): pad's own offload at P_ref = 1,000.0 kg: none found (status "
        "no_offload); "
    )
    caveat = next(c for c in data["meta"]["caveats"] if "offload block" in c)
    assert caveat == (
        "silo_s1, silo_s1__pad and pad__offload_stage1 are runs of the offload block, not "
        "compared with pad here. silo_s1 and pad__offload_stage1 fly P_ref = 1,000.0 kg and "
        "measure propellant saved at the same payload and orbit, not a payload change "
        "(summary.md, 'Propellant saved at fixed payload', with its caveats). silo_s1__pad is "
        "the paired pad (pad with the same offload and no push), flies its own payload "
        "capacity and measures a payload change (its payload against P_ref = 1,000.0 kg), not "
        "propellant saved. pad__offload_stage1 is pad's own pad control at P_ref, what the pad "
        "alone saves without a push (summary.md, 'Pad controls'): none found (status "
        "no_offload)."
    )
    page = replay.write_replay_page(run_dir, ["silo_s1__pad", "silo_s1"], tmp_path / "p.html")
    html = page.read_text(encoding="utf-8")
    assert "(paired pad)" in html and "propellant saved at the same payload" in html


def test_stage1_pad_control_says_what_it_found(tmp_path: Path) -> None:
    """The recorded stage-1 control of RQ1 (x_pad = 0, m_res(0) = -0.0016 kg, a
    resolution effect, consistency pass) is reported as such, not as a failure, in the
    note and in the comparison caveat; a pad control with a flag names it in the note."""
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)

    def recorded(metrics: dict[str, Any]) -> None:
        metrics["offload"]["pad_controls"][0].update(
            offload_kg=0.0,
            m_res_kg=-0.0016376905186916701,
            resolution_effect=True,
            consistency="pass",
            flags=[],
        )

    _amend_metrics(run_dir, recorded)
    data = replay.replay_data(run_dir, ["pad", "pad__offload_stage1"])
    found = (
        "none found (status no_offload, consistency pass; its recorded run at x = 0 ends 0.0016 "
        "kg short, a resolution effect)"
    )
    assert data["runs"][1]["detail"].startswith(
        f"pad control (stage1): pad's own offload at P_ref = 1,000.0 kg: {found}; "
    )
    caveat = next(c for c in data["meta"]["caveats"] if "offload block" in c)
    assert caveat.endswith(
        f"pad__offload_stage1 is pad's own pad control at P_ref, what the pad alone saves "
        f"without a push (summary.md, 'Pad controls'): {found}."
    )
    assert "did not reach orbit" not in " ".join(data["meta"]["caveats"])  # status inserted here
    assert replay.pad_control_result({"mode": "stage1"}) is None
    flagged = {"status": "ok", "offload_kg": 513.6, "flags": ["x"]}
    assert replay.pad_control_result(flagged) == "0.51 t (status ok); 1 flag (summary.md, Flags)"
    assert replay.pad_control_result(flagged, with_flags=False) == "0.51 t (status ok)"


def test_stage2_case_is_worded_as_net_of_the_pad_control_with_its_verdicts(
    tmp_path: Path,
) -> None:
    """A stage-2 solve names its stage (never '0.00% of the stage-1 load'), gives the
    gross removal, then the quoted figure net of the pad control as a property of the
    vehicle model, its failed verification as a lower bound on the gross removal (the
    verdict is on x*, RQ1-fuel-offload-2d 'Verification'; never on the net figure, which
    subtracts a flagged pad control and is uncertain both ways) and its flag count; its
    pad control gives its amount; the comparison caveat never calls it 'propellant saved'
    (the design's exit criterion 7)."""
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)
    _add_netted_cases(run_dir)
    data = replay.replay_data(run_dir, ["pad", "silo_s2", "pad__offload_stage2"])
    runs = {r["key"]: r for r in data["runs"]}
    assert runs["silo_s2"]["label"] == "silo_s2 (offload)"
    assert runs["silo_s2"]["detail"].startswith(
        "offload case silo_s2 of silo: 31.90 t less stage-2 propellant (solved; 29.68% of the "
        "stage-2 load, 6.15% of all), flying 1,000.0 kg against pad's full load at P_ref = "
        "1,000.0 kg, the same orbit; quoted 31.39 t net of the pad control's 0.51 t "
        "(summary.md basis row: a property of the vehicle model, not of the assist); "
        "verification failed (+15.36 kg against 2.6 kg): the gross removal is a flagged lower "
        "bound and the net figure, which also subtracts a flagged pad control, is uncertain "
        "both ways; 4 flags (summary.md, Flags); "
    )
    assert "0.00% of the stage-1 load" not in runs["silo_s2"]["detail"]
    assert not re.search(r"net [^;]*: a flagged lower bound", runs["silo_s2"]["detail"])
    assert "): a flagged lower bound" not in runs["silo_s2"]["detail"]
    assert runs["pad__offload_stage2"]["detail"].startswith(
        "pad control (stage2): pad's own offload at P_ref = 1,000.0 kg: 0.51 t (status ok); "
        "1 flag (summary.md, Flags); "
    )
    caveat = next(c for c in data["meta"]["caveats"] if "offload block" in c)
    assert caveat == (
        "silo_s2 and pad__offload_stage2 are runs of the offload block, not compared with pad "
        "here. pad__offload_stage2 flies P_ref = 1,000.0 kg and measures propellant saved at the "
        "same payload and orbit, not a payload change (summary.md, 'Propellant saved at fixed "
        "payload', with its caveats). silo_s2 flies P_ref = 1,000.0 kg and measures propellant "
        "the vehicle model does without, quoted net of the pad control as a property of the "
        "model's stage-2 sizing and guidance, not the assist's stage-1 headline (summary.md, "
        "basis row, with its caveats). pad__offload_stage2 is pad's own pad control at P_ref, "
        "what the pad alone saves without a push (summary.md, 'Pad controls'): 0.51 t (status "
        "ok)."
    )
    alone = next(c for c in _caveats(run_dir, ["pad", "silo_s2"]) if "offload block" in c)
    assert "propellant saved" not in alone and alone.startswith(
        "silo_s2 is a run of the offload block, not compared with pad here: it flies P_ref = "
        "1,000.0 kg and measures propellant the vehicle model does without, quoted net"
    )
    # the structure caveat keeps the physical load the run flew
    structure = next(c for c in _caveats(run_dir, ["pad", "silo_s2"]) if "structural" in c)
    assert "silo_s2 (542.1 t at push start, 31.90 t less propellant)" in structure


def test_both_stage_and_frontier_cases(tmp_path: Path) -> None:
    """A both-stage solve names both shares and is quoted net of a 0 t pad control
    (still a property of the vehicle model, D-SP1-10) with a passed verification and no
    flags said nothing about; a stage-1 solve with a stage-2 pre-offload says what was
    solved and what was imposed, and stays a gross stage-1 figure in the caveat."""
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)
    _add_netted_cases(run_dir)
    data = replay.replay_data(run_dir, ["pad", "silo_both", "pad__offload_both", "silo_pre"])
    runs = {r["key"]: r for r in data["runs"]}
    assert runs["silo_both"]["detail"].startswith(
        "offload case silo_both of silo: 46.17 t less propellant (solved; 8.91% of the stage-1 "
        "and 8.91% of the stage-2 load, 8.91% of all), flying 1,000.0 kg against pad's full "
        "load at P_ref = 1,000.0 kg, the same orbit; quoted 46.17 t net of the pad control's "
        "0.00 t (summary.md basis row: a property of the vehicle model, not of the assist); "
    )
    assert "verification" not in runs["silo_both"]["detail"]
    assert "flag" not in runs["silo_both"]["detail"]
    assert runs["pad__offload_both"]["detail"].startswith(
        "pad control (both): pad's own offload at P_ref = 1,000.0 kg: 0.00 t (status ok); "
    )
    assert runs["silo_pre"]["detail"].startswith(
        "offload case silo_pre of silo: 42.77 t less propellant (40.77 t solved on stage 1 plus "
        "2.00 t imposed on stage 2; 9.92% of the stage-1 and 1.86% of the stage-2 load, 8.25% "
        "of all), flying 1,000.0 kg against pad's full load at P_ref = 1,000.0 kg, the same "
        "orbit; "
    )
    assert "net of" not in runs["silo_pre"]["detail"]
    caveat = next(c for c in data["meta"]["caveats"] if "offload block" in c)
    assert "pad__offload_both and silo_pre fly P_ref = 1,000.0 kg and measure propellant saved" in (
        caveat
    )
    assert "silo_both flies P_ref = 1,000.0 kg and measures propellant the vehicle model" in caveat
    assert caveat.endswith(
        "pad__offload_both is pad's own pad control at P_ref, what the pad alone saves without "
        "a push (summary.md, 'Pad controls'): 0.00 t (status ok)."
    )


def test_offload_note_helpers_fall_back_without_the_keys() -> None:
    """Records from before the stage-2 fraction, the quoted figure or the verification
    were written keep the stage-1 wording and add nothing; a record whose basis says it
    is not quoted carries that basis verbatim."""
    solve = {"kind": "solve", "mode": "stage2", "total_offload_kg": 3000.0}
    assert replay.offload_stage_word(solve) is None
    assert replay.offload_shares(solve) == ""
    assert replay.offload_how(solve, 3000.0) == "solved"
    assert replay.offload_quoted_clause(solve) == ""
    assert replay.offload_verdict_clause(solve) == ""
    assert replay.offload_quoted_clause({**solve, "quoted_basis": "not quoted: no control"}) == (
        "; not quoted: no control"
    )
    assert replay.offload_quoted_clause({**solve, "quoted_offload_kg": 2500.0}) == (
        "; quoted 2.50 t net of the pad control (summary.md basis row: a property of the "
        "vehicle model, not of the assist)"
    )
    assert replay.offload_quoted_clause({**solve, "mode": "stage1", "quoted_offload_kg": 1.0}) == ""
    assert replay.offload_quoted_clause({**solve, "kind": "fixed", "quoted_offload_kg": 1.0}) == ""
    # the frontier split read from the quoted figure when the pre-offload key is absent
    frontier = {"kind": "solve", "mode": "stage1", "quoted_offload_kg": 40_000.0}
    assert replay.offload_how(frontier, 42_000.0) == (
        "40.00 t solved on stage 1 plus 2.00 t imposed on stage 2"
    )
    assert replay.offload_how({"kind": "fixed"}, 1.0) == "imposed"
    assert replay.offload_shares({"stage1_fraction": 0.1, "total_fraction": 0.08}) == (
        "; 10.00% of the stage-1 load, 8.00% of all"
    )
    assert replay.offload_shares({"stage2_fraction": 0.3, "total_fraction": 0.06}) == (
        "; 30.00% of the stage-2 load, 6.00% of all"
    )
    assert replay.offload_verdict_clause({"verification": {"passed": False}}) == (
        "; verification failed: the gross removal is unverified"
    )


def test_verification_verdict_follows_the_sign_of_the_payload_gap() -> None:
    """The lower-bound reading holds only for the sign the project's rule gives it
    (RQ1-fuel-offload-2d 'Definition'; docs/physics.md 'Independent verification'): an
    independent search that returned a payload above P_ref (silo_cold_s2's +15.36 kg) left
    gamma* suboptimal, so x* is a flagged lower bound; one that returned a payload below
    P_ref contradicts the recorded run, so x* is uncertain both ways and no bound; one that
    did not end ok leaves x* unverified. With a flagged pad control the net figure follows
    each reading."""
    above = {"verification": {"passed": False, "delta_kg": 15.36, "tolerance_kg": 2.6}}
    below = {"verification": {"passed": False, "delta_kg": -15.36, "tolerance_kg": 2.6}}
    unended = {
        "verification": {
            "passed": False,
            "status": "search_failed",
            "delta_kg": 0.4,
            "tolerance_kg": 2.6,
        }
    }
    assert replay.offload_verdict_clause(above) == (
        "; verification failed (+15.36 kg against 2.6 kg): the gross removal is a flagged lower "
        "bound"
    )
    assert replay.offload_verdict_clause(below) == (
        "; verification failed (-15.36 kg against 2.6 kg): the gross removal is uncertain both "
        "ways, not a lower bound (the independent search carried less than P_ref at this removal)"
    )
    assert "flagged lower bound" not in replay.offload_verdict_clause(below)
    assert replay.offload_verdict_clause(unended) == (
        "; verification failed (+0.40 kg against 2.6 kg): the gross removal is unverified (the "
        "verification search ended search_failed)"
    )
    flagged = {"mode": "stage2", "flags": ["offload: search_vs_final_payload"]}
    assert replay.offload_verdict_clause(below, flagged).endswith(
        "(the independent search carried less than P_ref at this removal), as is the net "
        "figure, which also subtracts a flagged pad control"
    )
    assert replay.offload_verdict_clause(unended, flagged).endswith(
        "ended search_failed), as is the net figure, which also subtracts a flagged pad control"
    )
    assert replay.offload_verdict_clause(above, flagged).endswith(
        "flagged lower bound and the net figure, which also subtracts a flagged pad control, is "
        "uncertain both ways"
    )
    # a gap inside the tolerance with a search that ended ok cannot fail; if a record says so,
    # it is unverified, never a bound
    odd = {"verification": {"passed": False, "status": "ok", "delta_kg": 1.0, "tolerance_kg": 2.6}}
    assert replay.offload_verdict_clause(odd) == (
        "; verification failed (+1.00 kg against 2.6 kg): the gross removal is unverified"
    )
    assert replay.verification_reading({"delta_kg": 3.0, "tolerance_kg": 2.6})[2] is True
    assert replay.verification_reading({"delta_kg": -3.0, "tolerance_kg": 2.6})[2] is False


def test_verdict_clause_speaks_of_the_net_figure_only_through_a_flagged_control() -> None:
    """The verification verdict names the gross removal; the net figure is said to be
    uncertain both ways only when the pad control it subtracts carries flags (after the
    verification verdict when there is one, on its own otherwise); an unflagged control
    adds nothing, and a gross stage-1 solve never gets a control (``replay_offload_note``
    passes one for a net-quoted solve only)."""
    failed = {"verification": {"passed": False, "delta_kg": 15.36, "tolerance_kg": 2.6}}
    flagged = {"mode": "stage2", "flags": ["offload: search_vs_final_payload"]}
    clean = {"mode": "stage2", "flags": []}
    assert replay.offload_verdict_clause(failed, flagged) == (
        "; verification failed (+15.36 kg against 2.6 kg): the gross removal is a flagged lower "
        "bound and the net figure, which also subtracts a flagged pad control, is uncertain both "
        "ways"
    )
    assert replay.offload_verdict_clause(failed, clean) == (
        "; verification failed (+15.36 kg against 2.6 kg): the gross removal is a flagged lower "
        "bound"
    )
    passed = {"verification": {"passed": True}, "flags": ["x"]}
    assert replay.offload_verdict_clause(passed, flagged) == (
        "; the net figure subtracts a flagged pad control and is uncertain both ways; 1 flag "
        "(summary.md, Flags)"
    )
    assert replay.offload_verdict_clause(passed, clean) == "; 1 flag (summary.md, Flags)"
    assert replay.offload_verdict_clause({}, None) == ""
    offload = {"pad_controls": [{"mode": "stage1", "run": "a"}, {"mode": "stage2", "run": "b"}]}
    assert replay.pad_control_record(offload, "stage2") == {"mode": "stage2", "run": "b"}
    assert replay.pad_control_record(offload, "both") is None
    assert replay.has_flags({"flags": ["x"]}) and not replay.has_flags({"flags": []})
    assert not replay.has_flags({"flags": "x"}) and not replay.has_flags({})
    # a stage-1 solve with a failed verification beside a flagged stage-1 control: gross, so
    # the control is not consulted and nothing is said about a net figure
    case = {
        "name": "s1",
        "run": "s1",
        "of": "silo",
        "kind": "solve",
        "mode": "stage1",
        "total_offload_kg": OFFLOAD_KG,
        "quoted_offload_kg": OFFLOAD_KG,
        "payload_kg": P_REF_KG,
        **failed,
    }
    block = {
        "reference_payload_kg": P_REF_KG,
        "cases": [case],
        "pad_controls": [{"mode": "stage1", "run": "s1_pad", "flags": ["x"]}],
        "runs": {},
    }
    note = replay.replay_offload_note(block, "s1", "pad")
    assert note.endswith(
        "the same orbit; verification failed (+15.36 kg against 2.6 kg): the gross removal is a "
        "flagged lower bound"
    )
    assert "net figure" not in note


def test_a_single_offload_kind_is_worded_with_a_pronoun(tmp_path: Path) -> None:
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)
    one = next(c for c in _caveats(run_dir, ["pad", "silo_s1"]) if "offload block" in c)
    assert one == (
        "silo_s1 is a run of the offload block, not compared with pad here: it flies P_ref = "
        "1,000.0 kg and measures propellant saved at the same payload and orbit, not a payload "
        "change (summary.md, 'Propellant saved at fixed payload', with its caveats)."
    )
    paired = next(c for c in _caveats(run_dir, ["pad", "silo_s1__pad"]) if "offload block" in c)
    assert paired == (
        "silo_s1__pad is a run of the offload block, not compared with pad here: it is the "
        "paired pad (pad with the same offload and no push), flies its own payload capacity "
        "and measures a payload change (its payload against P_ref = 1,000.0 kg), not "
        "propellant saved."
    )


def test_a_fixed_case_is_said_to_fly_its_own_payload_capacity(tmp_path: Path) -> None:
    """A fixed case's note gives P* - P_ref with its reading (D-SP2-27): above P_ref it
    carries more than the pad, so the imposed offload is not the largest possible; short
    of it, a payload loss at that offload, not a propellant saving; equal, said so. A
    solved case flies P_ref itself and gets no such clause."""
    run_dir = _make_dir(tmp_path)
    _add_offload(run_dir)
    data = replay.replay_data(run_dir, ["pad", "silo_fix"])
    assert data["runs"][1]["label"] == "silo_fix (offload)"
    assert data["runs"][1]["detail"].startswith(
        "offload case silo_fix of silo: 20.55 t less propellant (imposed; 5.00% of the stage-1 "
        "load, 3.96% of all), flying 1,030.0 kg against pad's full load at P_ref = 1,000.0 kg, "
        "the same orbit (30.0 kg above P_ref: it carries more than the pad, so the imposed "
        "offload is not the largest possible); "
    )
    caveat = next(c for c in data["meta"]["caveats"] if "offload block" in c)
    assert caveat == (
        "silo_fix is a run of the offload block, not compared with pad here: it imposes its "
        "offload and flies its own payload capacity: its figure is that payload against P_ref "
        "= 1,000.0 kg, a payload change at the imposed offload."
    )
    assert "flies P_ref" not in caveat
    assert "above P_ref" not in replay.replay_data(run_dir, ["pad", "silo_s1"])["runs"][1]["detail"]

    def flies(payload_kg: float) -> str:
        _amend_metrics(run_dir, lambda m: m["offload"]["cases"][1].update(payload_kg=payload_kg))
        return replay.replay_data(run_dir, ["silo_fix"])["runs"][0]["detail"]

    assert (
        "the same orbit (12.5 kg short of P_ref: a payload loss at this offload, not a "
        "propellant saving); "
    ) in flies(P_REF_KG - 12.5)
    assert "the same orbit (equal to P_ref); " in flies(P_REF_KG)
    assert replay.payload_reading(30.0, "P_ref", imposed=False) == " (30.0 kg above P_ref)"
    assert replay.payload_reading(-30.0, "P_ref = 1,000.0 kg", imposed=False) == (
        " (30.0 kg short of P_ref = 1,000.0 kg)"
    )


def test_replay_offload_note_without_a_recorded_delta_or_payload() -> None:
    """The paired pad's note falls back from the recorded delta to payload - P_ref, and
    says 'not P_ref' when no payload is recorded; an unknown run is 'a run of the
    offload block'; run_data's one-decimal note is untouched."""
    case = {
        "name": "s1",
        "run": "s1",
        "of": "silo",
        "kind": "solve",
        "total_offload_kg": OFFLOAD_KG,
        "paired_pad": {"run": "s1__pad", "payload_kg": 1010.0},
    }
    offload = {"reference_payload_kg": P_REF_KG, "cases": [case], "runs": {}}
    note = replay.replay_offload_note(offload, "s1__pad", "pad")
    assert note.endswith(
        "flying its own payload capacity, 1,010.0 kg (10.0 kg above P_ref = 1,000.0 kg)"
    )
    case["paired_pad"] = {"run": "s1__pad"}
    note = replay.replay_offload_note(offload, "s1__pad", "pad")
    assert note.endswith("flying its own payload capacity, not P_ref = 1,000.0 kg")
    assert replay.replay_offload_note(offload, "nowhere", "pad") == "a run of the offload block"
    assert replay.offload_note is run_data.offload_note
    assert "41.3 t less propellant" in run_data.offload_note(offload, "s1", "pad")


# ---------------------------------------------------------------- subtitle and close-up


def test_subtitle_names_the_baseline_only_when_it_is_on_the_page(tmp_path: Path) -> None:
    """Design 4.3: the subtitle does not name a baseline that is not on the page, so a
    page without it says only that the baseline is absent."""
    run_dir = _make_dir(tmp_path)
    with_pad = replay.replay_data(run_dir, ["pad", "silo"])["meta"]["subtitle"]
    assert with_pad.endswith("compare what each run carries to orbit against the baseline, pad.")
    without = replay.replay_data(run_dir, ["silo", "silo_step"])["meta"]["subtitle"]
    assert without.endswith(
        "compare what each run carries to orbit (the baseline is not on this page)."
    )
    assert "against the baseline" not in without and "pad" not in without.split("Replay")[-1]


def test_closeup_note_verb_agrees_with_one_or_several_runs(tmp_path: Path) -> None:
    run_dir = _make_dir(tmp_path)
    one = replay.replay_data(run_dir, ["pad", "silo"])["meta"]["closeup_notes"][0]
    assert one == (
        f"silo starts {DEPTH_M:.0f} m below ground and leaves the silo mouth at 50.0 m/s after "
        f"{PUSH_S:.1f} s."
    )
    two = replay.replay_data(run_dir, ["silo", "silo_step"])["meta"]["closeup_notes"][0]
    assert two.startswith("silo and silo_step start 50 m below ground and leave the silo mouth")


# ---------------------------------------------------------------- the exploratory mark


def test_exploratory_label_prepends_one_caveat_and_a_recorded_directory_gets_none(
    tmp_path: Path,
) -> None:
    run_dir = _make_dir(tmp_path)
    recorded = replay.replay_data(run_dir, ["pad", "silo"])
    assert not any("xploratory" in c for c in recorded["meta"]["caveats"])
    for label in ("calibration", "guidance_study", None):
        _amend_metrics(run_dir, lambda m, label=label: m.update(label=label))
        assert replay.replay_data(run_dir, ["pad", "silo"]) == recorded
    _amend_metrics(run_dir, lambda m: m.update(label=replay.EXPLORATORY_LABEL))
    marked = replay.replay_data(run_dir, ["pad", "silo"])
    assert (
        marked["meta"]["caveats"][0]
        == replay.EXPLORATORY_CAVEAT
        == (
            "EXPLORATORY app run, not a finding: launched from the local app's form, not from a "
            "committed experiment file, and not pre-registered."
        )
    )
    assert marked["meta"]["caveats"][1:] == recorded["meta"]["caveats"]
    assert marked["runs"] == recorded["runs"]  # the data block does not move
    assert {k: v for k, v in marked["meta"].items() if k != "caveats"} == {
        k: v for k, v in recorded["meta"].items() if k != "caveats"
    }
    page = replay.write_replay_page(run_dir, ["pad", "silo"], tmp_path / "marked.html")
    assert _embedded(page.read_text(encoding="utf-8"))["meta"]["caveats"][0].startswith(
        "EXPLORATORY app run"
    )


def test_exploratory_label_prepends_one_footnote_line_to_the_animation(tmp_path: Path) -> None:
    """plots.animation_caveats puts EXPLORATORY_FOOTNOTE, the replay page's own
    EXPLORATORY_CAVEAT (one string for the one mark, D-SP2-23), first for the label and
    nothing for any other value; the line fits the frame at 1280 px; the animation figure
    passes the directory's label through."""
    assert len(plots.animation_caveats([], "toy_2d")) == 3
    assert len(plots.animation_caveats([], "toy_2d", label="calibration")) == 3
    lines = plots.animation_caveats([], "toy_2d", label=replay.EXPLORATORY_LABEL)
    assert len(lines) == 4 and lines[0] == plots.EXPLORATORY_FOOTNOTE == replay.EXPLORATORY_CAVEAT
    assert lines[0].startswith("EXPLORATORY app run, not a finding")
    assert lines[1:] == plots.animation_caveats([], "toy_2d")
    size_in, dpi, (width_px, _height_px) = plots.frame_geometry(1280)
    fig = Figure(figsize=size_in, dpi=dpi)
    canvas = FigureCanvasAgg(fig)
    artist = fig.text(plots.ANIMATION_GRID["left"], 0.0, lines[0], fontsize=plots.FONT_FOOTNOTE_PT)
    canvas.draw()
    assert artist.get_window_extent(renderer=canvas.get_renderer()).x1 < (
        width_px * plots.ANIMATION_GRID["right"]
    )
    run_dir = _make_animation_dir(tmp_path)
    runs, metrics = plots.load_animation_runs(run_dir, ["pad", "silo"])
    size, dpi, _ = plots.frame_geometry(640)
    plain = plots._AscentFigure(runs, metrics, "toy_2d", size, dpi)
    assert not any("EXPLORATORY" in t.get_text() for t in plain.fig.texts)
    marked = plots._AscentFigure(
        runs, {**metrics, "label": replay.EXPLORATORY_LABEL}, "toy_2d", size, dpi
    )
    footnote = next(t.get_text() for t in marked.fig.texts if "EXPLORATORY" in t.get_text())
    assert footnote.startswith(plots.EXPLORATORY_FOOTNOTE) and footnote.count("\n") == 3
