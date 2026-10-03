# SP1 pre-registration: the offload experiments (step 8)

Written 2026-10-03 for SP1 step 8 (docs/phases/SP1-fuel-offload-planar.md, section 7) and
committed with the two experiment files before any run of them. Step 9 runs them from a
clean committed tree and writes docs/findings/RQ1-fuel-offload-2d.md against this note.
A change to either file after the pre-registration commit is an amendment: its own
commit, logged as a decision, this note kept and extended, never rewritten.

## 1. What is registered

| File | Vehicle | What it declares |
|---|---|---|
| experiments/silo_offload_2d.yaml | generic_f9_class_2d.yaml (gate, mass set C; calibrates +14.3% high, accepted 2026-09-30) | pad baseline; variants silo_cold, silo_hot_ramp_on_track, silo_cold_200m; an offload block with 11 cases, pad controls of three modes, 8 sensitivity arms and an energy block; 5 sweeps of 20 points, each solving a stage-1 case |
| experiments/silo_offload_2d_readme.yaml | generic_f9_class_2d_readme_loads.yaml (mass set A, README loads; calibrates +8.33%, inside the band) | pad baseline; variant silo_cold; an offload block with the headline case and its stage-1 pad control |

Commands for step 9, in this order, from the repository root:

    uv run python -m launchsim run experiments/silo_offload_2d.yaml
    uv run python -m launchsim sweep experiments/silo_offload_2d.yaml
    uv run python -m launchsim run experiments/silo_offload_2d_readme.yaml

Nothing in this step ran these files: they were resolved, the preflight
(`sim.check_resolved`) and the run-name checks (`results_io.check_result_names`) passed,
and tests/test_config_planar.py checks the properties below. No search, solve or flight
of them was made.

## 2. The headline is not unknown

Stated plainly: the headline quantity was already measured during validation. The step 5
and step 6 slow tests solve silo_cold's stage-1 offload at the pad's payload capacity on
this vehicle at the shipped search budget: x* = 41,262.9 kg (10.04% of the 410.9 t
stage-1 load, 7.96% of the 518.4 t total; test and shipped budgets agree to 0.0003 kg;
docs/physics.md, "Figures of merit (planar)", validation measurement). The step 6
decomposition splits its 228.2 m/s of ideal delta-v (2.755 times the ideal-screening
estimate) mainly into release speed 76.7, gravity 124.8, back-pressure 13.3 and the pad's
hold-down burn 14.4 m/s (229.2 m/s together); drag, steering and fairing take back 1.0
m/s (-0.877, -0.065 and -0.024 m/s; docs/physics.md, "Cross-vehicle decomposition",
Measured). The handoff probe read about 41.1 t off by hand.

So the headline case re-measures a known number inside the full design (pad controls,
independent verification, paired pad, decomposition, penalty rows, sensitivity arms, the
bridge, the sweeps); it does not discover it blind. What this pre-registration fixes in
advance is the design around the number and how each result will be read, not ignorance
of the number. It is expected to reproduce to grams (the test and shipped budgets agreed
on it to 0.0003 kg). A headline that moves away from 41,262.9 kg by more than the
resolution against a re-solved P_ref (about 3.8 kg: 1.3 kg from P_ref's tolerance, 0.25
kg and the gamma* allowance at its 2.30 kg cap, since the validation's gamma*_ref is on
record only to 0.01 deg; section 3, "Resolution") at the same budget and code is a
reproducibility question to answer before any finding.

## 3. Comparison basis

- Reference payload P_ref: the full-load pad's payload capacity P* on the same vehicle,
  orbit (200 km circular, 28.5 deg, due east) and shared blocks (one budget id; guidance
  sweep-optimized per run; results called "sweep-optimized").
- Offload x*: the largest evaluated stage-1 (or stage-2, or equal-fraction both-stage)
  propellant removal with residual propellant m_res >= 0 when the assisted run flies
  P_ref; tanks partly filled, every dry mass unchanged unless a row adds an assumed one.
  Different vehicles, same payload and orbit (`OFFLOAD_COMPARISON_BASIS`).
- Stage 1 is the only headline, quoted gross; its pad control is a consistency test of
  the solver. Stage-2 and both-stage offloads are quoted net of their pad controls and
  labelled a property of the vehicle model (D-SP1-10).
- Sensitivity arms: the assisted run and the pad perturbed alike (a run parameter, drive
  efficiency, on the assisted run only); each arm's P_ref is the perturbed pad's P*; no
  verification search (`OFFLOAD_SENSITIVITY_BASIS`).
- Sweep points: the experiment pad's P_ref, verified; no paired pad, pad control or arms.
  Their offload runs are not written (sweep_index.csv columns and checks only; SP1 step
  7, deviation 5), so no sweep point records its offload solve's gamma*_ref
  (sweep_index.csv's gamma_star_rad column is the point's own payload search at its own
  P*, not the solve at x*).
- Calibration: every number carries the gate fork's +14.3% miss; the bridge is the one
  robustness row on a fork inside the band.
- Resolution. A difference between two solves' x* is read against R = R_P + 0.25 kg + G,
  fixed here from documented constants and recorded outputs only:
  - s, the slope |dm_res/dx| (docs/physics.md, "Propellant offload at fixed payload"):
    0.039 kg of m_res per kg of x near silo_cold's x* and 0.031 near x = 0 on the pad
    (the stage-1 pad control). Solves whose x* lies near silo_cold's (the headline,
    silo_cold_200m_s1, sweep 2's points, the 40 m points of sweeps 4 and 5) use 0.039. A
    solve whose x* lies well below it has an unmeasured slope between the two and uses
    0.031, the larger allowance: the 200 m points of sweeps 4 and 5, lit about 2.8 s
    later than silo_cold.
  - R_P, P_ref's own tolerance. Between two solves at the same P_ref (the sweep points
    with each other, sweep 4 against sweep 5, silo_cold_200m_s1 against the headline)
    the offset it induces is common to both and cancels: R_P = 0. Against a re-solved
    P_ref (the headline against the validation measurement, an arm on its own perturbed
    pad, a comparison across the run and sweep commands when their summaries print
    different P_ref): R_P = final_payload_xtol_kg / s = 0.05 kg / 0.039 = 1.3 kg on
    silo_cold (1.6 kg at the pad's 0.031). The stage-1 pad control's consistency bound is
    the code's own final_payload_xtol_kg / s, with s from the control's logs (section 8).
    The sweep command re-solves the pad with the same code and budget as the run
    command, so its P_ref is expected to be the run command's.
  - 0.25 kg, each solve's resolution apart from gamma*: brentq's xtol of 0.05 kg of x and
    the warm-start-dependent LTG convergence inside the acceptance box (about 2 g of
    m_res, 0.05 kg of x) in each of the two, read with margin as 0.25 kg, five times the
    0.051 kg by which the 10x-tightened budget moved silo_cold's x* (the test and shipped
    budgets agree on it to 0.0003 kg).
  - G, the gamma* allowance. Each solve refines its gamma*_ref in search mode, which is
    noise-limited and resolves gamma* to about w = 0.07 deg (docs/physics.md, "Virtual
    propellant"). A gamma*_ref dg off the vertex of m_res(gamma*) lowers x* by
    0.5 k dg^2 / s, with k = 36.6 kg/deg^2 the curvature measured on the pad control
    (docs/physics.md, "Propellant offload at fixed payload"; assumed the same at
    silo_cold's x*): 0.05 kg at 0.01 deg, 0.19 kg at 0.02 deg and 2.30 kg at 0.07 deg (s
    = 0.039; 2.89 kg at 0.07 deg with s = 0.031). No output records the vertex, so G is a
    bound, not a correction. With |dg| <= w for each solve, 0.5 k |dg1^2 - dg2^2| / s <=
    0.5 k w^2 / s always, and, when the two solves share one vertex (dg1 - dg2 is then
    the recorded gamma*_ref difference), also <= k w |dgamma*_ref| / s, 65.7 kg per deg
    at s = 0.039 (0.66 kg per 0.01 deg). So G = min(65.7 kg/deg x |dgamma*_ref|, 2.30
    kg) for two solves that share one vertex and both record gamma*_ref:
    silo_cold_200m_s1 against the headline, whose flights after release are identical,
    each with `solve.gamma_star_rad` in the run command's metrics.json `offload` record.
    G = 0.5 k w^2 / s otherwise, 2.30 kg near silo_cold's x* and 2.89 kg for the 200 m
    pair of sweeps 4 and 5: any sweep point (none records its solve's gamma*_ref), event
    against closed form (different flights), and the validation measurement (its
    gamma*_ref, 22.99 deg, is on record only to 0.01 deg).

  So R is at most 2.55 kg at the same P_ref (3.14 kg for the 200 m pair of sweeps 4 and
  5) and about 3.8 kg against a re-solved P_ref.
  A difference within R_P + 0.25 kg reads as equal. One between that and R is consistent
  with no difference at the refine's gamma* resolution and is reported as unresolved, not
  as evidence either way. One beyond R is a real difference or, where none is expected,
  a defect to find before any finding, whatever the gamma*_ref values. For scale, the
  scatter seen so far is well inside w: the step 5 pad control's and pad search's
  gamma*_ref lay 0.001 and 0.005 deg from the fitted vertex.

## 4. The cases and what each is for

All on silo_cold unless stated (3 g0 net, 100 m vented vertical stroke, exit 76.707 m/s at
the mouth, massless carriage, stage 1 lit 0.5 s after release with the 2 s ramp; the same
resolved run as silo_screening_2d's silo_cold).

| Case | Mode | What it is for |
|---|---|---|
| silo_cold_s1 | stage 1, paired pad, sensitivity arms | The headline. The paired pad (the pad flying the same offload) separates the head start from the lighter, higher thrust-to-weight stack (SP1 step 6, deviation 5) |
| silo_cold_s2 | stage 2 | Stage-2 offload, net of its pad control |
| silo_cold_both | both (the same fraction of each load) | Both-stage offload, net of its pad control |
| silo_cold_s1_s2pre2t | stage 1 after 2 t taken from stage 2 | One frontier point of the both-stage trade (2 t: the phase file's choice) |
| silo_cold_s1_dry+2t, +4t, +8.1t | stage 1, assumed stage-1 dry mass added to the assisted run only | Structural penalty rows (D-SP1-04): assumptions, not a structural model. 8.1 t is the linear break-even of silo_cold's payload gain (RQ3-2d: 1,498.8 kg at about 184 kg per tonne, an extrapolation) |
| silo_cold_fix5pct, silo_cold_fix10pct | 5% and 10% of the stage-1 load imposed (20,545 and 41,090 kg) | The plain "reduce stage-1 propellant by X" knob; each reports its own P* against P_ref; also a cross-check of the solve from the other side |
| silo_hot_ramp_s1 | stage 1 on silo_hot_ramp_on_track | The ramp started on the carriage 2 s before release (94.6 m deep, 17.9 m/s), full thrust at release |
| silo_cold_200m_s1 | stage 1 on silo_cold_200m | The same release speed over twice the stroke at 1.5 g0 net (felt about 2.5 g0 instead of 4.0) |
| pad controls (pad__offload_stage1, _stage2, _both) | each solve mode on the pad | D-SP1-10: the pad's own offload in each mode |
| bridge silo_cold_s1 | stage 1 on the README-loads fork, paired pad, pad control | D-SP1-13: the robustness row against the calibration miss |

Sensitivity arms (8): the headline re-solved at +/-10% of stage-1 dry mass, stage-1
Isp_vac, cd_scale and drive efficiency (CLAUDE.md's headline sensitivity). The two
drive-efficiency arms change only the electricity (the push is prescribed), so they reuse
the nominal solve. The experiment-level sensitivity block lists no run of its own
(`of: []`, which the schema allows when only the arms are wanted): silo_cold's payload
sensitivity on these parameters is already in silo_screening_2d. A reporting artefact to
expect: the summary's payload Sensitivity section will print the code's "no sensitivity
block declared" note, whose text does not distinguish an empty `of` from a missing
block; the arms are in the offload section's Sensitivity table.

## 5. The sweeps and what each is for

Each sweep names the stage-1 case built on its own variant; at every point the case is
rebuilt on the point's run, solved at the pad's P_ref and verified.

| Sweep | Axis | Points | Question |
|---|---|---|---|
| 1 | assist.stroke_m on silo_cold (3 g0) | 25, 50, 100, 200, 300 m (exit 38.35-132.86 m/s) | How the offload grows with silo depth at fixed acceleration |
| 2 | assist.stroke_m on silo_cold_200m (exit speed fixed) | 50, 100, 200, 300 m (6, 3, 1.5, 1 g0 net) | Whether only the release speed matters: same offload expected at every point, with lower felt g and peak power and a longer facility |
| 3 | ignition.stage1.at_depth_m on silo_cold | 100, 75, 50, 25, 0 m (ramp start 0, 1.304, 1.844, 2.258 s after push start; 0 m at release) | Hot starts by depth: 100 m lights at the shaft floor |
| 4 | ignition.stage1.at_height_m by event on silo_cold | 10, 40, 100, 200 m | Cold starts lit later and later on the coast |
| 5 | ignition.stage1.at_height_m by closed form on silo_cold | 40, 200 m | The closed form against the event, point for point |

Checks made on the file (tests/test_config_planar.py): every depth lies within the 100 m
stroke; every height lies at least 100 m below the drag-free apex v_e^2 / (2 g_eff) =
301.06 m, so far below the flown apex (about 300.65 m on the gate fork, 300.61-300.69 m
over payload 0-30 t and C_D +/-10%; SP1 step 4, deviation 4) and the no_ignition band
between them; the closed-form heights convert to 0.540 and 3.302 s after release; the
fixed-exit-speed points keep silo_cold's exit speed exactly.

Notes fixed here:

- At 25 and 50 m (sweep 1) the drag-free coast has slowed to v_e - 0.5 s x g_eff = 33.5
  and 49.4 m/s by the ignition, below v_k = 50 m/s, so those points rise vertically
  under thrust to v_k before the kick; 100, 200 and 300 m kick at ignition. The kick
  regime changes inside sweep 1, as it did between 54 and 70 m/s in RQ3-2d's accel x
  stroke sweep, where no kink in dP* was resolved.
- At 300 m (sweep 1) the kick comes above `checks.unconstrained_kick_mps` (120 m/s): the
  model has no angle-of-attack aerodynamics, so that point is an upper bound.
- At 200 m (sweep 4 and 5) the drag-free coast has slowed to about 44 m/s, below v_k =
  50 m/s, so that point rises vertically under thrust to v_k before the kick, as the
  pad does; 10, 40 and 100 m kick at ignition. The kick regime changes inside the sweep.
- exhaust_impingement_fraction 0 (sweep 3 and silo_hot_ramp_s1): the whole rocket thrust
  on the track is credited against the drive force (lower drive energy and power), and
  nothing models the exhaust in the shaft (back-pressure, heating, the carriage in the
  plume). That favours hot starts. The push is prescribed, so the fraction moves neither
  the trajectory nor the offload (RQ3-2d: silo_hot_full and silo_hot_full_impinged fly
  identically); only the energy and the track forces would change.

## 6. Choices fixed by this pre-registration

1. **Unrounded exit speed.** silo_cold_200m and sweep 2 state their push by
   exit_speed_mps: 76.70717046013364, the Python repr of math.sqrt(2 * 3 * 9.80665 * 100)
   (g0 = 9.80665 m/s^2), which parses back to the same double, at least 12 significant
   digits as asked. The phase file proposed the rounded 76.71 m/s, which is 0.0028 m/s
   faster, about 1.5 kg of offload at the probe's rate (41.1 t over 76.7 m/s): six times
   the 0.25 kg within which two solves at the same P_ref read as equal, and a systematic
   offset that would hide inside the 2.30 kg gamma* allowance between sweep points
   (section 3, "Resolution") rather than show as scatter. With the unrounded value
   silo_cold_200m releases at exactly silo_cold's speed and is compared with silo_cold
   directly, and sweep 2's points are comparable with silo_cold and with each other.
   Sweep 2's 100 m point has a derived acceleration one ulp below silo_cold's 3 g0
   (29.419949999999993 against 29.41995 m/s^2), so it agrees with silo_cold to
   integrator noise (about 5e-8 relative; SP1 step 2, deviation 1), not bit for bit.
2. **Closed-form heights 40 m and 200 m**, two of the event heights, so the two methods
   compare point for point; the measured miss of the closed form on the gate fork is
   -3.8 mm at 40 m and -0.11 m at 200 m (docs/physics.md, "Silo model"; SP1 step 3,
   deviation 2). How the difference will be read is in section 7.
3. **Names.** Case names are short enough that every derived run name stays within 64
   characters (the longest, an Isp arm, has 58). Each sweep names the case built on its
   own variant (silo_cold_s1, or silo_cold_200m_s1 for sweep 2); at a point the case's
   `of` is replaced by the point's run either way.
4. **Fixed cases without a paired pad**: they are compared with the unchanged pad only.
5. **Energy inputs** (silo_offload_2d only): RP-1 123.5 t (stage 1) and 32.3 t (stage 2),
   the LOX/RP-1 split of the gate vehicle file's own propellant source (Espace &
   Exploration No. 39 via Wikipedia, Falcon 9 Full Thrust); RP-1 lower heating value
   43.03 MJ/kg, MIL-DTL-25576E (2006) net heat of combustion 18,500 Btu/lb minimum by
   ASTM D240 x 2.326 kJ/kg per Btu/lb = 43,031 kJ/kg (docs/phases/inputs/
   2026-10-02-source-rp1-heating-value.md). A specification minimum, written down to
   0.01 MJ/kg: both slightly lower the heat of the removed RP-1, so neither favours the
   assist. The ratio of that heat to the push's electricity is not an efficiency; it
   leaves out LOX production, refining and transport, generation and storage losses and
   the energy embodied in the silo.
6. **The bridge has no energy block**: the schema does not require one, and the
   README-loads fork has no sourced fuel split.

## 7. How each result will be read

These are expectations stated before the run, labelled estimates where they are. None is
a target: a different result is reported as it is.

**Headline (silo_cold_s1).** Expected to reproduce the validation measurement (section 2).
Supports the hypothesis if it ends ok with every blocking check passing, its
verification within tolerance and its offload explained by a closing decomposition. It is
expected to beat the ideal-screening estimate at its release speed by about 2.75 times
(step 6); CLAUDE.md's screening rule then requires the decomposition to explain the beat
(mainly gravity loss and the pad's hold-down burn), otherwise it is a bug.

**Paired pad.** The pad flying the same offload falls short of P_ref; the case's margin
over it is the head start at equal stack mass. If that margin is small against the
offload, most of the offload comes from the lighter stack's thrust-to-weight, not from the
head start, and the note says so.

**Penalty rows (undercut test).** To first order each tonne of stage-1 dry mass takes about
184 kg from the 1,498.8 kg payload margin the offload spends (RQ3-2d), so x* is expected
near x*(0) (1 - dm / 8.1 t), about 5 t of offload per tonne: about 31 t at +2 t, about
21 t at +4 t and about zero (no_offload, or a small x*) at +8.1 t, the payload break-even
by construction (estimates, a linear extrapolation). An offload that does not survive
the +8.1 t row means that a silo needing that much stage-1 strengthening (37% of the
22.2 t dry mass) replaces no propellant; an offload gone already at +2 or +4 t, faster
than the linear estimate, undercuts the headline further. The structural mass the 4 g0
full-stack push needs is unknown (no structural model; TODO.md B-004, README Phase 3),
so the note reports the rows beside the
headline and the rate at which the offload erodes per tonne.

**Fixed cases.** Expected P* - P_ref (estimates): the offload not taken, (x* - x) s /
|dm_res/dP|, with s = 0.031-0.039 kg of m_res per kg of x (the pad near x = 0 to
silo_cold near its x*; section 3) and |dm_res/dP| = 0.993 (silo_cold at x*;
docs/physics.md, "Propellant offload at fixed payload"). Several hundred kg above at 5%
(about 650-810 kg: 20.7 t of offload not taken) and a few kg above at 10% (about 5-7 kg:
10% is 172.9 kg less than the validated x*; the handoff probe read +7 kg at 41.1 t). A
fixed case on the other side of P_ref from what the solved x* implies by more than the
verification tolerance (`checks.search_final_flag_rel` x P_ref, about 2.6 kg) is an
inconsistency between the fixed and solved paths, resolved before any finding.

**Stage 2, both, and the frontier point.** The recorded marginal value of stage-2
propellant on the gate pad is about zero or slightly negative (adding 975 kg of real
stage-2 propellant lowered m_res by 15.3 kg at a fixed gamma* of 22 deg; docs/physics.md,
"Virtual propellant"; measured at another point and in the adding direction). Expected
from it (estimates): the stage-2 pad control removes a large amount, so the silo's
stage-2 offload net of it is small and ill-conditioned (risk 1); the both-stage solve may
remove more total tonnes than the stage-1 headline, because its stage-2 share rides about
free; the frontier case's stage-1 offload stays close to the headline's. The phase file
(section 5.3) states that total tonnes are maximised by a stage-1-only offload, so "both"
cannot beat the headline. That statement does not follow from this marginal value; it is
tested here, not assumed. Whatever the outcome, stage 1 stays the only headline, and a
large stage-2 or both-stage number is reported net of its pad control as a property of the
vehicle model's stage-2 sizing and guidance, not as the silo's offload.

**Sweep 1 (depth at 3 g0).** Expected to grow monotonically with the stroke (release speed
38-133 m/s). A fall with a deeper shaft would undercut "every m/s of assist helps" and
needs the decomposition to explain it. The 25 and 50 m points kick after a vertical rise
to v_k and the others at ignition (section 5), so a change of slope between 50 and 100 m
is read against that regime change, not as a defect; monotonic growth is still expected
across it (RQ3-2d resolved no kink in dP* there). The drive energy and peak power grow
with the stroke and are reported beside each point; the 300 m point is an
unconstrained-kick upper bound.

**Sweep 2 (depth at a fixed exit speed; undercut test).** The flight after release is the
same at every point (same release state, same ignition 0.5 s after release; the guidance
clocks run from the ignitions, the kick deadline from stage 1's and the linear-tangent
law from stage 2's, so nothing after release sees the longer push). The offload is
therefore expected to be the same at every point to the resolution of a difference at
the same P_ref (section 3, "Resolution": every point solves at the experiment pad's
P_ref, whose own offset cancels; no point records its solve's gamma*_ref, so G = 2.30
kg and R = 2.55 kg). Read on the spread, the largest x* less the smallest of the four:
within 0.25 kg, flat to the solves' own resolution; from 0.25 to 2.55 kg, flat within
the refine's gamma* resolution, reported as such, with no dependence on depth claimed
or excluded at that size; above 2.55 kg, not physics in this model but a defect to find
before any finding. For scale, the rounded 76.71 m/s would have moved x* by about 1.5 kg
(section 6), inside R, which is why the unrounded speed is used. Expected beside it
(closed forms): felt load (a + g_eff) / g0 = 7.0, 4.0, 2.5
and 2.0; peak electrical power per kg of vehicle (a + g_eff) v_e / eta = 10.5, 6.0, 3.8 and
3.0 kW/kg; electricity per kg (v_e^2 / 2 + g_eff L) / eta = 6.9, 7.8, 9.8 and 11.7 kJ/kg
(the push also lifts the vehicle through the stroke, so the same offload costs 71% more
electricity at 300 m than at 50 m); facility 110, 160, 260 and 360 m. Lower g and power
for more energy and length is the trade the note reports.

**Sweep 3 (ramp start by depth; undercut test).** Expected from RQ3-2d's payload results
(silo_hot_ramp_on_track +1,733.8 kg and silo_hot_full +1,488.6 kg against silo_cold's
+1,498.8 kg): starts on the carriage near full thrust at release (around 94.6 m, between
the 100 m and 75 m points, where silo_hot_ramp_s1 also sits) give the largest offload,
falling as the ramp start moves toward the mouth; 0 m (lit at release) above silo_cold
(lit 0.5 s later). Hot starts that lose to lighting at the mouth would undercut the
preference for hot starts and need the decomposition to explain them. With impingement
0 and no shaft plume model, a win for hot starts is an upper bound on their merit.

**Sweeps 4 and 5 (ramp start by height).** Expected to fall as the ramp start moves up the
coast: 10 m (lit about 0.13 s after release) above silo_cold (0.5 s, about 37 m) above
40, 100 and 200 m.

The event and closed-form points at the same height differ only through the closed
form's height miss (section 6): it lights 3.8 mm low at 40 m and 0.11 m low at 200 m,
that is earlier than the event, by 0.053 ms at 40 m (0.540041 against 0.540094 s after
release) and 2.51 ms at 200 m (3.30170 s by the closed form, 2 h / (v_e + sqrt(v_e^2 -
2 g_eff h)), against the event's 3.30421 s; docs/physics.md, "Silo model"). An earlier
ignition is worth more, so closed form minus event is expected positive. Its size
(estimates): the coast alone costs g_eff per second of delay, but the measured cost of a
delayed ignition is about 2.2 to 2.4 g_eff. silo_instant and silo_cold differ by about
1.5 s of impulse lag (0.5 s unlit plus half the 2 s ramp), and their matched attribution
delta-v margins at P_ref by 34.7 m/s on the gate fork (+199.990 against +165.248 m/s;
docs/findings/RQ3-silo-screening-2d.md, section (a)), 23.2 m/s per s, and by 32.3 m/s
on the README-loads fork (+187.2 against +154.9 m/s;
results/silo_bridge_2d_readme/20260930T185034Z/summary.md), 21.5 m/s per s. Of the two
differences, 31.5 and 29.1 m/s are in gravity and steering together (only their sum is
read; docs/physics.md, "Screening-beat rule (2-D)"), so the lower speed is paid for
again on the way up. A change in the assisted run's delta-v margin converts to offload
at (m_e / c2) / s: m_e = m_d2 + P_ref = 30,054.4 kg at insertion and c2 = 348 s x g0
give 8.81 kg of m_res per m/s, over s = 0.039 about 226 kg of offload per m/s at
silo_cold's x* (about 250 averaged over the solve: 41,262.9 kg over the +165.248 m/s by
which silo_cold's full-load margin at P_ref exceeds the pad's), and up to 284 kg per m/s
at s = 0.031 for the 200 m points' lower x*. The decomposition's 180.8 kg per m/s of
ideal delta-v (41,262.9 kg over 228.2 m/s) is not that rate: it leaves out that the
lighter stack also loses less. That gives about +12 to +17 kg at 200 m (+5.5 to +7 kg
at g_eff alone; more if the vertical rise below v_k at that point costs more) and about
+0.1 to +0.3 kg at 40 m. Each pair solves at the same P_ref, but the two flights differ
and neither point records its solve's gamma*_ref, so G takes its cap: R = 3.14 kg at
200 m (s = 0.031) and 2.55 kg at 40 m (s = 0.039; section 3, "Resolution"). The
readings cover every outcome:

- 200 m, closed form minus event: from +3.14 to +30 kg as expected (central estimate
  +12 to +17 kg); from -3.14 to +3.14 kg the sign is unresolved, reported as below the
  estimate beside the two points' decompositions; below -3.14 kg (the wrong sign beyond
  the resolution) or above 30 kg (about twice the estimate's top) investigated before
  any finding.
- 40 m: within +/-2.55 kg the two points read as equal (the expected +0.1 to +0.3 kg lies
  inside R); beyond it, of either sign, investigated before any finding.

**Bridge (undercut test).** RQ3-2d's bridge found silo_cold's payload gain nearly the same
fraction of P* on both forks (1,394.4 / 24,700.0 = 5.65% on README loads, 1,498.8 /
26,054.4 = 5.75% on the gate). The bridge's stage-1 offload is read as x* / m_p1 beside
the gate's, with the ideal delta-v change c1 ln(m0 / (m0 - x*)) of each. Expected to agree
within about 10% relative (about twice the 5.5% by which the gate pad's P*, 26,054.4 kg,
exceeds the README fork's, 24,700.0 kg). A larger disagreement means the headline
percentage depends on the vehicle masses more than the calibration difference suggests,
and the note puts that beside the headline. A reporting artefact to expect: the bridge
summary's calibration caveat will say the README-loads fork has no calibration record on
file (`plots.CALIBRATION_RECORDS` lists the gate fork only); its calibration is the
readme_loads case of docs/findings/CAL-f9-leo-2d.md (24,700.0 kg, +8.33%), which the
findings note states.

**Sensitivity.** The headline is quoted with the range of its eight arms beside it; an arm
that ends reference_failed, no_offload or with a failing decomposition is reported as such.

## 8. Checks that block findings

Blocking, by the code (the summary's blocked-findings lines):

- any run or comparison that is bug_suspect: the per-run closure, loss identity and
  insertion checks and the blocking screening checks (M2 is diagnostic, user decision of
  2026-09-30);
- an offload case's or arm's cross-vehicle decomposition whose residual exceeds
  `checks.closure_tol_mps` (1e-5 m/s): bug_suspect; and a paired-pad comparison that is
  bug_suspect;
- a stage-1 pad control that fails its consistency test (0 <= x_pad <= final_payload_xtol_kg
  / s for an ok control; a no_offload control passes only as the resolution effect,
  -0.05 kg < m_res(0) < 0; step 5 measured m_res(0) = -0.0016 kg). The step 7 test grid
  missed by 0.128 kg with the refine capped at 3 iterations, so the shipped run must show
  it passing.

Blocking the headline by this pre-registration (flags the code reports without blocking):
the headline case's `offload_verify_mismatch` (its independent payload search off P_ref by
more than about 2.6 kg), `offload_nonmonotone`, or a capped gamma* refine; and a
reference_failed pad. Each is explained before the number is quoted, and a headline with
a suboptimal gamma* is quoted as a flagged lower bound (risk 2). KI-006: M4 (blocking) and
M2 (diagnostic) over gamma* +/- 0.5 deg are reported for the offload runs, every point
where they fail disclosed.

Reported beside every number, never a gate: max-Q of each offloaded run against the pad's
(the handoff probe showed 38.4 against 37.2 kPa; unthrottled, no constrained variant),
peak felt g and interface force on the track, facility length with braking, the push's
electricity and peak power.

## 9. What nothing here measures

No structural mass for the 4 g0 push (the penalty rows are assumptions); no throttle, so
no max-Q-constrained offload; a prescribed-acceleration drive with a massless carriage and
no shaft air or plume; tanks partly filled with the mixture ratio kept and no ullage,
residuals or centre-of-gravity effects; the planar model and the calibration miss.

## 10. Runtime estimate (serial)

Measured costs used: a bare searched planar run about 12-25 s, an offload solve with its
verification about 90-110 s on a loaded machine (step 5 measured 89 s), a stage-1 pad
control ending no_offload about 30 s (step 5 and 7 notes); and the wall clock of the
shipped 2026-09-30 runs, which include comparisons, file writes and plots: 38 s per
searched run in the calibration re-run (16 runs in 612 s), 54 s in guidance_trigger_2d's
paired sweep (8 runs in 435 s), and 59-81 s per point in silo_screening_2d's sweeps. Below,
S is a searched run with its comparison and writes (25-55 s), V a solve with its
verification (90-110 s) and O a solve alone (V less a bare search, 65-100 s).

`run experiments/silo_offload_2d.yaml`:

| Item | Count | Cost each | Low [s] | High [s] |
|---|---|---|---|---|
| pad and the three variants | 4 | S | 100 | 220 |
| sensitivity runs (`of: []`) | 0 | | 0 | 0 |
| pad control stage 1 (no_offload expected, no verification) | 1 | about 30 s | 30 | 30 |
| pad controls stage 2 and both (verified if ok) | 2 | V | 180 | 220 |
| solved cases with verification | 9 | V | 810 | 990 |
| paired pad of the headline | 1 | S | 25 | 55 |
| fixed cases (own payload search, one matched evaluation) | 2 | S | 50 | 110 |
| sensitivity arms on vehicle parameters (perturbed pad, solve, no verification) | 6 | S + O | 540 | 930 |
| sensitivity arms on drive efficiency (nominal solve reused) | 2 | about 0 | 0 | 10 |
| writing about 19 run directories with plots | | about 2.5 s | 50 | 50 |
| total | | | 1,785 (30 min) | 2,615 (44 min) |

The stage-2 and both-stage solves (silo and pad) may need more bracket expansions than a
stage-1 solve (risk 1); at twice the cost they add about 6-7 min. Estimate: 30-50 min.

`sweep experiments/silo_offload_2d.yaml`: the pad (S) and 20 points, each a searched run
with its comparison, directory and plots (25-80 s) plus the stage-1 solve with its
verification (V): low 25 + 20 x 115 = 2,325 s (39 min), high 55 + 20 x 190 = 3,855 s
(64 min).

`run experiments/silo_offload_2d_readme.yaml`: pad, silo_cold and the paired pad (3 S),
the stage-1 pad control (about 30 s) and one solved case (V): 195-305 s, about 3-6 min.

All three: about 70-120 min serial. Neither experiment command exceeds about 90 minutes
on this estimate, so nothing is trimmed (the phase file's 30-minute threshold, risk 10,
is passed by both; the brief for this step says not to trim for it, and the phase file
records the departure as step 8 deviation 6 for the user to accept). Machine speed
varies about 3 times under load; under a heavier load than the measured one the sweep
could pass 90 minutes. `--no-plots` would shorten both commands without changing a
number, but the findings need the plots.

## Amendment 1 (2026-10-03, before any run)

Made in SP1 step 8a, before either file was run, and committed with that step's code.
The two experiment files are unchanged (byte for byte as in the pre-registration commit
c2a4cf0), and so is every case, sweep, budget and solve: the step changes reporting code
only (src/launchsim/results_io.py, summary.py, plots.py and replay.py), so that what the
run writes is accurate. No pre-registered criterion or reading changes: every verdict of
sections 3, 7 and 8 is taken as written, on the branch assignment section 3 gives.
Sections 1 to 10 stay as written. Where a sentence there describes what the outputs will
show (the two "reporting artefacts to expect" of sections 4 and 7, "no sweep point
records its solve's gamma*_ref" in sections 3 and 7, and the summary caveat that
section 7 says is tested, not assumed), it describes the reporting code of c2a4cf0;
this section says what the outputs show now.

1. **The payload Sensitivity note of an empty `of`** (section 4). silo_offload_2d's run
   summary no longer prints "no sensitivity block declared" in its payload Sensitivity
   section. It prints "(no run has payload sensitivity cases: the sensitivity block's
   `of` lists no run; its params perturb the offload block's sensitivity arms, reported
   in the section "Propellant saved at fixed payload"; C_D: ...)", and with
   `--no-offload` "... which --no-offload skipped with the block" in place of the
   pointer, or, with `run --variant` naming a variant other than silo_cold (not the
   registered command), "... none of which ran (their case's variant did not run)",
   since that offload section prints no arms table. The arms and the offload section
   are unchanged. The bridge declares no
   sensitivity block and keeps "no sensitivity block declared", which is true of it.
2. **The calibration record of the README-loads fork** (section 7, "Bridge").
   `plots.CALIBRATION_RECORDS` now holds generic_f9_class_2d_readme_loads: P* 24,700.0
   kg against 22,800 kg, +8.33%, inside the +/-10% band (case readme_loads of
   docs/findings/CAL-f9-leo-2d.md; 24,700.013 kg in tests/data/calibration_record.json).
   The bridge summary's calibration caveat therefore says that the fork "carries 24,700
   kg in its calibration run against the published 22,800 kg, +8.3% high, a documented
   calibration result (docs/findings/CAL-f9-leo-2d)" instead of "no calibration record
   on file"; the replay page of a bridge run says that the fork lies within the gate
   band; the animation footnote reads "This vehicle calibrates +8.3% high on payload,
   inside the +/-10% band (docs/findings/CAL-f9-leo-2d)." The gate fork's caveats are
   unchanged word for word.
3. **Sweep points record their solve's gamma*_ref and flags** (TODO.md KI-028; section
   3, "Sweep points" and "Resolution"). Each offload case of a sweep point now writes two
   more sweep_index.csv columns, appended after step 7's twelve (which keep their names
   and order): `<case>.solve_gamma_star_rad`, the solve's own gamma*_ref [rad], refined
   in search mode at X1 (the root of the first search in x) and held for X2 and the
   final search at x*, to 12 significant digits (the point's `gamma_star_rad` column
   stays its own payload search at its own P*), and `<case>.n_flags`, the number of the
   case record's flags (its solve's and its recorded run's). The sweep summary's Checks
   section lists the flags themselves, one line per point and case, with the status of a
   solve that did not end ok or no_offload (a search_failed solve has no flags of its
   own). The case is silo_cold_s1 in sweeps 1, 3, 4 and 5 and silo_cold_200m_s1 in
   sweep 2.
4. **The stage-2 caveat no longer states what section 7 tests** (section 7, "Stage 2,
   both, and the frontier point"). The caveat list of every offload summary
   (`summary.OFFLOAD_CAVEATS`) ended with "total tonnes are maximised by a stage-1-only
   offload, so 'both' cannot beat the headline", the phase file's section 5.3 statement
   that step 8 corrected and that section 7 tests rather than assumes. It now ends "a
   stage-1-only offload is not assumed to maximise the total tonnes ('both' may remove
   more, its stage-2 share riding about free), and stage 1 stays the only headline
   either way", and it places the measured marginal value of stage-2 propellant on the
   gate vehicle (it said "this vehicle", which the bridge summary would have printed of
   the README-loads fork, where nothing measured it). Section 7's reading of the
   both-stage case and the headline rule are unchanged.

**How the readings use the recorded gamma*_ref.** Section 3's rule for G has two
branches: G = min(65.7 kg/deg x |dgamma*_ref|, 2.30 kg) for two solves that share one
vertex of m_res(gamma*) and both record gamma*_ref, and G = 0.5 k w^2 / s otherwise
(2.30 kg at s = 0.039, 2.89 kg at s = 0.031). Section 3 assigns the pairs to the
branches by name, and sections 3 and 7 state the readings on that assignment:
silo_cold_200m_s1 against the headline in the first branch; every sweep point, every
event-against-closed-form pair and the validation measurement in the second. The sweep
points on the headline's flight after release (sweep 2's four points and sweep 1's 100 m
point) were put in the second branch only because none recorded its gamma*_ref; the
event-against-closed-form pairs and the other sweep points are there for their different
flights as well, and the validation measurement because its gamma*_ref is on record only
to 0.01 deg. This amendment moves no pair: every verdict keeps its registered branch.
Where the recorded values allow it, they add a second reading, reported beside the
registered one and never replacing it.

- **Sweep 2 (the flatness test): the verdict at the cap, the recorded gamma*_ref
  beside it.** The verdict is section 7's, on the spread (the largest x* less the
  smallest of the four) against R = 2.55 kg: within 0.25 kg, flat to the solves' own
  resolution; from 0.25 to 2.55 kg, flat within the refine's gamma* resolution, reported
  as such; above 2.55 kg, a defect to find before any finding. Beside it the findings
  note gives the recorded gamma*_ref of the two points that set the spread, their
  difference dgamma*_ref [deg] and R_rec = 0.25 kg + min(65.7 kg/deg x |dgamma*_ref|,
  2.30 kg), section 3's first branch. That branch holds under section 3's own
  assumptions: the four points share one vertex (they fly the same flight after release,
  section 7, to integrator noise of about 5e-8 relative, section 6), k is the same at
  each, and |dg| <= w for each. R_rec is at most 2.55 kg and reaches it when the two
  recorded values differ by 0.035 deg (2.30 / 65.7) or more. A spread from R_rec to
  2.55 kg stays unresolved, as section 7 reads it; the note adds that the recorded
  gamma*_ref difference does not account for it under those assumptions and examines
  the assumptions (the shared vertex, the same k) before quoting the spread. It is not
  read as a defect on that ground.
- **Sweeps 4 and 5 (the sign test): the cap, with no second reading.** Both points of
  each pair now record gamma*_ref, but they fly different flights (the closed form
  lights 0.053 ms earlier at 40 m and 2.51 ms earlier at 200 m; section 7), so their
  m_res(gamma*) curves need not share a vertex. The recorded difference bounds the
  gamma* term only through a common vertex (section 3: only then is dg1 - dg2 the
  recorded difference), and no output records either vertex. So G stays
  0.5 k w^2 / s: R = 3.14 kg at 200 m (s = 0.031) and 2.55 kg at 40 m (s = 0.039), and
  section 7's readings of both pairs are unchanged. The two points' recorded gamma*_ref
  and flags are reported beside each pair; they do not enter R.
- **Other pairs.** silo_cold_200m_s1 against the headline keeps section 3's first branch
  (both recorded by the run command). A sweep point on the headline's flight (sweep 1's
  100 m point, sweep 2's points) against silo_cold_s1 or silo_cold_200m_s1 keeps the cap
  for its verdict (section 3, "any sweep point"; across the run and sweep commands with
  R_P as section 3 gives it) and gets the first-branch reading beside it, as in sweep 2.
  Pairs on different flights (the other points of sweeps 1, 3, 4 and 5 against each
  other and against these) and the headline against the validation measurement get no
  second reading.
- **Flags.** A sweep point's flags (a capped gamma* refine, `offload_nonmonotone` and
  `offload_verify_mismatch` among them) are now on disk and are disclosed beside the
  point's reading. They block nothing that section 8 does not already block: its
  headline-blocking flags apply to the headline case, and a sweep point's bug_suspect
  decomposition blocks findings, as before.
