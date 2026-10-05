Provenance: SP2 step A0 survey 03 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session scratchpad (a0/03-config-and-form.md); a record, not edited (README.md).

# 03 - Config and form: the mapping from an app form to an experiment dict

Survey for SP2 step A0. Repository at HEAD b69ff0c, clean tree. Read-only: nothing in the
repository was changed, no simulation was run, pytest was not run. Everything below was
checked by calling only `config.resolve_experiment`, `sim.check_result_names`,
`sim.check_resolved` and `sim.run_ignition_specs` on in-memory dicts (about 200 dicts).

Scratch scripts and their outputs (same folder as this report):

| Script | Output | What it does |
|---|---|---|
| `s03_structure.py` | (console) | structure of the committed file, shared-block digests, model fields |
| `s03_refusals.py` | `s03_refusals_out.txt`, `s03_refusals_out.json` | 155 edited dicts: where each is refused, class and message |
| `s03_accept.py` | `s03_accept_out.txt` | the five minimal dicts, the presets, the five ramp-start ways, pad-only, README fork, holes |
| `s03_extra.py` | `s03_extra_out.txt` | sensitivity arms, several cases, cleaned messages, timing |
| `s03_literals.py` | `s03_literals_out.txt` | the minimal dict as a Python literal, verified by `ast.literal_eval` |
| `s03_recorded.py` | `s03_recorded_out.txt` | SP1's recorded numbers a preset can be checked against |

Line numbers are for `src/launchsim/config.py` unless a file is named.

---

## 1. `experiments/silo_offload_2d.yaml`: structure

Top-level keys, in file order (YAML line): `name` (20), `vehicle` (21), `dynamics` (22),
`site` (23), `target_orbit` (24), `guidance` (25-28), `search` (29-54), `checks` (55-72),
`baseline` (73-78), `variants` (85-113), `sweeps` (119-164), `sensitivity` (169-172),
`offload` (173-208). No `label`, no `bounds`, no `cases`.

The file has **no YAML anchor and no merge key** (grep for `&name`, `*name`, `<<:` finds
them only in `silo_screening_1d.yaml`, `silo_screening_2d.yaml` and
`silo_bridge_2d_readme.yaml`). Every variant writes its assist block in full, on purpose
(file comment, lines 82-84: a merge would carry `net_accel_g` into the exit-speed variant).

```text
name: silo_offload_2d
vehicle: configs/vehicles/generic_f9_class_2d.yaml
dynamics: planar_2d
site: {latitude_deg: 28.5, azimuth_deg: 90, include_rotation: true}
target_orbit: {kind: circular, altitude_km: 200}
guidance: {kick: {v_kick_mps: 50, mode: hold_to_alignment, max_duration_s: 60, deadline_s: 60},
           stage1: gravity_turn,
           stage2: {law: linear_tangent, frame: local_horizontal, cutoff: energy}}
search:   21 keys: figure_of_merit payload, gamma_grid_deg [8, 36, 2], ..., penalty {...}, ltg {16 keys}
checks:   16 keys: closure_tol_mps 1e-5, ..., convergence {6 keys}, gamma_sensitivity_step_deg 0.5, m2_role diagnostic
baseline: {name: pad, assist: {model: none},
           ignition: {stage1: {t_ign_s: -2.0, reference: release}, stage2: {t_ign_s: 0.0}},
           end: insertion,
           integrator: {method: DOP853, rtol: 1.0e-10, planar_max_step_s: 2.0, sample_dt_s: 0.05}}
variants:
  silo_cold:              (lines 88-92)
    assist: {model: constant_accel, net_accel_g: 3.0, stroke_m: 100, carriage_mass_t: 0,
             brake_decel_g: 5, drive_efficiency: 0.5, exhaust_impingement_fraction: 0.0,
             shaft: vented, track: {angle_deg: 90, exit_altitude_m: 0}}
    ignition: {stage1: {t_ign_s: 0.5, reference: release}}
  silo_hot_ramp_on_track: (lines 96-100) same assist; ignition: {stage1: {t_ign_s: -2.0, reference: release}}
  silo_cold_200m:         (lines 108-113)
    assist: {model: constant_accel, exit_speed_mps: 76.70717046013364, stroke_m: 200,
             carriage_mass_t: 0, brake_decel_g: 5, drive_efficiency: 0.5,
             exhaust_impingement_fraction: 0.0, shaft: vented, track: {angle_deg: 90, exit_altitude_m: 0}}
    ignition: {stage1: {t_ign_s: 0.5, reference: release}}
sweeps: 5 (5, 4, 5, 4 and 2 points), each with offload: [<a stage-1 case>]
sensitivity: {of: [], params: {vehicle.stages.stage1.dry_mass_t: 0.10,
              vehicle.stages.stage1.engine.isp_vac_s: 0.10, vehicle.aero.cd_scale: 0.10,
              assist.drive_efficiency: 0.10}}
offload:
  reference: pad                     (174)
  pad_control: true                  (175)
  sensitivity_of: [silo_cold_s1]     (176)  -> 8 arms
  cases:                             (177-203)
    - {name: silo_cold_s1, of: silo_cold, solve: stage1, paired_pad: true}          (181)
    - {name: silo_cold_s2, of: silo_cold, solve: stage2}                            (184)
    - {name: silo_cold_both, of: silo_cold, solve: both}                            (185)
    - {name: silo_cold_s1_s2pre2t, of: silo_cold, solve: stage1, stage2_offload_t: 2}   (188)
    - {name: silo_cold_s1_dry+2t, of: silo_cold, solve: stage1, stage1_dry_mass_added_t: 2}     (194)
    - {name: silo_cold_s1_dry+4t, of: silo_cold, solve: stage1, stage1_dry_mass_added_t: 4}     (195)
    - {name: silo_cold_s1_dry+8.1t, of: silo_cold, solve: stage1, stage1_dry_mass_added_t: 8.1} (196)
    - {name: silo_cold_fix5pct, of: silo_cold, fixed: {stage1_fraction: 0.05}}      (199)
    - {name: silo_cold_fix10pct, of: silo_cold, fixed: {stage1_fraction: 0.10}}     (200)
    - {name: silo_hot_ramp_s1, of: silo_hot_ramp_on_track, solve: stage1}           (202)
    - {name: silo_cold_200m_s1, of: silo_cold_200m, solve: stage1}                  (203)
  energy:                            (204-208)
    fuel_mass_t: {stage1: {value: 123.5, source: "..."}, stage2: {value: 32.3, source: "..."}}
    heating_value_MJ_per_kg: {value: 43.03, source: "MIL-DTL-25576E ..."}
```

Run names the committed block derives (`config.offload_run_names`): the 11 case names,
`silo_cold_s1__pad`, `pad__offload_stage1`, `pad__offload_stage2`, `pad__offload_both`.

### 1.1 What the loader really returns (a trap)

`cli.load_yaml` (cli.py 191-208) is `yaml.safe_load`. PyYAML reads a float written without a
sign in its exponent as a **string**. Three leaves of the shared blocks are therefore
strings in the raw dict:

| Path | Raw value |
|---|---|
| `search.penalty.base_kg` | `'1.0e6'` |
| `search.penalty.per_deg_kg` | `'1.0e4'` |
| `search.ltg.r_scale_m` | `'1.0e4'` |

pydantic coerces them (the models are not strict), so the resolved `SearchConfig` and its
`budget_id()` are right. But the raw dict is what `resolved_config.yaml` writes, what the
shared-block test compares and what `compare.trajectory_key` hashes. Measured: replacing
the three strings by floats keeps `RunConfig` and the budget id equal and changes the raw
run dict and the trajectory key. So the app must copy the blocks as loaded and never
re-type or re-serialise them.

### 1.2 Which blocks a form-built experiment copies verbatim

`config.SHARED_KEYS = ("dynamics", "site", "guidance", "search", "target_orbit", "checks")`
(162-166: `RUN_SHARED_KEYS` + `PLANAR_SHARED_KEYS`). Copy verbatim, from the committed file:

1. the six `SHARED_KEYS` blocks (the guidance parametrisation, the sweep grid and the
   optimizer budget are `guidance` and `search`; `checks` sets the verdict thresholds);
2. `baseline` whole (name `pad`, `assist`, both ignitions, `end: insertion`, `integrator`);
3. `vehicle` (the path string) together with the vehicle dict read from that path;
4. `offload.energy` (tied to this vehicle file: section 7);
5. `sensitivity` only if the app offers `offload.sensitivity_of` (it supplies the params).

Measured with the app-shaped dict (name `app`, the copies above, one variant):
the pad's raw run dict is byte-equal to the committed one (`json.dumps`, key order and name
included), the vehicle dict is equal, `compare.trajectory_key` is equal
(`a55d80ead000472f...`), `search.budget_id()` is equal
(`a17a01601d0f4ae0c48cac48342127d5597e056e769da83503d7364c7d65a7df`).

### 1.3 The test that pins the shared blocks

`tests/test_config_planar.py::test_shared_blocks_are_identical_across_the_planar_experiments`
(lines 167-179). Over `PLANAR_EXPERIMENTS` (62-69: `calibration_f9_2d`, `silo_screening_2d`,
`silo_bridge_2d_readme`, `guidance_trigger_2d`, `silo_offload_2d`, `silo_offload_2d_readme`)
it asserts: the raw `{k: raw[name][k] for k in SHARED_KEYS}` equal to `calibration_f9_2d`'s;
one distinct `baseline.run.planar` (the resolved `PlanarShared`); one distinct
`search.budget_id()`.

It does **not** assert the baseline or the integrator. Scratch digests: the six shared
blocks are identical in all six files (`b0ce7b2030d3b990`); the baseline block is identical
in five (`15a410ff380a4b80`) and differs in `calibration_f9_2d` (`sample_dt_s: 0.1`
against `0.05`; that difference is pinned by
`test_calibration_and_silo_baselines_differ_only_in_sample_dt`, 182-193). The model for an
app test is `test_offload_experiments_fly_the_screened_runs` (1142-1153): `json.dumps` of
the run dict and of the vehicle dict equal to the source experiment's.

---

## 2. Form field to dict keys

All form output goes into two places only: `variants[<name>]` (keys `assist` and
`ignition.stage1`) and `offload`. Types are the JSON types after `json.loads`.

### 2.1 Launch site and push: `variants[<name>].assist`

`AssistConfig` is a union discriminated by `model` (721-723). `model` is a `SWITCH_KEYS`
key: an assist dict whose `model` differs from the baseline's (`none`) **replaces the
baseline's assist dict whole** (`merge_run_dicts`, 2133-2164), so the variant's assist dict
must be complete.

| Key | Type and rule (line) | Model default | Committed silo |
|---|---|---|---|
| `model` | `"none"` or `"constant_accel"` (610, 633); `linear_motor`, `cable_winch` refused "planned for Phase 3" (718) | - | `constant_accel` |
| `stroke_m` | number > 0, **required** (636) | none | 100 (200 in `silo_cold_200m`) |
| `net_accel_g` | number > 0, in g0 (634) | absent | 3.0 |
| `exit_speed_mps` | number > 0, finite (635) | absent | 76.70717046013364 (`silo_cold_200m` only) |
| `carriage_mass_t` | number >= 0 (637) | 0.0 | 0 |
| `brake_decel_g` | number > 0, **required** (638) | none | 5 |
| `drive_efficiency` | number in (0, 1] (639) | **1.0** | **0.5** |
| `exhaust_impingement_fraction` | number in [0, 1] (640) | 0.0 | 0.0 |
| `shaft` | `"vented"` only (641) | `vented` | `vented` |
| `allow_negative_drive_force` | bool (642) | false | absent; not a form field |
| `track.angle_deg` | must equal 90 (588, 591-599) | 90.0 | 90 |
| `track.exit_altitude_m` | number, no bound (589) | 0.0 | 0 |

- Exactly one of `net_accel_g`, `exit_speed_mps` (`ASSIST_KEY_FAMILIES`, 88; validator
  645-671). A key present counts as given, an explicit `null` included. Send one key, never
  both, never a null.
- Two fields have no usable default: `brake_decel_g` is required, and `drive_efficiency`
  defaults to 1.0 where the committed silo uses 0.5 (measured: leaving it out resolves to
  1.0, which halves the electrical energy). The app writes all of them from its copy of the
  committed silo.
- A pad variant is `{"assist": {"model": "none"}}` and nothing else (section 8).

### 2.2 Ramp start: `variants[<name>].ignition.stage1`

`IgnitionConfig` fields (790-797): `t_ign_s: float = 0.0`, `reference: "release" |
"push_start" = "release"`, `at_depth_m` (>= 0, finite), `at_speed_mps` (>= 0, finite),
`at_height_m` (> 0, finite), `height_method: "event" | "closed_form"`, `startup`, `fails`.
At most one family of `IGNITION_KEY_FAMILIES` (91-96).

The variant gives `ignition: {"stage1": {...}}` only. The merge keeps the baseline's
`stage2: {t_ign_s: 0.0}` and, when the variant uses another family, removes the baseline's
`t_ign_s` and `reference` from `stage1` (measured below).

| Way | Dict sent | Resolved `IgnitionSpec` on the 3 g0, 100 m silo (measured) |
|---|---|---|
| time after release | `{"t_ign_s": 0.5, "reference": "release"}` | `t_ign_s=0.5, reference='release', trigger_kind='time'` |
| time from push start | `{"t_ign_s": 0.0, "reference": "push_start"}` | `t_ign_s=0.0, reference='push_start', trigger_kind='time'` |
| depth below the mouth | `{"at_depth_m": 50}` | `t_ign_s=1.8436523650785581, reference='push_start', trigger_kind='depth', trigger_value=50.0` |
| speed on the push | `{"at_speed_mps": 30}` | `t_ign_s=1.0197162129779282, reference='push_start', trigger_kind='speed', trigger_value=30.0` |
| height by event | `{"at_height_m": 40, "height_method": "event"}` | `t_ign_s=0.0, reference='release', trigger_kind='height_event', trigger_value=40.0` |
| height by closed form | `{"at_height_m": 40, "height_method": "closed_form"}` | `t_ign_s=0.5400405840992664, reference='release', trigger_kind='height_closed_form', trigger_value=40.0` |

Edges (measured): `at_depth_m` 100 (the floor) and 0 (the mouth, snaps to `0.0, release`)
are accepted; `at_speed_mps` 0 and exactly `sqrt(2*3*9.80665*100)` are accepted. In the
time family always send both keys: `{"t_ign_s": 0.5}` alone inherits `reference: release`
from the baseline (same resolved dict as the committed variant), but that relies on the
baseline.

Startup override, an extra key of the same dict: `"startup": {...}` with
`kind: "step" | "ramp" | "lag"` (729; `vehicle.StartupKind`, vehicle.py 38),
`t_ramp_s` (number >= 0, 730), `tau_s` (number >= 0, 731). The gate vehicle's stage 1 is
`kind: ramp, t_ramp_s: 2.0`; stage 2 is `step`. Rules (`StartupOverride.resolve`, 733-758,
called from `resolve_run` 2554-2557):

| Sent | Result (measured) |
|---|---|
| key absent | the vehicle's 2 s ramp |
| `{"t_ramp_s": 3.0}` | ramp 3 s (kind stays ramp) |
| `{"kind": "ramp", "t_ramp_s": 3.0}` | ramp 3 s |
| `{"kind": "lag", "tau_s": 1.0}` | lag, tau 1 s |
| `{"kind": "step"}` | step |
| `{"kind": "lag"}` | refused: `run 'silo', ignition stage1: startup override kind lag needs tau_s` |
| `{"kind": "ramp", "tau_s": 1.0}` or `{"tau_s": 1.0}` | refused: `... startup override gives tau_s but the kind is 'ramp'` |
| `{"kind": "step", "t_ramp_s": 2.0}` | refused: `... startup override gives t_ramp_s but the kind is 'step'` |

A startup override combines with any of the five ways (`{"at_depth_m": 50, "startup":
{"t_ramp_s": 1.0}}` resolves). `fails` is not a form field (it needs `end: impact`).

### 2.3 Propellant: `offload`

`OffloadConfig` (1709-1775), fields 1725-1729:

| Key | Type and rule |
|---|---|
| `reference` | string, must equal the baseline's name, `"pad"` (alias of `reference_run`, 1725; checked 2041-2045) |
| `cases` | list, at least 1 (1726) |
| `pad_control` | bool, default false (1727); required true by a `stage2` or `both` solve (1746-1752) |
| `sensitivity_of` | list of case names, default `[]` (1728); needs the experiment's `sensitivity` block (2054-2058); stage-1 solves and fixed cases only (1753-1758) |
| `energy` | `OffloadEnergyConfig` or absent (1729) |

One case, `OffloadCaseConfig` (1619-1673), fields 1632-1638:

| Key | Type and rule |
|---|---|
| `name` | string; becomes a results directory (section 4) |
| `of` | string; a variant, never the baseline (2046-2053) |
| `solve` | `"stage1"`, `"stage2"` or `"both"`; exactly one of `solve` and `fixed` (1644-1648) |
| `fixed` | dict with exactly one key (1575-1588): `stage1_t` (> 0, finite, t), `stage1_fraction` (0 < f < 1), `stage2_t`, `stage2_fraction`, `both_fraction` (1569-1573) |
| `stage2_offload_t` | number > 0, finite; only when the case's mode is `stage1` (1636, 1649-1653) |
| `stage1_dry_mass_added_t` | number > 0, finite (1637) |
| `paired_pad` | bool, default false (1638); refused with `stage1_dry_mass_added_t` (1654-1659) |

- A mass at or beyond the load is refused at resolve time (`offload_overrides`, 2674-2680):
  on the gate vehicle `stage1_t` < 410.9 and `stage2_t` < 107.5 (strict; 410.8 resolves).
- "0" is not a value: `stage1_dry_mass_added_t: 0` and `stage2_offload_t: 0` are refused
  (`Input should be greater than 0`). A penalty of 0 t and "no pre-offload" are the key
  left out.
- `pad_control: true` solves each distinct **solve** mode once on the pad
  (`pad_control_modes`, 1761-1768). With only fixed cases it does nothing (measured:
  `pad_control_modes == ()`).
- Accepted combinations (measured): `stage2_offload_t` on a fixed stage-1 case; `paired_pad`
  on a fixed case and on a stage-2 solve; a penalty on a fixed case and on a stage-2 solve;
  several cases in one block.
- `sensitivity_of` on one case adds 8 arms (4 params x 2 signs), each a further solve.
  Measured arm names are up to 63 characters; they are not directories.
- `energy` is optional for the schema; without it a case record has `energy: None`.

### 2.4 The minimal complete experiment dicts (Python literals)

`A1` is the whole dict. It was printed by `pprint` from the built dict and read back with
`ast.literal_eval`; that literal resolves, passes both checks, and its `pad` and
`silo_cold` run dicts are byte-equal to the committed experiment's. The three quoted
numbers in `search` are strings on purpose (section 1.1). In the app the shared blocks, the
baseline and the vehicle path are copies made at server start, never literals in code.

```python
A1 = {  # pad plus silo_cold, no offload
 'name': 'app',
 'vehicle': 'configs/vehicles/generic_f9_class_2d.yaml',
 'dynamics': 'planar_2d',
 'site': {'latitude_deg': 28.5, 'azimuth_deg': 90, 'include_rotation': True},
 'guidance': {'kick': {'v_kick_mps': 50, 'mode': 'hold_to_alignment',
                       'max_duration_s': 60, 'deadline_s': 60},
              'stage1': 'gravity_turn',
              'stage2': {'law': 'linear_tangent', 'frame': 'local_horizontal', 'cutoff': 'energy'}},
 'search': {'figure_of_merit': 'payload',
            'gamma_grid_deg': [8, 36, 2],
            'gamma_refine_halfwidth_deg': 4,
            'gamma_xatol_deg': 0.01,
            'gamma_refine_maxiter': 30,
            'gamma_root_tol_deg': 0.01,
            'delta_bracket_deg': [0.1, 45],
            'delta_step_deg': 0.25,
            'delta_xtol_rad': 1e-10,
            'payload_half_bracket_t': 2.0,
            'payload_max_expand': 6,
            'payload_backoff_max': 4,
            'payload_xtol_kg': 0.5,
            'brentq_rtol': 8.881784197001252e-16,
            'final_payload_xtol_kg': 0.05,
            'final_bracket_kg': [20, 1000],
            'search_rtol': 1e-08,
            'search_atol_scale': 10,
            'final_rtol': 1e-10,
            'penalty': {'base_kg': '1.0e6', 'per_deg_kg': '1.0e4'},
            'ltg': {'accept_r_m': 1.0, 'accept_vr_mps': 0.001, 'r_scale_m': '1.0e4',
                    'vr_scale_mps': 100, 'fd_step_search': 0.0001, 'fd_step_final': 1e-05,
                    'max_iters': 25, 'max_halvings': 6, 'grid_max_rungs': 2,
                    'p0_offset_deg': 5, 'pf_deg': -1, 'steep_p0_deg': 35,
                    'shallow_guess': [0.3, 0.3], 'pitch_bounds_deg': [-45, 75],
                    'tau_max_factor': 2.0, 'mass_floor_factor': 0.5}},
 'target_orbit': {'kind': 'circular', 'altitude_km': 200},
 'checks': {'closure_tol_mps': 1e-05,
            'identity_tol_mps': 1e-05,
            'insertion_e_max': 1e-06,
            'grav_ratio_bounds': [0.33, 3.0],
            'bp_ratio_bounds': [0.33, 3.0],
            'min_term_mps': 1.0,
            'max_drag_steer_share': 0.5,
            'anchor_margin_kg': 1.5,
            'search_final_flag_rel': 0.0001,
            'maxq_scan_points': 256,
            'maxq_xatol_s': 1e-06,
            'unconstrained_kick_mps': 120,
            'vk_margin_kg': 5,
            'convergence': {'rel_tol': 0.001, 'loss_floor_mps': 0.001, 'margin_floor_kg': 0.5,
                            'gamma_resolution_deg': 0.1, 'tighten_factor': 10,
                            'max_step_factor': 0.5},
            'gamma_sensitivity_step_deg': 0.5,
            'm2_role': 'diagnostic'},
 'baseline': {'name': 'pad',
              'assist': {'model': 'none'},
              'ignition': {'stage1': {'t_ign_s': -2.0, 'reference': 'release'},
                           'stage2': {'t_ign_s': 0.0}},
              'end': 'insertion',
              'integrator': {'method': 'DOP853', 'rtol': 1e-10,
                             'planar_max_step_s': 2.0, 'sample_dt_s': 0.05}},
 'variants': {'silo_cold': {
     'assist': {'model': 'constant_accel', 'net_accel_g': 3.0, 'stroke_m': 100,
                'carriage_mass_t': 0, 'brake_decel_g': 5, 'drive_efficiency': 0.5,
                'exhaust_impingement_fraction': 0.0, 'shaft': 'vented',
                'track': {'angle_deg': 90, 'exit_altitude_m': 0}},
     'ignition': {'stage1': {'t_ign_s': 0.5, 'reference': 'release'}}}},
}
```

The other four add one key. `ENERGY` is the committed `offload.energy` (YAML 204-208),
copied, never typed; the block also resolves without it.

```python
# A2: silo_cold with a solved stage-1 offload and the pad control
A2 = {**A1, 'offload': {
    'reference': 'pad', 'pad_control': True,
    'cases': [{'name': 'silo_cold_s1', 'of': 'silo_cold', 'solve': 'stage1'}],
    'energy': ENERGY}}
# runs written: pad, silo_cold, silo_cold_s1, pad__offload_stage1

# A3: a fixed 5 % stage-1 offload
A3 = {**A1, 'offload': {
    'reference': 'pad', 'pad_control': False,
    'cases': [{'name': 'silo_cold_fix5pct', 'of': 'silo_cold',
               'fixed': {'stage1_fraction': 0.05}}],
    'energy': ENERGY}}
# runs written: pad, silo_cold, silo_cold_fix5pct   (imposed 20,545.0 kg)

# A4: a stage-2 solve (pad_control must be True)
A4 = {**A1, 'offload': {
    'reference': 'pad', 'pad_control': True,
    'cases': [{'name': 'silo_cold_s2', 'of': 'silo_cold', 'solve': 'stage2'}],
    'energy': ENERGY}}
# runs written: pad, silo_cold, silo_cold_s2, pad__offload_stage2

# A5: the +8.1 t penalty row (no paired pad allowed)
A5 = {**A1, 'offload': {
    'reference': 'pad', 'pad_control': False,
    'cases': [{'name': 'silo_cold_s1_dry+8.1t', 'of': 'silo_cold', 'solve': 'stage1',
               'stage1_dry_mass_added_t': 8.1}],
    'energy': ENERGY}}
# runs written: pad, silo_cold, silo_cold_s1_dry+8.1t   (stage-1 dry mass restated 30.3 t, assumed)
```

All five resolve and pass `check_result_names` and `check_resolved`. With the committed
case names each case's `start` run (run dict, vehicle dict, trajectory key) equals the
committed experiment's case of that name. The committed block runs every case under
`pad_control: true`; A3 and A5 above drop it to show the minimum.

---

## 3. Refusals

The order of the checks is the one `cli.load_experiment` uses (cli.py 270-275):
`resolve_experiment` (2816), then `sim.check_result_names`, then `sim.check_resolved`.
`check_result_names` is defined in results_io.py 234-256 and re-exported by sim
(sim.py 248, `__all__` 468). `check_resolved` is sim.py 932-945.

Every refusal recorded (131 of 155 dicts) is a `ValueError` subclass, so one
`except ValueError` catches all, as cli.py 274 does:

| Class | Defined | Raised by |
|---|---|---|
| `pydantic.ValidationError` | pydantic | `ExperimentConfig.model_validate` (2835; title `ExperimentConfig`: baseline, offload block, experiment-level rules) and `RunConfig.model_validate` in `resolve_run` (2523; title `RunConfig`: every variant) |
| `config.ExclusiveKeysError` | 2128 | `merge_run_dicts` (2143-2144, 2180-2183), prefixed `variant 'x': ` at 2842-2843 |
| plain `ValueError` | - | `offload_overrides` (2675), `resolve_run` (2557), `_check_offload_energy` (2755-2765), `sim.check_resolved` (sim.py 945, wrapping prelude.py) |
| `results_io.InvalidNameError` | results_io.py 201 | `check_name` (results_io.py 212-225) |

`str()` of a `ValidationError` is several lines with `[type=..., input_value=...,
input_type=...]` and a pydantic URL. The messages below are `exc.errors()[i]["msg"]` with
the prefix `Value error, ` removed, and `loc` joined by dots. For a variant the `loc` is
relative to the run, carries the union tag (`assist.constant_accel.stroke_m`) and does
**not** name the variant; a model-level rule of a run has an empty `loc`.

### 3.1 The list of phase file section 5.7 (real messages)

Base dict: `A1` with the variant named `silo`.

| # | Bad input | Refused in | Class | File:line of the rule | Message (measured) |
|---|---|---|---|---|---|
| 1 | `net_accel_g` and `exit_speed_mps` both given (also with one of them `null`) | resolve | `ExclusiveKeysError` | 2180-2183 (via 2143; prefix 2843) | `variant 'silo': override 'assist': keys ['net_accel_g', 'exit_speed_mps'] of two exclusive families are given together; state the setting one way only ({net_accel_g} or {exit_speed_mps})` |
| 1b | neither key | resolve | `ValidationError` (RunConfig), loc `assist.constant_accel` | 652-657 | `constant_accel needs exactly one of net_accel_g or exit_speed_mps beside stroke_m (given: neither; a key given as null counts as given)` |
| 1c | `net_accel_g: null` alone | resolve | `ValidationError`, loc `assist.constant_accel` | 658-662 | `constant_accel net_accel_g is null: the key that states the push must hold a number (a null does not unset a key)` |
| 2 | two ramp-start families (`t_ign_s` + `at_depth_m`; also `t_ign_s: null` + `at_depth_m`) | resolve | `ExclusiveKeysError` | 2180-2183 | `variant 'silo': override 'ignition.stage1': keys ['t_ign_s', 'at_depth_m'] of two exclusive families are given together; state the setting one way only ({t_ign_s, reference} or {at_depth_m} or {at_speed_mps} or {at_height_m, height_method})` |
| 2b | `at_height_m` without `height_method`, or the reverse | resolve | `ValidationError`, loc `ignition.stage1` | 819-823 | `ignition at_height_m and height_method come together: the height above the track exit and how it is reached (closed_form or event)` |
| 3 | `at_depth_m: 150` on a 100 m stroke | resolve | `ValidationError` (RunConfig), loc empty | 1427-1433 (`RunConfig._ignition_rules`); prelude.py 338-339 is a backstop never reached this way | `ignition stage1: at_depth_m 150 m is deeper than the track (stroke_m 100 m)` |
| 4 | `at_speed_mps: 80` (exit 76.707 m/s); also `v_e + 1e-6` | **check_resolved** | `ValueError` | phases/prelude.py 343-347 (label added sim.py 945) | `run 'silo': at_speed_mps 80 m/s exceeds the exit speed 76.7071705 m/s: the push never reaches it` |
| 5 | `at_height_m: 301.5`, `height_method: event` or `closed_form` | **check_resolved** | `ValueError` | phases/prelude.py 315-320 (`_drag_free_exit_speed`) | `run 'silo': at_height_m 301.5 m is at or above the drag-free apex v_e^2 / (2 g_eff) = 301.060928 m of the coast after release (v_e = 76.7071705 m/s, g_eff = 9.77209172 m/s^2)` |
| 6a | variant `assist: {model: none}` with `reference: push_start` | resolve | `ValidationError` (RunConfig), loc empty | 1412-1417 | `ignition stage1: reference push_start needs an assist model (a pad run has no push)` |
| 6b | variant `assist: {model: none}` with `at_depth_m` (or `at_speed_mps`, `at_height_m`) | resolve | `ValidationError` (RunConfig), loc empty | 1422-1426 | `ignition stage1: a ramp start by at_depth_m needs an assist model (a pad run has no push and no track exit)` |
| 6c | the same two on the baseline | resolve | `ValidationError` (ExperimentConfig), loc `baseline` | same lines | same texts |
| 7a | `fixed: {stage1_t: 410.9}` (the load) or 500; `stage2_t: 107.5` | resolve | `ValueError` | 2674-2680 (`offload_overrides`) | `offload case 'f': takes 410.9 t of propellant from stage 'stage1', which carries 410.9 t (an offload beyond the load; a stage keeps some propellant)` |
| 7b | `stage1_fraction` 0, 1, 1.2, 5; `stage2_fraction: -0.1`; `both_fraction: 1.0` | resolve | `ValidationError` (ExperimentConfig), loc `offload.cases.0.fixed.stage1_fraction` | 1570, 1572, 1573 | `Input should be greater than 0` / `Input should be less than 1` |
| 7c | `fixed` with two keys or none | resolve | `ValidationError`, loc `offload.cases.0.fixed` | 1579-1585 | `a fixed offload states exactly one of stage1_t, stage1_fraction, stage2_t, stage2_fraction, both_fraction (given: stage1_t, stage1_fraction)` (or `(given: none)`) |
| 7d | `solve` and `fixed` both, or neither | resolve | `ValidationError`, loc `offload.cases.0` | 1644-1648 | `offload case 'f': give exactly one of solve (a mode to solve) or fixed (an imposed offload)` |
| 7e | `stage2_offload_t: 107.5` before a stage-1 solve | resolve | `ValueError` | 2674-2680 | `offload case 'silo_s1': takes 107.5 t of propellant from stage 'stage2', which carries 107.5 t (...)` |
| 8 | `stage2_offload_t` on a `stage2` or `both` case (solved or fixed) | resolve | `ValidationError`, loc `offload.cases.0` | 1649-1653 | `offload case 'c': stage2_offload_t is taken before a stage-1 case only (this case's mode is stage2)` |
| 9 | `paired_pad: true` with `stage1_dry_mass_added_t` | resolve | `ValidationError`, loc `offload.cases.0` | 1654-1659 | `offload case 'silo_s1': paired_pad compares the case with the pad on one vehicle (the matched-payload attribution), but stage1_dry_mass_added_t is the assisted run's only; give the penalty row without paired_pad` |
| 10 | `solve: stage2` or `both` with `pad_control: false` | resolve | `ValidationError`, loc `offload` | 1746-1752 | `offload case 'c': a stage2 solve is quoted net of the pad control (stage-2 and both-stage offloads are a property of the vehicle model, D-SP1-10), so the block needs pad_control: true` |
| 11a | `stroke_m` missing (also `brake_decel_g`) | resolve | `ValidationError`, loc `assist.constant_accel.stroke_m`, type `missing` | 636, 638 | `Field required` |
| 11b | `stroke_m: "abc"` or `""` | resolve | `ValidationError`, type `float_parsing` | 636 | `Input should be a valid number, unable to parse string as a number` |
| 11c | `stroke_m: null`; `t_ign_s: null` | resolve | `ValidationError`, type `float_type` | 636, 790 | `Input should be a valid number` |
| 11d | `stroke_m` 0, -100 or NaN | resolve | `ValidationError`, type `greater_than` | 636 | `Input should be greater than 0` |
| 11e | `at_depth_m: null` | resolve | `ValidationError`, loc `ignition.stage1` | 813-818 | `ignition at_depth_m is null: a key that states the ramp start must hold a value (a null does not unset a key)` |
| 12a | experiment or run name with a space, `/`, a leading `_`, a trailing `.`, a non-ASCII letter, or empty | **check_result_names** | `InvalidNameError` | results_io.py 212-216 | `run name 'silo cold' is not a valid results directory name: use letters, digits, '_', '.', '+' or '-', starting with a letter or digit and not ending in '.'` (prefix `experiment name` or `offload run name` for those) |
| 12b | name of 65 characters | check_result_names | `InvalidNameError` | results_io.py 217-221 | `run name '...' is longer than 64 characters (65); results paths must stay short on Windows` |
| 12c | `CON`, `nul`, `COM1`, ... | check_result_names | `InvalidNameError` | results_io.py 222-223 | `run name 'nul' is a reserved Windows device name` |
| 12d | run named `plots`, `baseline`, `sweep_2`, `run_1` | check_result_names | `InvalidNameError` | results_io.py 224-225 | `run name 'run_1' is reserved by the results layout` |
| 12e | variant with the baseline's name | resolve | `ValidationError` (ExperimentConfig), loc empty | 1896-1897 | `variant 'pad' has the baseline's name` |
| 12f | a case named like a run, a variant or a derived name | resolve | `ValidationError`, loc empty | 2008-2012 | `run name 'silo' is used twice (runs, bounds, cases and offload runs)` |
| 12g | a 60-character case name with `paired_pad` | check_result_names | `InvalidNameError` | results_io.py 255-256, 217 | `offload run name 'ccc...c__pad' is longer than 64 characters (65); ...` |

Nothing was written: `results/` listing unchanged, `results/app` does not exist.

### 3.2 Further refusals a form can reach

| Bad input | Refused in | Message |
|---|---|---|
| offload case `of` the baseline | resolve, 2047-2051 | `offload case 'silo_s1': of 'pad' is the baseline; the baseline's own offload is the pad control (pad_control: true)` |
| offload case `of` an unknown variant (also: an offload block with no variants) | resolve, 2052-2053 | `offload case 'silo_s1': of 'silo_cold': no such variant` |
| `offload.reference` not the baseline | resolve, 2041-2045 | `offload reference 'silo' must be the baseline 'pad': the reference payload is the full-load pad's P*` |
| `offload.cases: []` | resolve, 1726 | `List should have at least 1 item after validation, not 0` |
| `sensitivity_of` without the `sensitivity` block | resolve, 2054-2058 | `offload sensitivity_of re-solves its cases under the experiment's sensitivity params: declare the sensitivity block` |
| `sensitivity_of` naming a stage-2 solve | resolve, 1753-1758 | `offload sensitivity_of 'silo_cold_s2': a stage2 solve is quoted net of the pad control, which an arm does not solve under its perturbation; name stage-1 solves and fixed cases` |
| energy given as bare numbers | resolve, `Quantity` | `bare value; vehicle files need {value, source} or {value, assumed: true}` |
| a variant sets `site` (or `guidance`, `search`, `target_orbit`, `checks`, `dynamics`, `planar`) | resolve, 1783-1791 via 1915-1917 | `variant 'silo' sets 'site': site is an experiment-level shared block, identical for every run (only a paired sweep of a guidance_study may vary guidance.*)` |
| a variant sets `integrator` | resolve, 1931-1946, 2083-2089 | `variant 'silo' sets integrator ['sample_dt_s']: on planar_2d no integrator setting may differ between runs (...)` |
| the baseline carries a shared block | resolve, 1794-1806 | `baseline sets 'guidance': guidance is an experiment-level shared block; declare it once at the top of the experiment file` |
| an unknown top-level key (`display`) or assist key (`depth_m`) | resolve, `extra="forbid"` (217) | `Extra inputs are not permitted` |
| `label: "exploratory"` | resolve, 157 | `Input should be 'calibration' or 'guidance_study'` |
| `track.angle_deg: 45` | resolve, 591-599 | `track angle_deg other than 90 is a Phase 3 feature (Phase 2 releases from vertical tracks only)` |
| `assist.model: "linear_motor"` | resolve, 716-718 | `assist model 'linear_motor' is planned for Phase 3` |
| `dynamics` left out | resolve | `include_rotation: true is a Phase 2 feature: it needs dynamics: planar_2d (vertical_1d keeps omega_p = 0)` (misleading; the cause is the missing key) |

### 3.3 Bad inputs that are NOT refused (holes)

The config models are not strict (`ConfigDict(extra="forbid", frozen=True)`, 217) and most
numeric fields do not set `allow_inf_nan=False`. All of these pass `resolve_experiment`,
`check_result_names` and `check_resolved` (measured):

| Input | What happens |
|---|---|
| `stroke_m: "100"` (a string) | accepted; the model holds 100.0, the raw run dict keeps `'100'` |
| `stroke_m: true` | accepted as **1.0 m** |
| `fixed.stage1_fraction: "0.05"` | accepted |
| `paired_pad: "yes"` | accepted as true |
| `stroke_m: inf` (with `net_accel_g`) | accepted |
| `net_accel_g: inf`, `brake_decel_g: inf`, `carriage_mass_t: inf` | accepted |
| `t_ign_s: NaN`, `inf`, `1e9`, `-1e9` | accepted (no bound on `t_ign_s`, 790) |
| `track.exit_altitude_m: NaN`, `-1000`, `5000` | accepted (no bound, 589) |
| `startup.t_ramp_s: inf` | accepted |
| `stage1_dry_mass_added_t: 1000` | accepted |
| `allow_negative_drive_force: true` | accepted (a real model switch) |

Python's `json.loads` reads `NaN` and `Infinity` by default, so these can arrive in a
request body. Refused as they should be: `exit_speed_mps: inf` (`Input should be a finite
number`), NaN where a `gt`/`ge`/`lt` bound exists (`stroke_m`, `net_accel_g`, the
fractions, `t_ramp_s`), non-finite `at_*` values and offload masses.

Not a refusal but a failed run, beside the `no_ignition` band the phase file names
(`at_height_m: 300.9` by event passes the preflight here): a hot start whose thrust
exceeds what the prescribed push needs ends the run with status `drive_limit`
(`ev_drive_limit`, phases/engine.py 688-704; assist/base.py 99-100). Hand estimate, not
run: with full thrust on the track (7,607 kN) and a stack near 572 t this is a net
acceleration below about 0.36 g0.

---

## 4. Names

```python
# results_io.py
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]*$")                    # 186
MAX_NAME_LEN = 64                                                              # 187
RESERVED_RUN_NAME_PATTERN = re.compile(r"^(plots|baseline|sweep_\d+|run_\d+)$")  # 188
WINDOWS_DEVICE_NAMES = frozenset({"CON", "PRN", "AUX", "NUL", COM1..COM9, LPT1..LPT9})  # 189-198
def check_name(name: str, what: str, reserved: re.Pattern[str] | None = None) -> str   # 205
def check_run_name(name: str) -> str        # 229: check_name(name, "run name", RESERVED_RUN_NAME_PATTERN)
def check_result_names(resolved: ResolvedExperiment) -> None                          # 234
# config.py
def paired_baseline_name(point_name: str, baseline: str) -> str   # 2097: f"{point_name}__{baseline}"
def pad_control_run_name(baseline: str, mode: str) -> str         # 2102: f"{baseline}__offload_{mode}"
def offload_run_names(block: OffloadConfig, baseline: str) -> list[str]   # 2107
PAD_CONTROL_PREFIX = "offload_"                                    # 1555
```

- `check_name` also refuses a trailing `.`; the first dotted part is compared with the
  device names case-insensitively.
- The experiment name is checked without the reserved pattern (an experiment named
  `baseline` is accepted). It is checked again by `make_run_dir` (results_io.py 365-382),
  which creates `<root>/<experiment>/<YYYYMMDDTHHMMSSZ>/`, with `-2`, `-3`, ... on a clash.
- Derived names: paired pad `<case>__<baseline>` (so `<case>__pad` only because the
  baseline is named `pad`); pad control `<baseline>__offload_<mode>`: `pad__offload_stage1`,
  `pad__offload_stage2`, `pad__offload_both`. Each is checked as `offload run name`
  (results_io.py 254-256). With the baseline `pad` a case with a paired pad may be at most
  59 characters.
- Uniqueness over the baseline, variants and every offload run name: `_bound_and_case_names`
  (1989-2013).
- Two run names carry meaning: `silo_instant` and `pad_instant` are the M5 anchor pair
  (compare.py 113, 871-874, 1041-1059). A variant named `silo_instant` resolves (measured)
  and would be read as an anchor. The app must not use or allow these names.

Recommended names for a launch:

| Item | Name | Why |
|---|---|---|
| experiment | `app` | gives `results/app/<UTC timestamp>/` (phase file Q3); passes `check_name` |
| baseline | `pad` (copied verbatim) | derived names and SP1's records use `pad`; replay reads `metrics.json` `baseline` |
| variant | the preset's own name when the form equals a preset (`silo_cold`, `silo_hot_ramp_on_track`, `silo_cold_200m`), else one fixed server-chosen name such as `silo` | with the committed names the resolved run dict is byte-equal to SP1's, name included |
| case | SP1's pattern, built by the server: `<variant>_s1`, `<variant>_s2`, `<variant>_both`, `<variant>_fix...`, `..._dry+<t>t` | all match `NAME_PATTERN` (`+` and `.` are allowed: `silo_cold_s1_dry+8.1t`); the name enters the restated vehicle note, so the same name gives the same vehicle dict as SP1 |

If the user never types a name, "an invalid name" can only come from an optional label
field; that field goes through `check_run_name` and the uniqueness rule above.

Replay roles (replay.py 93-97, `run_source` 244-319): the baseline and the variants are
`ROLE_RUN` (found in `metrics.json` `runs`); a case run, a paired pad and a pad control are
`ROLE_OFFLOAD` (found in `metrics.json` `offload.runs` and `resolved_config.yaml`
`offload_runs`). The default selection (`plots.animation_run_names`, plots.py 645-658) is
the baseline plus up to `ANIMATION_DEFAULT_VARIANTS = 3` variants; offload runs are never
in it and must be named.

`.gitignore` (lines 10-14) keeps `results/*/*/summary.md` visible to git, so
`results/app/<ts>/summary.md` would show as untracked (checked with `git check-ignore -v`).
That is question Q3 of the phase file, not a config matter.

---

## 5. What the form may not change, and how to guarantee it

Not changeable without leaving the shared basis: `dynamics`, `site`, `guidance`, `search`,
`target_orbit`, `checks` (the six `SHARED_KEYS`), the whole `baseline` (its `integrator`,
`end` and both ignitions included), the `vehicle` path and the vehicle dict, and
`offload.energy`.

What config.py already enforces: a variant may not set a shared block or `planar`
(1915-1917), nor `integrator` (1931-1946); the baseline may not carry a shared block
(1794-1806). What it cannot enforce: that the top-level blocks of an in-memory dict are
the committed ones, and that the vehicle dict passed to `resolve_experiment` is the file
the `vehicle` string names (measured: the gate experiment dict resolves against the
README-loads vehicle dict without complaint; `vehicle_name` in the results comes from the
dict's own `name`).

Structural guarantee, recommended:

1. At server start read one committed experiment file with `cli.load_yaml` and the vehicle
   file it names with `cli.resolve_vehicle_path` + `cli.load_yaml`. Keep a frozen basis:
   `shared = {k: exp[k] for k in config.SHARED_KEYS}`, `baseline = exp["baseline"]`,
   `vehicle_path = exp["vehicle"]`, `vehicle_dict`, `energy = exp["offload"]["energy"]`,
   `sensitivity = exp["sensitivity"]`, and the preset fragments
   (`exp["variants"][name]`, the committed cases). Raw, as loaded (section 1.1).
2. One pure builder, `build_experiment(basis, form) -> dict`, deep-copies the basis and adds
   only `variants` and `offload`. The request parser is a whitelist that can produce
   nothing but the keys of sections 2.1-2.3; the variant dict has the keys `assist` and
   `ignition` (with `stage1` only) and never `end`, `integrator`, `site`, `planar`.
3. Tests: for every preset, `json.dumps` of each resolved run dict and vehicle dict equals
   the committed experiment's run of that name (the pattern of
   `test_offload_experiments_fly_the_screened_runs`); `{k: built[k] for k in SHARED_KEYS}`
   equals the committed file's; `search.budget_id()` equal; and a request that carries
   `search`, `baseline`, `vehicle`, `site`, `integrator` or any unknown key is refused by
   the parser before `resolve_experiment` is called.

Cost of validation, measured: `resolve_experiment` 6.7 ms, `check_result_names` 0.02 ms,
`check_resolved` 2.0 ms for one variant with one case (160 ms for the whole committed
file). A validate-on-change endpoint is affordable.

Number types: `compare.trajectory_key` (compare.py 1768) hashes the **raw** run dict and
vehicle dict. Measured: `stroke_m: 100.0` against the committed `100`, or `net_accel_g: 3`
against `3.0`, gives an equal `RunConfig` and a different raw dict and trajectory key. A
browser sends `3.0` as `3`. So a preset that must reproduce SP1's resolved config is taken
from the server's copy of the committed fragment, not rebuilt from numbers that went
through the page; a custom launch is compared at the `RunConfig` level. The pad baseline
is copied verbatim, so its trajectory key is stable and usable as the cache key.

---

## 6. Presets (phase file section 10, Q4)

Every fragment is from `experiments/silo_offload_2d.yaml`. Each preset below resolves,
passes both checks and (variant and case `start`, paired-pad start included) equals the
committed experiment's run of the same name in raw run dict, vehicle dict and trajectory
key (measured). Recorded numbers are from
`results/silo_offload_2d/20261003T112934Z/metrics.json` (git b3150c1754ee, clean), the
gate fork, which calibrates +14.3% high; they are for checking a preset, not new findings.

Common silo values (all but 200 m): depth 100 m, net acceleration 3.0 g0 (exit 76.707 m/s,
push 2.607 s, braking 60 m, facility 160 m), carriage 0 t, brake 5 g0, drive efficiency
0.5, exhaust impingement 0.0, vented, vertical, exit altitude 0 m; startup: the vehicle's
2 s ramp (no override).

| Preset | Form values | Dict fragment | Recorded |
|---|---|---|---|
| pad alone | launch site: pad | no `variants`, no `offload` | pad P* 26,054.396 kg |
| `silo_cold` | silo; 100 m; 3.0 g0; ramp start: time, +0.5 s after release | `variants: {silo_cold: <YAML 88-92>}` | P* 27,553.227 kg (+1,498.831) |
| `silo_hot_ramp_on_track` | silo; 100 m; 3.0 g0; ramp start: time, -2.0 s, reference release | `variants: {silo_hot_ramp_on_track: <YAML 96-100>}`, ignition `{stage1: {t_ign_s: -2.0, reference: release}}` | P* 27,788.201 kg (+1,733.805) |
| `silo_cold_200m` | silo; 200 m; exit speed 76.70717046013364 m/s (net 1.5 g0 derived, push 5.215 s, facility 260 m); +0.5 s | `variants: {silo_cold_200m: <YAML 108-113>}`, assist with `exit_speed_mps` and no `net_accel_g` | P* 27,553.227 kg (+1,498.831) |
| `silo_cold_s1` | `silo_cold` + propellant: solve, mode stage 1, paired pad on, pad control on | `offload: {reference: pad, pad_control: true, cases: [{name: silo_cold_s1, of: silo_cold, solve: stage1, paired_pad: true}], energy}` (YAML 174-175, 181) | x* 41,262.908 kg = 10.042% of the stage-1 load, verified |
| fixed 5% | `silo_cold` + propellant: fixed, stage-1 fraction 0.05 | `cases: [{name: silo_cold_fix5pct, of: silo_cold, fixed: {stage1_fraction: 0.05}}]` (199) | x 20,545 kg; P* - P_ref +783.163 kg |
| fixed 10% | fraction 0.10 | `cases: [{name: silo_cold_fix10pct, of: silo_cold, fixed: {stage1_fraction: 0.10}}]` (200) | x 41,090 kg; P* - P_ref +6.800 kg |
| penalty 0 | `silo_cold` + solve stage 1, penalty field empty | `cases: [{name: silo_cold_s1, of: silo_cold, solve: stage1}]` (the key left out; 0 is refused) | as `silo_cold_s1` |
| penalty +2 t | penalty 2 | `{name: silo_cold_s1_dry+2t, of: silo_cold, solve: stage1, stage1_dry_mass_added_t: 2}` (194) | x* 32,285.203 kg (7.857%) |
| penalty +4 t | penalty 4 | `{name: silo_cold_s1_dry+4t, ..., stage1_dry_mass_added_t: 4}` (195) | x* 22,875.961 kg (5.567%) |
| penalty +8.1 t | penalty 8.1 | `{name: silo_cold_s1_dry+8.1t, ..., stage1_dry_mass_added_t: 8.1}` (196) | x* 1,980.477 kg (0.482%) |

Notes:

- The committed block runs every case under `pad_control: true` and gives only
  `silo_cold_s1` a paired pad and the 8 sensitivity arms (`sensitivity_of`, 176). A preset
  that leaves the arms out differs from SP1's run only by not computing them.
- A penalty row cannot have a paired pad (refusal 9). Switching a preset from penalty 0
  with a paired pad to +2 t must clear the paired pad.
- The exit speed of `silo_cold_200m` must stay the full double. The YAML comment (101-104)
  says the rounded 76.71 m/s releases 0.0028 m/s higher. A JSON round trip keeps the
  double; a text field that shows 76.70717 and is re-read does not.
- The stage-2 case of SP1 (`silo_cold_s2`) is recorded with `verification.passed = False`
  and four flags; the handoff says to expect that from an app launch.

---

## 7. The README-loads fork (Q5)

- Experiment file: `experiments/silo_offload_2d_readme.yaml` (`name:
  silo_offload_2d_readme`, line 16). Vehicle: `configs/vehicles/
  generic_f9_class_2d_readme_loads.yaml` (line 17; mass set A: stage 1 395.7 t propellant
  and 25.6 t dry, stage 2 92.67 t and 3.9 t, fairing 1.9 t, all the loads `assumed: true`).
  `experiments/silo_bridge_2d_readme.yaml` is the earlier payload bridge on the same file.
- Its shared blocks and baseline are equal to `silo_offload_2d.yaml`'s (measured). One
  variant, `silo_cold` (80-84), written in full. Offload block (85-90): `reference: pad`,
  `pad_control: true`, one case `{name: silo_cold_s1, of: silo_cold, solve: stage1,
  paired_pad: true}`. No sweeps, no sensitivity.
- **No `energy` block** (file comment 14-15: the fork has no sourced LOX / RP-1 split).
  Recorded: `energy_inputs` absent and the case's `energy` is `None`.
- Calibration record exists: `plots.CALIBRATION_RECORDS` (plots.py 507-510),
  24,700.0 kg against 22,800 kg (+8.33%).
- Recorded (`results/silo_offload_2d_readme/20261003T112956Z`): pad P* 24,700.013 kg,
  `silo_cold` 26,094.432 kg (+1,394.419), `silo_cold_s1` x* 36,006.444 kg (9.099% of
  395.7 t), verified.

What a second vehicle choice costs:

1. The basis becomes one per vehicle: vehicle path, vehicle dict, energy (or none), the
   preset list. The shared blocks and the baseline can stay one copy (they are equal), but
   loading each vehicle's own committed file keeps the guarantee simple.
2. The gate fork's energy block must not be reused. Measured: it **passes validation** on
   the README fork (123.5 t <= 395.7 t and 32.3 t <= 92.67 t, `_check_offload_energy`
   2746-2765) and would state fuel shares of 31.2% and 34.9% where the sourced split is
   30.06% and 30.05%. So README launches have no energy comparison, and the results panel
   needs that case.
3. Limits shown by the form depend on the vehicle (`stage1_t` < 395.7, `stage2_t` < 92.67),
   so they are read from the vehicle dict, not typed.
4. Only one SP1 record exists to check against (the headline case). The +8.1 t penalty is
   the gate fork's break-even (YAML 189-193), with no meaning on this fork.
5. The pad baseline cache needs nothing new: its key includes the vehicle dict.
6. One more form switch, one more set of preset tests, and the calibration caveat text per
   vehicle (+8.3% inside the band against +14.3% outside).

---

## 8. Pad-only launches and the smallest experiment

Measured (resolve and both checks; nothing was flown):

| Dict | Result |
|---|---|
| no `variants` key | resolves; runs `['pad']` |
| `variants: {}` | resolves; runs `['pad']` |
| `variants: {pad2: {assist: {model: none}}}` | resolves; `pad2` has the baseline's trajectory key (a second, identical pad run) |
| `variants: {pad2: {}}` | resolves; the same duplicate |
| the same with an offload case `of: pad2` | **resolves** (runs `pad2_s1`, `pad__offload_stage1`): the config refuses a case of the baseline, not a case of a variant without an assist |

The smallest valid experiment has nine keys: `name`, `vehicle`, the six `SHARED_KEYS`
blocks and `baseline`. `variants`, `sweeps`, `sensitivity`, `bounds`, `cases`, `offload`
and `label` are optional (`ExperimentConfig`, 1863-1878). The baseline itself can shrink to
`{"name": "pad", "end": "insertion"}` and still resolve, but that is a different run
(ignition at 0 s, default integrator block absent from the raw dict). `end` cannot be left
out: `search.figure_of_merit: payload needs end: insertion (end: stage1_burnout runs only
with figure_of_merit: none, or end: impact, which skips the search)`. A baseline without
its `integrator` block resolves to an equal `IntegratorConfig` but a different raw run
dict and trajectory key. So the pad-only launch is the committed baseline, verbatim, with
no `variants` key.

Run path with no variants, read not run: `planar_experiment_result` takes
`variants: dict[str, RunResult]` and nothing in it needs one (results_io.py 1996-2027);
`planar_offload` returns `None` without a block (1713-1715); the summary prints
`(no variants)` (summary.py 454, 1147); `calibration_f9_2d` has no variants and runs
through this path under `label: calibration`. An unlabelled baseline-only write was not
executed in this survey; A4 should test it.

---

## 9. Statements of the phase file that HEAD contradicts or leaves open

1. Section 5.7, "Validation is the simulator's own" with "a missing or non-numeric value"
   among the refusals that must work. Missing values and non-numeric strings are refused,
   but numeric strings, booleans and several non-finite numbers are accepted (section 3.3;
   config.py 217, 636, 634, 638, 637, 790, 589, 730).
2. Section 5.7, "An offload case names a variant (`of`), never the baseline ..., so offload
   fields apply to a silo launch". The config refuses only `of` = the baseline or an
   unknown name (2046-2053). A case of a variant with `assist: {model: none}` resolves.
3. Section 5.6 run path lists the shared blocks as "site, target_orbit, guidance, search,
   checks, the baseline's integrator". `SHARED_KEYS` (162-166) also has `dynamics`, and the
   integrator is not a shared block. The cited test (tests/test_config_planar.py 167-179)
   asserts the six `SHARED_KEYS`, the resolved `PlanarShared` and the budget id; it does
   not assert the baseline or the integrator, and `calibration_f9_2d` differs in
   `sample_dt_s` (0.1 against 0.05).
4. Section 5.7, "derived names are `<case>__pad` for a paired pad". The code builds
   `<case>__<baseline>` (2097-2099, 2116); it is `__pad` only while the baseline is `pad`.
5. Section 10 Q4 lists "the penalty values 0, +2, +4, +8.1 t". A penalty of 0 cannot be
   sent: `stage1_dry_mass_added_t` must be > 0 (1637). Zero is the key left out.
6. Sections 4 and 5.7 point at the model validators for "exactly one of the two" and "two
   ramp-start families". For a variant both are refused earlier, by `merge_run_dicts`, as
   `ExclusiveKeysError` with another text (2143-2144, 2180-2183, 2842-2843). The
   validators' texts appear only for "neither", a lone null, or a broken height pair.

Line numbers the phase file cites were checked and match HEAD: config.py 88, 91, 157, 613,
761, 1709, 1865, 1948-1987; sim.py 932; results_io.py 400, 605, 613, 667, 676, 793, 831,
836, 1687, 2143; cli.py 273, 317; phases/prelude.py 84; summary.py 2021.
