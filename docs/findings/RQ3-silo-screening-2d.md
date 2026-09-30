# RQ3 (preliminary, 2-D): vertical silo screening on the planar model

Status: preliminary. Phase 2 planar model, sweep-optimized guidance (not an
optimal-control solution; Phase 5). Supersedes the 1-D preliminary numbers of
RQ3-silo-screening-1d.md for payload questions; the 1-D note stays as the reference
for what the 1-D model computes.

## Pre-registered v_k fairness rule: outcome (read first)

Plan decision 5 (pre-registered): if the pad's P* at any tested kick trigger v_k beats
its v_k = 50 m/s value by more than `checks.vk_margin_kg` (5 kg), every headline dP* is
quoted against the pad's best v_k. From guidance_trigger_2d (paired sweep, every point
re-runs the pad with the same v_k):

| v_k [m/s] | pad P* [kg] | pad vs its v_k = 50 [kg] | silo_cold P* [kg] | paired dP* [kg] | silo_cold kick regime |
|---|---|---|---|---|---|
| 30 | 26,055.1 | +0.72 | 27,553.2 | +1,498.1 | at the first lit instant (71.8 m/s) |
| 50 | 26,054.4 | 0 | 27,553.2 | +1,498.8 | at the first lit instant (71.8 m/s) |
| 80 | 26,047.7 | -6.71 | 27,550.6 | +1,502.9 | after a vertical rise to 80 m/s |
| 120 | 26,012.5 | -41.86 | 27,526.6 | +1,514.0 | after a vertical rise to 120 m/s |

- **The rule does not fire.** The pad's best tested v_k is 30 m/s, 0.72 kg above its
  v_k = 50 value, below the 5 kg margin. Every headline below is therefore quoted, as
  pre-registered, against the pad at v_k = 50 m/s (the shipped baseline, P* =
  26,054.4 kg).
- **Best-vs-best dP*** (each run at its own best tested v_k): silo_cold's best is v_k 30
  or 50 (identical: it kicks at its first lit instant either way, 27,553.2 kg); the
  pad's best is v_k 30 (26,055.1 kg). Best-vs-best dP* = **+1,498.1 kg**, 0.72 kg below
  the paired value at v_k = 50 (+1,498.8 kg). It is the conservative number for the
  assist; the difference is below the search noise discussed below.
- Probe (labelled, not a shipped run): experiments/guidance_trigger_2d.yaml copied to
  the session scratchpad (p2/step27/probe_vk_low_2d.yaml) with v_k [10, 20, 40] and an
  absolute vehicle path, run with --results-root in the scratchpad (results
  `probe_vk_low_2d/20260930T190111Z`, not retained in the repo) from HEAD 63b45c8
  (clean; it differs from 7ad381f only in results summaries,
  tests/data/calibration_record.json, TODO.md and docs/findings/CAL-f9-leo-2d.md, none
  of them a run input): the pad at v_k 20 and 40 m/s gives 26,055.2 and 26,054.9 kg (+0.77 and
  +0.53 kg against v_k 50); at v_k 10 m/s the pad's search fails (`search_failed`,
  bracket: every gamma* of 18 deg or more is unattainable because even the kick
  bracket's 0.1 deg low end over-turns a 10 m/s kick). So the pad's P*(v_k) is flat to
  within 0.8 kg from 20 to 50 m/s; no untested trigger in that range would move a
  headline by more than about 1 kg. The probe's pad at v_k 50 reproduces the shipped
  pad's P* to the printed digit (26,054.396 kg).
- Figure: RQ3-2d-trigger_run_0004_pad_angles.png (the pad at v_k 120 m/s: vertical
  rise to 120 m/s, kick at 26.4 s, q-alpha 1,941.6 Pa rad, P* 26,012.5 kg).

## Caveats (read first)

- **Model**: planar 2-D ascent over a spherical rotating Earth (omega_p from 28.5 N, due
  east; exact only for the plane of the launch), point-mass mu/r^2 gravity, ICAO
  atmosphere with an isothermal extension above 81 km (not US76), drag from a generic
  Braeunig C_D(M) table (not Falcon 9; A_ref 10.52 m^2), back-pressure p A_e. Point mass:
  thrust points instantly where the steering law says.
- **Unthrottled**: no throttle bucket, no q or q-alpha limit. Max-Q and q-alpha are
  upper bounds on flown values. The summaries flag every silo dP* as an unthrottled or
  unconstrained upper bound; the flag comes from q-alpha (the free kick, above the
  pad's in every silo variant), not from max-Q, which is lower for the silo. A q-limited
  throttle would probably cost the pad more than the silo (RQ6-aero-2d-preliminary.md),
  so the missing throttle likely biases dP* against the assist; unquantified.
- **The kick is free**: no angle-of-attack aerodynamics (no normal force, no induced
  drag). The silo kicks at its first lit instant at 72-77 m/s; the pad at 50 m/s. Its
  axial-drag part is estimated below (under 0.01 m/s); its load and constraint part
  (q-alpha above the pad's in every silo variant; a q-alpha limit could force a later
  or gentler kick) is unquantified.
- **Sweep-optimized guidance**: a shared parametrisation (vertical rise, a
  hold-to-alignment kick at v_k = 50 m/s, gravity turn along v_rel, linear-tangent
  stage 2); gamma* at MECO, the kick angle delta and the LTG pair are solved per run.
  v_k and the kick law were chosen with prototype knowledge (CAL-f9-leo-2d.md). Both
  runs of each comparison fly the same restricted family; how much an optimal-control
  ascent would change each is unknown until Phase 5.
- **Drive model**: `constant_accel`, a prescribed net acceleration (3 g0 net, 100 m
  stroke, vented shaft, no friction, infinite jerk at push start and release). The drive
  force is whatever the track equation needs; a hot start therefore buys no exit
  speed. Carriage mass 0 unless stated (silo_sled_22t: 22 t). Drive efficiency 0.5
  (assumed), braking at 5 g0 (assumed, added to the facility length, not modelled).
- **Track phase**: flat 1-DOF with constant g_eff = 9.7721 m/s^2 (rotation included,
  Coriolis neglected); no air drag in the vented shaft (under a prescribed acceleration
  the drive absorbs it, so the release speed and the payload are unchanged; the drive
  energy, peak power and interface force are biased low by about 0.87 MJ, 1.3 MW and
  17 kN, own estimate from q = 3.6 kPa at the exit, C_D 0.46 and a drag growing with s:
  0.04 %, 0.08 % and 0.08 %).
- **No structural penalty for the new load case**: every dP* is for the unmodified
  vehicle. The 4.0 g0 full-stack axial load on the track (22.5 MN interface force, with
  full tanks; the pad's stack feels 1.36 g0 at release, pad/timeseries.csv at t = 0, so
  2.9 times that) would need a stronger stage 1 (README: strengthen stage 1 and count
  the mass), which the model does not count. Derived from the recorded +/-10 %
  stage-1 dry-mass cases of silo_cold (+/-2.22 t): P* changes by about 184 kg per tonne
  of stage-1 dry mass ((27,966.6 - 27,148.5) kg / 4.44 t; 186.2 and 182.3 kg per t on
  the two sides). Silo-only strengthening of about 8.1 t (37 % of the 22.2 t stage-1 dry
  mass; derived, 1,498.8 / 184.3, a linear extrapolation beyond the +/-2.22 t tested)
  would cancel the +1,498.8 kg; each tonne costs about 184 kg.
- **Calibration miss carried**: the gate vehicle (mass set C,
  configs/vehicles/generic_f9_class_2d.yaml) reaches 26,054 kg to the reference orbit,
  +14.3 % against the published 22.8 t and outside the +/-10 % band
  (docs/findings/CAL-f9-leo-2d.md). The user accepted the miss on 2026-09-30; every
  number here is on that vehicle and inherits it. The vehicle payload P0 = 22.8 t is
  3.25 t below the pad's P*.
- **Other stated biases** (summaries' assumption lists): the power-on C_D table is used
  in the cold start's 0.5 s unlit coast (a small bias toward cold starts, sized below);
  one A_ref through staging and the fairing drop; MVac starts at full thrust; no
  flight-performance reserve or unusable residuals, the payload adapter counts as
  payload; stage 2 exit area 8.6 m^2 assumed; staging instantaneous; fairing dropped on
  the 1,135 W/m^2 heating rule; the matched residual at P0 is taken at the P*-optimal
  gamma* (a few kg low, against the assist).
- **Reference orbit**: 200 km circular, 28.5 deg, due east, expendable.

## Provenance

| experiment | results directory | git | contents |
|---|---|---|---|
| guidance_trigger_2d | results/guidance_trigger_2d/20260930T174950Z | 7ad381f227a9, clean | paired sweep of v_k over pad and silo_cold |
| silo_screening_2d (run) | results/silo_screening_2d/20260930T175743Z | 7ad381f227a9, clean | baseline pad, 9 variants, 24 sensitivity cases, the aero bound |
| silo_screening_2d (sweeps) | results/silo_screening_2d/20260930T182453Z | 7ad381f227a9, clean | sweep_1 accel x stroke, sweep_2 t_ign x t_ramp, sweep_3 lag tau |
| silo_bridge_2d_readme | results/silo_bridge_2d_readme/20260930T185034Z | 7ad381f227a9, clean | pad, pad_instant, silo_instant, silo_cold on the README-loads fork |
| calibration_f9_2d (context) | results/calibration_f9_2d/20260930T173928Z | 7ad381f227a9, clean | calibration re-run after the amendment |

- Pre-registration state: the inputs were frozen at c2849b7; the amendment 7ad381f (2 s
  planar step cap, M2 diagnostic only; the user's decisions of 2026-09-30) was committed
  before any research run. All four experiments ran from that clean commit; their
  top-level summaries are committed in 63b45c8. Every run shares search budget id
  a17a0160...a7df.
- Every run and every comparison passes its blocking checks (rocket-equation closure,
  loss identity, insertion e below 1e-6, attribution closure, M3, M4, M5 where
  applicable): no `bug_suspect` anywhere. M2 is diagnostic (below).
- Numbers are copied from the run's summary.md and metrics.json; derived numbers are
  labelled "derived" with the arithmetic shown.
- **Labelled probes** (not shipped runs). Their scripts, inputs and outputs are kept
  in docs/findings/probes/RQ3-2d/ (copied from the session scratchpad; the v_k
  probe's results directory itself was not retained):
  - v_k probe: see the fairness-rule section above (probes/RQ3-2d/probe_vk_low_2d.yaml).
  - Equal-gamma* probe (launchsim): probe_eqgamma/probe_eqgamma.py, output
    probe_eqgamma/probe_eqgamma_out.txt. Run from HEAD 63b45c8, whose src/, configs/
    and experiments/ are identical to 7ad381f (git diff 7ad381f HEAD on those paths is
    empty). It evaluates pad, pad_instant, silo_instant and silo_cold through
    launchsim's own rung-2 evaluation (SearchContext.evaluate in final mode, warm-started
    from each run's recorded delta and LTG pair) at P_ref = 26,054.4 kg with gamma*
    forced to a common value, and reads the terms with compare.attribution_terms. It
    reproduces the recorded matched margins at the runs' own gamma* (silo_cold 165.2476
    against 165.248 m/s; silo_instant 199.9899 against 199.990; pad 1e-4 m/s).
  - Stage-2 swap probe (reviewer; independent, untested integrator, not launchsim, not
    a validated model): review_skeptic/sk.py and e3.py, output review_skeptic/e3_out.txt.
    It restarts stage 2 from the pad's MECO state at the pad's gamma* with the silo's
    MECO speed or altitude swapped in. It reproduces the launchsim probe's post-MECO
    terms for the pad (gravity 400.869, steering 88.962 m/s) and silo_cold's margin at
    the pad's gamma* (159.504 m/s). Cited only to split a launchsim result, never as a
    finding.

## Headline: payload capacity against the pad

All silo variants: 3 g0 net, 100 m stroke, exit 76.707 m/s after 2.607 s, vented
shaft. dP* = variant P* - pad P* (26,054.4 kg), sweep-optimized, same vehicle, same
guidance parametrisation and search budget. "Yardstick" is the README's ideal
rocket-equation screening payload for the run's release speed, at the vehicle payload
P0 (the stricter, used for the verdict) and at the pad's P*.

| variant | stage-1 start | P* [kg] | dP* [kg] | yardstick P0 / P*_pad [kg] | beyond the stricter yardstick [kg] | screening status |
|---|---|---|---|---|---|---|
| pad (baseline) | lit at -2 s, 2 s ramp, held down | 26,054.4 | 0 | - | - | - |
| pad_instant (yardstick) | step at release | 26,137.5 | +83.1 | 0 / 0 | +83.1 | ok |
| silo_instant (yardstick) | step at release | 27,880.4 | +1,826.0 | 675.3 / 765.4 | +1,150.6 | ok |
| **silo_cold** (reference) | 0.5 s after release, 2 s ramp | 27,553.2 | **+1,498.8** | 675.3 / 765.4 | +823.5 | ok |
| silo_cold_lag | 0.5 s after release, lag tau 1 s | 27,553.2 | +1,498.8 | 675.3 / 765.4 | +823.4 | ok |
| silo_hot_ramp_on_track | lit at -2 s on the track, 2 s ramp | 27,788.2 | +1,733.8 | 675.3 / 765.4 | +1,058.5 | ok |
| silo_hot_full | lit 2 s before the push (hold), full on the track | 27,543.0 | +1,488.6 | 675.3 / 765.4 | +813.3 | ok |
| silo_hot_full_impinged | as silo_hot_full, f_imp = 1 | 27,543.0 | +1,488.6 | 675.3 / 765.4 | +813.3 | ok |
| silo_sled_22t | as silo_cold, 22 t carriage | 27,553.2 | +1,498.8 | 675.3 / 765.4 | +823.5 | ok |
| silo_failed | no ignition | impact | n/a | - | - | not_checked |

**Headline: the reference cold-start silo gains +1,498.8 kg (+5.75 % of the pad's
26,054.4 kg), about 2.0 times the README's ideal-screening estimate at its release
speed (765.4 kg at the pad's payload, 675.3 kg at 22.8 t).** Best-vs-best (trigger
study) +1,498.1 kg. It is an upper bound in its free kick (q-alpha above the pad's, no alpha
aerodynamics). It is unthrottled; the pad's higher max-Q suggests a throttle would cost
the pad more, unquantified (RQ6). Under every +/-10 % sensitivity case it stays between
+1,345 and +1,667 kg (section "Sensitivity and the aero bound"). Three things shrink it.
First, the pad's clamped 2 s ramp, a baseline convention, accounts for 130.7 kg gross
(8.7 %, the matched pre-flight credit) and 83.1 kg net (5.5 %, the pad_instant pair,
which also counts the pad's lighter liftoff): against pad_instant, which is lit at
release, the gain is +1,415.8 kg (derived: 27,553.2 - 26,137.5 = 1,498.8 - 83.1).
Second, the vehicle calibrates 14.3 % high: dP*/P* is 5.75 % here and 5.65 % on the
README-loads vehicle (bridge: 1,394.4 / 24,700.0 kg), so on a vehicle calibrated to
22.8 t the gain would be expected near 1.3 t (derived by proportion, 0.0575 x 22,800 =
1,311 kg; not run). Third, no structural mass is charged for the new 4.0 g0 full-stack
load case: at the recorded 184 kg of P* per tonne of stage-1 dry mass, about 8.1 t of
silo-only strengthening would cancel the gain (derived; Caveats). The drive is a
prescribed 3 g0 acceleration with a 0 t carriage and no shaft air drag; under
constant_accel none of these changes P*, but drive energy, power and interface force
are biased low (Caveats).

Every silo variant beats the screening yardstick by 0.8 to 1.2 t. CLAUDE.md requires
the loss breakdown to explain that or it is treated as a bug; the next section is that
investigation.

## Is the screening beat a bug? Investigation

### (a) The accounting closes exactly

The matched-payload attribution (docs/physics.md, "Screening-beat rule (2-D)") flies
each variant at the pad's P* (P_ref = 26,054.4 kg) with its own gamma*, and splits the
difference in delta-v margin into release speed, final speed, gravity, drag, steering,
back-pressure, pre-flight and fairing terms (each in the variant's favour). The kg
split is dP* x term / sum, so the kg column adds up to dP* by construction; the m/s
terms add up to the measured margin difference only if the physics bookkeeping is
right, and they do: residual 8.7e-12 m/s for silo_cold, at most 1.3e-9 m/s in any
comparison of the four experiments.

| term | silo_cold [m/s] | [kg] | silo_instant [m/s] | [kg] | silo_hot_ramp_on_track [m/s] | [kg] |
|---|---|---|---|---|---|---|
| release speed | +76.707 | +695.8 | +76.707 | +700.4 | +76.707 | +699.4 |
| gravity, flight start to MECO | +14.423 | | +37.538 | | +44.906 | |
| gravity, after MECO | +32.737 | | +39.158 | | +37.208 | |
| gravity, total | +47.160 | +427.8 | +76.696 | +700.3 | +82.114 | +748.7 |
| steering | +9.273 | +84.1 | +11.187 | +102.1 | +10.658 | +97.2 |
| gravity + steering (the only split read as physics) | +56.433 | +511.9 | +87.883 | +802.4 | +92.771 | +845.9 |
| drag | +3.507 | +31.8 | +3.620 | +33.1 | +3.356 | +30.6 |
| back-pressure | +13.574 | +123.1 | +16.635 | +151.9 | +16.620 | +151.5 |
| pre-flight (the pad's hold-down burn) | +14.408 | +130.7 | +14.408 | +131.5 | 0.000 | 0.0 |
| fairing | +0.618 | +5.6 | +0.737 | +6.7 | +0.696 | +6.3 |
| final speed (LTG acceptance) | +1.2e-5 | +1e-4 | -7e-6 | -6e-5 | -2e-7 | -1e-6 |
| **sum = d dv_margin, dP*** | **+165.248** | **+1,498.8** | **+199.990** | **+1,826.0** | **+190.151** | **+1,733.8** |
| attribution residual [m/s] | 8.7e-12 | | 0 | | 1.0e-9 | |

The gravity and steering terms trade against each other as gamma* moves (-15.1 and
+13.1 m/s per deg of the variant's gamma* for silo_cold), so only their sum is
interpreted. That sum moves -2.08 m/s per deg: over gamma*_ref -0.5 / 0 / +0.5 deg it
is 56.92 / 56.43 / 54.84 m/s for silo_cold.

### (b) The anchors and the closed forms

**Pure release-speed effect.** Two recorded pairs differ only in the 76.707 m/s
release speed:

- silo_instant vs pad_instant (both lit at release with a step, same mass at the flight
  start): dP* = 27,880.4 - 26,137.5 = **+1,742.9 kg** (derived from the two recorded
  P*). Difference of the two matched attributions (both against the same pad at the same
  P_ref; derived): +190.558 m/s = release speed 76.707 + gravity 82.419 (45.174 before
  MECO, 37.245 after) + steering 10.625 + back-pressure 16.741 + drag 3.364 + fairing
  0.701 + pre-flight 0.000. Gravity + steering +93.045 m/s.
- silo_hot_ramp_on_track vs pad (both lit at -2 s with the 2 s ramp, both at full
  thrust at release with the same 2,697.46 kg burned, one clamped on the pad, one
  riding the carriage): **+1,733.8 kg**, +190.151 m/s, pre-flight term exactly 0.

The two anchors agree to 9 kg (0.5 %). A 76.7 m/s vertical release alone is worth
about 1.74 t on this vehicle, 22.6 to 22.7 kg per m/s of release speed, 2.27 times the
screening estimate at the pad's payload (765.4 kg, 9.98 kg per m/s). M5 (the anchor
bound) passes for every named variant: silo_cold's +1,498.8 kg is below its bound of
+1,886.6 kg (anchor 1,742.9 + the screening equivalent of the pad's pre-flight term,
142.2 + the 1.5 kg margin).

**Pre-flight term, closed form.** The pad lights at -2 s with a linear 2 s ramp of nine
914.1 kN, Isp 311 s engines: mdot = 8,226.9 kN / (311 x 9.80665 m/s^2) = 2,697.46 kg/s
at full thrust, so the ramp burns mdot x t_ramp / 2 = 2,697.46 kg while clamped
(recorded 2,697.4608722 kg). At the pad's liftoff mass m0 = 572,354.4 kg the closed
form c1 ln(m0 / (m0 - 2,697.46 kg)) with c1 = 3,049.87 m/s gives 14.40776 m/s; the
recorded term is 14.407764742880927 m/s. The cold silo does not pay it. The pad reaches
T = W 0.49 s before release (derived from pad/timeseries.csv: T = T_vac(t) - p A_e with
T_vac ramping to 8,226.9 kN and p A_e = 620.1 kN; the first 0.05 s sample with
T >= m g_ref is -0.45 s, and linear interpolation gives -0.493 s; at release T =
7,607 kN against W = 5,567 kN, T/W 1.37) and stays clamped to t = 0 by the
pre-registered pad convention.

**What the avoided hold-down burn is worth, net.** pad_instant vs pad (both from the
pad, one without the 2 s clamped ramp): +83.1 kg = pre-flight +14.408 m/s (+126.9 kg)
- gravity + steering 5.162 m/s (-45.5 kg: pad_instant lifts off 2.7 t heavier, at a
lower thrust-to-weight) + drag, back-pressure and fairing +0.185 m/s. The mirror pair
silo_hot_ramp_on_track vs silo_instant (derived) gives -92.2 kg = pre-flight -14.408
m/s + gravity + steering +4.888 m/s + drag, back-pressure and fairing -0.320 m/s. So 2.7 t of propellant
burned before the flight costs 14.4 m/s of delta-v and returns about 5 m/s of gravity
loss through the lighter liftoff: net 83 to 92 kg.

**Cold-start penalty.** silo_cold vs silo_instant (derived): -327.1 kg, -34.742 m/s =
gravity -29.536 (-23.115 of it before MECO) + steering -1.914 + back-pressure -3.061 +
drag -0.113 + fairing -0.119. The 1-D constant-g formula for the same 0.5 s delay and
2 s ramp is g_eff (t_d + t_r/2) = 14.66 m/s (15.12 m/s integrated in 1-D); the 2-D
matched cost is 2.37 times the formula (RQ2-ignition-timing-2d.md).

**Chain (derived; an exact sum of recorded P* differences):** pad -> pad_instant +83.1
kg (no clamped ramp) -> silo_instant +1,742.9 kg (release speed) -> silo_cold -327.1 kg
(0.5 s coast and a 2 s ramp in the air instead of a step at release) = +1,498.8 kg.
Equivalently pad -> silo_hot_ramp_on_track +1,733.8 kg (release speed at equal mass and
thrust) -> silo_cold -235.0 kg (the ramp moved from the track into the air after a
0.5 s coast: +14.408 m/s pre-flight, -36.339 m/s gravity + steering, -3.046 m/s
back-pressure, +0.151 m/s drag, -0.078 m/s fairing).

### (c) Guidance and model artefacts that could favour the silo, sized

| candidate artefact | how it was sized | size |
|---|---|---|
| The pad must rise vertically to v_k = 50 m/s; the silo kicks at its first lit instant | Recorded trigger study (v_k 30 / 50 / 80 / 120) and the labelled probe (v_k 20 / 40): the pad's P* is flat to 0.77 kg between 20 and 50 m/s. Giving the silo the pad's constraint (v_k 80: it must rise to 80 m/s before kicking) costs it 2.6 kg (27,553.2 -> 27,550.6 kg) | at most about 3 kg, either way |
| The kick has no angle-of-attack aerodynamics | Derived bound from the recorded time series: an axial loss of int q A_ref C_N,alpha psi^2 / m dt with C_N,alpha = 4 per rad (twice the slender-body value; an assumed bound) is 0.0029 m/s for silo_cold, 0.0043 m/s for silo_instant and 0.0047 m/s for the pad over the whole flight | below 0.05 kg either way; for stage 1 (the kick) it is larger for the silo (pad 0.0005, silo_cold 0.0010, silo_instant 0.0027 m/s); the whole-flight values are dominated by stage-2 LTG psi (derived from the time series) |
| gamma* lands differently (silo_cold 21.65 deg, pad 22.99 deg) | Each is its own converged optimum: the refine objective is flat (the pad's m_res changes by 0.036 kg over the last 0.045 deg; silo_cold's by 0.0014 kg over 0.003 deg), so a 0.1 deg gamma* error costs under 0.2 kg (quadratic estimate from the pad's refine points; derived). Forcing silo_cold to the pad's gamma* (22.99 deg) lowers its matched margin by 5.74 m/s (165.248 -> 159.504 m/s; g + s by 6.66 m/s; about 52 kg at 9.07 kg per m/s; labelled launchsim probe, Provenance). The linear extrapolation from the recorded +/-0.5 deg points (-2.08 m/s per deg x 1.34 deg) gives only 2.8 m/s, because g + s is curved in gamma* (56.92 / 56.43 / 54.84 m/s). A handicap for the silo, not a favour | under 0.2 kg in the silo's favour |
| The LTG acceptance box | The final-speed term: +1.2e-5 m/s for silo_cold; insertion errors 0.02 m and 1.1e-4 m/s for both | 1e-4 kg |
| Search and integration noise | Final payload xtol 0.05 kg; search minus final payload -0.037 kg on both runs; shipped vs 10x tighter budget moves P* by at most 3.4e-3 kg and under-states silo_cold's margin at P0 by about 0.2 kg more than the pad's (docs/physics.md, "Convergence (planar)") | about 1 kg (taken as the search noise) |
| The power-on C_D table in the cold start's 0.5 s unlit coast | Derived: drag at release 17 kN (q 3.6 kPa, C_D 0.46, 10.52 m^2) on 574 t is 0.03 m/s^2; even a doubled power-off C_D costs 0.015 m/s over 0.5 s | under 0.4 kg (0.015 m/s of release-time speed at the anchor's 22.7 kg per m/s) |
| No air drag in the shaft | Under constant_accel the drive absorbs it: release speed and flight unchanged | 0 kg (energy, power and force biased low, see Caveats) |
| The pad convention itself: clamped to t = 0 although T > W from -0.49 s | Not an artefact of guidance but of the pre-registered baseline. Its cost is silo_cold's pre-flight term (130.7 kg of the split). A pad released at T = W was not run; the pad_instant pair (+83.1 kg, the whole clamped ramp removed) bounds what a different pad convention could recover | up to 83 kg of the headline belongs to the pad convention, not to the push |

No candidate reaches the search noise except the kick-trigger asymmetry (about 3 kg)
and the pad convention, which is a stated baseline choice, not a bug.

### (d) Verdict: where silo_cold's +1,498.8 kg comes from

| part | m/s at P_ref | kg (share) | what it is |
|---|---|---|---|
| release speed, face value | 76.707 | 695.8 (46.4 %) | the exit speed at the matched rate of 9.07 kg per m/s of margin (770.0 kg, 51.4 %, in the capacity basis; below) |
| avoided hold-down burn | 14.408 | 130.7 (8.7 %) | the pad's 2.7 t clamped ramp; closed form exact; worth 83.1 kg net in the pad_instant pair |
| trajectory effect: gravity + steering | 56.433 | 511.9 (34.2 %) | the release's trajectory gain (+93.0 m/s in the anchor pair), less the heavier liftoff of a pad lit at release (-5.2 m/s, pad_instant vs pad), less the cold start's in-air startup (-31.5 m/s against silo_instant): 93.045 - 5.162 - 31.450 = 56.433 (derived). The matched split (14.4 m/s of gravity before MECO, 32.7 after, 9.3 steering) depends on gamma* and is not read as physics: at equal gamma* the release saves about 25 m/s of stage-1 gravity loss; silo_cold's in-air startup and the pad's lighter liftoff give it back (below) |
| back-pressure | 13.574 | 123.1 (8.2 %) | the silo is higher at every time, so p A_e costs less; M3 ratio 0.67 of its time-shift estimate |
| drag | 3.507 | 31.8 (2.1 %) | lower q through the transonic region (RQ6-aero-2d-preliminary.md) |
| fairing | 0.618 | 5.6 (0.4 %) | earlier fairing drop |
| **unexplained** | 8.7e-12 | 0 | below the search noise; **no suspected bug** |

Why the README's screening misses it: the ideal screening converts the release speed
into payload at fixed losses. The release changes the losses by about its own size
(74.1 m/s of gravity, steering, back-pressure, drag and fairing for 76.7 m/s of
release in silo_cold, derived: 56.433 + 13.574 + 3.507 + 0.618; 113.9 m/s in the instant
anchor), and the pad's pre-flight burn adds 14.4 m/s; the beat beyond screening (derived: 1,498.8 - 765.4 = 733.4 kg at the pad's
payload) is carried by the loss and pre-flight terms in either attribution basis.

The kg shares depend on the attribution basis; neither basis is the physics:

| part | matched basis (P_ref, 9.07 kg per m/s) [kg] | capacity basis (own P*, 10.04 kg per m/s) [kg] |
|---|---|---|
| release speed | 695.8 (46.4 %) | 770.0 (51.4 %) |
| gravity + steering | 511.9 (34.2 %) | 405.3 (27.0 %) |
| pre-flight (the pad's hold-down burn) | 130.7 (8.7 %) | 144.6 (9.6 %) |
| back-pressure | 123.1 (8.2 %) | 136.2 (9.1 %) |
| drag | 31.8 (2.1 %) | 36.5 (2.4 %) |
| fairing | 5.6 (0.4 %) | 6.1 (0.4 %) |

The capacity basis is derived from the recorded delta_* fields of metrics.json
(comparison.silo_cold): at the two runs' own payloads the ideal delta-v difference is
149.308 m/s = release 76.707 + gravity 41.570 - steering 1.195 + pre-flight 14.408 +
back-pressure 13.572 + drag 3.639 + fairing 0.607, and dP* / 149.308 = 10.04 kg per
m/s, split pro rata. In that basis the release speed alone is worth 770 kg, equal to
the 765.4 kg yardstick, as the screening assumes. The matched basis flies both runs at
the pad's P*, where the silo's g + s gain is 56.4 m/s against 40.4 m/s at the capacity
payloads; its pro-rata split charges the extra losses of carrying the added 1.5 t to
every term, which is why its release term (695.8 kg) sits below the yardstick. That is
a property of the allocation, not of the release.

Is the gravity term physical? With M2 diagnostic (the user's decision of 2026-09-30),
no blocking check bounds it; its size rests on the exactly closing identity and on the
following evidence, none of which is a proof:

- Mechanism. In vertical flight a release speed V0 persists as a speed gain of V0 plus
  an altitude gain that grows as V0 t (the 1-D model shows it; its burnout-speed figure
  of merit discarded the altitude). In 2-D, at their own payloads, silo_cold reaches
  MECO 5,716 m higher and 100.9 m/s faster (Earth-relative) than the pad while carrying
  1,498.8 kg more payload. Stage 2 then starts faster and higher; at the matched
  payload (the pad's P*) its burn is shorter, which the accounting books as less gravity
  loss after MECO (32.7 m/s) and less steering (9.3 m/s). At each run's own P* both
  stage-2 burns run to depletion and last the same 373.97 s. Which of the two MECO
  differences carries the gain is in the next bullet.
- Equal gamma* (labelled launchsim probe, Provenance, unless stated). At equal gamma*
  silo_cold's stage-1 gravity loss to MECO is within 2.5 m/s of the pad's (+2.52 m/s
  with both at the pad's 22.99 deg, +1.62 m/s with both at the silo's 21.65 deg)
  because three effects cancel:
  - the release itself saves about 25 m/s: silo_instant against pad_instant, both lit
    at release, 1,074.20 against 1,099.66 m/s at 22.99 deg (-25.46 m/s) and -26.73 m/s
    at 21.38 deg; docs/physics.md ("Time-shift mechanism", instant-pair row) measured
    -32.1 / -27.7 / -23.8 m/s at 15 / 20 / 25 deg, a quarter of the time-shift estimate;
  - the cold start's 0.5 s coast and in-air ramp give back 19.43 m/s (silo_cold minus
    silo_instant at 22.99 deg);
  - the pad's 2.7 t lighter liftoff gives back 8.55 m/s (pad_instant minus pad).

  Derived: -25.46 + 19.43 + 8.55 = +2.52 m/s. docs/physics.md's cold-start row (-3.2 to
  +3.9 m/s over 15 to 25 deg, ratio -0.04 to 0.03) is the same cancellation. So the
  +14.4 m/s before MECO in silo_cold's matched split is the gamma* difference, and for
  silo_cold the trajectory gain appears after MECO. At 22.99 deg both runs reach MECO
  with the same mass (161,454.4 kg); silo_cold's MECO is 8,191 m higher and 106.09 m/s
  faster (Earth-relative), and its post-MECO gravity + steering is 52.29 m/s below the
  pad's (gravity 29.40, steering 22.89 m/s; derived from the probe's terms). The
  reviewer's stage-2 swap probe (untested, not launchsim; Provenance) splits that
  52.3 m/s: the silo's MECO speed alone gives 32.4 m/s of it (22.3 m/s steering: the
  LTG steers less) and 138.6 m/s of margin (1.31 m/s of margin per m/s of MECO speed
  over the full 106 m/s; 1.33 for the first 1 m/s); the silo's altitude alone gives
  22.8 m/s (19.8 m/s gravity) and 23.8 m/s of margin (2.9 m/s per km; 3.0 for the
  first km); the two do not add (52.3 m/s and 159.5 m/s of margin jointly). On that
  probe, most of the post-MECO gain is the faster MECO state, not the altitude.
- Bound. The whole-flight gravity gain stays below the plan's time-shift estimate in
  every named variant (M2 ratios 0.449 to 0.913; stage 1 alone 0.137 to 0.608): the
  model produces less gravity-loss saving than the plan's optimistic estimate, not
  more (at nominal inputs; one sensitivity case, silo_hot_full at stage-1 Isp -10 %,
  reaches 1.047).
- Symmetry. The same amplification appears with the opposite sign when early speed is
  lost at an identical release: the release anchor gives 190.6 m/s of margin for
  76.7 m/s of release speed (2.48 times), the cold-start penalty 34.7 m/s for a 14.66
  m/s formula loss (2.37 times), and every point of the ignition sweeps 2.29 to 2.45
  times its formula. An error in the release map or the track phase would not be
  expected to produce the same factor for a change of ignition timing alone, where
  both runs leave the track identically.
- Smoothness. In the accel x stroke sweep dP* per m/s of release speed rises smoothly
  with the release speed, and the slope of dP* between neighbouring speeds (22.4 to
  23.5 kg per m/s up to 99 m/s; 21.9 and 21.3 kg per m/s to the two unconstrained-kick
  points at 133 and 172 m/s) shows no step at the kick-regime boundary.

**Conclusion.** The screening beat is explained by the loss breakdown and is not
treated as a bug. In plain terms, for silo_cold (matched basis; capacity basis in
brackets): about 46 % (51 %) of the gain is the release speed at face value, about 9 %
(10 %) is the pad's hold-down burn that the silo does not pay (a baseline convention,
not the push), about 34 % (27 %) is a trajectory effect (lower gravity and steering
loss, net of the cold start's own startup cost; at equal gamma* it appears after MECO,
because the in-air startup and the pad's lighter liftoff give back the release's
stage-1 gravity saving), about 8 % (9 %) is back-pressure and about 2 % drag. Nothing is
unexplained beyond the search noise. What remains unverified is whether an
optimal-control ascent (Phase 5) would change the trajectory term in either direction
(both runs fly the same restricted guidance family), and the headline charges no
structural mass for the new load case (Caveats).

## Matched-payload attribution, every variant

At P_ref = 26,054.4 kg, m/s in the variant's favour (summary.md). "g + s" is gravity +
steering; M2 is diagnostic.

| variant | release | g + s | gravity (to MECO / after) | back-pressure | drag | pre-flight | fairing | d dv_margin | dP* [kg] | M2 ratio (stage 1) | M3 | M4 share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pad_instant | 0 | -5.162 | -5.723 (-7.636 / +1.913) | -0.107 | +0.256 | +14.408 | +0.036 | +9.432 | +83.1 | n/a | n/a | 0.087 |
| silo_instant | 76.707 | +87.883 | +76.696 (37.538 / 39.158) | +16.635 | +3.620 | +14.408 | +0.737 | +199.990 | +1,826.0 | 0.730 (0.357) | 0.824 | 0.120 |
| silo_cold | 76.707 | +56.433 | +47.160 (14.423 / 32.737) | +13.574 | +3.507 | +14.408 | +0.618 | +165.248 | +1,498.8 | 0.449 (0.137) | 0.673 | 0.144 |
| silo_cold_lag | 76.707 | +56.436 | +47.165 (14.423 / 32.743) | +13.557 | +3.517 | +14.408 | +0.619 | +165.243 | +1,498.8 | 0.449 (0.137) | 0.672 | 0.144 |
| silo_hot_ramp_on_track | 76.707 | +92.771 | +82.114 (44.906 / 37.208) | +16.620 | +3.356 | 0 | +0.696 | +190.151 | +1,733.8 | 0.782 (0.427) | 0.824 | 0.124 |
| silo_hot_full | 76.707 | +105.201 | +95.869 (63.898 / 31.972) | +16.573 | +2.653 | -37.889 | +0.592 | +163.837 | +1,488.6 | 0.913 (0.608) | 0.821 | 0.138 |
| silo_hot_full_impinged | as silo_hot_full (f_imp changes only track forces and drive energy) | | | | | | | +163.837 | +1,488.6 | 0.913 (0.608) | 0.821 | 0.138 |
| silo_sled_22t | identical to silo_cold (the carriage mass changes only the drive) | | | | | | | +165.248 | +1,498.8 | 0.449 (0.137) | 0.673 | 0.144 |

kg split (matched basis, summary.md) of the variants not in the table of (a):
silo_hot_full and silo_hot_full_impinged: release 697.0, gravity + steering 955.9,
back-pressure 150.6, drag 24.1, pre-flight -344.3, fairing 5.4; sum 1,488.6 kg.
silo_cold_lag: release 695.7, gravity + steering 511.9, back-pressure 123.0, drag 31.9,
pre-flight 130.7, fairing 5.6; sum 1,498.8 kg. pad_instant: see (b).

## Screening check per variant

- pad_instant: beats its 0 kg yardstick by 83.1 kg, explained by the pre-flight term
  (+14.408 m/s) less the heavier liftoff's gravity + steering (-5.162 m/s). M4's verdict
  is not robust over gamma* +/- 0.5 deg (the drag + steering share of this small
  9.4 m/s gain swings from -0.76 to 0.83; the summary marks it); the beat itself is the
  pre-flight term.
- silo_instant, silo_cold, silo_cold_lag, silo_hot_ramp_on_track, silo_sled_22t: beat
  the yardstick by 823 to 1,151 kg; explained by gravity + steering (56 to 93 m/s),
  back-pressure (13.6 to 16.6 m/s), drag (3.4 to 3.6 m/s) and, for the variants lit
  after release, the pad's pre-flight term (14.4 m/s). Every blocking check passes.
- silo_hot_full and silo_hot_full_impinged: beat it by 813.3 kg although their
  pre-flight term is -37.9 m/s (9,730.6 kg burned before release, 2,697.5 kg in the
  hold and 7,033.1 kg on the track); a 9.7 t lighter vehicle at release flies a lower-loss
  trajectory (gravity + steering +105.2 m/s, the largest of all). Explained, not a bug;
  but the hot start buys nothing over the cold one (RQ2-ignition-timing-2d.md).
- silo_failed: no attribution (no orbit), no finding rests on a beat.
- Sensitivity cases and the aero bound compared with the baseline of the same vehicle:
  every one is attributed and ok. The summary's "Unexplained beats" line lists the same
  cases compared with the unperturbed pad (two different vehicles, not attributed by
  design, `not_checked`); those cross-vehicle numbers support no finding and are not
  used here.

## Sensitivity and the aero bound

Pre-registered +/-10 % cases of silo_cold and silo_hot_full. Each vehicle perturbation
is compared with the pad re-run under the same perturbation (full shared search on
both); drive efficiency and the screening Isp do not change the trajectory. Change =
case minus the nominal dP*.

| parameter | silo_cold dP* -10 % / +10 % [kg] | change [kg] | silo_hot_full dP* -10 % / +10 % [kg] | change [kg] |
|---|---|---|---|---|
| nominal | 1,498.8 | - | 1,488.6 | - |
| stage-1 dry mass | 1,510.4 / 1,487.5 | +11.6 / -11.4 (+/-0.8 %) | 1,496.5 / 1,480.8 | +7.9 / -7.8 |
| stage-1 Isp_vac | 1,345.0 / 1,667.4 | -153.8 / +168.5 (-10.3 / +11.2 %) | 1,326.5 / 1,667.4 | -162.1 / +178.8 |
| stage-2 Isp_vac | 1,374.2 / 1,611.7 | -124.6 / +112.9 (-8.3 / +7.5 %) | 1,356.0 / 1,610.5 | -132.6 / +121.9 |
| C_D scale | 1,496.0 / 1,501.7 | -2.9 / +2.8 (+/-0.2 %) | 1,487.1 / 1,490.1 | -1.5 / +1.5 |
| drive efficiency | 1,498.8 / 1,498.8 | 0 (electrical 1,388.3 / 1,135.9 kWh) | 1,488.6 / 1,488.6 | 0 (electrical 900.9 / 737.1 kWh) |
| screening Isp (yardstick only) | 1,498.8 / 1,498.8 | 0 (yardstick 683.4 / 667.5 kg) | 1,488.6 / 1,488.6 | 0 |

- The headline moves by at most 11 % under any single +/-10 % case: +1,345 to
  +1,667 kg for silo_cold. The engine Isp dominates (a better engine makes every m/s,
  including the release speed's, worth more payload); the stage-1 dry mass and C_D move
  it by under 1 %. Every case is attributed and passes every blocking check.
- Sensitivity was pre-registered for silo_cold and silo_hot_full only; the other
  variants' dP* (silo_instant, silo_hot_ramp_on_track, the sweeps) carry no sensitivity
  run.
- silo_hot_full minus silo_cold (derived from the recorded cases, each against the pad
  under the same perturbation): -10.2 kg nominal; -13.9 / -6.6 kg for stage-1 dry mass
  -10 / +10 %, -18.5 / +0.1 kg for stage-1 Isp, -18.2 / -1.2 kg for stage-2 Isp, -8.9 /
  -11.6 kg for C_D, -10.2 kg for drive efficiency. The full hot start never gains more
  than 0.1 kg over the cold start, but the size of its deficit is not robust: the two
  are a tie within the sensitivity, not a clear loss.
- Carriage mass and drive efficiency cannot change the payload under the
  prescribed-acceleration drive, by construction; they move only energy and power.
- **Aero bound** (A_ref 21.24 m^2, the 5.2 m fairing section, run as a paired bound):
  pad 25,663.5 kg, silo_cold 27,190.3 kg, dP* **+1,526.8 kg** (+28.0 kg against the
  nominal +1,498.8). The drag term doubles (+3.507 -> +6.928 m/s, 31.8 -> 62.1 kg); the
  pad's drag loss is 51.9 m/s against 26.0 m/s at the nominal area. Doubling the drag
  area helps the assist slightly; the aero bound does not change the conclusion.

## Loads (flagged against the pad)

| quantity | pad | silo_cold | silo_instant | silo_hot_full | flag |
|---|---|---|---|---|---|
| felt axial g on the track [g0] | n/a | 3.996 (a + g_eff, full stack) | 3.996 | 3.996 | new load case |
| interface force on the track [MN] | 0 (hold-down: -2.04 MN tension at the end of the ramp) | 22.49 (constant) | 22.50 | 14.78 peak / 14.50 min | new load case |
| peak felt axial g in flight [g0] | 5.195 (MECO, 161.5 t) | 5.148 (MECO, 163.0 t) | 5.138 | 5.148 | below the pad |
| peak felt lateral g in flight [g0] | 6.4e-5 (kick) | 1.0e-4 (kick) | 1.7e-4 | 2.0e-4 | above the pad, negligible |
| peak q-alpha [Pa rad] (unconstrained) | 74.7 at 12.5 s (kick) | 129.9 at 0.5 s (kick at ignition) | 222.2 at 0 s | 251.3 at 0 s | **above the pad** (every silo variant) |
| max-Q [kPa] (unthrottled) | 37.19 | 31.24 | 30.95 | 32.51 | below the pad (RQ6) |
| track-normal g [g0] | 0 | 0 | 0 | 0 | vertical track |

- The load case the silo adds is 4.0 g0 felt by the full stack (573.9 t at silo_cold's
  P*) and a 22.5 MN interface force, 2.7 times the 8.23 MN vacuum thrust, at the moment
  the vehicle is heaviest (the pad's stack feels 1.36 g0 at release). No structural mass
  is charged for it: about 184 kg of P* per tonne of stage-1 dry mass (Caveats). In flight the peak felt g is lower than the pad's, because
  the silo vehicle carries more payload to MECO.
- q-alpha is above the pad's in every silo variant: the kick happens at 72 to 77 m/s at
  sea level (q about 3.1 to 3.6 kPa) instead of at 50 m/s. The values stay small
  (130 to 251 Pa rad) at the 3 g0, 100 m point but grow fast with the release speed
  (sweep below). The model has no alpha aerodynamics, so these are unconstrained loads,
  and every silo dP* is marked as an unconstrained upper bound for this reason.
- A hot start lowers the interface force (14.5 to 14.8 MN against 22.5 MN; the engines
  carry part of the stack) at a propellant cost (RQ2-ignition-timing-2d.md).

## Energy, power and facility length

| variant | drive energy [GJ] | [kWh] | electrical at 50 % [kWh] | peak drive power [GW] | interface force [MN] | facility incl. braking [m] |
|---|---|---|---|---|---|---|
| silo_cold | 2.249 | 624.7 | 1,249.5 | 1.725 | 22.49 | 160 |
| silo_instant | 2.250 | 625.1 | 1,250.2 | 1.726 | 22.50 | 160 |
| silo_hot_ramp_on_track | 1.834 | 509.3 | 1,018.7 | 1.134 | 22.50 / 14.79 | 160 |
| silo_hot_full | 1.459 | 405.4 | 810.8 | 1.112 | 14.78 / 14.50 | 160 |
| silo_hot_full_impinged | 2.220 | 616.7 | 1,233.4 | 1.696 | 14.78 / 14.50 | 160 |
| silo_sled_22t | 2.335 | 648.7 | 1,297.4 | 1.791 | 22.49 (drive force 23.35) | 160 |

- The facility is sized by power: 1.7 GW for 2.6 s. Energy is 2.25 GJ (0.62 MWh
  mechanical, 1.25 MWh electrical at the assumed 50 %). The numbers are about 5.7 %
  above the 1-D note's (2.128 GJ, 1.632 GW) because the stack is heavier (573.9 t
  against 542.6 t): 26.5 t from the gate vehicle's larger propellant load (569.1 t at
  P0, silo_failed's mass at release) and 4.8 t of payload above P0 (derived).
- Facility length: 100 m stroke + 60 m braking at 5 g0 = 160 m for every 3 g0, 100 m
  variant. The shaft's drag is not modelled (Caveats: under 0.1 % of energy and power).
- The 22 t carriage (MagLifter's about 4 %) changes nothing for the vehicle (same dP*,
  same interface force) and adds 3.8 % drive energy.

## The accel x stroke sweep (silo_cold; kick regime and q-alpha per point)

sweeps/sweep_1 (unpaired, against the pad). The kick regime depends on |v_rel| at the
first lit instant, 0.5 s after release: a 54.2 m/s release has slowed below 50 m/s by
then and rises vertically to 50 m/s before kicking.

| a [g0] | L [m] | V0 [m/s] | dP* [kg] | dP*/V0 [kg per m/s] | yardstick P*_pad [kg] | g + s [m/s] | kick regime (v at kick, m/s) | q-alpha [Pa rad] | max-Q [kPa] | M2 (diag.) | facility [m] | energy [GJ] | peak power [GW] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | 50 | 22.14 | +240.2 | 10.85 | 218.8 | -11.12 | vertical rise (50.0) | 68.6 | 35.91 | fail (-0.363) | 55 | 0.42 | 0.19 |
| 0.5 | 100 | 31.32 | +456.1 | 14.56 | 309.9 | +0.72 | vertical rise (50.0) | 63.1 | 34.89 | fail (-0.047) | 110 | 0.84 | 0.26 |
| 1 | 50 | 31.32 | +456.1 | 14.56 | 309.9 | +0.72 | vertical rise (50.0) | 63.1 | 34.89 | fail (-0.047) | 60 | 0.56 | 0.35 |
| 1 | 100 | 44.29 | +758.0 | 17.12 | 439.4 | +17.11 | vertical rise (50.0) | 55.4 | 33.61 | fail (0.186) | 120 | 1.12 | 0.50 |
| 0.5 | 300 | 54.24 | +987.5 | 18.21 | 539.1 | +29.42 | vertical rise (50.0) | 49.4 | 32.76 | fail (0.294) | 330 | 2.52 | 0.46 |
| 3 | 50 | 54.24 | +987.5 | 18.21 | 539.1 | +29.42 | vertical rise (50.0) | 49.4 | 32.76 | fail (0.294) | 80 | 1.12 | 1.22 |
| 5 | 50 | 70.02 | +1,347.7 | 19.25 | 697.9 | +48.54 | first lit instant (65.1) | 85.9 | 31.64 | pass (0.413) | 100 | 1.69 | 2.36 |
| 1 | 300 | 76.71 | +1,498.8 | 19.54 | 765.4 | +56.43 | first lit instant (71.8) | 129.9 | 31.24 | pass (0.449) | 360 | 3.37 | 0.86 |
| 3 | 100 | 76.71 | +1,498.8 | 19.54 | 765.4 | +56.43 | first lit instant (71.8) | 129.9 | 31.24 | pass (0.449) | 160 | 2.25 | 1.73 |
| 5 | 100 | 99.03 | +1,998.4 | 20.18 | 992.2 | +82.16 | first lit instant (94.1) | 393.2 | 30.20 | pass (0.545) | 200 | 3.38 | 3.34 |
| 3 | 300 | 132.86 | +2,740.1 | 20.62 | 1,339.3 | +119.06 | first lit instant (127.9), **unconstrained kick** | 1,293.3 | 29.41 | pass (0.647) | 480 | 6.76 | 2.99 |
| 5 | 300 | 171.52 | +3,563.3 | 20.77 | 1,741.3 | +157.88 | first lit instant (166.6), **unconstrained kick** | 3,408.8 | 29.57 | pass (0.734) | 600 | 10.16 | 5.81 |

- Every point beats its screening yardstick, from 1.10 times at 22 m/s to 2.05 times
  at 172 m/s (at the pad's payload); every point's screening status is ok.
- **Regime kink.** Points up to 54.2 m/s kick after a vertical rise to 50 m/s; from
  70.0 m/s they kick at ignition. The slope of dP* between neighbouring release speeds
  is 23.5, 23.3, 23.1 kg per m/s below the boundary, 22.8 across it (54.2 to 70.0 m/s)
  and 22.6, 22.4, 21.9, 21.3 above: no step is resolved at this sweep's resolution. The
  plan's warning is confirmed in kind (the regime changes between 54 and 70 m/s) but
  not as a visible kink in dP*.
- **Unconstrained kicks.** The two fastest points kick above checks.unconstrained_kick_mps
  (120 m/s): q-alpha 1,293 and 3,409 Pa rad, 17 and 46 times the pad's 74.7. Their dP*
  (+2,740 and +3,563 kg) assumes a free kick at q = 10.0 and 16.9 kPa (recorded at the
  kick, 0.5 s after release, at 127.9 and 166.6 m/s and 65 and 85 m altitude); they
  are labelled, not headline numbers. At 5 g0 and
  300 m the max-Q is no longer on the tropopause (RQ6).
- **Low-speed corner.** At 0.5 g0 and 50 m (22.1 m/s) the gravity + steering term is
  negative (-11.1 m/s): the cold start's 0.5 s coast and 2 s ramp in the air cost more
  than the short push's trajectory gain. Its +240.2 kg is still positive, but 14.4 of
  its 27.2 m/s margin (about 127 kg gross, derived pro rata; about 83 kg net of the
  pad's lighter liftoff, 35 %, the pad_instant pair) is the pad's hold-down burn, not
  the push.
- **M4 is not robust at the slow points.** At 22.1 and 31.3 m/s (sweep_1 run_0001,
  run_0002 and run_0004) the M4 verdict (blocking) changes within gamma* +/- 0.5 deg:
  the drag + steering share of the gain beyond the release speed is 0.472 / 0.219 at
  gamma*_ref (bound 0.5) but reaches 2.02 / 0.56 at one end of the range, a fail
  (sweeps summary.md). The pre-registered verdict at gamma*_ref stands. The beats at
  these low speeds rest mainly on the pad's pre-flight term.
- M2 (diagnostic) fails at every point below 55 m/s release speed; its verdict is not
  robust over gamma* +/- 0.5 deg at the two 54.2 m/s points (run_0003, run_0007). No
  blocking check fails at any point's gamma*_ref.

## Failed ignition (silo_failed)

The engines never light after the 76.707 m/s release. Unpowered coast with drag,
rotation and mu/r^2 from the shaft mouth:

| event | time after release [s] | altitude [m] | speed or offset |
|---|---|---|---|
| apex | 7.843 | 300.65 | 0.20 m west of the shaft axis |
| back at the mouth (ground event) | 15.689 | 0 | 76.60 m/s down, 0.40 m west |

- The 1-D note gave 300.27 m and 15.66 s (no drag, g_eff 9.798 m/s^2). The 2-D apex is
  0.38 m higher: the lower g_ref with rotation (9.772 m/s^2) raises it more than the
  drag loss (0.146 m/s) lowers it.
- With rotation the stack drifts 0.4 m west over the fall-back (Coriolis): not enough
  to clear a shaft of any practical bore, so the full 569.1 t stack (P0 payload; no search) falls back into the
  shaft at 76.6 m/s. Nothing in the model stops it; no abort is modelled. The carriage
  encounter (1-D: 60 m above the mouth at 14.8 s) is not re-computed in 2-D.

## Bridge: vehicle change versus model change

silo_bridge_2d_readme flies the 2-D model on the README-loads fork (the 1-D masses:
25.6 / 395.7 / 3.9 / 92.67 t, fairing 1.9 t; the fork's other inputs are the gate
fork's: 11 s staging coast, stage-2 A_e 8.6 m^2, the heating-rule fairing drop, the aero
block).

| quantity (silo_cold unless stated) | 1-D, README masses (RQ3-1d) | 2-D, README masses (bridge) | 2-D, gate masses (this note) |
|---|---|---|---|
| figure of merit | +69.64 m/s at stage-1 burnout; ideal-screening equivalent 621 kg | P* +1,394.4 kg (24,700.0 -> 26,094.4) | P* +1,498.8 kg |
| screening yardstick at 76.7 m/s | 685 kg | 684.8 kg (P0) / 738.7 kg (P*_pad) | 675.3 / 765.4 kg |
| pad_instant vs pad | +5.58 m/s | +90.9 kg | +83.1 kg |
| silo_instant vs pad | +84.77 m/s | +1,695.7 kg | +1,826.0 kg |
| anchor silo_instant vs pad_instant | +79.19 m/s (derived) | +1,604.8 kg (derived) | +1,742.9 kg (derived) |
| cold-start cost vs silo_instant | 15.12 m/s integrated (14.70 formula) | 32.30 m/s, 301.3 kg (derived) | 34.74 m/s, 327.1 kg (derived) |
| gravity + steering term | n/a (1-D) | +45.83 m/s (412.5 kg) | +56.43 m/s (511.9 kg) |
| back-pressure, drag, pre-flight terms | n/a / n/a / hold-down credit 5.40 m/s | +12.61 / +3.79 / +15.15 m/s | +13.57 / +3.51 / +14.41 m/s |

- **Model change (1-D to 2-D, same masses): 621 kg ideal-screening equivalent of the
  1-D burnout delta -> P* +1,394.4 kg (x2.25, a change of figure of merit as well as
  of model).** Most of it
  is what the 1-D figure of merit could not see: in 1-D the release speed arrives at
  burnout as speed plus altitude, and only the speed (plus a 2.2 m/s mu/r^2 altitude
  term) was scored; in 2-D the altitude and the flatter, faster MECO state lower the
  gravity and steering losses of the whole flight, and back-pressure and drag add
  about 16 m/s that 1-D did not model. Part of the change is also the fork's own
  inputs (coast, fairing rule, A_e), which apply to pad and silo alike.
- **Vehicle change (README to gate masses, same 2-D model): 1,394.4 -> 1,498.8 kg,
  +104.4 kg (+7.5 %).** The gate vehicle is heavier on propellant (410.9 / 107.5 t
  against 395.7 / 92.67 t) and makes more payload overall, so each m/s is worth more
  kg; the gravity + steering term is also 10.6 m/s larger.
- The bridge's attribution closes (residual below 1.7e-10 m/s) and every blocking check
  passes. Figures: RQ3-2d-bridge_pad_losses.png and RQ3-2d-bridge_silo_cold_losses.png
  (recorded runs at their own P*: gravity 1,372.9 against 1,337.0 m/s, back-pressure
  62.5 against 49.9 m/s, drag 29.9 against 26.0 m/s).

## What the 1-D preliminary numbers got right and wrong

Right:
- Exit speed, push time and felt g on the track (76.71 m/s, 2.607 s, 4.0 g0), the
  interface force, drive energy and peak power per tonne of stack (all scale with the
  stack mass; the 2-D stack is heavier: gate masses plus P*), the 60 m braking
  distance and the
  160 m facility.
- The shape of the ignition loss: it depends on the delay and the ramp or lag
  duration only through t_d + t_r/2 (ramp) and t_d + tau (lag) to within 7 %, and a lag
  costs as much as a ramp twice as long (RQ2-ignition-timing-2d.md).
- The hold-down credit exists and must be stated separately: the pad's 2.7 t clamped
  ramp is 14.4 m/s of delta-v, part of every after-release-lit variant's gain.
- Hot starts buy no exit speed under a prescribed acceleration and cut drive energy
  and peak power by the thrust work on the track.
- Failed ignition: apex about 300 m at about 7.8 s, back at the mouth at about 15.7 s
  at the exit speed.

Wrong (or incomplete):
- The payload value of the push. 1-D's 621 kg ideal-screening equivalent (not a
  payload result; below the README's 685 kg yardstick) becomes a P* gain of +1,394.4 kg
  on the same masses in 2-D, above the yardstick by a factor of
  about 2. The 1-D reading that the concept's own contribution is the exit speed less
  the ignition loss (62.0 m/s, 81 % of the exit speed) does not survive: in 2-D the
  cold start delivers 1.96 times the screening payload at the pad's payload.
- The cost of the startup. 1-D's 15.1 m/s ignition loss is, on the same README masses
  in 2-D (bridge), a 32.30 m/s (301.3 kg) payload cost, 2.14 times larger (34.74 m/s,
  327.1 kg on the gate vehicle): early speed is worth more than its face value in 2-D,
  in both directions.
- Hot full versus cold. 1-D put silo_hot_full 5.5 m/s behind silo_cold at burnout; in
  2-D they are within 10.2 kg (1,488.6 against 1,498.8 kg; -18.5 to +0.1 kg under the
  +/-10 % cases): the lighter vehicle at release recovers about a third of the delta-v
  it burned before release, enough to nearly match the cold start.
- Peak felt g in flight (5.71 g0 in 1-D with vacuum thrust from sea level) is 5.15 to
  5.20 g0 in 2-D.
- The failed-ignition drift and the Coriolis effect were not in 1-D (0.4 m west).

## M2 (diagnostic, the user's decision of 2026-09-30)

M2 compares the matched gravity term with the time-shift estimate over the pad's own
trajectory (estimate -105.06 m/s at 76.7 m/s, t_v0 = 18.21 s) and no longer blocks
findings. Verdicts:

- Named variants: pass everywhere it applies: silo_instant 0.730, silo_cold 0.449,
  silo_cold_lag 0.449, silo_hot_ramp_on_track 0.782, silo_hot_full and
  silo_hot_full_impinged 0.913, silo_sled_22t 0.449 (stage-1 ratios 0.137 to 0.608;
  every verdict robust over gamma* +/- 0.5 deg). pad_instant: n/a.
- Trigger study: pass at every v_k (0.4485, 0.4489, 0.4522, 0.4624).
- Sweep 1: fail at every release speed of 54.2 m/s or less (-0.363, -0.047, 0.186,
  0.294), pass from 70.0 m/s (0.413 to 0.734). Not robust over gamma* +/- 0.5 deg at
  sweep_1 run_0003 and run_0007 (both 54.2 m/s).
- Ignition sweeps (RQ2-2d): fail at t_ign 1 s with a 3 s ramp (0.262) and at lag tau
  2 and 3 s (0.258, 0.063); pass elsewhere. Not robust over gamma* +/- 0.5 deg at
  sweep_2 run_0006, run_0008 and run_0009.
- Aero bound: pass (0.468). Bridge: silo_instant 0.713, silo_cold 0.4225, pass.
- Sensitivity: every case passes, with ratios 0.395 to 1.047 (silo_cold 0.395 to
  0.525); silo_hot_full at stage-1 Isp -10 % exceeds the time-shift estimate (1.047:
  more gravity-loss saving than the estimate). silo_cold's stage-1 Isp +10 % case's M2
  verdict is not robust over gamma* +/- 0.5 deg (diagnostic only).

Reading: M2 fails exactly where the cold start's in-air startup is large compared
with the release speed (slow releases, long delays, long ramps or lags), as
docs/physics.md predicted. The time-shift estimator models neither the startup nor the
heavier vehicle at equal speed; its fails are not evidence of a bug, and its passes are
not proof of the gravity term.

## Findings stated plainly, including the ones against the hypothesis

- The reference silo (3 g0, 100 m, cold start 0.5 s + 2 s ramp) gains **+1,498.8 kg**
  over the pad (+5.75 %), sweep-optimized, unthrottled, free kick, on a vehicle that
  calibrates 14.3 % high; +1,345 to +1,667 kg under the +/-10 % cases; +1,526.8 kg with
  the doubled drag area; +1,498.1 kg best-vs-best over the kick trigger.
- It beats the README's ideal-screening estimate by a factor of about 2 (765.4 kg at the
  pad's payload). The beat is explained by the loss breakdown, not a bug: in the matched
  basis 46 % release speed at face value, 34 % lower gravity and steering loss (for
  silo_cold it appears after MECO at equal gamma*, a cancellation), 9 % the pad's
  hold-down burn (gross; 5.5 % net), 8 % back-pressure, 2 % drag (capacity basis:
  51 / 27 / 10 / 9 / 2 %; the shares depend on the basis); nothing unexplained beyond
  the search noise.
- **Against the hypothesis "every m/s of assist helps, as screened":**
  - Part of the headline is not the push: the pad's 2.7 t clamped ramp, a baseline
    convention the silo lit after release does not pay, accounts for 130.7 kg gross
    (8.7 %, the matched pre-flight credit) and 83.1 kg net (5.5 %, the pad_instant
    pair, which also counts the pad's lighter liftoff). Against a pad that lit at
    release (pad_instant) the cold silo gains +1,415.8 kg (derived: 27,553.2 -
    26,137.5).
  - No structural mass is charged for the 4.0 g0 full-stack load case (22.5 MN
    interface force, 2.9 times the pad's 1.36 g0 at release). At about 184 kg of P* per
    tonne of stage-1 dry mass (derived from the recorded +/-10 % cases), about 8.1 t of
    silo-only strengthening (37 % of the stage-1 dry mass) would cancel the whole gain.
  - The cold start gives back 327 kg against an instant start at release, 2.14 times
    the 1-D ignition loss on the same masses (bridge; 2.37 times the constant-g formula
    on the gate vehicle); with the 0.5 s delay and a 3 s lag it gives
    back 781 kg, 43 % of the instant start's 1,826 kg (RQ2-ignition-timing-2d.md).
    The gain depends as much on how quickly the engines reach full thrust after
    release as on the push.
  - The plan's time-shift estimate of the gravity-loss gain is optimistic, and at equal
    gamma* the cold start's in-air startup gives back all of the stage-1 gravity saving
    that the release produces when lit at release (about 25 m/s; with the pad's lighter
    liftoff the silo ends 2.5 / 1.6 m/s worse to MECO at the pad's / its own gamma*;
    docs/physics.md, "Time-shift mechanism", and the labelled launchsim probe). The
    +14.4 m/s before MECO in the matched split is the gamma* difference. For silo_cold
    the trajectory gain appears after MECO, from a MECO state 8.2 km higher and 106 m/s
    faster at the same gamma* and mass (22.9 m/s of it is lower stage-2 steering loss;
    launchsim probe), and it is the part a better (Phase 5) pad ascent could change.
  - At the slow corner of the sweep (0.5 g0, 50 m, 22 m/s) the trajectory term is
    negative (-11.1 m/s); about 127 kg of that point's +240 kg is the gross pre-flight
    credit (about 83 kg net, 35 %).
  - A full hot start does not pay: silo_hot_full is 10 kg behind the cold start
    (-18.5 to +0.1 kg under the +/-10 % cases: no gain, a tie within the sensitivity)
    and 337 kg behind the instant yardstick. Lit-on-the-carriage with the ramp ending
    at release (silo_hot_ramp_on_track, +1,733.8 kg) is the best physical variant here,
    235 kg ahead of the cold start, and it pays in 2.7 t burned on the track; it had no
    sensitivity run (not pre-registered).
  - Loads: 4.0 g0 on the full 574 t stack and a 22.5 MN interface force (2.7 times the
    vacuum thrust) are a new load case; q-alpha at the kick is above the pad's in every
    silo variant (130 to 251 Pa rad here, up to 3,409 Pa rad at 172 m/s); the model
    charges no structural mass for the axial load and no aerodynamic penalty or limit
    for the q-alpha.
  - A failed ignition returns the full stack to the shaft mouth at 76.6 m/s after
    15.7 s, 0.4 m from the axis.
- For the hypothesis: in the planar model an early vertical m/s is worth about 22.7 kg
  of payload on this vehicle (the release anchor), 2.3 times the screening's 10 kg, and
  for the cold start the marginal value (the slope of dP* between sweep points) stays
  between 22.4 and 23.5 kg per m/s from 22 to 99 m/s (21.9 and 21.3 kg per m/s up to 133
  and 172 m/s, where the kicks are unconstrained); the benefit is insensitive to
  the drag assumptions (+/-0.2 % for +/-10 % C_D; +1.9 % for the doubled area).
  (Carriage mass and drive efficiency cannot change the payload under the
  prescribed-acceleration drive, by construction; they move only energy and power, so
  they are no evidence either way.)
- These are preliminary: the drive is a prescribed acceleration, there is no throttle,
  no alpha aerodynamics, no optimal control, no structural penalty for the track load,
  and the vehicle misses calibration high.

## Open items raised by this note

- A pad convention released at T = W (instead of full thrust) would bound the
  hold-down share of every headline more tightly; not run (up to 83 kg).
- The pad's delta bracket cannot reach gamma* of 18 deg or more at v_k = 10 m/s (probe);
  irrelevant for the shipped v_k but a limit of the shared bracket at very low triggers.
- Phase 5 (optimal control) is needed to know whether the trajectory term (34 % of the
  headline) survives a pad ascent optimised beyond the gravity-turn family.
- silo_instant and silo_hot_ramp_on_track (now the best physical variant) have no
  +/-10 % sensitivity run; a future pre-registered experiment should add them.
- The structural cost of the 4.0 g0 full-stack load case (RQ1/RQ7) is not modelled; the
  184 kg per tonne above is a linear estimate, not a sized structure.
- An untested richer stage-1 guidance probe from a reviewer's independent integrator
  (constant angle of attack above the vertical rise; scratchpad
  p2/step27/review_phys/l2_*, l3_*, l4_*.txt; not launchsim, points not
  self-consistent) suggests both P* rise by about 0.9 t and the matched gap widens,
  which would also enlarge the calibration miss. Not cited as a result; Phase 5 must
  settle the direction of the trajectory term.

## Figures

Copied next to this note from results/silo_screening_2d/20260930T175743Z/plots/ (and
one sweep point from results/silo_screening_2d/20260930T182453Z/sweep_1/run_0012/plots/):

- RQ3-2d-pad_losses.png and RQ3-2d-silo_cold_losses.png: cumulative gravity, drag,
  steering and back-pressure losses from release (recorded runs at their own P*:
  gravity 1,492.0 against 1,450.4 m/s, back-pressure 63.1 against 49.6 m/s).
- RQ3-2d-pad_trajectory.png and RQ3-2d-silo_cold_trajectory.png: altitude against
  downrange to insertion.
- RQ3-2d-pad_angles.png and RQ3-2d-silo_cold_angles.png: gamma_rel and pitch; the pad
  rises vertically for 12.5 s, the silo kicks 0.5 s after release.
- RQ3-2d-silo_cold_felt_g.png: 4.0 g0 on the track, 0 in the 0.5 s coast, the ramp,
  5.15 g0 at MECO.
- RQ3-2d-silo_cold_track_forces.png and RQ3-2d-silo_cold_drive_power.png: the constant
  22.49 MN drive and interface force, and the drive power rising to 1.73 GW at release.
- RQ3-2d-silo_sled_22t_track_forces.png: the 22 t carriage raises the drive force to
  23.35 MN; the interface force stays 22.49 MN.
- RQ3-2d-silo_failed_trajectory.png and RQ3-2d-silo_failed_speed.png: the fall-back
  coast (apex 300.65 m, 0.4 m westward drift).
- RQ3-2d-sweep1_run_0012_angles.png: the 5 g0, 300 m point (171.5 m/s), whose kick at
  166.6 m/s is an unconstrained kick.
- RQ3-2d-bridge_pad_losses.png and RQ3-2d-bridge_silo_cold_losses.png (from
  results/silo_bridge_2d_readme/20260930T185034Z/plots/): cumulative losses of pad and
  silo_cold on the README-loads fork.
- RQ3-2d-trigger_run_0004_pad_angles.png (from
  results/guidance_trigger_2d/20260930T174950Z/sweep_1/run_0004__pad/plots/): the pad
  at v_k 120 m/s, a vertical rise to 120 m/s and a kick at 26.4 s (P* 26,012.5 kg,
  41.9 kg below v_k 50).
