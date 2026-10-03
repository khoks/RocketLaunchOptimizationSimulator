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
``with_assumptions`` and the offload assumption texts here at call time. These are the
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

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

import pandas as pd

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
    ChecksConfig,
    ResolvedExperiment,
    ResolvedRun,
    RunConfig,
)
from launchsim.constants import MU_EARTH_M3S2
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
    planar_problem_factory,
    solve_offload,
)
from launchsim.orbit import TargetOrbit
from launchsim.phases import (
    AscentStart,
    IgnitionSpec,
    IntegratorSettings,
    PhaseResult,
    RunTrace,
    VerticalPlanner,
)
from launchsim.phases.planar import PLANAR_MODEL, PlanarEnvironment, PlanarPlanner
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
from launchsim.vehicle import OffloadMode, Vehicle, with_payload

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
    reaches, a height at or above the drag-free apex) writes nothing. Raises
    ValueError naming the run and where it comes from."""
    for label, run in every_resolved_run(resolved):
        try:
            run_ignition_specs(run.run, run.to_vehicle())
        except ValueError as exc:
            raise ValueError(f"{label}: {exc}") from exc


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
run, a paired pad, a pad control's recorded run; docs/physics.md, "Assumptions")."""


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


def offload_problem_factory(resolved: ResolvedRun) -> ProblemFactory:
    """The planar problem factory of a resolved run (``offload.planar_problem_factory``
    of its SearchContext, built as ``run_planar`` builds it: ``planar_setup`` and
    ``search_context``), for an offload solve on that run's vehicle."""
    vehicle = resolved.to_vehicle()
    setup = planar_setup(resolved.run, vehicle)
    return planar_problem_factory(search_context(setup, vehicle, resolved.run.end))


def solve_resolved_offload(
    resolved: ResolvedRun, mode: OffloadMode, reference_payload_kg: float
) -> OffloadResult:
    """``offload.solve_offload`` on a resolved run's vehicle along mode at the reference
    payload P_ref [kg], without its built-in verification (the pipeline verifies with
    ``run_resolved`` of the offloaded run, ``offload.with_verification``). Looked up on
    this module at call time by ``results_io``."""
    factory = offload_problem_factory(resolved)
    return solve_offload(factory, resolved.to_vehicle(), mode, reference_payload_kg, verify=False)


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
