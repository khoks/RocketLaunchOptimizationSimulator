"""Scaffold rules from CLAUDE.md: Earth constants live in one place, every file open
declares an encoding (Windows consoles are cp1252), public physics functions carry
docstrings, and the dev tooling installs with both uv sync and pip install -e .[dev].
"""

from __future__ import annotations

import ast
import importlib
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "launchsim"

CONSTANT_LITERALS = [
    r"3\.986004418e14",
    r"6378137",
    r"6_378_137",
    r"7\.2921150e-5",
    r"7\.292115e-5",
    r"9\.80665",
    r"(?<![\d.])9\.81(?![\d])",
]

PHYSICS_MODULES = [
    "atmosphere",
    "dynamics",
    "losses",
    "phases/__init__",
    "phases/engine",
    "phases/prelude",
    "phases/planar",
    "phases/vertical",
    "phases/trace",
    "vehicle",
    "units",
    "offload",  # pure per CLAUDE.md's layout (SP7 step S1, D-SP7-34)
    "structure",  # the structural sizing primitives (SP7 step S1)
    "assist/base",
    "assist/constant_accel",
    "assist/none",
    "assist/track",
    "display",  # the scene's display-only reconstructions (SP2 step A2, design 4.1)
]
"""Module paths under src/launchsim (without .py) whose public functions, classes and
methods must carry a docstring. Every path must exist: a missing one fails the check
(the package ``phases`` is listed file by file; SP7 step S1, D-SP7-34)."""


def _source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_package_imports_and_version() -> None:
    launchsim = importlib.import_module("launchsim")
    assert re.fullmatch(r"\d+\.\d+\.\d+", launchsim.__version__)
    for name in ["launchsim.constants", "launchsim.units", "launchsim.cli"]:
        importlib.import_module(name)


def test_earth_constants_only_in_constants_py() -> None:
    offenders = []
    for path in _source_files():
        if path.name == "constants.py":
            continue
        text = path.read_text(encoding="utf-8")
        offenders += [
            f"{path.relative_to(REPO)}: {pattern}"
            for pattern in CONSTANT_LITERALS
            if re.search(pattern, text)
        ]
    assert not offenders, offenders


def test_every_file_open_declares_encoding() -> None:
    offenders = []
    for path in _source_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if re.search(r"\b(open|read_text|write_text)\(", line):
                window = "\n".join(lines[i : i + 4])
                if "encoding=" not in window:
                    offenders.append(f"{path.relative_to(REPO)}:{i + 1}")
    assert not offenders, offenders


def test_public_physics_functions_have_docstrings() -> None:
    """Every public module-level function and class, and every public method of those
    classes, in each PHYSICS_MODULES file has a docstring (what the docstring says is for
    review: this checks that one exists); a listed path that does not exist fails."""
    absent = [module for module in PHYSICS_MODULES if not (SRC / f"{module}.py").is_file()]
    assert not absent, f"PHYSICS_MODULES lists missing module files: {absent}"
    missing = []
    for module in PHYSICS_MODULES:
        path = SRC / f"{module}.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        nodes: list[ast.FunctionDef | ast.ClassDef] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.ClassDef):
                nodes.append(node)
                if isinstance(node, ast.ClassDef):
                    nodes += [n for n in node.body if isinstance(n, ast.FunctionDef)]
        for node in nodes:
            if node.name.startswith("_"):
                continue
            if ast.get_docstring(node) is None:
                missing.append(f"{path.relative_to(REPO)}:{node.name}")
    assert not missing, missing


def test_pyproject_dev_tooling_installable_both_ways() -> None:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["requires-python"].startswith(">=3.12")
    extra = data["project"]["optional-dependencies"]["dev"]
    group = data["dependency-groups"]["dev"]
    assert any(pkg.startswith("pytest") for pkg in extra)
    assert any(pkg.startswith("ruff") for pkg in extra)
    assert group == ["launchsim[dev]"] or sorted(group) == sorted(extra)
