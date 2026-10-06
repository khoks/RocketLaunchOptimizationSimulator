"""display.py, the pure display-only reconstructions of the 2-D scene (SP2 step A2;
docs/physics.md, "Display-only reconstructions (not part of the model)").

Every expected value is computed here from constants, closed forms or the synthetic rows
the test builds, never from the package's own formulas. Fast tier; the real flights are
the fixed-guidance pad of experiments/silo_screening_2d.yaml at a 0.5 s sample step
(about a second), run once per module into a temporary folder, and the planner flights of
tests/test_run_data.py's real-row recipes (stage 1 through the staging coast; one flight
to insertion), each written to a temporary run folder and read back through run_data;
results/ is never read.

- The display files: a Quantity needs a source or ``assumed: true``, an unknown key is
  refused, the shipped files validate, every name the display file lists is a vehicle
  file's and the body diameter matches the one implied by each listed planar vehicle
  file's reference area (sqrt(4 A / pi)) within 2 %; the generic shape from a reference
  area.
- Tank levels on synthetic rows (a hold burn, a staging step, a fairing drop in the
  stage-2 burn or at stage-2 ignition, an offload, a penalty block): closure to 1e-6 kg,
  the fill reference per entry type, the step series; the checks pass on consistent rows
  and flag a wrong fairing flag and a wrong payload. On planner rows, the three fairing
  forms no recorded run shows (at staging by criterion or by rule, kept, at stage-2
  ignition): closure, the fairing flag's rule and every check passing.
- The separation state against hypot(v_r, v_theta) computed here; the coast's energy and
  angular-momentum drift under 1e-8 and its agreement with the closed-form Kepler time
  of flight, apex and impact arc to 1e-6 relative; a coast from the staging state of the
  real pad within 1 m of its recorded COAST_STAGING rows in position and, with the
  recorded drag integral taken out (the drag the vacuum coast ignores), within 0.01 m/s
  in speed.
- The transform and the camera law on hand-computed points; the row selection on a
  synthetic series with steps, a lag ramp and a fall-back apex; the held angle.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml
from test_run_data import (  # the planner recipes of the reader's real-row tests
    ENV,
    GAMMA_STAR_RAD,
    MET_AT_STAGING_W_M2,
    RealRun,
    _block_with_rule,
    _fly_stage1,
    _planner,
    _real_run,
)

from launchsim import display, metrics_planar, run_data, sim
from launchsim.config import SearchConfig, VehicleConfig, resolve_experiment
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.guidance import DeltaSolveSettings, solve_delta_for_gamma
from launchsim.metrics_planar import (
    FAIRING_AT_IGNITION,
    FAIRING_AT_STAGING,
    FAIRING_IN_BURN,
    FAIRING_KEPT,
)
from launchsim.phases.planar import COAST_STAGING, fmh_rate_W_m2

DISPLAY_DIR = Path(__file__).resolve().parents[1] / "configs" / "display"
VEHICLE_DIR = Path(__file__).resolve().parents[1] / "configs" / "vehicles"
BODY_DIAMETER_TOL_REL = 0.02
"""Agreement asked between the display file's body diameter and sqrt(4 A_ref / pi)."""
CLOSURE_TOL_KG = 1e-6
"""Closure of the tank rebuild on synthetic rows (exact arithmetic; rounding only)."""
MASS_TOL_KG = 1.0
"""Exit criterion 6's mass tolerance [kg], for the planner rows' tank readings (the
stage-1 tank at MECO, the stage-2 tank against its load and the recorded residual)."""
COAST_DRIFT_TOL = 1e-8
"""Relative drift of the coast's specific energy and angular momentum (measured 4e-13)."""
KEPLER_TOL_REL = 1e-6
"""Relative agreement of the numerical coast with the closed form (measured 1e-11)."""
REAL_COAST_TOL_M = 1.0
"""Position agreement [m] of the display coast with the recorded staging coast."""
REAL_COAST_TOL_MPS = 0.01
"""Speed agreement [m/s] of the display coast with the recorded staging coast once the
recorded drag, which the vacuum coast ignores by design, is taken out."""
REAL_COAST_DRAG_MAX_MPS = 0.1
"""Bound [m/s] on the recorded drag's effect over the 11 s staging coast (measured about
0.05 m/s at 66 to 76 km on the test run; the recorded runs of results/ give 0.011 to
0.060 m/s): the raw speed residual of the display coast."""
FIXED_GAMMA_DEG = 20.0
FIXED_LTG = (0.756790, 2.19338e-3)
"""The pad's LTG pair at gamma* 20 deg (tests/test_planar_pipeline.py)."""
FAST_SAMPLE_DT_S = 0.5

# ------------------------------------------------------------------ synthetic rows

D1_T, P1_T, D2_T, P2_T, FAIRING_T, PAYLOAD_T = 20.0, 201.0, 4.0, 100.0, 2.0, 20.0
"""The synthetic vehicle [t]: stage 1 burns 1,000 kg in a 2 s hold and 2,000 kg/s to a
MECO at 100 s, so its 201 t load is exactly depleted there."""
FLOWN_PAYLOAD_KG = 25_000.0
"""The payload the synthetic run flies (its metrics record), not the block's 20 t."""
HOLD_RATE_KGPS = 500.0
BURN1_KGPS = 2_000.0
BURN2_KGPS = 200.0
T_IGN1_S, T_RELEASE_S, T_KICK_S = -2.0, 0.0, 10.0
T_MECO_S, T_IGN2_S, T_FAIRING_S, T_END_S = 100.0, 110.0, 130.0, 200.0
"""The schedule of the nominal synthetic block (``_schedule``: MECO when the 201 t load
is burned; the other three at fixed offsets after it)."""
F1_N, F2_N = 8_226_900.0, 981_000.0
RESIDUAL2_KG = P2_T * 1000.0 - BURN2_KGPS * (T_END_S - T_IGN2_S)
"""Stage-2 propellant left at cutoff on the synthetic rows: 82,000 kg (every block burns
stage 2 for the same 90 s)."""
OMEGA_P = OMEGA_EARTH_RADS * math.cos(math.radians(28.5))
"""omega_p of the shipped site (28.5 deg, azimuth 90)."""


def _q(value: float) -> dict[str, Any]:
    return {"value": value, "assumed": True}


def _block(
    name: str = "toy_2d", d1_t: float = D1_T, p1_t: float = P1_T, p2_t: float = P2_T
) -> dict[str, Any]:
    """A complete raw vehicle block (tonnes) of the synthetic vehicle."""
    return {
        "name": name,
        "stages": [
            {
                "name": "stage1",
                "dry_mass_t": _q(d1_t),
                "propellant_mass_t": _q(p1_t),
                "engine": {"count": _q(9), "thrust_vac_kN": _q(914.1), "isp_vac_s": _q(311)},
            },
            {
                "name": "stage2",
                "dry_mass_t": _q(D2_T),
                "propellant_mass_t": _q(p2_t),
                "engine": {"count": _q(1), "thrust_vac_kN": _q(981), "isp_vac_s": _q(348)},
            },
        ],
        "fairing_mass_t": _q(FAIRING_T),
        "payload_mass_t": _q(PAYLOAD_T),
        "fairing_drop": "never",
    }


def _form(events: list[run_data.EventRow], masses: run_data.VehicleMasses) -> str | None:
    """How the fairing left, as the scene hands it to display (run_data.fairing_case on
    the event rows and the masses; display itself never imports the reader)."""
    return run_data.fairing_case(events, None, masses)


def _event(name: str, t_rel: float, stage: str, phase: str, m_kg: float) -> run_data.EventRow:
    return run_data.EventRow(
        t_s=t_rel,
        t_rel_s=t_rel,
        name=name,
        phase=phase,
        stage=stage,
        alt_m=10.0 * max(t_rel, 0.0) ** 2,
        downrange_m=max(t_rel, 0.0) ** 3,
        speed_rel_mps=20.0 * max(t_rel, 0.0),
        speed_inertial_mps=math.nan,
        gamma_rel_rad=math.pi / 2,
        m_kg=m_kg,
    )


def _schedule(masses: run_data.VehicleMasses) -> tuple[float, float, float, float]:
    """(MECO, stage-2 ignition, fairing drop, cutoff) [s after release] of the synthetic
    run of ``masses``: MECO when the stage-1 load is exactly burned (the hold burn, then
    BURN1_KGPS), the rest at fixed offsets after it."""
    p1 = masses.stage_propellant_kg[0]
    t_meco = (p1 - HOLD_RATE_KGPS * (T_RELEASE_S - T_IGN1_S)) / BURN1_KGPS
    return t_meco, t_meco + 10.0, t_meco + 30.0, t_meco + 100.0


def _synthetic(
    masses: run_data.VehicleMasses,
    payload_kg: float,
    *,
    step_s: float = 1.0,
    fairing_at_ignition: bool = False,
) -> tuple[display.RunRows, list[run_data.EventRow]]:
    """Rows and events of the synthetic run built from the vehicle's masses: a 2 s hold
    burn at HOLD_RATE_KGPS with a linear thrust ramp, release at 0, a kick at T_KICK_S,
    stage 1 at BURN1_KGPS to MECO (two rows: before and after the staging map), a coast,
    stage-2 ignition (two rows: thrust 0 then full), the fairing drop in the burn (two
    rows: attached, then gone), cutoff; the times from ``_schedule``, so the stage-1
    load is exactly empty at MECO whatever the block's load. With ``fairing_at_ignition``
    the fairing leaves at stage-2 ignition instead (the heating criterion first met in
    the staging coast): its row is logged there in LTG_BURN with the ignition row's mass,
    and the second of the two rows at that time is lighter by the fairing."""
    d1, d2 = masses.stage_dry_kg
    p1, p2 = masses.stage_propellant_kg
    f = masses.fairing_kg
    base = payload_kg + d2 + p2 + f
    t_meco, t_ign2, t_fairing, t_end = _schedule(masses)
    if fairing_at_ignition:
        t_fairing = t_ign2

    def mass(t: float, after_map: bool) -> float:
        if t <= T_RELEASE_S:
            burned = HOLD_RATE_KGPS * (t - T_IGN1_S)
            return base + d1 + p1 - burned
        burned1 = HOLD_RATE_KGPS * (T_RELEASE_S - T_IGN1_S) + BURN1_KGPS * min(t, t_meco)
        if t < t_meco or (t == t_meco and not after_map):
            return base + d1 + p1 - burned1
        m = base - BURN2_KGPS * max(0.0, t - t_ign2)  # the empty stage 1 has left
        if t > t_fairing or (t == t_fairing and after_map):
            m -= f
        return m

    def thrust(t: float, after_map: bool) -> float:
        if t < T_RELEASE_S:
            return F1_N * (t - T_IGN1_S) / (T_RELEASE_S - T_IGN1_S)
        if t < t_meco or (t == t_meco and not after_map):
            return F1_N
        if t < t_ign2 or (t == t_ign2 and not after_map):
            return 0.0
        return F2_N

    def phase(t: float, after_map: bool) -> str:
        if t < T_RELEASE_S:
            return "HOLD"
        if t < T_KICK_S:
            return "VERTICAL_RISE"
        if t < t_meco or (t == t_meco and not after_map):
            return "GRAVITY_TURN"
        if t < t_ign2 or (t == t_ign2 and not after_map):
            return COAST_STAGING
        return "LTG_BURN"

    grid = {round(T_IGN1_S + k * step_s, 6) for k in range(round((t_end - T_IGN1_S) / step_s) + 1)}
    grid = {t for t in grid if t <= t_end} | {
        round(t_meco, 6),
        round(t_ign2, 6),
        round(t_fairing, 6),
        round(t_end, 6),
    }
    doubled = {round(t_meco, 6), round(t_ign2, 6), round(t_fairing, 6)}
    times: list[tuple[float, bool]] = []
    for t in sorted(grid):
        times.append((t, False))
        if t in doubled:
            times.append((t, True))
    t_meco, t_ign2, t_fairing, t_end = (round(x, 6) for x in (t_meco, t_ign2, t_fairing, t_end))
    rows = display.RunRows(
        t_s=np.array([t for t, _ in times]),
        t_rel_s=np.array([t for t, _ in times]),
        phase=tuple(phase(t, a) for t, a in times),
        stage=tuple(
            "stage2" if (t > t_meco or (t == t_meco and a)) else "stage1" for t, a in times
        ),
        alt_m=np.array([10.0 * max(t, 0.0) ** 2 for t, _ in times]),
        downrange_m=np.array([max(t, 0.0) ** 3 for t, _ in times]),
        speed_rel_mps=np.array([20.0 * max(t, 0.0) for t, _ in times]),
        pitch_rad=np.array([math.pi / 2 - 0.004 * max(t - T_KICK_S, 0.0) for t, _ in times]),
        m_kg=np.array([mass(t, a) for t, a in times]),
        thrust_vac_N=np.array([thrust(t, a) for t, a in times]),
    )
    events = [
        _event("ignition", T_IGN1_S, "stage1", "HOLD", mass(T_IGN1_S, False)),
        _event("release", T_RELEASE_S, "stage1", "HOLD", mass(T_RELEASE_S, False)),
        _event("kick_start", T_KICK_S, "stage1", "VERTICAL_RISE", mass(T_KICK_S, False)),
        _event("propellant", t_meco, "stage1", "GRAVITY_TURN", mass(t_meco, False)),
        _event("staging", t_meco, "stage2", COAST_STAGING, mass(t_meco, True)),
        _event("ignition", t_ign2, "stage2", "LTG_BURN", mass(t_ign2, False)),
        _event("fairing", t_fairing, "stage2", "LTG_BURN", mass(t_fairing, False)),
        _event("cutoff", t_end, "stage2", "LTG_BURN", mass(t_end, False)),
        _event("end", t_end, "stage2", "LTG_BURN", mass(t_end, False)),
    ]
    form = FAIRING_AT_IGNITION if fairing_at_ignition else FAIRING_IN_BURN
    return rows, run_data.with_drop_masses(events, masses, form)


# ------------------------------------------------------------------ display files


def _shipped(name: str) -> dict[str, Any]:
    return yaml.safe_load((DISPLAY_DIR / name).read_text(encoding="utf-8"))


def test_shipped_display_files_validate_and_are_sourced_or_assumed() -> None:
    """Both shipped files load; every number carries a source or an assumption, which the
    geometry's provenance repeats; the stack is the published 70 m; nothing is generic."""
    cfg = display.VehicleDisplayConfig.model_validate(_shipped("f9_class.yaml"))
    scene = display.SceneDisplayConfig.model_validate(_shipped("scene.yaml"))
    geometry = cfg.geometry()
    assert not geometry.generic and geometry.reason == "display file f9_class"
    assert geometry.stack_length_m == pytest.approx(70.0)
    assert set(geometry.provenance) == {
        *(f"vehicle.{k}" for k in geometry.vehicle),
        *(f"silo.{k}" for k in geometry.silo),
        *(f"pad.{k}" for k in geometry.pad),
    }
    for text in geometry.provenance.values():
        assert text.startswith(("source: ", "assumed: "))
    assert geometry.provenance["vehicle.body_diameter_m"].startswith("source: ")
    assert geometry.provenance["vehicle.fairing_length_m"].startswith("source: ")
    assert geometry.provenance["silo.shaft_diameter_m"].startswith("assumed: ")
    for text in {
        **scene.camera.provenance(),
        **scene.provenance(),
        **scene.generic.provenance(),
    }.values():
        assert text.startswith("assumed: ")
    assert scene.camera.min_view_height_m.value == 150.0 and scene.camera.margin.value == 1.25
    assert scene.to_scale_min_body_px.value == 3.0 and scene.closeup_stack_px.value == 160.0


def test_display_quantity_needs_exactly_one_provenance_and_refuses_unknown_keys() -> None:
    """A bare number, a number with both a source and ``assumed``, a blank source and an
    unknown key each fail; so do a non-positive length and a shaft narrower than the
    fairing."""
    good = _shipped("f9_class.yaml")
    display.VehicleDisplayConfig.model_validate(good)
    bad = copy.deepcopy(good)
    bad["vehicle"]["stage1_length_m"] = 42.0
    with pytest.raises(ValueError, match="bare value"):
        display.VehicleDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(good)
    bad["vehicle"]["stage1_length_m"] = {"value": 42.0, "source": "x", "assumed": True}
    with pytest.raises(ValueError, match="exactly one of source or assumed"):
        display.VehicleDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(good)
    bad["vehicle"]["stage1_length_m"] = {"value": 42.0}
    with pytest.raises(ValueError, match="exactly one of source or assumed"):
        display.VehicleDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(good)
    bad["vehicle"]["stage1_length_m"] = {"value": 42.0, "source": "  "}
    with pytest.raises(ValueError, match="source must not be blank"):
        display.VehicleDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(good)
    bad["vehicle"]["nose_cone_m"] = _q(1.0)
    with pytest.raises(ValueError, match="nose_cone_m"):
        display.VehicleDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(good)
    bad["colour"] = "red"
    with pytest.raises(ValueError, match="colour"):
        display.VehicleDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(good)
    bad["vehicle"]["stage2_length_m"] = _q(0.0)
    with pytest.raises(ValueError, match="above zero"):
        display.VehicleDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(good)
    bad["silo"]["shaft_diameter_m"] = _q(5.0)
    with pytest.raises(ValueError, match="shaft_diameter_m must exceed"):
        display.VehicleDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(good)
    bad["applies_to"] = ["a", "a"]
    with pytest.raises(ValueError, match="repeats"):
        display.VehicleDisplayConfig.model_validate(bad)
    scene = _shipped("scene.yaml")
    bad = copy.deepcopy(scene)
    bad["camera"]["margin"] = _q(0.9)
    with pytest.raises(ValueError, match="at least 1"):
        display.SceneDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(scene)
    bad["generic"]["fairing_fraction"] = _q(0.9)
    with pytest.raises(ValueError, match="sum below 1"):
        display.SceneDisplayConfig.model_validate(bad)
    bad = copy.deepcopy(scene)
    bad["fps"] = _q(30)
    with pytest.raises(ValueError, match="fps"):
        display.SceneDisplayConfig.model_validate(bad)


F9_CLASS_VEHICLES = (
    "generic_f9_class",
    "generic_f9_class_2d",
    "generic_f9_class_2d_readme_loads",
    "generic_f9_class_2d_recorded_scope",
)
"""The vehicle names f9_class.yaml lists (``applies_to``): each must name a vehicle file."""


def test_body_diameter_matches_every_listed_planar_vehicle_file() -> None:
    """f9_class.yaml lists the four Falcon 9-class vehicles and each listed name is the
    ``name`` of a vehicle file (no stale names); its body diameter agrees with
    sqrt(4 A_ref / pi) of every listed vehicle file that has an aero block, within 2 %. A
    vehicle file the display file does not list is allowed: it is drawn with the generic
    shape, flagged (D-SP2-18; tests/test_scene.py checks that fallback)."""
    cfg = display.VehicleDisplayConfig.model_validate(_shipped("f9_class.yaml"))
    assert set(cfg.applies_to) == set(F9_CLASS_VEHICLES)
    blocks = {}
    for path in sorted(VEHICLE_DIR.glob("*.yaml")):
        block = yaml.safe_load(path.read_text(encoding="utf-8"))
        blocks[block["name"]] = block
    assert set(cfg.applies_to) <= set(blocks), set(cfg.applies_to) - set(blocks)
    planar = 0
    for name in cfg.applies_to:
        aero = blocks[name].get("aero")
        if aero is None:
            continue
        planar += 1
        area = float(aero["reference_area_m2"]["value"])
        implied = math.sqrt(4.0 * area / math.pi)
        assert cfg.vehicle.body_diameter_m.value == pytest.approx(
            implied, rel=BODY_DIAMETER_TOL_REL
        ), name
        assert display.body_diameter_from_area_m(area) == pytest.approx(implied, rel=1e-12)
    assert planar >= 3
    with pytest.raises(ValueError, match="above zero"):
        display.body_diameter_from_area_m(0.0)


def test_generic_geometry_from_a_reference_area() -> None:
    """The generic shape: diameter sqrt(4 A / pi), stack length fineness x D, the parts as
    their fractions, every provenance naming its ratio, flagged generic with the reason."""
    scene = display.SceneDisplayConfig.model_validate(_shipped("scene.yaml"))
    area = 10.52
    geo = display.generic_geometry(area, scene.generic, "no file")
    d = math.sqrt(4.0 * area / math.pi)
    g = scene.generic
    assert geo.generic and geo.reason == "no file"
    assert geo.vehicle["body_diameter_m"] == pytest.approx(d)
    assert geo.stack_length_m == pytest.approx(g.fineness.value * d)
    assert geo.vehicle["fairing_length_m"] == pytest.approx(
        g.fairing_fraction.value * geo.stack_length_m
    )
    assert geo.vehicle["fairing_diameter_m"] == pytest.approx(g.fairing_diameter_ratio.value * d)
    assert geo.silo["shaft_diameter_m"] > geo.vehicle["fairing_diameter_m"]
    assert all(v > 0.0 for v in (*geo.vehicle.values(), *geo.silo.values(), *geo.pad.values()))
    assert set(geo.provenance) == {
        *(f"vehicle.{k}" for k in geo.vehicle),
        *(f"silo.{k}" for k in geo.silo),
        *(f"pad.{k}" for k in geo.pad),
    }
    assert "assumed" in geo.provenance["vehicle.fairing_length_m"]
    assert geo.as_dict()["generic"] is True


# ------------------------------------------------------------------ tank levels


def test_tank_levels_close_and_follow_the_steps() -> None:
    """On the synthetic rows (a hold burn, a staging step, a fairing drop in the burn, a
    flown payload above the block's): the rebuild closes to 1e-6 kg at every row; the
    stage-1 tank starts at its load, falls through the hold (fill below 1 at release) and
    is empty at MECO; the stage-2 tank holds its load to stage-2 ignition and ends at
    the residual; the fairing is on up to and including the first row at its time; thrust
    is on from the ignition row to before MECO and from stage-2 ignition to before cutoff;
    the stage index switches on the second row at staging."""
    masses = run_data.vehicle_masses(_block())
    rows, events = _synthetic(masses, FLOWN_PAYLOAD_KG)
    levels = display.tank_levels(
        rows, masses, FLOWN_PAYLOAD_KG, events, masses, _form(events, masses)
    )
    prop1, prop2 = levels.prop_kg
    assert np.max(np.abs(display.rebuilt_mass_kg(levels, masses) - rows.m_kg)) < CLOSURE_TOL_KG
    assert prop1[0] == pytest.approx(P1_T * 1000.0, abs=CLOSURE_TOL_KG)
    i_rel = int(np.nonzero(rows.t_rel_s == T_RELEASE_S)[0][0])
    assert prop1[i_rel] == pytest.approx(P1_T * 1000.0 - 1000.0, abs=CLOSURE_TOL_KG)
    assert levels.fill[0][i_rel] == pytest.approx(1.0 - 1000.0 / (P1_T * 1000.0), abs=1e-12)
    meco = np.nonzero(rows.t_rel_s == T_MECO_S)[0]
    assert len(meco) == 2
    assert prop1[meco[0]] == pytest.approx(0.0, abs=CLOSURE_TOL_KG)
    assert prop1[meco[1]] == prop1[meco[0]]  # held after staging
    assert np.all(prop1[meco[1] :] == prop1[meco[0]])
    before_ign2 = rows.t_rel_s < T_IGN2_S
    assert np.max(np.abs(prop2[before_ign2] - P2_T * 1000.0)) < CLOSURE_TOL_KG
    assert prop2[-1] == pytest.approx(RESIDUAL2_KG, abs=CLOSURE_TOL_KG)
    fair = np.nonzero(rows.t_rel_s == T_FAIRING_S)[0]
    assert levels.fairing_on[fair[0]] and not levels.fairing_on[fair[1]]
    assert np.all(levels.fairing_on[: fair[0]]) and not np.any(levels.fairing_on[fair[1] :])
    assert levels.fairing_form == FAIRING_IN_BURN
    t = rows.t_rel_s
    expect_on = ((t >= T_IGN1_S) & (t < T_MECO_S)) | ((t >= T_IGN2_S) & (t < T_END_S))
    assert np.array_equal(levels.thrust_on, expect_on)
    assert not levels.thrust_on[-1]  # the cutoff row reads full thrust, the rule says off
    assert levels.stage_index[meco[0]] == 0 and levels.stage_index[meco[1]] == 1
    assert (
        levels.load_kg == (P1_T * 1000.0, P2_T * 1000.0) and levels.payload_kg == FLOWN_PAYLOAD_KG
    )
    assert levels.offload_fraction == (0.0, 0.0) and levels.not_loaded_kg == (0.0, 0.0)
    assert len(rows) == len(prop1)


def test_fill_reference_per_entry_type_and_offload_and_penalty() -> None:
    """An offloaded block (stage-1 load 0.9 of the full one) drawn against the full-load
    reference starts at fill 0.9 (a run, bound or offload entry); drawn against its own
    block (a case) it starts full. A penalty block (stage-1 dry mass + 8.1 t) closes with
    its own masses and starts at its own fill."""
    full = run_data.vehicle_masses(_block())
    offloaded = run_data.vehicle_masses(_block(p1_t=0.9 * P1_T))
    rows, events = _synthetic(offloaded, FLOWN_PAYLOAD_KG)
    against_full = display.tank_levels(
        rows, offloaded, FLOWN_PAYLOAD_KG, events, full, _form(events, offloaded)
    )
    assert against_full.fill[0][0] == pytest.approx(0.9, abs=1e-12)
    assert against_full.fill[1][0] == pytest.approx(1.0, abs=1e-12)
    assert against_full.offload_fraction[0] == pytest.approx(0.1, abs=1e-12)
    assert against_full.not_loaded_kg[0] == pytest.approx(0.1 * P1_T * 1000.0, abs=1e-6)
    against_own = display.tank_levels(
        rows, offloaded, FLOWN_PAYLOAD_KG, events, offloaded, _form(events, offloaded)
    )
    assert against_own.fill[0][0] == pytest.approx(1.0, abs=1e-12)
    assert (
        np.max(np.abs(display.rebuilt_mass_kg(against_full, offloaded) - rows.m_kg))
        < CLOSURE_TOL_KG
    )
    report = display.tank_checks(
        rows,
        against_full,
        offloaded,
        events,
        recorded_m_res_kg=RESIDUAL2_KG,
        offload_fractions=(0.1, 0.0),
    )
    assert report.passed, report.failed
    penalty = run_data.vehicle_masses(_block(d1_t=D1_T + 8.1))
    rows, events = _synthetic(penalty, FLOWN_PAYLOAD_KG)
    levels = display.tank_levels(
        rows, penalty, FLOWN_PAYLOAD_KG, events, full, _form(events, penalty)
    )
    assert np.max(np.abs(display.rebuilt_mass_kg(levels, penalty) - rows.m_kg)) < CLOSURE_TOL_KG
    report = display.tank_checks(rows, levels, penalty, events, recorded_m_res_kg=RESIDUAL2_KG)
    assert report.passed, report.failed
    staging = next(e for e in events if e.name == "staging")
    assert staging.m_before_kg - staging.m_after_kg == pytest.approx((D1_T + 8.1) * 1000.0)
    # the block's own payload when the run has no metric (a failed search): still closes
    rows, events = _synthetic(full, full.payload_kg)
    levels = display.tank_levels(rows, full, full.payload_kg, events, full, _form(events, full))
    assert np.max(np.abs(display.rebuilt_mass_kg(levels, full) - rows.m_kg)) < CLOSURE_TOL_KG


def test_checks_pass_on_consistent_rows_and_flag_a_wrong_fairing_flag_and_payload() -> None:
    """The report passes on the synthetic rows with every item applicable; with the
    fairing row removed (the flag stays on: review 01 finding 1) the stage-2 tank steps
    at the fairing time and misses the residual, both flagged; with a payload 1,000 kg
    too high the liftoff identity and the empty-at-MECO item fail while the identity
    rebuild still closes; a run without a stage-2 end reports that item not applicable."""
    masses = run_data.vehicle_masses(_block())
    rows, events = _synthetic(masses, FLOWN_PAYLOAD_KG)
    levels = display.tank_levels(
        rows, masses, FLOWN_PAYLOAD_KG, events, masses, _form(events, masses)
    )
    report = display.tank_checks(
        rows,
        levels,
        masses,
        events,
        liftoff_mass_kg=float(rows.m_kg[0]),
        recorded_m_res_kg=RESIDUAL2_KG,
    )
    assert report.passed and not report.failed
    assert all(item.passed is True for item in report.items)
    names = [item.name for item in report.items]
    assert names[0] == "liftoff identity" and "no tank step at a doubled time" in names
    as_dict = report.as_dict()
    assert as_dict["passed"] is True and as_dict["failed"] == []
    assert all(isinstance(i["worst"], float) for i in as_dict["items"])

    without = [e for e in events if e.name != "fairing"]
    kept = run_data.with_drop_masses([e for e in without], masses, FAIRING_KEPT)
    wrong = display.tank_levels(rows, masses, FLOWN_PAYLOAD_KG, kept, masses, _form(kept, masses))
    assert wrong.fairing_on.all() and wrong.fairing_form == FAIRING_KEPT
    assert np.max(np.abs(display.rebuilt_mass_kg(wrong, masses) - rows.m_kg)) < CLOSURE_TOL_KG
    flagged = display.tank_checks(rows, wrong, masses, kept, recorded_m_res_kg=RESIDUAL2_KG)
    assert not flagged.passed
    assert "no tank step at a doubled time" in flagged.failed
    assert "stage-2 tank equals recorded_m_res_kg on the last row" in flagged.failed
    step = next(i for i in flagged.items if i.name == "no tank step at a doubled time")
    assert step.worst == pytest.approx(FAIRING_T * 1000.0, abs=1e-6)

    heavy = display.tank_levels(
        rows, masses, FLOWN_PAYLOAD_KG + 1000.0, events, masses, _form(events, masses)
    )
    assert np.max(np.abs(display.rebuilt_mass_kg(heavy, masses) - rows.m_kg)) < CLOSURE_TOL_KG
    flagged = display.tank_checks(rows, heavy, masses, events, recorded_m_res_kg=RESIDUAL2_KG)
    assert "liftoff identity" in flagged.failed
    assert "stage-1 tank empty at the stage-1 propellant event" in flagged.failed
    assert "stage-1 start fill equals one minus the offload fraction" in flagged.failed

    short = [e for e in events if e.name not in ("cutoff", "end")]
    report = display.tank_checks(rows, levels, masses, short, recorded_m_res_kg=RESIDUAL2_KG)
    item = next(i for i in report.items if i.name.startswith("stage-2 tank equals"))
    assert item.passed is None and report.passed


def test_fairing_flag_cases_and_thrust_rule_corners() -> None:
    """A fairing row in COAST_STAGING, or none under rule staging (the reader adds the
    row), means attached on the stage-1 rows only; no row under rule never means attached
    throughout; a vehicle without a fairing mass is never attached; a fairing row at
    stage-2 ignition (LTG_BURN, the ignition row's time and mass) means attached through
    the first of the two rows at that time and gone from the second, the stage-2 tank
    equal on both and every check passing (no tank step at that doubled time). A stage
    without an ignition row is never on; one without an end row stays on."""
    masses = run_data.vehicle_masses(_block())
    rows, events = _synthetic(masses, FLOWN_PAYLOAD_KG)
    stage_idx = display.stage_indices(rows.stage, masses.stage_names)
    staging = next(e for e in events if e.name == "staging")
    at_staging = [e for e in events if e.name != "fairing"]
    at_staging.append(
        run_data.EventRow(
            t_s=staging.t_s,
            t_rel_s=staging.t_rel_s,
            name="fairing",
            phase=COAST_STAGING,
            stage="stage2",
            alt_m=staging.alt_m,
            downrange_m=staging.downrange_m,
            speed_rel_mps=staging.speed_rel_mps,
            speed_inertial_mps=math.nan,
            gamma_rel_rad=staging.gamma_rel_rad,
            m_kg=staging.m_kg,
        )
    )
    flags, form = display.fairing_on_flags(
        rows, at_staging, masses, stage_idx, _form(at_staging, masses)
    )
    assert form == FAIRING_AT_STAGING and np.array_equal(flags, stage_idx == 0)
    by_rule = run_data.vehicle_masses({**_block(), "fairing_drop": "staging"})
    added = run_data.with_drop_masses([e for e in events if e.name != "fairing"], by_rule, None)
    assert any(e.name == "fairing" and not e.recorded for e in added)
    flags, form = display.fairing_on_flags(rows, added, by_rule, stage_idx, _form(added, by_rule))
    assert form == FAIRING_AT_STAGING and np.array_equal(flags, stage_idx == 0)
    kept = [e for e in events if e.name != "fairing"]
    flags, form = display.fairing_on_flags(rows, kept, masses, stage_idx, _form(kept, masses))
    assert form == FAIRING_KEPT and flags.all()
    no_fairing = run_data.vehicle_masses({**_block(), "fairing_mass_t": _q(0.0)})
    flags, form = display.fairing_on_flags(
        rows, events, no_fairing, stage_idx, _form(events, no_fairing)
    )
    assert form is None and not flags.any()
    # at stage-2 ignition (heating criterion first met in the staging coast): the 'first
    # row at the time is attached' rule meets a doubled time whose two rows differ in mass
    rows2, events2 = _synthetic(masses, FLOWN_PAYLOAD_KG, fairing_at_ignition=True)
    form2 = _form(events2, masses)
    assert form2 == FAIRING_AT_IGNITION
    fairing2 = next(e for e in events2 if e.name == "fairing")
    assert (fairing2.t_s, fairing2.phase) == (T_IGN2_S, "LTG_BURN")
    assert fairing2.m_before_kg - fairing2.m_after_kg == pytest.approx(FAIRING_T * 1000.0)
    levels2 = display.tank_levels(rows2, masses, FLOWN_PAYLOAD_KG, events2, masses, form2)
    ign = np.nonzero(rows2.t_s == T_IGN2_S)[0]
    assert len(ign) == 2 and levels2.fairing_form == FAIRING_AT_IGNITION
    assert levels2.fairing_on[rows2.t_s < T_IGN2_S].all() and levels2.fairing_on[ign[0]]
    assert not levels2.fairing_on[ign[1] :].any()
    prop2 = levels2.prop_kg[1]
    assert prop2[ign[0]] == prop2[ign[1]] == pytest.approx(P2_T * 1000.0, abs=CLOSURE_TOL_KG)
    rebuilt = display.rebuilt_mass_kg(levels2, masses)
    assert np.max(np.abs(rebuilt - rows2.m_kg)) < CLOSURE_TOL_KG
    report2 = display.tank_checks(
        rows2,
        levels2,
        masses,
        events2,
        liftoff_mass_kg=float(rows2.m_kg[0]),
        recorded_m_res_kg=RESIDUAL2_KG,
    )
    assert report2.passed and all(item.passed is True for item in report2.items)
    step2 = next(i for i in report2.items if i.name == "no tank step at a doubled time")
    assert step2.worst < CLOSURE_TOL_KG
    with pytest.raises(ValueError, match="lacks"):
        display.stage_indices(("stage3",), masses.stage_names)
    never_lit = [e for e in events if not (e.name == "ignition" and e.stage == "stage2")]
    on = display.thrust_on_flags(rows.t_s, never_lit, masses.stage_names)
    assert not on[rows.t_s >= T_IGN2_S].any()
    no_end = [e for e in events if e.name not in ("cutoff", "end")]
    on = display.thrust_on_flags(rows.t_s, no_end, masses.stage_names)
    assert on[-1]
    (match,) = display.match_events(rows.t_s, [staging])
    assert (match.index, match.count, match.last_index) == (match.index, 2, match.index + 1)
    off = run_data.EventRow(**{**staging.__dict__, "t_s": staging.t_s + 0.3})
    assert display.match_events(rows.t_s, [off])[0].index is None
    near = run_data.EventRow(**{**staging.__dict__, "t_s": staging.t_s + 1e-9})
    assert display.match_events(rows.t_s, [near])[0].index == match.index
    assert display.duplicate_groups(rows.t_s) == [
        (int(np.nonzero(rows.t_s == t)[0][0]), 2) for t in (T_MECO_S, T_IGN2_S, T_FAIRING_S)
    ]


# ------------------------------------------------------------------ tank levels on planner rows


@pytest.fixture(scope="module")
def gate_raw_block() -> dict[str, Any]:
    """The raw vehicle file of the gate fork (generic_f9_class_2d.yaml): a vehicle block
    as resolved_config.yaml holds it (tests/test_run_data.py's ``gate_block``)."""
    return yaml.safe_load((VEHICLE_DIR / "generic_f9_class_2d.yaml").read_text(encoding="utf-8"))


def _planner_rows(frame: pd.DataFrame) -> display.RunRows:
    """RunRows of a planar time series read back with both rows of every doubled time
    (run_data.read_series_frame), every numeric column as float, as the scene builds them."""

    def col(name: str) -> np.ndarray:
        return frame[name].to_numpy(dtype=float)

    return display.RunRows(
        t_s=col("t_s"),
        t_rel_s=col("t_rel_release_s"),
        phase=tuple(frame["phase"].astype(str)),
        stage=tuple(frame["stage"].astype(str)),
        alt_m=col("alt_m"),
        downrange_m=col("downrange_m"),
        speed_rel_mps=col("speed_rel_mps"),
        pitch_rad=col("pitch_rad"),
        m_kg=col("m_kg"),
        thrust_vac_N=col("thrust_vac_N"),
    )


def _planner_tanks(
    run: RealRun, form: str, recorded_m_res_kg: float | None
) -> tuple[display.RunRows, list[run_data.EventRow], display.TankLevels, display.CheckReport]:
    """The tank series and the load-time checks of a planner flight written as a run
    folder and read back through run_data, built as the scene builds them: the events with
    their drop masses (run_data.with_drop_masses on the run's metric), the fairing form
    read from those rows (asserted equal to the metric and to ``form``), the tanks from
    the block's payload. Asserts the rebuild closes to CLOSURE_TOL_KG at every row and
    every applicable check passes. Returns (rows, events, levels, report)."""
    rows = _planner_rows(run.raw)
    events = run_data.with_drop_masses(run.rows, run.masses, run.metric)
    assert run.metric == form and run_data.fairing_case(events, None, run.masses) == form
    levels = display.tank_levels(rows, run.masses, run.masses.payload_kg, events, run.masses, form)
    assert levels.fairing_form == form
    rebuilt = display.rebuilt_mass_kg(levels, run.masses)
    assert np.max(np.abs(rebuilt - rows.m_kg)) < CLOSURE_TOL_KG
    report = display.tank_checks(
        rows, levels, run.masses, events, recorded_m_res_kg=recorded_m_res_kg
    )
    assert report.passed, report.failed
    return rows, events, levels, report


@pytest.mark.parametrize(
    ("rule", "form"),
    [
        (MET_AT_STAGING_W_M2, FAIRING_AT_STAGING),
        ("staging", FAIRING_AT_STAGING),
        ("never", FAIRING_KEPT),
    ],
    ids=["criterion_met_at_staging", "rule_staging", "rule_never"],
)
def test_tanks_on_planner_rows_with_the_fairing_dropped_at_staging_or_kept(
    tmp_path: Path, gate_raw_block: dict[str, Any], rule: Any, form: str
) -> None:
    """Real planner rows (tests/test_run_data.py's stage-1 flight of the gate fork through
    staging and the staging coast, written with results_io's CSV writer and read back
    through run_data) for two fairing forms no recorded run shows. At staging (a heating
    criterion already met at MECO, its row logged in COAST_STAGING; or rule staging, the
    row added by the reader): the fairing is on exactly on the stage-1 rows. Kept (rule
    never): on throughout. Either way the rebuild closes to 1e-6 kg, the stage-1 tank is
    empty at MECO, the stage-2 tank holds its load through the coast with no step at the
    staging time, and every applicable check passes."""
    run = _real_run(tmp_path, "run", _block_with_rule(gate_raw_block, rule), _fly_stage1)
    rows, events, levels, report = _planner_tanks(run, form, None)
    if form == FAIRING_AT_STAGING:
        assert np.array_equal(levels.fairing_on, levels.stage_index == 0)
    else:
        assert levels.fairing_on.all()
    staging = next(e for e in events if e.name == "staging")
    at = np.nonzero(rows.t_s == staging.t_s)[0]
    assert len(at) == 2 and list(levels.stage_index[at]) == [0, 1]
    prop1, prop2 = levels.prop_kg
    assert abs(prop1[at[0]]) < MASS_TOL_KG
    p2 = run.masses.stage_propellant_kg[1]
    assert np.max(np.abs(prop2 - p2)) < MASS_TOL_KG  # stage 2 never lights in this flight
    empty = next(i for i in report.items if i.name.startswith("stage-1 tank empty"))
    assert empty.passed is True  # applicable: the flight has its stage-1 propellant row


def test_tanks_on_planner_rows_with_the_fairing_dropped_at_stage2_ignition(
    tmp_path: Path, gate_raw_block: dict[str, Any]
) -> None:
    """Real planner rows of a heating criterion first met in the staging coast (the
    recipe of tests/test_engine_planar.py and tests/test_run_data.py: a limit at the
    geometric mean of the rates at MECO and at stage-2 ignition), flown to insertion: the
    fairing row is logged at stage-2 ignition, and the fairing is on through the first of
    the two rows at that time and gone from the second; the stage-2 tank reads its load on
    both rows (no step), the rebuild closes to 1e-6 kg and every check passes, the
    stage-2 tank ending at the model's own recorded_m_res_kg
    (metrics_planar.fixed_guidance_metrics of the trace)."""
    gate = VehicleConfig.model_validate(gate_raw_block).to_vehicle()
    probe = _planner(gate, "insertion", dense=False)
    kick = probe.to_kick(probe.start())
    sol = solve_delta_for_gamma(
        lambda d: probe.from_kick(d, kick),
        GAMMA_STAR_RAD,
        DeltaSolveSettings.from_config(SearchConfig()),
    )
    ltg = probe.solve_stage2(sol.handover)
    handover = probe.stage1(sol.delta_rad, probe.start())
    assert handover.y_ign2 is not None
    rate_meco = fmh_rate_W_m2(handover.prefix.burnouts["stage1"][1], ENV)
    rate_ign = fmh_rate_W_m2(handover.y_ign2, ENV)
    assert rate_ign < rate_meco
    block = _block_with_rule(gate_raw_block, math.sqrt(rate_meco * rate_ign))
    run = _real_run(
        tmp_path,
        "run",
        block,
        lambda v: _planner(v, "insertion").run(sol.delta_rad, ltg=(ltg.a, ltg.b_per_s)),
    )
    m_res = metrics_planar.fixed_guidance_metrics(run.trace, run.vehicle, "fixed")[
        "recorded_m_res_kg"
    ]
    assert m_res is not None
    rows, events, levels, report = _planner_tanks(run, FAIRING_AT_IGNITION, m_res)
    fairing = next(e for e in events if e.name == "fairing")
    ignition = next(e for e in events if e.name == "ignition" and e.stage == "stage2")
    assert (fairing.t_s, fairing.phase) == (ignition.t_s, "LTG_BURN")
    at = np.nonzero(rows.t_s == fairing.t_s)[0]
    assert len(at) == 2
    assert levels.fairing_on[: at[0] + 1].all() and not levels.fairing_on[at[1] :].any()
    prop2 = levels.prop_kg[1]
    p2 = run.masses.stage_propellant_kg[1]
    assert abs(prop2[at[0]] - p2) < MASS_TOL_KG and abs(prop2[at[1]] - p2) < MASS_TOL_KG
    residual = next(i for i in report.items if i.name.startswith("stage-2 tank equals"))
    assert residual.passed is True and abs(prop2[-1] - m_res) < MASS_TOL_KG


# ------------------------------------------------------------------ separation state and coast


def test_separation_state_matches_hypot_computed_here() -> None:
    """From synthetic row values the rebuilt state has r = R_E + alt, theta = d / R_E +
    omega_p t, v_r = V sin(gamma), v_theta = V cos(gamma) + omega_p r, and its inertial
    speed is hypot(v_r, v_theta) computed here; omega_p is omega_E cos(lat) sin(az)."""
    alt, d, v, gamma, t = 70_000.0, 100_000.0, 2_700.0, 0.4, 150.0
    omega = display.planar_omega_p(math.radians(28.5), math.radians(90.0))
    assert omega == pytest.approx(OMEGA_P, rel=1e-15)
    assert display.planar_omega_p(math.radians(28.5), math.radians(90.0), False) == 0.0
    assert display.planar_omega_p(0.0, math.radians(90.0)) == pytest.approx(OMEGA_EARTH_RADS)
    state = display.separation_state(alt, d, v, gamma, t, omega)
    r = R_EARTH_M + alt
    v_r = v * math.sin(gamma)
    v_t = v * math.cos(gamma) + omega * r
    assert state.r_m == r and state.theta_rad == pytest.approx(d / R_EARTH_M + omega * t, rel=1e-15)
    assert state.v_r_mps == pytest.approx(v_r, rel=1e-15)
    assert state.v_theta_mps == pytest.approx(v_t, rel=1e-15)
    assert state.speed_inertial_mps == pytest.approx(math.hypot(v_r, v_t), rel=1e-15)
    assert np.array_equal(state.as_array(), [r, state.theta_rad, state.v_r_mps, state.v_theta_mps])
    # the pad at rest, equatorial east: the inertial speed is omega_E R_E
    rest = display.separation_state(0.0, 0.0, 0.0, math.pi / 2, 0.0, OMEGA_EARTH_RADS)
    assert rest.speed_inertial_mps == pytest.approx(OMEGA_EARTH_RADS * R_EARTH_M)


def test_vacuum_coast_conserves_invariants_and_matches_kepler() -> None:
    """From a staging-like state the numerical coast keeps the specific energy and angular
    momentum to 1e-8 relative, and its time of flight, apex altitude and impact arc agree
    with the closed form to 1e-6 relative; downrange and speed are Earth-fixed and
    Earth-relative; a clip stops the samples early without changing the impact."""
    omega = OMEGA_P
    d0 = 99_000.0
    state = display.separation_state(69_500.0, d0, 2_665.0, 0.4012, 151.3, omega)
    coast = display.vacuum_coast(state, d0, omega)
    kepler = display.kepler_coast(state)
    assert coast.reached_surface and coast.impact_t_s is not None
    assert coast.energy_drift_rel < COAST_DRIFT_TOL and coast.h_drift_rel < COAST_DRIFT_TOL
    assert coast.impact_t_s == pytest.approx(kepler.tof_s, rel=KEPLER_TOL_REL)
    assert coast.apex_alt_m == pytest.approx(kepler.apex_alt_m, rel=KEPLER_TOL_REL)
    arc = (coast.impact_downrange_m - d0) / R_EARTH_M + omega * coast.impact_t_s
    assert arc == pytest.approx(kepler.impact_arc_rad, rel=KEPLER_TOL_REL)
    assert 0.0 < coast.apex_t_s < coast.impact_t_s
    assert coast.alt_m[0] == pytest.approx(69_500.0, abs=1e-6) and abs(coast.alt_m[-1]) < 1e-3
    assert coast.downrange_m[0] == pytest.approx(d0) and coast.speed_rel_mps[0] == pytest.approx(
        2_665.0
    )
    assert coast.t_s[-1] == coast.impact_t_s and np.all(np.diff(coast.t_s) > 0.0)
    assert 0.0 < kepler.e < 1.0 and kepler.a_m > 0.0
    # energy and angular momentum computed here from the state, as the oracle
    y = state.as_array()
    assert display.specific_energy_j_per_kg(y) == pytest.approx(
        0.5 * (y[2] ** 2 + y[3] ** 2) - MU_EARTH_M3S2 / y[0]
    )
    assert display.specific_angular_momentum_m2ps(y) == y[0] * y[3]
    clipped = display.vacuum_coast(state, d0, omega, clip_s=50.0)
    assert clipped.t_s[-1] == 50.0 and len(clipped.t_s) == 51
    assert clipped.impact_t_s == coast.impact_t_s
    assert clipped.impact_downrange_m == coast.impact_downrange_m
    assert np.allclose(clipped.alt_m, coast.alt_m[:51])
    # a body already descending: its apex is the separation point
    down = display.separation_state(50_000.0, d0, 2_000.0, -0.3, 300.0, omega)
    falling = display.vacuum_coast(down, d0, omega)
    assert falling.apex_t_s == 0.0 and falling.apex_alt_m == pytest.approx(50_000.0)
    # a body in orbit never reaches the surface inside the time limit
    orbit = display.PlanarState(
        R_EARTH_M + 300e3, 0.0, 0.0, math.sqrt(MU_EARTH_M3S2 / (R_EARTH_M + 300e3))
    )
    free = display.vacuum_coast(orbit, 0.0, 0.0, t_max_s=100.0)
    assert not free.reached_surface and free.impact_t_s is None and free.t_s[-1] == 100.0
    with pytest.raises(ValueError, match="perigee"):
        display.kepler_coast(orbit)
    with pytest.raises(ValueError, match="bound orbit"):
        display.kepler_coast(display.PlanarState(R_EARTH_M + 1e5, 0.0, 0.0, 12_000.0))
    with pytest.raises(ValueError, match="clip_s"):
        display.vacuum_coast(state, d0, omega, clip_s=-1.0)


def test_coast_gap_is_exact_at_the_given_times_and_measures_an_offset() -> None:
    """coast_gap_m evaluates the coast at the given times exactly: fed the coast's own
    samples (a repeated time included) it reads under 1e-6 m; one point moved by 1 m in
    altitude and 2 m in downrange reads hypot(1, 2 (R_E + alt) / R_E) m, the screen
    distance computed here; at a separation time alone it is the gap at the state; no
    points give NaN; a decreasing or negative time is refused."""
    omega = OMEGA_P
    d0 = 99_000.0
    state = display.separation_state(69_500.0, d0, 2_665.0, 0.4012, 151.3, omega)
    coast = display.vacuum_coast(state, d0, omega, sample_dt_s=0.7, clip_s=11.0)
    dt = np.concatenate([coast.t_s[:5], coast.t_s[4:]])  # one time repeated
    alt = np.concatenate([coast.alt_m[:5], coast.alt_m[4:]])
    down = np.concatenate([coast.downrange_m[:5], coast.downrange_m[4:]])
    assert display.coast_gap_m(state, d0, omega, dt, alt, down) < 1e-6
    moved_alt, moved_down = alt.copy(), down.copy()
    moved_alt[7] += 1.0
    moved_down[7] += 2.0
    expected = math.hypot(1.0, 2.0 * (R_EARTH_M + alt[7]) / R_EARTH_M)
    assert display.coast_gap_m(state, d0, omega, dt, moved_alt, moved_down) == pytest.approx(
        expected, abs=1e-6
    )
    at_once = display.coast_gap_m(
        state, d0, omega, np.array([0.0]), np.array([69_500.0 + 0.3]), np.array([d0])
    )
    assert at_once == pytest.approx(0.3, abs=1e-9)
    none = np.array([])
    assert math.isnan(display.coast_gap_m(state, d0, omega, none, none, none))
    with pytest.raises(ValueError, match="non-decreasing"):
        display.coast_gap_m(state, d0, omega, np.array([1.0, 0.5]), np.zeros(2), np.zeros(2))
    with pytest.raises(ValueError, match="same length"):
        display.coast_gap_m(state, d0, omega, np.array([0.0]), np.zeros(2), np.zeros(2))


@pytest.fixture(scope="module")
def real_pad(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixed-guidance pad and silo_failed of silo_screening_2d (gamma* 20 deg, the
    pad's LTG pair, a 0.5 s sample step; tests/test_planar_pipeline.py's fast experiment
    without silo_cold), run once through sim.run_experiment into a temporary results
    root. Returns the results directory."""
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_2d.yaml").read_text(encoding="utf-8")
    )
    veh = yaml.safe_load(
        (repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml").read_text(
            encoding="utf-8"
        )
    )
    exp["search"].update(
        {
            "figure_of_merit": "none",
            "fixed_gamma_star_deg": FIXED_GAMMA_DEG,
            "fixed_ltg_a": FIXED_LTG[0],
            "fixed_ltg_b_per_s": FIXED_LTG[1],
        }
    )
    exp["baseline"]["integrator"]["sample_dt_s"] = FAST_SAMPLE_DT_S
    exp["variants"] = {k: v for k, v in exp["variants"].items() if k == "silo_failed"}
    for key in ("sweeps", "sensitivity", "bounds"):
        exp.pop(key, None)
    resolved = resolve_experiment(exp, veh)
    root = tmp_path_factory.mktemp("display_real")
    _, out = sim.run_experiment(resolved, root, plots=False, repo_root=repo_root)
    return out


def test_coast_from_the_real_staging_state_reproduces_the_recorded_staging_coast(
    real_pad: Path,
) -> None:
    """The display coast started from the pad's recorded staging row reproduces every
    recorded COAST_STAGING row (the vehicle coasting unpowered above 66 km) within 1 m in
    altitude and downrange. Its Earth-relative speed differs from the recorded one by the
    drag the display coast ignores by design: the residual grows at the recorded drag_N /
    m_kg (about 0.05 m/s over the 11 s coast here, at 66 to 76 km) and, with that integral
    taken out, the two agree within 0.01 m/s at every row."""
    columns = (
        "t_s",
        "t_rel_release_s",
        "phase",
        "alt_m",
        "downrange_m",
        "speed_rel_mps",
        "drag_N",
        "m_kg",
    )
    frame = run_data.read_series(real_pad, "pad", columns)
    offset = run_data.release_offset_s(frame)
    events = run_data.read_events(real_pad / "pad" / run_data.EVENTS_FILE, offset)
    staging = next(e for e in events if e.name == "staging")
    config = run_data.read_yaml(real_pad / run_data.CONFIG_FILE)
    site = config["runs"]["pad"]["run"]["site"]
    omega = display.planar_omega_p(
        math.radians(site["latitude_deg"]),
        math.radians(site["azimuth_deg"]),
        site["include_rotation"],
    )
    state = display.separation_state(
        staging.alt_m,
        staging.downrange_m,
        staging.speed_rel_mps,
        staging.gamma_rel_rad,
        staging.t_rel_s,
        omega,
    )
    assert state.speed_inertial_mps == pytest.approx(staging.speed_inertial_mps, abs=1e-6)
    coast_rows = frame[frame["phase"] == COAST_STAGING]
    assert len(coast_rows) >= 10
    dt = coast_rows["t_rel_release_s"].to_numpy(dtype=float) - staging.t_rel_s
    coast = display.vacuum_coast(
        state, staging.downrange_m, omega, sample_dt_s=0.5, clip_s=float(dt[-1])
    )
    alt = np.interp(dt, coast.t_s, coast.alt_m)
    downrange = np.interp(dt, coast.t_s, coast.downrange_m)
    speed = np.interp(dt, coast.t_s, coast.speed_rel_mps)
    recorded = coast_rows["speed_rel_mps"].to_numpy(dtype=float)
    assert np.max(np.abs(alt - coast_rows["alt_m"].to_numpy(dtype=float))) < REAL_COAST_TOL_M
    assert (
        np.max(np.abs(downrange - coast_rows["downrange_m"].to_numpy(dtype=float)))
        < REAL_COAST_TOL_M
    )
    decel = coast_rows["drag_N"].to_numpy(dtype=float) / coast_rows["m_kg"].to_numpy(dtype=float)
    drag_loss = np.concatenate([[0.0], np.cumsum(0.5 * (decel[1:] + decel[:-1]) * np.diff(dt))])
    assert 0.0 < drag_loss[-1] < REAL_COAST_DRAG_MAX_MPS  # the drag the coast ignores
    assert np.max(np.abs((speed - drag_loss) - recorded)) < REAL_COAST_TOL_MPS
    assert np.max(np.abs(speed - recorded)) < REAL_COAST_DRAG_MAX_MPS
    assert speed[0] == pytest.approx(recorded[0], abs=1e-9) and np.all(speed >= recorded)
    # the measured screen gap the scene quotes per spent stage: exact at the row times
    gap = display.coast_gap_m(
        state,
        staging.downrange_m,
        omega,
        dt,
        coast_rows["alt_m"].to_numpy(dtype=float),
        coast_rows["downrange_m"].to_numpy(dtype=float),
    )
    assert 0.0 < gap < REAL_COAST_TOL_M
    # it agrees with the interpolated residuals above up to the sag of a 0.5 s chord under
    # the surface gravity (g h^2 / 8) and the (R_E + alt) / R_E stretch of the screen x
    x_alt = np.max(np.abs(alt - coast_rows["alt_m"].to_numpy(dtype=float)))
    x_down = np.max(np.abs(downrange - coast_rows["downrange_m"].to_numpy(dtype=float)))
    sag = MU_EARTH_M3S2 / R_EARTH_M**2 * FAST_SAMPLE_DT_S**2 / 8.0
    assert max(x_alt, x_down) - sag <= gap <= 1.02 * math.hypot(x_alt, x_down) + sag


# ------------------------------------------------------------------ transform and camera


def test_screen_transform_and_camera_law_on_hand_points() -> None:
    """The launch site maps to the origin, a point straight above it to (0, alt), a point a
    quarter turn downrange to (R_E, -R_E); the drawn angle is pitch - d / R_E; the camera
    law gives H_MIN at zero extent and margin x E far out; the extent never shrinks."""
    assert display.screen_xy(0.0, 0.0) == (0.0, 0.0)
    x, y = display.screen_xy(1_000.0, 0.0)
    assert (x, y) == (0.0, pytest.approx(1_000.0))
    x, y = display.screen_xy(0.0, math.pi * R_EARTH_M / 2.0)
    assert x == pytest.approx(R_EARTH_M) and y == pytest.approx(-R_EARTH_M)
    xs, ys = display.screen_xy(np.array([0.0, 100.0]), np.array([0.0, R_EARTH_M * 0.01]))
    assert xs[1] == pytest.approx((R_EARTH_M + 100.0) * math.sin(0.01))
    assert ys[1] == pytest.approx((R_EARTH_M + 100.0) * math.cos(0.01) - R_EARTH_M)
    assert display.screen_angle_rad(math.pi / 2, 0.0) == math.pi / 2
    assert display.screen_angle_rad(0.3, R_EARTH_M * 0.01) == pytest.approx(0.29)
    assert display.view_height_m(0.0, 150.0, 1.25) == 150.0
    assert display.view_height_m(1.0e6, 150.0, 1.25) == pytest.approx(1.25e6, rel=1e-7)
    assert display.view_height_m(120.0, 150.0, 1.25) == pytest.approx(math.hypot(150.0, 150.0))
    alt = np.array([-100.0, 0.0, 300.0, 200.0, 50.0])
    d = np.array([0.0, 0.0, 0.0, 400.0, 100.0])
    extent = display.running_extent_m(alt, d, floor_m=-100.0, body_length_m=70.0)
    assert extent[0] == pytest.approx(math.hypot(100.0 + 70.0, 0.0))
    assert extent[2] == pytest.approx(300.0 + 100.0 + 70.0)
    assert extent[3] == pytest.approx(math.hypot(200.0 + 170.0, 400.0))
    assert extent[4] == extent[3] and np.all(np.diff(extent) >= 0.0)
    wide = display.running_extent_m(alt, d, floor_m=-100.0, body_length_m=70.0, aspect=2.0)
    assert wide[3] == pytest.approx(470.0)  # hypot(370, 400 / 2) = 420.6 < the running maximum
    assert wide[3] < extent[3]
    with pytest.raises(ValueError, match="aspect"):
        display.running_extent_m(alt, d, floor_m=0.0, body_length_m=1.0, aspect=0.0)


# ------------------------------------------------------------------ row selection


def test_row_selection_keeps_duplicates_and_events_and_meets_half_tolerance() -> None:
    """On a synthetic series with doubled rows (steps), a lag startup (1 - exp(-t / tau))
    and a fall-back apex (the pitch sweeping 180 deg in two rows), the selection keeps
    both rows of every doubled time and every event row, converges in bounded passes,
    inserts rows where the base grid misses, and leaves every CSV row within half of each
    tolerance under linear interpolation; the base selection alone does not."""
    t = np.round(np.arange(-2.0, 120.0, 0.05), 6)
    t = np.sort(np.concatenate([t, [0.0, 30.0, 60.0]]))  # doubled rows at three steps
    n = len(t)
    plume = np.where(t >= 0.0, 1.0 - np.exp(-np.maximum(t, 0.0) / 1.0), 0.0)
    second = np.r_[False, np.diff(t) == 0.0]
    plume = np.where((t == 30.0) & second, 0.0, plume)
    plume = np.where(t > 30.0, 0.0, plume)
    pitch = np.full(n, math.pi / 2)
    apex = 80.0
    pitch = np.where(t > apex, math.pi / 2 + math.pi, pitch)
    pitch = np.where(np.isclose(t, apex), math.pi, pitch)
    alt = np.where(t < 0.0, -100.0 * (1.0 - (1.0 + t / 2.0) ** 2), 60.0 * np.maximum(t, 0.0))
    alt = np.where(t > 30.0, 1800.0 + 50.0 * (t - 30.0) - 0.6 * (t - 30.0) ** 2, alt)
    downrange = np.maximum(t, 0.0) ** 2 / 50.0
    mass = np.where(t >= 0.0, 5.0e5 - 2000.0 * np.minimum(t, 30.0), 5.0e5)
    mass = np.where((t == 30.0) & second, 5.0e5 - 60_000.0 - 20_000.0, mass)
    mass = np.where(t > 30.0, 5.0e5 - 60_000.0 - 20_000.0, mass)
    fields = [
        display.SelectionField("alt_m", alt, display.ALT_TOL_MIN_M, display.ALT_TOL_REL),
        display.SelectionField(
            "downrange_m", downrange, display.DOWNRANGE_TOL_MIN_M, display.DOWNRANGE_TOL_REL
        ),
        display.SelectionField("pitch_rad", pitch, display.PITCH_TOL_RAD),
        display.SelectionField("plume", plume, display.PLUME_TOL),
        display.SelectionField("mass_kg", mass, display.MASS_TOL_KG),
    ]
    events = [int(np.nonzero(t == x)[0][0]) for x in (0.0, 30.0, 60.0, apex)]
    events.append(int(np.nonzero(t == 10.05)[0][0]))  # an event on a single, odd row
    base = display.base_selection(t, events)
    selection = display.select_rows(t, fields, events)
    sel = selection.indices
    assert selection.converged and 0 < selection.passes <= display.SELECTION_MAX_PASSES
    assert len(sel) > len(base) and set(base) <= set(sel)
    for start, count in display.duplicate_groups(t):
        assert all(i in sel for i in range(start, start + count))
    assert all(i in sel for i in events)
    assert sel[0] == 0 and sel[-1] == n - 1 and np.all(np.diff(sel) > 0)
    for field in fields:
        residual = display.interpolation_residuals(t, field.values, sel)
        assert np.all(residual <= display.SELECTION_HALF * field.tolerance() + 1e-12), field.name
        assert selection.worst[field.name].frac <= display.SELECTION_HALF
    base_bad = any(
        np.any(
            display.interpolation_residuals(t, f.values, base)
            > display.SELECTION_HALF * f.tolerance()
        )
        for f in fields
    )
    assert base_bad  # the lag ramp and the apex need the inserted rows
    early = sel[t[sel] < display.SELECTION_EARLY_END_S]
    assert len(early) >= len([i for i in range(n) if t[i] < display.SELECTION_EARLY_END_S]) // 2
    report = selection.as_dict()
    assert report["samples"] == len(sel) and set(report["worst"]) == {f.name for f in fields}
    with pytest.raises(ValueError, match="at least one field"):
        display.select_rows(t, [], events)
    # bounded passes: with no insertion allowed the report says not converged
    stuck = display.select_rows(t, fields, events, max_passes=0)
    assert not stuck.converged and stuck.passes == 0 and len(stuck.indices) == len(base)


def test_rebuilt_mass_residual_counts_rounding_only_on_selected_rows() -> None:
    """On the synthetic tank rows every CSV row is selected, so the rebuilt-mass residual
    is the tank rounding alone (at most 0.05 kg at 0.1 kg); with the rows thinned, the
    residual at an unselected row is the interpolation error of the active tank."""
    masses = run_data.vehicle_masses(_block())
    rows, events = _synthetic(masses, FLOWN_PAYLOAD_KG)
    levels = display.tank_levels(
        rows, masses, FLOWN_PAYLOAD_KG, events, masses, _form(events, masses)
    )
    every = np.arange(len(rows))
    residual = display.rebuilt_mass_residual_kg(
        rows, levels, masses, every, time_decimals=6, tank_decimals=1
    )
    assert np.max(residual) <= 0.05 + 1e-9
    exact = display.rebuilt_mass_residual_kg(
        rows, levels, masses, every, time_decimals=6, tank_decimals=6
    )
    assert np.max(exact) < 1e-5
    i_rel = int(np.nonzero(rows.t_rel_s == T_RELEASE_S)[0][0])
    thin = display.base_selection(rows.t_rel_s, [i_rel], early_step=3, late_step=3)
    thinned = display.rebuilt_mass_residual_kg(
        rows, levels, masses, thin, time_decimals=6, tank_decimals=6
    )
    assert len(thin) < len(rows) and np.max(thinned) < 1e-5  # linear burns between rows
    without_release = display.base_selection(rows.t_rel_s, [], early_step=3, late_step=3)
    kinked = display.rebuilt_mass_residual_kg(
        rows, levels, masses, without_release, time_decimals=6, tank_decimals=6
    )
    assert np.max(kinked) > display.MASS_TOL_KG  # the burn rate kinks at release


# ------------------------------------------------------------------ held attitude


def test_held_angle_follows_the_rule() -> None:
    """Where the attitude is defined the drawn angle is pitch - d / R_E; where it is not,
    the last defined screen angle is held (not the pitch), the first rows keep their own
    angle when nothing precedes them, and the model's instant steps pass through. At the
    doubled time of stage-2 ignition the time-based thrust flag is on at both rows, but
    the pre-map row is still the coast (recorded thrust 0, pitch the coast's v_rel angle):
    it is not defined and holds the coast's angle, so the ignition step is the only step.
    The same for the end row of a cold silo's COAST_PRE_IGN at the ignition time."""
    pitch = np.array([math.pi / 2, math.pi / 2, 1.5, 1.4, 1.3, 1.2, 1.1, 1.5, 1.45])
    d = np.array([0.0, 0.0, 0.0, 1.0e4, 2.0e4, 3.0e4, 3.5e4, 3.5e4, 5.0e4])
    phase = (
        "HOLD",
        "ASSIST",
        "KICK",
        "GRAVITY_TURN",
        "COAST_STAGING",
        "COAST_STAGING",
        "COAST_STAGING",  # the pre-map row of the ignition pair (one time with the next)
        "LTG_BURN",
        "LTG_BURN",
    )
    thrust_on = np.array([False, False, True, True, False, False, True, True, True])
    defined = display.attitude_defined(phase, thrust_on)
    assert np.array_equal(defined, [True, True, True, True, False, False, False, True, True])
    held = display.held_screen_angle_rad(pitch, d, defined)
    expected = pitch - d / R_EARTH_M
    assert np.allclose(held[[0, 1, 2, 3, 7, 8]], expected[[0, 1, 2, 3, 7, 8]])
    assert held[4] == held[3] and held[5] == held[3]  # the screen angle of the last defined row
    assert held[6] == held[5]  # the pre-map ignition row holds the coast's angle
    assert held[4] != pitch[4] - d[4] / R_EARTH_M
    assert held[6] != pitch[6] - d[6] / R_EARTH_M
    assert held[2] - held[1] == pytest.approx(1.5 - math.pi / 2)  # the kick's step as recorded
    steps = np.abs(np.diff(held))
    assert steps[5] == 0.0 and steps[6] > 0.0  # no step before the ignition, one at it
    none_before = display.held_screen_angle_rad(pitch[:3], d[:3], np.array([False, False, True]))
    assert np.allclose(none_before, expected[:3])
    # a cold silo: COAST_PRE_IGN ends at the ignition time, flagged on by time, not defined
    cold = display.attitude_defined(
        ("ASSIST", "COAST_PRE_IGN", "COAST_PRE_IGN", "KICK"), np.array([False, False, True, True])
    )
    assert np.array_equal(cold, [True, False, False, True])
    assert set(display.UNPOWERED_PHASES) == {"COAST_PRE_IGN", "COAST_STAGING", "COAST"}


def test_run_rows_refuse_inconsistent_arrays() -> None:
    """RunRows needs equal lengths, at least one row and non-decreasing times."""
    one = np.array([0.0])
    good = display.RunRows(one, one, ("HOLD",), ("stage1",), one, one, one, one, one, one)
    assert len(good) == 1
    with pytest.raises(ValueError, match="same length"):
        display.RunRows(one, one, ("HOLD", "HOLD"), ("stage1",), one, one, one, one, one, one)
    with pytest.raises(ValueError, match="at least one row"):
        empty = np.array([])
        display.RunRows(empty, empty, (), (), empty, empty, empty, empty, empty, empty)
    two = np.array([1.0, 0.0])
    with pytest.raises(ValueError, match="not decrease"):
        display.RunRows(
            two, two, ("HOLD", "HOLD"), ("stage1", "stage1"), two, two, two, two, two, two
        )
