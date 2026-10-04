# Findings index

One note per research question and model, plus the calibration record. Every research note (RQ*) is **preliminary**, covers only concept A (a vertical silo whose drive imposes a prescribed acceleration, `constant_accel`) and has a "Caveats (read first)" section near the top. The calibration note (CAL) is the record of the vehicle they all use; it flies the pad only. The research questions are listed in the top-level [README](../../README.md#research-questions), and its [Results so far](../../README.md#results-so-far) section summarises these notes.

## Notes

| Note | Question | Status | Model |
|---|---|---|---|
| [CAL-f9-leo-2d.md](CAL-f9-leo-2d.md) | Does the generic Falcon 9-class vehicle reach 22.8 t to low Earth orbit within ±10%? | Calibration record (labelled calibration, not validation). Closed as a documented miss, accepted by the user on 2026-09-30 | planar 2-D, pad only |
| [RQ1-fuel-offload-2d.md](RQ1-fuel-offload-2d.md) | RQ1 (fuel-replacement form): how much stage-1 propellant the silo push replaces at the pad's payload, and how much assumed structure cancels it | Preliminary; pre-registered (SP1) | planar 2-D to a 200 km orbit |
| [RQ3-silo-screening-2d.md](RQ3-silo-screening-2d.md) | RQ3: what a vertical silo push is worth in payload, and what it costs in loads, energy and power | Preliminary; the main payload result | planar 2-D to a 200 km orbit |
| [RQ2-ignition-timing-2d.md](RQ2-ignition-timing-2d.md) | RQ2: hot or cold start; how delay, ramp and lag cost payload | Preliminary | planar 2-D to a 200 km orbit |
| [RQ6-aero-2d-preliminary.md](RQ6-aero-2d-preliminary.md) | RQ6: unthrottled max-Q, q-alpha and drag deltas of the silo | Preliminary, deliberately narrow | planar 2-D, unthrottled |
| [RQ3-silo-screening-1d.md](RQ3-silo-screening-1d.md) | RQ3 in 1-D: exit speed, loads, energy, power, failed ignition | Preliminary; superseded for payload questions by RQ3-2d, kept as the 1-D record | 1-D vertical, stage-1 burnout speed |
| [RQ2-ignition-timing-1d.md](RQ2-ignition-timing-1d.md) | RQ2 in 1-D: exact ignition-loss forms and the hot-start trade | Preliminary; superseded for payload questions by RQ2-2d, kept as the 1-D record | 1-D vertical, stage-1 burnout speed |

Headline and main caveat of each note:

- **CAL-f9-leo-2d.** The gate vehicle (mass set C) reaches 26,054.4 kg to 200 km circular at 28.5° (+14.27%). That is 974.4 kg above the band's upper edge, a miss high. Set A (the README masses) reaches 24,700.0 kg (+8.33%), inside the band. Set B reaches 25,416.3 kg (+11.48%), outside. *Caveat:* the cause of the miss is not established, since the unmodelled effects point both ways, and every 2-D finding inherits the miss.
- **RQ1-fuel-offload-2d.** At the pad's payload the cold-start silo (3 g net, 100 m, 76.7 m/s) lets the gate vehicle leave out 41.26 t of stage-1 propellant, 10.04% of the stage-1 load (7.96% of the total), 2.76× the ideal-screening offload; the loss breakdown explains the beat. ±10% arms: 38.67–44.46 t; README masses: 36.01 t (9.10%). *Caveat:* no structural mass is charged for the 4 g push: an assumed +2/+4/+8.1 t of stage-1 dry mass leaves 32.29/22.88/1.98 t, and about 8.5 t (extrapolated) cancels it; the pad flown with the same offload falls 1,402 kg short: read as the pre-registration worded it (3.4% of the offload), the "most of the offload is the lighter stack" branch fired; in ideal delta-v (a reading chosen after the run) 28–29% of the saved delta-v is the lighter stack's own thrust-to-weight gain; the offloaded run's max-Q is 3.4% above the pad's; sweep-optimized, unthrottled, calibration miss carried; the stage-2 case failed its verification.
- **RQ3-silo-screening-2d.** The cold-start silo (3 g net, 100 m, 76.7 m/s) gains +1,498.8 kg over the pad (+5.75%). That is about 2.0× the ideal-screening estimate of 765.4 kg; the loss breakdown explains the gap, so it is not a bug. *Caveat:* no structural mass is charged for the 4.0 g full-stack load, and about 8.1 t of stage-1 strengthening would cancel the gain. The note is also sweep-optimized, unthrottled, uses a free kick, and carries the calibration miss.
- **RQ2-ignition-timing-2d.** The 0.5 s + 2 s cold start costs 327.1 kg (34.74 m/s) against an instant start, 2.37× the 1-D formula (2.29–2.45× across the sweeps). Lighting on the carriage with the ramp ending at release is best, at +235.0 kg over cold; a full hot start ties the cold one. *Caveat:* under a prescribed acceleration a hot start cannot add exit speed, so the hot-start question waits for the Phase 3 `linear_motor`. silo_instant, the hot ramp and the sweeps have no ±10% run.
- **RQ6-aero-2d-preliminary.** Unthrottled max-Q falls 16.0% (31.24 against 37.19 kPa). q-alpha at the kick is 1.7–3.4× the pad's. Drag is 2% of the gain (+3.5 m/s, 32 kg). *Caveat:* there is no throttle and no angle-of-attack aerodynamics, and max-Q is pinned at the ICAO tropopause kink (11.02 km).
- **RQ3-silo-screening-1d.** The cold start gains +69.64 m/s at stage-1 burnout: 76.71 exit, + 5.40 hold-down credit, − 14.70 ignition loss, + 2.23 altitude term. Its ideal-screening equivalent is 621 kg. The full stack feels 4.0 g (21.28 MN at the interface), and the push peaks at 1.632 GW. After a failed ignition the apex is 300.27 m at 7.829 s. *Caveat:* 1-D with no atmosphere, and burnout speed is not payload.
- **RQ2-ignition-timing-1d.** The ignition loss is exact: g (t_d + t_r/2) for a ramp and g (t_d + τ) for a lag, so a lag costs as much as a ramp twice as long. The README's 5–25 m/s band is the ramp band; a lag gives 9.8–39.2 m/s. Hot starts buy no exit speed and trade 2.7–9.7 t of propellant for drive energy. *Caveat:* 1-D and prescribed-acceleration; 2-D amplifies the loss about 2×.

## Suggested reading order

1. [CAL-f9-leo-2d.md](CAL-f9-leo-2d.md), the vehicle every 2-D number rests on, and its +14.3% miss.
2. [RQ3-silo-screening-2d.md](RQ3-silo-screening-2d.md), the payload headline, the screening-beat investigation and the full caveat list. Its "What the 1-D preliminary numbers got right and wrong" section compares it with the 1-D notes.
3. [RQ1-fuel-offload-2d.md](RQ1-fuel-offload-2d.md), the same push read as propellant replaced at fixed payload, with the structural penalty rows, depth and ramp-start sweeps and the pre-registered readings.
4. [RQ2-ignition-timing-2d.md](RQ2-ignition-timing-2d.md), ignition timing, which relies on RQ3-2d's caveats.
5. [RQ6-aero-2d-preliminary.md](RQ6-aero-2d-preliminary.md), the aerodynamic side.
6. [RQ3-silo-screening-1d.md](RQ3-silo-screening-1d.md) and [RQ2-ignition-timing-1d.md](RQ2-ignition-timing-1d.md), the 1-D record: closed forms, loads, energy and the failed-ignition coast.

RQ1 (net benefit) has a note on its fuel-replacement form only: interface hardware on the vehicle, a sized structure and other vehicle classes are not covered. No notes exist yet for RQ4 (ramp design), RQ5 (drive and energy), RQ7 (vehicle redesign) or RQ8 (scale).

## Probes

[`probes/RQ3-2d/`](probes/RQ3-2d/) holds the labelled probes that RQ3-silo-screening-2d cites: the launchsim equal-γ* probe, the low-v_k probe input, and a reviewer's independent stage-2 swap probe, which uses an untested integrator. None is a shipped run, and the note labels each probe where it cites it.

## Plot files

Plots are copied here from the run directories named in each note. The file name tells you where each one comes from:

- **Prefix = note.** `CAL-` is the calibration; `RQ2-` and `RQ3-` without `2d` are the 1-D notes; `RQ1-2d-`, `RQ2-2d-`, `RQ3-2d-` and `RQ6-2d-` are the 2-D notes.
- **`derived_` after the prefix** marks a figure drawn for the note from a run's metrics.json and sweep_index.csv (RQ1-2d only), not a run's own plot; the note names its source files.
- **Next part = run.** It is the run name (`pad`, `silo_cold`, ...), or `sweepN_run_NNNN` for a sweep point, `bridge_` for silo_bridge_2d_readme, and `trigger_` for guidance_trigger_2d. The `__aero_bound` suffix marks the 21.24 m² drag-area case.
- **Last part = kind of plot:** trajectory, speed, angles, losses, q_mach, felt_g, mass_thrust, track_forces, drive_power, or altitude (1-D only).

Animations of 2-D runs are in [`../media/`](../media/).
