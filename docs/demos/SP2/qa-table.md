# SP2 step A7: visual QA table (exit criteria 5 and 6, through the app)

Produced on 2026-10-07 at commit 931b19b from the app, not from the standalone page. The app served the
working tree of step A7 before its commit: the committed code plus this step's QA fixes of
src/launchsim/templates/scene.html (a stopped separated body keeps a label; the close-up title follows the
halves' drawn motion, half by half; a label's leader no longer crosses an earlier label; the close-up
frames stage 2 whole at staging; see-through caption plates; the readout's slot under the close-up in the
overlay layout; the other panel's marker named once; from review round 2, the carriage label clear of the
close-up inset and the other panel's label plate clear of the ring key; docs/demos/SP2/README.md lists them),
which change no value the criterion-5 and criterion-6 rows check. The watchability checks at the end
(criterion 16 and the review's close-up checks) were run after the last of those fixes.

How it was produced:

1. The app, started from the repository root with its results folder read-only (no launch was made):

       uv run python -m launchsim app --port 0 --results-root results

   It printed `http://127.0.0.1:64897/`.
2. For each pair below the app's scene route was opened in headless Edge with the QA hash, which makes the page
   write `window.launchsimScene.stateAt(t)` for every listed time into its `#qa-state` element, and the DOM was dumped
   (scratchpad scripts plan.py, dump.ps1, compare.py; the commands are in docs/demos/SP2/README.md):

       "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --no-first-run
           --no-default-browser-check --disable-extensions --user-data-dir=<own folder> --window-size=1280,900
           --virtual-time-budget=30000 --dump-dom "http://127.0.0.1:64897/scene/<experiment>/<timestamp>/<left>,<right>#qa=<t1>,<t2>,..."

3. The page values were compared with the run's own timeseries.csv, events.csv and resolved_config.yaml, read with
   pandas and yaml (not through launchsim). Reference rule: at an event time the later of the two CSV rows; between
   rows linear interpolation (step fields from the earlier row); before a run's first row that row (the page holds it).

Pairs and times (every events.csv event of both runs, the mid-push row of each pushed run, and times between):

- Q1: pad beside silo_cold (results/silo_screening_2d/20260930T175743Z, route .../pad,silo_cold; the page puts the baseline on the left), 46 times
- Q2: pad beside silo_hot_ramp_on_track (results/silo_screening_2d/20260930T175743Z, route .../silo_hot_ramp_on_track,pad; the page puts the baseline on the left), 41 times
- Q3: pad beside silo_failed (results/silo_screening_2d/20260930T175743Z, route .../pad,silo_failed; the page puts the baseline on the left), 48 times
- Q4: pad beside silo_cold_s1 (results/silo_offload_2d/20261003T112934Z, route .../pad,silo_cold_s1; the page puts the baseline on the left), 46 times

Fields and tolerances (criterion 5 and 6): altitude within the larger of 0.5% and 1 m; downrange within the larger
of 0.5% and 10 m; drawn attitude within 0.5 deg where the model defines one (thrust on, hold, on the track),
measured from the painted base and nose in to-scale mode (in marker mode or when unpowered the row says n/a and
why); the close-up's drawn attitude within 0.5 deg of the pitch where defined; plume fraction within 0.02 except on a
run's last row; thrust on equal to the event rule (from a stage's ignition row to its propellant, cutoff,
ignition_failed or end row); the stage exact; the rebuilt stack mass within 1 kg of m_kg; the painted base within
1 px of the screen transform of the CSV altitude and downrange; on the first row each tank's fill equal to its
load over the full load within 1e-4 (criterion 6: one minus the offload fraction); at the stage-1 propellant event
the stage-1 tank under 1 kg and the stage-2 tank equal to its load within 1 kg.

Rows are the five runs named by criterion 5 (pad and silo_cold from Q1, silo_hot_ramp_on_track from Q2,
silo_failed from Q3, silo_cold_s1 from Q4). The companion panel of Q2, Q3 and Q4 (pad) was checked the same way
and is summarised below the table; any failing companion check is listed under Deviations.

| pair | run | at | t after release [s] | CSV row | field | CSV value | page value | tolerance | verdict |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | thrust on | false | false | exact (event rule) | pass |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | rebuilt mass [kg] | 572354.396 | 572354.396 | 1.0 kg | pass |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | tank start fill stage 1 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q1 | pad | other run's event | -2.607318 | held (before first row) 0 | tank start fill stage 2 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | altitude [m] | -100.00 | -100.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | rebuilt mass [kg] | 573853.227 | 573853.227 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | tank start fill stage 1 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q1 | silo_cold | silo_cold:push_start | -2.607318 | first row 0 | tank start fill stage 2 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | rebuilt mass [kg] | 572354.396 | 572354.396 | 1.0 kg | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | tank start fill stage 1 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q1 | pad | pad:ignition_s1 | -2.000000 | first row 0 | tank start fill stage 2 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | altitude [m] | -94.57 | -94.56 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | rebuilt mass [kg] | 573853.227 | 573853.227 | 1.0 kg | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | other run's event | -2.000000 | between rows | painted base [px off transform] | 0 | 0.014 | 1.0 px | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | plume fraction | 0.3463 | 0.3463 | 0.02 | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | rebuilt mass [kg] | 572030.620 | 572030.655 | 1.0 kg | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | other run's event | -1.307318 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | altitude [m] | -75.14 | -75.10 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | rebuilt mass [kg] | 573853.227 | 573853.227 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | silo_cold:mid_push | -1.307318 | row 26 | painted base [px off transform] | 0 | 0.065 | 1.0 px | pass |
| Q1 | pad | between | -1.300000 | row 14 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | -1.300000 | row 14 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | -1.300000 | row 14 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | -1.300000 | row 14 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | -1.300000 | row 14 | plume fraction | 0.3500 | 0.3500 | 0.02 | pass |
| Q1 | pad | between | -1.300000 | row 14 | rebuilt mass [kg] | 572023.957 | 572023.996 | 1.0 kg | pass |
| Q1 | pad | between | -1.300000 | row 14 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | pad | between | -1.300000 | row 14 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | -1.300000 | row 14 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | altitude [m] | -74.85 | -74.81 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | rebuilt mass [kg] | 573853.227 | 573853.227 | 1.0 kg | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | -1.300000 | between rows | painted base [px off transform] | 0 | 0.065 | 1.0 px | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | rebuilt mass [kg] | 569656.935 | 569656.896 | 1.0 kg | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | pad:release | +0.000000 | row 41 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:release | +0.000000 | row 54 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:release | +0.000000 | row 54 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:release | +0.000000 | row 54 | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:release | +0.000000 | row 54 | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | silo_cold:release | +0.000000 | row 54 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:release | +0.000000 | row 54 | rebuilt mass [kg] | 573853.227 | 573853.227 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:release | +0.000000 | row 54 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q1 | silo_cold | silo_cold:release | +0.000000 | row 54 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | altitude [m] | 0.45 | 0.45 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | rebuilt mass [kg] | 568308.205 | 568308.196 | 1.0 kg | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | other run's event | +0.500000 | row 51 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | altitude [m] | 37.13 | 37.10 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | rebuilt mass [kg] | 573853.227 | 573853.227 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | drawn attitude [deg] | 87.639 | 87.639 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | close-up attitude [deg] | 87.639 | 87.639 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | silo_cold:ignition_s1; silo_cold:kick_start | +0.500000 | row 66 | painted base [px off transform] | 0 | 0.041 | 1.0 px | pass |
| Q1 | pad | between | +0.900000 | row 59 | altitude [m] | 1.46 | 1.45 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +0.900000 | row 59 | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +0.900000 | row 59 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +0.900000 | row 59 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +0.900000 | row 59 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +0.900000 | row 59 | rebuilt mass [kg] | 567229.221 | 567229.246 | 1.0 kg | pass |
| Q1 | pad | between | +0.900000 | row 59 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | pad | between | +0.900000 | row 59 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +0.900000 | row 59 | painted base [px off transform] | 0 | 0.010 | 1.0 px | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | altitude [m] | 65.09 | 65.10 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | plume fraction | 0.2000 | 0.1997 | 0.02 | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | rebuilt mass [kg] | 573745.118 | 573745.100 | 1.0 kg | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | drawn attitude [deg] | 87.639 | 87.639 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | close-up attitude [deg] | 87.639 | 87.639 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +0.900000 | between rows | painted base [px off transform] | 0 | 0.015 | 1.0 px | pass |
| Q1 | pad | between | +1.600000 | row 73 | altitude [m] | 4.63 | 4.60 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +1.600000 | row 73 | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +1.600000 | row 73 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +1.600000 | row 73 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +1.600000 | row 73 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +1.600000 | row 73 | rebuilt mass [kg] | 565340.998 | 565340.996 | 1.0 kg | pass |
| Q1 | pad | between | +1.600000 | row 73 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | pad | between | +1.600000 | row 73 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +1.600000 | row 73 | painted base [px off transform] | 0 | 0.030 | 1.0 px | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | altitude [m] | 111.22 | 111.18 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | downrange [m] | 0.03 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | plume fraction | 0.5500 | 0.5497 | 0.02 | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | rebuilt mass [kg] | 573037.035 | 573037.006 | 1.0 kg | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | drawn attitude [deg] | 87.639 | 87.639 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | close-up attitude [deg] | 87.639 | 87.639 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +1.600000 | between rows | painted base [px off transform] | 0 | 0.051 | 1.0 px | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | altitude [m] | 11.36 | 11.35 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | rebuilt mass [kg] | 562913.283 | 562913.296 | 1.0 kg | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | other run's event | +2.500000 | row 91 | painted base [px off transform] | 0 | 0.007 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | altitude [m] | 168.74 | 168.70 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | downrange [m] | 0.28 | 0.30 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | rebuilt mass [kg] | 571155.766 | 571155.727 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | drawn attitude [deg] | 87.639 | 87.639 | 0.5 deg (painted base and nose, to scale) | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | close-up attitude [deg] | 87.639 | 87.639 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | silo_cold:ramp_end | +2.500000 | row 108 | painted base [px off transform] | 0 | 0.040 | 1.0 px | pass |
| Q1 | pad | between | +4.200000 | row 125 | altitude [m] | 32.38 | 32.40 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +4.200000 | row 125 | downrange [m] | -0.01 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +4.200000 | row 125 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +4.200000 | row 125 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +4.200000 | row 125 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +4.200000 | row 125 | rebuilt mass [kg] | 558327.600 | 558327.596 | 1.0 kg | pass |
| Q1 | pad | between | +4.200000 | row 125 | drawn attitude [deg] | 90.000 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +4.200000 | row 125 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +4.200000 | row 125 | painted base [px off transform] | 0 | 0.015 | 1.0 px | pass |
| Q1 | silo_cold | between | +4.200000 | between rows | altitude [m] | 283.60 | 283.62 | 1.42 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +4.200000 | between rows | downrange [m] | 1.89 | 1.91 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +4.200000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +4.200000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +4.200000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +4.200000 | between rows | rebuilt mass [kg] | 566570.083 | 566570.090 | 1.0 kg | pass |
| Q1 | silo_cold | between | +4.200000 | between rows | drawn attitude [deg] | 87.639 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +4.200000 | between rows | close-up attitude [deg] | 87.639 | 87.639 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +4.200000 | between rows | painted base [px off transform] | 0 | 0.014 | 1.0 px | pass |
| Q1 | pad | other run's event | +8.025553 | between rows | altitude [m] | 120.95 | 120.94 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | +8.025553 | between rows | downrange [m] | -0.04 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | +8.025553 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | other run's event | +8.025553 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | other run's event | +8.025553 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | other run's event | +8.025553 | between rows | rebuilt mass [kg] | 548008.320 | 548008.330 | 1.0 kg | pass |
| Q1 | pad | other run's event | +8.025553 | between rows | drawn attitude [deg] | 90.000 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | other run's event | +8.025553 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | other run's event | +8.025553 | between rows | painted base [px off transform] | 0 | 0.018 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | altitude [m] | 581.28 | 581.30 | 2.91 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | downrange [m] | 11.29 | 11.30 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | rebuilt mass [kg] | 556250.804 | 556250.827 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | drawn attitude [deg] | 87.638 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | close-up attitude [deg] | 87.639 | 87.638 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | silo_cold:kick_end | +8.025553 | row 220 | painted base [px off transform] | 0 | 0.011 | 1.0 px | pass |
| Q1 | pad | between | +9.700000 | row 235 | altitude [m] | 178.45 | 178.50 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +9.700000 | row 235 | downrange [m] | -0.07 | -0.10 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +9.700000 | row 235 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +9.700000 | row 235 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +9.700000 | row 235 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +9.700000 | row 235 | rebuilt mass [kg] | 543491.565 | 543491.546 | 1.0 kg | pass |
| Q1 | pad | between | +9.700000 | row 235 | drawn attitude [deg] | 90.000 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +9.700000 | row 235 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +9.700000 | row 235 | painted base [px off transform] | 0 | 0.020 | 1.0 px | pass |
| Q1 | silo_cold | between | +9.700000 | between rows | altitude [m] | 729.45 | 729.47 | 3.65 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +9.700000 | between rows | downrange [m] | 18.00 | 18.03 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +9.700000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +9.700000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +9.700000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +9.700000 | between rows | rebuilt mass [kg] | 551734.048 | 551734.083 | 1.0 kg | pass |
| Q1 | silo_cold | between | +9.700000 | between rows | drawn attitude [deg] | 87.173 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +9.700000 | between rows | close-up attitude [deg] | 87.173 | 87.173 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +9.700000 | between rows | painted base [px off transform] | 0 | 0.013 | 1.0 px | pass |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | altitude [m] | 301.05 | 301.00 | 1.51 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | downrange [m] | -0.16 | -0.20 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | rebuilt mass [kg] | 535955.591 | 535955.596 | 1.0 kg | pass |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | drawn attitude [deg] | 87.166 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | close-up attitude [deg] | 87.166 | 87.166 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | pad:kick_start | +12.493729 | row 292 | painted base [px off transform] | 0 | 0.019 | 1.0 px | pass |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | altitude [m] | 1002.15 | 1002.11 | 5.01 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | downrange [m] | 33.57 | 33.61 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | rebuilt mass [kg] | 544198.073 | 544198.102 | 1.0 kg | pass |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | drawn attitude [deg] | 86.286 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | close-up attitude [deg] | 86.286 | 86.286 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | other run's event | +12.493729 | between rows | painted base [px off transform] | 0 | 0.016 | 1.0 px | pass |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | altitude [m] | 628.77 | 628.80 | 3.14 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | downrange [m] | 9.44 | 9.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | rebuilt mass [kg] | 521712.229 | 521712.196 | 1.0 kg | pass |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | drawn attitude [deg] | 87.166 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | close-up attitude [deg] | 87.166 | 87.166 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | pad:kick_end | +17.774014 | row 400 | painted base [px off transform] | 0 | 0.009 | 1.0 px | pass |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | altitude [m] | 1609.77 | 1609.75 | 8.05 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | downrange [m] | 83.88 | 83.86 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | rebuilt mass [kg] | 529954.711 | 529954.693 | 1.0 kg | pass |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | drawn attitude [deg] | 84.236 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | close-up attitude [deg] | 84.237 | 84.237 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | other run's event | +17.774014 | between rows | painted base [px off transform] | 0 | 0.006 | 1.0 px | pass |
| Q1 | pad | between | +21.000000 | row 465 | altitude [m] | 894.78 | 894.80 | 4.47 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +21.000000 | row 465 | downrange [m] | 25.62 | 25.60 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +21.000000 | row 465 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +21.000000 | row 465 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +21.000000 | row 465 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +21.000000 | row 465 | rebuilt mass [kg] | 513010.257 | 513010.246 | 1.0 kg | pass |
| Q1 | pad | between | +21.000000 | row 465 | drawn attitude [deg] | 85.874 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +21.000000 | row 465 | close-up attitude [deg] | 85.874 | 85.874 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +21.000000 | row 465 | painted base [px off transform] | 0 | 0.004 | 1.0 px | pass |
| Q1 | silo_cold | between | +21.000000 | between rows | altitude [m] | 2044.15 | 2044.15 | 10.22 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +21.000000 | between rows | downrange [m] | 133.39 | 133.43 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +21.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +21.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +21.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +21.000000 | between rows | rebuilt mass [kg] | 521252.740 | 521252.783 | 1.0 kg | pass |
| Q1 | silo_cold | between | +21.000000 | between rows | drawn attitude [deg] | 82.756 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +21.000000 | between rows | close-up attitude [deg] | 82.757 | 82.758 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +21.000000 | between rows | painted base [px off transform] | 0 | 0.007 | 1.0 px | pass |
| Q1 | pad | between | +37.500000 | row 795 | altitude [m] | 3141.11 | 3141.15 | 15.71 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +37.500000 | row 795 | downrange [m] | 387.17 | 387.15 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +37.500000 | row 795 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +37.500000 | row 795 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +37.500000 | row 795 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +37.500000 | row 795 | rebuilt mass [kg] | 468502.153 | 468502.146 | 1.0 kg | pass |
| Q1 | pad | between | +37.500000 | row 795 | drawn attitude [deg] | 76.295 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +37.500000 | row 795 | close-up attitude [deg] | 76.298 | 76.298 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +37.500000 | row 795 | painted base [px off transform] | 0 | 0.003 | 1.0 px | pass |
| Q1 | silo_cold | between | +37.500000 | between rows | altitude [m] | 5111.50 | 5111.51 | 25.56 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +37.500000 | between rows | downrange [m] | 799.05 | 799.02 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +37.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +37.500000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +37.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +37.500000 | between rows | rebuilt mass [kg] | 476744.636 | 476744.590 | 1.0 kg | pass |
| Q1 | silo_cold | between | +37.500000 | between rows | drawn attitude [deg] | 73.084 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +37.500000 | between rows | close-up attitude [deg] | 73.091 | 73.091 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +37.500000 | between rows | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q1 | pad | between | +52.000000 | row 1085 | altitude [m] | 6511.12 | 6511.73 | 32.56 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +52.000000 | row 1085 | downrange [m] | 1566.94 | 1567.60 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +52.000000 | row 1085 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +52.000000 | row 1085 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +52.000000 | row 1085 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +52.000000 | row 1085 | rebuilt mass [kg] | 429388.970 | 429388.946 | 1.0 kg | pass |
| Q1 | pad | between | +52.000000 | row 1085 | drawn attitude [deg] | 65.800 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +52.000000 | row 1085 | close-up attitude [deg] | 65.814 | 65.814 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +52.000000 | row 1085 | painted base [px off transform] | 0 | 0.031 | 1.0 px | pass |
| Q1 | silo_cold | between | +52.000000 | between rows | altitude [m] | 9119.43 | 9119.47 | 45.60 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +52.000000 | between rows | downrange [m] | 2430.10 | 2430.12 | 12.15 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +52.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +52.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +52.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +52.000000 | between rows | rebuilt mass [kg] | 437631.453 | 437631.487 | 1.0 kg | pass |
| Q1 | silo_cold | between | +52.000000 | between rows | drawn attitude [deg] | 63.133 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +52.000000 | between rows | close-up attitude [deg] | 63.155 | 63.155 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +52.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | between | +75.000000 | row 1545 | altitude [m] | 14782.71 | 14783.35 | 73.91 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +75.000000 | row 1545 | downrange [m] | 6957.39 | 6958.67 | 34.79 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +75.000000 | row 1545 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +75.000000 | row 1545 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +75.000000 | row 1545 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +75.000000 | row 1545 | rebuilt mass [kg] | 367347.370 | 367347.346 | 1.0 kg | pass |
| Q1 | pad | between | +75.000000 | row 1545 | drawn attitude [deg] | 49.945 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +75.000000 | row 1545 | close-up attitude [deg] | 50.008 | 50.009 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +75.000000 | row 1545 | painted base [px off transform] | 0 | 0.023 | 1.0 px | pass |
| Q1 | silo_cold | between | +75.000000 | between rows | altitude [m] | 18182.61 | 18182.65 | 90.91 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +75.000000 | between rows | downrange [m] | 8806.64 | 8806.69 | 44.03 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +75.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +75.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +75.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +75.000000 | between rows | rebuilt mass [kg] | 375589.853 | 375589.887 | 1.0 kg | pass |
| Q1 | silo_cold | between | +75.000000 | between rows | drawn attitude [deg] | 48.202 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +75.000000 | between rows | close-up attitude [deg] | 48.281 | 48.281 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +75.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | between | +101.000000 | row 2065 | altitude [m] | 28566.42 | 28567.08 | 142.83 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +101.000000 | row 2065 | downrange [m] | 22070.32 | 22072.35 | 110.35 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +101.000000 | row 2065 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +101.000000 | row 2065 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +101.000000 | row 2065 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +101.000000 | row 2065 | rebuilt mass [kg] | 297213.387 | 297213.421 | 1.0 kg | pass |
| Q1 | pad | between | +101.000000 | row 2065 | drawn attitude [deg] | 36.508 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +101.000000 | row 2065 | close-up attitude [deg] | 36.707 | 36.708 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +101.000000 | row 2065 | painted base [px off transform] | 0 | 0.016 | 1.0 px | pass |
| Q1 | silo_cold | between | +101.000000 | between rows | altitude [m] | 32485.38 | 32485.44 | 162.43 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +101.000000 | between rows | downrange [m] | 25215.77 | 25215.80 | 126.08 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +101.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +101.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +101.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +101.000000 | between rows | rebuilt mass [kg] | 305455.870 | 305455.887 | 1.0 kg | pass |
| Q1 | silo_cold | between | +101.000000 | between rows | drawn attitude [deg] | 35.353 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +101.000000 | between rows | close-up attitude [deg] | 35.579 | 35.580 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +101.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | between | +133.000000 | row 2705 | altitude [m] | 52146.38 | 52147.18 | 260.73 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +133.000000 | row 2705 | downrange [m] | 61608.19 | 61611.40 | 308.04 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +133.000000 | row 2705 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +133.000000 | row 2705 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +133.000000 | row 2705 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +133.000000 | row 2705 | rebuilt mass [kg] | 210894.639 | 210894.621 | 1.0 kg | pass |
| Q1 | pad | between | +133.000000 | row 2705 | drawn attitude [deg] | 26.017 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +133.000000 | row 2705 | close-up attitude [deg] | 26.571 | 26.571 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +133.000000 | row 2705 | painted base [px off transform] | 0 | 0.011 | 1.0 px | pass |
| Q1 | silo_cold | between | +133.000000 | between rows | altitude [m] | 55936.64 | 55936.68 | 279.68 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +133.000000 | between rows | downrange [m] | 66064.11 | 66064.22 | 330.32 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +133.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +133.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +133.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +133.000000 | between rows | rebuilt mass [kg] | 219137.122 | 219137.087 | 1.0 kg | pass |
| Q1 | silo_cold | between | +133.000000 | between rows | drawn attitude [deg] | 25.042 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +133.000000 | between rows | close-up attitude [deg] | 25.636 | 25.636 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +133.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +144.000000 | row 2925 | altitude [m] | 62154.25 | 62155.20 | 310.77 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +144.000000 | row 2925 | downrange [m] | 82557.16 | 82560.93 | 412.79 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +144.000000 | row 2925 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +144.000000 | row 2925 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +144.000000 | row 2925 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +144.000000 | row 2925 | rebuilt mass [kg] | 181222.570 | 181222.546 | 1.0 kg | pass |
| Q1 | pad | between | +144.000000 | row 2925 | drawn attitude [deg] | 23.520 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +144.000000 | row 2925 | close-up attitude [deg] | 24.262 | 24.262 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +144.000000 | row 2925 | painted base [px off transform] | 0 | 0.010 | 1.0 px | pass |
| Q1 | silo_cold | between | +144.000000 | between rows | altitude [m] | 65645.67 | 65645.72 | 328.23 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +144.000000 | between rows | downrange [m] | 87260.88 | 87261.02 | 436.30 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +144.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +144.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +144.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +144.000000 | between rows | rebuilt mass [kg] | 189465.053 | 189465.087 | 1.0 kg | pass |
| Q1 | silo_cold | between | +144.000000 | between rows | drawn attitude [deg] | 22.541 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +144.000000 | between rows | close-up attitude [deg] | 23.325 | 23.325 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +144.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +147.500000 | row 2995 | altitude [m] | 65583.70 | 65584.73 | 327.92 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +147.500000 | row 2995 | downrange [m] | 90205.73 | 90209.73 | 451.03 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +147.500000 | row 2995 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +147.500000 | row 2995 | stage | stage1 | stage1 | exact | pass |
| Q1 | pad | between | +147.500000 | row 2995 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +147.500000 | row 2995 | rebuilt mass [kg] | 171781.457 | 171781.471 | 1.0 kg | pass |
| Q1 | pad | between | +147.500000 | row 2995 | drawn attitude [deg] | 22.818 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +147.500000 | row 2995 | close-up attitude [deg] | 23.629 | 23.629 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +147.500000 | row 2995 | painted base [px off transform] | 0 | 0.010 | 1.0 px | pass |
| Q1 | silo_cold | between | +147.500000 | between rows | altitude [m] | 68945.27 | 68946.41 | 344.73 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +147.500000 | between rows | downrange [m] | 94953.20 | 94958.30 | 474.77 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +147.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +147.500000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | between | +147.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +147.500000 | between rows | rebuilt mass [kg] | 180023.940 | 180023.937 | 1.0 kg | pass |
| Q1 | silo_cold | between | +147.500000 | between rows | drawn attitude [deg] | 21.835 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +147.500000 | between rows | close-up attitude [deg] | 22.688 | 22.689 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +147.500000 | between rows | painted base [px off transform] | 0 | 0.013 | 1.0 px | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | altitude [m] | 69485.82 | 69485.80 | 347.43 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | downrange [m] | 99171.02 | 99171.00 | 495.86 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | thrust on | false | false | exact (event rule) | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 22.103 held | n/a | pass (held angle, drawn not computed) |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | stage-1 tank at the stage-1 propellant event [kg] | < 1 | 0.000 | under 1.0 kg | pass |
| Q1 | pad | pad:MECO; pad:staging | +151.328438 | row 3073 | stage-2 tank at MECO [kg] | 107500.0 | 107500.0 | equals the stage-2 load before stage-2 ignition, 1 kg | pass |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | altitude [m] | 72683.54 | 72684.61 | 363.42 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | downrange [m] | 103942.57 | 103947.40 | 519.71 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | stage | stage1 | stage1 | exact | pass |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | rebuilt mass [kg] | 169696.878 | 169696.859 | 1.0 kg | pass |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | drawn attitude [deg] | 21.107 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | close-up attitude [deg] | 22.041 | 22.041 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | other run's event | +151.328438 | between rows | painted base [px off transform] | 0 | 0.011 | 1.0 px | pass |
| Q1 | pad | other run's event | +153.828438 | between rows | altitude [m] | 72061.96 | 72061.34 | 360.31 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | +153.828438 | between rows | downrange [m] | 105235.49 | 105235.41 | 526.18 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | +153.828438 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q1 | pad | other run's event | +153.828438 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | other run's event | +153.828438 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | pad | other run's event | +153.828438 | between rows | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q1 | pad | other run's event | +153.828438 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 22.103 held | n/a | pass (held angle, drawn not computed) |
| Q1 | pad | other run's event | +153.828438 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | altitude [m] | 75202.25 | 75202.20 | 376.01 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | downrange [m] | 110154.82 | 110154.80 | 550.77 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | rebuilt mass [kg] | 140753.227 | 140753.227 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 20.663 held | n/a | pass (held angle, drawn not computed) |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | stage-1 tank at the stage-1 propellant event [kg] | < 1 | 0.000 | under 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:MECO; silo_cold:staging | +153.828438 | row 3138 | stage-2 tank at MECO [kg] | 107500.0 | 107500.0 | equals the stage-2 load before stage-2 ignition, 1 kg | pass |
| Q1 | pad | between | +155.500000 | row 3157 | altitude [m] | 73755.45 | 73754.93 | 368.78 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +155.500000 | row 3157 | downrange [m] | 109287.21 | 109287.17 | 546.44 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +155.500000 | row 3157 | thrust on | false | false | exact (event rule) | pass |
| Q1 | pad | between | +155.500000 | row 3157 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +155.500000 | row 3157 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | pad | between | +155.500000 | row 3157 | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q1 | pad | between | +155.500000 | row 3157 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 22.103 held | n/a | pass (held angle, drawn not computed) |
| Q1 | pad | between | +155.500000 | row 3157 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +155.500000 | between rows | altitude [m] | 76896.29 | 76895.27 | 384.48 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +155.500000 | between rows | downrange [m] | 114400.80 | 114400.68 | 572.00 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +155.500000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | between | +155.500000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +155.500000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +155.500000 | between rows | rebuilt mass [kg] | 140753.227 | 140753.227 | 1.0 kg | pass |
| Q1 | silo_cold | between | +155.500000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 20.663 held | n/a | pass (held angle, drawn not computed) |
| Q1 | silo_cold | between | +155.500000 | between rows | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q1 | pad | between | +159.000000 | row 3227 | altitude [m] | 77226.24 | 77225.26 | 386.13 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +159.000000 | row 3227 | downrange [m] | 117762.92 | 117762.80 | 588.81 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +159.000000 | row 3227 | thrust on | false | false | exact (event rule) | pass |
| Q1 | pad | between | +159.000000 | row 3227 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +159.000000 | row 3227 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | pad | between | +159.000000 | row 3227 | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q1 | pad | between | +159.000000 | row 3227 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 22.103 held | n/a | pass (held angle, drawn not computed) |
| Q1 | pad | between | +159.000000 | row 3227 | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q1 | silo_cold | between | +159.000000 | between rows | altitude [m] | 80369.26 | 80368.90 | 401.85 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +159.000000 | between rows | downrange [m] | 123282.96 | 123282.94 | 616.41 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +159.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | between | +159.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +159.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +159.000000 | between rows | rebuilt mass [kg] | 140753.227 | 140753.227 | 1.0 kg | pass |
| Q1 | silo_cold | between | +159.000000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 20.663 held | n/a | pass (held angle, drawn not computed) |
| Q1 | silo_cold | between | +159.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | altitude [m] | 80432.61 | 80432.60 | 402.16 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | downrange [m] | 125813.41 | 125813.40 | 629.07 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | drawn attitude [deg] | 30.261 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | close-up attitude [deg] | 31.391 | 31.391 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | pad:ignition_s2 | +162.328438 | row 3295 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | other run's event | +162.328438 | between rows | altitude [m] | 83579.04 | 83578.06 | 417.90 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | other run's event | +162.328438 | between rows | downrange [m] | 131719.58 | 131719.46 | 658.60 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | other run's event | +162.328438 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | other run's event | +162.328438 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | other run's event | +162.328438 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q1 | silo_cold | other run's event | +162.328438 | between rows | rebuilt mass [kg] | 140753.227 | 140753.227 | 1.0 kg | pass |
| Q1 | silo_cold | other run's event | +162.328438 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 20.663 held | n/a | pass (held angle, drawn not computed) |
| Q1 | silo_cold | other run's event | +162.328438 | between rows | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q1 | pad | other run's event | +164.828438 | between rows | altitude [m] | 82792.02 | 82791.60 | 413.96 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | +164.828438 | between rows | downrange [m] | 131872.68 | 131873.17 | 659.36 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | +164.828438 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | other run's event | +164.828438 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | other run's event | +164.828438 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | other run's event | +164.828438 | between rows | rebuilt mass [kg] | 138535.760 | 138535.745 | 1.0 kg | pass |
| Q1 | pad | other run's event | +164.828438 | between rows | drawn attitude [deg] | 30.043 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | other run's event | +164.828438 | between rows | close-up attitude [deg] | 31.228 | 31.228 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | other run's event | +164.828438 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | altitude [m] | 85930.38 | 85930.40 | 429.65 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | downrange [m] | 138050.02 | 138050.00 | 690.25 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | rebuilt mass [kg] | 140753.227 | 140753.227 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | drawn attitude [deg] | 29.392 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | close-up attitude [deg] | 30.632 | 30.632 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | silo_cold:ignition_s2 | +164.828438 | row 3360 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +166.000000 | row 3369 | altitude [m] | 83887.80 | 83887.28 | 419.44 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +166.000000 | row 3369 | downrange [m] | 134723.26 | 134723.88 | 673.62 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +166.000000 | row 3369 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +166.000000 | row 3369 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +166.000000 | row 3369 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +166.000000 | row 3369 | rebuilt mass [kg] | 138198.989 | 138198.966 | 1.0 kg | pass |
| Q1 | pad | between | +166.000000 | row 3369 | drawn attitude [deg] | 29.941 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +166.000000 | row 3369 | close-up attitude [deg] | 31.151 | 31.151 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +166.000000 | row 3369 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +166.000000 | between rows | altitude [m] | 87017.15 | 87016.78 | 435.09 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +166.000000 | between rows | downrange [m] | 141018.86 | 141019.28 | 705.09 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +166.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +166.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +166.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +166.000000 | between rows | rebuilt mass [kg] | 140416.456 | 140416.444 | 1.0 kg | pass |
| Q1 | silo_cold | between | +166.000000 | between rows | drawn attitude [deg] | 29.291 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +166.000000 | between rows | close-up attitude [deg] | 30.558 | 30.558 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +166.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | between | +175.000000 | row 3549 | altitude [m] | 92096.64 | 92096.07 | 460.48 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +175.000000 | row 3549 | downrange [m] | 156860.66 | 156861.31 | 784.30 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +175.000000 | row 3549 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +175.000000 | row 3549 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +175.000000 | row 3549 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +175.000000 | row 3549 | rebuilt mass [kg] | 135611.899 | 135611.921 | 1.0 kg | pass |
| Q1 | pad | between | +175.000000 | row 3549 | drawn attitude [deg] | 29.149 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +175.000000 | row 3549 | close-up attitude [deg] | 30.558 | 30.558 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +175.000000 | row 3549 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +175.000000 | between rows | altitude [m] | 95155.96 | 95155.56 | 475.78 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +175.000000 | between rows | downrange [m] | 164060.87 | 164061.34 | 820.30 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +175.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +175.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +175.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +175.000000 | between rows | rebuilt mass [kg] | 137829.366 | 137829.344 | 1.0 kg | pass |
| Q1 | silo_cold | between | +175.000000 | between rows | drawn attitude [deg] | 28.510 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +175.000000 | between rows | close-up attitude [deg] | 29.984 | 29.985 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +175.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | between | +188.000000 | row 3809 | altitude [m] | 103310.07 | 103309.53 | 516.55 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +188.000000 | row 3809 | downrange [m] | 189604.73 | 189605.40 | 948.02 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +188.000000 | row 3809 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +188.000000 | row 3809 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +188.000000 | row 3809 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +188.000000 | row 3809 | rebuilt mass [kg] | 131874.991 | 131874.966 | 1.0 kg | pass |
| Q1 | pad | between | +188.000000 | row 3809 | drawn attitude [deg] | 27.985 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +188.000000 | row 3809 | close-up attitude [deg] | 29.688 | 29.688 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +188.000000 | row 3809 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +188.000000 | between rows | altitude [m] | 106265.74 | 106265.39 | 531.33 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +188.000000 | between rows | downrange [m] | 198099.20 | 198099.67 | 990.50 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +188.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +188.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +188.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +188.000000 | between rows | rebuilt mass [kg] | 134092.458 | 134092.444 | 1.0 kg | pass |
| Q1 | silo_cold | between | +188.000000 | between rows | drawn attitude [deg] | 27.364 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +188.000000 | between rows | close-up attitude [deg] | 29.144 | 29.144 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +188.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | between | +192.500000 | row 3899 | altitude [m] | 107017.26 | 107017.20 | 535.09 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +192.500000 | row 3899 | downrange [m] | 201157.40 | 201157.53 | 1005.79 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +192.500000 | row 3899 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +192.500000 | row 3899 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +192.500000 | row 3899 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +192.500000 | row 3899 | rebuilt mass [kg] | 130581.445 | 130581.466 | 1.0 kg | pass |
| Q1 | pad | between | +192.500000 | row 3899 | drawn attitude [deg] | 27.577 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +192.500000 | row 3899 | close-up attitude [deg] | 29.384 | 29.384 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +192.500000 | row 3899 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | between | +192.500000 | between rows | altitude [m] | 109936.38 | 109935.89 | 549.68 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +192.500000 | between rows | downrange [m] | 210096.32 | 210096.87 | 1050.48 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +192.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +192.500000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +192.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +192.500000 | between rows | rebuilt mass [kg] | 132798.912 | 132798.944 | 1.0 kg | pass |
| Q1 | silo_cold | between | +192.500000 | between rows | drawn attitude [deg] | 26.962 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +192.500000 | between rows | close-up attitude [deg] | 28.849 | 28.849 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +192.500000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | other run's event | +193.816497 | between rows | altitude [m] | 108085.06 | 108084.62 | 540.43 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | +193.816497 | between rows | downrange [m] | 204558.88 | 204559.43 | 1022.79 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | +193.816497 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | other run's event | +193.816497 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | other run's event | +193.816497 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | other run's event | +193.816497 | between rows | rebuilt mass [kg] | 130203.012 | 130203.005 | 1.0 kg | pass |
| Q1 | pad | other run's event | +193.816497 | between rows | drawn attitude [deg] | 27.457 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | other run's event | +193.816497 | between rows | close-up attitude [deg] | 29.294 | 29.294 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | other run's event | +193.816497 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | altitude [m] | 110993.43 | 110993.40 | 554.97 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | downrange [m] | 213627.47 | 213627.50 | 1068.14 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | rebuilt mass [kg] | 130720.480 | 130720.527 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | drawn attitude [deg] | 26.844 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | close-up attitude [deg] | 28.763 | 28.763 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | silo_cold:fairing | +193.816497 | row 3942 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | altitude [m] | 110483.04 | 110483.00 | 552.42 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | downrange [m] | 212323.82 | 212323.80 | 1061.62 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | rebuilt mass [kg] | 127643.226 | 127643.196 | 1.0 kg | pass |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | drawn attitude [deg] | 27.183 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | close-up attitude [deg] | 29.091 | 29.090 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | pad:fairing | +196.807531 | row 3987 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | altitude [m] | 113367.05 | 113366.81 | 566.84 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | downrange [m] | 221686.77 | 221687.10 | 1108.43 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | rebuilt mass [kg] | 129860.693 | 129860.708 | 1.0 kg | pass |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | drawn attitude [deg] | 26.575 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | close-up attitude [deg] | 28.566 | 28.566 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | other run's event | +196.807531 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +205.000000 | row 4151 | altitude [m] | 116855.01 | 116854.49 | 584.28 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +205.000000 | row 4151 | downrange [m] | 233861.27 | 233862.01 | 1169.31 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +205.000000 | row 4151 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +205.000000 | row 4151 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +205.000000 | row 4151 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +205.000000 | row 4151 | rebuilt mass [kg] | 125288.264 | 125288.271 | 1.0 kg | pass |
| Q1 | pad | between | +205.000000 | row 4151 | drawn attitude [deg] | 26.427 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +205.000000 | row 4151 | close-up attitude [deg] | 28.528 | 28.528 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +205.000000 | row 4151 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +205.000000 | between rows | altitude [m] | 119672.07 | 119671.62 | 598.36 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +205.000000 | between rows | downrange [m] | 244026.96 | 244027.57 | 1220.13 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +205.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +205.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +205.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +205.000000 | between rows | rebuilt mass [kg] | 127505.731 | 127505.704 | 1.0 kg | pass |
| Q1 | silo_cold | between | +205.000000 | between rows | drawn attitude [deg] | 25.831 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +205.000000 | between rows | close-up attitude [deg] | 28.023 | 28.023 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +205.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | between | +260.000000 | row 5251 | altitude [m] | 152548.45 | 152547.95 | 762.74 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +260.000000 | row 5251 | downrange [m] | 389573.06 | 389573.94 | 1947.87 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +260.000000 | row 5251 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +260.000000 | row 5251 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +260.000000 | row 5251 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +260.000000 | row 5251 | rebuilt mass [kg] | 109478.268 | 109478.271 | 1.0 kg | pass |
| Q1 | pad | between | +260.000000 | row 5251 | drawn attitude [deg] | 21.096 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +260.000000 | row 5251 | close-up attitude [deg] | 24.596 | 24.596 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +260.000000 | row 5251 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +260.000000 | between rows | altitude [m] | 154884.40 | 154883.99 | 774.42 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +260.000000 | between rows | downrange [m] | 404930.85 | 404931.60 | 2024.65 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +260.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +260.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +260.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +260.000000 | between rows | rebuilt mass [kg] | 111695.735 | 111695.704 | 1.0 kg | pass |
| Q1 | silo_cold | between | +260.000000 | between rows | drawn attitude [deg] | 20.599 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +260.000000 | between rows | close-up attitude [deg] | 24.237 | 24.236 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +260.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | between | +350.000000 | row 7051 | altitude [m] | 187386.43 | 187386.10 | 936.93 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +350.000000 | row 7051 | downrange [m] | 695169.61 | 695170.92 | 3475.85 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +350.000000 | row 7051 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +350.000000 | row 7051 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +350.000000 | row 7051 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +350.000000 | row 7051 | rebuilt mass [kg] | 83607.364 | 83607.371 | 1.0 kg | pass |
| Q1 | pad | between | +350.000000 | row 7051 | drawn attitude [deg] | 11.358 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +350.000000 | row 7051 | close-up attitude [deg] | 17.602 | 17.603 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +350.000000 | row 7051 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | between | +350.000000 | between rows | altitude [m] | 188847.60 | 188847.31 | 944.24 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +350.000000 | between rows | downrange [m] | 717986.15 | 717987.25 | 3589.93 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +350.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +350.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +350.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +350.000000 | between rows | rebuilt mass [kg] | 85824.831 | 85824.804 | 1.0 kg | pass |
| Q1 | silo_cold | between | +350.000000 | between rows | drawn attitude [deg] | 11.083 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +350.000000 | between rows | close-up attitude [deg] | 17.533 | 17.533 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +350.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +444.000000 | row 8931 | altitude [m] | 199815.57 | 199815.38 | 999.08 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +444.000000 | row 8931 | downrange [m] | 1107854.74 | 1107856.74 | 5539.27 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +444.000000 | row 8931 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +444.000000 | row 8931 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +444.000000 | row 8931 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +444.000000 | row 8931 | rebuilt mass [kg] | 56586.643 | 56586.626 | 1.0 kg | pass |
| Q1 | pad | between | +444.000000 | row 8931 | drawn attitude [deg] | -0.274 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +444.000000 | row 8931 | close-up attitude [deg] | 9.678 | 9.678 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +444.000000 | row 8931 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | between | +444.000000 | between rows | altitude [m] | 200380.86 | 200380.73 | 1001.90 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +444.000000 | between rows | downrange [m] | 1135949.05 | 1135950.75 | 5679.75 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +444.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +444.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +444.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +444.000000 | between rows | rebuilt mass [kg] | 58804.110 | 58804.104 | 1.0 kg | pass |
| Q1 | silo_cold | between | +444.000000 | between rows | drawn attitude [deg] | -0.239 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +444.000000 | between rows | close-up attitude [deg] | 9.965 | 9.965 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +444.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +460.000000 | row 9251 | altitude [m] | 200273.24 | 200273.07 | 1001.37 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +460.000000 | row 9251 | downrange [m] | 1190921.80 | 1190924.05 | 5954.61 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +460.000000 | row 9251 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +460.000000 | row 9251 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +460.000000 | row 9251 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +460.000000 | row 9251 | rebuilt mass [kg] | 51987.371 | 51987.371 | 1.0 kg | pass |
| Q1 | pad | between | +460.000000 | row 9251 | drawn attitude [deg] | -2.416 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +460.000000 | row 9251 | close-up attitude [deg] | 8.282 | 8.282 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +460.000000 | row 9251 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | between | +460.000000 | between rows | altitude [m] | 200706.78 | 200706.67 | 1003.53 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +460.000000 | between rows | downrange [m] | 1219473.57 | 1219475.40 | 6097.37 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +460.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +460.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +460.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +460.000000 | between rows | rebuilt mass [kg] | 54204.838 | 54204.873 | 1.0 kg | pass |
| Q1 | silo_cold | between | +460.000000 | between rows | drawn attitude [deg] | -2.321 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +460.000000 | between rows | close-up attitude [deg] | 8.634 | 8.633 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +460.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +480.000000 | row 9651 | altitude [m] | 200437.51 | 200437.43 | 1002.19 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +480.000000 | row 9651 | downrange [m] | 1301323.92 | 1301326.46 | 6506.62 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +480.000000 | row 9651 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +480.000000 | row 9651 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +480.000000 | row 9651 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +480.000000 | row 9651 | rebuilt mass [kg] | 46238.281 | 46238.271 | 1.0 kg | pass |
| Q1 | pad | between | +480.000000 | row 9651 | drawn attitude [deg] | -5.166 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +480.000000 | row 9651 | close-up attitude [deg] | 6.524 | 6.524 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +480.000000 | row 9651 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +480.000000 | between rows | altitude [m] | 200722.07 | 200722.03 | 1003.61 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +480.000000 | between rows | downrange [m] | 1330174.37 | 1330176.46 | 6650.87 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +480.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +480.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +480.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +480.000000 | between rows | rebuilt mass [kg] | 48455.748 | 48455.773 | 1.0 kg | pass |
| Q1 | silo_cold | between | +480.000000 | between rows | drawn attitude [deg] | -4.993 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +480.000000 | between rows | close-up attitude [deg] | 6.956 | 6.956 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +480.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +500.000000 | row 10051 | altitude [m] | 200310.59 | 200310.58 | 1001.55 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +500.000000 | row 10051 | downrange [m] | 1419921.86 | 1419924.72 | 7099.61 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +500.000000 | row 10051 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +500.000000 | row 10051 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +500.000000 | row 10051 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +500.000000 | row 10051 | rebuilt mass [kg] | 40489.191 | 40489.171 | 1.0 kg | pass |
| Q1 | pad | between | +500.000000 | row 10051 | drawn attitude [deg] | -8.003 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +500.000000 | row 10051 | close-up attitude [deg] | 4.753 | 4.752 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +500.000000 | row 10051 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +500.000000 | between rows | altitude [m] | 200468.13 | 200468.12 | 1002.34 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +500.000000 | between rows | downrange [m] | 1448691.99 | 1448694.36 | 7243.46 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +500.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +500.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +500.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +500.000000 | between rows | rebuilt mass [kg] | 42706.659 | 42706.673 | 1.0 kg | pass |
| Q1 | silo_cold | between | +500.000000 | between rows | drawn attitude [deg] | -7.748 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +500.000000 | between rows | close-up attitude [deg] | 5.266 | 5.266 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +500.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +515.000000 | row 10351 | altitude [m] | 200142.32 | 200142.35 | 1000.71 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +515.000000 | row 10351 | downrange [m] | 1514962.45 | 1514965.71 | 7574.81 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +515.000000 | row 10351 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +515.000000 | row 10351 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +515.000000 | row 10351 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +515.000000 | row 10351 | rebuilt mass [kg] | 36177.374 | 36177.371 | 1.0 kg | pass |
| Q1 | pad | between | +515.000000 | row 10351 | drawn attitude [deg] | -10.191 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +515.000000 | row 10351 | close-up attitude [deg] | 3.418 | 3.418 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +515.000000 | row 10351 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +515.000000 | between rows | altitude [m] | 200222.45 | 200222.47 | 1001.11 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +515.000000 | between rows | downrange [m] | 1543356.60 | 1543359.24 | 7716.78 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +515.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +515.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +515.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +515.000000 | between rows | rebuilt mass [kg] | 38394.841 | 38394.873 | 1.0 kg | pass |
| Q1 | silo_cold | between | +515.000000 | between rows | drawn attitude [deg] | -9.872 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +515.000000 | between rows | close-up attitude [deg] | 3.992 | 3.992 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +515.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +525.000000 | row 10551 | altitude [m] | 200046.99 | 200047.02 | 1000.23 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +525.000000 | row 10551 | downrange [m] | 1581568.05 | 1581571.60 | 7907.84 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +525.000000 | row 10551 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +525.000000 | row 10551 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +525.000000 | row 10551 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +525.000000 | row 10551 | rebuilt mass [kg] | 33302.829 | 33302.826 | 1.0 kg | pass |
| Q1 | pad | between | +525.000000 | row 10551 | drawn attitude [deg] | -11.681 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +525.000000 | row 10551 | close-up attitude [deg] | 2.526 | 2.526 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +525.000000 | row 10551 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +525.000000 | between rows | altitude [m] | 200085.67 | 200085.76 | 1000.43 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +525.000000 | between rows | downrange [m] | 1609525.19 | 1609528.03 | 8047.63 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +525.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +525.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +525.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +525.000000 | between rows | rebuilt mass [kg] | 35520.296 | 35520.304 | 1.0 kg | pass |
| Q1 | silo_cold | between | +525.000000 | between rows | drawn attitude [deg] | -11.318 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +525.000000 | between rows | close-up attitude [deg] | 3.141 | 3.141 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +525.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | between | +535.000000 | row 10751 | altitude [m] | 200000.70 | 200000.79 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | between | +535.000000 | row 10751 | downrange [m] | 1651032.12 | 1651036.02 | 8255.16 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | between | +535.000000 | row 10751 | thrust on | true | true | exact (event rule) | pass |
| Q1 | pad | between | +535.000000 | row 10751 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | between | +535.000000 | row 10751 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | pad | between | +535.000000 | row 10751 | rebuilt mass [kg] | 30428.284 | 30428.271 | 1.0 kg | pass |
| Q1 | pad | between | +535.000000 | row 10751 | drawn attitude [deg] | -13.199 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | pad | between | +535.000000 | row 10751 | close-up attitude [deg] | 1.633 | 1.633 | 0.5 deg (close-up base and nose) | pass |
| Q1 | pad | between | +535.000000 | row 10751 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | silo_cold | between | +535.000000 | between rows | altitude [m] | 200007.34 | 200007.39 | 1000.04 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | between | +535.000000 | between rows | downrange [m] | 1678372.86 | 1678375.93 | 8391.86 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | between | +535.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | between | +535.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | between | +535.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | between | +535.000000 | between rows | rebuilt mass [kg] | 32645.752 | 32645.773 | 1.0 kg | pass |
| Q1 | silo_cold | between | +535.000000 | between rows | drawn attitude [deg] | -12.789 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | between | +535.000000 | between rows | close-up attitude [deg] | 2.288 | 2.288 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | between | +535.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | pad | pad:cutoff; pad:end | +536.300685 | last row 10778 | altitude [m] | 199999.98 | 200000.00 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | pad:cutoff; pad:end | +536.300685 | last row 10778 | downrange [m] | 1660290.86 | 1660290.90 | 8301.45 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | pad:cutoff; pad:end | +536.300685 | last row 10778 | thrust on | false | false | exact (event rule) | pass |
| Q1 | pad | pad:cutoff; pad:end | +536.300685 | last row 10778 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | pad:cutoff; pad:end | +536.300685 | last row 10778 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q1 | pad | pad:cutoff; pad:end | +536.300685 | last row 10778 | rebuilt mass [kg] | 30054.397 | 30054.396 | 1.0 kg | pass |
| Q1 | pad | pad:cutoff; pad:end | +536.300685 | last row 10778 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | -13.398 held | n/a | pass (held angle, drawn not computed) |
| Q1 | pad | pad:cutoff; pad:end | +536.300685 | last row 10778 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | altitude [m] | 200003.21 | 200003.32 | 1000.02 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | downrange [m] | 1687536.56 | 1687540.03 | 8437.68 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | rebuilt mass [kg] | 32271.864 | 32271.887 | 1.0 kg | pass |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | drawn attitude [deg] | -12.982 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | close-up attitude [deg] | 2.177 | 2.177 | 0.5 deg (close-up base and nose) | pass |
| Q1 | silo_cold | other run's event | +536.300685 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q1 | pad | other run's event | +538.800685 | last row 10778 | altitude [m] | 199999.98 | 200000.00 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q1 | pad | other run's event | +538.800685 | last row 10778 | downrange [m] | 1660290.86 | 1660290.90 | 8301.45 (larger of 0.5% and 10 m) | pass |
| Q1 | pad | other run's event | +538.800685 | last row 10778 | thrust on | false | false | exact (event rule) | pass |
| Q1 | pad | other run's event | +538.800685 | last row 10778 | stage | stage2 | stage2 | exact | pass |
| Q1 | pad | other run's event | +538.800685 | last row 10778 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q1 | pad | other run's event | +538.800685 | last row 10778 | rebuilt mass [kg] | 30054.397 | 30054.396 | 1.0 kg | pass |
| Q1 | pad | other run's event | +538.800685 | last row 10778 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | -13.398 held | n/a | pass (held angle, drawn not computed) |
| Q1 | pad | other run's event | +538.800685 | last row 10778 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q1 | silo_cold | silo_cold:cutoff; silo_cold:end | +538.800685 | last row 10843 | altitude [m] | 199999.98 | 200000.00 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q1 | silo_cold | silo_cold:cutoff; silo_cold:end | +538.800685 | last row 10843 | downrange [m] | 1705290.25 | 1705290.20 | 8526.45 (larger of 0.5% and 10 m) | pass |
| Q1 | silo_cold | silo_cold:cutoff; silo_cold:end | +538.800685 | last row 10843 | thrust on | false | false | exact (event rule) | pass |
| Q1 | silo_cold | silo_cold:cutoff; silo_cold:end | +538.800685 | last row 10843 | stage | stage2 | stage2 | exact | pass |
| Q1 | silo_cold | silo_cold:cutoff; silo_cold:end | +538.800685 | last row 10843 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q1 | silo_cold | silo_cold:cutoff; silo_cold:end | +538.800685 | last row 10843 | rebuilt mass [kg] | 31553.228 | 31553.227 | 1.0 kg | pass |
| Q1 | silo_cold | silo_cold:cutoff; silo_cold:end | +538.800685 | last row 10843 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | -13.354 held | n/a | pass (held angle, drawn not computed) |
| Q1 | silo_cold | silo_cold:cutoff; silo_cold:end | +538.800685 | last row 10843 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | altitude [m] | -100.00 | -100.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | thrust on | false | false | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | rebuilt mass [kg] | 574088.201 | 574088.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | tank start fill stage 1 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:push_start | -2.607318 | first row 0 | tank start fill stage 2 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | altitude [m] | -94.57 | -94.60 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | rebuilt mass [kg] | 574088.201 | 574088.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s1 | -2.000000 | row 14 | painted base [px off transform] | 0 | 0.041 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | altitude [m] | -75.14 | -75.10 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | plume fraction | 0.3463 | 0.3460 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | rebuilt mass [kg] | 573764.635 | 573764.601 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:mid_push | -1.307318 | row 28 | painted base [px off transform] | 0 | 0.065 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | altitude [m] | -74.85 | -74.82 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | plume fraction | 0.3500 | 0.3497 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | rebuilt mass [kg] | 573757.551 | 573757.517 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | -1.300000 | between rows | painted base [px off transform] | 0 | 0.053 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | rebuilt mass [kg] | 571390.740 | 571390.701 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | drawn attitude [deg] | 86.343 | 86.343 | 0.5 deg (painted base and nose, to scale) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | close-up attitude [deg] | 86.343 | 86.343 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ramp_end; silo_hot_ramp_on_track:release; silo_hot_ramp_on_track:kick_start | +0.000000 | row 56 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | altitude [m] | 70.46 | 70.49 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | downrange [m] | 0.34 | 0.31 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | rebuilt mass [kg] | 568963.025 | 568963.057 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | drawn attitude [deg] | 86.343 | 86.343 | 0.5 deg (painted base and nose, to scale) | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | close-up attitude [deg] | 86.343 | 86.343 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +0.900000 | between rows | painted base [px off transform] | 0 | 0.054 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | altitude [m] | 127.24 | 127.21 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | downrange [m] | 1.08 | 1.11 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | rebuilt mass [kg] | 567074.803 | 567074.764 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | drawn attitude [deg] | 86.343 | 86.343 | 0.5 deg (painted base and nose, to scale) | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | close-up attitude [deg] | 86.343 | 86.343 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +1.600000 | between rows | painted base [px off transform] | 0 | 0.049 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | altitude [m] | 353.80 | 353.77 | 1.77 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | downrange [m] | 7.45 | 7.43 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | rebuilt mass [kg] | 560061.404 | 560061.364 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | drawn attitude [deg] | 86.343 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | close-up attitude [deg] | 86.343 | 86.343 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +4.200000 | between rows | painted base [px off transform] | 0 | 0.023 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | altitude [m] | 730.22 | 730.20 | 3.65 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | downrange [m] | 27.12 | 27.10 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | rebuilt mass [kg] | 549840.822 | 549840.801 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | drawn attitude [deg] | 86.343 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | close-up attitude [deg] | 86.343 | 86.343 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:kick_end | +7.988964 | row 217 | painted base [px off transform] | 0 | 0.010 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | altitude [m] | 919.15 | 919.13 | 4.60 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | downrange [m] | 40.15 | 40.16 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | rebuilt mass [kg] | 545225.370 | 545225.364 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | drawn attitude [deg] | 85.760 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | close-up attitude [deg] | 85.761 | 85.761 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +9.700000 | between rows | painted base [px off transform] | 0 | 0.007 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | altitude [m] | 1254.28 | 1254.23 | 6.27 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | downrange [m] | 68.09 | 68.11 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | rebuilt mass [kg] | 537689.395 | 537689.377 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | drawn attitude [deg] | 84.705 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | close-up attitude [deg] | 84.705 | 84.705 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +12.493729 | between rows | painted base [px off transform] | 0 | 0.013 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | altitude [m] | 1983.08 | 1983.10 | 9.92 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | downrange [m] | 150.60 | 150.63 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | rebuilt mass [kg] | 523446.033 | 523446.049 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | drawn attitude [deg] | 82.370 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | close-up attitude [deg] | 82.371 | 82.371 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +17.774014 | between rows | painted base [px off transform] | 0 | 0.005 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | altitude [m] | 2493.52 | 2493.51 | 12.47 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | downrange [m] | 226.36 | 226.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | rebuilt mass [kg] | 514744.062 | 514744.064 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | drawn attitude [deg] | 80.740 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | close-up attitude [deg] | 80.742 | 80.742 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +21.000000 | between rows | painted base [px off transform] | 0 | 0.004 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | altitude [m] | 5969.09 | 5969.09 | 29.85 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | downrange [m] | 1125.02 | 1125.06 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | rebuilt mass [kg] | 470235.957 | 470235.964 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | drawn attitude [deg] | 70.651 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | close-up attitude [deg] | 70.661 | 70.661 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +37.500000 | between rows | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | altitude [m] | 10340.23 | 10340.49 | 51.70 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | downrange [m] | 3121.57 | 3121.94 | 15.61 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | rebuilt mass [kg] | 431122.775 | 431122.801 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | drawn attitude [deg] | 60.745 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | close-up attitude [deg] | 60.774 | 60.773 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +52.000000 | between rows | painted base [px off transform] | 0 | 0.014 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | altitude [m] | 19953.99 | 19954.26 | 99.77 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | downrange [m] | 10428.05 | 10428.68 | 52.14 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | rebuilt mass [kg] | 369081.175 | 369081.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | drawn attitude [deg] | 46.299 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | close-up attitude [deg] | 46.392 | 46.393 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +75.000000 | between rows | painted base [px off transform] | 0 | 0.010 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | altitude [m] | 34804.78 | 34805.02 | 174.02 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | downrange [m] | 28409.76 | 28410.70 | 142.05 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | rebuilt mass [kg] | 298947.192 | 298947.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | drawn attitude [deg] | 34.037 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | close-up attitude [deg] | 34.293 | 34.293 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +101.000000 | between rows | painted base [px off transform] | 0 | 0.006 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | altitude [m] | 58842.01 | 58842.29 | 294.21 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | downrange [m] | 71980.68 | 71982.12 | 359.90 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | rebuilt mass [kg] | 212628.444 | 212628.411 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | drawn attitude [deg] | 24.205 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | close-up attitude [deg] | 24.852 | 24.853 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +133.000000 | between rows | painted base [px off transform] | 0 | 0.005 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | altitude [m] | 68762.57 | 68762.91 | 343.81 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | downrange [m] | 94370.44 | 94372.14 | 471.85 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | rebuilt mass [kg] | 182956.375 | 182956.401 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | drawn attitude [deg] | 21.818 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | close-up attitude [deg] | 22.666 | 22.666 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +144.000000 | between rows | painted base [px off transform] | 0 | 0.004 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | altitude [m] | 72134.70 | 72135.82 | 360.67 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | downrange [m] | 102479.17 | 102484.28 | 512.40 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | rebuilt mass [kg] | 173515.261 | 173515.261 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | drawn attitude [deg] | 21.144 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | close-up attitude [deg] | 22.064 | 22.064 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +147.500000 | between rows | painted base [px off transform] | 0 | 0.012 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | altitude [m] | 75956.55 | 75956.60 | 379.78 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | downrange [m] | 111947.75 | 111947.80 | 559.74 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | thrust on | false | false | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | rebuilt mass [kg] | 140988.201 | 140988.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 20.456 held | n/a | pass (held angle, drawn not computed) |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | stage-1 tank at the stage-1 propellant event [kg] | < 1 | 0.000 | under 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:MECO; silo_hot_ramp_on_track:staging | +151.328438 | row 3086 | stage-2 tank at MECO [kg] | 107500.0 | 107500.0 | equals the stage-2 load before stage-2 ignition, 1 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +155.500000 | between rows | altitude [m] | 80129.63 | 80128.60 | 400.65 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +155.500000 | between rows | downrange [m] | 122611.92 | 122611.84 | 613.06 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +155.500000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +155.500000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +155.500000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +155.500000 | between rows | rebuilt mass [kg] | 140988.201 | 140988.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +155.500000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 20.456 held | n/a | pass (held angle, drawn not computed) |
| Q2 | silo_hot_ramp_on_track | between | +155.500000 | between rows | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +159.000000 | between rows | altitude [m] | 83521.31 | 83521.26 | 417.61 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +159.000000 | between rows | downrange [m] | 131547.16 | 131547.17 | 657.74 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +159.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +159.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +159.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +159.000000 | between rows | rebuilt mass [kg] | 140988.201 | 140988.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +159.000000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 20.456 held | n/a | pass (held angle, drawn not computed) |
| Q2 | silo_hot_ramp_on_track | between | +159.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | altitude [m] | 86654.05 | 86654.10 | 433.27 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | downrange [m] | 140034.46 | 140034.50 | 700.17 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | rebuilt mass [kg] | 140988.201 | 140988.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | drawn attitude [deg] | 29.267 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | close-up attitude [deg] | 30.525 | 30.525 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:ignition_s2 | +162.328438 | row 3308 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | altitude [m] | 90028.92 | 90028.74 | 450.14 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | downrange [m] | 149425.75 | 149426.02 | 747.13 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | rebuilt mass [kg] | 139932.794 | 139932.758 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | drawn attitude [deg] | 28.951 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | close-up attitude [deg] | 30.293 | 30.293 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +166.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | altitude [m] | 98041.15 | 98040.96 | 490.21 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | downrange [m] | 172740.78 | 172741.07 | 863.70 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | rebuilt mass [kg] | 137345.704 | 137345.747 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | drawn attitude [deg] | 28.168 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | close-up attitude [deg] | 29.720 | 29.719 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +175.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | altitude [m] | 108971.29 | 108971.06 | 544.86 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | downrange [m] | 207179.21 | 207179.44 | 1035.90 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | rebuilt mass [kg] | 133608.795 | 133608.758 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | drawn attitude [deg] | 27.019 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | close-up attitude [deg] | 28.880 | 28.880 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +188.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | altitude [m] | 111074.66 | 111074.70 | 555.37 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | downrange [m] | 214202.15 | 214202.20 | 1071.01 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | rebuilt mass [kg] | 131158.844 | 131158.801 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | drawn attitude [deg] | 26.786 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | close-up attitude [deg] | 28.710 | 28.710 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:fairing | +190.608939 | row 3876 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | altitude [m] | 112580.71 | 112580.24 | 562.90 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | downrange [m] | 219316.60 | 219317.18 | 1096.58 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | rebuilt mass [kg] | 130615.250 | 130615.247 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | drawn attitude [deg] | 26.616 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | close-up attitude [deg] | 28.586 | 28.587 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +192.500000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | altitude [m] | 115953.73 | 115953.66 | 579.77 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | downrange [m] | 231043.06 | 231043.05 | 1155.22 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | rebuilt mass [kg] | 129377.031 | 129377.032 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | drawn attitude [deg] | 26.228 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | close-up attitude [deg] | 28.303 | 28.303 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | other run's event | +196.807531 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | altitude [m] | 122150.32 | 122149.96 | 610.75 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | downrange [m] | 253644.30 | 253644.82 | 1268.22 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | rebuilt mass [kg] | 127022.069 | 127022.097 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | drawn attitude [deg] | 25.483 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | close-up attitude [deg] | 27.761 | 27.761 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +205.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | altitude [m] | 156675.44 | 156675.16 | 783.38 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | downrange [m] | 416383.21 | 416383.82 | 2081.92 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | rebuilt mass [kg] | 111212.072 | 111212.097 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | drawn attitude [deg] | 20.242 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | close-up attitude [deg] | 23.982 | 23.982 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +260.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | altitude [m] | 189685.38 | 189685.13 | 948.43 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | downrange [m] | 732820.34 | 732821.15 | 3664.10 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | rebuilt mass [kg] | 85341.169 | 85341.197 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | drawn attitude [deg] | 10.716 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | close-up attitude [deg] | 17.299 | 17.300 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +350.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | altitude [m] | 200531.92 | 200531.81 | 1002.66 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | downrange [m] | 1155050.84 | 1155052.11 | 5775.25 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | rebuilt mass [kg] | 58320.447 | 58320.418 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | drawn attitude [deg] | -0.610 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | close-up attitude [deg] | 9.766 | 9.766 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +444.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | altitude [m] | 200785.06 | 200784.99 | 1003.93 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | downrange [m] | 1239412.35 | 1239413.76 | 6197.06 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | rebuilt mass [kg] | 53721.176 | 53721.197 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | drawn attitude [deg] | -2.693 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | close-up attitude [deg] | 8.441 | 8.441 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +460.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | altitude [m] | 200732.85 | 200732.84 | 1003.66 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | downrange [m] | 1351222.24 | 1351223.86 | 6756.11 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | rebuilt mass [kg] | 47972.086 | 47972.097 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | drawn attitude [deg] | -5.366 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | close-up attitude [deg] | 6.772 | 6.772 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +480.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | altitude [m] | 200441.18 | 200441.21 | 1002.21 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | downrange [m] | 1470933.14 | 1470935.02 | 7354.67 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | rebuilt mass [kg] | 42222.996 | 42222.997 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | drawn attitude [deg] | -8.121 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | close-up attitude [deg] | 5.092 | 5.093 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +500.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | altitude [m] | 200189.56 | 200189.57 | 1000.95 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | downrange [m] | 1566560.72 | 1566562.77 | 7832.80 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | rebuilt mass [kg] | 37911.179 | 37911.197 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | drawn attitude [deg] | -10.247 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | close-up attitude [deg] | 3.826 | 3.826 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +515.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | altitude [m] | 200060.76 | 200060.77 | 1000.30 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | downrange [m] | 1633410.54 | 1633412.75 | 8167.05 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | rebuilt mass [kg] | 35036.634 | 35036.618 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | drawn attitude [deg] | -11.693 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | close-up attitude [deg] | 2.980 | 2.980 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +525.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | altitude [m] | 200000.89 | 200000.97 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | downrange [m] | 1702976.61 | 1702979.00 | 8514.88 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | rebuilt mass [kg] | 32162.089 | 32162.097 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | drawn attitude [deg] | -13.166 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | close-up attitude [deg] | 2.132 | 2.132 | 0.5 deg (close-up base and nose) | pass |
| Q2 | silo_hot_ramp_on_track | between | +535.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:cutoff; silo_hot_ramp_on_track:end | +536.300685 | last row 10791 | altitude [m] | 199999.98 | 200000.00 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:cutoff; silo_hot_ramp_on_track:end | +536.300685 | last row 10791 | downrange [m] | 1712236.81 | 1712236.80 | 8561.18 (larger of 0.5% and 10 m) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:cutoff; silo_hot_ramp_on_track:end | +536.300685 | last row 10791 | thrust on | false | false | exact (event rule) | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:cutoff; silo_hot_ramp_on_track:end | +536.300685 | last row 10791 | stage | stage2 | stage2 | exact | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:cutoff; silo_hot_ramp_on_track:end | +536.300685 | last row 10791 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:cutoff; silo_hot_ramp_on_track:end | +536.300685 | last row 10791 | rebuilt mass [kg] | 31788.201 | 31788.201 | 1.0 kg | pass |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:cutoff; silo_hot_ramp_on_track:end | +536.300685 | last row 10791 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | -13.358 held | n/a | pass (held angle, drawn not computed) |
| Q2 | silo_hot_ramp_on_track | silo_hot_ramp_on_track:cutoff; silo_hot_ramp_on_track:end | +536.300685 | last row 10791 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | altitude [m] | -100.00 | -100.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | tank start fill stage 1 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q3 | silo_failed | silo_failed:push_start | -2.607318 | first row 0 | tank start fill stage 2 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | altitude [m] | -94.57 | -94.56 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q3 | silo_failed | other run's event | -2.000000 | between rows | painted base [px off transform] | 0 | 0.013 | 1.0 px | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | altitude [m] | -75.14 | -75.10 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q3 | silo_failed | silo_failed:mid_push | -1.307318 | row 26 | painted base [px off transform] | 0 | 0.057 | 1.0 px | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | altitude [m] | -74.85 | -74.81 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q3 | silo_failed | between | -1.300000 | between rows | painted base [px off transform] | 0 | 0.057 | 1.0 px | pass |
| Q3 | silo_failed | silo_failed:release; silo_failed:ignition_failed | +0.000000 | row 54 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | silo_failed:release; silo_failed:ignition_failed | +0.000000 | row 54 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | silo_failed:release; silo_failed:ignition_failed | +0.000000 | row 54 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | silo_failed:release; silo_failed:ignition_failed | +0.000000 | row 54 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | silo_failed:release; silo_failed:ignition_failed | +0.000000 | row 54 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | silo_failed:release; silo_failed:ignition_failed | +0.000000 | row 54 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | silo_failed:release; silo_failed:ignition_failed | +0.000000 | row 54 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | silo_failed:release; silo_failed:ignition_failed | +0.000000 | row 54 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q3 | silo_failed | between | +0.900000 | between rows | altitude [m] | 65.07 | 65.09 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +0.900000 | between rows | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +0.900000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +0.900000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +0.900000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +0.900000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +0.900000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +0.900000 | between rows | painted base [px off transform] | 0 | 0.027 | 1.0 px | pass |
| Q3 | silo_failed | between | +1.600000 | between rows | altitude [m] | 110.19 | 110.15 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +1.600000 | between rows | downrange [m] | -0.01 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +1.600000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +1.600000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +1.600000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +1.600000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +1.600000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +1.600000 | between rows | painted base [px off transform] | 0 | 0.045 | 1.0 px | pass |
| Q3 | silo_failed | between | +2.000000 | between rows | altitude [m] | 133.82 | 133.82 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +2.000000 | between rows | downrange [m] | -0.02 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +2.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +2.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +2.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +2.000000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +2.000000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +2.000000 | between rows | painted base [px off transform] | 0 | 0.017 | 1.0 px | pass |
| Q3 | silo_failed | between | +4.200000 | between rows | altitude [m] | 235.81 | 235.86 | 1.18 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +4.200000 | between rows | downrange [m] | -0.07 | -0.10 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +4.200000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +4.200000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +4.200000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +4.200000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +4.200000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +4.200000 | between rows | painted base [px off transform] | 0 | 0.037 | 1.0 px | pass |
| Q3 | silo_failed | between | +5.000000 | between rows | altitude [m] | 261.16 | 261.20 | 1.31 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +5.000000 | between rows | downrange [m] | -0.10 | -0.10 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +5.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +5.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +5.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +5.000000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +5.000000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +5.000000 | between rows | painted base [px off transform] | 0 | 0.022 | 1.0 px | pass |
| Q3 | silo_failed | silo_failed:apex | +7.842648 | row 212 | altitude [m] | 300.65 | 300.60 | 1.50 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | silo_failed:apex | +7.842648 | row 212 | downrange [m] | -0.20 | -0.20 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | silo_failed:apex | +7.842648 | row 212 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | silo_failed:apex | +7.842648 | row 212 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | silo_failed:apex | +7.842648 | row 212 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | silo_failed:apex | +7.842648 | row 212 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | silo_failed:apex | +7.842648 | row 212 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | silo_failed:apex | +7.842648 | row 212 | painted base [px off transform] | 0 | 0.029 | 1.0 px | pass |
| Q3 | silo_failed | between | +8.000000 | between rows | altitude [m] | 300.52 | 300.49 | 1.50 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +8.000000 | between rows | downrange [m] | -0.21 | -0.20 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +8.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +8.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +8.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +8.000000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +8.000000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +8.000000 | between rows | painted base [px off transform] | 0 | 0.025 | 1.0 px | pass |
| Q3 | silo_failed | between | +9.700000 | between rows | altitude [m] | 283.79 | 283.77 | 1.42 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +9.700000 | between rows | downrange [m] | -0.27 | -0.30 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +9.700000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +9.700000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +9.700000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +9.700000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +9.700000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +9.700000 | between rows | painted base [px off transform] | 0 | 0.023 | 1.0 px | pass |
| Q3 | silo_failed | other run's event | +12.493729 | between rows | altitude [m] | 194.98 | 194.95 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | other run's event | +12.493729 | between rows | downrange [m] | -0.36 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | other run's event | +12.493729 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | other run's event | +12.493729 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | other run's event | +12.493729 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | other run's event | +12.493729 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | other run's event | +12.493729 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | other run's event | +12.493729 | between rows | painted base [px off transform] | 0 | 0.029 | 1.0 px | pass |
| Q3 | silo_failed | between | +12.500000 | between rows | altitude [m] | 194.69 | 194.66 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +12.500000 | between rows | downrange [m] | -0.36 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +12.500000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +12.500000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +12.500000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +12.500000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +12.500000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +12.500000 | between rows | painted base [px off transform] | 0 | 0.030 | 1.0 px | pass |
| Q3 | silo_failed | between | +14.900000 | between rows | altitude [m] | 57.40 | 57.40 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +14.900000 | between rows | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +14.900000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +14.900000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +14.900000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +14.900000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +14.900000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +14.900000 | between rows | painted base [px off transform] | 0 | 0.006 | 1.0 px | pass |
| Q3 | silo_failed | between | +15.500000 | between rows | altitude [m] | 14.31 | 14.34 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +15.500000 | between rows | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +15.500000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +15.500000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +15.500000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q3 | silo_failed | between | +15.500000 | between rows | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +15.500000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +15.500000 | between rows | painted base [px off transform] | 0 | 0.020 | 1.0 px | pass |
| Q3 | silo_failed | silo_failed:impact; silo_failed:end | +15.689059 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | silo_failed:impact; silo_failed:end | +15.689059 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | silo_failed:impact; silo_failed:end | +15.689059 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | silo_failed:impact; silo_failed:end | +15.689059 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | silo_failed:impact; silo_failed:end | +15.689059 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | silo_failed:impact; silo_failed:end | +15.689059 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | silo_failed:impact; silo_failed:end | +15.689059 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | silo_failed:impact; silo_failed:end | +15.689059 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +15.750000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +15.750000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +15.750000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +15.750000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +15.750000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +15.750000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +15.750000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +15.750000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | other run's event | +17.774014 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | other run's event | +17.774014 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | other run's event | +17.774014 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | other run's event | +17.774014 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | other run's event | +17.774014 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | other run's event | +17.774014 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | other run's event | +17.774014 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | other run's event | +17.774014 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +21.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +21.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +21.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +21.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +21.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +21.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +21.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +21.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +37.500000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +37.500000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +37.500000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +37.500000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +37.500000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +37.500000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +37.500000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +37.500000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +52.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +52.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +52.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +52.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +52.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +52.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +52.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +52.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +75.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +75.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +75.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +75.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +75.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +75.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +75.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +75.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +101.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +101.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +101.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +101.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +101.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +101.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +101.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +101.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +133.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +133.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +133.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +133.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +133.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +133.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +133.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +133.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +144.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +144.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +144.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +144.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +144.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +144.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +144.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +144.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +147.500000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +147.500000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +147.500000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +147.500000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +147.500000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +147.500000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +147.500000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +147.500000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | other run's event | +151.328438 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | other run's event | +151.328438 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | other run's event | +151.328438 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | other run's event | +151.328438 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | other run's event | +151.328438 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | other run's event | +151.328438 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | other run's event | +151.328438 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | other run's event | +151.328438 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +155.500000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +155.500000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +155.500000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +155.500000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +155.500000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +155.500000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +155.500000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +155.500000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +159.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +159.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +159.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +159.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +159.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +159.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +159.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +159.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | other run's event | +162.328438 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | other run's event | +162.328438 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | other run's event | +162.328438 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | other run's event | +162.328438 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | other run's event | +162.328438 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | other run's event | +162.328438 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | other run's event | +162.328438 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | other run's event | +162.328438 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +166.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +166.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +166.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +166.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +166.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +166.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +166.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +166.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +175.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +175.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +175.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +175.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +175.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +175.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +175.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +175.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +188.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +188.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +188.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +188.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +188.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +188.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +188.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +188.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +192.500000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +192.500000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +192.500000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +192.500000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +192.500000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +192.500000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +192.500000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +192.500000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | other run's event | +196.807531 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | other run's event | +196.807531 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | other run's event | +196.807531 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | other run's event | +196.807531 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | other run's event | +196.807531 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | other run's event | +196.807531 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | other run's event | +196.807531 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | other run's event | +196.807531 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +205.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +205.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +205.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +205.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +205.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +205.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +205.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +205.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +260.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +260.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +260.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +260.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +260.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +260.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +260.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +260.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +350.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +350.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +350.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +350.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +350.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +350.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +350.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +350.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +444.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +444.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +444.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +444.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +444.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +444.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +444.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +444.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +460.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +460.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +460.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +460.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +460.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +460.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +460.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +460.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +480.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +480.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +480.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +480.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +480.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +480.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +480.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +480.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +500.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +500.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +500.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +500.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +500.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +500.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +500.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +500.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +515.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +515.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +515.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +515.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +515.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +515.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +515.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +515.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +525.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +525.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +525.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +525.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +525.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +525.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +525.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +525.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | between | +535.000000 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | between | +535.000000 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | between | +535.000000 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | between | +535.000000 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | between | +535.000000 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | between | +535.000000 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | between | +535.000000 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | between | +535.000000 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q3 | silo_failed | other run's event | +536.300685 | last row 370 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q3 | silo_failed | other run's event | +536.300685 | last row 370 | downrange [m] | -0.40 | -0.40 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q3 | silo_failed | other run's event | +536.300685 | last row 370 | thrust on | false | false | exact (event rule) | pass |
| Q3 | silo_failed | other run's event | +536.300685 | last row 370 | stage | stage1 | stage1 | exact | pass |
| Q3 | silo_failed | other run's event | +536.300685 | last row 370 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q3 | silo_failed | other run's event | +536.300685 | last row 370 | rebuilt mass [kg] | 569100.000 | 569100.000 | 1.0 kg | pass |
| Q3 | silo_failed | other run's event | +536.300685 | last row 370 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q3 | silo_failed | other run's event | +536.300685 | last row 370 | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | altitude [m] | -100.00 | -100.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | rebuilt mass [kg] | 531091.488 | 531091.496 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | tank start fill stage 1 | 0.899579 (offload 41.2629 t) | 0.899579 | 0.0001 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:push_start | -2.607318 | first row 0 | tank start fill stage 2 | 1.000000 (offload 0.0000 t) | 1.000000 | 0.0001 | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | altitude [m] | -94.57 | -94.56 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | rebuilt mass [kg] | 531091.488 | 531091.496 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | other run's event | -2.000000 | between rows | painted base [px off transform] | 0 | 0.013 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | altitude [m] | -75.14 | -75.10 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | rebuilt mass [kg] | 531091.488 | 531091.496 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:mid_push | -1.307318 | row 26 | painted base [px off transform] | 0 | 0.059 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | altitude [m] | -74.85 | -74.81 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | rebuilt mass [kg] | 531091.488 | 531091.496 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | drawn attitude [deg] | 90.000 | 90.000 | 0.5 deg (painted base and nose, to scale) | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | close-up attitude [deg] | 90.000 | 90.000 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | -1.300000 | between rows | painted base [px off transform] | 0 | 0.059 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:release | +0.000000 | row 54 | altitude [m] | 0.00 | 0.00 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:release | +0.000000 | row 54 | downrange [m] | 0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:release | +0.000000 | row 54 | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:release | +0.000000 | row 54 | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:release | +0.000000 | row 54 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:release | +0.000000 | row 54 | rebuilt mass [kg] | 531091.488 | 531091.496 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:release | +0.000000 | row 54 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 90.000 held | n/a | pass (held angle, drawn not computed) |
| Q4 | silo_cold_s1 | silo_cold_s1:release | +0.000000 | row 54 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | altitude [m] | 37.13 | 37.10 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | rebuilt mass [kg] | 531091.488 | 531091.496 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | drawn attitude [deg] | 85.872 | 85.872 | 0.5 deg (painted base and nose, to scale) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | close-up attitude [deg] | 85.872 | 85.872 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s1; silo_cold_s1:kick_start | +0.500000 | row 66 | painted base [px off transform] | 0 | 0.036 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | altitude [m] | 65.09 | 65.10 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | downrange [m] | -0.00 | 0.00 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | plume fraction | 0.2000 | 0.1997 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | rebuilt mass [kg] | 530983.379 | 530983.369 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | drawn attitude [deg] | 85.872 | 85.872 | 0.5 deg (painted base and nose, to scale) | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | close-up attitude [deg] | 85.872 | 85.872 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +0.900000 | between rows | painted base [px off transform] | 0 | 0.013 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | altitude [m] | 111.30 | 111.27 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | downrange [m] | 0.07 | 0.10 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | plume fraction | 0.5500 | 0.5497 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | rebuilt mass [kg] | 530275.296 | 530275.275 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | drawn attitude [deg] | 85.872 | 85.872 | 0.5 deg (painted base and nose, to scale) | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | close-up attitude [deg] | 85.872 | 85.872 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +1.600000 | between rows | painted base [px off transform] | 0 | 0.042 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | altitude [m] | 169.33 | 169.30 | 1.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | downrange [m] | 0.56 | 0.60 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | rebuilt mass [kg] | 528394.027 | 528393.996 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | drawn attitude [deg] | 85.872 | 85.872 | 0.5 deg (painted base and nose, to scale) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | close-up attitude [deg] | 85.872 | 85.872 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ramp_end | +2.500000 | row 108 | painted base [px off transform] | 0 | 0.041 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | altitude [m] | 287.36 | 287.34 | 1.44 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | downrange [m] | 3.64 | 3.62 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | rebuilt mass [kg] | 523808.344 | 523808.352 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | drawn attitude [deg] | 85.872 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | close-up attitude [deg] | 85.872 | 85.872 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +4.200000 | between rows | painted base [px off transform] | 0 | 0.021 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | altitude [m] | 596.46 | 596.50 | 2.98 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | downrange [m] | 21.07 | 21.10 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | rebuilt mass [kg] | 513697.347 | 513697.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | drawn attitude [deg] | 85.872 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | close-up attitude [deg] | 85.872 | 85.872 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:kick_end | +7.948339 | row 219 | painted base [px off transform] | 0 | 0.019 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | altitude [m] | 764.92 | 764.94 | 3.82 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | downrange [m] | 34.39 | 34.37 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | rebuilt mass [kg] | 508972.309 | 508972.352 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | drawn attitude [deg] | 85.085 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | close-up attitude [deg] | 85.086 | 85.086 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +9.700000 | between rows | painted base [px off transform] | 0 | 0.011 | 1.0 px | pass |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | altitude [m] | 1066.64 | 1066.62 | 5.33 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | downrange [m] | 64.02 | 64.01 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | rebuilt mass [kg] | 501436.334 | 501436.371 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | drawn attitude [deg] | 83.703 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | close-up attitude [deg] | 83.704 | 83.704 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | other run's event | +12.493729 | between rows | painted base [px off transform] | 0 | 0.005 | 1.0 px | pass |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | altitude [m] | 1753.31 | 1753.29 | 8.77 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | downrange [m] | 158.19 | 158.17 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | rebuilt mass [kg] | 487192.972 | 487192.962 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | drawn attitude [deg] | 80.715 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | close-up attitude [deg] | 80.716 | 80.717 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | other run's event | +17.774014 | between rows | painted base [px off transform] | 0 | 0.003 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | altitude [m] | 2251.60 | 2251.60 | 11.26 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | downrange [m] | 248.78 | 248.74 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | rebuilt mass [kg] | 478491.001 | 478490.959 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | drawn attitude [deg] | 78.687 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | close-up attitude [deg] | 78.690 | 78.689 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +21.000000 | between rows | painted base [px off transform] | 0 | 0.005 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | altitude [m] | 5821.40 | 5821.38 | 29.11 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | downrange [m] | 1378.77 | 1378.74 | 10.00 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | rebuilt mass [kg] | 433982.897 | 433982.859 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | drawn attitude [deg] | 67.007 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | close-up attitude [deg] | 67.019 | 67.019 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +37.500000 | between rows | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | altitude [m] | 10458.23 | 10458.23 | 52.29 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | downrange [m] | 3901.69 | 3901.71 | 19.51 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | rebuilt mass [kg] | 394869.714 | 394869.756 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | drawn attitude [deg] | 56.599 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | close-up attitude [deg] | 56.635 | 56.635 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +52.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | altitude [m] | 20781.31 | 20781.30 | 103.91 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | downrange [m] | 12939.50 | 12939.53 | 64.70 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | rebuilt mass [kg] | 332828.114 | 332828.156 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | drawn attitude [deg] | 42.676 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | close-up attitude [deg] | 42.793 | 42.792 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +75.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | altitude [m] | 36900.32 | 36900.34 | 184.50 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | downrange [m] | 34628.82 | 34628.90 | 173.14 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | rebuilt mass [kg] | 262694.131 | 262694.156 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | drawn attitude [deg] | 31.639 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | close-up attitude [deg] | 31.950 | 31.950 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +101.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | altitude [m] | 63713.06 | 63713.11 | 318.57 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | downrange [m] | 86490.05 | 86490.16 | 432.45 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | stage | stage1 | stage1 | exact | pass |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | rebuilt mass [kg] | 176375.384 | 176375.356 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | drawn attitude [deg] | 23.151 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | close-up attitude [deg] | 23.928 | 23.928 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +133.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | altitude [m] | 69300.13 | 69300.10 | 346.50 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | downrange [m] | 99243.24 | 99243.20 | 496.22 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 22.102 held | n/a | pass (held angle, drawn not computed) |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | stage-1 tank at the stage-1 propellant event [kg] | < 1 | 0.000 | under 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:MECO; silo_cold_s1:staging | +138.531493 | row 2832 | stage-2 tank at MECO [kg] | 107500.0 | 107500.0 | equals the stage-2 load before stage-2 ignition, 1 kg | pass |
| Q4 | silo_cold_s1 | between | +144.000000 | between rows | altitude [m] | 74868.04 | 74867.68 | 374.34 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +144.000000 | between rows | downrange [m] | 112504.26 | 112504.25 | 562.52 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +144.000000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +144.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +144.000000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +144.000000 | between rows | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +144.000000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 22.102 held | n/a | pass (held angle, drawn not computed) |
| Q4 | silo_cold_s1 | between | +144.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +147.500000 | between rows | altitude [m] | 78301.34 | 78300.36 | 391.51 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +147.500000 | between rows | downrange [m] | 120977.86 | 120977.77 | 604.89 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +147.500000 | between rows | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +147.500000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +147.500000 | between rows | plume fraction | 0.0000 | 0.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +147.500000 | between rows | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +147.500000 | between rows | drawn attitude [deg] | none (unpowered: the model defines no attitude) | 22.102 held | n/a | pass (held angle, drawn not computed) |
| Q4 | silo_cold_s1 | between | +147.500000 | between rows | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | altitude [m] | 80247.52 | 80247.50 | 401.24 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | downrange [m] | 125891.38 | 125891.40 | 629.46 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | rebuilt mass [kg] | 139254.396 | 139254.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | drawn attitude [deg] | 30.300 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | close-up attitude [deg] | 31.430 | 31.431 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:ignition_s2 | +149.531493 | row 3054 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | altitude [m] | 81946.43 | 81945.86 | 409.73 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | downrange [m] | 130244.33 | 130244.97 | 651.22 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | rebuilt mass [kg] | 138737.856 | 138737.866 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | drawn attitude [deg] | 30.143 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | close-up attitude [deg] | 31.313 | 31.313 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | other run's event | +151.328438 | between rows | painted base [px off transform] | 0 | 0.002 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | altitude [m] | 85833.21 | 85832.73 | 429.17 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | downrange [m] | 140413.73 | 140414.26 | 702.07 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | rebuilt mass [kg] | 137538.722 | 137538.713 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | drawn attitude [deg] | 29.778 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | close-up attitude [deg] | 31.039 | 31.039 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +155.500000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | altitude [m] | 89032.97 | 89032.60 | 445.16 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | downrange [m] | 149015.95 | 149016.36 | 745.08 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | rebuilt mass [kg] | 136532.632 | 136532.613 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | drawn attitude [deg] | 29.470 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | close-up attitude [deg] | 30.808 | 30.808 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +159.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | altitude [m] | 92024.34 | 92023.77 | 460.12 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | downrange [m] | 157256.51 | 157257.19 | 786.28 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | rebuilt mass [kg] | 135575.857 | 135575.866 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | drawn attitude [deg] | 29.175 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | close-up attitude [deg] | 30.588 | 30.588 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | other run's event | +162.328438 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | altitude [m] | 95266.16 | 95265.77 | 476.33 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | downrange [m] | 166415.25 | 166415.74 | 832.08 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | rebuilt mass [kg] | 134520.450 | 134520.413 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | drawn attitude [deg] | 28.848 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | close-up attitude [deg] | 30.343 | 30.343 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +166.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | altitude [m] | 102958.27 | 102957.90 | 514.79 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | downrange [m] | 189176.52 | 189177.00 | 945.88 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | rebuilt mass [kg] | 131933.360 | 131933.392 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | drawn attitude [deg] | 28.039 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | close-up attitude [deg] | 29.739 | 29.739 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +175.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | altitude [m] | 110492.87 | 110492.90 | 552.46 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | downrange [m] | 213043.37 | 213043.40 | 1065.22 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | rebuilt mass [kg] | 127574.267 | 127574.296 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | drawn attitude [deg] | 27.196 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | close-up attitude [deg] | 29.109 | 29.110 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:fairing | +184.250483 | row 3751 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | altitude [m] | 113441.44 | 113440.97 | 567.21 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | downrange [m] | 222857.90 | 222858.55 | 1114.29 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | rebuilt mass [kg] | 126496.452 | 126496.442 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | drawn attitude [deg] | 26.850 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | close-up attitude [deg] | 28.852 | 28.852 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +188.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | altitude [m] | 116901.44 | 116901.13 | 584.51 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | downrange [m] | 234747.32 | 234747.78 | 1173.74 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | rebuilt mass [kg] | 125202.906 | 125202.892 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | drawn attitude [deg] | 26.433 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | close-up attitude [deg] | 28.542 | 28.542 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +192.500000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | altitude [m] | 120133.66 | 120133.45 | 600.67 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | downrange [m] | 246242.82 | 246243.09 | 1231.21 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | rebuilt mass [kg] | 123964.687 | 123964.688 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | drawn attitude [deg] | 26.031 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | close-up attitude [deg] | 28.243 | 28.243 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | other run's event | +196.807531 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | altitude [m] | 126068.11 | 126067.68 | 630.34 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | downrange [m] | 268421.78 | 268422.44 | 1342.11 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | rebuilt mass [kg] | 121609.725 | 121609.742 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | drawn attitude [deg] | 25.259 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | close-up attitude [deg] | 27.670 | 27.670 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +205.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | altitude [m] | 159025.57 | 159025.16 | 795.13 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | downrange [m] | 428969.14 | 428969.97 | 2144.85 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | rebuilt mass [kg] | 105799.729 | 105799.742 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | drawn attitude [deg] | 19.814 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | close-up attitude [deg] | 23.667 | 23.667 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +260.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | altitude [m] | 190204.00 | 190203.71 | 951.02 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | downrange [m] | 745030.01 | 745031.16 | 3725.15 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | rebuilt mass [kg] | 79928.825 | 79928.842 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | drawn attitude [deg] | 9.873 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | close-up attitude [deg] | 16.566 | 16.566 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +350.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | altitude [m] | 200174.93 | 200174.78 | 1000.87 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | downrange [m] | 1174075.50 | 1174077.42 | 5870.38 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | rebuilt mass [kg] | 52908.104 | 52908.073 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | drawn attitude [deg] | -1.994 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | close-up attitude [deg] | 8.552 | 8.552 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +444.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | altitude [m] | 200398.57 | 200398.45 | 1001.99 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | downrange [m] | 1260812.38 | 1260814.44 | 6304.06 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | rebuilt mass [kg] | 48308.832 | 48308.842 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | drawn attitude [deg] | -4.181 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | close-up attitude [deg] | 7.145 | 7.145 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +460.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | altitude [m] | 200366.14 | 200366.06 | 1001.83 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | downrange [m] | 1376334.86 | 1376337.25 | 6881.67 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | rebuilt mass [kg] | 42559.742 | 42559.742 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | drawn attitude [deg] | -6.990 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | close-up attitude [deg] | 5.373 | 5.373 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +480.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | altitude [m] | 200162.98 | 200163.02 | 1000.81 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | downrange [m] | 1500789.71 | 1500792.43 | 7503.95 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | rebuilt mass [kg] | 36810.652 | 36810.642 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | drawn attitude [deg] | -9.890 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | close-up attitude [deg] | 3.591 | 3.592 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +500.000000 | between rows | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | altitude [m] | 200027.20 | 200027.29 | 1000.14 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | downrange [m] | 1600838.06 | 1600841.16 | 8004.19 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | thrust on | true | true | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | plume fraction | 1.0000 | 1.0000 | 0.02 | pass |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | rebuilt mass [kg] | 32498.835 | 32498.842 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | drawn attitude [deg] | -12.130 | marker mode (heading tick) | n/a: body under the pixel threshold | pass (marker mode) |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | close-up attitude [deg] | 2.250 | 2.250 | 0.5 deg (close-up base and nose) | pass |
| Q4 | silo_cold_s1 | between | +515.000000 | between rows | painted base [px off transform] | 0 | 0.001 | 1.0 px | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:cutoff; silo_cold_s1:end | +523.503743 | last row 10537 | altitude [m] | 200000.00 | 200000.00 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:cutoff; silo_cold_s1:end | +523.503743 | last row 10537 | downrange [m] | 1660430.87 | 1660430.90 | 8302.15 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:cutoff; silo_cold_s1:end | +523.503743 | last row 10537 | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:cutoff; silo_cold_s1:end | +523.503743 | last row 10537 | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:cutoff; silo_cold_s1:end | +523.503743 | last row 10537 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q4 | silo_cold_s1 | silo_cold_s1:cutoff; silo_cold_s1:end | +523.503743 | last row 10537 | rebuilt mass [kg] | 30054.396 | 30054.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | silo_cold_s1:cutoff; silo_cold_s1:end | +523.503743 | last row 10537 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | -13.425 held | n/a | pass (held angle, drawn not computed) |
| Q4 | silo_cold_s1 | silo_cold_s1:cutoff; silo_cold_s1:end | +523.503743 | last row 10537 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +525.000000 | last row 10537 | altitude [m] | 200000.00 | 200000.00 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +525.000000 | last row 10537 | downrange [m] | 1660430.87 | 1660430.90 | 8302.15 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +525.000000 | last row 10537 | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +525.000000 | last row 10537 | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +525.000000 | last row 10537 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q4 | silo_cold_s1 | between | +525.000000 | last row 10537 | rebuilt mass [kg] | 30054.396 | 30054.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +525.000000 | last row 10537 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | -13.425 held | n/a | pass (held angle, drawn not computed) |
| Q4 | silo_cold_s1 | between | +525.000000 | last row 10537 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | between | +535.000000 | last row 10537 | altitude [m] | 200000.00 | 200000.00 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | between | +535.000000 | last row 10537 | downrange [m] | 1660430.87 | 1660430.90 | 8302.15 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | between | +535.000000 | last row 10537 | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | between | +535.000000 | last row 10537 | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | between | +535.000000 | last row 10537 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q4 | silo_cold_s1 | between | +535.000000 | last row 10537 | rebuilt mass [kg] | 30054.396 | 30054.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | between | +535.000000 | last row 10537 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | -13.425 held | n/a | pass (held angle, drawn not computed) |
| Q4 | silo_cold_s1 | between | +535.000000 | last row 10537 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |
| Q4 | silo_cold_s1 | other run's event | +536.300685 | last row 10537 | altitude [m] | 200000.00 | 200000.00 | 1000.00 (larger of 0.5% and 1 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +536.300685 | last row 10537 | downrange [m] | 1660430.87 | 1660430.90 | 8302.15 (larger of 0.5% and 10 m) | pass |
| Q4 | silo_cold_s1 | other run's event | +536.300685 | last row 10537 | thrust on | false | false | exact (event rule) | pass |
| Q4 | silo_cold_s1 | other run's event | +536.300685 | last row 10537 | stage | stage2 | stage2 | exact | pass |
| Q4 | silo_cold_s1 | other run's event | +536.300685 | last row 10537 | plume fraction | 0.0000 | 0.0000 | not checked on a run's last row | pass (last row) |
| Q4 | silo_cold_s1 | other run's event | +536.300685 | last row 10537 | rebuilt mass [kg] | 30054.396 | 30054.396 | 1.0 kg | pass |
| Q4 | silo_cold_s1 | other run's event | +536.300685 | last row 10537 | drawn attitude [deg] | none (unpowered: the model defines no attitude) | -13.425 held | n/a | pass (held angle, drawn not computed) |
| Q4 | silo_cold_s1 | other run's event | +536.300685 | last row 10537 | painted base [px off transform] | 0 | 0.000 | 1.0 px | pass |

Summary: 1994 rows, 1994 pass, 0 fail, over 227 panel states of the five runs;
attitude rows not applicable: 123 in marker mode (body under the pixel threshold), 69 unpowered (held angle).
Companion panels: 135 states, 1218 checks, 0 failing.
Worst: altitude 0.0455 of its tolerance, downrange 0.0664 of its tolerance, drawn attitude 0.0005 deg,
close-up attitude 0.0009 deg, plume 0.00034, mass 0.0486 kg, painted base 0.0652 px,
tank start fill 1.97e-07.

## Deviations

None: every row passes.

## Watchability (exit criterion 16 and the review's close-up checks)

Added at review round 1 of step A7 and re-run at review round 2, after the last fix of
src/launchsim/templates/scene.html (the app restarted on it). The same route and QA hash as above, over a dense
time scan: every 2 s over each pair's span, plus 0.25 s steps through the push and the kick, the staging zoom,
the separation and the pan, the fairing drop and the halves' leaving, and 0.5 s steps after the separated
bodies' impacts and through the cutoffs. Pairs (scene route, baseline on the left): S1 pad beside silo_cold and
S3 pad beside silo_failed (results/silo_screening_2d/20260930T175743Z), S4 pad beside silo_cold_s1
(results/silo_offload_2d/20261003T112934Z).

Viewport: the round-2 scan dumps the DOM over the DevTools protocol (scratchpad dump.mjs) with the viewport
set as the screenshots are taken, `Emulation.setDeviceMetricsOverride` 1280 x 900 at scale 1, the scene
route's layout: the column layout in every state, each panel's view 605 px wide (x 0 and
617) and 514 px tall for S1, 474 px for S4 (its note band takes two lines) and 464 px for S3 (its caution
plate), the close-up inset 236 x 286 px at each view's top left. The app page's frame that the screenshots
show lays the views out 596 px wide at x 0 and 608 and 414 px tall (S1) or 374 px (S4), which drops the
carriage label at every time after release, since the 3.0 m carriage draws under its 4 px minimum at every
scale after release in a view that short (see README: the record of the round-2 fix). Round 1 had dumped with `--window-size=1280,900`
and `--dump-dom`, whose effective viewport laid the views out 584.5 x 421 px, smaller than the screenshots'; at
that size the carriage label was not drawn in the states where, at the screenshots' size, it ran under the
close-up inset for about the first second after release (the review's finding; W6 could not see it). At
1280 x 900 the pre-fix template gave 3 overlapping pairs in S1 (the carriage label against the close-up at
0.9, 1.39 and 1.4 s); after the fix (the label keeps clear of the inset) the column reads 0.
Checks, per panel state, from the state hook:

- W1: the close-up vehicle at least 120 px long (criterion 16; `closeup_len_px`).
- W2: the close-up's painted base and nose inside its drawing (`closeup_base_px`, `closeup_nose_px` against
  `closeup_drawing`); during the zoom before staging (`closeup_framing` "zooming in for staging") the nose and
  stage 2's base (`closeup_stage2_base_px`), since the zoom frames the upper stage and the stage-1 engines leave
  at the bottom. The review found the whole of stage 2 outside the drawing for about 2.5 s after every MECO.
- W3: the close-up title's word for the fairing halves against the drawing: "leaving" only while a half's
  outline is in the drawing (`closeup_halves_drawn`), "gone" only when none is. The review found "leaving" over
  an empty drawing for about 3.6 s after each drop.
- W4: a separated body that has stopped keeps a label.
- W5: the other panel's marker named once: no label plate while the ring key lies within reach (`key_near`),
  and the key never absent. On this route the two-panel page lays the key out in its band under the gauges,
  outside the view, so no plate was suppressed here; the suppression shows in the app page's screenshots and
  the video frames (the overlay layout), where the key sits in the view.
- W6: every label plate inside the view and no two plates overlapping.
- W7: the close-up's caption plate inside the drawing.
- W8: the readout's corner (for the record: on this route the readout has its own row, so no corner).

Columns give the number of failing states and, where measured, the worst value (W1: the least length; W2: the
least margin inside the drawing, in px, and the number of states in the staging zoom).

| pair | run | states | W1 close-up length: fails, least [px] | W2 base and nose in the drawing: fails, least margin [px] (zoom states) | W3 halves' word vs drawn: fails (words seen) | W4 stopped body unlabelled | W5 other marker named twice: fails (plates suppressed) | W6 plates out of view or overlapping | W7 caption plate outside the drawing | W8 readout corner |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | pad | 800 | 0, 121.0 | 0, 10 (13) | 0 (leaving 51, opening 7) | 0 | 0 (0) | 0 | 0 | readout in its own row (column layout: no corner) |
| S1 | silo_cold | 800 | 0, 121.0 | 0, 10 (14) | 0 (leaving 51, opening 6) | 0 | 0 (0) | 0 | 0 | readout in its own row (column layout: no corner) |
| S3 | pad | 104 | 0, 160.0 | 0, 10 (0) | 0 (no fairing drop) | 0 | 0 (0) | 0 | 0 | readout in its own row (column layout: no corner) |
| S3 | silo_failed | 104 | 0, 160 | 0, 10 (0) | 0 (no fairing drop) | 0 | 0 (0) | 0 | 0 | readout in its own row (column layout: no corner) |
| S4 | pad | 794 | 0, 121.0 | 0, 10 (13) | 0 (leaving 51, opening 7) | 0 | 0 (0) | 0 | 0 | readout in its own row (column layout: no corner) |
| S4 | silo_cold_s1 | 794 | 0, 121.0 | 0, 10 (13) | 0 (gone 1, leaving 49, opening 7) | 0 | 0 (0) | 0 | 0 | readout in its own row (column layout: no corner) |

Summary: 3396 panel states, 0 failing checks.
