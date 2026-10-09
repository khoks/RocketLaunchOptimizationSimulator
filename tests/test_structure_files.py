"""The structure files and their configuration (SP7 step S2; design 4.3; the source note
docs/phases/inputs/2026-10-08-SP7-sources.md, sections 3-8 and 12): both files validate
through cli.load_structure; every number carries a source or assumed: true; the shared
coefficient sections are identical; the SP-8007 table is the note's and lies on or below
its source points; the conversion to structure.py's dataclasses goes through units.py;
the overrides the search uses are checked.
"""

from __future__ import annotations

import copy
import importlib.util
import itertools
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest
import yaml

from launchsim import cli
from launchsim import structure as st
from launchsim.config import STRUCTURE_SET_NAMES, StructureConfig


def _load_support() -> ModuleType:
    """tests/structure_support.py, loaded by path (any pytest import mode)."""
    name = "structure_support"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ss = _load_support()

FILES = (ss.GATE_STRUCTURE, ss.README_STRUCTURE)
SHARED_SECTIONS = (
    "layout",
    "materials",
    "factors",
    "pressures",
    "buckling",
    "geometry",
    "load_entry",
    "nof",
    "dynamics",
    "ring",
    "thrust_structure",
    "interstage",
    "payload_limits",
    "plausibility",
    "sizing_only",
)
"""The sections the README-loads fork reuses unchanged (design 4.3: only its layout masses,
mixture fraction and breakdown differ; the layout holds no masses)."""

# The source note's section 6.3 table (x = (p/E)(r/t)^2, Delta_gamma), written out.
NOTE_TABLE = (
    (0.0, 0.0),
    (0.015, 0.0226),
    (0.02, 0.0286),
    (0.0261, 0.0351),
    (0.03, 0.0396),
    (0.04, 0.0494),
    (0.05, 0.0573),
    (0.06, 0.0652),
    (0.08, 0.0802),
    (0.1, 0.0910),
    (0.15, 0.1147),
    (0.2, 0.1330),
    (0.3, 0.1564),
    (0.4, 0.1731),
    (0.5, 0.1855),
    (0.6, 0.1962),
    (0.8, 0.2076),
    (0.883, 0.2113),
    (1.0, 0.2167),
    (1.5, 0.2330),
    (2.0, 0.2408),
    (3.0, 0.2446),
    (10.0, 0.2446),
)
# The source note's section 6.2 source points (the 2020 path's 28 segment ends).
NOTE_SOURCE_POINTS = (
    (0.015023, 0.022683),
    (0.017576, 0.025695),
    (0.020038, 0.028664),
    (0.023293, 0.032152),
    (0.026481, 0.035553),
    (0.031362, 0.041175),
    (0.037005, 0.046860),
    (0.043292, 0.052085),
    (0.055164, 0.061406),
    (0.065871, 0.069961),
    (0.081348, 0.081132),
    (0.098992, 0.090494),
    (0.12263, 0.10280),
    (0.14872, 0.11424),
    (0.19256, 0.13088),
    (0.24529, 0.14399),
    (0.31538, 0.15951),
    (0.40163, 0.17343),
    (0.49753, 0.18529),
    (0.62888, 0.19853),
    (0.88537, 0.21145),
    (1.2579, 0.22679),
    (1.7380, 0.23721),
    (2.6606, 0.24643),
    (4.3093, 0.24883),
    (6.7791, 0.24653),
    (8.8718, 0.24552),
    (9.8843, 0.24466),
)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_structure_files_validate_through_the_loader(path: Path) -> None:
    """cli.load_structure reads and validates both files: two stages named as the vehicle,
    the central set and each range's ends convert, the four frozen sets of S2's search
    convert (tests/test_structure_search.py checks them), applies_to the file's own
    vehicle; a copy without its sets block refuses a set by name."""
    config = cli.load_structure(path)
    assert isinstance(config, StructureConfig)
    assert config.applies_to == [path.stem]
    layout = config.stack_layout()
    assert (layout.stage1.name, layout.stage2.name) == ("stage1", "stage2")
    assert layout.stations_per_barrel == 200 and layout.radius_m == 1.83
    assert config.sets is not None
    for name in STRUCTURE_SET_NAMES:
        config.coefficients(name)
    bare = ss.load_yaml(path)
    del bare["sets"]
    without = StructureConfig.model_validate(bare)
    assert without.sets is None
    with pytest.raises(ValueError, match="no frozen sets"):
        without.coefficients(STRUCTURE_SET_NAMES[0])


def test_load_structure_refuses_bad_files(tmp_path: Path) -> None:
    """A missing file, a number without provenance, a range out of order and an unknown key
    are CliErrors with one message."""
    with pytest.raises(cli.CliError, match="not found"):
        cli.load_structure(tmp_path / "missing.yaml")
    base = ss.load_yaml(ss.GATE_STRUCTURE)
    broken = []
    a = copy.deepcopy(base)
    del a["materials"]["E_GPa"]["assumed"]
    broken.append(a)
    b = copy.deepcopy(base)
    b["materials"]["E_GPa"]["low"] = 80.0
    broken.append(b)
    c = copy.deepcopy(base)
    c["materials"]["unknown_key"] = 1
    broken.append(c)
    d = copy.deepcopy(base)
    d["factors"]["FS_ult"] = 1.4
    broken.append(d)
    for i, data in enumerate(broken):
        path = tmp_path / f"bad{i}.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        with pytest.raises(cli.CliError, match="invalid structure file"):
            cli.load_structure(path)


def _provenance_gaps(node: Any, path: str, covered: bool) -> list[str]:
    """Paths of numbers in a parsed YAML tree with no source or assumed: true on the
    mapping that holds them or on an enclosing one (within a quantity's own mapping)."""
    gaps: list[str] = []
    if isinstance(node, dict):
        here = covered or "source" in node or node.get("assumed") is True
        for key, value in node.items():
            if key in ("source", "note", "assumed", "label", "path"):
                continue
            gaps += _provenance_gaps(value, f"{path}.{key}", here)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            gaps += _provenance_gaps(value, f"{path}[{i}]", covered)
    elif isinstance(node, bool):
        return gaps
    elif isinstance(node, int | float) and not covered:
        gaps.append(path)
    return gaps


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_every_number_has_provenance(path: Path) -> None:
    """Every number in the file sits in a mapping with ``source`` or ``assumed: true`` (a
    Quantity, a range, a discrete choice, a layout choice, a provenance-carrying list) and
    every such mapping has exactly one of them (the models refuse the rest); every range
    and every choice whose numbers are not all opened values used for what they measure is
    ``assumed: true``: the source note section 12's list."""
    data = ss.load_yaml(path)
    assert _provenance_gaps(data, path.stem, False) == []
    source_alone = {
        "materials.nu",
        "materials.rho_wall_kg_per_m3",
        "buckling.k_stiff",
        "nof.nof_dome",
        "buckling.s_dg",
    }
    config = cli.load_structure(path)
    for item in config.coefficient_ranges():
        node: Any = config
        for part in item.path.split("."):
            node = getattr(node, part)
        assert (node.source is not None) == (item.path in source_alone), item.path
        assert node.assumed == (item.path not in source_alone), item.path


def test_shared_coefficient_sections_are_identical() -> None:
    """The README-loads fork reuses the gate file's coefficient sections and layout
    unchanged (design 4.3, a test): only name, description, applies_to, mixture (its
    fractions assumed equal to the gate's, its notes its own), breakdown and the frozen
    sets (its own search on its own pad and headline push) differ."""
    gate, fork = ss.load_yaml(ss.GATE_STRUCTURE), ss.load_yaml(ss.README_STRUCTURE)
    for section in SHARED_SECTIONS:
        assert gate[section] == fork[section], section
    differing = {k for k in gate.keys() | fork.keys() if gate.get(k) != fork.get(k)}
    assert differing == {"name", "description", "applies_to", "mixture", "breakdown", "sets"}
    for stage in ("stage1", "stage2"):
        assert (
            gate["mixture"][stage]["lox_mass_fraction"]["value"]
            == fork["mixture"][stage]["lox_mass_fraction"]["value"]
        )


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_breakdowns_close_the_vehicle_dry_masses(path: Path) -> None:
    """Each stage's breakdown sums to its vehicle file's dry mass (the remainder closes it,
    source note sections 5.1-5.3), and the thrust-structure placement uses D-SP7-37's
    central 0.2805 kg/kN (0.2805 x 8,226.9 kN and x 981 kN, rounded)."""
    layout = cli.load_structure(path).stack_layout()
    vehicle_path = ss.GATE_VEHICLE if path == ss.GATE_STRUCTURE else ss.README_VEHICLE
    vehicle = ss.vehicle(vehicle_path)
    for stage, lay in zip(vehicle.stages, (layout.stage1, layout.stage2), strict=True):
        assert lay.breakdown.total_kg == stage.dry_mass_kg
    assert layout.stage1.breakdown.thrust_structure_kg == round(0.2805 * 8226.9)
    assert layout.stage2.breakdown.thrust_structure_kg == round(0.2805 * 981.0)
    assert layout.stage1.breakdown.rest_at == st.REST_AT_BASE
    assert layout.stage2.breakdown.rest_at == st.REST_AT_FORWARD_END


def test_delta_gamma_table_is_the_notes() -> None:
    """The file's SP-8007 table equals the source note's section 6.3 table, written out here
    with its source points (section 6.2)."""
    config = cli.load_structure(ss.GATE_STRUCTURE)
    assert config.buckling.delta_gamma_table.pairs() == NOTE_TABLE
    assert config.buckling.delta_gamma_source_points.pairs() == NOTE_SOURCE_POINTS
    assert config.coefficients().delta_gamma_table == NOTE_TABLE


def test_delta_gamma_table_against_its_source_points() -> None:
    """The source note's rules for the table (section 6.2-6.3): at every source point the
    linearly interpolated table is at or below the source value, at most 1.1% below it below
    x = 2.4 and at most 1.8% below it above (the largest gap 1.70% at x = 4.31); x strictly
    ascending, values non-decreasing, constant beyond x = 10, the chord rule met."""
    xs = [p[0] for p in NOTE_TABLE]
    ys = [p[1] for p in NOTE_TABLE]
    assert all(b > a for a, b in itertools.pairwise(xs))
    assert all(b >= a for a, b in itertools.pairwise(ys))
    st.check_delta_gamma_table(NOTE_TABLE)
    gaps = []
    for x, curve in NOTE_SOURCE_POINTS:
        table = st.delta_gamma(x, NOTE_TABLE)
        assert math.isclose(table, float(np.interp(x, xs, ys)), rel_tol=1e-12)
        assert table <= curve
        gap = 1.0 - table / curve
        gaps.append((x, gap))
        assert gap <= (0.011 if x < 2.4 else 0.018), (x, gap)
    worst = max(gaps, key=lambda item: item[1])
    assert round(worst[0], 2) == 4.31 and round(100.0 * worst[1], 2) == 1.70
    assert st.delta_gamma(50.0, NOTE_TABLE) == 0.2446


def test_gerard_rows_named_in_the_file_exist_with_the_notes_pairs() -> None:
    """The file names Gerard rows only; structure.GERARD_ROWS holds the pairs (source note
    section 13 item 12), equal to the note's section 3.3 table: ring_common_z (6.48, 3/5),
    ring_common_y (5.93, 3/5), ring_improved_z (7.14, 7/11), ring_improved_y (6.01, 7/11),
    and plate_limited."""
    config = cli.load_structure(ss.GATE_STRUCTURE)
    named = set(config.buckling.gerard_row.choices) | {
        line.value for line in config.sizing_only if line.field == "buckling.gerard_row"
    }
    assert named == set(st.GERARD_CHOICES)
    pairs = {row.name: (row.c, row.exponent) for row in st.GERARD_ROWS}
    assert pairs == {
        "ring_common_z": (6.48, 3.0 / 5.0),
        "ring_common_y": (5.93, 3.0 / 5.0),
        "ring_improved_z": (7.14, 7.0 / 11.0),
        "ring_improved_y": (6.01, 7.0 / 11.0),
    }


def test_coefficients_convert_through_units() -> None:
    """The central set in SI (units.py): E 75.84 GPa, F_tu 558.5 MPa, MEOP 2.62 bar and its
    minimum 0.84 x 2.62 bar, t_min 1.65 mm, k_ts 0.2805 kg/kN; the 2219-T851 domes (455.05
    MPa, 2851.0 kg/m^3) and the 2195 alternative taking the materials block's values; the
    coefficient count of section 9.1 (23 continuous physics, 4 discrete, 7 continuous
    design axes and the integer pad count); the stage-2-only five."""
    config = cli.load_structure(ss.GATE_STRUCTURE)
    c = config.coefficients()
    assert c.e_pa == 75.84e9 and c.f_tu_pa == 558.5e6 and c.rho_wall_kgm3 == 2712.6
    assert c.p_meop_pa("stage1", "lox") == 2.62e5
    assert math.isclose(c.p_min_pa("stage2", "rp1"), 0.84 * 2.62e5, rel_tol=1e-15)
    assert math.isclose(c.t_min_m, 1.65e-3, rel_tol=1e-15)
    assert math.isclose(c.k_ts_kg_per_n, 0.2805e-3, rel_tol=1e-15)
    assert c.dome_alloy == "2219-T851" and c.dome_f_tu_pa == 455.05e6 and c.dome_rho_kgm3 == 2851.0
    assert c.fs_ult == 1.40 and c.fitting_factor == 1.15 and c.ring_pads == 8
    assert c.s_dg == 1.0 and c.gerard_row == "ring_common_z"
    assert c.skirt_envelope_path == "hold_down"
    alt = config.coefficients(
        overrides={"materials.dome_alloy": "2195", "materials.F_tu_MPa": 530.0}
    )
    assert alt.dome_f_tu_pa == 530.0e6 and alt.dome_rho_kgm3 == 2712.6
    ranges = config.coefficient_ranges()
    kinds = [(r.group, r.kind) for r in ranges]
    assert kinds.count(("physics", "continuous")) == 23
    assert kinds.count(("physics", "discrete")) == 4
    assert kinds.count(("design", "continuous")) == 7
    assert kinds.count(("design", "integer")) == 1
    assert {r.path for r in ranges if r.stage2_only} == {
        "pressures.stage2_lox.p_meop_bar",
        "pressures.stage2_lox.p_min_fraction",
        "pressures.stage2_rp1.p_meop_bar",
        "pressures.stage2_rp1.p_min_fraction",
        "geometry.interstage_length_m",
    }


def test_coefficient_overrides_are_checked() -> None:
    """The search's hook refuses an unknown path, a value outside its range, a discrete
    value it does not offer, a non-integer pad count and a change to a fixed number, and
    takes the file's sizing-only lines (FS_ult 1.25, k_stiff 0.85 and 0.52, the three
    out-of-band Gerard rows); check_ranges=False lifts the range check only."""
    config = cli.load_structure(ss.GATE_STRUCTURE)
    bad = (
        {"materials.E_GPa_typo": 75.0},
        {"materials.E_GPa": 90.0},
        {"buckling.gerard_row": "ring_isotropic"},
        {"ring.ring_pads": 6.5},
        {"ring.ring_pads": 3},
        {"factors.FS_ult": 1.5},
    )
    for overrides in bad:
        with pytest.raises(ValueError):
            config.coefficients(overrides=overrides)
    assert config.coefficients(overrides={"factors.FS_ult": 1.25}).fs_ult == 1.25
    assert config.coefficients(overrides={"buckling.k_stiff": 0.52}).k_stiff == 0.52
    assert config.coefficients(overrides={"buckling.gerard_row": "ring_improved_y"}).gerard_row == (
        "ring_improved_y"
    )
    loose = config.coefficients(overrides={"materials.E_GPa": 90.0}, check_ranges=False)
    assert loose.e_pa == 90.0e9
    with pytest.raises(ValueError):
        config.coefficients(overrides={"nope.nope": 1.0}, check_ranges=False)


def test_layout_facts_the_model_hard_codes_are_checked() -> None:
    """The layout facts the model hard-codes are refused when edited, so the file cannot
    disagree with the model it documents: each stage's construction must be
    structure.MODELLED_CONSTRUCTION for its role (a renamed or retyped element, a missing
    one or a typo in a construction name refused), the interstage's charged_to must be
    stage 1 (D-SP7-36); the materials block's alloy carries its provenance (assumed for the
    skirt, ring and tube, source note section 2.3)."""
    base = ss.load_yaml(ss.GATE_STRUCTURE)
    config = StructureConfig.model_validate(base)
    for i, role in enumerate(st.STAGE_ROLES):
        assert config.layout.stages[i].construction.value == dict(st.MODELLED_CONSTRUCTION[role])
    assert config.interstage.charged_to.value == st.INTERSTAGE_CHARGED_TO == "stage1"
    assert config.materials.block_alloy_name == "2195"
    assert config.materials.block_alloy.assumed and config.materials.block_alloy.note
    edits = (
        ("lox_barrel", "stiffened_gerard", 0),
        ("aft_skirt", "stiffened_gerrard", 0),
        ("domes", "membrane_domes", 1),
        ("load_ring", None, 0),
    )
    for element, value, stage in edits:
        bad = copy.deepcopy(base)
        construction = bad["layout"]["stages"][stage]["construction"]["value"]
        if value is None:
            del construction[element]
        else:
            construction[element] = value
        with pytest.raises(ValueError, match="construction"):
            StructureConfig.model_validate(bad)
    extra = copy.deepcopy(base)
    extra["layout"]["stages"][1]["construction"]["value"]["aft_skirt"] = "stiffened_gerard"
    with pytest.raises(ValueError, match="construction"):
        StructureConfig.model_validate(extra)
    moved = copy.deepcopy(base)
    moved["interstage"]["charged_to"]["value"] = "stage2"
    with pytest.raises(ValueError, match="charged_to"):
        StructureConfig.model_validate(moved)
    bare = copy.deepcopy(base)
    bare["materials"]["block_alloy"] = "2195"
    with pytest.raises(ValueError):
        StructureConfig.model_validate(bare)
