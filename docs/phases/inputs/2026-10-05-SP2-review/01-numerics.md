# SP2 design review 01: the numerics lens (first draft of the plan, 2026-10-05, at b69ff0c)

VERDICT: Sound through this lens, with no blocker: I re-ran the tank algorithm and the D-SP2-16 row-selection grid on all 31 run folders (liftoff identity within 5e-7 kg, one insertion pass, 191 to 987 samples, mass within 0.51 kg after 6-decimal times and 0.1 kg tanks), and the cache re-wrap, the attitude premises, the frame conventions and the transform all agree with the code. The most important change is to exit criteria 5 and 6. The mass-closure clause is an identity that passes with a wrong fairing flag (stage-2 tank at -1,700 kg), and the plume and attitude clauses do not test the thrust-on switch, the cutoff row or anything after the canvas transform. The fill rule also needs a change: against the top-level block it draws a fully fuelled calibration case as 3.7% and 13.8% offloaded.

## 1. [major] Criterion 6 and A2's mass-closure gate are an identity; a wrong fairing flag or stage-2 split passes

CLAIM: The tank series are m_kg minus constants and the page adds the same constants back, so 'rebuilt stack mass equals m_kg within 1 kg' tests only interpolation, and no clause of criterion 6 checks the stage-2 tank or the fairing flag.

EVIDENCE: Plan 4.4 formulas and survey 09 section 1.2 ('the definition rebuild equals m_kg to 6e-11 kg'). Scratch run review/r10_checks.py on results/silo_screening_2d/20260930T175743Z/pad with the fairing flag forced on for the whole run (the bug D-SP2-15 exists to prevent): max |rebuilt - m_kg| = 5.8e-11 kg, start fill 1.000, stage-1 tank 0.0 kg at MECO. All three clauses of criterion 6 pass, while the stage-2 tank reads -1,700 kg at cutoff. A wrong payload (22,800 kg) also closes to 0 kg and is caught only by the MECO clause (3,254 kg). The independent rebuild from thrust_vac_N/(g0 Isp) (survey check g, review/r4_tanks_all.py) is not an identity: at most 1.8e-6 kg on 29 folders, 0.56 kg on silo_cold_lag, 57.6 kg on silo_instant (see the silo_instant finding).

CHANGE: Add to criterion 6 and to A2's gate, at every CSV row: (a) each tank series never rises and has no step above 1 kg at staging or at the fairing time; (b) the stage-2 tank equals the run block's stage-2 load within 1 kg on every row before stage-2 ignition and equals metrics recorded_m_res_kg within 1 kg on the last row of a flight that reached cutoff or depletion; (c) liftoff_mass_kg equals vehicle masses plus payload within 1 kg (today only a load-time flag); (d) every tank, offloaded or not, starts at one minus its offload fraction. Keep the m_kg clause but describe it as the interpolation and rounding check.

## 2. [major] Fill against the top-level block is wrong for a calibration case with its own vehicle

CLAIM: Plan 4.4's rule draws a fully fuelled calibration case as partly offloaded, in a directory the scene does not refuse.

EVIDENCE: D:/DEV/ClaudeProjects/SpaceRocketOptimization/results/calibration_f9_2d/20260930T173928Z/resolved_config.yaml: cases.readme_loads.vehicle has stage loads 395.7 t and 92.67 t; the top-level vehicle has 410.9 t and 107.5 t. The directory is planar, has summary.md and no FAILED.txt, is not a sweep, so it is outside the refusal list of plan 4.4, and replay already selects cases. review/r9_cases.py: with the run's own block the liftoff identity closes to 1.2e-7 kg, but fill against the top-level load is 0.963 (stage 1) and 0.862 (stage 2) for a vehicle with full tanks. The rule is right for the penalty rows (0.995180 on dry+8.1t) and the two bound runs (1.000; only aero.reference_area_m2 differs).

CHANGE: 4.4: the fill reference is the top-level block for entries under runs, bound_runs and offload_runs, and the entry's own block for entries under cases. Every mass and the plume denominator always come from the run's own block. Add calibration_f9_2d/20260930T173928Z readme_loads to A2's gate (both tanks start at 1.000). Alternatively add 'a case with its own vehicle file' to the refusal list and say so.

## 3. [major] Criterion 5 does not test thrust on or off, conflicts with the cutoff row, and leaves the side at an event time undefined

CLAIM: The reworded criterion dropped the on/off test, yet names 'cutoff' as a sample where the single CSV row reads full thrust and the page must show the engine off, and at every other event the CSV has two rows with different values.

EVIDENCE: review/r6_ign_rows.py: the last row of every orbital flight has thrust_vac_N/full = 1.000 and is a single row (30 of 31 folders; silo_failed has none). Survey 09 section 6 says the plume must be switched off by the cutoff event. Plan 4.5's hook returns both 'plume fraction' and 'thrust on' as 'the values the drawing uses'. If that plume value is 0 at cutoff the criterion fails on four of the five QA runs; if it is the raw series, nothing tests the flag that gates the drawn plume. At an event time the two rows differ by 2.2 to 10.9 deg of pitch, 1.0 of plume, 22.2 t of mass and the stage (survey 09 section 3.3). The copied helpers are right-continuous (src/launchsim/templates/replay.html 235-249: idxAt returns the last index with T <= t), so the page can only show the later row.

CHANGE: Criterion 5: (a) at an event time the page state equals the later of the two CSV rows, and the QA table names that row; (b) thrust on equals the event rule (the stage's ignition <= t < its propellant, cutoff or end) at every CSV row, and the drawn plume length is plume fraction times thrust on; (c) the run's last row is excluded from the plume-fraction comparison, and the QA line for cutoff checks thrust off, stage and position instead.

## 4. [major] The state hook reports numbers before the canvas transform, so 'drawn attitude' and position are not measured

CLAIM: A sign error in the y-down rotation, a mirrored x or a wrong scale passes criterion 5, because the hook returns the values handed to the drawing, not what is painted.

EVIDENCE: Plan 4.5: stateAt(t) returns altitude, downrange, drawn attitude, plume fraction, thrust on, stage, tank fills, rebuilt mass, events, camera scale, icon mode; no canvas coordinates. Plan 4.4 gives only 'drawn angle = pitch - d/R_E' (y up). Survey 09 section 3.1 warns the canvas rotation is the negative of that on a y-down canvas and that the wrong sign differs by 1.8 to 3.2 deg in the gravity turn. Only screenshots (A3, A7) would show it, and the to-scale rocket leans 2.4 to 4.1 deg after the kick and becomes an icon at about 35 s.

CHANGE: 4.5: the hook also returns, per panel, the canvas-space points (px) of the rocket base and nose, the launch-site ground point and the px-per-metre actually applied. A3 and A7 assert from them: nose above base on the pad (smaller canvas y); after the kick, atan2(-dy, dx) of base to nose equals pitch - d/R_E within 0.5 deg; the base sits at the transform's (x, y) within 1 px; base-to-nose length equals rocket length times scale in to-scale mode.

## 5. [minor] silo_instant's recorded step is one row late; the survey fact behind 'at every time' is wrong

CLAIM: On the step-startup preset silo_instant both rows at the ignition time read thrust 0 and full thrust appears only on the next row, so linear interpolation draws a 43 ms plume ramp the model does not have.

EVIDENCE: results/silo_screening_2d/20260930T175743Z/silo_instant/timeseries.csv: rows at t_rel 0 (ASSIST and KICK) have thrust_vac_N = 0; the row at +0.0427 s has 8,226,900 N and m_kg already 115.13 kg lower (full flow from the ignition instant). metrics t_ign_rel_release_s_stage1 = 1.78e-15 s, so the row is sampled a rounding step before ignition (vehicle.py 104: dt < 0 gives 0). Same in silo_bridge_2d_readme. Survey 09 section 6 says 'two rows at 0 s: 0 then 1'. pad_instant (first row 1.0) and stage-2 ignition (0 then 1) are as the survey says. Each CSV row is still matched exactly. None of criterion 5's five QA runs has a lag or step stage-1 startup.

CHANGE: Criterion 5: replace 'at every time' with 'at every CSV row'. Add silo_cold_lag and silo_instant to A2's independent comparison for the plume fraction. Log a known issue: a step startup at release records thrust 0 on its first flight row. Any gate that rebuilds mass by integrating thrust excludes silo_instant's first interval (57.6 kg).

## 6. [minor] Step flags on the page should follow the sample index, not a separately rounded event time

CLAIM: The plan does not say how the page switches stage, fairing and thrust flags; comparing the clock with an event time computed as event t_s minus t_release can land on the wrong side of the duplicate rows.

EVIDENCE: Survey 09 section 5: that subtraction differs from the row's t_rel_release_s by up to 5e-11 s and produced a 22,200 kg error at staging on three of eleven runs. With 6-decimal rounding the two values round apart only near a rounding boundary (about 5e-5 per event), so it would pass every gate and show up as a flagged app run. All events match a row on t_s exactly in the 31 folders (review/r4_tanks_all.py, 0 unmatched), which is structural: every EventSpec factory is terminal (phases/engine.py 589-863). Smallest positive row spacing on disk is 3.4e-5 s, so 6 decimals never merges distinct rows.

CHANGE: 4.4: stage, fairing-on and thrust-on are per-sample step series read with idxAt at the same index as the tank samples. An event's page time is the matched time-series row's t_rel_release_s rounded to 6 decimals, the same number as its two samples; it is never event t_s minus the release time.

## 7. [minor] Payload source for bound runs and cases is not stated; '31 run folders' is not every folder on disk

CLAIM: 'The run's payload_kg, else the block's value' closes on bound runs and cases only if it reads metrics bounds[].metrics, bounds[].paired_baseline_metrics and cases.<name>.

EVIDENCE: Brief 5.3 says the two bound runs were not checked; the survey loader (a0/s09_common.py run_metrics) raises KeyError for them. With the block's 22,800 kg the liftoff identity misses by 2,863.5 kg (pad__aero_bound flies 25,663.5 kg) and 4,390.3 kg (silo_cold__aero_bound, 27,190.3 kg). With the bounds metrics both close to 4.5e-7 kg (review/r4_tanks_all.py). replay.py 266-291 already resolves these. 31 is the count of the two reference directories only: complete planar directories on disk hold 25 more run folders (calibration_f9_2d x2, silo_bridge_2d_readme, silo_offload_2d_readme); the 17 I checked also close within 5e-7 kg.

CHANGE: 4.4: the payload is payload_kg of the run's metrics record as run_data.run_source resolves it (runs, offload.runs, bounds[].metrics, bounds[].paired_baseline_metrics, cases), else the block's value. A2's gate: every run folder of every complete planar directory on disk, not only the 31.

## 8. [minor] The stage-2-ignition fairing case cannot come from the planner call the plan names

CLAIM: Plan 4.2 says the at-stage-2-ignition case is tested on rows built with the planner call of tests/test_planar_events.py, but that call stops at the stage-2 ignition handover.

EVIDENCE: tests/test_planar_events.py 308-343 (test_staging_map_and_coast) calls planner.stage1 only. Survey 06 section 5.4 says cases 1 and 2 'need a stage-2 burn: use hand-written rows', which would encode the reader's own assumption. A real recipe exists in tests/test_engine_planar.py 150-175: a heating limit at the geometric mean of the rates at MECO and at stage-2 ignition, then planner.stage2, giving a fairing event in LTG_BURN at t_ign2. I read the logging order in phases/planar.py 1283-1306 and 1689-1692 and it supports D-SP2-15's rule and 4.4's 'first of the two rows' rule for all four cases.

CHANGE: 4.2: build the stage-2-ignition case with the recipe of tests/test_engine_planar.py 150-175 (dense output on) and the staging cases with test_planar_events.py's call. Pass the traces through sample_trace_planar and events_frame_planar so that A2 also tests 4.4's fairing flag and tank series on real rows for the three cases with no recorded example.

## 9. [minor] Section 4.10's numbers for the separated bodies are off and misattributed

CLAIM: The text to be shown on the page, in the manual and in the gallery quotes a speed range the recorded runs exceed and ascribes a display-only result to the model.

EVIDENCE: Plan 4.10: 'reaches the surface at 2.9-3.6 km/s ... by the model they stay within 0.2 m of the vehicle for the 11 s staging coast'. review/r10_checks.py (energy and angular-momentum conservation from the event rows, all folders of the two directories): spent stage 2,798 m/s (silo_cold_s1__pad) to 3,587 m/s; fairing 3,053 to 3,869 m/s (silo_cold_s2). The model has no spent stage; 0.2 m is the gap between the display-only coast and the vehicle's recorded path, measured on two runs, and it holds for the stage only: the fairing is 462 m behind after 11 s (survey 09 section 2.4). In silo_cold_s2 neither body lands before the run ends (survey 09 section 2.2).

CHANGE: 4.10: show each run's own impact speed and downrange, computed, with no fixed range. Reword to: 'the display-only coast of the spent stage stays within 0.2 m of the vehicle's recorded path during the 11 s staging coast (pad and silo_cold of the screening directory), so any gap drawn then is a drawing choice; the fairing halves leave during the stage-2 burn and fall behind; a body still in flight when the run ends is drawn stopped there'.

## 10. [minor] A run with an empty time series in a complete directory is not covered

CLAIM: A failed search writes a header-only timeseries.csv into a directory that has summary.md and no FAILED.txt, and neither the refusal list nor the load-time checks say what the scene does with it.

EVIDENCE: src/launchsim/sim.py 1373-1385 and 1428-1439: search_failed_result and guidance_failed_result return empty_planar_timeseries() and empty events, and write_run still writes summary.md. replay.py 374-375 raises 'is empty (a failed search writes no trajectory)'. The form's free inputs (fixed offload fractions, stroke, penalty) can produce such a variant, and the default selection is the pad plus the launched run. Criterion 2's 'its scene plays' cannot hold for it.

CHANGE: 4.4: a selected run with an empty time series is left out with a one-line reason; the scene shows the remaining runs and the results panel shows the run's status and flag. Criterion 2: 'its scene plays' applies to runs that flew.

## 11. [minor] D-SP2-17 does not say which angle is held

CLAIM: 'Holds the last such attitude' can mean the pitch above the local horizontal or the screen angle, and the two diverge as the body moves downrange.

EVIDENCE: Plan 4.4: drawn angle = pitch - d/R_E. Over the 11 s staging coast d/R_E moves 0.24 deg (survey 09 section 3.2: 0.89087 to 1.13020 deg on the pad); over a spent stage's fall of about 740 km it moves 6.6 deg. The rule's premises are confirmed in code: HOLD pi/2 (metrics_planar.py 473), ASSIST phi (509), unpowered flight along v_rel (dynamics.py 756-757), Radial, FixedTilt, AlongVrel and LinearTangent (guidance.py 133-212). Holding gives no wrong picture on recorded data: 90 against 90.004 deg in COAST_PRE_IGN, and a step of +8.4 deg instead of +10.2 deg at stage-2 ignition.

CHANGE: D-SP2-17 and the physics.md display section: state that the held quantity is the screen angle (or the pitch; pick one), that the same rule applies to the spent stage and the fairing halves, and that the instant steps at the kick and at stage-2 ignition are the model's and are shown as recorded.
