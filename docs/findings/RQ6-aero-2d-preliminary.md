# RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo

Status: preliminary, and deliberately narrow. Plan decision 6 limits RQ6 in Phase 2 to
"unthrottled max-Q deltas": there is no throttle, no q or q-alpha limit and no
angle-of-attack aerodynamics in the model, so nothing here is a flown load. The
caveats, provenance and the v_k fairness outcome of RQ3-silo-screening-2d.md apply
(the rule did not fire; headlines against the pad at v_k = 50 m/s).

## Caveats (read first)

- **Unthrottled**: every max-Q is an upper bound on a flown value, and the bias is not
  the same for every run. A real vehicle throttles through max-Q (the pad's model max-Q
  of 37.2 kPa is above the 22-30 kPa band of flown Falcon 9 values listed in the plan's
  sanity ranges, reliability C). The run with the higher unthrottled max-Q (the pad)
  would throttle more and pay more gravity loss for it; the payload deltas below do not
  include that.
- **No alpha aerodynamics**: q-alpha is computed with alpha = psi (the angle between
  thrust and v_rel) and charged nothing. The kick is the only phase with psi above zero
  in stage 1.
- **Generic drag**: the Braeunig ballpark power-on C_D(M) table (23 knots, PCHIP, peak
  0.730 at Mach 1.15; not Falcon 9), A_ref 10.52 m^2 through the whole flight; the
  21.24 m^2 fairing section is the aero bound.
- **Atmosphere**: ICAO standard atmosphere, no wind, co-rotating; its tropopause is a
  kink in the temperature profile (see below).
- Gate vehicle, +14.3 % calibration miss (CAL-f9-leo-2d.md); sweep-optimized guidance.

## Provenance

results/silo_screening_2d/20260930T175743Z (run), results/silo_screening_2d/
20260930T182453Z (sweeps), results/silo_bridge_2d_readme/20260930T185034Z (bridge),
results/guidance_trigger_2d/20260930T174950Z (trigger study); all git 7ad381f227a9,
clean. Timing and slope figures marked "derived" come from the recorded time series
(0.05 s samples), not from new runs.

## Max-Q and q-alpha against the pad (unthrottled)

| run | max-Q [kPa] | delta vs pad [kPa] | t after release [s] | Mach | altitude [m] | peak q-alpha [Pa rad] (when) | drag loss [m/s] (own P*) |
|---|---|---|---|---|---|---|---|
| pad (baseline) | 37.19 | 0 | 65.75 | 1.532 | 11,019.1 | 74.7 (kick, 12.5 s) | 26.04 |
| pad_instant | 36.77 | -0.42 | 66.15 | 1.523 | 11,019.1 | 72.5 (kick, 12.7 s) | 25.77 |
| silo_instant | 30.95 | -6.24 (-16.8 %) | 54.19 | 1.398 | 11,019.1 | 222.2 (kick, 0 s) | 22.25 |
| silo_cold | 31.24 | -5.95 (-16.0 %) | 57.61 | 1.404 | 11,019.1 | 129.9 (kick, 0.5 s) | 22.40 |
| silo_cold_lag | 31.22 | -5.97 | 57.60 | 1.404 | 11,019.1 | 129.9 (kick, 0.5 s) | 22.39 |
| silo_hot_ramp_on_track | 31.37 | -5.82 | 53.93 | 1.407 | 11,019.1 | 230.0 (kick, 0 s) | 22.52 |
| silo_hot_full (and _impinged) | 32.51 | -4.68 | 53.26 | 1.433 | 11,019.1 | 251.3 (kick, 0 s) | 23.24 |
| silo_sled_22t | 31.24 | -5.95 | 57.61 | 1.404 | 11,019.1 | 129.9 | 22.40 |
| silo_failed | 3.60 (at release) | n/a | 0 | 0.225 | 0 | 0 | 0.15 |

- **Max-Q falls by 4.7 to 6.2 kPa (13 to 17 %) in every silo variant; no variant is
  flagged above the pad.** The silo reaches the tropopause 8.1 to 12.5 s earlier after
  release, having burned less propellant and gained less speed, so it crosses it at
  Mach 1.40 instead of 1.53.
- **q-alpha rises in every silo variant (1.7 to 3.4 times the pad's) and is flagged.**
  The kick starts at the first lit instant, at 72 to 77 m/s near sea level (q about 3.1
  to 3.6 kPa), where the pad kicks at 50 m/s after 12.5 s. The values are small at this
  push (130 to 251 Pa rad) but grow fast with the release speed (below). Without alpha
  aerodynamics the model charges them nothing; a derived upper bound on the axial loss
  such a kick could cause (C_N,alpha = 4 per rad) is under 0.005 m/s for pad and silo
  alike (RQ3-2d), so the flag is about loads, not payload.
- **Sensitivity of the max-Q delta** (recorded +/-10 % cases, each against the pad
  re-run under the same perturbation; metrics.json
  sensitivity[].comparison_vs_perturbed_baseline.delta_max_q_pa): silo_cold -5.25 kPa
  (stage-1 Isp +10 %) to -6.80 kPa (stage-1 Isp -10 %), i.e. -15.4 to -16.7 %; stage-1
  dry mass -5.98 / -5.92 kPa (-10 / +10 %), stage-2 Isp -6.04 / -5.86, C_D -6.00 /
  -5.91, drive efficiency and screening Isp unchanged (-5.95). silo_hot_full -4.11 to
  -5.37 kPa (-12.0 to -13.2 %). max_q_above_baseline is False in every case, and max-Q
  stays at the 11,019.07 m tropopause in every case, pad and silo. The sign and the
  location are robust; the size moves by -0.85 to +0.70 kPa, almost all of it from the
  stage-1 Isp.
- **The trigger study leaves max-Q unchanged** (pad 37.09 to 37.19 kPa, silo_cold 31.19
  to 31.24 kPa over v_k 30 to 120 m/s), while the pad's own q-alpha rises from 10.6 Pa
  rad at v_k 30 to 1,942 Pa rad at v_k 120.

## The tropopause pins max-Q (what that means for its location)

Max-Q lies at 11,019.1 m in every run flown to orbit here except one: that is the ICAO
tropopause (11,000 m geopotential = 11,019.07 m geometric with the ICAO radius
6,356,766 m; derived). The ICAO temperature profile has a kink there (lapse -6.5 K/km
below, isothermal above), so the density scale height jumps from 7.83 to 6.34 km in
geopotential metres (7.86 to 6.36 km geometric; derived from the ICAO constants). q = 0.5 rho v^2 then has a corner:

| run | d ln q / dt just below 11,019 m [1/s] | just above [1/s] | max-Q |
|---|---|---|---|
| pad | +0.0053 | -0.0062 | at the kink |
| silo_cold | +0.0044 | -0.0065 | at the kink |
| silo_instant | +0.0033 | -0.0075 | at the kink |
| sweep_1 3 g0, 300 m (132.9 m/s) | +0.0009 | -0.0098 | at the kink |
| sweep_1 5 g0, 300 m (171.5 m/s) | -0.0025 | -0.0133 | before the kink: 29.57 kPa at 10,241 m, Mach 1.286 |

(derived from the recorded time series.) In every run but the fastest sweep point, q is
still rising when the vehicle reaches the kink and falls right after it, so the maximum
is a corner of the atmosphere model, not a smooth maximum of the trajectory. What this
means:

- The altitude of max-Q (11.02 km) is set by the atmosphere model, not by the
  trajectory, and is the same for pad and silo. Its time and Mach move with the
  trajectory (65.8 s and Mach 1.53 for the pad, 57.6 s and Mach 1.40 for silo_cold).
- The max-Q delta is therefore essentially the difference of 0.5 rho(11.02 km) v^2 at
  the tropopause crossing: a clean like-for-like comparison at a fixed altitude, but its
  size depends on how sharply the real atmosphere turns at the tropopause. With a
  smoother real temperature profile the peak would be a smooth maximum near, not
  exactly at, 11 km; the direction of the delta (lower for the silo, because it crosses
  that height slower) would not change, its size could.
- The fastest release (171.5 m/s) is already past its own smooth maximum below the
  tropopause (d ln q / dt negative before the kink). At 132.9 m/s the margin is small
  (+0.0009 /s). So the pinning is a property of this vehicle and release range, not a
  general law.

## Transonic context

The C_D table peaks at Mach 1.15 (0.730). The largest drag force comes shortly after
it, before max-Q (derived from the time series):

| run | Mach 1 crossing: t [s], altitude [m], q [kPa] | peak drag force [kN] at Mach, altitude |
|---|---|---|
| pad | 52.60, 6,681, 30.1 | 259.0 at M 1.21, 8,465 m |
| silo_cold | 46.34, 7,402, 27.2 | 227.5 at M 1.20, 9,262 m |
| silo_instant | 42.84, 7,371, 27.3 | 227.0 at M 1.19, 9,153 m |

The silo goes transonic about 0.7 km higher and at about 10 % lower q, so its peak
drag force is 12 % lower.

## Drag-loss deltas

- Recorded runs at their own P*: drag loss 22.25 to 23.24 m/s for the silo variants
  against 26.04 m/s for the pad (almost all of it before MECO: the pad's 26.00 of 26.04
  m/s).
- Matched at the pad's P* (RQ3-2d attribution): the drag term is +3.51 m/s (31.8 kg)
  for silo_cold, +3.36 to +3.62 m/s for the 77 m/s variants, 2.65 m/s for silo_hot_full.
  Across the accel x stroke sweep it grows from +0.78 m/s at 22 m/s to +4.47 m/s at
  133 m/s and is +4.35 m/s at 172 m/s. Drag is 2 % of the silo's payload gain.
- M4 (blocking: the drag + steering share of the gain beyond the release speed, at
  most 0.5) passes at gamma*_ref everywhere: 0.120 to 0.144 for the named silo variants
  (pad_instant 0.087). The verdict is not robust over gamma* +/- 0.5 deg for pad_instant
  and for sweep_1 points run_0001, run_0002 and run_0004 (22.1 and 31.3 m/s; run_0001's
  share is 0.472 against the 0.5 bound and spans -1.13 to 2.02 over the range); the
  pre-registered verdict at gamma*_ref stands (RQ3-2d).

## The aero bound (A_ref 21.24 m^2) and the C_D sensitivity

| case | pad P* [kg] | silo_cold P* [kg] | dP* [kg] | pad / silo drag loss [m/s] | pad / silo max-Q [kPa] |
|---|---|---|---|---|---|
| nominal (10.52 m^2) | 26,054.4 | 27,553.2 | +1,498.8 | 26.04 / 22.40 | 37.19 / 31.24 |
| aero bound (21.24 m^2) | 25,663.5 | 27,190.3 | +1,526.8 | 51.94 / 44.74 | 35.49 / 30.00 |
| C_D scale -10 % / +10 % (paired) | - | - | +1,496.0 / +1,501.7 | - | - |

- Doubling the drag area costs the pad 390.9 kg and the silo 362.9 kg, so the assist's
  dP* rises by 28.0 kg (+1.9 %): the matched drag term doubles (+3.51 -> +6.93 m/s,
  31.8 -> 62.1 kg). C_D +/-10 % moves dP* by +/-2.9 kg (0.2 %).
- With the larger area both max-Qs fall (the heavier drag slows both), and the silo's
  delta is -5.49 kPa (-15.5 %).
- Drag is not what the silo's advantage rests on; the aero assumption cannot change the
  sign or the size of the headline by more than about 2 %.

## Release speed and max-Q (the accel x stroke sweep)

| V0 [m/s] | 22.1 | 31.3 | 44.3 | 54.2 | 70.0 | 76.7 | 99.0 | 132.9 | 171.5 |
|---|---|---|---|---|---|---|---|---|---|
| max-Q [kPa] | 35.91 | 34.89 | 33.61 | 32.76 | 31.64 | 31.24 | 30.20 | 29.41 | 29.57 |
| q-alpha [Pa rad] | 68.6 | 63.1 | 55.4 | 49.4 | 85.9 | 129.9 | 393.2 | 1,293.3 | 3,408.8 |

Max-Q falls monotonically with the release speed up to 133 m/s and rises again at
172 m/s, where it has left the tropopause. q-alpha falls slowly (68.6 to 49.4 Pa rad) while the kick
happens after a vertical rise at 50 m/s (release speeds up to 54 m/s) and then rises
steeply once the kick happens at ignition: 17 and 46
times the pad's at the two fastest points (unconstrained kicks, above 120 m/s).

## Bridge (README-loads vehicle)

Max-Q pad 42.73 kPa, silo_cold 36.39 kPa (-6.35 kPa, -14.8 %), silo_instant 36.11 kPa;
q-alpha 105.2 against 198.1 Pa rad; drag loss 29.93 against 25.99 m/s. The same
pattern on the lighter README-loads vehicle, at higher q (its larger thrust-to-weight
flies faster through the tropopause).

## What cannot be concluded before throttling and alpha aerodynamics exist

- Whether the silo's lower unthrottled max-Q turns into payload: a q-limited throttle
  would cost the pad more gravity loss than the silo, which would widen the payload gap,
  but by how much is unknown until a throttle law exists and both runs fly it.
- Flown max-Q values or their altitudes: the model's max-Q sits on the ICAO tropopause
  corner and is 24 % above the top of the flown 22-30 kPa band for the pad.
- Whether the silo's kick at 72-77 m/s near sea level is acceptable: q-alpha is only
  reported. With alpha aerodynamics the kick would produce a normal force and a bending
  load, and a q-alpha limit could force a later or gentler kick, which would move the
  trajectory term of RQ3-2d. At 133-172 m/s release speeds the unconstrained q-alpha
  (1.3 to 3.4 kPa rad) makes the dP* of those points unusable as design numbers.
- Base drag and plume effects in the cold start's unlit coast (the power-on table is
  used), and any shaft-exit aerodynamics (the shaft is vented and drag-free).

## Findings stated plainly

- Unthrottled max-Q falls by 13 to 17 % for every silo variant (31.2 against 37.2 kPa
  for the cold start; -15.4 to -16.7 % under the +/-10 % cases), because the silo
  crosses the tropopause earlier and slower. The
  location of max-Q (11.02 km) is fixed by the atmosphere model's tropopause kink, not
  by the trajectory, in every run except the 172 m/s point.
- q-alpha rises in every silo variant (1.7 to 3.4 times the pad's at 77 m/s; up to 46
  times at 172 m/s) because the silo kicks near sea level at the release speed. That is
  the one aerodynamic load that gets worse, and the model does not charge it.
- Drag is a minor part of the silo's gain (+3.5 m/s, 32 kg of 1,499 kg); doubling the
  drag area adds 28 kg to the silo's advantage.

## Figures

Copied next to this note from results/silo_screening_2d/20260930T175743Z/plots/ (and
results/silo_screening_2d/20260930T182453Z/sweep_1/run_0012/plots/):

- RQ6-2d-pad_q_mach.png, RQ6-2d-silo_cold_q_mach.png, RQ6-2d-silo_instant_q_mach.png:
  q and Mach against time from release; the q peak is a corner at the tropopause.
- RQ6-2d-pad__aero_bound_q_mach.png and RQ6-2d-silo_cold__aero_bound_q_mach.png: the
  same with the 21.24 m^2 area.
- RQ6-2d-sweep1_run_0012_q_mach.png: the 171.5 m/s release, q of 18 kPa at release and
  a smooth maximum below the tropopause.
- RQ6-2d-pad_losses.png and RQ6-2d-silo_cold_losses.png: cumulative losses; drag is the
  small curve that saturates by about 100 s.
