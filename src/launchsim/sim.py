"""Run one configuration and return a Result; the package's dispatch point.

``run`` dispatches on the RunConfig's ``dynamics``. vertical_1d (Phase 1, unchanged byte
for byte): ``simulate`` (pure) runs one configuration through the 1-D planner
(``phases``) and assembles the Result (time series, events and metrics from
``metrics``, the loss budget from ``losses``); ``run`` builds its inputs (mu/r^2
gravity, g_eff = mu/R_E^2, ignition specs, the assist model and its track through
``assist.build_assist``). planar_2d (Phase 2): ``run_planar`` runs the shared search
(``search.run_search``) or the fixed guidance and ``simulate_planar`` (pure) assembles
the Result of the recorded run (``metrics_planar``; ``PLANAR_ASSUMPTIONS``; the
per-run checks of the screening-beat rule, status ``bug_suspect``);
``rerun_resolved`` rebuilds an energy-only sensitivity case on a run already flown,
``matched_run`` executes the rung-2 runs of the matched-payload attribution for
``compare.compare_planar`` (amendment 16), and ``solve_resolved_offload`` and
``offload_run_result`` solve an offload on a resolved run and assemble its recorded run
(SP1 step 7). ``run_resolved`` wraps a Result with the
run's name and config. Units are SI; frames: the +z-up ascent datum frame (1-D), planar
ECI (2-D).

The structural model's adapters and search drivers (SP7 step S2; structure.py holds the
physics and the search, pure): ``stack_masses`` and ``structure_pad_cases`` turn a pad
baseline's Vehicle and planar Result into structure.py's stage masses and load cases (the
envelope), ``constant_accel_push_load`` builds the analytic push (no trajectory flown),
``structure_sizing`` makes the screened search's sizing callable from a structure file,
``structure_search_inputs`` flies a committed experiment's pad baseline for it,
``time_structure_sizing`` times one sizing (the rate the search's fallbacks are chosen
by), ``structure_screened_search`` runs searches A to C, and ``structure_sets_record`` and
``structure_search_method`` give the structure file's frozen ``sets`` block as plain data
(the caller writes it; frame: the stack axis).

The coupling to the offload solve (SP7 step S3; docs/physics.md, "Coupling the structure
to the offload solve"): ``StructureTransform`` is the vehicle transform of a structural
offload case (``offload.VehicleTransform``), built once per case by
``build_structure_transform`` (the geometry from the full-load vehicle, the envelope from
the pad's own flight, closed over) or, from a resolved case and its pad,
``offload_structure_transform``; each call sizes the analytic constant_accel push of the
vehicle it is given by a short fixed-point iteration and adds dm to the stages' dry
masses (``charge_structure``); ``structure_record`` gives the run-level record keys and
``structure_assumption`` the run's assumption line.

The reporting of the structure (SP7 step S3b; docs/physics.md, "Reporting the structure"):
``payload_structure_transform`` builds the transform of a structure payload case (the
payload form, flown by results_io), ``offload_pad_load_set`` is the one seam the pass reads
the pad's envelope cases through, ``offload_structure_inputs`` gives the block-level
``structure_inputs`` record (the envelope per element, the plausibility table, the frozen
sets), ``central_plausibility`` and ``plausibility_factor_for`` the plausibility-scaled
row's factor (D-SP7-33, computed from the envelope), ``structure_flight_cases`` and
``structure_flight_check`` the post-hoc flight check of a recorded run (the rows after the
release against the same envelope, sized and never iterated) and ``with_flight_check`` its
record keys; ``STRUCTURE_ARM_CAVEAT`` is printed beside the structural sensitivity arms.

The reporting pipeline lives in sibling modules. Every name sim.py defined before the
split (plus ``NoAssist``) is re-exported here (``__all__``), so each
``launchsim.sim.<name>`` import path of Phase 1 keeps working; library names sim.py
only imported (numpy, yaml, units, phases constants, ...) are not re-exported, so import
those from the modules that own them:

- ``metrics``: time series, events and the per-run metrics (pure)
- ``compare``: the comparison against the baseline and the sensitivity cases
- ``summary``: the summary.md text (pure)
- ``results_io``: names, run directories, git provenance, writers and the
  ``run_experiment`` / ``run_sweep`` entry points the CLI calls (I/O; see its docstring
  for the results layout)
- ``plots``: the plot writers (I/O)

Monkeypatch seams: ``results_io`` and ``compare.run_sensitivity`` look ``run_resolved``,
``git_info`` and ``_git`` up on this module at call time, so patching ``sim.run`` (which
``run_resolved`` calls), ``sim.run_resolved``, ``sim.git_info`` or ``sim._git`` changes
what the entry points execute, and patching a name that ``simulate`` or ``run`` calls
reaches those two. The offload pass of ``results_io`` (SP1 step 7) also looks up
``solve_resolved_offload``, ``offload_run_result``, ``matched_run``, ``rerun_resolved``,
``with_assumptions`` and the offload assumption texts (``OFFLOAD_ASSUMPTIONS``,
``offload_penalty_assumption``) here at call time, and (SP7 step S3)
``offload_structure_transform``, ``structure_record``, ``structure_assumption``,
``with_structure_items``, ``without_assumptions`` and
``OFFLOAD_STRUCTURE_ASSUMPTIONS``. These are the
only live seams on ``sim``: every other reporting
function (``compare``, ``write_plots``, ``experiment_summary``, ``write_run``,
``metrics_record``, ...) is bound in its owning module, so patching it on ``sim`` has no
effect on the pipeline; patch it on the owning module (``metrics``, ``compare``,
``summary``, ``results_io``, ``plots``) instead.

The result types (``Result``, ``RunResult``) are imported by the sibling modules under
``TYPE_CHECKING`` only, so their string annotations do not resolve there at run time:
``typing.get_type_hints`` on a sibling-module class or function needs
``localns=vars(launchsim.sim)``.
"""

from __future__ import annotations

import itertools
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

import numpy as np
import pandas as pd

from launchsim import structure
from launchsim.assist import NoAssist, build_assist
from launchsim.assist.base import AssistModel, TrackGeometry
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.atmosphere import ATMOSPHERE_ASSUMPTIONS, ambient_scalar
from launchsim.compare import (  # re-exported
    ATTRIBUTION_TERMS,
    BUG_SUSPECT,
    CD_SENSITIVITY_NOTE,
    CD_SENSITIVITY_NOTES,
    CHECK_NA,
    COMPARISON_BASES,
    COMPARISON_BASIS,
    DIMENSIONLESS_UNIT,
    IDENTITY_TOL_MPS,
    INSTANT_VARIANT_NAME,
    PLANAR_CD_SENSITIVITY_NOTE,
    PLANAR_COMPARISON_BASIS,
    PLANAR_FIXED_COMPARISON_BASIS,
    SAME_RELEASE_ALT_TOL_M,
    SAME_RELEASE_SPEED_TOL_MPS,
    SCREENING_NOT_CHECKED,
    SCREENING_OK,
    SENSITIVITY_NONE_DECLARED,
    SENSITIVITY_NONE_FOR_RUNS,
    SENSITIVITY_SKIPPED,
    SENSITIVITY_SWEEP_POINT,
    SI_SUFFIX_CONVERSIONS,
    Anchor,
    MatchedRun,
    SensitivityRow,
    _delta,
    _is_finite_number,
    _is_number,
    _is_numeric_or_missing,
    _is_pandas_missing,
    anchor_from,
    compare,
    compare_planar,
    gamma_sensitivity_step_rad,
    identity_budget,
    matched_attribution,
    payload_equiv_kg,
    perturbed_value,
    run_sensitivity,
    sensitivity_record,
    si_value,
    trajectory_key,
)
from launchsim.config import (
    NO_SEARCH,
    PLANAR_2D,
    SEARCHED_FIGURES,
    STRUCTURE_SET_NAMES,
    STRUCTURE_SIZING_FULL_LOAD,
    ChecksConfig,
    ResolvedExperiment,
    ResolvedOffloadCase,
    ResolvedRun,
    ResolvedStructureCase,
    ResolvedStructurePayloadCase,
    RunConfig,
    StructureConfig,
    StructureFile,
)
from launchsim.constants import MU_EARTH_M3S2, P_SEA_LEVEL_PA
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    ConstantGravity,
    Gravity,
    InverseSquareGravity,
    PlanarDynamics2D,
    g_eff_track,
)
from launchsim.guidance import GuidanceSpec, solve_delta_for_gamma
from launchsim.losses import (
    AssistEnergyBudget,
    ClosureTerms,
    LossBudget,
    assist_energy_budget,
    loss_budget,
    rocket_equation_closure,
)
from launchsim.metrics import (  # re-exported
    EVENT_COLUMNS,
    EVENT_TEXT_COLUMNS,
    REQUIRED_METRICS,
    RESERVED_METRIC_KEYS,
    TIMESERIES_COLUMNS,
    TIMESERIES_TEXT_COLUMNS,
    TRACK_COLUMNS,
    TRACK_METRIC_ALIASES,
    _peak_felt,
    _phase_samples,
    _rel_release,
    _track_rows,
    carriage_park_altitude_m,
    descent_crossing,
    descent_crossing_time_s,
    empty_events,
    empty_timeseries,
    events_frame,
    failed_ignition_flags,
    failed_ignition_metrics,
    ignition_timing_metrics,
    last_burn_end_s,
    metrics_record,
    run_metrics,
    sample_trace,
    track_flags,
    track_metrics,
)
from launchsim.metrics_planar import (  # re-exported
    PLANAR_EVENT_COLUMNS,
    PLANAR_REQUIRED_METRICS,
    PLANAR_TIMESERIES_COLUMNS,
    SEARCH_METRIC_KEYS,
    closure_metrics,
    empty_planar_events,
    empty_planar_timeseries,
    events_frame_planar,
    fixed_guidance_metrics,
    offload_metrics,
    planar_run_metrics,
    planar_track_metrics,
    ramp_start_metrics,
    sample_trace_planar,
    search_metrics,
)
from launchsim.offload import (
    OffloadResult,
    ProblemFactory,
    VehicleTransform,
    planar_problem_factory,
    solve_offload,
)
from launchsim.orbit import TargetOrbit
from launchsim.phases import (
    ASSIST_KIND,
    HOLD_KIND,
    AscentStart,
    IgnitionSpec,
    IntegratorSettings,
    PhaseResult,
    RunTrace,
    VerticalPlanner,
)
from launchsim.phases.planar import (
    FAIRING_EVENT,
    LIT_KINDS,
    PLANAR_MODEL,
    PlanarEnvironment,
    PlanarPlanner,
)
from launchsim.phases.prelude import resolve_stage_ignitions
from launchsim.plots import (  # re-exported
    PLANAR_PLOT_PANELS,
    PLOT_ABSCISSA,
    PLOT_ABSCISSA_LABEL,
    PLOT_DPI,
    PLOT_FIGSIZE_IN,
    PLOT_GRID_COLOR,
    PLOT_GRID_LINE_WIDTH,
    PLOT_LINE_WIDTH,
    PLOT_PANELS,
    PLOT_SERIES_COLOR,
    PLOT_SERIES_COLORS,
    PLOT_STEM_UNSAFE,
    PLOT_TRACK_PANELS,
    PlotPanel,
    _plot_text,
    planar_plot_panels,
    plot_panels,
    plot_stem,
    write_planar_plots,
    write_plots,
)
from launchsim.results_io import (  # re-exported
    CSV_FLOAT_FORMAT,
    FAILED_MARKER,
    GIT_EXCLUDE_RESULTS,
    GIT_TIMEOUT_S,
    MAX_DIR_SUFFIX,
    MAX_NAME_LEN,
    NAME_PATTERN,
    NOT_A_REPO_MARKER,
    PLANAR_SWEEP_INDEX_METRICS,
    PLANAR_SWEEP_INDEX_TEXT,
    RESERVED_RUN_NAME_PATTERN,
    SWEEP_INDEX_FIXED_COLUMNS,
    SWEEP_INDEX_METRICS,
    TIMESTAMP_FORMAT,
    WINDOWS_DEVICE_NAMES,
    BoundRow,
    ExperimentResult,
    InvalidNameError,
    SweepResult,
    _git,
    _metrics_dict,
    _repo_root_of,
    _resolved_config_dict,
    _run_sweeps_into,
    check_name,
    check_result_names,
    check_run_name,
    git_info,
    is_planar,
    json_safe,
    make_run_dir,
    planar_bounds,
    planar_comparisons,
    planar_experiment_result,
    planar_sweep_index_frame,
    reference_payload_kg,
    run_experiment,
    run_sweep,
    sweep_index_frame,
    utc_timestamp,
    write_csv,
    write_failure_marker,
    write_json,
    write_run,
    write_single,
    write_summary,
    write_timeseries,
    write_yaml,
)
from launchsim.search import (
    FINAL_MODE,
    INFEASIBLE,
    SearchBudget,
    SearchContext,
    SearchRecord,
    WarmEntry,
    WarmStore,
    run_search,
)
from launchsim.structure import (
    FLIGHT,
    HOLD,
    PUSH,
    SET_PHYSICS_HIGH,
    SET_PHYSICS_LOW,
    STAGE1,
    STAGE2,
    CoefficientRange,
    CoefficientValue,
    Envelope,
    FlightCheck,
    Increment,
    LoadCase,
    PadLoadSet,
    Plausibility,
    PushLoad,
    RampedPlateau,
    ReleaseState,
    ScreenedSearch,
    SearchEvaluator,
    SizingCase,
    SizingFn,
    StackGeometry,
    StackLayout,
    StackMasses,
    StageMasses,
    StructureFlag,
    build_geometry,
    flight_exceedance,
    flight_load_set,
    implied_stack_length_m,
    pad_load_set,
    plausibility,
    screened_search,
    size,
)
from launchsim.summary import (  # re-exported
    CALIBRATION_BANNER,
    DISPLAY_ZERO_ABS,
    EXCESS_NOISE_MPS,
    FAILED_ROWS,
    FINDINGS_BLOCKED,
    FIXED_GUIDANCE_LABEL,
    FLIGHT_BURN_AFTER_KEY,
    FLIGHT_BURN_ROWS,
    NOT_A_FIGURE_OF_MERIT,
    NOT_UNTIL_PHASE2,
    PLANAR_VARIANT_ROWS,
    SENSITIVITY_CASE_COLUMNS,
    SENSITIVITY_HEADER,
    STEP_STARTUP_KIND,
    STRUCTURE_ARM_CAVEAT,
    STRUCTURE_FLIGHT_CHECK_SCOPE,
    STRUCTURE_PAYLOAD_CONTRACTION_MAX,
    STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA,
    STRUCTURE_PAYLOAD_RECORD_KIND,
    STRUCTURE_PAYLOAD_RESIDUAL_FRACTION,
    SWEEP_OPTIMIZED_LABEL,
    VARIANT_ROWS,
    VariantRow,
    _excess_text,
    _flight_burn_differs,
    _fmt,
    _signed,
    _table,
    _variant_cell,
    assumptions_section,
    checks_section,
    experiment_summary,
    first_stage_name,
    flags_section,
    git_label,
    guidance_label,
    identity_lines,
    ignition_rows,
    payload_yardstick_lines,
    planar_experiment_summary,
    planar_sweep_summary,
    provenance_lines,
    sensitivity_table,
    step_startup_note,
    sweep_point_header,
    sweep_summary,
    variant_rows,
    variants_table,
)
from launchsim.units import from_g, to_g
from launchsim.vehicle import (
    OffloadMode,
    Vehicle,
    propellant_burned_kg,
    with_offload,
    with_payload,
    with_stage_dry_mass,
)

# Every name sim.py defined before the split (Phase 1), whether defined here or
# re-exported from the reporting modules, plus NoAssist (tests build a pad run with
# sim.NoAssist()): the stable import surface of launchsim.sim. Phase 2 adds the planar
# pipeline (defined here, or re-exported from compare and metrics_planar).
__all__ = [
    "ATTRIBUTION_TERMS",
    "BUG_SUSPECT",
    "CALIBRATION_BANNER",
    "CD_SENSITIVITY_NOTE",
    "CD_SENSITIVITY_NOTES",
    "CHECK_NA",
    "COMPARISON_BASES",
    "COMPARISON_BASIS",
    "CSV_FLOAT_FORMAT",
    "DIMENSIONLESS_UNIT",
    "DISPLAY_ZERO_ABS",
    "EVENT_COLUMNS",
    "EVENT_TEXT_COLUMNS",
    "EXCESS_NOISE_MPS",
    "FAILED_IGNITION_ASSUMPTIONS",
    "FAILED_IGNITION_TRACK_ASSUMPTIONS",
    "FAILED_MARKER",
    "FAILED_ROWS",
    "FINDINGS_BLOCKED",
    "FIXED_GUIDANCE_ASSUMPTIONS",
    "FIXED_GUIDANCE_LABEL",
    "FIXED_GUIDANCE_STATUS",
    "FLIGHT_BURN_AFTER_KEY",
    "FLIGHT_BURN_ROWS",
    "GIT_EXCLUDE_RESULTS",
    "GIT_TIMEOUT_S",
    "GUIDANCE_FAILED_STATUS",
    "IDENTITY_TOL_MPS",
    "INSTANT_VARIANT_NAME",
    "MAX_DIR_SUFFIX",
    "MAX_NAME_LEN",
    "NAME_PATTERN",
    "NOT_A_FIGURE_OF_MERIT",
    "NOT_A_REPO_MARKER",
    "NOT_UNTIL_PHASE2",
    "OFFLOAD_ASSUMPTIONS",
    "OFFLOAD_STRUCTURE_ASSUMPTIONS",
    "OMEGA_P_PHASE1_RADS",
    "PHASE1_ASSUMPTIONS",
    "PLANAR_ASSUMPTIONS",
    "PLANAR_AZIMUTH_ASSUMPTION",
    "PLANAR_CD_SENSITIVITY_NOTE",
    "PLANAR_COMPARISON_BASIS",
    "PLANAR_EVENT_COLUMNS",
    "PLANAR_EXACT_AZIMUTH_RAD",
    "PLANAR_FAILED_IGNITION_ASSUMPTIONS",
    "PLANAR_FIXED_COMPARISON_BASIS",
    "PLANAR_MODEL",
    "PLANAR_PLOT_PANELS",
    "PLANAR_REQUIRED_METRICS",
    "PLANAR_SWEEP_INDEX_METRICS",
    "PLANAR_SWEEP_INDEX_TEXT",
    "PLANAR_TIMESERIES_COLUMNS",
    "PLANAR_VARIANT_ROWS",
    "PLOT_ABSCISSA",
    "PLOT_ABSCISSA_LABEL",
    "PLOT_DPI",
    "PLOT_FIGSIZE_IN",
    "PLOT_GRID_COLOR",
    "PLOT_GRID_LINE_WIDTH",
    "PLOT_LINE_WIDTH",
    "PLOT_PANELS",
    "PLOT_SERIES_COLOR",
    "PLOT_SERIES_COLORS",
    "PLOT_STEM_UNSAFE",
    "PLOT_TRACK_PANELS",
    "REQUIRED_METRICS",
    "RESERVED_METRIC_KEYS",
    "RESERVED_RUN_NAME_PATTERN",
    "RUN_MODEL_ASSUMPTIONS",
    "SAME_RELEASE_ALT_TOL_M",
    "SAME_RELEASE_SPEED_TOL_MPS",
    "SCREENING_NOT_CHECKED",
    "SCREENING_OK",
    "SEARCH_ASSUMPTIONS",
    "SENSITIVITY_CASE_COLUMNS",
    "SENSITIVITY_HEADER",
    "SENSITIVITY_NONE_DECLARED",
    "SENSITIVITY_NONE_FOR_RUNS",
    "SENSITIVITY_SKIPPED",
    "SENSITIVITY_SWEEP_POINT",
    "SIM_ASSUMPTIONS",
    "SI_SUFFIX_CONVERSIONS",
    "SKIPPED_STATUS_PREFIX",
    "STEP_STARTUP_KIND",
    "STRUCTURE_ARM_CAVEAT",
    "STRUCTURE_FLIGHT_CHECK_SCOPE",
    "STRUCTURE_PAYLOAD_CONTRACTION_MAX",
    "STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA",
    "STRUCTURE_PAYLOAD_RECORD_KIND",
    "STRUCTURE_PAYLOAD_RESIDUAL_FRACTION",
    "SWEEP_INDEX_FIXED_COLUMNS",
    "SWEEP_INDEX_METRICS",
    "SWEEP_OPTIMIZED_LABEL",
    "TIMESERIES_COLUMNS",
    "TIMESERIES_TEXT_COLUMNS",
    "TIMESTAMP_FORMAT",
    "TRACK_ASSUMPTIONS",
    "TRACK_COLUMNS",
    "TRACK_METRIC_ALIASES",
    "VARIANT_ROWS",
    "WINDOWS_DEVICE_NAMES",
    "Anchor",
    "BoundRow",
    "ExperimentResult",
    "InvalidNameError",
    "MatchedRun",
    "NoAssist",
    "PlanarSetup",
    "PlotPanel",
    "Result",
    "RunResult",
    "SensitivityRow",
    "Status",
    "SweepResult",
    "VariantRow",
    "_delta",
    "_excess_text",
    "_flight_burn_differs",
    "_fmt",
    "_git",
    "_is_finite_number",
    "_is_number",
    "_is_numeric_or_missing",
    "_is_pandas_missing",
    "_metrics_dict",
    "_peak_felt",
    "_phase_samples",
    "_plot_text",
    "_rel_release",
    "_repo_root_of",
    "_resolved_config_dict",
    "_run_sweeps_into",
    "_signed",
    "_table",
    "_track_rows",
    "_variant_cell",
    "anchor_from",
    "assumptions_section",
    "carriage_park_altitude_m",
    "check_name",
    "check_resolved",
    "check_result_names",
    "check_run_name",
    "checks_section",
    "closure_metrics",
    "compare",
    "compare_planar",
    "descent_crossing",
    "descent_crossing_time_s",
    "empty_events",
    "empty_planar_events",
    "empty_planar_timeseries",
    "empty_timeseries",
    "events_frame",
    "events_frame_planar",
    "every_resolved_run",
    "experiment_summary",
    "failed_ignition_flags",
    "failed_ignition_metrics",
    "first_stage_name",
    "fixed_guidance_metrics",
    "flags_section",
    "fly_without_search",
    "gamma_sensitivity_step_rad",
    "git_info",
    "git_label",
    "gravity_assumption",
    "guidance_failed_result",
    "guidance_label",
    "identity_budget",
    "identity_lines",
    "ignition_rows",
    "ignition_specs",
    "ignition_timing_metrics",
    "is_planar",
    "json_safe",
    "last_burn_end_s",
    "make_run_dir",
    "matched_attribution",
    "matched_run",
    "metrics_record",
    "offload_penalty_assumption",
    "offload_problem_factory",
    "offload_run_result",
    "payload_equiv_kg",
    "payload_yardstick_lines",
    "perturbed_value",
    "planar_assumption_list",
    "planar_bounds",
    "planar_comparisons",
    "planar_experiment_result",
    "planar_experiment_summary",
    "planar_plot_panels",
    "planar_ramp_start_items",
    "planar_run_assumptions",
    "planar_run_metrics",
    "planar_setup",
    "planar_startup_items",
    "planar_sweep_index_frame",
    "planar_sweep_summary",
    "planar_track_metrics",
    "plot_panels",
    "plot_stem",
    "provenance_lines",
    "ramp_start_metrics",
    "reference_payload_kg",
    "rerun_planar",
    "rerun_resolved",
    "run",
    "run_experiment",
    "run_ignition_specs",
    "run_metrics",
    "run_planar",
    "run_resolved",
    "run_sensitivity",
    "run_sweep",
    "sample_trace",
    "sample_trace_planar",
    "search_context",
    "search_failed_result",
    "search_metrics",
    "sensitivity_record",
    "sensitivity_table",
    "si_value",
    "simulate",
    "simulate_planar",
    "solve_resolved_offload",
    "step_startup_note",
    "sweep_index_frame",
    "sweep_point_header",
    "sweep_summary",
    "track_flags",
    "track_metrics",
    "trajectory_key",
    "utc_timestamp",
    "variant_rows",
    "variants_table",
    "with_assumptions",
    "without_assumptions",
    "write_csv",
    "write_failure_marker",
    "write_json",
    "write_planar_plots",
    "write_plots",
    "write_run",
    "write_single",
    "write_summary",
    "write_timeseries",
    "write_yaml",
]


Status = Literal[
    "nominal",
    "impact",
    "no_liftoff",
    "drive_limit",
    "inserted",
    "off_target",
    "short_of_orbit",
    "search_failed",
    "guidance_failed",
    "bug_suspect",
]
"""Run statuses: the 1-D ones (nominal, impact, no_liftoff, drive_limit); a planar
recorded run's inserted (the energy cutoff inside the LTG acceptance), off_target (the
cutoff outside it), short_of_orbit (stage 2 burned out first); search_failed (no
recorded run); guidance_failed (a run flown at fixed guidance whose guidance raised a
typed failure, no recorded run); bug_suspect (a planar run failing a per-run check:
closure, identity, insertion e)."""
PLANAR_EXACT_AZIMUTH_RAD = 0.5 * math.pi
"""The launch azimuth [rad] (due east) at which the planar model is exact in inclination
(i = lat); any other azimuth raises the planar-azimuth run flag and adds
PLANAR_AZIMUTH_ASSUMPTION (amendment 13)."""
PLANAR_AZIMUTH_ASSUMPTION = (
    "the launch azimuth is not due east, so the orbit's inclination differs from the "
    "site latitude; the planar model (omega_p = omega_E cos(lat) sin(az), the site "
    "velocity's out-of-plane part and the air's out-of-plane velocity neglected) is an "
    "approximation for this run"
)
"""The assumption line of a run whose azimuth is not PLANAR_EXACT_AZIMUTH_RAD."""


PHASE1_ASSUMPTIONS: tuple[str, ...] = (
    "1-D vertical motion",
    "vacuum thrust from sea level (no back-pressure), no atmosphere, no drag",
    "no Earth rotation (omega_p = 0), Coriolis neglected",
    "no throttling; instantaneous cutoff at propellant depletion",
)
# Phase 1 runs without Earth rotation: the planar rate ``run`` hands to g_eff_track, the
# one place the value lives (the assumption string below quotes it).
OMEGA_P_PHASE1_RADS = 0.0
# What ``run`` fixes and ``simulate`` cannot know from its arguments alone: the run
# model's gravity and the origin of its g_eff (simulate states the model it was handed).
RUN_MODEL_ASSUMPTIONS: tuple[str, ...] = (
    "pad and track g_eff = mu/R_E^2 - omega_p^2 R_E with omega_p = "
    f"{OMEGA_P_PHASE1_RADS:g} rad/s, continuous with mu/r^2 at z = 0",
)


@dataclass(frozen=True)
class Result:
    """Outcome of one run (SI; times are seconds since the run's internal t = 0).

    metrics: flat name -> value dict (numbers, strings, None); written to metrics.json.
    timeseries: sampled state, columns TIMESERIES_COLUMNS (t_s, z_m, v_mps, m_kg,
    t_rel_release_s, thrust_N, thrust_vac_N, accel_felt_g, phase, stage, J_*_mps).
    events: logged events, columns EVENT_COLUMNS (t_s, event, phase, stage, z_m, v_mps,
    m_kg).
    loss_budget: LossBudget from release onward (all zero when the run never flew);
    assist_budget: the AssistEnergyBudget of the push (None for a pad).
    assumptions: attributed assumption strings for the summary.
    phases: the PhaseResult list of the run.
    status: a Status (1-D: nominal, impact, no_liftoff or drive_limit).
    flags: warnings such as interface_tensile, drive_braking or a disarmed event.
    model: the dynamics model (vertical_1d; planar_2d for ``simulate_planar``, whose
    time series has PLANAR_TIMESERIES_COLUMNS and events PLANAR_EVENT_COLUMNS).
    search: the planar SearchRecord (None for the 1-D model and a run without a
    search); closure: the planar rocket-equation ClosureTerms (None without a stage-2
    burn); trace: the planar recorded RunTrace (None for the 1-D model and a failed
    search; the matched-payload attribution and the mechanism checks read it).
    """

    metrics: dict[str, Any]
    timeseries: pd.DataFrame
    loss_budget: LossBudget | None
    assist_budget: AssistEnergyBudget | None
    assumptions: list[str]
    phases: list[PhaseResult]
    status: Status
    flags: list[str]
    events: pd.DataFrame = field(default_factory=empty_events)
    model: str = "vertical_1d"
    search: SearchRecord | None = None
    closure: ClosureTerms | None = None
    trace: RunTrace | None = None


@dataclass(frozen=True)
class RunResult:
    """A resolved run together with its Result."""

    name: str
    resolved: ResolvedRun
    result: Result


# ------------------------------------------------------------------------ simulate

SIM_ASSUMPTIONS: tuple[str, ...] = (
    "loss quadratures reset at release; the identity is accounted from release onward",
    "a vehicle at rest on the ground is clamped until its thrust exceeds its weight; no "
    "gravity loss accrues while clamped (propellant burned then is reported as burned "
    "before flight)",
    "felt axial acceleration is T/m in flight (vacuum thrust, unthrottled), g_eff while "
    "clamped and (F_int + T)/m_v = sddot + g_eff sin phi on the track",
)
TRACK_ASSUMPTIONS: tuple[str, ...] = (
    "track phase: 1-DOF along the track in a flat local frame with constant g_eff; the "
    "carriage stays on the track at release; carriage braking is not modelled as a phase "
    "(its distance v^2/(2 a_brake) is added to the facility length)",
    "hot start: the propellant burned before release is reported with its delta-v "
    "equivalent; the exhaust impingement fraction f_imp on the carriage is an assumed "
    "amendment to the track equation (the system keeps (1 - f_imp) T)",
    "drive energy: electrical_energy = (positive drive work) / efficiency; no regeneration "
    "is credited for any negative (braking) drive work",
)
# Added to a run in which a stage's ignition failed and the unpowered fall-back coast
# actually ran (docs/physics.md, "Failed-ignition coast"): what that coast leaves out.
FAILED_IGNITION_ASSUMPTIONS: tuple[str, ...] = (
    "failed ignition: the fall-back coast is drag-free (no atmosphere in Phase 1; "
    "docs/physics.md, 'Failed-ignition coast', gives the order of magnitude of the "
    "neglected drag for the F9 class at its exit speed)",
    "failed ignition: no abort is modelled (a tilted exit that carries the vehicle clear "
    "of the mouth is the planar branch of Phase 2/3); Coriolis drift during the coast is "
    "neglected (omega_p = 0)",
)
# Added on top of FAILED_IGNITION_ASSUMPTIONS when the failed run had a track.
FAILED_IGNITION_TRACK_ASSUMPTIONS: tuple[str, ...] = (
    "failed ignition: the braked carriage parks its braking distance beyond the track "
    "exit, in the fall-back path (failed_carriage_alt_m); the vehicle would meet it "
    "there first, on the way down (failed_t_carriage_s, failed_speed_at_carriage_mps, "
    "from the drag-free coast), unless the carriage is withdrawn in time, and no impact "
    "with it is modelled: the return to the mouth, the impact at the ground and the "
    "shaft-bottom speed are the obstacle-free values",
    "failed ignition: the speed at the shaft bottom is derived from the impact speed at "
    "the ground and the fall from there to the track start (v^2 = v_impact^2 + 2 g_eff "
    "(z_impact - z_track_start)), not integrated",
)


def gravity_assumption(gravity: Gravity) -> str:
    """The assumption line naming the ascent gravity model ``simulate`` was handed."""
    if isinstance(gravity, InverseSquareGravity):
        return (
            f"gravity mu/r^2 in flight (mu = {gravity.mu_m3s2:.10g} m^3/s^2; "
            "InverseSquareGravity, the run model; ConstantGravity exists only for tests)"
        )
    if isinstance(gravity, ConstantGravity):
        return (
            f"constant gravity g = {gravity.g_mps2:.7g} m/s^2 in flight (analytic test model, "
            "not the run model)"
        )
    return f"gravity model {type(gravity).__name__} in flight"


def simulate(
    vehicle: Vehicle,
    ignition: Mapping[str, IgnitionSpec],
    gravity: Gravity,
    g_eff_mps2: float,
    assist: AssistModel,
    track: TrackGeometry | None,
    start: AscentStart | None,
    end: str,
    settings: IntegratorSettings,
) -> Result:
    """Run one configuration and return its Result (pure: no I/O).

    Inputs: the Vehicle; ignition, an IgnitionSpec per stage name; gravity, the ascent
    Gravity (``run`` passes InverseSquareGravity(MU); tests may inject
    ConstantGravity); g_eff_mps2, the pad/track effective gravity [m/s^2] and the
    reference g_ref of the gravity-loss split; assist, the assist model (``NoAssist``
    for a pad, ``ConstantAccelAssist`` with its track otherwise); track, the track
    geometry (None for a pad; required for any other model); start, the AscentStart
    of a pad run (z0, v0 at release; None = the pad at rest; a track run accepts only
    the default); end, one of phases.END_KINDS; settings, the IntegratorSettings.
    Output: a Result with the sampled time series, the events, the metrics, the
    LossBudget from release onward, the AssistEnergyBudget of the push (None for a
    pad), the run's status (nominal, impact, no_liftoff, drive_limit) and flags
    (``interface_tensile`` is evaluated over the ASSIST rows only; ``drive_braking``
    when the drive did negative work). A run in which a stage's ignition failed
    (``IgnitionSpec.fails``) carries the ``failed_*`` metrics
    (``failed_ignition_metrics``), the ``failed_ignition_flags`` (a track mouth not at
    the ground) and, when its fall-back coast actually ran (``t_fail_s`` set: not a
    pad ``no_liftoff``), FAILED_IGNITION_ASSUMPTIONS plus the carriage lines of
    FAILED_IGNITION_TRACK_ASSUMPTIONS when it had a track. Every run also carries the
    constant-g ignition-timing yardsticks of ``ignition_timing_metrics``
    (``ignition_loss_formula_mps``, ``preflight_burn_cost_mps``). The assumptions
    name the gravity model and the g_eff actually used, not the run model's (``run``
    adds those).
    """
    planner = VerticalPlanner(vehicle, ignition, gravity, g_eff_mps2, end, settings)
    if track is None:
        if assist.name != "none":
            raise ValueError(f"assist model {assist.name!r} needs a track")
        trace = planner.run_pad(AscentStart() if start is None else start)
    else:
        if assist.name == "none":
            raise ValueError("a track was given with the 'none' assist model")
        if start is not None and start != AscentStart():
            raise ValueError("a track run starts at rest at the track start; no AscentStart")
        trace = planner.run_track(assist, track)
    budget = loss_budget(trace.ascent_phases())
    frame = sample_trace(trace, vehicle, settings)
    metrics = run_metrics(trace, vehicle, budget, frame, assist.name)
    metrics.update(ignition_timing_metrics(trace, vehicle, ignition, g_eff_mps2, metrics))
    flags = list(trace.flags)
    assumptions = [
        *PHASE1_ASSUMPTIONS,
        gravity_assumption(gravity),
        f"pad/track effective gravity g_eff = {g_eff_mps2:.7g} m/s^2, also the g_ref of the "
        "gravity-loss split",
        *SIM_ASSUMPTIONS,
    ]
    assist_budget: AssistEnergyBudget | None = None
    if track is not None:
        assist_phases = trace.assist_phases()
        assist_budget = assist_energy_budget(
            assist_phases,
            assist_phases[0].spec.params.layout,
            assist.carriage_mass_kg,
            g_eff_mps2,
        )
        metrics.update(track_metrics(trace, assist, track, assist_budget, frame))
        flags += track_flags(frame, metrics["drive_work_out_J"])
        assumptions += [
            *TRACK_ASSUMPTIONS,
            f"track: straight, L = {track.length_m:.6g} m at {track.phi(0.0):.6g} rad above "
            f"horizontal, start altitude {track.start_altitude_m:.6g} m (exit at "
            f"{track.start_altitude_m + track.z(track.length_m):.6g} m)",
        ]
    if trace.failed_stage is not None:
        metrics.update(failed_ignition_metrics(trace, g_eff_mps2, assist, track))
        flags += failed_ignition_flags(trace, track, planner.z_ground_m)
        if trace.t_fail_s is not None:  # the coast ran (not a pad no_liftoff)
            assumptions += FAILED_IGNITION_ASSUMPTIONS
            if track is not None:
                assumptions += FAILED_IGNITION_TRACK_ASSUMPTIONS
    assumptions += [*trace.assumptions, *assist.assumptions()]
    return Result(
        metrics=metrics,
        timeseries=frame,
        loss_budget=budget,
        assist_budget=assist_budget,
        assumptions=assumptions,
        phases=list(trace.phases),
        status=trace.status,  # type: ignore[arg-type]
        flags=flags,
        events=events_frame(trace),
    )


def ignition_specs(
    run_config: RunConfig,
    vehicle: Vehicle,
    assist: AssistModel,
    track: TrackGeometry | None,
    g_eff_mps2: float,
) -> dict[str, IgnitionSpec]:
    """One IgnitionSpec per stage from the run's ignition block (defaults when absent)
    through ``phases.prelude.resolve_stage_ignitions`` (``resolve_ignition`` per stage):
    startup overrides resolved against the vehicle's own Startup, and a ramp start
    stated by depth, speed or closed-form height converted to a time with the run's
    assist model, its track and the track's g_eff [m/s^2] (a height reached by the
    altitude event stays a height, checked against the same drag-free apex; ValueError
    when the conversion or that check is refused, and for such a ramp start on a stage
    after the first)."""
    return resolve_stage_ignitions(run_config, vehicle, assist, track, g_eff_mps2)


def run(run_config: RunConfig, vehicle: Vehicle) -> Result:
    """Run one validated configuration (SI) and return its Result.

    A planar_2d run goes to ``run_planar`` (the dispatch on ``dynamics``). A vertical_1d
    run, byte for byte as in Phase 1: builds InverseSquareGravity(MU_EARTH_M3S2) for the
    ascent, g_eff = g_eff_track(0) (omega_p = 0 in Phase 1, stated in the assumptions)
    for the pad and the track, the
    IgnitionSpecs from the config, the assist model and its track
    (``assist.build_assist``), and calls ``simulate``; RUN_MODEL_ASSUMPTIONS go in front
    of the assumptions ``simulate`` derived from what it was handed.
    """
    if run_config.dynamics == PLANAR_2D:
        return run_planar(run_config, vehicle)
    g_eff = g_eff_track(OMEGA_P_PHASE1_RADS)
    assist, track = build_assist(run_config.assist, g_eff)
    result = simulate(
        vehicle=vehicle,
        ignition=ignition_specs(run_config, vehicle, assist, track, g_eff),
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=g_eff,
        assist=assist,
        track=track,
        start=AscentStart(),
        end=run_config.end,
        settings=IntegratorSettings.from_config(run_config.integrator),
    )
    return replace(result, assumptions=[*RUN_MODEL_ASSUMPTIONS, *result.assumptions])


def run_resolved(resolved: ResolvedRun) -> RunResult:
    """Run a ResolvedRun and wrap the Result with its name and config. Every exception
    propagates (FAILED.txt is written by the caller)."""
    vehicle = resolved.to_vehicle()
    return RunResult(resolved.name, resolved, run(resolved.run, vehicle))


def run_ignition_specs(run_config: RunConfig, vehicle: Vehicle) -> dict[str, IgnitionSpec]:
    """The IgnitionSpecs a validated run will fly, built as ``run`` builds them, without
    integrating anything: on planar_2d through ``planar_setup`` (the site's g_ref as the
    track's g_eff; the assist model, its track, the guidance spec and the shared budget
    are built on the way), on vertical_1d with g_eff_track(0) and ``build_assist``.
    Raises ValueError where a run would (a refused ramp-start conversion)."""
    if run_config.dynamics == PLANAR_2D:
        return planar_setup(run_config, vehicle).ignition
    g_eff = g_eff_track(OMEGA_P_PHASE1_RADS)
    assist, track = build_assist(run_config.assist, g_eff)
    return ignition_specs(run_config, vehicle, assist, track, g_eff)


def every_resolved_run(resolved: ResolvedExperiment) -> list[tuple[str, ResolvedRun]]:
    """Every run an experiment resolves, labelled by where it comes from: the baseline
    and the variants (``run 'name'``), every sweep point and its paired baseline
    (``sweep k point run_NNNN``), every sensitivity run, every bound run with its
    paired baseline, every calibration case and, with an offload block (SP1 step 7),
    the start of every offload case of a sweep point and of the block, every paired-pad
    start and every offload sensitivity run (its perturbed pad too)."""
    out = [(f"run {name!r}", run) for name, run in resolved.runs.items()]
    for points in resolved.sweeps:
        for point in points:
            out.append((f"sweep {point.sweep_index} point {point.run.name}", point.run))
            if point.paired_baseline is not None:
                paired = point.paired_baseline
                out.append((f"sweep {point.sweep_index} point {paired.name}", paired))
    out += [(f"sensitivity run {case.run.name!r}", case.run) for case in resolved.sensitivity]
    for bound in resolved.bounds:
        for run in (*bound.runs.values(), bound.baseline):
            out.append((f"bound {bound.name!r} run {run.name!r}", run))
    out += [(f"case {name!r}", run) for name, run in resolved.cases.items()]
    for points in resolved.sweeps:
        for point in points:
            for case in point.offload:
                label = f"sweep {point.sweep_index} point {point.run.name} offload {case.name!r}"
                out.append((label, case.start))
    if resolved.offload is not None:
        for case in resolved.offload.cases:
            out.append((f"offload case {case.name!r}", case.start))
            if case.pad_start is not None:
                out.append((f"offload case {case.name!r} paired pad", case.pad_start))
        for arm in resolved.offload.arms:
            out.append((f"offload sensitivity run {arm.start.name!r}", arm.start))
            if arm.pad_perturbed:
                out.append((f"offload sensitivity run {arm.pad.name!r}", arm.pad))
    return out


def check_resolved(resolved: ResolvedExperiment) -> None:
    """Preflight of an experiment (SP1 step 3; ``results_io.run_experiment`` and
    ``run_sweep`` call it before they create the run directory): build the assist
    model, its track and the IgnitionSpecs of every run the experiment resolves
    (``every_resolved_run``: variants, sweep points, sensitivity runs, bounds, cases)
    as the run will (``run_ignition_specs``), integrating nothing, so a configuration
    refused only when its specs are built (a ramp start at a speed the push never
    reaches, a height at or above the drag-free apex) writes nothing. With a structure
    block (SP7 step S3b) the reference pad must light stage 1 before its hold-down
    release, so that it holds down under thrust above its weight (the skirt's hold-down
    envelope is built from the pad's HOLD rows, ``structure.pad_load_set``, and only such
    a pad gives them the restrained-thrust case); a pad lit at or after the release, at a
    height, or never, is refused here (``structure_block_needs_hold``) rather than after
    the nominal runs have flown. Raises ValueError naming the run and where it comes
    from."""
    for label, run in every_resolved_run(resolved):
        try:
            run_ignition_specs(run.run, run.to_vehicle())
        except ValueError as exc:
            raise ValueError(f"{label}: {exc}") from exc
    if resolved.structure is not None:
        structure_block_needs_hold(resolved.baseline)


def structure_block_needs_hold(pad: ResolvedRun) -> None:
    """Refuse a structure block whose reference pad never holds down under thrust above
    its weight (SP7 step S3b; review N-S3b-R3-02 and its follow-up): the pad's first
    stage must light before the hold-down release (reference "release", t_ign_s < 0, not
    failing and not lit at a height). The skirt's hold-down envelope is built from the
    pad's HOLD rows (``structure.pad_load_set``), and only a pad lit before its release
    holds down with the thrust above the weight, the restrained-thrust case; a pad lit at
    or after the release holds, if at all, through the liftoff extension at TWR < 1
    (``prelude.hold_until_liftoff``: with the shipped 2 s startup ramp its HOLD rows carry
    the weight alone; with a step startup there is no HOLD row and ``pad_load_set``
    raises), so its envelope would lack that case. A modelling choice of the structural
    reference, stricter than the pass's own requirement of one HOLD row, not a failure of
    the run. Raises ValueError naming the pad and how it lights."""
    specs = run_ignition_specs(pad.run, pad.to_vehicle())
    stage1 = pad.to_vehicle().stages[0].name
    spec = specs[stage1]
    if spec.fails:
        how = "never lights stage 1"
    elif spec.lights_at_height:
        how = "lights stage 1 at a height after its hold-down release"
    else:
        t_ign = spec.t_ign_abs_s(0.0, 0.0)
        if t_ign < 0.0:
            return
        how = (
            "lights stage 1 at its hold-down release"
            if t_ign == 0.0
            else f"lights stage 1 {t_ign:g} s after its hold-down release"
        )
    raise ValueError(
        f"structure block: the reference pad {pad.name!r} {how}, so it never holds down "
        "under thrust above its weight: its HOLD rows, if any, come from the liftoff "
        "extension at TWR < 1 and carry the weight alone, and the skirt's hold-down envelope "
        "(structure.pad_load_set, built from the pad's HOLD rows) would lack the "
        "restrained-thrust case; the block needs the pad's stage 1 lit on the pad before the "
        "release (ignition.stage1: {t_ign_s: <0, reference: release}); a modelling choice of "
        "the structural reference, not a failure of the run"
    )


# -------------------------------------------------------------------- planar model

PLANAR_ASSUMPTIONS: tuple[str, ...] = (
    "planar ascent in the plane of the site and the launch azimuth, with omega_p = omega_E "
    "cos(lat) sin(az); the air's out-of-plane velocity omega_E sin(lat) r sin(theta) is "
    "neglected (exact for an equatorial east launch, and for the inertial dynamics, "
    "inclination and site velocity of an az 90 launch at i = lat)",
    "spherical Earth of radius R_E, point-mass gravity mu/r^2, geometric altitude h = r - R_E",
    "the atmosphere co-rotates with Earth and has no wind: drag, Mach, q and gamma_rel use "
    "v_rel = (v_r, v_theta - omega_p r)",
    "point mass: the thrust points where the steering law says, instantly (no attitude "
    "dynamics); the body axis is the thrust axis, so the angle of attack of q-alpha is "
    "psi, the angle between thrust and v_rel",
    "pure drag along -v_rel (no lift, no angle-of-attack dependence), one A_ref for the "
    "whole flight (through staging and the fairing drop)",
    "the power-on C_D table (base drag included) is also used in unlit coasts (a small "
    "bias toward cold starts)",
    "below |v_rel| = 1e-9 m/s the flight-path angle is local vertical (the pad)",
    "loss quadratures accumulate from the flight start (release, or the liftoff root of an "
    "extended hold); a clamped vehicle accrues no gravity loss",
    "stage-1 guidance: a vertical rise with inertially radial thrust, a kick held at the "
    "angle delta from local vertical until the velocity is aligned with it, then a gravity "
    "turn along v_rel; the kick starts at the first lit instant at which |v_rel| >= v_k "
    "while rising; delta is solved so that gamma_rel at MECO equals gamma* (searched per "
    "run, or the shared fixed value of fixed guidance)",
    "the track push is flat and 1-DOF with g_eff = mu/R_E^2 - omega_p^2 R_E and the "
    "constant ambient pressure of the exit; no Coriolis and no air drag in the vented "
    "shaft: under a prescribed net acceleration (constant_accel) the drive force would "
    "absorb that drag, so the release speed is unchanged, and the drive energy, the peak "
    "drive power and the interface force are biased low (by int D v dt, D v_exit and D); "
    "release from a vertical track only",
    "staging is instantaneous and impulse-free; the fairing stays on through staging under "
    "the heating rule unless the criterion is already met there",
    "stage 2 flies linear-tangent steering (tan p = a - b tau in the local horizontal "
    "frame); the engine cuts off instantly when the orbital energy reaches the target's",
    "the fairing is jettisoned instantly and impulse-free when 0.5 rho |v_rel|^3 falls "
    "below the vehicle's limit (in the stage-2 burn, or at stage-2 ignition when the "
    "criterion was met during the staging coast)",
    "no throttling (max-Q and q-alpha are unthrottled and unconstrained: upper bounds on "
    "the flown values), no flight-performance reserve, no unusable residuals; a payload "
    "adapter counts as payload",
    "with rotation a vertical fall-back has u < 0, so gamma_rel = atan2(w, u) wraps "
    "through +/-180 deg at the apex; the time series and events report gamma_rel and the "
    "pitch unwrapped per run (numpy.unwrap; a step within the integrator's angular "
    "tolerance of -pi, the rotation-off apex, is taken as +pi, so a vertical fall reads 3 "
    "pi/2 with or without rotation; the apex itself reads pi/2 without rotation, the "
    "local-vertical fallback, and about pi with it)",
)
"""The assumptions every planar_2d run carries (plan section 5 and amendment 14); the
run-, vehicle- and site-dependent lines come from ``planar_run_assumptions`` (with
SEARCH_ASSUMPTIONS or FIXED_GUIDANCE_ASSUMPTIONS), the atmosphere's from
``atmosphere.ATMOSPHERE_ASSUMPTIONS``."""
SEARCH_ASSUMPTIONS: tuple[str, ...] = (
    "stage 2's (a, b) are solved by shooting for the target radius and zero radial velocity",
    "searches burn virtual stage-2 propellant past the real load, down to a mass floor "
    "(the final verification's evaluations too, at the final tolerance); only the "
    "recorded run carries the real depletion, and one that runs dry before the cutoff "
    "reports its evaluation's signed (negative) m_res and dv_margin. A negative m_res is "
    "a virtual (massless) shortfall, propellant that weighs nothing until burned, not the "
    "load of a larger tank (which would make the shortfall worse)",
    "the residual propellant at the vehicle payload of a payload search is taken at the "
    "P*-optimal gamma*_ref, not re-optimised at P0 (a few kg low, against the assist)",
    '"sweep-optimized" guidance: gamma* is the best point of the shared grid refined by a '
    "bounded Brent search at the first payload estimate, delta and (a, b) are solved for "
    "it, and P* is the largest verified payload with m_res >= 0 (not an optimal-control "
    "solution; Phase 5)",
)
"""The assumptions of a run whose figure of merit is searched (payload, residual)."""
FIXED_GUIDANCE_ASSUMPTIONS: tuple[str, ...] = (
    "fixed guidance (figure_of_merit none): gamma* and the LTG pair (a, b) are shared "
    "fixed inputs, not solved; only delta is solved for gamma* (at the final tolerance); "
    "there is no payload search and no P*, so a run can end off target, and its residual "
    "propellant and dv margin are the recorded run's own at its cutoff",
)
"""The assumptions of a run flown at the shared fixed guidance (stage 1 lit)."""
PLANAR_FAILED_IGNITION_ASSUMPTIONS: tuple[str, ...] = (
    "failed ignition: no abort is modelled; the unpowered coast to the apex and the ground "
    "is flown with drag, rotation and mu/r^2, from the track exit (or the pad)",
)
"""Added to a planar run whose failed-ignition coast ran (the 1-D texts assume no
atmosphere, so they are not reused)."""
FIXED_GUIDANCE_STATUS = "none (fixed guidance)"
"""search_status of a run flown at the shared fixed guidance (figure_of_merit none)."""
SKIPPED_STATUS_PREFIX = "skipped"
"""search_status prefix of a run whose search is skipped (``RunConfig.search_skip_reason``)."""


@dataclass(frozen=True)
class PlanarSetup:
    """What a planar run builds from its RunConfig and Vehicle: env (mu/r^2, omega_p of
    the site, ICAO, datum R_E), the assist model (``constant_accel`` told its omega_p for
    the assumption text) and track (None, NoAssist for a pad; the track's g_eff = g_ref),
    the IgnitionSpec per stage, the stage-1 GuidanceSpec, the shared SearchBudget, the
    TargetOrbit (None without one), the recorded run's IntegratorSettings (rtol =
    final_rtol, dense output on) and the ChecksConfig. SI; frame planar ECI."""

    env: PlanarEnvironment
    assist: AssistModel
    track: TrackGeometry | None
    ignition: dict[str, IgnitionSpec]
    guidance: GuidanceSpec
    budget: SearchBudget
    target: TargetOrbit | None
    settings: IntegratorSettings
    checks: ChecksConfig


def planar_setup(run_config: RunConfig, vehicle: Vehicle) -> PlanarSetup:
    """The PlanarSetup of a validated planar_2d RunConfig and its Vehicle (ValueError for
    a run without the planar block)."""
    planar = run_config.planar
    if planar is None:
        raise ValueError(f"run {run_config.name!r}: planar_2d needs the planar shared block")
    env = PlanarEnvironment(
        InverseSquareGravity(MU_EARTH_M3S2), run_config.site.omega_p_rads, ambient_scalar
    )
    assist, track = build_assist(run_config.assist, env.g_ref_mps2)
    if isinstance(assist, ConstantAccelAssist):
        assist = replace(assist, omega_p_rads=env.omega_p_rads)
    target = planar.target_orbit
    return PlanarSetup(
        env=env,
        assist=assist,
        track=track,
        ignition=ignition_specs(run_config, vehicle, assist, track, env.g_ref_mps2),
        guidance=GuidanceSpec.from_config(planar.guidance),
        budget=SearchBudget.from_config(planar.search, planar.checks),
        target=None if target is None else TargetOrbit(target.radius_m),
        settings=replace(IntegratorSettings.from_config(run_config.integrator), dense_output=True),
        checks=planar.checks,
    )


def search_context(setup: PlanarSetup, vehicle: Vehicle, end: str) -> SearchContext:
    """The SearchContext of a planar setup (the vehicle at its own payload P0)."""
    if setup.target is None:
        raise ValueError("a planar search needs a target orbit")
    return SearchContext(
        vehicle=vehicle,
        ignition=setup.ignition,
        guidance=setup.guidance,
        env=setup.env,
        target=setup.target,
        settings=setup.settings,
        budget=setup.budget,
        assist=None if setup.track is None else setup.assist,
        track=setup.track,
        end=end,
    )


def planar_run_assumptions(
    run_config: RunConfig, vehicle: Vehicle, setup: PlanarSetup
) -> list[str]:
    """The run-, site- and vehicle-dependent planar assumption lines: the guidance
    (SEARCH_ASSUMPTIONS for a searched figure of merit, FIXED_GUIDANCE_ASSUMPTIONS for
    fixed guidance with stage 1 lit, neither for a failed stage-1 ignition); the site
    (latitude and azimuth in deg, omega_p [rad/s], g_ref [m/s^2]) and, away from due
    east, PLANAR_AZIMUTH_ASSUMPTION; the target orbit; the drag model (table,
    interpolation, cd_scale, A_ref); stage 2's startup and exit area; the fairing rule; a
    pad's hold-down convention (stage 1 lit at t_ign before the release at t = 0, its
    startup)."""
    site = run_config.site
    env = setup.env
    lines: list[str] = []
    if run_config.figure_of_merit in SEARCHED_FIGURES:
        lines += SEARCH_ASSUMPTIONS
    elif not setup.ignition[vehicle.stage_names[0]].fails:
        lines += FIXED_GUIDANCE_ASSUMPTIONS
    lines.append(
        f"site latitude {site.latitude_deg:g} deg, azimuth {site.azimuth_deg:g} deg, rotation "
        f"{'on' if site.include_rotation else 'off'}: omega_p = {env.omega_p_rads:.7g} rad/s, "
        f"g_ref = mu/R_E^2 - omega_p^2 R_E = {env.g_ref_mps2:.8g} m/s^2 (the pad balance, the "
        "track's g_eff and the reference of the gravity-loss split)"
    )
    if site.azimuth_rad != PLANAR_EXACT_AZIMUTH_RAD:
        lines.append(PLANAR_AZIMUTH_ASSUMPTION)
    if setup.target is not None:
        lines.append(
            f"target: circular orbit of radius {setup.target.r_m:.9g} m (altitude "
            f"{setup.target.r_m - env.r_datum_m:.6g} m above R_E), energy cutoff"
        )
    aero = vehicle.aero
    if aero is not None:
        lines.append(
            f"drag: C_D(Mach) through the vehicle's {len(aero.table.mach)}-knot power-on "
            f"table (PCHIP, held beyond the end knots) x cd_scale {aero.cd_scale:g}, on "
            f"A_ref = {aero.reference_area_m2:.6g} m^2"
        )
    if vehicle.n_stages > 1:
        s2 = vehicle.stages[1]
        kind = s2.startup.effective_kind
        start = "at full thrust (step startup)" if kind == "step" else f"with a {kind} startup"
        lines.append(
            f"stage 2 ({s2.name}) starts {start}; its exit area {s2.exit_area_total_m2:.6g} "
            "m^2 (the vehicle file's value; the Phase 2 forks mark it assumed, not "
            "published) sets the back-pressure p A_e"
        )
    rule = vehicle.fairing_rule
    if vehicle.fairing_mass_kg > 0.0:
        what = (
            f"dropped when 0.5 rho |v_rel|^3 < {rule.limit_W_m2:.6g} W/m^2"
            if rule.limit_W_m2 is not None
            else {"staging": "dropped with stage 1", "never": "never dropped"}[rule.trigger]
        )
        lines.append(f"fairing ({vehicle.fairing_mass_kg:.6g} kg): {what}")
    stage0 = vehicle.stages[0]
    spec = setup.ignition[stage0.name]
    if setup.track is None and not spec.fails and spec.t_ign_s < 0.0:
        startup = stage0.startup if spec.startup is None else spec.startup
        lines.append(
            f"pad: held down to the release at t = 0 s; stage 1 lit at t = {spec.t_ign_s:g} s "
            f"with a {startup.effective_kind} startup, then clamped until its thrust exceeds "
            "its weight"
        )
    return lines


def _run_flags(run_config: RunConfig) -> list[str]:
    """Run flags of a planar configuration (amendment 13: a flag, never warnings.warn):
    the planar approximation away from due east (site.azimuth_rad !=
    PLANAR_EXACT_AZIMUTH_RAD, so i != lat); the flag quotes the configured azimuth in
    degrees, as the YAML gives it."""
    site = run_config.site
    if site.azimuth_rad == PLANAR_EXACT_AZIMUTH_RAD:
        return []
    return [
        f"planar azimuth: {site.azimuth_deg:g} deg is not due east, so the inclination "
        "differs from the latitude and the planar model (omega_p = omega_E cos(lat) "
        "sin(az)) is approximate"
    ]


def _run_checks(
    trace: RunTrace,
    budget: LossBudget,
    closure: ClosureTerms | None,
    checks: ChecksConfig,
    metrics: dict[str, Any],
) -> list[str]:
    """The per-run checks of the screening-beat rule (docs/physics.md): the
    rocket-equation closure below checks.closure_tol_mps, the loss identity below
    checks.identity_tol_mps and, for an inserted run, e below checks.insertion_e_max.
    Returns the failures (empty when all pass)."""
    failed: list[str] = []
    if closure is not None and not abs(closure.residual_mps) < checks.closure_tol_mps:
        failed.append(
            f"closure residual {closure.residual_mps:.3g} m/s (tolerance "
            f"{checks.closure_tol_mps:g})"
        )
    if trace.ascent_phases() and not abs(budget.residual_mps()) < checks.identity_tol_mps:
        failed.append(
            f"loss-identity residual {budget.residual_mps():.3g} m/s (tolerance "
            f"{checks.identity_tol_mps:g})"
        )
    e = metrics.get("insertion_e")
    if trace.status == "inserted" and e is not None and not e < checks.insertion_e_max:
        failed.append(f"insertion e = {e:.3g} (limit {checks.insertion_e_max:g})")
    return failed


def simulate_planar(
    trace: RunTrace,
    vehicle: Vehicle,
    setup: PlanarSetup,
    *,
    sample_dt_s: float,
    figure_items: dict[str, Any],
    search: SearchRecord | None = None,
    run_flags: Sequence[str] = (),
    run_assumptions: Sequence[str] = (),
) -> Result:
    """Assemble the Result of a recorded planar run (pure: no I/O).

    Inputs: the RunTrace (dense output on: ``RunTrace.require_dense``); the Vehicle it
    flew (a searched run's recorded payload P_final); the PlanarSetup (environment,
    assist and track, checks, target); sample_dt_s [s], the time-series interval;
    figure_items, the figure-of-merit metrics (``metrics_planar.search_metrics`` or
    ``fixed_guidance_metrics``); the SearchRecord (None without a search); run flags and
    run assumptions from the caller. Output: a Result with model planar_2d, the planar
    time series and events, the metrics (``planar_run_metrics``, the track items for a
    push, how stage 1 starts and its ramp start (``planar_ramp_start_items``), the
    figure items, the closure items, ``trace_status``, ``run_checks`` and
    ``run_checks_failed``), the loss budget from the flight start (|v_rel| speed), the
    push's AssistEnergyBudget, the rocket-equation closure (None without a stage-2 burn)
    and the attributed assumptions. status is the trace's (inserted, off_target,
    short_of_orbit, impact, nominal, no_liftoff, drive_limit), or bug_suspect when a
    per-run check fails (closure, identity, insertion e; flagged). Frame: planar ECI.
    """
    trace.require_dense("simulate_planar")
    env, assist, track, checks = setup.env, setup.assist, setup.track, setup.checks
    frame = sample_trace_planar(trace, vehicle, sample_dt_s)
    speed = PlanarDynamics2D(env.omega_p_rads, env.r_datum_m).speed
    budget = loss_budget(trace.ascent_phases(), PLANAR_LAYOUT, speed)
    metrics = planar_run_metrics(
        trace,
        vehicle,
        budget,
        frame,
        assist.name,
        n_points=checks.maxq_scan_points,
        xatol_s=checks.maxq_xatol_s,
        mu_m3s2=env.mu_m3s2,
        target_r_m=None if setup.target is None else setup.target.r_m,
    )
    flags = [*trace.flags, *run_flags]
    assist_budget: AssistEnergyBudget | None = None
    phases = trace.assist_phases()
    if track is not None and phases:
        assist_budget = assist_energy_budget(
            phases, phases[0].spec.params.layout, assist.carriage_mass_kg, env.g_ref_mps2
        )
        metrics.update(planar_track_metrics(trace, assist, track, assist_budget, frame))
        flags += track_flags(frame, metrics["drive_work_out_J"])
    if trace.failed_stage is not None:
        metrics["failed_stage"] = trace.failed_stage
    assumptions = planar_assumption_list(trace, setup, run_assumptions)
    metrics.update(planar_startup_items(vehicle, setup))
    metrics.update(planar_ramp_start_items(trace, vehicle, setup))
    metrics.update(figure_items)
    has_stage2 = vehicle.n_stages > 1 and vehicle.stage_names[1] in trace.burnouts
    closure = rocket_equation_closure(trace, vehicle) if has_stage2 else None
    metrics.update(closure_metrics(closure))
    failed = _run_checks(trace, budget, closure, checks, metrics)
    metrics["trace_status"] = trace.status
    metrics["run_checks"] = BUG_SUSPECT if failed else SCREENING_OK
    metrics["run_checks_failed"] = "; ".join(failed) if failed else None
    flags += [f"{BUG_SUSPECT}: {f}" for f in failed]
    return Result(
        metrics=metrics,
        timeseries=frame,
        loss_budget=budget,
        assist_budget=assist_budget,
        assumptions=assumptions,
        phases=list(trace.phases),
        status=BUG_SUSPECT if failed else trace.status,  # type: ignore[arg-type]
        flags=flags,
        events=events_frame_planar(trace),
        model=PLANAR_MODEL,
        search=search,
        closure=closure,
        trace=trace,
    )


def planar_assumption_list(
    trace: RunTrace, setup: PlanarSetup, run_assumptions: Sequence[str]
) -> list[str]:
    """The assumptions of a planar run, in order: PLANAR_ASSUMPTIONS, the run's own
    lines (``planar_run_assumptions``), ATMOSPHERE_ASSUMPTIONS, for a push the
    TRACK_ASSUMPTIONS and the track geometry, for a failed ignition whose coast ran
    PLANAR_FAILED_IGNITION_ASSUMPTIONS, the trace's own and the assist model's (with
    the track's actual g_eff and omega_p)."""
    lines = [*PLANAR_ASSUMPTIONS, *run_assumptions, *ATMOSPHERE_ASSUMPTIONS]
    track = setup.track
    if track is not None and trace.assist_phases():
        lines += [
            *TRACK_ASSUMPTIONS,
            f"track: straight, L = {track.length_m:.6g} m at {track.phi(0.0):.6g} rad above "
            f"horizontal, start altitude {track.start_altitude_m:.6g} m (exit at "
            f"{track.start_altitude_m + track.z(track.length_m):.6g} m)",
        ]
    if trace.failed_stage is not None and trace.t_fail_s is not None:
        lines += PLANAR_FAILED_IGNITION_ASSUMPTIONS
    return [*lines, *trace.assumptions, *setup.assist.assumptions()]


def planar_startup_items(vehicle: Vehicle, setup: PlanarSetup) -> dict[str, Any]:
    """How stage 1 starts (as the 1-D ``ignition_timing_metrics`` reports it, for the
    ignition rows of the summary): ``startup_kind_<stage>`` (step, ramp or lag; step is
    instant full thrust, a yardstick no engine achieves) and ``t_startup_s_<stage>``
    (t_ramp, tau, or 0 for a step) [s]."""
    stage0 = vehicle.stages[0]
    spec = setup.ignition[stage0.name]
    startup = stage0.startup if spec.startup is None else spec.startup
    kind = startup.effective_kind
    return {
        f"startup_kind_{stage0.name}": kind,
        f"t_startup_s_{stage0.name}": {"ramp": startup.t_ramp_s, "lag": startup.tau_s}.get(
            kind, 0.0
        ),
    }


def planar_ramp_start_items(
    trace: RunTrace, vehicle: Vehicle, setup: PlanarSetup
) -> dict[str, Any]:
    """The requested and achieved stage-1 ramp start of a recorded planar run
    (``metrics_planar.ramp_start_metrics``) with the track exit's altitude [m] and the
    push time [s] the ignition time resolved against (``push_time_estimate``), both None
    for a pad."""
    track = setup.track
    z_exit = None if track is None else track.start_altitude_m + track.z(track.length_m)
    t_push = None if track is None else setup.assist.push_time_estimate(track)
    stage0 = vehicle.stages[0]
    return ramp_start_metrics(trace, stage0.name, setup.ignition[stage0.name], z_exit, t_push)


def search_failed_result(
    run_config: RunConfig, vehicle: Vehicle, setup: PlanarSetup, record: SearchRecord
) -> Result:
    """The Result of a run whose search failed (no recorded run): status search_failed,
    empty planar time series and events, the search items (NaN figures of merit as
    None, the failure kind and message, the grid in ``search_record``), a flag naming
    the failure (with the shared-grid advice for kind edge) and the planar
    assumptions."""
    flags = [*record.flags, *_run_flags(run_config)]
    advice = (
        " (widen the shared gamma* grid for every run)" if record.failure_kind == "edge" else ""
    )
    flags.append(f"search_failed: {record.failure_kind}: {record.failure_message}{advice}")
    metrics: dict[str, Any] = {
        "assist_model": setup.assist.name,
        "liftoff_mass_kg": vehicle.liftoff_mass_kg(),
        **search_metrics(record, vehicle.payload_mass_kg),
        "trace_status": None,
        "run_checks": CHECK_NA,
        "run_checks_failed": None,
    }
    assumptions = [
        *PLANAR_ASSUMPTIONS,
        *planar_run_assumptions(run_config, vehicle, setup),
        *ATMOSPHERE_ASSUMPTIONS,
        *setup.assist.assumptions(),
    ]
    return Result(
        metrics=metrics,
        timeseries=empty_planar_timeseries(),
        loss_budget=None,
        assist_budget=None,
        assumptions=assumptions,
        phases=[],
        status="search_failed",
        flags=flags,
        events=empty_planar_events(),
        model=PLANAR_MODEL,
        search=record,
    )


GUIDANCE_FAILED_STATUS = "guidance_failed"
"""Status of a fixed-guidance run whose guidance raised a typed failure (GuidanceFailure
or PreludeFailure: no kick, no cutoff, a prelude without a flight, ...)."""


def guidance_failed_result(
    run_config: RunConfig, vehicle: Vehicle, setup: PlanarSetup, exc: Exception
) -> Result:
    """The Result of a run flown without a search whose guidance raised a typed failure
    (``search.INFEASIBLE``; a searched run turns these into penalties instead): status
    guidance_failed, empty planar time series and events, the SEARCH_METRIC_KEYS as a
    fixed-guidance run carries them (search_status FIXED_GUIDANCE_STATUS, the fixed
    gamma* [rad] and LTG pair, no figures of merit), ``guidance_failure_kind`` and
    ``guidance_failure_message``, a flag naming the failure and the planar
    assumptions."""
    search = run_config.planar.search  # type: ignore[union-attr]
    kind = str(getattr(exc, "kind", type(exc).__name__))
    message = str(getattr(exc, "message", ""))
    metrics: dict[str, Any] = {
        "assist_model": setup.assist.name,
        "liftoff_mass_kg": vehicle.liftoff_mass_kg(),
        **dict.fromkeys(SEARCH_METRIC_KEYS),
        "search_status": FIXED_GUIDANCE_STATUS,
        "figure_of_merit": NO_SEARCH,
        "gamma_star_rad": search.fixed_gamma_star_rad,
        "ltg_a": search.fixed_ltg_a,
        "ltg_b_per_s": search.fixed_ltg_b_per_s,
        "guidance_failure_kind": kind,
        "guidance_failure_message": message,
        "trace_status": None,
        "run_checks": CHECK_NA,
        "run_checks_failed": None,
    }
    flags = [*_run_flags(run_config), f"{GUIDANCE_FAILED_STATUS}: {kind}: {message}"]
    assumptions = [
        *PLANAR_ASSUMPTIONS,
        *planar_run_assumptions(run_config, vehicle, setup),
        *ATMOSPHERE_ASSUMPTIONS,
        *setup.assist.assumptions(),
    ]
    return Result(
        metrics=metrics,
        timeseries=empty_planar_timeseries(),
        loss_budget=None,
        assist_budget=None,
        assumptions=assumptions,
        phases=[],
        status="guidance_failed",
        flags=flags,
        events=empty_planar_events(),
        model=PLANAR_MODEL,
    )


def _solve_fixed_delta(
    setup: PlanarSetup, vehicle: Vehicle, end: str, gamma_star_rad: float
) -> float | None:
    """The kick angle delta [rad] that reaches the fixed gamma* at MECO (the inner solve
    at the final tolerance, dense output off); None when the prelude gives no flight or
    stage 1 does not light (``FlightStart.stage1_lights``: a stage that lights at an
    altitude does). Raises GuidanceFailure from the flight (no_ignition when a pending
    ignition's coast never reaches its altitude)."""
    b = setup.budget
    settings = replace(
        setup.settings, rtol=b.final_rtol, atol_scale=b.final_atol_scale, dense_output=False
    )
    solver = PlanarPlanner(
        vehicle,
        setup.ignition,
        setup.guidance,
        setup.env,
        end,
        settings,
        target=setup.target,
        ltg=b.ltg_for(FINAL_MODE),
    )
    start = solver.start(setup.assist, setup.track)
    if start.status != "nominal" or not start.stage1_lights:
        return None
    kick = solver.to_kick(start)
    sol = solve_delta_for_gamma(lambda d: solver.from_kick(d, kick), gamma_star_rad, b.delta)
    return sol.delta_rad


def fly_without_search(
    run_config: RunConfig, vehicle: Vehicle, setup: PlanarSetup
) -> tuple[RunTrace, dict[str, Any]]:
    """The recorded run of a planar run without a search, and its figure items: a
    failed stage-1 ignition (the search skipped: ``search_skip_reason``) flies no
    guidance; otherwise the shared fixed guidance of figure_of_merit none (fixed
    gamma*, delta solved for it at the final tolerance, the fixed LTG pair). Raises
    ValueError when stage 1 lights without fixed guidance (the config refuses that)."""
    planner = PlanarPlanner(
        vehicle,
        setup.ignition,
        setup.guidance,
        setup.env,
        run_config.end,
        setup.settings,
        target=setup.target,
        ltg=setup.budget.ltg_for(FINAL_MODE),
    )
    skip = run_config.search_skip_reason
    if setup.ignition[vehicle.stage_names[0]].fails:
        trace = planner.run(None, setup.assist, setup.track)
        status = f"{SKIPPED_STATUS_PREFIX} ({skip})"
        return trace, fixed_guidance_metrics(trace, vehicle, status)
    search = run_config.planar.search  # type: ignore[union-attr]
    gamma = search.fixed_gamma_star_rad
    if gamma is None or search.fixed_ltg_a is None or search.fixed_ltg_b_per_s is None:
        raise ValueError(
            f"run {run_config.name!r}: stage 1 lights without a search and without the "
            "shared fixed guidance (figure_of_merit none)"
        )
    ltg = (search.fixed_ltg_a, search.fixed_ltg_b_per_s)
    delta = _solve_fixed_delta(setup, vehicle, run_config.end, gamma)
    trace = planner.run(delta, setup.assist, setup.track, ltg=ltg)
    status = FIXED_GUIDANCE_STATUS if skip is None else f"{SKIPPED_STATUS_PREFIX} ({skip})"
    items = fixed_guidance_metrics(
        trace, vehicle, status, gamma_star_rad=gamma, delta_rad=delta, ltg=ltg
    )
    return trace, items


def run_planar(run_config: RunConfig, vehicle: Vehicle) -> Result:
    """Run one validated planar_2d configuration and return its Result.

    A searched figure of merit (payload, residual) runs ``search.run_search`` on the
    run's SearchContext (a fresh WarmStore: no cross-run seeding) and assembles the
    recorded run at the final payload (``simulate_planar``); a failed search gives
    ``search_failed_result``. figure_of_merit none (fixed guidance, or a search skipped
    by a failed ignition) flies ``fly_without_search``; a typed guidance failure there
    (``search.INFEASIBLE``) gives ``guidance_failed_result``. The run's assumption lines
    (``planar_run_assumptions``) and flags (``_run_flags``) are attached."""
    setup = planar_setup(run_config, vehicle)
    extra = planar_run_assumptions(run_config, vehicle, setup)
    flags = _run_flags(run_config)
    dt = run_config.integrator.sample_dt_s
    if run_config.figure_of_merit in SEARCHED_FIGURES:
        record = run_search(search_context(setup, vehicle, run_config.end))
        if record.trace is None or record.final is None:
            return search_failed_result(run_config, vehicle, setup, record)
        flown = with_payload(vehicle, record.final.at_final.payload_kg)
        items = search_metrics(record, vehicle.payload_mass_kg)
        return simulate_planar(
            record.trace,
            flown,
            setup,
            sample_dt_s=dt,
            figure_items=items,
            search=record,
            run_flags=[*record.flags, *flags],
            run_assumptions=extra,
        )
    try:
        trace, items = fly_without_search(run_config, vehicle, setup)
    except INFEASIBLE as exc:
        return guidance_failed_result(run_config, vehicle, setup, exc)
    return simulate_planar(
        trace,
        vehicle,
        setup,
        sample_dt_s=dt,
        figure_items=items,
        run_flags=flags,
        run_assumptions=extra,
    )


def rerun_planar(run_config: RunConfig, vehicle: Vehicle, nominal: Result, source: str) -> Result:
    """The Result of a planar run whose trajectory equals the nominal run's (the same
    ``compare.trajectory_key``: an energy-only ``assist.drive_efficiency`` or a
    ``vehicle.screening`` sensitivity case), without flying anything: the nominal's
    time series, events, loss budget, closure, search record and metrics, with the
    items this run's configuration changes recomputed (the track metrics, with its drive
    efficiency's electrical energy; the assumptions, with its drive and vehicle lines);
    the screening Isp enters only the comparison's yardstick. metrics gain
    ``trajectory_reused`` (True) and a flag names the source run."""
    setup = planar_setup(run_config, vehicle)
    note = f"trajectory reused from run {source} (the same trajectory-relevant configuration)"
    flags = [*nominal.flags, note]
    extra = planar_run_assumptions(run_config, vehicle, setup)
    trace = nominal.trace
    if trace is None:
        if nominal.search is not None:
            result = search_failed_result(run_config, vehicle, setup, nominal.search)
            return replace(result, flags=[*result.flags, note])
        if nominal.status != GUIDANCE_FAILED_STATUS:
            raise ValueError(f"run {source!r} has neither a trace nor a search record")
        metrics = {**nominal.metrics, "trajectory_reused": True}
        return replace(nominal, metrics=metrics, flags=flags)
    metrics = dict(nominal.metrics)
    if setup.track is not None and nominal.assist_budget is not None:
        metrics.update(
            planar_track_metrics(
                trace, setup.assist, setup.track, nominal.assist_budget, nominal.timeseries
            )
        )
    metrics["trajectory_reused"] = True
    assumptions = planar_assumption_list(trace, setup, extra)
    return replace(nominal, metrics=metrics, flags=flags, assumptions=assumptions)


def rerun_resolved(resolved: ResolvedRun, nominal: RunResult) -> RunResult:
    """``rerun_planar`` of a ResolvedRun on the trajectory of the RunResult nominal,
    wrapped with the resolved run's name and config."""
    vehicle = resolved.to_vehicle()
    result = rerun_planar(resolved.run, vehicle, nominal.result, nominal.name)
    return RunResult(resolved.name, resolved, result)


def matched_run(
    resolved: ResolvedRun, result: Result, payload_kg: float, *, neighbours: bool = False
) -> MatchedRun | None:
    """The rung-2 run of a planar run at the matched payload payload_kg [kg] (amendment
    16: executed here, handed to ``compare.compare_planar``): at its own gamma*.

    A searched run already evaluated at payload_kg (the baseline at its own P*, a
    residual search at P0) reuses its final evaluation's trace; any other searched run
    is evaluated once more in final mode (the delta and LTG pair warm-started from its
    final evaluation; the stage-2 burn on virtual propellant to the cutoff, so a variant
    above its capacity still has a cutoff state). With neighbours, a searched run is
    also evaluated the same way at gamma* -/+ h (compare.gamma_sensitivity_step_rad of
    the run's checks block)
    (``MatchedRun.neighbours``; None when either cannot fly). A run without a search
    (fixed guidance) reuses its recorded trace when it flew stage 2 at payload_kg, with
    no neighbours (its LTG pair is fixed, so a neighbour would miss the target). None
    when the run has no such trace or the evaluation cannot fly (typed guidance
    failure)."""
    vehicle = resolved.to_vehicle()
    setup = planar_setup(resolved.run, vehicle)
    env = setup.env
    record = result.search
    gamma: float | None
    near: tuple[MatchedRun, MatchedRun] | None = None
    at_payload = with_payload(vehicle, payload_kg)

    def as_matched(
        g: float, t: RunTrace, around: tuple[MatchedRun, MatchedRun] | None
    ) -> MatchedRun:
        return MatchedRun(
            name=resolved.name,
            payload_kg=payload_kg,
            gamma_star_rad=g,
            trace=t,
            vehicle=at_payload,
            omega_p_rads=env.omega_p_rads,
            r_datum_m=env.r_datum_m,
            neighbours=around,
        )

    if record is not None:
        if record.final is None or record.gamma is None:
            return None
        at = record.final.at_final
        gamma = record.gamma.gamma_star_rad
        ctx = search_context(setup, vehicle, resolved.run.end)
        seed = WarmEntry(gamma, at.payload_kg, at.delta_rad, at.ltg)

        def fly(g: float) -> RunTrace | None:
            try:
                res = ctx.evaluate(payload_kg, g, WarmStore(), FINAL_MODE, seed=seed)
            except INFEASIBLE:
                return None
            return None if res.shot is None else res.shot.prefix

        if at.payload_kg == payload_kg and at.shot is not None:
            trace = at.shot.prefix
        else:
            flown = fly(gamma)
            if flown is None:
                return None
            trace = flown
        if neighbours:
            h = gamma_sensitivity_step_rad(resolved.run.planar.checks)
            lo, hi = gamma - h, gamma + h
            t_lo, t_hi = fly(lo), fly(hi)
            if t_lo is not None and t_hi is not None:
                near = (as_matched(lo, t_lo, None), as_matched(hi, t_hi, None))
    else:
        trace = result.trace
        gamma = result.metrics.get("gamma_star_rad")
        stage2 = vehicle.stage_names[-1]
        if trace is None or gamma is None or vehicle.payload_mass_kg != payload_kg:
            return None
        if stage2 not in trace.burnouts:
            return None
    return as_matched(float(gamma), trace, near)


# ------------------------------------------------------------ offload (SP1 step 7)

OFFLOAD_ASSUMPTIONS: tuple[str, ...] = (
    "offload: the propellant removed from a full load leaves the tanks partly filled; "
    "every dry mass (tank structure included), engine, the payload, the fairing and the "
    "aerodynamics are unchanged and each stage keeps its mixture ratio; no ullage, "
    "centre-of-gravity or tank-mass effect is modelled",
)
"""The assumptions every offloaded run carries (a case's recorded run, a fixed case's
run, a paired pad, a pad control's recorded run; docs/physics.md, "Assumptions"). A
structural case's recorded run carries OFFLOAD_STRUCTURE_ASSUMPTIONS in its place."""

OFFLOAD_STRUCTURE_ASSUMPTIONS: tuple[str, ...] = (
    "offload: the propellant removed from a full load leaves the tanks partly filled; "
    "every dry mass is unchanged except for the modelled structural increment of the push "
    "load (the structure line), and the engine, the payload, the fairing and the "
    "aerodynamics are unchanged and each stage keeps its mixture ratio; no ullage, "
    "centre-of-gravity or tank-mass effect is modelled",
)
"""OFFLOAD_ASSUMPTIONS for a structural case's recorded run (SP7 step S3), whose dry
masses do carry the modelled increment: the sentence "every dry mass ... unchanged" would
contradict the structure line one line below it, so the run carries this variant instead
(``results_io._offload_assumptions``; S3a words the caveats)."""


def offload_penalty_assumption(added_t: float) -> str:
    """The assumption line of a run with an assumed stage-1 dry-mass penalty of added_t
    [t] (an offload case's ``stage1_dry_mass_added_t``)."""
    return (
        f"offload: stage-1 dry mass +{added_t:g} t is an assumed structural penalty (a "
        "parametric row), not a structure sized for the push load"
    )


def with_assumptions(rr: RunResult, lines: Sequence[str]) -> RunResult:
    """rr with the assumption lines appended (each once, the order kept)."""
    extra = [line for line in lines if line not in rr.result.assumptions]
    if not extra:
        return rr
    result = replace(rr.result, assumptions=[*rr.result.assumptions, *extra])
    return replace(rr, result=result)


def without_assumptions(rr: RunResult, lines: Sequence[str]) -> RunResult:
    """rr with the given assumption lines removed (the others keep their order); rr
    itself when none of them is present."""
    kept = [line for line in rr.result.assumptions if line not in lines]
    if len(kept) == len(rr.result.assumptions):
        return rr
    return replace(rr, result=replace(rr.result, assumptions=kept))


def offload_problem_factory(resolved: ResolvedRun) -> ProblemFactory:
    """The planar problem factory of a resolved run (``offload.planar_problem_factory``
    of its SearchContext, built as ``run_planar`` builds it: ``planar_setup`` and
    ``search_context``), for an offload solve on that run's vehicle."""
    vehicle = resolved.to_vehicle()
    setup = planar_setup(resolved.run, vehicle)
    return planar_problem_factory(search_context(setup, vehicle, resolved.run.end))


def solve_resolved_offload(
    resolved: ResolvedRun,
    mode: OffloadMode,
    reference_payload_kg: float,
    *,
    transform: VehicleTransform | None = None,
) -> OffloadResult:
    """``offload.solve_offload`` on a resolved run's vehicle along mode at the reference
    payload P_ref [kg], without its built-in verification (the pipeline verifies with
    ``run_resolved`` of the offloaded run, ``offload.with_verification``); a structural
    case passes its ``StructureTransform`` (SP7 step S3; None: SP1's solve). Looked up on
    this module at call time by ``results_io``."""
    factory = offload_problem_factory(resolved)
    vehicle = resolved.to_vehicle()
    if transform is None:
        return solve_offload(factory, vehicle, mode, reference_payload_kg, verify=False)
    return solve_offload(
        factory, vehicle, mode, reference_payload_kg, verify=False, transform=transform
    )


def offload_run_result(resolved: ResolvedRun, offload: OffloadResult) -> RunResult:
    """The recorded run of an offload solve as a RunResult, flying nothing (pure): the
    solve's recorded trace (the vehicle offloaded by x* flying P_ref, final tolerance,
    dense output, the real depletion event) assembled by ``simulate_planar`` on that
    vehicle at P_ref with resolved's run config (its assist, ignition and integrator
    sample interval; resolved's vehicle dict is the offloaded vehicle's, for the record),
    the figure items ``metrics_planar.offload_metrics``, the solve's flags and the
    planar run assumptions plus OFFLOAD_ASSUMPTIONS. ValueError for a solve without a
    recorded run (search_failed)."""
    vehicle = offload.offloaded_vehicle
    if offload.recorded is None or vehicle is None:
        raise ValueError(f"offload solve of {resolved.name!r} has no recorded run")
    run_config = resolved.run
    setup = planar_setup(run_config, vehicle)
    flown = with_payload(vehicle, offload.reference_payload_kg)
    result = simulate_planar(
        offload.recorded.trace,
        flown,
        setup,
        sample_dt_s=run_config.integrator.sample_dt_s,
        figure_items=offload_metrics(offload, vehicle.payload_mass_kg),
        run_flags=[*offload.flags, *_run_flags(run_config)],
        run_assumptions=planar_run_assumptions(run_config, vehicle, setup),
    )
    return with_assumptions(RunResult(resolved.name, resolved, result), OFFLOAD_ASSUMPTIONS)


# ------------------------------------------------------------------------ structure (SP7 S2)

STRUCTURE_MASS_TOL_KG = 1.0e-3
"""Tolerance [kg] of the adapter's mass checks between a Result and the Vehicle it is said
to have flown (survey 05 found the events' bookkeeping exact to 1e-6 kg)."""


def stack_masses(vehicle: Vehicle) -> StackMasses:
    """The masses and thrusts ``structure.build_geometry`` builds the stations from: each
    stage's name, dry mass, propellant load and total vacuum thrust [kg, kg, N] of a
    two-stage launchsim Vehicle (pass the full-load vehicle: the geometry is built once
    from it and closed over, design 4.2)."""
    if vehicle.n_stages != 2:
        raise ValueError(
            f"the structural model sizes two stages, the vehicle has {vehicle.n_stages}"
        )
    s1, s2 = vehicle.stages
    return StackMasses(
        stage1=StageMasses(s1.name, s1.dry_mass_kg, s1.propellant_mass_kg, s1.thrust_vac_total_N),
        stage2=StageMasses(s2.name, s2.dry_mass_kg, s2.propellant_mass_kg, s2.thrust_vac_total_N),
    )


def _fairing_drop(events: pd.DataFrame) -> tuple[float, float] | None:
    """(time [s], mass at the event [kg]) of the fairing jettison event, or None."""
    rows = events[events["event"] == FAIRING_EVENT]
    if rows.empty:
        return None
    first = rows.iloc[0]
    return float(first["t_s"]), float(first["m_kg"])


def _non_negative_mass(value_kg: float, load_kg: float) -> float:
    """A propellant mass recovered from the bookkeeping [kg], clamped to [0, load] within
    STRUCTURE_MASS_TOL_KG (rounding at depletion); ValueError outside that."""
    if value_kg < -STRUCTURE_MASS_TOL_KG or value_kg > load_kg + STRUCTURE_MASS_TOL_KG:
        raise ValueError(
            f"a recovered propellant mass {value_kg!r} kg is outside [0, {load_kg!r}] kg: the "
            "vehicle is not the one the Result flew"
        )
    return min(max(value_kg, 0.0), load_kg)


def structure_pad_cases(
    result: Result, vehicle: Vehicle, layout: StackLayout, *, label: str = "pad"
) -> tuple[LoadCase, ...]:
    """The pad baseline's load cases for the structural envelope (pure; design 4.2,
    D-SP7-15; survey 05 sections 1-3).

    Inputs: result, the pad baseline's planar Result (its time series and events; no
    ASSIST rows); vehicle, the Vehicle it flew (the flown payload: a searched pad's
    P_final); layout, the structure file's StackLayout (stage names and each stage's LOX
    mass fraction); label, the cases' label prefix.
    Output: one LoadCase per HOLD row (kind hold; n = felt_axial_g, which is g_eff/g0 on a
    clamped row; the support m n g0 - T), per stage-1 flight row (an engine lit: phase in
    LIT_KINDS) and per stage-2 burn row (stage 1 gone), in time-series order. Masses as
    survey 05 recovers them: U = stage 2 wet + the fairing while attached + the payload,
    the stage-1 propellant m - dry1 - U, the stage-2 propellant on its burn m - dry2 -
    payload - the fairing while attached (attached before the fairing event; on a row at
    the event's time, by its mass), split by each stage's LOX mass fraction. Checked
    against the vehicle: the first row is the full stack and the stage-1 propellant is 0
    at its depletion event, within STRUCTURE_MASS_TOL_KG. Coasts are left out (n near 0:
    never governing).
    Frame: the stack axis.
    """
    if result.model != PLANAR_MODEL:
        raise ValueError(f"the structural envelope reads a planar Result, got {result.model!r}")
    masses = stack_masses(vehicle)
    stage1, stage2 = masses.stage1.name, masses.stage2.name
    if (layout.stage1.name, layout.stage2.name) != (stage1, stage2):
        raise ValueError("the structure layout's stage names differ from the vehicle's")
    ts, events = result.timeseries, result.events
    if (ts["phase"] == ASSIST_KIND).any():
        raise ValueError("the envelope is the pad baseline's flight: this Result has a push")
    s1, s2 = vehicle.stages
    fairing, payload = vehicle.fairing_mass_kg, vehicle.payload_mass_kg
    drop = _fairing_drop(events)
    m = ts["m_kg"].to_numpy(dtype=float)
    t = ts["t_s"].to_numpy(dtype=float)

    def attached(i: int) -> bool:
        if drop is None or t[i] < drop[0]:
            return True
        if t[i] > drop[0]:
            return False
        return abs(m[i] - drop[1]) <= 0.5 * fairing

    full = s1.wet_mass_kg + s2.wet_mass_kg + fairing + payload
    if abs(m[0] - full) > STRUCTURE_MASS_TOL_KG:
        raise ValueError(f"the Result's first mass {m[0]!r} kg is not the vehicle's {full!r} kg")
    f1, f2 = layout.stage1.lox_mass_fraction, layout.stage2.lox_mass_fraction
    lox2_full = f2 * s2.propellant_mass_kg
    rp12_full = s2.propellant_mass_kg - lox2_full
    cases: list[LoadCase] = []
    phases = ts["phase"].astype(str).to_numpy()
    stages = ts["stage"].astype(str).to_numpy()
    felt = ts["felt_axial_g"].to_numpy(dtype=float)
    thrust = ts["thrust_N"].to_numpy(dtype=float)
    for i in range(len(ts)):
        phase, stage = phases[i], stages[i]
        upper2 = payload + (fairing if attached(i) else 0.0)
        tag = f"{label} {phase} t={t[i]:.4f} s"
        if stage == stage1 and (phase == HOLD_KIND or phase in LIT_KINDS):
            upper = s2.wet_mass_kg + upper2
            prop1 = _non_negative_mass(m[i] - s1.dry_mass_kg - upper, s1.propellant_mass_kg)
            lox1 = f1 * prop1
            hold = phase == HOLD_KIND
            support = float(m[i]) * float(from_g(felt[i])) - float(thrust[i]) if hold else None
            cases.append(
                LoadCase(
                    label=tag,
                    kind=HOLD if hold else FLIGHT,
                    t_s=float(t[i]),
                    n_g=float(felt[i]),
                    stage1_attached=True,
                    lox_stage1_kg=lox1,
                    rp1_stage1_kg=prop1 - lox1,
                    lox_stage2_kg=lox2_full,
                    rp1_stage2_kg=rp12_full,
                    upper_mass_stage1_kg=upper,
                    upper_mass_stage2_kg=upper2,
                    vehicle_mass_kg=float(m[i]),
                    thrust_N=float(thrust[i]),
                    hold_down_support_N=support,
                )
            )
        elif stage == stage2 and phase in LIT_KINDS:
            prop2 = _non_negative_mass(m[i] - s2.dry_mass_kg - upper2, s2.propellant_mass_kg)
            lox2 = f2 * prop2
            cases.append(
                LoadCase(
                    label=tag,
                    kind=FLIGHT,
                    t_s=float(t[i]),
                    n_g=float(felt[i]),
                    stage1_attached=False,
                    lox_stage1_kg=0.0,
                    rp1_stage1_kg=0.0,
                    lox_stage2_kg=lox2,
                    rp1_stage2_kg=prop2 - lox2,
                    upper_mass_stage1_kg=0.0,
                    upper_mass_stage2_kg=upper2,
                    vehicle_mass_kg=float(m[i]),
                    thrust_N=float(thrust[i]),
                )
            )
    depletion = events[(events["event"] == "propellant") & (events["stage"] == stage1)]
    if not depletion.empty:
        m_dep = float(depletion.iloc[0]["m_kg"])
        on = drop is None or float(depletion.iloc[0]["t_s"]) < drop[0]
        left = m_dep - s1.dry_mass_kg - s2.wet_mass_kg - payload - (fairing if on else 0.0)
        if abs(left) > STRUCTURE_MASS_TOL_KG:
            raise ValueError(
                f"stage 1's propellant at its depletion event is {left!r} kg, not 0: the "
                "vehicle is not the one the Result flew"
            )
    return tuple(cases)


def constant_accel_push_load(
    vehicle: Vehicle,
    assist: ConstantAccelAssist,
    track: TrackGeometry,
    layout: StackLayout,
    *,
    g_eff_mps2: float,
    stage1_ignition_s: float | None = None,
    p_amb_pa: float = P_SEA_LEVEL_PA,
    label: str = "push",
) -> PushLoad:
    """The analytic load case of a constant_accel push (pure; design 4.4: no trajectory is
    flown; survey 05 section 6 found the recorded rows equal to it to 5e-12).

    Inputs: vehicle, the Vehicle at the offload x and payload P being sized (its masses
    are the push's); assist and track, the push (a straight track, phi read at s = 0);
    layout, the structure file's StackLayout (each stage's LOX mass fraction); g_eff_mps2,
    the track's effective gravity [m/s^2]; stage1_ignition_s, stage 1's ignition time from
    the push start [s] (None: a cold push, no thrust on the track); p_amb_pa, the ambient
    pressure of the delivered thrust on the track [Pa] (sea level by default); label.
    Output: a PushLoad with one case: n = (a + g_eff sin phi)/g0, constant; the tank
    contents at push start; F_int = the largest over the push of m_v(t) (a + g_eff
    sin phi) - T(t) (at the start, the thrust schedule's kinks and the release; m_v (a +
    g_eff sin phi) cold) with the thrust at that instant; n_rest = g_eff sin phi/g0 and
    F_rest = m_v(0) g_eff sin phi - T(0) (a hold's for a lit start); the RampedPlateau
    (L, v_e, a) for the ``rise_time`` mode; the release at the end of the stroke with the
    contents then, n before the drop the plateau and after it T/(m_v g0) (drag neglected).
    Frame: the track's axis (the stack axis on the vertical track).
    """
    if vehicle.n_stages != 2:
        raise ValueError("the structural model sizes two stages")
    s1, s2 = vehicle.stages
    length = track.length_m
    sin_phi = math.sin(track.phi(0.0))
    accel = assist.net_accel_mps2
    a_up = accel + g_eff_mps2 * sin_phi
    t_push = assist.push_time_s(length)
    schedule = None if stage1_ignition_s is None else s1.schedule(stage1_ignition_s)
    m0 = vehicle.stack_mass_kg(0)

    def burned(t: float) -> float:
        return 0.0 if schedule is None else propellant_burned_kg(schedule, t)

    def thrust(t: float) -> float:
        return 0.0 if schedule is None else schedule.thrust_N(t, p_amb_pa)

    samples = [0.0, t_push]
    if schedule is not None:
        samples += [k for k in schedule.kink_times() if 0.0 < k < t_push]
    forces = [((m0 - burned(t)) * a_up - thrust(t), thrust(t)) for t in sorted(samples)]
    f_int, t_at = max(forces, key=lambda pair: pair[0])
    f1, f2 = layout.stage1.lox_mass_fraction, layout.stage2.lox_mass_fraction
    upper2 = vehicle.payload_mass_kg + vehicle.fairing_mass_kg
    upper = s2.wet_mass_kg + upper2
    lox2 = f2 * s2.propellant_mass_kg

    def case_at(t: float, interface: float, thrust_N: float, tag: str) -> LoadCase:
        prop1 = s1.propellant_mass_kg - burned(t)
        lox1 = f1 * prop1
        return LoadCase(
            label=f"{label} {tag}",
            kind=PUSH,
            t_s=t,
            n_g=float(to_g(a_up)),
            stage1_attached=True,
            lox_stage1_kg=lox1,
            rp1_stage1_kg=prop1 - lox1,
            lox_stage2_kg=lox2,
            rp1_stage2_kg=s2.propellant_mass_kg - lox2,
            upper_mass_stage1_kg=upper,
            upper_mass_stage2_kg=upper2,
            vehicle_mass_kg=m0 - burned(t),
            thrust_N=thrust_N,
            interface_force_N=interface,
        )

    start = case_at(0.0, f_int, t_at, "push start")
    m_rel = m0 - burned(t_push)
    t_rel = thrust(t_push)
    release = case_at(t_push, m_rel * a_up - t_rel, t_rel, "release")
    return PushLoad(
        cases=(start,),
        n_rest_g=float(to_g(g_eff_mps2 * sin_phi)),
        f_rest_N=(m0 - burned(0.0)) * g_eff_mps2 * sin_phi - thrust(0.0),
        ramp=RampedPlateau(
            stroke_m=length,
            exit_speed_mps=assist.exit_speed_mps(length),
            accel_net_mps2=accel,
        ),
        rise_time_s=None,
        release=ReleaseState(
            n_before_g=float(to_g(a_up)),
            n_after_g=float(to_g(t_rel / m_rel)),
            case=release,
        ),
    )


# ----------------------------------------------------------- structure coupling (SP7 S3)

STRUCTURE_FIXED_POINT_TOL_KG = 1.0e-6
"""The inner iteration's tolerance [kg] (design 4.4): a transform call stops when the
larger of the two stages' |dm_k+1 - dm_k| falls below it (the push's interface force
depends on the vehicle mass, dm included)."""
STRUCTURE_FIXED_POINT_MAX_ITERATIONS = 25
"""The inner iteration's cap (sizings per transform call): reaching it before the
tolerance raises ``structure.FLAG_FIXED_POINT_CAP``. Design 4.4 wrote 10; D-SP7-44 raised
it to 25 after the gate file's outer_high_mass set was measured to need exactly 10 (its
contraction 0.050 against the gate file's central 0.0057), leaving the flag no margin; the loop
breaks on convergence, so the raise costs a converging call nothing."""


def charge_structure(vehicle: Vehicle, dm_stage1_kg: float, dm_stage2_kg: float) -> Vehicle:
    """vehicle with a modelled structural increment added to its first two stages' dry
    masses [kg] (``vehicle.with_stage_dry_mass``; design 4.4: dm1 on stage 1, the
    interstage included (D-SP7-36), dm2 on stage 2); a zero increment leaves its stage
    alone, so dm = 0 returns the vehicle itself. Pure."""
    out = vehicle
    for i, dm in enumerate((dm_stage1_kg, dm_stage2_kg)):
        if dm != 0.0:
            out = with_stage_dry_mass(out, i, out.stages[i].dry_mass_kg + dm)
    return out


@dataclass(frozen=True, eq=False)
class StructureSizing:
    """One sizing of a structural transform for one vehicle (``StructureTransform.sizing``;
    design 4.4).

    dm_stage1_kg (the stage-1 elements and the interstage, D-SP7-36) and dm_stage2_kg
    [kg]: the last iterate, the increment the transform adds; increment: the Increment
    that gave it (sized on the vehicle carrying the iterate before; its element masses
    are unscaled, the iterate is ``factor`` times them); iterations: the sizings made
    (each call starts from dm = 0, so the first sizes the uncharged vehicle); capped:
    True when STRUCTURE_FIXED_POINT_MAX_ITERATIONS was reached before the tolerance;
    steps: each iteration's larger |dm_k+1 - dm_k| of the two stages [kg] (the first is
    |dm_1 - 0|); factor: the plausibility rule's factor the iterate carries (SP7 step
    S3b; 1.0 for a case that is not plausibility-scaled).
    """

    dm_stage1_kg: float
    dm_stage2_kg: float
    increment: Increment
    iterations: int
    capped: bool
    steps: tuple[float, ...]
    factor: float = 1.0

    @property
    def total_kg(self) -> float:
        """dm_stage1_kg + dm_stage2_kg [kg]."""
        return self.dm_stage1_kg + self.dm_stage2_kg

    @property
    def contraction(self) -> float | None:
        """The measured contraction of the iteration [-]: the largest ratio of consecutive
        nonzero steps after the first (step k+1 over step k, k >= 2); None with fewer than
        three steps or no nonzero pair (a constant dm converges in two)."""
        ratios = [b / a for a, b in itertools.pairwise(self.steps[1:]) if a > 0.0]
        return max(ratios) if ratios else None


@dataclass(frozen=True, eq=False)
class StructureTransform:
    """The structural transform of one structural offload case (SP7 step S3; design 4.4,
    D-SP7-20; an ``offload.VehicleTransform``): the vehicle offloaded by x at its own
    payload P0 and P_ref [kg] to the same vehicle with the modelled dm added to its dry
    masses.

    settings: the case's ResolvedStructureCase; geometry: built once from the full-load
    vehicle (D-SP7-13) and closed over; envelope: built once from the pad's own flight
    (both stages, at the case's margin and cap); layout; assist, track and g_eff_mps2
    [m/s^2]: the case's push (constant_accel); stage1_ignition_s [s]: stage 1's ignition
    from the push start when it lights on the track (None: cold); start_vehicle: the
    solve's full-load vehicle (x = 0, payload P0); mode: the solve's offload mode;
    reference_payload_kg: P_ref [kg]; envelope_pad: the name of the run whose flight is
    the envelope; envelope_pad_key: its ``compare.trajectory_key``; plausibility (SP7
    step S3b): the plausibility rule's check at the central coefficients on this pad's
    envelope (margin 0, no cap: the rule's basis, D-SP7-33); plausibility_factor: the
    factor every sizing's dm is multiplied by (the rule's factor for the case's physics
    band end when ``settings.plausibility_scaled``, else 1.0).

    Pure and deterministic: a call depends on its arguments and these fields only and
    starts from dm = 0, so ``OffloadProblem.vehicle_at(x)`` gives the same bits in any
    call order. Frame: the stack axis.
    """

    settings: ResolvedStructureCase
    geometry: StackGeometry
    envelope: Envelope
    layout: StackLayout
    assist: ConstantAccelAssist
    track: TrackGeometry
    g_eff_mps2: float
    stage1_ignition_s: float | None
    start_vehicle: Vehicle
    mode: OffloadMode
    reference_payload_kg: float
    envelope_pad: str
    envelope_pad_key: str
    plausibility: Plausibility
    plausibility_factor: float

    @property
    def plausibility_ratio(self) -> float:
        """M_model / R [-]: the model's envelope tank mass over Heineman's relation at the
        central coefficients (``structure.plausibility``)."""
        return self.plausibility.m_model_kg / self.plausibility.relation_kg

    @property
    def memo_key(self) -> tuple[str, str]:
        """What the offload pass's solve and run memos add for this transform (design 4.4,
        "Memo"): the structure key (settings, file and its sha256) and the envelope pad's
        trajectory key."""
        return (self.settings.key, self.envelope_pad_key)

    def push(self, vehicle: Vehicle) -> PushLoad:
        """The analytic constant_accel push of vehicle (its masses as flown, dm included)
        (``constant_accel_push_load``)."""
        return constant_accel_push_load(
            vehicle,
            self.assist,
            self.track,
            self.layout,
            g_eff_mps2=self.g_eff_mps2,
            stage1_ignition_s=self.stage1_ignition_s,
        )

    def iterate(self, flown: Vehicle) -> StructureSizing:
        """The fixed point dm = f S(push(flown + dm)) from dm = 0 (design 4.4): sized with
        ``structure.size_increment`` on the closed-over geometry and envelope until the
        larger stage step is below STRUCTURE_FIXED_POINT_TOL_KG, at most
        STRUCTURE_FIXED_POINT_MAX_ITERATIONS sizings; f the ``plausibility_factor`` (1.0
        unless the case is plausibility-scaled, SP7 step S3b: then the scaled dm is the
        mass flown, so the fixed point is taken on it). flown: the vehicle at the payload
        it flies [kg]."""
        st = self.settings
        f = self.plausibility_factor
        dm1 = dm2 = 0.0
        steps: list[float] = []
        increment: Increment | None = None
        for _ in range(STRUCTURE_FIXED_POINT_MAX_ITERATIONS):
            increment = structure.size_increment(
                self.geometry,
                st.coefficients,
                self.envelope,
                self.push(charge_structure(flown, dm1, dm2)),
                dynamic=st.dynamic,  # type: ignore[arg-type]
                entry=st.entry,  # type: ignore[arg-type]
            )
            n1, n2 = f * increment.dm_stage1_kg, f * increment.dm_stage2_kg
            steps.append(max(abs(n1 - dm1), abs(n2 - dm2)))
            dm1, dm2 = n1, n2
            if steps[-1] < STRUCTURE_FIXED_POINT_TOL_KG:
                break
        assert increment is not None
        capped = steps[-1] >= STRUCTURE_FIXED_POINT_TOL_KG
        return StructureSizing(dm1, dm2, increment, len(steps), capped, tuple(steps), f)

    def sizing(self, vehicle: Vehicle, payload_kg: float) -> StructureSizing:
        """The sizing a call with vehicle (offloaded, at its own payload) and payload_kg
        [kg] charges: ``flown`` sizes vehicle flying payload_kg; ``full_load`` sizes the
        full-load start vehicle flying payload_kg (x = 0), whatever vehicle is given."""
        base = self.start_vehicle if self.settings.sizing == STRUCTURE_SIZING_FULL_LOAD else vehicle
        return self.iterate(with_payload(base, payload_kg))

    def __call__(self, vehicle: Vehicle, payload_kg: float) -> Vehicle:
        """vehicle with the sizing's dm added to its dry masses (``charge_structure``); its
        payload is kept (the solve flies P_ref on it)."""
        s = self.sizing(vehicle, payload_kg)
        return charge_structure(vehicle, s.dm_stage1_kg, s.dm_stage2_kg)

    def sizing_at(self, offload_kg: float) -> StructureSizing:
        """The sizing the solve charges at offload x = offload_kg [kg] along the mode at
        P_ref (what ``OffloadProblem.vehicle_at(x)`` added)."""
        offloaded = with_offload(self.start_vehicle, self.mode, offload_kg)
        return self.sizing(offloaded, self.reference_payload_kg)


def build_structure_transform(
    settings: ResolvedStructureCase,
    full_load_vehicle: Vehicle,
    start: ResolvedRun,
    mode: OffloadMode,
    pad_cases: PadLoadSet,
    reference_payload_kg: float,
    *,
    envelope_pad: str,
    envelope_pad_key: str,
) -> StructureTransform:
    """The StructureTransform of a structural case (design 4.4), built once.

    Inputs: settings, the case's resolved structure; full_load_vehicle, the variant's
    vehicle at its full loads (the geometry's masses, D-SP7-13); start, the solve's start
    run (its push: assist, track, the site's g_eff, stage 1's ignition; its vehicle is the
    solve's x = 0); mode, the offload mode; pad_cases, the pad's PadLoadSet (the envelope);
    reference_payload_kg, P_ref [kg]; envelope_pad and envelope_pad_key, the pad run's
    name and trajectory key (the records and the memo key).
    Output: the transform. Raises ValueError for a start with no push and
    NotImplementedError for a drive other than constant_accel (a flown push inside the
    transform is step S4b's). The plausibility rule's check (``central_plausibility``) is
    taken on this pad at the central coefficients, and its factor for the case's physics
    band end is applied to every sizing when ``settings.plausibility_scaled`` (SP7 step
    S3b; ``plausibility_factor_for``). Frame: the stack axis.
    """
    config = settings.file.config
    layout = config.stack_layout()
    coeffs = settings.coefficients
    start_vehicle = start.to_vehicle()
    setup = planar_setup(start.run, start_vehicle)
    assist = setup.assist
    if setup.track is None or isinstance(assist, NoAssist):
        raise ValueError(f"run {start.name!r}: structure sizes the push load, but it has no push")
    if not isinstance(assist, ConstantAccelAssist):
        raise NotImplementedError(
            f"run {start.name!r}: the structural transform sizes a constant_accel push "
            f"analytically; a {type(assist).__name__} push is flown inside the transform "
            "in SP7 step S4b, not built yet"
        )
    masses = stack_masses(full_load_vehicle)
    geometry = build_geometry(masses, layout, coeffs)
    envelope = structure.build_envelope(
        geometry,
        coeffs,
        pad_cases,
        margin=settings.margin,
        envelope_cap_g=settings.envelope_cap_g,
    )
    check = central_plausibility(config, masses, pad_cases)
    t_push = assist.push_time_s(setup.track.length_m)
    return StructureTransform(
        settings=settings,
        geometry=geometry,
        envelope=envelope,
        layout=layout,
        assist=assist,
        track=setup.track,
        g_eff_mps2=setup.env.g_ref_mps2,
        stage1_ignition_s=_push_stage1_ignition_s(setup, start_vehicle, t_push),
        start_vehicle=start_vehicle,
        mode=mode,
        reference_payload_kg=reference_payload_kg,
        envelope_pad=envelope_pad,
        envelope_pad_key=envelope_pad_key,
        plausibility=check,
        plausibility_factor=plausibility_factor_for(settings, check),
    )


def central_plausibility(
    config: StructureConfig, masses: StackMasses, pad_cases: PadLoadSet
) -> Plausibility:
    """The plausibility rule's check (design 4.2.5, D-SP7-33; ``structure.plausibility``)
    at the rule's basis: the structure file's central coefficients, the geometry of the
    full-load masses and the pad's envelope at margin 0 with no cap (stage 1 only: the
    rule reads the stage-1 tank elements). Computed from the envelope, never typed in
    (SP7 step S3b). Frame: the stack axis."""
    coeffs = config.coefficients()
    geometry = build_geometry(masses, config.stack_layout(), coeffs)
    envelope = structure.build_envelope(geometry, coeffs, pad_cases, stages=(STAGE1,))
    return plausibility(geometry, coeffs, envelope)


def plausibility_factor_for(settings: ResolvedStructureCase, check: Plausibility) -> float:
    """The factor a plausibility-scaled case multiplies its sized dm by (D-SP7-33, applied
    as approved, D-SP7-41): on set physics_low_mass the rule's favourable-end factor
    ((1 + band) R / M when the model's tank mass M lies above (1 + band) R, else 1.0), on
    physics_high_mass its adverse-end factor ((1 - band) R / M below (1 - band) R, else
    1.0), with band the structure file's ``heineman_band_fraction`` (0.30 in the shipped
    files; ``Plausibility.band_fraction``); 1.0 for a case that is not
    plausibility-scaled. ``plausibility_end_factor`` gives the end's factor whether or not
    the case applies it (the record prints it on every run)."""
    if not settings.plausibility_scaled:
        return 1.0
    return plausibility_end_factor(settings.set_name, check)


def plausibility_end_factor(set_name: str, check: Plausibility) -> float:
    """The plausibility rule's factor for a coefficient set's band end: physics_low_mass
    the favourable-end factor, physics_high_mass the adverse-end factor, any other set
    1.0 (the rule scales the two physics band ends and nothing else, D-SP7-33)."""
    if set_name == SET_PHYSICS_LOW:
        return check.favourable_end_factor
    if set_name == SET_PHYSICS_HIGH:
        return check.adverse_end_factor
    return 1.0


def offload_pad_load_set(
    pad: RunResult, reference_payload_kg: float, layout: StackLayout
) -> PadLoadSet:
    """The envelope's load cases of a reference pad (``structure_pad_cases`` of its Result
    on its vehicle at the payload it flew, P_ref [kg], prepared by ``pad_load_set``). The
    one seam every structural builder of the offload pass reads the pad through
    (``offload_structure_transform``, ``payload_structure_transform``,
    ``offload_structure_inputs``), looked up on this module at call time by ``results_io``
    (and replaced by a synthetic pad in the tests)."""
    pad_vehicle = with_payload(pad.resolved.to_vehicle(), reference_payload_kg)
    return pad_load_set(structure_pad_cases(pad.result, pad_vehicle, layout, label=pad.name))


def offload_structure_transform(
    case: ResolvedOffloadCase, pad: RunResult, reference_payload_kg: float
) -> StructureTransform:
    """The StructureTransform of a resolved structural offload case against its pad
    (``results_io`` looks it up here at call time): the envelope from the pad's own flight
    (``offload_pad_load_set``: ``structure_pad_cases`` of its Result on its vehicle at the
    payload it flew, P_ref; for a sensitivity arm, the pad flown under the same
    perturbation), the geometry from the case's variant at its full loads, the push of
    the case's start. ValueError for a case without structure."""
    settings = case.structure
    if settings is None:
        raise ValueError(f"offload case {case.name!r} has no structure")
    layout = settings.file.config.stack_layout()
    cases = offload_pad_load_set(pad, reference_payload_kg, layout)
    return build_structure_transform(
        settings,
        case.variant.to_vehicle(),
        case.start,
        case.config.mode,
        cases,
        reference_payload_kg,
        envelope_pad=pad.name,
        envelope_pad_key=trajectory_key(pad.resolved),
    )


def payload_structure_transform(
    case: ResolvedStructurePayloadCase, pad: RunResult, reference_payload_kg: float
) -> StructureTransform:
    """The StructureTransform of a structure payload case (design 4.4, "Payload form";
    SP7 step S3b; ``results_io`` looks it up here at call time): the envelope from the
    reference pad's own flight (``offload_pad_load_set``), the geometry from the case's
    variant at its full loads, the push of that variant (its start: the payload form flies
    the variant itself, offloaded by nothing), the sizing basis full_load (the settings
    were resolved so), the mode STRUCTURE_OFFLOAD_MODE (unused by a full-load sizing: the
    transform never offloads, ``StructureTransform.sizing`` sizes the start vehicle at the
    payload it is given)."""
    settings = case.structure
    layout = settings.file.config.stack_layout()
    cases = offload_pad_load_set(pad, reference_payload_kg, layout)
    return build_structure_transform(
        settings,
        case.variant.to_vehicle(),
        case.variant,
        STRUCTURE_OFFLOAD_MODE,
        cases,
        reference_payload_kg,
        envelope_pad=pad.name,
        envelope_pad_key=trajectory_key(pad.resolved),
    )


def _flag_record(flag: StructureFlag) -> dict[str, Any]:
    """A structure flag as plain data: name, fired and its numbers by key."""
    return {"name": flag.name, "fired": flag.fired, "values": dict(flag.values)}


def structure_record(
    transform: StructureTransform, at_x: StructureSizing | None, at_zero: StructureSizing
) -> dict[str, Any]:
    """The run-level record keys of a structural run (design 4.4, "Records"; SP7 step S3),
    in this order, for the case record and the recorded run's metrics: structure_charged
    (True); structure_dm_kg, dm1 + dm2 at x* [kg], and structure_dm_stage2_kg, dm2 [kg]
    (dm1 the difference); structure_dm_x0_kg, dm1 + dm2 at x = 0 [kg] (the full-load
    sizing at P_ref: on a structure payload case's record dm_0, its first pass's sizing,
    the same quantity, while its structure_dm_kg is dm_1, the mass its run carries);
    structure_flight_exceedance_kg (SP7 step S3b: the post-hoc flight check's exceedance
    mass [kg], unscaled, None until ``with_flight_check`` fills it on a recorded run that
    has a time series); structure_set, structure_sizing, structure_dynamic, structure_entry,
    structure_margin [-], structure_envelope_cap_g [g0 or None], structure_overrides (the
    case's design-axis coefficients by path, file units; {} when none; D-SP7-43: the
    coefficients that sized dm are on disk, not only in the memo key);
    structure_plausibility_ratio (M_model / R at the central coefficients on this
    envelope, S3b), structure_plausibility_factor (the rule's factor for the case's band
    end: physics_low_mass (1 + band) R / M above (1 + band) R, physics_high_mass (1 -
    band) R / M below (1 - band) R, band the file's ``heineman_band_fraction``; 1.0 when
    the rule does not fire on that end or the set is not a physics end) and
    structure_plausibility_scaled (whether dm carries that factor); at x*: structure_dlf
    [-], structure_t_r_s and structure_f_Hz (the rise time [s] and axial frequency [Hz]
    behind it), structure_n_q_g and structure_n_peak_g [g0], structure_F_peak_N [N],
    structure_ramp_cost_rel (the constant_accel plateau's raise (a' - a)/a [-]),
    structure_elements (kg per ``<stage>.<element>``; a scaled case's times its factor,
    so they sum to dm), structure_closed_form_kg and structure_ring_kg [kg] (likewise),
    structure_governing (the element with the largest increment: stage, element, push
    and envelope modes, station index, height z [m], the envelope case's index and
    label; None when dm is 0), structure_flags (each of structure.size_increment's flags
    and FLAG_FIXED_POINT_CAP, fired or not, with their numbers; the cap flag's:
    iterations, last_step_kg, tolerance_kg, max_iterations and contraction, the measured
    step ratio, so a call at the cap's edge can be told from a comfortably converged one
    on disk; ``with_flight_check`` appends FLAG_FLIGHT_EXCEEDANCE), structure_iterations
    (the sizings at x*), structure_file and structure_file_sha256, structure_envelope_pad
    (the run whose flight is the envelope). at_x and at_zero: the transform's sizings at
    x* and at x = 0; at_x None for a solve that found no x* (search_failed): every key at
    x* is then None (the flags an empty list), the settings, dm at x = 0, the
    plausibility keys and the file are still recorded, so the record says the case was
    structural."""
    st = transform.settings
    settings_items = {
        "structure_set": st.set_name,
        "structure_sizing": st.sizing,
        "structure_dynamic": st.dynamic,
        "structure_entry": st.entry,
        "structure_margin": st.margin,
        "structure_envelope_cap_g": st.envelope_cap_g,
        "structure_overrides": dict(st.overrides),
        "structure_plausibility_ratio": transform.plausibility_ratio,
        "structure_plausibility_factor": plausibility_end_factor(
            st.set_name, transform.plausibility
        ),
        "structure_plausibility_scaled": st.plausibility_scaled,
    }
    if at_x is None:
        out = dict.fromkeys(STRUCTURE_RECORD_KEYS)
        out.update(
            {
                "structure_charged": True,
                "structure_dm_x0_kg": at_zero.total_kg,
                **settings_items,
                "structure_flags": [],
                "structure_file": st.file.path,
                "structure_file_sha256": st.file.sha256,
                "structure_envelope_pad": transform.envelope_pad,
            }
        )
        return out
    inc = at_x.increment
    f = at_x.factor
    req = inc.requirement
    gov = inc.governing
    governing = None
    if gov is not None:
        case = gov.envelope_case
        label = None
        if case is not None and case >= 0:
            label = transform.envelope.pad.cases[case].label
        governing = {
            "stage": gov.stage,
            "element": gov.element,
            "push_mode": gov.push_mode,
            "envelope_mode": gov.envelope_mode,
            "station_index": gov.station_index,
            "z_m": gov.z_m,
            "envelope_case": case,
            "envelope_case_label": label,
        }
    cap = {
        "name": structure.FLAG_FIXED_POINT_CAP,
        "fired": at_x.capped,
        "values": {
            "iterations": at_x.iterations,
            "last_step_kg": at_x.steps[-1],
            "tolerance_kg": STRUCTURE_FIXED_POINT_TOL_KG,
            "max_iterations": STRUCTURE_FIXED_POINT_MAX_ITERATIONS,
            "contraction": at_x.contraction,
        },
    }
    return {
        "structure_charged": True,
        "structure_dm_kg": at_x.total_kg,
        "structure_dm_stage2_kg": at_x.dm_stage2_kg,
        "structure_dm_x0_kg": at_zero.total_kg,
        "structure_flight_exceedance_kg": None,
        **settings_items,
        "structure_dlf": req.dlf,
        "structure_t_r_s": req.rise_time_s,
        "structure_f_Hz": req.axial_frequency_hz,
        "structure_n_q_g": req.n_quasi_g,
        "structure_n_peak_g": req.n_peak_g,
        "structure_F_peak_N": req.f_peak_N,
        "structure_ramp_cost_rel": req.ramp_cost_rel,
        "structure_elements": {f"{e.stage}.{e.element}": f * e.kg for e in inc.elements},
        "structure_closed_form_kg": f * inc.closed_form_kg,
        "structure_ring_kg": f * inc.ring_kg,
        "structure_governing": governing,
        "structure_flags": [*(_flag_record(fl) for fl in inc.flags), cap],
        "structure_iterations": at_x.iterations,
        "structure_file": st.file.path,
        "structure_file_sha256": st.file.sha256,
        "structure_envelope_pad": transform.envelope_pad,
    }


STRUCTURE_RECORD_KEYS: tuple[str, ...] = (
    "structure_charged",
    "structure_dm_kg",
    "structure_dm_stage2_kg",
    "structure_dm_x0_kg",
    "structure_flight_exceedance_kg",
    "structure_set",
    "structure_sizing",
    "structure_dynamic",
    "structure_entry",
    "structure_margin",
    "structure_envelope_cap_g",
    "structure_overrides",
    "structure_plausibility_ratio",
    "structure_plausibility_factor",
    "structure_plausibility_scaled",
    "structure_dlf",
    "structure_t_r_s",
    "structure_f_Hz",
    "structure_n_q_g",
    "structure_n_peak_g",
    "structure_F_peak_N",
    "structure_ramp_cost_rel",
    "structure_elements",
    "structure_closed_form_kg",
    "structure_ring_kg",
    "structure_governing",
    "structure_flags",
    "structure_iterations",
    "structure_file",
    "structure_file_sha256",
    "structure_envelope_pad",
)
"""The run-level keys ``structure_record`` writes, in order (design 4.4): only a
structural run carries any of them."""


def structure_assumption(settings: ResolvedStructureCase, envelope_pad: str) -> str:
    """The assumption line of a structural run (SP7 step S3; neutral: S3a words the
    caveats): the model, the file, the set, the case's sizing, dynamic, entry, margin and
    cap, and any overrides (``settings.provenance``, D-SP7-43: the one string that is
    also the restated dry mass's source), and the run whose flight is the envelope. The
    run carries it after OFFLOAD_STRUCTURE_ASSUMPTIONS
    (``results_io._offload_assumptions``)."""
    return (
        "structure: the dry masses carry the modelled structural mass of the push load "
        f"({settings.provenance}; the envelope is {envelope_pad}'s own flight)"
    )


def _structure_flag_line(flag: Mapping[str, Any]) -> str:
    """The run flag of a fired structure flag record (``_flag_record``'s form: name,
    fired, values): ``<name>: <what fired, with its numbers>``. The release, upper-stack
    and payload-limit checks are flags with numbers, never sized and never blocking
    (D-SP7-19); the cap flag names the cap, the last step and the tolerance. A name this
    function does not know gets a generic line pointing at ``structure_flags``."""
    name, v = flag["name"], flag["values"]
    if name == structure.FLAG_FIXED_POINT_CAP:
        return (
            f"{name}: the structural fixed point stopped at its cap of "
            f"{v['max_iterations']} sizings, last step {v['last_step_kg']:.3g} kg "
            f"(tolerance {v['tolerance_kg']:g} kg)"
        )
    if name == structure.FLAG_RELEASE_UNLOAD:
        return (
            f"{name}: the push's instant release unloads the stack further than the pad's "
            f"MECO shutdown (release swing {v['release_swing_g']:.3g} g0 against MECO's "
            f"{v['meco_swing_g']:.3g} g0; stage-1 LOX and RP-1 bottom pressures "
            f"{v['lox_bottom_pressure_min_abs_pa']:.3g} and "
            f"{v['rp1_bottom_pressure_min_abs_pa']:.3g} Pa absolute; common-dome reverse "
            f"pressure {v['common_dome_reverse_pressure_pa']:.3g} Pa against MECO's "
            f"{v['meco_common_dome_reverse_pressure_pa']:.3g} Pa; upper-stack swing "
            f"{v['upper_stack_swing_N']:.3g} N against MECO's "
            f"{v['meco_upper_stack_swing_N']:.3g} N)"
        )
    if name == structure.FLAG_UPPER_STACK:
        return (
            f"{name}: the push's peak upper-stack load {v['push_n_upper_N']:.4g} N exceeds "
            f"the pad envelope's {v['envelope_n_upper_N']:.4g} N, so stage 2's tanks and the "
            "interstage were sized"
        )
    if name == structure.FLAG_PAYLOAD_LIMIT:
        return (
            f"{name}: the push's peak axial load {v['n_peak_g']:.3g} g0 and release swing "
            f"{v['release_swing_g']:.3g} g0 against the payload's axial limits "
            f"{v['limit_axial_min_g']:g} to {v['limit_axial_max_g']:g} g0"
        )
    if name == structure.FLAG_FLIGHT_EXCEEDANCE:
        cap = v.get("envelope_cap_g")
        capped = (
            "no cap"
            if cap is None or not math.isfinite(float(cap))
            else f"the flight's stage-1 felt n capped at {float(cap):g} g0 as the envelope's was"
        )
        factor = float(v.get(FLIGHT_DM_FACTOR_KEY, 1.0))
        scaled = (
            ""
            if factor == 1.0
            else (
                f"; the exceedance is the unscaled sizing while the dm carries the "
                f"plausibility rule's factor {factor:.4g}"
            )
        )
        stage2 = (
            "stage 2 not checked (not sized by the push)"
            if float(v.get("stage2_checked", 1.0)) == 0.0
            else f"stage 2 {v['stage2_kg']:.3g} kg"
        )
        return (
            f"{name}: the recorded run's own flight after its release needs "
            f"{v['total_kg']:.3g} kg more wall than the pad envelope its structure was sized "
            f"to (stage 1 {v['stage1_kg']:.3g} kg, {stage2}; {STRUCTURE_FLIGHT_CHECK_SCOPE}; "
            f"sized, not charged or iterated; the flight evaluated unfactored against the "
            f"envelope at margin {v.get('margin', 0.0):g}, {capped}{scaled}; the flag's "
            f"threshold is {v['threshold_kg']:g} kg)"
        )
    if name == STRUCTURE_PAYLOAD_FLAG:
        return (
            f"{name}: the payload form's two-pass residual estimate "
            f"{v['residual_estimate_kg']:.3g} kg against the tolerance {v['tolerance_kg']:g} kg, "
            f"contraction {v['contraction']:.3g} against {v['contraction_max']:g} (the passes "
            "are not iterated further; the estimate is never measured)"
        )
    return f"{name}: fired (its numbers are in structure_flags)"


def with_structure_items(rr: RunResult, items: Mapping[str, Any]) -> RunResult:
    """rr with the structural record keys appended to its metrics (``structure_record``)
    and every fired flag in ``structure_flags`` (``size_increment``'s release, upper-stack
    and payload-limit flags, the cap flag, the flight check's and, on a payload case, the
    payload form's, in ``structure_flags`` order) appended to its flags as one line each
    with its numbers (``_structure_flag_line``), so the case record's ``flags``,
    summary.md and a sweep's ``n_flags`` see them; the numbers stay in
    ``structure_flags``. Informational (D-SP7-19): no flag changes a status."""
    metrics = {**rr.result.metrics, **items}
    flags = list(rr.result.flags)
    for flag in items.get("structure_flags", ()):
        if flag["fired"]:
            flags.append(_structure_flag_line(flag))
    return replace(rr, result=replace(rr.result, metrics=metrics, flags=flags))


# ------------------------------------------------------- structure reporting (SP7 S3b)
# STRUCTURE_ARM_CAVEAT (the caveat printed beside the structural sensitivity arms),
# STRUCTURE_PAYLOAD_RECORD_KIND (the kind of a structure payload case's record),
# STRUCTURE_PAYLOAD_CONTRACTION_MAX and STRUCTURE_PAYLOAD_RESIDUAL_FRACTION (the payload
# flag's two limits, which the payload table's labels are built from),
# STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA (the flight check on a payload case: not applicable)
# and STRUCTURE_FLIGHT_CHECK_SCOPE (the elements the flight check covers) live in
# summary.py beside the rows that print them and are re-exported here.

STRUCTURE_PAYLOAD_FLAG = "structure_payload_unconverged"
"""The payload form's flag: the two-pass residual estimate c |P_2* - P_1*| above
STRUCTURE_PAYLOAD_RESIDUAL_FRACTION of the final payload tolerance, or the contraction c
above STRUCTURE_PAYLOAD_CONTRACTION_MAX (both in ``summary``, re-exported here)."""
STRUCTURE_PAYLOAD_CASE_ASSUMPTION = (
    "structure payload case: the variant flies at its own payload capacity P* with the "
    "structure sized for its full-load push in two passes (dm_0 sized at the pad's P_ref, "
    "P_1* searched on the vehicle carrying dm_0, dm_1 sized at P_1*, P_2* searched on the "
    "vehicle carrying dm_1, which is the mass this run carries); the passes are not "
    "iterated further, and the residual of the sizing at P_2* is estimated from the "
    "contraction of the two passes, never measured; the post-hoc flight check is "
    f"{STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA}"
)
"""The assumption line of a structure payload case's recorded run (SP7 step S3b), carried
before its structure line; it ends with STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA (the flight check
is not run on a payload case, review N-S3b-R3-01)."""


def plausibility_rule_text(band_fraction: float) -> str:
    """The plausibility rule in words (design 4.2.5; printed in the Structure subsection)
    with the band's half-width as the structure file states it
    (``heineman_band_fraction``: the edges (1 - band) R and (1 + band) R are printed from
    it, never assumed)."""
    lo, hi = 1.0 - band_fraction, 1.0 + band_fraction
    return (
        "D-SP7-33 (applied as approved, D-SP7-41): the model's envelope mass of the sized "
        "stage-1 tank elements at the central coefficients (M, the non-optimum factors "
        "included) is compared with Heineman's tank relation R = c V^e within its "
        f"+/-{band_fraction:.0%} band (the file's heineman_band_fraction); below {lo:g} R the "
        f"physics band's high-mass end is multiplied by {lo:g} R / M, above {hi:g} R its "
        f"low-mass end by {hi:g} R / M, mechanically; a case that states plausibility_scaled "
        "carries that factor in its dm, and D-SP7-41 asks that the unscaled and the scaled "
        "ends be printed side by side; a calibration check, not a validation"
    )


STRUCTURE_SETS_NOT_IN_FILE = (
    "not in the structure file: the structure file freezes the four sets of searches A to C "
    "and their checks only; the sizing-only tornado and search D's break-even values were "
    "recorded in the phase file's step S2 session log at SP1's headline push and are not "
    "frozen in any config file (the sets' method says D is not frozen there)"
)
"""What ``offload_structure_inputs`` records under ``tornado`` and ``break_even`` (SP7 step
S3b): the structure file carries neither, so the record says so rather than quoting a
number from elsewhere."""


def structure_flight_cases(
    result: Result, vehicle: Vehicle, layout: StackLayout, *, label: str = "flight"
) -> tuple[LoadCase, ...]:
    """A recorded assisted run's post-release load cases for the flight check (pure; SP7
    step S3b; design 4.2: the run's own flight against the envelope its structure was
    sized to). The pad adapter ``structure_pad_cases`` refuses a Result with a push, so
    this adapter reads the rows after the release instead of changing that contract.

    Inputs: result, the recorded run's planar Result (its time series and events; HOLD
    and ASSIST rows are skipped); vehicle, the Vehicle it flew (the offloaded vehicle
    with the modelled dm in its dry masses, at the payload it flew); layout, the structure
    file's StackLayout (stage names and each stage's LOX mass fraction); label, the cases'
    label prefix.
    Output: one FLIGHT LoadCase per stage-1 row with an engine lit after the release
    (phase in LIT_KINDS) and per stage-2 burn row, in time-series order, the masses
    recovered as the pad adapter recovers them (U = stage 2 wet + the fairing while
    attached + the payload; the stage-1 propellant m - dry1 - U, clamped to [0, the
    offloaded load] within STRUCTURE_MASS_TOL_KG; the stage-2 propellant on its burn),
    split by each stage's LOX mass fraction; no hold-down support (no HOLD row). Checked:
    the first flight row's mass is at most the full stack's and stage 1's propellant is 0
    at its depletion event, within STRUCTURE_MASS_TOL_KG (else the vehicle is not the one
    the Result flew). Raises ValueError for a Result that is not planar or has no lit
    stage-1 row after the release. Frame: the stack axis.
    """
    if result.model != PLANAR_MODEL:
        raise ValueError(f"the flight check reads a planar Result, got {result.model!r}")
    masses = stack_masses(vehicle)
    stage1, stage2 = masses.stage1.name, masses.stage2.name
    if (layout.stage1.name, layout.stage2.name) != (stage1, stage2):
        raise ValueError("the structure layout's stage names differ from the vehicle's")
    ts, events = result.timeseries, result.events
    s1, s2 = vehicle.stages
    fairing, payload = vehicle.fairing_mass_kg, vehicle.payload_mass_kg
    drop = _fairing_drop(events)
    m = ts["m_kg"].to_numpy(dtype=float)
    t = ts["t_s"].to_numpy(dtype=float)

    def attached(i: int) -> bool:
        if drop is None or t[i] < drop[0]:
            return True
        if t[i] > drop[0]:
            return False
        return abs(m[i] - drop[1]) <= 0.5 * fairing

    full = s1.wet_mass_kg + s2.wet_mass_kg + fairing + payload
    f1, f2 = layout.stage1.lox_mass_fraction, layout.stage2.lox_mass_fraction
    lox2_full = f2 * s2.propellant_mass_kg
    rp12_full = s2.propellant_mass_kg - lox2_full
    cases: list[LoadCase] = []
    phases = ts["phase"].astype(str).to_numpy()
    stages = ts["stage"].astype(str).to_numpy()
    felt = ts["felt_axial_g"].to_numpy(dtype=float)
    thrust = ts["thrust_N"].to_numpy(dtype=float)
    for i in range(len(ts)):
        phase, stage = phases[i], stages[i]
        if phase not in LIT_KINDS:
            continue
        upper2 = payload + (fairing if attached(i) else 0.0)
        tag = f"{label} {phase} t={t[i]:.4f} s"
        if stage == stage1:
            if not cases and m[i] > full + STRUCTURE_MASS_TOL_KG:
                raise ValueError(
                    f"the Result's first flight mass {m[i]!r} kg exceeds the vehicle's full "
                    f"stack {full!r} kg: the vehicle is not the one the Result flew"
                )
            upper = s2.wet_mass_kg + upper2
            prop1 = _non_negative_mass(m[i] - s1.dry_mass_kg - upper, s1.propellant_mass_kg)
            lox1 = f1 * prop1
            cases.append(
                LoadCase(
                    label=tag,
                    kind=FLIGHT,
                    t_s=float(t[i]),
                    n_g=float(felt[i]),
                    stage1_attached=True,
                    lox_stage1_kg=lox1,
                    rp1_stage1_kg=prop1 - lox1,
                    lox_stage2_kg=lox2_full,
                    rp1_stage2_kg=rp12_full,
                    upper_mass_stage1_kg=upper,
                    upper_mass_stage2_kg=upper2,
                    vehicle_mass_kg=float(m[i]),
                    thrust_N=float(thrust[i]),
                )
            )
        elif stage == stage2:
            prop2 = _non_negative_mass(m[i] - s2.dry_mass_kg - upper2, s2.propellant_mass_kg)
            lox2 = f2 * prop2
            cases.append(
                LoadCase(
                    label=tag,
                    kind=FLIGHT,
                    t_s=float(t[i]),
                    n_g=float(felt[i]),
                    stage1_attached=False,
                    lox_stage1_kg=0.0,
                    rp1_stage1_kg=0.0,
                    lox_stage2_kg=lox2,
                    rp1_stage2_kg=prop2 - lox2,
                    upper_mass_stage1_kg=0.0,
                    upper_mass_stage2_kg=upper2,
                    vehicle_mass_kg=float(m[i]),
                    thrust_N=float(thrust[i]),
                )
            )
    if not any(c.stage1_attached for c in cases):
        raise ValueError("the flight check needs a lit stage-1 row after the release")
    depletion = events[(events["event"] == "propellant") & (events["stage"] == stage1)]
    if not depletion.empty:
        m_dep = float(depletion.iloc[0]["m_kg"])
        on = drop is None or float(depletion.iloc[0]["t_s"]) < drop[0]
        left = m_dep - s1.dry_mass_kg - s2.wet_mass_kg - payload - (fairing if on else 0.0)
        if abs(left) > STRUCTURE_MASS_TOL_KG:
            raise ValueError(
                f"stage 1's propellant at its depletion event is {left!r} kg, not 0: the "
                "vehicle is not the one the Result flew"
            )
    return tuple(cases)


def structure_flight_check(
    transform: StructureTransform, rr: RunResult, sizing: StructureSizing
) -> FlightCheck | None:
    """The post-hoc flight check of a structural offload case's recorded run (design 4.2;
    SP7 step S3b): the run's own flight after its release (``structure_flight_cases`` of
    its Result on its vehicle, which carries the restated dm, at the payload it flew,
    P_ref) against the transform's envelope (``structure.flight_exceedance``, the tank
    elements with a station envelope: STRUCTURE_FLIGHT_CHECK_SCOPE; stage 2 when the
    sizing at x* sized it), the flight's stage-1 felt n capped as the envelope's was and
    the flight unfactored against the envelope at the case's margin (so a capped case
    does not report the pad's own loads above the cap, and a margin row's check fires
    only above the margin's headroom). The exceedance is sized, never charged or
    iterated: the solve is not repeated. It is the unscaled sizing: a plausibility-scaled
    case's dm carries the rule's factor (``sizing.factor``), its exceedance does not, and
    the flag's values carry that factor under FLIGHT_DM_FACTOR_KEY (1.0 for an unscaled
    case) so the two bases are told apart on disk and in the flag line. None when the run
    has no time series to check (a solve that recorded no flight, or a test's fake run).
    Not called on a structure payload case (STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA): its run
    flies its own P_2* while the envelope is the pad's at P_ref, so the check would
    measure the payload gain, which the pad's own flight at P_2* would need too."""
    frame = rr.result.timeseries
    needed = {"t_s", "phase", "stage", "felt_axial_g", "m_kg", "thrust_N"}
    if frame.empty or not needed <= set(frame.columns) or rr.result.events is None:
        return None
    payload = rr.result.metrics.get("payload_kg")
    vehicle = rr.resolved.to_vehicle()
    if payload is not None and math.isfinite(float(payload)):
        vehicle = with_payload(vehicle, float(payload))
    cases = structure_flight_cases(rr.result, vehicle, transform.layout, label=rr.name)
    check = flight_exceedance(
        transform.geometry,
        transform.settings.coefficients,
        transform.envelope,
        flight_load_set(cases),
        stage2=sizing.increment.stage2_sized,
    )
    flag = check.flag
    values = (*flag.values, (FLIGHT_DM_FACTOR_KEY, float(sizing.factor)))
    return replace(check, flag=replace(flag, values=values))


FLIGHT_DM_FACTOR_KEY = "dm_plausibility_factor"
"""The flight check flag's value naming the plausibility factor the case's dm carries
(``structure_flight_check``; 1.0 unless the case is plausibility-scaled): the exceedance
itself is never scaled."""


def with_flight_check(items: Mapping[str, Any], check: FlightCheck | None) -> dict[str, Any]:
    """The structure record keys with the flight check filled in (SP7 step S3b):
    ``structure_flight_exceedance_kg`` set to the check's total (the unscaled sizing, a
    scaled case's dm carrying the factor its flag names) and FLAG_FLIGHT_EXCEEDANCE
    appended to ``structure_flags`` (with its numbers, fired above the threshold); the
    items unchanged, as a copy, when the check is None (``structure_flight_check`` had no
    time series). Called before ``with_structure_items``, so a fired flag reaches the run's
    flags like the others."""
    out = dict(items)
    if check is None:
        return out
    out["structure_flight_exceedance_kg"] = check.total_kg
    out["structure_flags"] = [*out.get("structure_flags", []), _flag_record(check.flag)]
    return out


def _plausibility_record(check: Plausibility, envelope: Envelope) -> dict[str, Any]:
    """The plausibility table as plain data (design 4.2.5; ``structure.plausibility``):
    the element masses, M_model (physical and cylinder-equivalent lengths), the length
    ratios, R, its per-tank form, band and band fraction, M/R, the factor on each end, the
    rule's text (``plausibility_rule_text`` at the file's band) and the quantities printed
    beside; and the rule's trigger (SP7 step S3b, D-SP7-41: "the ratio and its trigger"),
    computed from the envelope, never typed in: ``dominant``, the stage-1 tank element
    that carries the largest share of M_model, its share [-], and the governing mode, load
    case label and station height z [m] of its thickest station in the envelope the rule
    reads (``_envelope_elements_record``'s point); the summary prints it with the central
    case's own push increment on that element."""
    items = dict(check.element_kg)
    name = max(items, key=lambda n: items[n])
    element = envelope.element(STAGE1, name)
    i = int(np.argmax(element.t_m))
    case = int(element.case_index[i])
    load_case = envelope.pad.cases[case] if case >= 0 else None
    return {
        "element_kg": items,
        "m_model_kg": check.m_model_kg,
        "m_model_cylinder_kg": check.m_model_cylinder_kg,
        "lox_length_ratio": check.lox_length_ratio,
        "rp1_length_ratio": check.rp1_length_ratio,
        "relation_kg": check.relation_kg,
        "relation_per_tank_kg": check.relation_per_tank_kg,
        "lower_kg": check.lower_kg,
        "upper_kg": check.upper_kg,
        "band_fraction": check.band_fraction,
        "ratio": check.m_model_kg / check.relation_kg,
        "low_mass_end_factor": check.favourable_end_factor,
        "high_mass_end_factor": check.adverse_end_factor,
        "rule": plausibility_rule_text(check.band_fraction),
        "dominant": {
            "element": f"{STAGE1}.{name}",
            "share": items[name] / check.m_model_kg,
            "mode": element.modes[i],
            "case_label": None if load_case is None else load_case.label,
            "z_m": float(element.z_m[i]),
        },
        "akin_kg": check.akin_kg,
        "interstage_relation_kg": check.interstage_relation_kg,
        "thrust_structure_relation_kg": check.thrust_structure_relation_kg,
        "stage1_dry_less_engines_kg": check.stage1_dry_less_engines_kg,
    }


def _envelope_elements_record(envelope: Envelope) -> list[dict[str, Any]]:
    """The envelope per element as plain data: for each element of each built stage, the
    required thickness's maximum over its stations [m], the station index and height z
    [m] of that maximum, the governing mode there and the governing load case (its index,
    label and time [s]; None at the minimum gauge)."""
    out: list[dict[str, Any]] = []
    for stage, table in ((STAGE1, envelope.stage1), (STAGE2, envelope.stage2)):
        if table is None:
            continue
        for name, element in table.items():
            i = int(np.argmax(element.t_m))
            case = int(element.case_index[i])
            load_case = envelope.pad.cases[case] if case >= 0 else None
            out.append(
                {
                    "stage": stage,
                    "element": name,
                    "t_max_m": float(element.t_m[i]),
                    "station_index": i,
                    "z_m": float(element.z_m[i]),
                    "mode": element.modes[i],
                    "case_index": case if case >= 0 else None,
                    "case_label": None if load_case is None else load_case.label,
                    "case_t_s": None if load_case is None else load_case.t_s,
                }
            )
    return out


def _sets_record(config: StructureConfig) -> dict[str, Any] | None:
    """The frozen sets as the structure file records them (design 4.2.6), as plain data:
    the label, source, method, evaluation count, fallbacks, seed, parent commit and
    reproducing test, and per set its values, searches, implied stack length, each
    search's polish (passes, converged, dm before and after, the moves counted) and each
    extremality check; None for a file without sets."""
    sets = config.sets
    if sets is None:
        return None
    out: dict[str, Any] = {
        "label": sets.label,
        "source": sets.source,
        "method": sets.method,
        "evaluation_count": sets.evaluation_count,
        "fallbacks": list(sets.fallbacks),
        "seed": sets.seed,
        "parent_commit": sets.parent_commit,
        "test": sets.test,
    }
    for name in STRUCTURE_SET_NAMES:
        item = getattr(sets, name)
        out[name] = {
            "values": dict(item.values),
            "searches": item.searches,
            "implied_stack_length_m": item.implied_stack_length_m,
            "polish": [
                {
                    "search": p.search,
                    "passes": p.passes,
                    "converged": p.converged,
                    "dm_before_kg": p.dm_before_kg,
                    "dm_after_kg": p.dm_after_kg,
                    "moves": len(p.moves),
                }
                for p in item.polish
            ],
            "extremality": [
                {
                    "search": c.search,
                    "check": c.check,
                    "trials": c.trials,
                    "found_dm_kg": c.found_dm_kg,
                    "extreme_dm_kg": c.extreme_dm_kg,
                    "excess_kg": c.excess_kg,
                    "path": c.path,
                    "value": c.value,
                }
                for c in item.extremality
            ],
        }
    return out


def offload_structure_inputs(
    sfile: StructureFile, pad: RunResult, reference_payload_kg: float, full_load_vehicle: Vehicle
) -> dict[str, Any]:
    """The block-level ``structure_inputs`` record of an offload pass with a structure
    block (design 4.4, "Records"; SP7 step S3b; beside ``energy_inputs``): the structure
    file's path and sha256; the envelope pad and P_ref [kg]; ``envelope``, the pad's
    envelope per element at the central coefficients, margin 0 and no cap (both stages;
    ``_envelope_elements_record``: the required thickness's maximum per element, its
    station, mode and governing load case); ``plausibility``, the rule's table on that
    envelope (``_plausibility_record``); ``sets``, the frozen sets as the file records
    them (``_sets_record``, with the method and the evaluation count; their label is
    structure.SEARCH_LABEL); ``tornado`` and ``break_even`` None with
    STRUCTURE_SETS_NOT_IN_FILE as ``tornado_note`` (the file freezes neither: a
    deviation from design 4.4's record list, logged in the phase file's section 12,
    since the record quotes no value the frozen file does not hold). The pad is read
    through ``offload_pad_load_set``; the geometry is the full-load vehicle's (the
    experiment's baseline vehicle at its full loads)."""
    config = sfile.config
    layout = config.stack_layout()
    cases = offload_pad_load_set(pad, reference_payload_kg, layout)
    masses = stack_masses(full_load_vehicle)
    coeffs = config.coefficients()
    geometry = build_geometry(masses, layout, coeffs)
    envelope = structure.build_envelope(geometry, coeffs, cases)
    check = plausibility(geometry, coeffs, envelope)
    return {
        "file": sfile.path,
        "sha256": sfile.sha256,
        "envelope_pad": pad.name,
        "reference_payload_kg": reference_payload_kg,
        "envelope_basis": (
            "the central coefficients, margin 0, no cap; the envelope of a case with a "
            "margin or a cap is its own"
        ),
        "envelope": _envelope_elements_record(envelope),
        "plausibility": _plausibility_record(check, envelope),
        "sets": _sets_record(config),
        "sets_label": structure.SEARCH_LABEL,
        "tornado": None,
        "break_even": None,
        "tornado_note": STRUCTURE_SETS_NOT_IN_FILE,
    }


# ------------------------------------------------------------------- structure search (SP7 S2)

STRUCTURE_SEARCH_VARIANT = "silo_cold"
"""The variant of the committed experiments whose push is SP1's headline (constant_accel
3 g0 net, 100 m vertical stroke, cold start: stage 1 lit 0.5 s after release)."""
STRUCTURE_PAYLOAD_TOL_KG = 0.002
"""How close the flown pad's P* must lie to SP1's recorded P_ref [kg] (design section 6,
criterion 3: the pad capacities within 0.002 kg)."""
STRUCTURE_OFFLOAD_MODE: OffloadMode = "stage1"
"""The headline push's offload mode (SP1's stage-1 solve)."""


def _push_stage1_ignition_s(
    setup: PlanarSetup, vehicle: Vehicle, push_time_s: float
) -> float | None:
    """Stage 1's ignition time from the push start [s] when it lights on the track (before
    the release at push_time_s), else None (a cold push)."""
    spec = setup.ignition[vehicle.stages[0].name]
    if spec.fails or spec.lights_at_height:
        return None
    t_abs = spec.t_ign_abs_s(push_time_s, 0.0)
    return t_abs if t_abs < push_time_s else None


def structure_sizing(
    config: StructureConfig,
    vehicle: Vehicle,
    pad: PadLoadSet,
    run_config: RunConfig,
    *,
    headline_offload_kg: float,
) -> SizingFn:
    """The screened search's sizing (``structure.SizingFn``): a coefficient assignment (paths
    to file values) and a ``structure.SizingCase`` to one ``structure.size`` with a fresh
    geometry and envelope.

    Inputs: config, the structure file; vehicle, the full-load vehicle at P_ref (the
    geometry's masses, closed over); pad, the flown pad's PadLoadSet; run_config, the
    variant whose push is sized (a constant_accel run: its assist, track, g_eff and stage-1
    ignition); headline_offload_kg [kg], the push's stage-1 offload when a case gives none.
    Output: the SizingFn. Each push is the analytic constant_accel case
    (``constant_accel_push_load``) of the vehicle offloaded along STRUCTURE_OFFLOAD_MODE,
    built once per offload and kept (a closure cache). Frame: the stack frame.
    """
    masses = stack_masses(vehicle)
    layout = config.stack_layout()
    pushes: dict[float, PushLoad] = {}

    def push_at(offload_kg: float) -> PushLoad:
        if offload_kg not in pushes:
            flown = (
                with_offload(vehicle, STRUCTURE_OFFLOAD_MODE, offload_kg)
                if offload_kg > 0.0
                else vehicle
            )
            setup = planar_setup(run_config, flown)
            if not isinstance(setup.assist, ConstantAccelAssist) or setup.track is None:
                raise ValueError(f"run {run_config.name!r}: the push is not a constant_accel push")
            t_push = setup.assist.push_time_s(setup.track.length_m)
            pushes[offload_kg] = constant_accel_push_load(
                flown,
                setup.assist,
                setup.track,
                layout,
                g_eff_mps2=setup.env.g_ref_mps2,
                stage1_ignition_s=_push_stage1_ignition_s(setup, flown, t_push),
            )
        return pushes[offload_kg]

    def sizing(values: Mapping[str, CoefficientValue], case: SizingCase) -> Increment:
        coeffs = config.coefficients(overrides=dict(values), check_ranges=case.check_ranges)
        x = headline_offload_kg if case.offload_kg is None else case.offload_kg
        return size(
            masses,
            layout,
            coeffs,
            pad,
            push_at(x),
            dynamic=case.dynamic,
            entry=case.entry,
            margin=case.margin,
            envelope_cap_g=case.envelope_cap_g,
        )

    return sizing


@dataclass(frozen=True)
class StructureSearchInputs:
    """What the screened search sizes against (``structure_search_inputs``): experiment, the
    experiment's name; variant, the push's variant; pad, the flown pad baseline (RunResult);
    payload_kg, its P* [kg]; vehicle, the full-load vehicle at P* (the geometry's masses);
    pad_cases, its PadLoadSet; headline_offload_kg [kg]; push_run, the variant's RunConfig;
    sizing, the SizingFn; ranges, the structure file's coefficients; pad_seconds, the pad's
    flight time [s] (wall clock)."""

    experiment: str
    variant: str
    pad: RunResult
    payload_kg: float
    vehicle: Vehicle
    pad_cases: PadLoadSet
    headline_offload_kg: float
    push_run: RunConfig
    sizing: SizingFn
    ranges: tuple[CoefficientRange, ...]
    pad_seconds: float


def structure_search_inputs(
    resolved: ResolvedExperiment,
    config: StructureConfig,
    *,
    offload_kg: float,
    reference_payload_kg: float | None = None,
    variant: str = STRUCTURE_SEARCH_VARIANT,
) -> StructureSearchInputs:
    """Fly a committed experiment's pad baseline and build the screened search's inputs
    (SP7 step S2; design 4.2.6: the envelope from the pad as flown, the headline push
    analytic).

    Inputs: resolved, the experiment (cli.load_experiment); config, its vehicle's structure
    file; offload_kg, the headline push's stage-1 offload [kg] (SP1's recorded x*);
    reference_payload_kg, SP1's recorded P_ref [kg] the flown P* must equal within
    STRUCTURE_PAYLOAD_TOL_KG (None: not checked); variant, the push's variant.
    Output: StructureSearchInputs. Raises ValueError when the pad's search gives no P*,
    its P* misses the reference, or the variant is not a constant_accel push.
    """
    t0 = time.perf_counter()
    pad = run_resolved(resolved.baseline)
    pad_seconds = time.perf_counter() - t0
    p_star = pad.result.metrics.get("payload_kg")
    if p_star is None or not math.isfinite(float(p_star)):
        raise ValueError(f"the pad baseline's payload search gave no P* ({p_star!r})")
    if reference_payload_kg is not None and abs(p_star - reference_payload_kg) > (
        STRUCTURE_PAYLOAD_TOL_KG
    ):
        raise ValueError(
            f"the flown pad's P* {p_star!r} kg is not SP1's P_ref {reference_payload_kg!r} kg "
            f"within {STRUCTURE_PAYLOAD_TOL_KG} kg"
        )
    vehicle = with_payload(resolved.baseline.to_vehicle(), float(p_star))
    layout = config.stack_layout()
    cases = pad_load_set(structure_pad_cases(pad.result, vehicle, layout))
    push_run = resolved.runs[variant].run
    return StructureSearchInputs(
        experiment=resolved.experiment.name,
        variant=variant,
        pad=pad,
        payload_kg=float(p_star),
        vehicle=vehicle,
        pad_cases=cases,
        headline_offload_kg=offload_kg,
        push_run=push_run,
        sizing=structure_sizing(config, vehicle, cases, push_run, headline_offload_kg=offload_kg),
        ranges=config.coefficient_ranges(),
        pad_seconds=pad_seconds,
    )


STRUCTURE_HEADLINE_CASE = SizingCase()
"""The headline push's sizing case (rise_time, aft_ring, margin 0, no cap)."""
STRUCTURE_STEP_CASE = SizingCase(dynamic="step")
"""The step row's sizing case (DLF 2 on the plain plateau), search B's push."""
STRUCTURE_TIMING_REPEATS = 20
"""Repeats of the timed sizing (the median is taken)."""


def time_structure_sizing(
    inputs: StructureSearchInputs, repeats: int = STRUCTURE_TIMING_REPEATS
) -> tuple[float, float]:
    """The median wall time [s] of one sizing at the central coefficients with a fresh
    geometry and envelope (``structure.size``), at the headline and at the step row (stage 2
    sized), after one warm-up each (the pad's features cached): the rate the fallbacks of
    source note 9.3 are chosen by (``structure.choose_fallbacks`` on the larger median; the
    structure files' sets notes record the medians this call measured before the search)."""
    out = []
    for case in (STRUCTURE_HEADLINE_CASE, STRUCTURE_STEP_CASE):
        inputs.sizing({}, case)
        times = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            inputs.sizing({}, case)
            times.append(time.perf_counter() - t0)
        out.append(sorted(times)[len(times) // 2])
    return out[0], out[1]


def structure_screened_search(
    inputs: StructureSearchInputs, *, fallbacks: Sequence[str] = ()
) -> tuple[ScreenedSearch, SearchEvaluator]:
    """Searches A to C (``structure.screened_search``) on the inputs with the given
    fallbacks; returns the search and its evaluator (whose memo serves search D and the
    reports)."""
    evaluator = SearchEvaluator(inputs.sizing, inputs.ranges)
    search = screened_search(
        evaluator,
        headline=STRUCTURE_HEADLINE_CASE,
        step=STRUCTURE_STEP_CASE,
        fallbacks=fallbacks,
    )
    return search, evaluator


def structure_search_method(inputs: StructureSearchInputs, search: ScreenedSearch) -> str:
    """The method sentence the structure file records for the frozen sets."""
    grid = (
        structure.GRID_POINTS_FALLBACK
        if structure.FALLBACK_GRID_TWO_POINTS in search.fallbacks
        else structure.GRID_POINTS
    )
    return (
        "Design 4.2.6 and source note section 9.3, searches A to C (D, the design axes' "
        "break-even values, is not frozen here), sizing only, at the headline push of "
        f"{inputs.experiment}'s {inputs.variant} (the analytic constant_accel case at a "
        f"stage-1 offload of {inputs.headline_offload_kg!r} kg and P_ref "
        f"{inputs.payload_kg!r} kg) on the envelope of its pad baseline as flown. A: the "
        "physics band at the design axes' central: the tornado, "
        f"{structure.SCAN_POINTS}-point scans, step 3 (monotone coefficients at their ends; "
        f"the pressures and any other non-monotone coefficient on {grid} points per set "
        "direction, crossed with the (s_dg, gerard_row) combinations, stage by stage), then "
        "the polish of D-SP7-38 (each varied coefficient moved alone over its "
        f"{structure.SCAN_POINTS} scan points or its choices, re-read at the end itself, "
        f"until a pass moves nothing; at most {structure.POLISH_MAX_PASSES} passes). B: the "
        "stage-2-only five per physics set at the step row (DLF 2), enumerated and polished "
        "with every other coefficient at A's value. C: the outer envelope, A re-run at the "
        "design axes' two corners (the margin's direction from its tornado). Checks, "
        f"recorded and not acted on: {search.physics.samples} seeded samples for A (numpy "
        "default_rng; B and C their own), and a one-coordinate check from each found end "
        f"({structure.LOCAL_CHECK_POINTS} points per continuous coefficient, every other "
        "choice of a discrete one; B's also over the stage-1 coefficients it holds at A's "
        "values). The ends are the extremes this search found, not bounds: neither check "
        "proves an end extreme."
    )


def structure_sets_record(
    inputs: StructureSearchInputs,
    config: StructureConfig,
    search: ScreenedSearch,
    *,
    parent_commit: str,
    test: str,
    note: str | None = None,
) -> dict[str, Any]:
    """The structure file's ``sets`` block for a search (plain data, as YAML writes it):
    the label, a source naming the search and the test, the method, the evaluation count,
    the fallbacks, the seed, the parent commit, the test, the note and the four sets with
    their values, searches, polish records (each move with the dm it adds [kg]),
    extremality checks (the found end's dm, the most extreme trial and its excess [kg],
    sizing-only numbers at the search's push) and implied stack lengths
    (``structure.implied_stack_length_m`` on each set's geometry, the file's fairing
    height)."""
    masses = stack_masses(inputs.vehicle)
    layout = config.stack_layout()
    fairing = config.layout.fairing_height_m.value
    record: dict[str, Any] = {
        "label": search.label,
        "source": (
            "SP7 step S2's screened search (src/launchsim/structure.py screened_search; "
            f"design 4.2.6, source note section 9.3), reproduced by {test}"
        ),
        "method": structure_search_method(inputs, search),
        "evaluation_count": search.evaluations,
        "fallbacks": list(search.fallbacks),
        "seed": search.seed,
        "parent_commit": parent_commit,
        "test": test,
    }
    if note is not None:
        record["note"] = note
    for item in search.sets:
        coeffs = config.coefficients(overrides=item.coefficient_values())
        geometry = build_geometry(masses, layout, coeffs)
        record[item.name] = {
            "values": dict(item.values),
            "searches": item.searches,
            "polish": [_polish_record(name, polish) for name, polish in item.polish],
            "extremality": [_check_record(name, check) for name, check in item.extremality],
            "implied_stack_length_m": implied_stack_length_m(geometry, fairing),
        }
    return record


def _polish_record(search: str, polish: structure.Polish) -> dict[str, Any]:
    """One search's polish as the sets block writes it (plain data; dm in kg)."""
    return {
        "search": search,
        "passes": polish.passes,
        "converged": polish.converged,
        "dm_before_kg": float(polish.dm_before_kg),
        "dm_after_kg": float(polish.dm_after_kg),
        "moves": [
            {
                "path": move.path,
                "from_value": move.from_value,
                "to_value": move.to_value,
                "dm_change_kg": float(move.dm_change_kg),
                "pass_index": move.pass_index,
            }
            for move in polish.moves
        ],
    }


def _check_record(search: str, check: structure.ExtremalityCheck) -> dict[str, Any]:
    """One extremality check as the sets block writes it (plain data; dm in kg)."""
    return {
        "search": search,
        "check": check.check,
        "trials": check.trials,
        "found_dm_kg": float(check.found_dm_kg),
        "extreme_dm_kg": None if check.extreme_dm_kg is None else float(check.extreme_dm_kg),
        "excess_kg": float(check.excess_kg),
        "path": check.path,
        "value": check.value,
    }
