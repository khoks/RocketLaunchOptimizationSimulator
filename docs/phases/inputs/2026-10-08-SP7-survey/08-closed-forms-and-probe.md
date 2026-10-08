<!-- Record of SP7 step 0: read-only survey 08-closed-forms-and-probe (closed forms checked, and a labelled planning probe), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# SP7 step 0, survey 08: closed forms checked, and a first-order planning probe of the structural increment

Summary. All closed forms that SP7's tests will use match numerical integration far tighter than the 1e-10 asked for. They are the linear motor (a force ramp from rest, then the force limit, then the power limit, on a vertical or a horizontal track), the dynamic load factor (DLF) for a step and for a linear ramp, the load drop at release, the adiabatic trapped column under a sealing carriage, and constant-deceleration braking. The worst relative error over all of them was 2.5e-13. The first-order station sizing probe of brief 5.3 option B uses placeholder coefficients, the recorded pad envelope and the recorded silo_cold_s1 push. Treated as quasi-static, it puts the stage-1 membrane increment at 1.4 to 3.5 t, about 2.0 to 2.6 t at the central coefficients. The elements that take most of it are the RP-1 tank wall (axial buckling: the LOX column and everything above it at 4 g0), the lower LOX wall and the bottom domes (hoop from the 4 g0 hydrostatic head), the intertank and the aft skirt. The load-entry and interface hardware add k x 20.8 MN, which is 0.4 to 2.1 t at k = 20 to 100 kg/MN. A DLF on the push multiplies the structural part: x1.12 at DLF 1.1, x1.36 at 1.3 and x2.2 to 2.7 at 2.0 (the undamped value for constant_accel's infinite-jerk start). Placed on SP1's penalty-row curve, with dm re-evaluated at the offload it produces, the expected stage-1 offload is 12 to 33 t quasi-static (30% to 80% of the 41.26 t headline). It is 2 to 29 t with DLF 1.3, and 0 to 20 t with DLF 2.0. **The range covers most of the offload, and its two biggest drivers are the DLF (rise time against structural period) and the interface-hardware coefficient k, not the material allowables.** No probed case keeps the full headline: the smallest increment, about 1.9 t, still takes about 8 t off it. These numbers are a labelled planning probe. They are not a finding and not a target, and must be disclosed as such in the pre-registration.

## 1. Scope, inputs and what was run

Note: REPORT.md was not written. The harness refused report files ("Subagents should return findings as text, not write report files"). This message is the report.

Facts (read at HEAD 22c62e9, clean tree; nothing in the repository was written):

- Brief: docs/phases/SP7-structural-mass-push-load.md, section 2 (lines 59-129), 5.2 (315-347), 5.3 (349-367), 5.5 (379-402), 5.7 (413-456; the closed forms at 424-437), 5.9 (478-498), 6 (533-769), 10 (903-953; Q7 at 916, R1 at 922).
- Vehicle: configs/vehicles/generic_f9_class_2d.yaml: stage-1 dry 22.2 t (46), propellant 410.9 t, 287.4 LOX + 123.5 RP-1 (47); stage 2 4.0 + 107.5 t (58-59); fairing 1.7 t (69); 3.66 m body (84). P_ref 26,054.396 kg (pad payload, from the run's masses).
- Records (read-only): results/silo_offload_2d/20261003T112934Z/pad/timeseries.csv (3,073 stage-1 samples, -2 s hold to MECO at 151.33 s), silo_cold_s1/timeseries.csv (54 ASSIST samples, 531,091.5 kg stack, felt 3.99648 g0, interface 20.8146 MN), silo_cold/timeseries.csv (573,853.2 kg, interface 22.4905 MN). The pad's recorded loads: release 0.9965 g0 (HOLD), 1.362 g0 one sample after, max-Q 37.19 kPa at 65.75 s (2.04 g0, 392.3 t), MECO 5.19547 g0 at 161,454 kg.
- `felt_axial_g` in flight is (T - D cos psi)/m in g0 (src/launchsim/metrics_planar.py:461).
- Penalty rows (docs/findings/RQ1-fuel-offload-2d.md:296-299): dm 0, 2, 4, 8.1 t give x* 41.263, 32.285, 22.876, 1.980 t.
- The offload is split by stage only (src/launchsim/vehicle.py:613 `offload_split_kg`, 653 `with_offload`). The code has no per-tank masses, so the probe's LOX and RP-1 split at the mixture ratio (287.4/123.5) is its own assumption.
- `constant_accel` states "infinite jerk at push start and release" (src/launchsim/assist/constant_accel.py:224) and "shaft vented (no air column)" (222). Its braking distance is v^2/(2 a_brake) with a_brake the stated deceleration (166-168).

Scripts and outputs (all under C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/08-closed-forms-and-probe/):

| Script | What | Output |
|---|---|---|
| a1_linear_motor.py | ramp, force and power phases against DOP853 (rtol 1e-13), vertical and horizontal; interface-force signs | a1_out.txt |
| a1b_energy.py | drive work as an integrated state against 1/2 M v^2 + M g s | a1b_out.txt |
| a1c_hold_release.py | ramp with a hold released after F = M g | a1c_out.txt |
| a2_dlf.py | DLF table: closed form, undamped SDOF, 2% damped SDOF, envelope; release drop | a2_out.txt |
| a3_a4_air_brake.py | trapped column: closed-form work against quad; bound; air ahead of the vehicle; braking | a3_a4_out.txt |
| b_probe.py | the sizing model (vectorized); b_probe_v1_slow.py is the first loop version and gives the same envelope (9,244 kg) | |
| b_checks.py | primitives against hand values; stations, sample stride and knockdown iterations converged | b_checks_out.txt |
| b_driver.py | envelope masses, diagnostics, sets, OAT, corners, DLF, comparison pushes, dm(x), placement, release check | b_out.txt |
| b_range.py | corner sets x k x DLF: coupled placement and the full-load bound | b_range_out.txt, b_range_console.txt |
| b_quick.py | a one-case timing run | |

## 2. Part A1: linear motor closed forms (facts)

Model: constant mass M, constant g, no drag. Drive F = min(F_ramp(t), F_max, P_max / v) with F_ramp = F_max t / t_r.

- **Ramp from rest (the stack rests on its bottom stops).** The stack leaves the stops at t0 = M g t_r / F_max, when F = M g. For t0 <= t <= t_r:
  a = (F_max/(M t_r)) (t - t0), v = F_max (t - t0)^2 / (2 M t_r), s = F_max (t - t0)^3 / (6 M t_r).
  At the ramp end, v_r = (F_max t_r / (2M)) (1 - M g/F_max)^2 and s_r = (F_max t_r^2 / (6M)) (1 - M g/F_max)^3.
- **Force-limited phase**, from (t_r, v_r, s_r): a = F_max/M - g, v = v_r + a (t - t_r), s = s_r + v_r (t - t_r) + a (t - t_r)^2/2, up to v_c = P_max/F_max at t_c = t_r + (v_c - v_r)/a.
- **Power-limited phase (vertical).** Brief 5.7's t(v) and s(v) (lines 429-430) were re-derived by hand: integrate v dv / (g (v_inf - v)) and v^2 dv / (g (v_inf - v)), with v_inf = P_max/(M g). They are confirmed. Horizontal: v^2 = v_c^2 + 2 P (t - t_c)/M and v^3 = v_c^3 + 3 P (s - s_c)/M, confirmed.
- **Validity conditions** (inferred from the algebra; tests should state them): F_max > M g, which is the same as v_c < v_inf; and v_r < v_c, so that the ramp ends before the power limit. If the ramp is still running at v = P/F_ramp, the corner falls inside the ramp and these forms do not cover it.
- **Numerical check.** Five vertical cases (F_max = 2.5 to 6 M g0, v_c = 40 to 70 m/s, t_r = 0 to 0.5 s, M = 531,091 kg, g = 9.772) and two horizontal cases. Worst relative error 2.5e-13 over ramp, force-phase and power-phase t(v) and s(v) (a1_out.txt). Drive work integrated as a state equals 1/2 M v^2 + M g s to 3e-15 (a1b_out.txt). The ramp costs little: at F = 4 M g0 and v_c = 50 m/s, t_r = 0.2 s delays the corner by 0.125 s (s_c 42.466 against 42.438 m).
- **Hold released later**, at t_h > t0: v = (k/2)(t^2 - t_h^2) - g (t - t_h) and s = (k/6)(t^3 - t_h^3) - (k/2) t_h^2 (t - t_h) - (g/2)(t - t_h)^2, with k = F_max/(M t_r). Error 8e-15 (a1c_out.txt). Releasing at t_h > t0 brings back an acceleration step of k t_h - g: 0.50 g0 at t_h = 1.5 t0 and 1.99 g0 at t_h = 3 t0, with t_r = 0.5 s and F_max = 4 M g0. That step carries its own DLF of 2.
- **Does the vehicle lift off the carriage before F = M g? Cold start: no.** At rest the interface force is m_v g (5.19 MN for the headline stack, about 5.2 MN). Once moving it is m_v (a + g) = m_v F/M > 0, so the vehicle stays on the carriage through the whole push. The stack (vehicle and carriage) leaves the stops exactly at F = M g.
  Hot start: at rest the interface force is m_v g - T, and 7.607 MN of sea-level thrust exceeds the 5.21 MN vehicle weight, so the vehicle lifts off the carriage unless it is held. Moving, it is (m_v F - (m_c + f_imp m_v) T)/M, which agrees with brief 5.7 line 420. Separation follows if m_v F < m_c T, for example F < 0.315 MN with a 22 t carriage. A linear-motor hot start therefore needs a stated hold-down or carriage-latch rule (recommendation).

## 3. Part A2: dynamic load factor (facts)

The SDOF is x'' + 2 zeta w x' + w^2 x = w^2 f(t), with f a step or a ramp to 1 over t_r.

- Closed form, undamped: DLF = 1 + |sin(pi t_r/T)| / (pi t_r/T), and 2 for a step. There is no overshoot during the ramp: x <= t/t_r there. The worst difference between the undamped SDOF and the closed form is 3.4e-8 (sampling-limited). With 2% damping the step gives 1 + exp(-zeta pi / sqrt(1 - zeta^2)) = 1.9391.
- Table (each cell: closed / undamped SDOF / 2% damped SDOF / envelope min(2, 1 + T/(pi t_r))):

| t_r [s] | T = 0.05 s | T = 0.1 s | T = 0.2 s | T = 0.33 s |
|---|---|---|---|---|
| 0 | 2.000/2.000/1.939/2.000 | 2.000/2.000/1.939/2.000 | 2.000/2.000/1.939/2.000 | 2.000/2.000/1.939/2.000 |
| 0.05 | 1.000/1.000/1.018/1.318 | 1.637/1.637/1.598/1.637 | 1.900/1.900/1.846/2.000 | 1.963/1.963/1.904/2.000 |
| 0.1 | 1.000/1.000/1.017/1.159 | 1.000/1.000/1.018/1.318 | 1.637/1.637/1.598/1.637 | 1.856/1.856/1.804/2.000 |
| 0.2 | 1.000/1.000/1.015/1.080 | 1.000/1.000/1.017/1.159 | 1.000/1.000/1.018/1.318 | 1.496/1.496/1.466/1.525 |
| 0.5 | 1.000/1.000/1.011/1.032 | 1.000/1.000/1.014/1.064 | 1.127/1.127/1.107/1.127 | 1.210/1.210/1.186/1.210 |
| 1.0 | 1.000/1.000/1.007/1.016 | 1.000/1.000/1.011/1.032 | 1.000/1.000/1.014/1.064 | 1.010/1.010/1.018/1.105 |

- **Release (load drop from n to about 0 over t_r).** The minimum response is -(DLF - 1) times the static load: an undamped instantaneous drop swings to a full tension of n times the static compression, -0.939 with 2% damping. For the central probe walls (b_out.txt, "RELEASE CHECK") the tension thickness this needs (2.5 to 5.5 mm) stays below the push-sized walls (6.4 to 13.6 mm). The liquid is the problem: the LOX bottom's hydrostatic head at the push is 0.982 MPa, so an undamped instantaneous drop swings the bottom pressure to -0.53 MPa absolute, and the column would separate from the dome. This is an undamped bound (inferred). It is a reason to ramp the release as well as the start, or at least to list the risk.
- Recommendations. Charge the envelope bound min(2, 1 + T/(pi t_r)), not the exact |sinc|. The exact form drops to 1.000 whenever t_r/T is an integer (the cancellation above), so picking t_r = T on an uncertain T would be tuning toward the assist. Damping alone lifts those cells only to 1.007-1.018. Under `constant_accel` as modelled (infinite jerk), the honest DLF is 2 (1.94 at 2% damping). The push's dynamic part is n - 1 (from 1 g0 at rest), so n_peak = 1 + DLF (n - 1): 3.996, 4.296, 4.895 and 6.993 g0 for DLF 1.0, 1.1, 1.3 and 2.0. **Above DLF 1.400 the push's n_peak exceeds MECO's 5.195 g0**: (5.19547 - 1)/(3.99648 - 1) = 1.400. Stage 2, the interstage and the payload would then also need strengthening, which the probe does not charge, so its DLF 2.0 rows are low (inferred).

## 4. Part A3 and A4: air column and braking (facts)

- **Trapped column.** A carriage seals a bore of area A at gap s0 above a closed bottom, with atmosphere above it. Then p(s) = p0 (s0/(s0+s))^gamma, F = (p_atm - p) A (resisting, 0 <= F < p_atm A), and W(L) = p_atm A L - p0 A s0/(gamma - 1) [1 - (s0/(s0+L))^(gamma-1)]. Against quad the worst relative error is 3e-16. The bound for a 3.7 m bore is A = 10.752 m^2, p_atm A = 1.0895 MN, matching the README's 1.1 MN.
- Headline push (100 m, mechanical drive work 578.2 kWh, which is 1,156.4 kWh of electricity at eta = 0.5 and matches RQ1's row):

| s0 [m] | Work [MJ] | Work [kWh] | Share of drive work | F at the exit [MN] | F / 20.81 MN | p at the exit [Pa] | T at the exit [K] |
|---|---|---|---|---|---|---|---|
| 0.5 | 107.7 | 29.9 | 5.2% | 1.089 | 5.2% | 60 | 35 |
| 1 | 106.7 | 29.6 | 5.1% | 1.088 | 5.2% | 158 | 45 |
| 5 | 99.4 | 27.6 | 4.8% | 1.074 | 5.2% | 1,428 | 85 |
| 10 | 92.1 | 25.6 | 4.4% | 1.052 | 5.1% | 3,530 | 110 |
| 50 | 60.5 | 16.8 | 2.9% | 0.855 | 4.1% | 21,764 | 186 |

  - At small s0 the gas cools to 35-110 K, and its sound speed (118-211 m/s) is only 1.5 to 3 times the carriage's 76.7 m/s. The uniform-pressure adiabat is therefore only first order at the end of the stroke: the face pressure would be lower and the force nearer the bound (inferred). The p_atm A bound holds regardless.
  - The force acts on the carriage, below the vehicle. Under `constant_accel` it changes only the drive force and energy. Under a force-limited drive it lowers the acceleration, and with it the interface force, the felt g and the exit speed (brief 5.7 line 421).
- **Air ahead of the vehicle in a snug shaft** (order of magnitude). A 10-60 m column (132-790 kg) is pushed out of the mouth. Its momentum flux at 76.7 m/s is rho v^2 A = 77 kN, plus m a = 4-23 kN at 3 g0: 0.4-0.5% of the 20.81 MN interface force. This acts on the vehicle, so it does reach the interface force. It is about 5 times RQ3-2d's free-air drag estimate of 17 kN at the exit (docs/findings/RQ3-silo-screening-2d.md:77-81).
- **Braking at a constant total deceleration a**: d = v^2/(2a), t = v/a, carriage energy 1/2 m_c v^2. At 76.707 m/s: 3 g0 gives 100.0 m and 2.607 s; 5 g0 gives 60.0 m and 1.564 s; 10 g0 gives 30.0 m and 0.782 s. A 22 t carriage carries 64.7 MJ (18.0 kWh); a massless one carries none. Integrating the ODE at 5 g0 matches to 1e-12.
  - Convention to settle (recommendation). On a vertical track gravity supplies g_eff of the deceleration, so the brake itself supplies a - g_eff (39.26 m/s^2 at 5 g0). It absorbs 1/2 m_c v^2 - m_c g_eff d (51.8 MJ for 22 t at 5 g0). The current closed form treats a_brake as the total deceleration (constant_accel.py:166-168). A modelled braking phase must say which of the two it uses.

## 5. Part B: probe model and placeholders (stated assumptions)

PLANNING PROBE, not a finding and not a target. Every coefficient is a placeholder, to be replaced by sourced values in step S0.

- **Layout** (assumed). Bottom to top: load ring at the stage base; aft skirt of length h_dome + 1.0 m; RP-1 tank; an unpressurized intertank of 2 h_dome + 0.5 m; LOX tank (LOX above RP-1, separate domes). Tank cylinders are sized from the propellant volumes with 3% ullage, LOX 1141 kg/m^3 and RP-1 820 kg/m^3. r = 1.83 m. Domes are 0.707 ellipsoidal (height 1.294 m, area 17.08 m^2, crown coefficient 0.7071 p r/sigma) or hemispherical (0.5 p r/sigma). Central lengths: LOX cylinder 22.93 m, intertank 3.09 m, RP-1 cylinder 13.02 m, aft skirt 2.29 m; 42.6 m from the aft ring to the LOX dome crown, plus the interstage.
- **Masses.** 2.0 t of unmodelled stage-1 mass sits at the top (interstage, fins); the rest of the unmodelled mass and the engines (9 x 470 kg) sit at the base and load no sized element. LOX and RP-1 are on board at the mixture split. The upper stack is stage 2 full, the fairing and P_ref.
- **Loads** (the brief's): tank-wall compression N = (mass above, excluding this tank's liquid) n g0 - p_u pi r^2; intertank and skirt N = (everything above) n g0; hoop p_u + rho n g0 h; bottom domes from the apex pressure; one ullage pressure for every case; drag left out of the envelope (central; a sensitivity checks it). The envelope is the maximum over every 5th pad stage-1 sample plus the first three and the last. That changes dm by 0.04 kg against every sample, and 800 stations or 80 knockdown iterations change it by less than 0.01 kg (b_checks_out.txt).
- **Modes.** t = max(hoop FS p r/sigma_ult, tension, compressive yield, buckling, 2 mm).
  - Monocoque: FS N/(2 pi r) = gamma(t) 0.6052 E t^2/r with gamma = 1 - 0.901 (1 - exp(-sqrt(r/t)/16)). The probe's r/t is 130-915, inside the formula's usual range.
  - Stiffened, in the stated form: the smeared equivalent thickness t_mono(N)/k, k = 2 or 3.
  - "pinf": pressurized walls never buckle. This is a limiting bracket, not a model, standing in for the SP-8007 pressure increment (Delta gamma), whose curve I could not source in this survey. Places to check in S0: SP-8007 (1968) and NASA/SP-8007-2020/REV 2 (the shellbuckling.com preliminary revision PDF was too large to fetch).
- Central coefficients: E 76 GPa, nu 0.3, rho 2700 kg/m^3, sigma_ult 450 MPa, FS 1.4, p_u 3.5 bar gauge in both tanks.
- Primitives checked by hand (b_checks_out.txt): hoop at 1 MPa is 5.6933 mm; half-spheroid area 1.6232 pi r^2; gamma(r/t = 500) = 0.3217; buckling residual below 6e-10. The LOX apex hydrostatic head at 3.996 g0 is 1.0899 MPa full (1.0706 MPa cylinder-equivalent, m n g0/A).
- Thrust structure: under aft-ring entry it carries only the engines in the push, so it adds nothing. Alternative entry: see section 7.

## 6. Part B: envelope plausibility (labelled calibration, not validation)

Model envelope masses of the sized elements against stage-1 dry minus engines (22,200 - 4,230 = 17,970 kg):

| Buckling form | LOX wall | Intertank | RP-1 wall | Aft skirt | Domes | Sum | Share of 17,970 kg |
|---|---|---|---|---|---|---|---|
| monocoque | 4,638 | 845 | 2,705 | 642 | 413 | 9,244 | 51.4% |
| stiffened 2x | 2,399 | 420 | 1,327 | 319 | 413 | 4,878 | 27.1% |
| stiffened 3x | 2,129 | 279 | 984 | 213 | 413 | 4,018 | 22.4% |
| pinf | 2,125 | 839 | 978 | 638 | 413 | 4,993 | 27.8% |

That leaves 8.7 to 14.0 t for the interstage, thrust structure, legs and fins, frames, joints and welds, plumbing, COPVs, avionics and margins. I have no sourced breakdown to compare against (S0's job). Nothing was tuned toward a target.

Where the envelope comes from (b_out.txt, "DIAGNOSTICS"):

- The LOX, intertank and RP-1 walls are governed by axial buckling at MECO (5.195 g0, stage-1 tanks empty). The bottoms of the tank walls in the stiffened cases are governed by hoop at liftoff (t = 0.2 s, 1.363 g0).
- The aft skirt is governed at t of about 97-101 s (2.7-2.8 g0). That is where (mass above) x n peaks, at 7.7-7.9 MN, not at MECO.
- The bottom domes are governed at liftoff: 0.72 MPa at the LOX apex.
- Max-Q drag in the envelope changes dm by -1 to -2 kg, because max-Q governs nothing here.

## 7. Part B: the increment, element by element (facts of the probe)

Central monocoque, 3.5 bar, quasi-static, silo_cold_s1 (x = 41.26 t):

| Element | Envelope [mm] | Envelope load | Push requirement [mm] | Push load | Increment [kg] |
|---|---|---|---|---|---|
| RP-1 wall | 6.6-6.7 | 3.95 MN | 10.9 | 12.39 MN | 1,710 |
| Aft skirt | 9.0 | 7.88 MN | 13.6 | 20.40 MN | 327 |
| Intertank | 8.8 | 7.49 MN | 12.2 | 15.91 MN | 323 |
| LOX bottom dome | 2.89 | | 5.36 | 1.33 MPa apex pressure | 114 |
| RP-1 bottom dome | 2.05 | | 3.13 | | 50 |
| LOX wall | 6.6 | buckling | 7.24 at the bottom station | hoop | 27 |
| Top domes | | | | | 0 |
| **Total** | | | | | **2,550 (11.5% of the 22.2 t dry)** |

The LOX wall's push compression (2.0 MN) stays below its envelope (3.8 MN at MECO); its increment is hoop at the bottom station only. Stage 2 and the interstage carry 4.0 g0 against MECO's 5.2 g0, so the push sizes neither, which confirms brief 5.2's first look.

Buckling form x ullage pressure (sigma_ult 450 MPa, FS 1.4), dm_struct in kg:

| Form | 2.5 bar | 3.5 bar | 4.5 bar | Dominant element and mode |
|---|---|---|---|---|
| monocoque | 2,373 | 2,550 | 2,979 | RP-1 wall buckling (62-67%) |
| stiffened 2x | 1,852 | 2,248 | 2,373 | LOX lower-wall hoop and RP-1 wall buckling, in equal shares |
| stiffened 3x | 1,932 | 1,972 | 1,804 | LOX lower-wall hoop (50-55%) |
| pinf | 2,409 | 2,234 | 2,080 | LOX hoop (41-48%), then RP-1 wall, intertank and skirt |

- The bottom domes add a fixed 148-164 kg, whatever the buckling form.
- The ullage pressure's effect changes sign with the form. Relief lowers the envelope and the push compression by the same p_u A. In the buckling mode t grows as sqrt(N), so the gap between push and envelope grows as both fall. The hoop increment, on the other hand, rises with p_u only where hoop governs both cases. **Low and high sets therefore cannot be built by picking each coefficient's direction on its own; they must be computed for each buckling form** (recommendation for S0 and S2).

One-at-a-time sensitivities (b_out.txt; change in kg around the 3.5 bar central of each form):

| Coefficient | Monocoque (2,550) | Stiffened 2x (2,248) | Stiffened 3x (1,972) |
|---|---|---|---|
| sigma_ult 400 / 520 MPa | +130 / -59 | +205 / -278 | +214 / -188 |
| FS 1.25 / 1.5 | -165 / +114 | -229 / +141 | -190 / +123 |
| p_u 2.5 / 4.5 bar | -177 / +429 | -397 / +125 | -40 / -168 |
| aft skirt +1 m / -0.5 m | +142 / -71 | +71 / -36 | +78 / -39 |
| intertank +1 m | +103 | +53 | +43 |
| E 70 / 80 GPa | +71 / -40 | +17 / -12 | +16 / -10 |
| minimum gauge 3 mm | -50 | -49 | -346 (a thicker envelope) |
| densities, ullage fraction, top mass, hemispherical domes, drag in the envelope | 0 to 60 each | 0 to 60 each | 0 to 60 each |

Corner sets: sigma, FS and E at the ends that lower or raise dm, and p_u at its best or worst for the form:

| Form | Low corner | Central | High corner |
|---|---|---|---|
| monocoque | 2,159 kg | 2,550 kg | 3,487 kg |
| stiffened 2x | 1,390 kg | 2,248 kg | 2,550 kg |
| stiffened 3x | 1,492 kg | 1,972 kg | 2,345 kg |

Quasi-static structural range: **1.4 to 3.5 t**.

Further results:

- **The DLF on the push's dynamic part** multiplies the structural increment (dm_struct; the interface force F_int in brackets):

| Form | DLF 1.0 (20.81 MN) | DLF 1.1 (22.38 MN) | DLF 1.3 (25.50 MN) | DLF 2.0 (36.42 MN) |
|---|---|---|---|---|
| monocoque | 2,550 | 2,857 | 3,473 | 6,328 |
| stiffened 2x | 2,248 | 2,513 | 3,029 | 4,951 |
| stiffened 3x | 1,972 | 2,238 | 2,836 | 5,250 |
| pinf | 2,234 | 2,555 | 3,209 | 5,545 |

  The DLF 2.0 values exclude any stage-2, interstage or payload increment (section 3).
- **Interface hardware** at k kg/MN of the peak interface force (placeholder): k = 20, 50, 100 give 0.42, 1.04, 2.08 t at DLF 1, and 0.73, 1.82, 3.64 t at DLF 2.
- **Alternative load entry through the thrust structure** (Q5): the increment is m_ts (F_int/T_MECO - 1) = 1.53 m_ts, that is +1.5, 3.1 or 4.6 t for an assumed m_ts of 1, 2 or 3 t. This is as large as the whole tank increment, so the Q5 choice matters as much as the tank model (inference from the probe).
- **Dependence on the offload x** (central, quasi-static), dm_struct in kg:

| Form | x = 0 | 10 t | 20 t | 30 t | 41.26 t |
|---|---|---|---|---|---|
| monocoque | 2,892 | 2,806 | 2,722 | 2,640 | 2,550 |
| stiffened 2x | 2,722 | 2,603 | 2,487 | 2,373 | 2,248 |
| stiffened 3x | 2,534 | 2,393 | 2,255 | 2,119 | 1,972 |

  The slope is -9 to -14 kg per tonne of offload, about 1% of the propellant change. Brief 5.5 option (i) should therefore keep m_res(x) monotone; the solver's `offload_nonmonotone` check still decides that (inferred). The recorded silo_cold push (P* 27.55 t, full tanks) gives 2,904 / 2,728 / 2,539 kg, close to the x = 0 values at P_ref.

## 8. Part B: placement on SP1's penalty curve (planning probe)

dm = dm_struct + k F_int. Placement is a linear interpolation of RQ1:296-299; beyond 8.1 t it is extrapolated with the last segment, and x <= 0 means no offload. "Coupled" is the fixed point x = X(dm(x)), with dm re-evaluated at the offload it produces. That is what brief 5.5 option (i) would solve, up to the error of interpolating the curve.

| Case | Naive (dm at x = 41.26 t) | Coupled |
|---|---|---|
| Monocoque central, DLF 1, k = 20 | 27.74 t | 27.16 t |
| Monocoque central, DLF 1, k = 50 | 24.80 t | 23.99 t |
| Monocoque central, DLF 1, k = 100 | 19.66 t | 18.25 t |
| Stiffened 2x central, DLF 1, k = 50 | 26.22 t | 25.23 t |
| Stiffened 3x central, DLF 1, k = 50 | 27.52 t | 26.47 t |
| Monocoque central, DLF 1.3, k = 50 | 19.07 t | 17.44 t |
| Monocoque central, DLF 2.0, k = 20 | 7.30 t | 4.26 t |
| Monocoque central, DLF 2.0, k = 50 | 1.73 t (extrapolated) | 0 |

- Over the nine corner sets and k = 20-100 (b_range_console.txt), the coupled x is:
  - DLF 1.0: **12.2 to 32.9 t (30% to 80% of 41.263 t)**
  - DLF 1.1: 8.7 to 31.8 t
  - DLF 1.3: 1.6 to 29.5 t
  - DLF 2.0: 0 to 20.2 t
- The full-load sizing bound (option iii: dm fixed at the x = 0 push) sits 0.6 to 2.6 t below the coupled value at DLF 1.
- Bias of the naive placement (fact of the probe). Brief 5.5's pre-registration idea (dm at the headline placed on the curve, lines 396-399) overstates the offload by 0.4 to 1.7 t at DLF 1, and by up to 4 t at DLF 2.0, which favours the assist. **Recommendation: pre-register the coupled estimate, or state the bias.**
- **The range covers most of the offload.** Even quasi-static it runs from 30% to 80% of the headline, and with any DLF above 1.3 it reaches zero. In R1's terms (brief line 922), the probe cannot decide whether "the 10%" survives until three things are pinned down: the DLF (the structural period T against the drive's rise time), the interface-hardware coefficient k with the Q5 load path, and the buckling form. The material allowables, the factor of safety and the ullage pressure move dm by only about ±0.2-0.4 t each. What the probe does say: no probed case keeps the full 41 t. The best quasi-static case retains about 80%, and the central quasi-static cases with k = 50 retain 58-64%.

## 9. What the probe leaves out (facts and inferences)

Left out:

- bending (max-Q, winds) and lateral loads (out of scope, brief 2);
- ring frames, Y-rings, joints, weld-land knockdowns and dome-cylinder discontinuity stresses;
- feedlines (the LOX downcomer under 4 g0);
- COPV and engine mounts;
- the thrust structure under aft-ring entry;
- the hot-start case (higher tank g at a fixed F_max, brief 5.7 line 420);
- the release transients' effect on propellant settling before the 0.5 s-late ignition (inferred risk);
- any spare margin of the real stage-1 structure (Q3: zero margin assumed). Margin would lower dm; the omitted items would raise it.

The mixture-ratio split of the offload is the probe's own assumption, since the code splits by stage only (vehicle.py:613).

## 10. Recommendations for the plan (not facts)

1. **Tests.** Take the closed forms of sections 2-4 as the test oracles, with their validity conditions: F_max > M g; v_r < v_c; the stack starts from its stops at F = M g. Also state the braking convention, total deceleration or brake-only.
2. **Q7, the DLF.** Charge min(2, 1 + T/(pi t_r)) from a stated rise time and an assumed or sourced structural period, rather than the exact sinc. Report `constant_accel` at DLF 2. Apply the factor at release too, or list the tension swing and the LOX column-separation risk. If DLF > 1.40, add the upper-stack check.
3. **S0 priorities, in order of leverage.** (a) The stage's first axial period T, together with the drive's rise-time rule. (b) The interface and load-entry coefficient k, with Q5's path (the aft ring against the thrust structure). (c) The tank construction (monocoque against stiffened; F9's actual design). (d) The ullage pressures. (e) The allowable and the factor of safety. Geometry comes second; densities, ullage fraction, the top mass and drag are negligible.
4. **Low and high sets** are computed for each buckling form, not chosen per coefficient: the direction of p_u flips between forms.
5. **Pre-registration** uses the coupled placement (or states the naive bias) and discloses this probe's numbers as a planning probe, beside SP1's penalty rows.

Sources consulted, none used for a value: [shellbuckling.com SP-8007 preliminary revision](https://shellbuckling.com/papers/prelimNASA_SP-8007-2018-mwh-2019.07.24.pdf) (too large to fetch), [shellbuckling.com pressurized-cylinder page](https://shellbuckling.com/presentations/unstiffenedCylinders/pages/page_97.html) (no Delta gamma values), [NTRS 19930084510](https://ntrs.nasa.gov/api/citations/19930084510/downloads/19930084510.pdf) (named by a search as containing "Effect of Internal Pressure"; not opened).
