<!-- Record of SP7 step 0: read-only survey 02-config-and-validators (the configuration layer and KI-030's validators), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# 02 - Config and validators: the configuration layer SP7 builds on (survey at 22c62e9)

This read-only survey of the configuration layer was done at HEAD 22c62e9 with a clean tree. Nothing in the repository was edited, created or run, and `git status --short` was empty after every step. Four facts shape the SP7 design:

1. **The resolved dicts are the raw merged YAML, not `model_dump`.** The digest pin, `resolved_config.yaml` and `compare.trajectory_key` all hash the raw dicts. A new field with a default on a pydantic model therefore cannot move a shipped digest. Measured: with a defaulted field added to `ConstantAccelConfig`, the 214 run and vehicle dicts of the seven shipped files hash the same. What such a field does break is the dump-key pin at tests/test_config.py 432-443 (two failures measured). Inside `SearchConfig` it would move `budget_id`. Section 5.10 of the phase file names the wrong guard.
2. **All 16 KI-030 inputs reproduce at HEAD.** Per-field `strict=True` plus `allow_inf_nan=False` refuses 12 of them. The other 4 (`t_ign_s` of ±1e9, `exit_altitude_m` of -1000 and 5000) need range bounds, which is a policy choice. With that patch every shipped file resolves to identical digests and YAML integers such as `stroke_m: 100` are still accepted. Exactly one existing test case fails (tests/test_config.py 389). Strictness for the whole model (`strict=True` on `_Model`) refuses all six planar files.
3. **No existing construct gives an assisted variant its own payload search with an extra stage-1 dry mass the pad does not get.** SP7's payload form needs a new construct.
4. **A structural offload case that applies the structural mass dm inside the solve factory has two traps.** It would silently reuse the headline case's solve through the solve memo (results_io.py 1174), unless the structure enters the start's trajectory key. Its verification would fly without dm, unless `offload_solved_run` restates the dry mass at the solved offload x*.

## 1. Method and scratch files

**How it was checked.** Everything below was checked at 22c62e9 by reading the code and by scripts that call `config.resolve_experiment` on dicts read with `cli.load_yaml`. The digest check calls `cli.load_experiment`, which adds the pure `check_result_names` and `check_resolved`. Nothing was flown.

**Candidate validators.** To test them, `src/launchsim` (without `__pycache__`) was copied into the scratch folder, the copy was edited, and that copy was put first on `PYTHONPATH`. Each script prints which `launchsim` it imported.

**Targeted pytest runs.** They used `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`; the full suite was not run.

**REPORT.md was not written.** The harness refused the write ("Subagents should return findings as text, not write report files"), so this message is the report.

Scratch folder: `C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/02-config-and-validators/`

| Script | Output | What it does |
|---|---|---|
| `s1_scan_shipped.py` | `s1_scan_shipped_out.txt` | For every shipped experiment: numeric-looking string leaves, bool leaves, and the value and type of every KI-030 field in every resolved run dict |
| `s2_ki030_probe.py` | `s2_probe_head.json`, `s2_probe_ki030.json` | 57 one-value edits of `silo_offload_2d` through `resolve_experiment`: the 16 KI-030 items, 8 controls and 33 further edits |
| `s3_make_patched.py` | `patched_ki030/`, `patched_default/`, `patched_global_strict/` | Three edited copies of the sources: strict and finite per field; one new field with a default; strict on `_Model` |
| `s4_compare.py` | `s4_compare_out.md` | The probe table and the digest comparison |
| `s5_digests.py` | `s5_digests_{head,ki030,default,global_strict}.json` | `planar_pin_support.resolved_digests` for all 7 files under each source tree, compared with tests/data/planar_pins/resolved_digests.json |
| `s7_payload_form_probe.py` | `s7_payload_form_probe_out.txt` | Which existing constructs could carry an assisted-only dry mass |
| pytest runs | `s6_pytest_ki030_config.txt`, `s6_pytest_default_config.txt`, `s6_pytest_ki030_appform.txt` | test_config.py + test_config_planar.py (`-m "not slow"`) under `patched_ki030` and `patched_default`; test_appform.py under `patched_ki030` |

Versions: pydantic 2.13.5, PyYAML 6.0.3.

## 2. The assist configuration today (facts)

**Base model.** `_Model` (config.py 219-222) sets `extra="forbid", frozen=True` and is not strict, so lax coercion applies: `True` becomes 1.0, `"100"` becomes 100.0, `"yes"` becomes True. Only the fields that say so set `allow_inf_nan=False`: `Quantity.value` 246, `FiniteFloat` 270, `exit_speed_mps` 640, the `at_*` fields 797-799, `planar_max_step_s` 900, `stage1_t`/`stage2_t` 1574/1576, and `stage2_offload_t`/`stage1_dry_mass_added_t` 1641-1642.

**Planned models.**
- `PlannedModel = Literal["linear_motor", "cable_winch"]` at config.py 78; `PLANNED_MODELS` at 79-80.
- `PlannedAssistConfig` (713-723) uses `extra="allow"` so that the "planned for Phase 3" error (723) wins over an extra-key error.
- The union is `AssistConfig = Annotated[NoAssistConfig | ConstantAccelConfig | PlannedAssistConfig, Field(discriminator="model")]` (726-728).

Every consumer of the planned-model names at HEAD:
- config.py 25-29 (module docstring) and 719.
- appform.py 64 (import) and 187: `ASSIST_UNION_TAGS = frozenset({"none", "constant_accel", *PLANNED_MODELS})`. Its only use is `_clean_loc` (1700-1707), which strips union tags from pydantic error locations.
- tests/test_config.py 26 (import).
- tests/test_config.py 218-220: the `linear_motor` refusal, plus the pin `PLANNED_MODELS == ("linear_motor", "cable_winch")`.
- tests/test_config.py 283-289: `test_other_drives_are_phase_3`, parametrized on both names, matching "Phase 3", including a block with an extra `F_max_kN` key.

Uses of the literal `"linear_motor"` that do not go through config validation:
- tests/test_caveat_wording.py 479-489 and 689-712 edit resolved_config dicts directly.
- tests/test_planar_pipeline.py 988-997 pins `drive_efficiency` as trajectory-relevant for `linear_motor` (`compare.ENERGY_ONLY_ASSIST_KEYS`, compare.py 1744-1749).
- Docstrings: assist/__init__.py 5-10 and 41-42, assist/constant_accel.py 11, physics.md 4623 and 5040.

**`TrackConfig`** (589-609):
- `angle_deg: float = 90.0` (593); only 90 is accepted (596-604).
- `exit_altitude_m: float = 0.0` (594) has no bound and no finiteness check.
- `phi_rad` gives the SI angle (606-609).

**`NoAssistConfig`** (612-615) has only `model: "none"`.

**`ConstantAccelConfig`** (618-710):

| Field (line) | Type, default, bound | SI property |
|---|---|---|
| `model` 638 | `Literal["constant_accel"]` | |
| `net_accel_g` 639 | `float \| None`, None, `gt=0` (inf accepted) | `net_accel_mps2` 691-700 (`units.from_g`, or v²/(2L) from the exit speed) |
| `exit_speed_mps` 640 | `float \| None`, None, `gt=0`, finite | |
| `stroke_m` 641 | `float`, required, `gt=0` (inf accepted) | |
| `carriage_mass_t` 642 | `float`, 0.0, `ge=0` | `carriage_mass_kg` 702-705 |
| `brake_decel_g` 643 | `float`, required, `gt=0` | `brake_decel_mps2` 707-710 |
| `drive_efficiency` 644 | 1.0, `(0, 1]` | |
| `exhaust_impingement_fraction` 645 | 0.0, `[0, 1]` | |
| `shaft` 646 | `Literal["vented"]` | |
| `allow_negative_drive_force` 647 | `bool` False | |
| `track` 648 | `TrackConfig()` | |

**How the push is stated.** `_one_push_parameterisation` (650-676) requires exactly one of the `ASSIST_KEY_FAMILIES` keys (88-90) to be present. An explicit null counts as given, through `model_fields_set` (655-662). A null value is refused (663-667). For the exit-speed form the derived a = v²/(2L) must be finite and > 0 (668-675).

**How unset keys are left out of a dump.**
- `_dump_one_push_key` (678-689) is a wrap serializer that deletes the push key holding None from `model_dump`.
- It is pinned by tests/test_config.py 415-448, with the exact key list at 432-443.
- The only other dump rule is `IgnitionConfig._dump_one_ramp_start` (831-842). Every other model dumps every field, defaults included.

**What a "resolved dict" is.**
- `resolve_run` (2531-2577) sets `name` on the merged raw dict (2535) and validates it as a `RunConfig` (2536). It stores that raw dict as `ResolvedRun.run_dict` and a deep copy of the raw vehicle dict (2571-2577).
- Variants are built by `merge_run_dicts` over the baseline after the shared blocks are injected (2849, 2854; rules at 2146-2177, including the `SWITCH_KEYS` wholesale replace at 81-84 and 2175-2177).
- Sweep points, sensitivity cases, bounds and offload starts are built by `apply_overrides` / `_set_path` (2270-2346).
- `inject_shared` (1828-1839) puts `dynamics`, `site` and `planar` right after `name`.

These raw dicts are what three consumers use:
- `results_io._resolved_config_dict` (589-622) writes them.
- `compare.trajectory_key` (1768-1783) hashes them.
- The digest pin (tests/planar_pin_support.py 126-130, 185-194) hashes them.

The only `model_dump` on the run path is `SearchConfig.budget_id` (config.py 1218-1222, "every field, defaults included"), recorded as `search_budget_id` (metrics_planar.py 1187; results_io.py 677, 2025). The raw dicts keep YAML's own spelling: integers stay integers, and the planar `'1.0e6'`/`'1.0e4'` leaves stay strings (PyYAML reads an unsigned exponent as a string).

**Measured with `patched_default`** (HEAD plus `force_rise_time_s: float | None = None` on `ConstantAccelConfig`):
- All 7 shipped files give identical digests: 214 labels, run and vehicle dict each. The 4 pinned files report no problems, and `budget_id` is unchanged.
- The silo_cold assist dump gains the key, and `RunConfig.model_validate(run.model_dump(mode="json")) == run` still holds.
- test_config.py plus test_config_planar.py: 249 pass. Only the two parametrizations of `test_constant_accel_dump_states_the_push_by_its_one_key` fail, on the key list at 432-443.

## 3. What a `LinearMotorConfig` needs

### Constraints at HEAD (facts)

- **Field names.** `test_exclusive_family_table_is_the_design_and_is_scoped_by_key_name` (tests/test_config.py 662-690, `FAMILY_OWNERS` 638) scans every pydantic model in config.py. Only `ConstantAccelConfig` may have an assist-family field name, and only `IgnitionConfig` an ignition-family one. The new model (and any structure-file model placed in config.py) must therefore avoid these names: `net_accel_g`, `exit_speed_mps`, `t_ign_s`, `reference`, `at_depth_m`, `at_speed_mps`, `at_height_m`, `height_method`. A target-speed release needs another name, such as `release_speed_mps`.
- **Merging.** A variant that switches the assist `model` replaces the whole assist dict (2175-2177; `_set_path` 2284-2286), so no constant_accel key survives into a linear_motor block.
- **What can move a resolved dict.** Only three things can (inferred from section 2 and the measurement):
  - an edit to a shipped YAML file;
  - a new `SWITCH_KEYS` or `EXCLUSIVE_KEY_FAMILIES` entry over key names the shipped files use (`stroke_m`, `carriage_mass_t`, `brake_decel_g`, `drive_efficiency`, `exhaust_impingement_fraction`, `shaft`, `allow_negative_drive_force`, `track`, `angle_deg`, `exit_altitude_m`; s1 output);
  - a change to the code that builds vehicle dicts (`offload_overrides` 2671-2709, `_restated_quantity` 2652-2668).

  New fields on a new model are none of these.
- **Where the run path reads the assist config.** It reads it only through `build_assist` (assist/__init__.py 36-55; called at sim.py 861, 892, 1064 and search.py 559), plus two places outside it:
  - `RunConfig._ignition_rules`: its depth-against-stroke check runs only for `isinstance(self.assist, ConstantAccelConfig)` (config.py 1433-1438).
  - Ramp starts by depth, speed or height: the preflight refuses them for any drive other than `constant_accel` (phases/prelude.py 282-286). Validation only refuses `model == "none"` (1427-1431), although the docstring at 781-782 says "constant_accel only".
- **Units.**
  - `units.kn_to_n` exists (units.py 44). No MW or kW conversion exists, and units.py 1-10 says nothing else may multiply by 1e6.
  - `compare.SI_SUFFIX_CONVERSIONS` (compare.py 85-101) knows `kN`, `t`, `g`, `s`, `m`, `W` and `mps`, but not `MW`. A key with an unknown suffix is treated as dimensionless in the sensitivity table.
- **`ENERGY_ONLY_ASSIST_KEYS`** lists only `constant_accel: (drive_efficiency,)` (1744-1749). test_planar_pipeline.py 997 pins linear_motor's efficiency as trajectory-relevant. That pin is right if the power limit is electrical and wrong if it is stated at the carriage.
- **The app's error-location tags.** If `PLANNED_MODELS` becomes `("cable_winch",)`, `ASSIST_UNION_TAGS` (appform.py 187) loses `"linear_motor"`, so `_clean_loc` stops stripping that tag. The phase file's "follows automatically" (section 2, item 5) is therefore misleading. Nothing breaks from the form today, since the form builds `constant_accel` only (inferred).

### Recommended model (to confirm in Plan mode)

Every number field gets `strict=True` and `allow_inf_nan=False`.

| YAML key | SI property | Bound | Note |
|---|---|---|---|
| `model: linear_motor` | | | discriminator |
| `stroke_m` | m | > 0 | not a family key, so it can share the name |
| `force_max_kN` | `force_max_N` (`units.kn_to_n`) | > 0 | |
| `power_max_MW` or `power_max_W` | `power_max_W` | > 0 | `_MW` needs a new `units.mw_to_w` and an `"MW"` suffix row in compare; `_W` needs neither. State whether the limit is at the carriage or at the supply: that decides `ENERGY_ONLY_ASSIST_KEYS` and test_planar_pipeline.py 997 |
| `force_rise_time_s` | s | >= 0 | 0 is a step (infinite jerk); input to the dynamic load factor |
| `carriage_mass_t` | `carriage_mass_kg` | >= 0 | |
| `brake_decel_g` | `brake_decel_mps2` | > 0 | until braking is modelled |
| `drive_efficiency` | | (0, 1] | |
| `exhaust_impingement_fraction` | | [0, 1] | |
| `release_speed_mps` (optional) | m/s | > 0, or absent | needs its own event (only `ev_track_end`, phases/engine.py 674); leave it out of the dump when None |
| `shaft` | | `Literal["vented"]` | `"sealed"` later, with its own block |
| `track` | `TrackConfig` | | |

Further recommendations:
- Put checks that need the vehicle, such as F_max > M g_eff at push start or v_inf = P/(M g_eff) above the release speed, in `resolve_run` or in the preflight (inferred: the payload varies during the search).
- Generalize the depth-bound check at 1433-1438 to any track drive.
- Build `ASSIST_UNION_TAGS` from one config tuple that lists every union tag.
- New union: `NoAssistConfig | ConstantAccelConfig | LinearMotorConfig | PlannedAssistConfig`, with `PlannedModel = Literal["cable_winch"]`.
- Tests that change: tests/test_config.py 218-220 (the pin at 220) and 283-289 (drop `linear_motor` from the parametrization).

## 4. KI-030: reproduction and the validators that close it

### 4.1 Reproduced at HEAD (fact)

Probe base: silo_offload_2d without sweeps and sensitivity. Each value was read back from the validated model.

| # | Input | HEAD | Patched (strict and finite per field) |
|---|---|---|---|
| 1 | `stroke_m: true` | accepted as 1.0 | refused (`float_type`) |
| 2 | `stroke_m: "100"` | accepted as 100.0 | refused (`float_type`) |
| 3 | `fixed.stage1_fraction: "0.05"` | accepted | refused (`float_type`) |
| 4 | `paired_pad: "yes"` | accepted as True | refused (`bool_type`) |
| 5 | `stroke_m: inf` (with `net_accel_g`) | accepted | refused (`finite_number`) |
| 6-8 | `net_accel_g`, `brake_decel_g`, `carriage_mass_t` set to inf | accepted | refused (`finite_number`) |
| 9-10 | `t_ign_s` NaN or inf | accepted | refused |
| 11-12 | `t_ign_s` 1e9 or -1e9 | accepted | **still accepted** (needs a range bound) |
| 13 | `track.exit_altitude_m: NaN` | accepted | refused |
| 14-15 | `exit_altitude_m` -1000 or 5000 | accepted | **still accepted** (needs a range bound) |
| 16 | `startup.t_ramp_s: inf` | accepted | refused |

The 8 controls stay refused under the patch: `exit_speed_mps` inf, `stroke_m` NaN, `net_accel_g` NaN, `t_ramp_s` NaN, `at_depth_m` inf, `stage1_dry_mass_added_t` inf, `fixed.stage1_t` inf, and `stroke_m: "abc"`. Two error types change: a bad string goes from `float_parsing` to `float_type`, and NaN on a bounded field goes from `greater_than` to `finite_number`.

### 4.2 Further holes of the same kind (measured)

Accepted at HEAD and refused by the patch:
- **Assist block:** `net_accel_g` true or "3"; `exit_speed_mps` true or "76.7"; `brake_decel_g` true; `carriage_mass_t` true; `drive_efficiency` true or "0.5"; `exhaust_impingement_fraction` true; `allow_negative_drive_force` "yes" or 1; `track.angle_deg` "90"; `exit_altitude_m` true or inf.
- **Ignition:** `t_ign_s` true or "0.5"; `at_depth_m` true; `at_speed_mps` "30"; `fails` "no" or 0; `t_ramp_s` true; `tau_s` inf.
- **Offload block:** `stage1_dry_mass_added_t` true or "2"; `stage2_offload_t` true; `fixed.stage1_t` true or "5"; `pad_control` "yes".

Accepted at HEAD and outside the patch:
- `stage1_dry_mass_added_t: 1000` (no upper bound).
- The baseline's `integrator.t_max_s` and `sample_dt_s` set to inf (`gt=0` only, 895-902).
- `site.include_rotation: "yes"` and `site.latitude_deg: "28.5"`.
- `Quantity.assumed: "yes"` (a lax bool, 248). The Quantity value itself already refuses bool and str (251-262).

### 4.3 Validator forms (recommendation; this is the measured patch, `s3_make_patched.py` list `KI030`)

- **`ConstantAccelConfig`:**
  - `strict=True, allow_inf_nan=False` on `net_accel_g` 639, `stroke_m` 641, `carriage_mass_t` 642 and `brake_decel_g` 643;
  - `strict=True` on `exit_speed_mps` 640, `drive_efficiency` 644 and `exhaust_impingement_fraction` 645;
  - `allow_negative_drive_force: bool = Field(default=False, strict=True)` (647).
- **`TrackConfig`:** `angle_deg` and `exit_altitude_m` become `Field(default=..., strict=True, allow_inf_nan=False)` (593-594).
- **`StartupOverride`:** `t_ramp_s` and `tau_s` get strict and finite (735-736).
- **`IgnitionConfig`:**
  - `t_ign_s` becomes `Field(default=0.0, strict=True, allow_inf_nan=False)` (795);
  - `at_*` get strict (797-799);
  - `fails` becomes a strict bool (802).
- **`OffloadFixedConfig`:** strict and finite on all five keys (1574-1578).
- **`OffloadCaseConfig`:** strict on `stage2_offload_t` and `stage1_dry_mass_added_t` (1641-1642), and a strict bool for `paired_pad` (1643).
- **`OffloadConfig`:** a strict bool for `pad_control` (1732).
- **Shorter spelling (not measured):** an alias beside `FiniteFloat` (270), `StrictFinite = Annotated[float, Field(strict=True, allow_inf_nan=False)]`, plus pydantic's `StrictBool`.

**Range cases (a policy for Plan mode):**
- **`t_ign_s`:** shipped values are stage 1 in {-2.0, 0, 0.5, 1.0} and stage 2 = 0.0.
- **`exit_altitude_m`:** shipped value is only 0.
  - A `ge=0` bound would refuse the -30 m mouth that tests/test_failed_ignition.py 322-330 runs below config, which that test itself describes as "not a consistent 1-D geometry".
  - metrics.py 637-638 documents the mouth-below-ground case.
- **A bound like |t_ign_s| <= `t_max_s`** needs a `RunConfig`-level validator, and `t_max_s` itself accepts inf.

### 4.4 Effect on shipped files and pins (measured)

- **Digests.** Under `patched_ki030` all 7 shipped files load through `cli.load_experiment`, with digests identical to HEAD for all 214 dicts. Per file: calibration_f9_2d 16, guidance_trigger_2d 10, silo_bridge_2d_readme 4, silo_offload_2d 70, silo_offload_2d_readme 4, silo_screening_1d 50, silo_screening_2d 60. The 4 pinned files report no problems, and `budget_id` (`a17a0160...`) is unchanged.
- **Tests:**
  - test_config.py plus test_config_planar.py: 250 passed, 1 failed. The 1-D golden test (269) and the digest pin (323) pass.
  - The failing case is tests/test_config.py 389-392, `{"exit_speed_mps": 76.71, "stroke_m": math.inf}`. It expects the derived-acceleration message, but the field-level `finite_number` error now fires first, so the case must expect "finite number". The docstring phrase "or an infinite stroke" (config.py 653-654) becomes unreachable.
  - test_appform.py: 23 passed.
- **YAML integers that must keep validating.** Strict float accepts `int` (stored as 100.0) and refuses `bool` and `str` (measured). The shipped files use integers for:
  - **assist:** `stroke_m` (25, 50, 100, 200, 300), `net_accel_g` (1, 3, 5), `brake_decel_g` (5), `carriage_mass_t` (0, 22), `angle_deg` (90), `exit_altitude_m` (0);
  - **ignition:** `at_depth_m` (0, 25, 50, 75, 100), `at_height_m` (10, 40, 100, 200), `t_ign_s` (0), `t_ramp_s` (1, 2, 3), `tau_s` (1, 2, 3);
  - **offload:** `stage2_offload_t` (2), `stage1_dry_mass_added_t` (2, 4).
- **YAML strings.** `stroke_m: 1e3` (an unsigned exponent) is a string to PyYAML: lax mode coerces it today, strict mode refuses it. No KI-030 field in a shipped file holds such a string. The only numeric strings anywhere are `search.penalty.base_kg`, `search.penalty.per_deg_kg` and `search.ltg.r_scale_m` in all six planar files.
- **Model-wide strictness.** With `strict=True` on `_Model`, all six planar files are refused with 20 errors each. Tuple fields given as YAML lists (`search.gamma_grid_deg`, `checks.bp_ratio_bounds`, and others) fail, as do the three strings. silo_screening_1d passes. Strictness must therefore be set per field, never on `_Model` or on the shared blocks.

## 5. The offload block, and where a structural switch could live

### 5.1 Facts

- **`OffloadCaseConfig`** (1624-1678) has the fields `name`, `of`, `solve`, `fixed`, `stage2_offload_t`, `stage1_dry_mass_added_t` and `paired_pad` (1637-1643). Its rules (1645-1665): exactly one of `solve` and `fixed`; `stage2_offload_t` only on a stage-1 case; `paired_pad` refused together with a penalty.
- **`OffloadFixedConfig`** (1564-1621): exactly one key, > 0, fractions < 1.
- **`ResolvedOffloadCase`** (2424-2445).
- **`offload_overrides`** (2671-2709) restates masses as `{value, assumed: true, note}` (`_restated_quantity` 2652-2668). The penalty note (2702-2705) sits in the start's vehicle dict, so it enters `trajectory_key` and `offload_runs`. tests/test_offload_pipeline.py 232 pins it.
- **`offload_case_start`** (2721-2744).
- **`offload_solved_run`** (2747-2756) passes `dry_added_kg=0.0` at 2756.
- **`resolve_experiment`** builds every start, paired pad, arm and sweep-point case (2781-2826, 2874-2879).
- **The solve factory.** `sim.offload_problem_factory` (sim.py 1708-1714) builds `offload.planar_problem_factory` (offload.py 256-265, which is `dataclasses.replace(ctx, vehicle=...)`). `OffloadProblem.vehicle_at` (195-203) applies `with_offload`. vehicle.py has `with_payload` 585, `with_stage_propellant` 600 and `with_offload` 653, but no dry-mass helper.
- **Two traps.**
  - The solve memo key is `(trajectory_key(start), P_ref, mode)` (results_io.py 1168-1180, key at 1174). A structural case whose start equals the headline's would reuse the headline's solve. *Inferred consequence.*
  - The verification flies `offload_solved_run(case.start, ...)` (results_io.py 1339; `_verified` 1183-1194). Unless that function restates the dry mass at dm(x*), the verification search and the recorded `offload_runs` vehicle would lack the structure. *Inferred consequence.*
- **The payload form (s7, measured).** No current construct works:
  - A variant may not hold `vehicle.stages...` keys or a `vehicle` block (`RunConfig` `extra_forbidden`; its fields are listed at 1325-1332).
  - A bound on `vehicle.stages.stage1.dry_mass_t` resolves, but it also re-runs the pad at 30.3 t (`pad__dry`; `paired_baseline: Literal[True]`, 1497), which breaks D-SP1-03.
  - Offload cases need `solve` or a `fixed` offload > 0; both `stage1_t: 0` and a penalty-only case are refused.
- **The payload search.** `SearchContext.vehicle` is fixed, and each evaluation flies `with_payload(self.vehicle, payload_kg)` (search.py 511-603, planner 589-603).

### 5.2 Where the switch could live

| Option | Changes shipped resolved dicts? | Needs | Notes |
|---|---|---|---|
| (a) Field on the offload case, e.g. `structure: {set: central, sizing: flown}` | No. With a default of None the raw dicts are unchanged. tests/test_config_planar.py 1350 compares two case dumps, which stay equal (inferred) | The structure must enter the solve and its memo key (1174). `offload_solved_run` must restate dm(x*). Refuse it with `stage1_dry_mass_added_t` and with `paired_pad` (the reasoning of 1659-1664) | Sweep-point cases (2874-2879) and sensitivity arms inherit it, which suits the stroke series of section 5.8, item 2 |
| (a2) The same field on a case with neither `solve` nor `fixed`: the variant flies at its own payload capacity P* with dm | No (inferred) | Relax `_one_way` (1649-1653); a new `quoted_basis` and record kind (results_io.py 1445-1492). `xv_dry_mass_delta_kg` already exists (compare.py 1534) | Reuses the offload machinery for RQ3's payload form; KI-039 applies to it |
| (b) An experiment-level `structure:` block | No, if it is optional and not injected. As a shared block it would break test_config_planar.py 167-179 (`raw[name][k]` for every key in `SHARED_KEYS`) and `appform.make_basis` | Must name the runs and cases it applies to | Like `offload`, it is not a run setting (physics.md 5561-5564) |
| (c) A variant-level `RunConfig` field | No. `RunConfig.model_dump` gains a key and the round trips still hold (inferred) | dm at resolve time, with the variant's vehicle dict restated, or dm(P) computed inside the search | Gives the payload form and linear-motor variants directly. A variant flying a different vehicle from the pad, outside the offload block, is unchecked here (inferred risk) |
| (d) `configs/structures/<file>.yaml`, chosen by vehicle name | No (not read unless switched on) | A loader and a model (section 6) | Holds the coefficients and the low/central/high sets. Still needs (a), (a2), (b) or (c) as the switch |

**Recommendation.**
- Use (a) for the offload solve and (a2) for the payload form, with (d) holding the coefficients.
- Size dm at a stated payload (P_ref) and report its sensitivity to the payload. A dm that is self-consistent with the payload P would need a per-evaluation vehicle hook in `SearchContext.planner`, analogous to `OffloadProblem.vehicle_at`, and a check that the residual stays monotonic in P (inferred).
- Never put a structural field in `SearchConfig`, because `budget_id` is computed from its dump.

## 6. Loading files, and a structure file with the vehicle files' provenance rule

### Facts

- **config.py does no file I/O** (docstring 3-6). A calibration case's vehicle file arrives through a `VehicleLoader` (2504-2506), and is refused without one (2639-2643).
- **The CLI loads the files.** `cli.load_yaml` (267-284, UTF-8 `yaml.safe_load`) and `resolve_vehicle_path` (305-327, looks next to the experiment, then at the repo root) do the reading. `load_experiment` (330-352) passes the loader on at 347.
- **The app reads committed files by `git cat-file`** (`app.load_basis` 296, YAML at 288). It calls `resolve_experiment(exp, basis.vehicle_copy())` at app.py 600 and 4203, and appform.py 564, 575, 1002, 1279 and 1315. results_io and sim read no config files.
- **Provenance rule: `Quantity`** (241-267) and `_check_provenance` (233-238). Each number has exactly one of a non-blank `source` or `assumed: true`, plus an optional `note`. The value must be finite and not a bool or string. There is no sign bound: `{value: -5.0, assumed: true}` validates (measured). `QuantityList` (273-306) does the same for tables, and the physical checks live in the dataclass the model builds (`VehicleConfig._checks` 489-502).
- **Display-file precedent.**
  - Models in the pure display.py: `_DisplayModel` (153-187) reuses `config.Quantity`; `VehicleDisplayConfig` (244-282) holds `name` and `applies_to: list[str]` of vehicle names, non-empty and without repeats.
  - Loader in scene.py: `load_display_configs` (364-379), reading through `run_data.read_yaml`.
  - Folder from `cli.scene_display_dir` (567-580) and `DEFAULT_DISPLAY_DIR` (scene.py 141).
  - Selection: `vehicle_name in cfg.applies_to` (scene.py 397-402).
- **Vehicle names.** The gate vehicle is `generic_f9_class_2d`; the bridge vehicle is `generic_f9_class_2d_readme_loads`.

### Recommendation

- Define the `StructureConfig` model in config.py, as CLAUDE.md's layout puts the YAML models there.
  - Make every number a `Quantity` and every table a `QuantityList`.
  - Give it `name`, `applies_to` and the low/central/high coefficient sets.
  - Its validator builds the frozen dataclass that structure.py uses, as `VehicleConfig` does.
  - Keep its field names clear of the family keys.
- Read the file in `cli.load_experiment`, either from a path given in the switch or by matching `applies_to` over `configs/structures/*.yaml`. Pass it to `resolve_experiment` as a keyword-only `load_structure` (the `VehicleLoader` pattern), so the seven app call sites stay unchanged.
- Record the file in resolved_config.yaml under a new top-level key, written only when a structure is used. The output capture compares that file's top-level keys for the fast experiment (planar_pin_support docstring 25-27).

## 7. How a new experiment file is classified, and what the pins cover (facts)

- **`PLANAR_EXPERIMENTS`** (tests/test_config_planar.py 62-69) must equal the set of experiments/*.yaml files with `dynamics: planar_2d` (880-890). A new planar file must therefore be added there, and it then has to pass:
  - 167-179: its six `SHARED_KEYS` blocks must be raw-equal to calibration_f9_2d's and give one `budget_id`. Copy them verbatim, keeping the `1.0e6` strings as written.
  - 893-915: `planar_max_step_s` must be written out as 2.0.
  - The m2_role test at 1053.
  - tests/test_results_io.py 896-908, which covers every experiments/*.yaml: every run must pass the preflight, and `sim.every_resolved_run` must list the runs in the same order as `planar_pin_support.resolved_runs`.
- **The digest pin** (323-344) covers only the 4 files in `PINNED_EXPERIMENTS` (planar_pin_support.py 86-91).
  - It hashes the sha256 of `json.dumps` of every `run_dict` and `vehicle_dict`, key order kept, under each label of `resolved_runs` (132-183).
  - The number of labels must equal `_declared_run_count` (306-317), and the order is checked (`compare_digests` 213-230).
  - The reference commit is c587a08, and the pin is never recaptured.
- **The offload experiments are not pinned.** They are guarded instead by `test_offload_experiments_fly_the_screened_runs` (1142-1154: the run and vehicle dicts of their shared runs equal silo_screening_2d's or the bridge's) and by the 1-D golden test (262-290).
- **SP7 must not edit shipped files.** This is phase file section 5.10, and `app.sp1_files_same` (app.py 2628-2657) diffs silo_offload_2d.yaml and its vehicle file against SP1's commit.

## 8. Schema documentation and the label rule

**Facts.**
- "Experiment schema (planar)" is docs/physics.md 5412-5784:
  - shared blocks 5439-5445;
  - labels 5528-5539;
  - offload keys 5561-5601;
  - merge rule and families 5603-5699, with the assist group at 5657-5669 and the dump note at 5688-5692;
  - pins 5701-5749, with counts 16, 60, 4 and 10 that match my measurement;
  - shipped-file table 5757-5770;
  - re-resolving from raw dicts, never from a dump: 5782-5784.
- **The `exploratory` label** (config.py 157-164; validator 1986-1992) requires planar_2d and no sweeps, and allows no `cases`. Its reservation for the app is a decision (D-SP2-12), not something the code enforces.
- **The assist keys are documented** in "Silo model" (4591-4630; linear_motor is named at 4623), not in the schema section.

**Recommendation.**
- Give SP7's experiment file no label, like silo_offload_2d.
- In the same change, add a `linear_motor` key table and the structural switch to the schema section.
- Extend 5657-5669 to say that the linear motor's keys belong to no family.

## 9. Phase-file statements that HEAD contradicts or refines

1. **Section 5.10 and R4: "a default added to `ConstantAccelConfig` would change every resolved dict and break the digest pin."** Measured: it changes no resolved dict and no digest. It breaks the dump-key pin at tests/test_config.py 432-443. Inside `SearchConfig` it would move `budget_id`. The advice to put new fields on new models still holds.
2. **Section 2, item 5: "`ASSIST_UNION_TAGS` follows automatically."** It follows by dropping `linear_motor` from the stripped tags (section 3).
3. **Section 2, item 9: KI-030's validators "change no resolved dict."** True, as measured, but only if strictness is per field. One test case changes (tests/test_config.py 389). The ±1e9 `t_ign_s` and the -1000/5000 `exit_altitude_m` cases need range bounds, which are a policy choice.
4. **The phase file's line references hold at 22c62e9**, with two small offsets: `_dump_one_push_key`'s decorator is at 678 and `ResolvedOffloadCase`'s at 2424.

## 10. Questions for Plan mode

1. What range bounds for `t_ign_s` and `exit_altitude_m`, and should `stage1_dry_mass_added_t` get an upper bound?
2. Is the linear motor's power limit at the carriage or at the supply? Is it written in MW (new units and compare entries) or W?
3. Which construct carries the payload form, (a2) or (c)? Is dm sized at P_ref, or made self-consistent with the payload?
4. Is the structure file chosen by a path in the switch or by `applies_to`?
5. How does a structural case enter the solve memo key (results_io.py 1174) and the recorded vehicle dict at x* (config.py 2756)?
6. Should KI-030 also cover the integrator's `t_max_s` and `sample_dt_s` (inf is accepted), and the bools in the shared blocks? Strict floats in the shared blocks are ruled out by the YAML strings and the tuple fields.
