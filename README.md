# launch-assist-sim

A research simulator for giving rockets a ground-powered head start, and for finding out what that head start is really worth.

**Status:** Phases 0-2 done: the 1-D vertical model, the constant-acceleration vertical silo push (concept A), and a 2-D rotating-Earth ascent to orbit with drag, guidance and payload search. The Falcon 9-class calibration missed high (+14.3%, documented in `docs/findings/CAL-f9-leo-2d.md`), and the first 2-D concept-A findings are in `docs/findings/`. Phase 3 (assist models) is next; `TODO.md` tracks the steps. This README is the research brief; `CLAUDE.md` holds the build rules for Claude Code.

## Why this exists

Kerbal Space Program, OpenRocket and RocketPy all assume a rocket starts from a pad or a short launch rail. None of them can answer questions like these:

- What happens if a vertical maglev silo pushes the rocket out at 80 m/s before (or while) its engines light?
- What if a cable drive pulls the rocket along a track that curves from horizontal toward vertical?
- How much propellant does that save, how much payload does it add, what loads does it put on the rocket, and how much energy and peak power does the ground system need?

This project builds a simulator in which the launch-assist phase is a swappable model, and every result is compared against the same rocket launched normally.

## The concepts

**A. Vertical maglev silo.** The rocket stands in an underground shaft lined with electromagnetic rings, which together form a vertical linear motor. The rings push either a carriage under the rocket or supports mounted on its body. Engines light inside the shaft (a hot launch, which needs exhaust ducting) or just after the rocket leaves it (a cold launch).

Body supports avoid a carriage that has to be braked, but they fly with the rocket. A carriage stays behind, but it sits in the exhaust if the engines are lit in the shaft.

```text
         ↑  release at the silo mouth (~50–100 m/s)
 ────────┬───────┬──────── ground
         │   ▲   │
         │  ███  │  rocket
         │  ███  │
         │  ███  │  EM rings line the shaft
         │  ═══  │  carriage (or supports on the body)
         │       │  stroke L, plus braking length for a carriage
         └───────┘
```

**B. Cable-pulled ramp.** A drive pulls a cable that runs over pulleys to a carriage holding the rocket. The track starts horizontal and curves up toward vertical, and the rocket is released at the top of the curve. The original idea used a train to pull the cable.

```text
                                  ↑ release, 80–90° above horizontal
                                 ╱
                               ╱   curved section of radius R
                             ╱     (about R tall if it ends vertical)
 ═══════════════════════════╯
 [carriage + rocket] → → → →   horizontal run
 cable ← pulleys ← drive (winch, flywheel, or train)
```

**C. Baseline.** The same rocket launched from a normal pad, with its own optimized ascent. Every result is a delta against C.

**Hypothesis.** Any ground-supplied velocity, however small, cuts the propellant the rocket needs, or raises its payload. The ground energy can come from renewables and be reused every launch.

## What first-order numbers say

These are hand calculations to size the problem before any simulation exists.

### Exit speed

Exit speed is v = √(2aL), where a is the net acceleration along the track. A vertical silo must also supply 1 g just to hold the rocket's weight.

| Track length | 1 g | 3 g | 5 g |
|---|---|---|---|
| 10 m | 14 m/s | 24 m/s | 31 m/s |
| 50 m | 31 m/s | 54 m/s | 70 m/s |
| 100 m | 44 m/s | 77 m/s | 99 m/s |
| 300 m | 77 m/s | 133 m/s | 172 m/s |
| 1,000 m | 140 m/s | 243 m/s | 313 m/s |

For scale: reaching low Earth orbit takes roughly 9.4 km/s including losses. The U.S. Navy's EMALS catapult already accelerates a 45 t aircraft to about 67 m/s over 91 m. At hobby scale, RocketPy's example high-power flights leave a 5.2 m rail at 26–45 m/s.

### Why small assists matter more than they look

Payload is a thin slice of liftoff mass, about 4% for a Falcon 9-class rocket, so every m/s saved gets multiplied. The estimate below uses the ideal rocket equation with a generic Falcon 9-class two-stage vehicle and holds all losses constant. It uses public propellant and upper-stage masses; the stage-1 dry mass (25.6 t) and average stage-1 Isp (295 s) are assumed, and the fairing is dropped at staging. The model totals 542.6 t against the published 549 t.

| Assist velocity | Payload gain | Or: stage-1 propellant saved at the same payload |
|---|---|---|
| 25 m/s | +220 kg (+1.0%) | — |
| 50 m/s | +440 kg (+1.9%) | — |
| 77 m/s (100 m at 3 g) | +690 kg (+3.0%) | 14 t (3.6%) |
| 99 m/s (100 m at 5 g) | +890 kg (+3.9%) | 18 t (4.6%) |
| 150 m/s | +1,360 kg (+6.0%) | — |
| 300 m/s | +2,790 kg (+12.2%) | 53 t (13.5%) |

That works out to about 9 kg of payload per m/s, so in the ideal case the hypothesis holds. (Carrying the fairing into stage-2 flight raises the 77 m/s gain to about +740 kg.)

NASA's Magnetic Launch Assist papers cited "over 20%" onboard-fuel savings for an assist of roughly 270–280 m/s (600 mph, or 1,000 km/h), in the context of reusable and single-stage vehicles. A fixed vehicle can't get there on the rocket equation alone: a hydrogen-fueled single-stage vehicle saves only ~7% of its propellant at 275 m/s, and the table above gives 13.5% of stage-1 propellant at 300 m/s. The 20% figure probably assumes a vehicle resized around the assist. Treat it as a claim to explain, not a number to tune toward.

### What can eat the gain

The simulator's real job is to measure these penalties against the ideal numbers above.

| Penalty | First-order size | What it implies |
|---|---|---|
| Axial load on a full stack | A 3 g net vertical push means a fully fueled rocket feels 4 g. The interface carries 21.5 MN, 2.8× Falcon 9's liftoff thrust, and hydrostatic pressure at the tank bottoms rises ~2.8× over liftoff (1.4 g). Rockets normally see such g only near burnout, with nearly empty tanks. | Push gently, or strengthen stage 1 and count the mass. At 0.5 g net (1.5 g felt), 100 m gives only 31 m/s, and 77 m/s needs ~600 m of stroke. |
| Lighting engines after release | The rocket coasts against gravity until thrust builds: loss ≈ g × (delay + ramp/2) for a linear thrust ramp, or g × (delay + τ) for a first-order lag. That is 5–25 m/s for a 0–1 s delay and a 1–3 s ramp, up to a third of a 77 m/s assist. | Light the engines on the carriage, as MagLifter and Radian plan to. Then the exhaust hits whatever pushes the base. |
| Interface hardware on the rocket | 1 kg added to stage 1 costs ~0.13 kg of payload; 1 kg on stage 2 costs 1 kg. A 77 m/s assist breaks even at ~5.5 t extra on stage 1, or ~0.7 t on stage 2. | Keep magnets and supports on a ground carriage or stage 1, never on the upper stage. Strengthening stage 1 for a harder push comes out of the same ~5.5 t. |
| Curve geometry (B) | Curve radius R = v²/aₙ. At 77 m/s that is 600 m for 1 g of centripetal acceleration and 200 m for 3 g; at the start of the curve, gravity adds another 1 g of track load. A curve that ends vertical is a tower about R tall, and climbing it costs speed: at R = 200 m an unpowered carriage leaves the top at 44 m/s, and at R = 600 m it can't coast up at all. Exiting at 77 m/s from the 600 m curve takes ~3× the kinetic energy (~4.8 GJ for 549 t). | The drive has to keep pulling through the curve, as the original train-and-cable idea had it. Prior art used mountainsides (MagLifter) or wings (Radian). |
| Shallow release without wings | The flight path droops at g·cos γ / v: at 77 m/s, 5.2°/s at 45°, 3.7°/s at 60°, 1.3°/s at 80°. | Release near vertical. The release angle can replace the usual pitch-over maneuver. |
| Train traction (B) | Wheel-on-rail friction (coefficient ~0.35–0.5 in good conditions) caps a self-propelled train at a fraction of 1 g, and it has to accelerate its own mass as well as the rocket. | Use a stationary winch or flywheel drive, as launch coasters do, or a linear motor. The cable-and-pulley idea itself is sound. |
| Peak power | A 549 t rocket pushed 100 m vertically at 3 g takes ≈2.2 GJ in 2.6 s, peaking near 1.65 GW mechanical. That is ~1.2 MWh of electricity per launch at 50% efficiency. | Energy is cheap; power isn't. Store energy and discharge it fast (EMALS flywheels release up to 484 MJ in 2–3 s and recharge in 45 s), and trickle-charge from renewables. A 13 t small launcher needs only ~38 MJ of kinetic energy, less than one EMALS launch (122 MJ). |
| Silo air (A) | A snug shaft acts like a piston: up to atmospheric pressure × bore area. A 3.7 m bore sees up to 1.1 MN, ~5% of a 21.5 MN drive force. A 140 mm hobby tube sees up to 1.6 kN, against ~0.2 kN of drive force for a 5 kg rocket. | Vent the shaft, or model the air column. |
| Carriage braking | At 77 m/s, a carriage braking at 5 g needs ~60 m. | The facility is longer than the stroke. |
| Failed ignition (A) | After a 77 m/s vertical exit, an unlit rocket coasts ~300 m up for ~7.8 s, then falls back into the silo. | Needs an abort mode; a slight tilt may help. |
| Sideways loads | A fueled rocket lying on a horizontal track, or turning through a curve, carries sideways loads along its whole length. Supports along the body concentrate loads at new points. | Report sideways loads from the start; do structural analysis later. |
| Aerodynamics | Extra speed low in the dense atmosphere raises drag loss and possibly peak dynamic pressure (max-Q). | Only a trajectory simulation answers this. |

## Prior art

| Project | What it did | Status | Lesson |
|---|---|---|---|
| NASA Magnetic Launch Assist / MagLifter (1990s–2000s) | Horizontal maglev track about 1.5 miles long, 600 mph in 9.5 s. A superconducting-sled study put levitation modules at ~4% of liftoff weight, for vehicle-plus-sled masses up to ~600 t. | Technology demos only; systems like it were estimated to cost billions | The closest precedent; its claims are a benchmark to explain |
| EMALS, U.S. Navy (Ford-class carriers) | A 91 m linear motor launches a 45 t aircraft to 240 km/h. Four flywheel alternators store 121 MJ each, released in 2–3 s and recharged in 45 s. | Operational | Proves the ~100 m, ~2.5 g, ~70 m/s regime at 45 t |
| Holloman maglev sled, U.S. Air Force (2016) | A rocket-propelled, superconducting maglev sled reached 633 mph on a 2,100 ft track. | Test facility | Maglev works for sleds near Mach 1 |
| DARPA/NASA Horizontal Launch Study (2011) | Reviewed 130+ horizontal-launch studies spanning 60 years. | Only Pegasus ever became operational | Many concepts close on paper; cost decides |
| NASA KSC railgun launch assist (2011) | Argued a railgun could give a heavy vehicle 2–3 g for several seconds, beyond Mach 1. | Analysis and lab tests | Another drive option |
| Radian Aerospace | A rocket-powered rail sled, about 2 miles long, releases a winged spaceplane at Mach 0.7 with its engines already lit. | In development; subscale tests in 2024 | Wings make a shallow release workable |
| SpinLaunch | A 33 m vacuum centrifuge threw test vehicles at ~10,000 g in 10 flights (2021–22). | No orbital system built, as of 2025 reports | Kinetic launch suits only g-hardened payloads |
| Long March 11, China | A 58 t solid-fuel launcher cold-launched from a tube, igniting after ejection; 700 kg to low Earth orbit. | Operational | "Eject, then ignite" works at 58 t with solid motors |
| Intamin Accelerator Coasters (e.g., Kingda Ka, 2005–2024) | A hydraulic winch and cable pull a catch car: 0–206 km/h in 3.5 s, then a vertical climb up a 139 m tower. Kingda Ka's drive could deliver up to 15.5 MW. | Kingda Ka demolished in 2025 | Concept B at amusement-park scale, including rollbacks when speed falls short |

## Research questions

1. **Net benefit.** How does payload (or propellant) change with exit speed for each vehicle class, after interface mass, extra structure and ignition losses? Where is break-even?
2. **Hot or cold start.** Engines lit on the carriage versus after release: how sensitive are results to ignition delay and thrust ramp?
3. **Silo design.** Stroke versus the g a fully fueled stack can take (or the extra structure it would need), venting, carriage braking, and a failed-ignition abort (vertical versus slightly tilted exit).
4. **Ramp design.** Release angle versus payload; curve radius versus sideways load versus tower height. Is near-vertical release mandatory without wings?
5. **Drive and energy.** Linear motor versus cable winch (versus counterweight); cable dynamics; efficiency; energy-storage size; renewable charging at a given launch cadence.
6. **Aerodynamics.** How do drag loss and max-Q change when the rocket starts fast, low in the atmosphere?
7. **Vehicle redesign.** A Falcon 9 lifts off at a thrust-to-weight ratio near 1.4. With an assist, can stage 1 carry smaller or fewer engines, and what is that worth?
8. **Scale.** Hobby rocket, small launcher (~13–60 t), medium launcher (~550 t): where does the idea pay off, and where does existing EMALS-class hardware already suffice?

## The simulator at a glance

- **Phases:** hold → assist (motion along a track of any shape) → release → ignition → ascent (2-D, spherical rotating Earth, standard atmosphere, drag varying with Mach) → staging → orbit insertion.
- **Assist models (swappable):** none (pad), constant acceleration (screening), linear motor (force- and power-limited), track geometry (vertical, straight, curved), and cable winch (elastic cable, drum inertia, pulleys).
- **Outputs for every run:** payload or propellant margin versus baseline; gravity, drag, steering and back-pressure losses; max-Q; peak felt axial and sideways g, and the interface force; assist energy, peak power and facility length.
- **Validation first:** every physics piece gets an analytic test before any experiment is trusted. The list lives in `CLAUDE.md`.

## What you need to start

### Knowledge, in the order you'll need it

1. The rocket equation, staging, Δv budgets and loss terms. Sutton & Biblarz, *Rocket Propulsion Elements*; Curtis, *Orbital Mechanics for Engineering Students* (its rocket-dynamics chapter covers the gravity turn).
2. Numerical integration of ODEs with events (SciPy `solve_ivp`): tolerances, event detection, convergence checks.
3. Atmospheric flight: standard atmosphere, drag versus Mach, dynamic pressure. Anderson, *Introduction to Flight*.
4. Orbit basics: circular velocity, vis-viva, the boost from Earth's rotation. Bate, Mueller & White, *Fundamentals of Astrodynamics*.
5. Ascent guidance, then optimal control for fair comparisons: gravity turn, then linear-tangent steering, then direct collocation (Dymos/OpenMDAO or CasADi).
6. Linear motors and pulsed power at the black-box level: force–speed curves, efficiency, and flywheel, capacitor and battery storage. The EMALS literature is a good start.
7. Load paths: axial versus sideways loads, why rocket tanks are pressure-stabilized, how hardpoints add mass.
8. Cables and pulleys (concept B): cable stretch, oscillation, drum inertia, sheave friction.

### Software

Python 3.12 managed with uv; numpy, scipy, pandas and matplotlib; PyYAML and pydantic for configs; pytest and ruff; `ambiance` for the ICAO standard atmosphere (valid to about 81 km); RocketPy for 6-DOF hobby-scale comparisons; later, Dymos/OpenMDAO or CasADi for trajectory optimization; JupyterLab for exploration. Git, plus a private GitHub repo.

### Data

- Public vehicle numbers (Falcon 9, Electron, Long March 11). Each value in a vehicle file names its source, and anything estimated is marked as assumed.
- A generic drag-versus-Mach curve for slender launchers to start with; RocketPy or OpenRocket curves at hobby scale.
- For the hobby-scale case, a real rocket's measured mass, center of gravity and motor thrust curve (a Level 1 build works well).
- EMALS and launch-coaster figures to sanity-check drive sizing.

### Compute

A laptop. A single ascent simulation takes seconds at most, thousand-run sweeps take minutes, and trajectory optimization takes minutes to hours.

### Safety

This is a simulation project. Before building any physical assist device at hobby scale, talk to your club's range safety officer: it isn't a standard launcher and may not be allowed at club launches. Amateur rocket flights in the U.S. also fall under FAA rules (14 CFR Part 101).

## Roadmap

| Phase | Deliverable | Done when |
|---|---|---|
| 0. Scaffold | Package, constants, atmosphere wrapper, CLI stub, test harness | Tests pass and the commands in `CLAUDE.md` work |
| 1. Vertical 1-D | Rocket equation, gravity and staging in one dimension | Rocket-equation, gravity-loss and coast-apex tests pass |
| 2. Ascent to orbit | Spherical rotating Earth, drag, thrust versus ambient pressure, gravity turn, loss budget, payload search | Orbit, loss-budget and convergence tests pass; the generic Falcon 9-class vehicle lands within ±10% of 22.8 t to low Earth orbit at a stated reference altitude |
| 3. Assist models | Constant acceleration, linear motor, track geometry (vertical, straight, curved), cable winch, ignition timing | Track, ramp-energy, release-mapping, energy-balance and cable tests pass |
| 4. Experiments | Sweeps for research questions 1–8 | Each question has a write-up in `docs/findings/` with plots and caveats |
| 5. Fair comparison | Optimized ascent for each configuration (Dymos or CasADi) | Headline results re-run with optimized guidance |
| 6. Hobby scale in 6-DOF | RocketPy model of a real rocket with an assist before the rail | Baseline apogee matches RocketPy within ±5%, and the assist's effect is quantified |

## Repository layout

`CLAUDE.md` has the annotated version.

```text
launch-assist-sim/
├── README.md
├── CLAUDE.md
├── pyproject.toml
├── src/launchsim/     physics, models, simulation, CLI
├── configs/vehicles/  vehicle definitions with sources
├── experiments/       one YAML file per experiment
├── results/           generated output, never hand-edited
├── docs/physics.md    equations and assumptions
├── docs/findings/     one write-up per research question
├── notebooks/         exploration only
└── tests/
```

## Working with Claude on this

- Build in the Code tab with this folder open, starting each phase in Plan mode. Use Opus 5.5 at high effort for implementation, and Fable 5.1 (or Opus 5.5 at xhigh) for physics design and for debugging results that look wrong.
- Do literature digging and physics Q&A in Chat, then save conclusions to `docs/findings/` so Code sessions see them.

## References

- NASA Magnetic Launch Assist overview (science.gov): https://www.science.gov/topicpages/m/magnetic+launch+assist
- NASA MSFC maglev launch-assist paper (NTRS 20000103883): https://ntrs.nasa.gov/api/citations/20000103883/downloads/20000103883.pdf
- Hybrid chemical–electrical launch assist, MagLifter SSTO context (NTRS 20090034160): https://ntrs.nasa.gov/api/citations/20090034160/downloads/20090034160.pdf
- Magnetic Launch Assist, NASA's vision for the future: https://www.researchgate.net/publication/3102084_Magnetic_Launch_Assist_-_NASA's_vision_for_the_future
- Superconducting magnets for Maglifter launch-assist sleds: https://www.researchgate.net/publication/3311683_Superconducting_magnets_for_Maglifter_launch_assist_sleds
- Report of the DARPA/NASA Horizontal Launch Study (NTRS 20110015353): https://ntrs.nasa.gov/citations/20110015353
- Near-term horizontal launch results (NTRS 20130000446): https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20130000446.pdf
- The Feasibility of Railgun Horizontal-Launch Assist (NTRS 20110005535): https://ntrs.nasa.gov/citations/20110005535
- Electromagnetic Aircraft Launch System: https://en.wikipedia.org/wiki/Electromagnetic_Aircraft_Launch_System
- Holloman maglev sled record: https://www.airandspaceforces.com/breaking-the-maglev-record-again/
- Radian Aerospace: https://payloadspace.com/radian-aerospace-deep-dive/ and https://spacenews.com/radian-aerospace-begins-tests-of-spaceplane-prototype/
- SpinLaunch: https://www.space.com/spinlaunch-aces-10th-suborbital-test-launch and https://thespacebucket.com/spinlaunch-is-still-trying-to-make-an-orbital-accelerator/
- Long March 11: https://en.wikipedia.org/wiki/Long_March_11
- Accelerator Coaster launch system: https://en.wikipedia.org/wiki/Accelerator_Coaster
- Kingda Ka: https://en.wikipedia.org/wiki/Kingda_Ka
- Wheel–rail adhesion: https://en.wikipedia.org/wiki/Adhesion_railway
- Falcon 9: https://www.spacex.com/vehicles/falcon-9 and https://en.wikipedia.org/wiki/Falcon_9_Block_5
- Electron: https://en.wikipedia.org/wiki/Rocket_Lab_Electron
- RocketPy: https://github.com/RocketPy-Team/RocketPy and https://docs.rocketpy.org/
- ambiance (ICAO standard atmosphere): https://github.com/airinnova/ambiance
- Dymos: https://openmdao.github.io/dymos/
