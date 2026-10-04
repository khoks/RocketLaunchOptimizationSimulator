# SP7: Structural mass of the push load, and a force-limited drive (planar model)

Status: not started

Phase file of the program board ([README.md](README.md)). How a session runs:
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Written 2026-10-04 in
the SP1 session (step 10, the close-out) after decision D-SP1-18, which added this phase
and ordered it after SP2 and before the 3-D phases SP3-SP6. The number is an identifier,
not a position (board, "How to add a phase"). Nothing in this file has been built or run.
No design input exists under docs/phases/inputs/ yet: SP7's own Plan mode makes the
design and saves it there. The session before SP7 (SP2's close-out in the planned order)
re-checks sections 4, 6 and 13 against the code as it then is and finalises the prompt.

This file is a brief, not the detailed design. Where it offers options, it gives a
recommendation; SP7's Plan mode settles them with the user before any code is written.

## 1. Goal and what you can see at the end

**Goal.** Charge the structural mass that the 4 g full-stack push needs, so that the
fuel-offload and payload findings carry a modelled structural cost instead of the assumed
penalty rows; and build the drive realism that interacts with that cost: a force- and
power-limited linear motor, carriage mass and modelled braking, and the silo air column.
These are the README roadmap Phase 3 items that bear on the answer (README, "Roadmap";
TODO.md B-004, B-005, and parts of B-007).

Why now (D-SP1-18): SP1's headline is 41.26 t of stage-1 propellant, 10.04% of stage 1
and 7.96% of the total, at the pad's payload and orbit, before any structural mass
(docs/findings/RQ1-fuel-offload-2d.md). Its assumed penalty rows show how fragile that is:
+2, +4 and +8.1 t of stage-1 dry mass leave 32.29, 22.88 and 1.98 t, and about 8.5 t
(extrapolated) leaves nothing. How much strengthening the 4 g push really needs, at the
low end of those rows or near their top, therefore decides whether the 10% survives,
while the 3-D models are expected to move the
headline by kilograms (D-SP1-18; SP3 pre-registers |dP*| < 5 kg of payload against the
planar gate). So the structural question comes first.

At the end you can see:

- a first-order structural sizing model, validated against closed forms, that turns a
  push (felt g, the stack mass and propellant levels on the track, where the load enters)
  into an added stage-1 dry mass, with every coefficient sourced or `assumed: true`;
- the headline offload re-solved with that modelled mass, as a central value with an
  uncertainty band, beside SP1's parametric penalty rows (which stay as the bracket);
- the depth question re-opened: at a fixed exit speed a deeper, gentler push needs less
  structure, so with structure charged the offload no longer stays the same by
  construction across strokes (RQ1, "Depth and g-level");
- a `linear_motor` silo run (force and power limits, efficiency, carriage mass) beside
  the `constant_accel` run it replaces, and the hot-start question that RQ1 left open
  under the prescribed drive;
- `uv run python -m launchsim run experiments/<SP7 file>.yaml` reproducing it from a
  pre-registered experiment; the findings note updated; a recorded demo under
  docs/demos/SP7/.

This phase may produce a result that undercuts the hypothesis (a modelled structure that
cancels most of the offload). That result is reported as plainly as any other (CLAUDE.md,
"Project"; protocol section 6).

## 2. Scope and out of scope

**In scope (proposed; Plan mode confirms each line)**

1. A first-order structural sizing model of the stage-1 load path for the push, as a pure
   module: tank walls (hoop stress from ullage plus hydrostatic pressure at the felt g;
   axial compression from the inertial load less the pressure relief, against a buckling
   allowable), the tank bottoms, the structure where the carriage load enters, and the
   interface hardware on the rocket (B-004 names it). Charged as the increment over the
   vehicle's existing load envelope (section 5.2), so a push inside the envelope costs
   nothing.
2. A structure file per vehicle with the sizing coefficients and a stage-1 mass breakdown,
   every number sourced or `assumed: true`; the calibrated vehicle files stay untouched.
3. The coupling of the modelled mass into SP1's offload solve and into the payload search,
   reported beside the penalty rows (the rows stay; D-SP1-04).
4. An uncertainty band: the headline re-solved at low, central and high coefficient sets
   (section 5.6).
5. `linear_motor`: F = min(F_max, P_max / sdot) with efficiency eta, a stated force rise
   time (finite jerk), carriage mass, and release at s = L or at a target speed
   (CLAUDE.md, "Physics model", items 2 and 3). It replaces the `PlannedAssistConfig`
   placeholder for that key (config.py 78, 708).
6. Modelled carriage braking after release (distance, time, energy) instead of the closed
   form added to the facility length, and a sealed-shaft air column (adiabatic trapped
   column) beside the vented default. Proposed, and the first items to cut if the session
   runs short: they move facility length, drive force and energy, and under the
   force-limited drive the exit speed, but they are not the structural answer (section
   5.7). TODO.md B-007 is re-targeted when Plan mode confirms them.
7. Validation tests for each new physics piece before any experiment uses it (section
   5.9); `docs/physics.md` updated in the same change as each.
8. A pre-registered experiment (committed before it is run), the runs from a clean
   commit, the findings, and SP7's close per the protocol (public face, SP3's file
   fact-checked, handoff, memory).

**Out of scope (each has a home)**

- Structural FEM, shell buckling analysis beyond closed forms, or any load model beyond
  first order. CLAUDE.md lists structural FEM as a scope expansion that needs the user's
  approval; this file does not propose it (section 5.3, option C).
- Bending from wind or q-alpha, lateral loads on the track, and the max-Q load case as a
  sizing input beyond what the envelope check needs. The kick has no angle-of-attack
  aerodynamics in the model (RQ6); a q-alpha structural case needs that first.
- The curved track and the frictionless circular-arc ramp test, the cable winch and its
  small-oscillation test, friction, the tilted-exit abort with Coriolis, engine shutdown
  transients: the README Phase 3 remainder (TODO.md B-006, B-008, B-009, friction in
  B-007), on the board's "Later" table. Friction from the normal load is zero on a vertical
  straight track (its track-normal load is 0; RQ3-2d, "Loads"), so it belongs with the
  curved and inclined tracks.
- A resized vehicle (tanks shrunk around the offload; RQ7) and interface hardware on
  stage 2.
- Throttling and a max-Q constraint (TODO.md B-003, README Phase 5).
- The 3-D models (SP3-SP6) and the app's form: SP2's app exposes the penalty field
  (D-SP1-04), not the structural model; adding it to the form is a backlog item unless the
  user asks for it in Plan mode.
- Any change to a validated number: the pad baseline, the 1-D golden outputs, the planar
  digests, SP1's recorded runs (section 5.10).

## 3. Decisions already taken

Cited by id; the text is in TODO.md's decisions log.

- D-SP1-18 (2026-10-04, user): SP2 runs next as planned; then this phase, SP7, for the
  structural mass of the push load and a force-limited drive, inserted before the 3-D
  phases SP3-SP6, because the structural cost decides whether SP1's 10% survives while
  the 3-D models are expected to move it by kilograms. Phase numbers are never
  renumbered. It amends the order of D-SP1-07.
- D-SP1-04: the structural penalty is shown as parametric rows (+2, +4, +8.1 t of assumed
  stage-1 dry mass on the assisted run only). SP7 keeps those rows beside the modelled
  mass; it does not replace them.
- D-SP1-03: offload semantics (stage 1 is the headline; tanks partly filled, dry masses
  unchanged except a penalty; fixed payload P_ref = the full-load pad's P* on the same
  vehicle and orbit). The modelled structure is an added dry mass on the assisted run
  only; the pad keeps its vehicle.
- D-SP1-09 and D-SP1-10: the `offload:` block and post-pass; pad controls; stage 1 the
  only headline.
- D-SP1-08: one fresh session for the phase; it prepares the next phase's documents,
  memory and prompt (SP3 in the planned order).
- D-SP1-14 to D-SP1-16: push after every step; public face kept current at the close.
- D-P1-01: `constant_accel` is a prescribed net acceleration, so carriage mass and drive
  efficiency move only energy and power, and a hot start buys no exit speed. The linear
  motor is the model where they can move the exit speed and the offload.
- D-P2-08: the gate vehicle's +14.3% calibration miss travels with every number.

## 4. Entry criteria

1. SP2 is "done" on the program board (the planned order, D-SP1-18). SP7 uses nothing from
   SP2: if the user moves SP7 ahead of SP2, SP1 "done" is enough, the move is logged as a
   decision in TODO.md, and SP2's file is re-checked afterwards (SP7 edits config.py, the
   assist package and the offload reporting, which SP2's inventory names).
2. Clean tree; HEAD is the bookkeeping commit that follows the closing commit the handoff
   names (SESSION_PROTOCOL.md section 3, item 3).
3. Fast suite green (`uv run pytest -q -m "not slow"`); ruff clean; the 1-D golden tier,
   SP1's planar digest pin
   (`tests/test_config_planar.py::test_shipped_planar_resolved_dicts_match_the_pinned_digests`)
   and the planar output capture
   (`tests/test_planar_pipeline.py::test_written_outputs_keep_the_captured_structure`)
   pass; the pad and silo_cold payload capacities reproduce 26,054.3962 and 27,553.2271 kg
   within 0.002 kg (SP1 step 5 gate).
4. SP1's offload solver and pipeline exist as SP1 left them: `OffloadProblem` built from a
   problem factory (offload.py 151, 256), the `offload:` block with
   `stage1_dry_mass_added_t` (config.py 1637), the cross-vehicle decomposition with a
   dry-mass difference (compare.py 1534), and the slow test that re-solves the headline
   (`tests/test_offload.py::test_gate_silo_offload_recorded_run_and_verification`, 795).
5. SP1's run data on disk for comparison: `results/silo_offload_2d/20261003T112934Z` (the
   headline and the penalty rows) and `results/silo_offload_2d/20261003T112949Z` (sweep 2,
   the fixed-exit-speed strokes), or re-runs of them from SP1's closing commit (CSVs are
   not tracked).
6. Section 6 of this file has been re-checked at the current HEAD and its commit and date
   updated by the session before SP7. SP2 edits `plots.py`, `replay.py`, `cli.py` and adds
   modules; it may touch `config.py` (a display block) and `results_io.py` (a hook) if its
   Plan mode chose to.
7. `gh` is authenticated and the last Pages deployment is green (push cadence, D-SP1-15).

## 5. Design

Proposed, for SP7's Plan mode to confirm or change. Three CLAUDE.md rules bind it:

- Plan mode for anything touching equations of motion, frames, events, integrator settings
  or loss accounting, with `docs/physics.md` updated in the same change. The linear motor,
  the air column and the braking phase touch the track equation and events; the
  structural model changes a vehicle input (dry mass) only.
- No physics feature is used in an experiment until its closed-form test passes.
- Never tune a parameter to make an assist look better; never edit a calibrated vehicle
  file (copy it); justify every new dependency in one line.

### 5.1 What is charged today

Nothing structural. The 4 g0 full-stack push (3.996 g0 felt at 3 g0 net; 22.49 MN at the
interface for the full-load silo_cold, 20.81 MN for the offloaded headline) carries no
added mass. The README's first-order row: the interface carries 21.5 MN, 2.8 times
Falcon 9's liftoff thrust, and the hydrostatic pressure at the tank bottoms rises about
2.8 times over liftoff (README, "What can eat the gain"). The only stand-ins are:

- payload space (RQ3-2d): 184 kg of payload per tonne of stage-1 dry mass, from the
  +/-10% dry-mass cases; about 8.1 t of silo-only strengthening cancels the +1,498.8 kg
  gain (a linear extrapolation);
- offload space (RQ1): the penalty rows above; each tonne of assumed structure takes 4.5
  to 5.1 t off the offload, and the erosion steepens.

Both notes say plainly that the needed mass is unknown. SP7's model supplies an estimate
of it with an uncertainty band; it does not make the rows obsolete.

### 5.2 The load case the push adds

The push is one more quasi-static axial load case: every station x of the stack carries
the compressive load m_above(x) n g0, and each tank's liquid presses on its bottom with
p(h) = p_ullage + rho n g0 h, where n is the felt axial load factor and h the depth below
the liquid surface. What makes the push new is the combination of a high n with full
stage-1 tanks. The existing vehicle already flies (from the pad run's own time series):

- liftoff: about 1.36 g0 felt at release with full tanks (RQ3-2d, "Loads");
- MECO: 5.195 g0 felt on the 161.5 t stack, stage 1 nearly empty (RQ3-2d, "Loads";
  5.19547 g0 in RQ1's "Headline" table);
- max-Q in between (37.19 kPa unthrottled, pad).

The model charges only what the push needs beyond that envelope, station by station. A
first look from the recorded values, for the Plan mode to confirm with the model: at the
interstage and above, the mass is the same at the push and at MECO (stage 2 full, the
payload, the fairing), and the push's 4.0 g0 is below MECO's 5.2 g0, so the push should
not size stage 2 or the interstage. In the stage-1 tanks and the aft structure the push
carries the stage-1 propellant (all of it, less any offload) at about 4 g0 against
1.36 g0 at liftoff with the same tanks full, so that is where the mass goes. These statements are quasi-static. A sudden push overshoots: the
`constant_accel` model has infinite jerk at push start (its own assumption list), and a
step load on an undamped elastic structure peaks at twice the static load (the
dynamic-load-factor closed form for a step; for a linear ramp of rise time t_r it is
1 + |sin(pi t_r / T)| / (pi t_r / T), T the structure's period). The linear motor's force
rise time therefore enters the structural load, and the Plan mode decides whether SP7
charges a dynamic load factor from a stated rise time and an assumed period, or reports
the quasi-static mass with the factor as a sensitivity.

Where the load enters is a design choice with mass consequences (question Q5): an aft
ring at the stage base (the whole stack above is compressed, as under thrust), the thrust
structure (it then carries 22.5 MN instead of the engines' 8.23 MN vacuum thrust), or
supports along the body (they fly, and the README notes they concentrate loads). The
hydrostatic pressure at the tank bottoms is the same whichever way the stack is pushed.

### 5.3 Structural sizing model: options

| Option | What it is | Cost | Fit |
|---|---|---|---|
| A. Parametric fraction | Added mass = a load-bearing fraction of stage-1 dry mass times (n_push / n_envelope - 1), coefficients assumed | Small | Little more than the penalty rows with a rule for picking the row; the coefficients carry the whole answer and no closed form checks them |
| **B. First-order station sizing (recommended)** | Thin-walled cylinders and domes per tank: wall thickness from hoop stress (Barlow, p r / t) at ullage plus hydrostatic pressure, and from axial compression (inertial load less pressure relief p pi r^2) against a classical buckling allowable times a knockdown factor; tank bottoms sized by the hydrostatic pressure; the load-entry structure and the interface hardware scaled with the peak interface force by a sourced or assumed coefficient. Each element's thickness is taken as the larger of the push requirement and the envelope requirement; only the excess mass is charged | Medium: one pure module, about a dozen closed-form tests, a structure file with sourced coefficients | Every term has a closed form to test, the coefficients are physical (material allowables, factors of safety, knockdown, densities, ullage pressures) and can be sourced, and the increment is zero inside the envelope by construction |
| C. FEM or detailed shell analysis | A finite-element or shell-buckling model of stage 1 | Large, and a scope expansion that needs the user's approval (CLAUDE.md) | Not proposed: the model's inputs (geometry, the real envelope and margins) are not public, so the extra fidelity would rest on assumptions anyway |

Recommendation: B. Candidate sources to check in step S0 (named here as places to look,
not as values): NASA SP-8007 (buckling of thin-walled circular cylinders; knockdown
factors), NASA-STD-5001 (structural factors of safety for spaceflight hardware), material
data for the tank alloy, the propellant densities behind the vehicle file's LOX/RP-1 split
(287.4 t LOX and 123.5 t RP-1 in stage 1, configs/vehicles/generic_f9_class_2d.yaml), and
any public breakdown of the 22.2 t stage-1 dry mass (engines, thrust structure, tanks,
interstage). Where no source exists the number is `assumed: true` and gets a sensitivity.

A plausibility check, labelled calibration and not validation: the model's tank mass for
the pad's own envelope, against the stage-1 dry mass and its breakdown. Nothing is tuned
toward a target; a large disagreement is reported and widens the band.

### 5.4 Where the coefficients live

Proposed: `configs/structures/<vehicle>.yaml` (one per vehicle that an SP7 experiment
flies: the gate vehicle and, for the bridge, the README-loads fork), every number with
`source:` or `assumed: true`, validated by a pydantic model, read only by the structural
model. Alternatives: a `structure:` block inside a forked vehicle file (a copy of the
calibrated file, CLAUDE.md), or inside the experiment's `offload:` block. The separate
file keeps the calibrated vehicle files and every resolved dict of the shipped experiments
unchanged, which the digest pin checks (section 5.10).

### 5.5 Coupling to the offload solve

The structural mass depends on the stack on the track, which depends on the offload x
itself: a lighter stack needs less strengthening. Options:

| Option | How | Trade-off |
|---|---|---|
| **(i) Inside the problem factory (recommended)** | Wrap the factory SP1 built: the problem at offload x flies the vehicle offloaded by x with stage-1 dry mass raised by dm(x), the sizing model applied to that vehicle's push. `solve_offload` is unchanged | One solve; the solver's own monotonicity check (`offload_nonmonotone`) tests the argument that m_res still falls with x (dm falls as x grows, so this must be checked, not assumed) |
| (ii) Fixed point | Solve x with dm fixed, re-size at x*, repeat until dm changes by less than a tolerance | Uses the penalty-row path as it is; several solves (about 90-110 s each with the verification, measured in SP1) |
| (iii) Size for the full-load push | dm computed once for the full stack and charged at every x | Simple and conservative (a vehicle that can also fly full); over-charges the offloaded vehicle. Proposed as a bound row beside (i) |

Which load the structure is sized for (the offloaded stack actually flown, or the full
load) is a modelling choice that changes the answer; it is question Q2 for the user. A
cross-check that fixes the coupling: the structural model forced to return a constant
2 t must reproduce SP1's `silo_cold_s1_dry+2t` row (32,285 kg; RQ1) within the
reproduction tolerance SP1 used for its headline (about 3.8 kg; RQ1, "Headline").

Pre-registration idea for step S6: the modelled dm at the headline, computed before any
solve, placed on the penalty-row curve (32.29, 22.88, 1.98 t at +2, +4, +8.1 t) by
interpolation, gives the expected offload; the solve should land near it, differing only
through dm's dependence on x.

The payload form (RQ3) is re-solved the same way: silo_cold's P* with the modelled dm of
its full-load push, against the pad's 26,054.4 kg and the 184 kg-per-tonne line.

### 5.6 Uncertainty band

The coefficients, not the solver, set the uncertainty. Proposed: three coefficient sets
(low, central, high) fixed in the structure file before the run, each propagated through
a full offload solve; plus one-at-a-time sensitivities on the coefficients that move dm
most (identified in step S2 from the sizing model alone, without flying). The band is
reported as the offload range, with dm beside each end. If the band is wider than the
offload itself, the note says the model cannot decide whether the 10% survives, and why.

### 5.7 Drive realism and how it reaches the structural answer

| Item | Under `constant_accel` today | Under a force-limited drive | Reaches the structural answer by |
|---|---|---|---|
| Force and power limits (`linear_motor`) | Drive force unbounded, solved from the prescribed acceleration | F = min(F_max, P_max / sdot): constant force, then constant power; the exit speed follows from the limits and the stroke | Setting the felt g (and so dm) and the exit speed (and so the offload) together |
| Force rise time | Infinite jerk | A stated ramp of the drive force | The dynamic load factor of section 5.2 |
| Carriage mass | Moves only drive energy (the 22 t sled changed nothing for the vehicle and added 3.8% drive energy; RQ3-2d) | At a fixed F_max a heavier carriage lowers the acceleration, the interface force and the exit speed | Lower felt g, lower exit speed |
| Hot start | Thrust on the track buys no exit speed; the interface force falls to 14.5-14.8 MN against 22.5 MN (RQ3-2d) while the tanks feel the same g | Thrust adds acceleration and exit speed | The tanks see a higher g; in the force-limited phase the interface force is (m_v / M) F_max - T (m_c + f_imp m_v) / M, from the track equation of assist/base.py (exactly F_max for a massless carriage and no impingement). RQ1's ordering of hot starts "may change with a force- or power-limited drive" |
| Air column (sealed shaft) | Moves only drive force and energy; the vented shaft's drag biases energy, power and interface force low by about 0.04%, 0.08% and 0.08% (RQ3-2d) | Lowers the exit speed; the README bounds the piston force at atmospheric pressure times the bore area (up to 1.1 MN for a 3.7 m bore) | Whether it acts on the carriage (below the vehicle) or on the vehicle decides whether it reaches the interface force at all |
| Braking | Distance v^2 / (2 a_brake) added to the facility length (60 m at 5 g0) | The same closed form, now a modelled phase | Facility length and the failed-ignition geometry only; not the structural mass |

Linear motor closed forms for the tests, on a vertical track with constant mass M (a cold
start) and g = g_eff: the force-limited phase has a = F_max / M - g, v = a t, s = a t^2 / 2,
up to the corner speed v_c = P_max / F_max. In the power-limited phase,
M dv/dt = P_max / v - M g; with v_inf = P_max / (M g), from (t_c, s_c, v_c):

    t - t_c = (1/g) [ (v_c - v) + v_inf ln((v_inf - v_c) / (v_inf - v)) ]
    s - s_c = (1/g) [ (v_c^2 - v^2)/2 + v_inf (v_c - v) + v_inf^2 ln((v_inf - v_c) / (v_inf - v)) ]

and on a horizontal track (g = 0), v^2 = v_c^2 + 2 P_max (t - t_c) / M and
v^3 = v_c^3 + 3 P_max (s - s_c) / M. The assist energy identity of CLAUDE.md ("Validation
first") holds with eta and the piston work as stated terms. Parameter values (F_max,
P_max, rise time, carriage mass) are design choices marked `assumed: true`, chosen in Plan
mode by a rule stated before any run (for example: the limits that reach the headline's
76.7 m/s at 100 m with a stated rise time), never adjusted toward a better offload.

### 5.8 Experiments (proposed; pre-registered in step S6)

1. The headline case (3 g0, 100 m, cold start, stage-1 solve) with the modelled structure:
   central, low and high sets; the full-load-sizing bound row; SP1's penalty rows re-run
   or cited beside it.
2. The stroke at the fixed exit speed 76.7072 m/s (50, 100, 200, 300 m; SP1's sweep 2:
   felt 7.0, 4.0, 2.5, 2.0 g0; electricity 1,012 to 1,733 kWh; facility 110 to 360 m)
   with the structure charged: where depth stops being the same by construction, and
   whether a stroke exists where the structural cost is small against the offload.
3. `linear_motor` against `constant_accel` at the same exit speed and stroke; a hot start
   under the force-limited drive; carriage mass 0 against 22 t.
4. The air column (vented against sealed) under the force-limited drive, if taken.
5. The payload form: silo_cold's P* with the modelled structure.
6. The bridge on the README-loads fork (robustness against the calibration miss), one
   case.

The run time is minutes per solve (SP1: about 90-110 s per solve with its verification,
about 30 s per pad control; the full SP1 run about 14 min and its sweep about 21 min, with
the three SP1 commands running at once); Plan mode budgets the design against that.

### 5.9 Validation tests (before any experiment uses the piece)

- Hydrostatic pressure p = p_ullage + rho n g0 h against the closed form; the load factor
  of a push equals (a + g_eff) / g0 (3.9991 g0 at 3 g0 net in the 1-D model without
  rotation, docs/physics.md "Silo model"; 3.996 g0 on the planar track at 28.5 deg).
- Thin cylinder: hoop thickness p r / sigma; axial stress p r / (2 t) - F / (2 pi r t);
  classical buckling stress E t / (r sqrt(3 (1 - nu^2))) times the knockdown; dome
  thickness p r / (2 sigma) for a hemisphere. Each against a hand-computed value in the
  test, not the code's own formula.
- Zero increment inside the envelope, exactly; the increment non-decreasing in n and in
  the propellant on board; the pad's own load cases give zero.
- The coupling cross-check of section 5.5 (a constant 2 t reproduces the +2 t row).
- Linear motor: the force-limited and power-limited closed forms of section 5.7 (vertical
  and horizontal), the force and power limits honoured at every sample, the assist energy
  identity with eta (relative error < 1e-6, the CLAUDE.md bound), release at a target
  speed.
- Dynamic load factor: step (2) and linear ramp closed forms, if Plan mode takes it.
- Braking: distance v^2 / (2 a) and time v / a for a constant deceleration.
- Air column: p = p0 (V0 / V)^gamma for the trapped column and its work integral in the
  energy identity; the force bounded by p_atm A.
- Convergence: tightening tolerances 10x changes the structural offload by < 0.1%.

### 5.10 What must not move

- The 1-D golden tier, SP1's planar digest pin and the planar output capture.
- The pad and silo_cold P* within 0.002 kg; SP1's headline offload with the structural
  model off (the slow test of entry criterion 4).
- The shipped experiment and vehicle files, byte for byte. New config fields go on the new
  models (`LinearMotorConfig`, the structure file) or are left out of `model_dump` when
  unset, as SP1 did for `exit_speed_mps`; a default added to `ConstantAccelConfig` would
  change every resolved dict and break the digest pin (the same risk as SP3's risk 5).

### 5.11 Module layout (proposed)

| File | Content |
|---|---|
| `src/launchsim/structure.py` (new, pure) | load cases from a run's track and flight records, the envelope, the sizing elements, the increment |
| `src/launchsim/assist/linear_motor.py` (new, pure) | `LinearMotorAssist` behind `assist.base.AssistModel`, registered in `assist.ASSIST_MODELS` |
| `src/launchsim/config.py` | `LinearMotorConfig` (replacing the placeholder for that key), the structure-file model, the offload case's structure switch |
| `src/launchsim/offload.py`, `sim.py` | the factory wrapper of section 5.5 (or the fixed point) |
| `src/launchsim/results_io.py`, `summary.py`, `compare.py`, `metrics_planar.py` | structural rows in the offload block, metrics keys, assumptions; the decomposition already takes a dry-mass difference |
| `configs/structures/` (new) | coefficients and mass breakdown, sourced or assumed |
| `docs/physics.md` | sections for the structural model, the linear motor, braking and the air column; the assumptions; the test-to-equation map |

CLAUDE.md's layout lists the new modules at SP7's close.

## 6. Inventory of the code this phase touches

The code, and the documents whose numbers SP7 builds on.

Checked at commit cfd9059 on 2026-10-04 by the SP1 close-out (every `def`, `class` and
constant line below found by grep at that commit; the working tree then held only
document, site and `plots.py` edits). SP2 runs before SP7 in the planned order and edits
some of these files; the session before SP7 re-checks every line.

**Documents (the record SP7 builds on)**

| Where | What |
|---|---|
| README.md, "What can eat the gain" | the axial-load row (21.5 MN, 2.8 times liftoff thrust; hydrostatic about 2.8 times liftoff), the interface-hardware row (1 kg on stage 1 costs about 0.13 kg of payload in the screening; 0.18 kg in 2-D), the silo-air and carriage-braking rows, and the "Simulation updates" below the table |
| README.md, "Roadmap" | Phase 3's items and its "Done when" (track, ramp-energy, release-mapping, energy-balance and cable tests) |
| TODO.md, backlog and "Future items" | B-004 (structural mass and interface hardware) and B-005 (linear motor), re-targeted to SP7 by D-SP1-18; B-007 (air column, friction, modelled braking, release at a target speed), still "later" when this file was written; B-006, B-008, B-009 stay later |
| docs/findings/RQ1-fuel-offload-2d.md | "Structural penalty rows and break-even" (284-317): the four rows, erosion 4.5-5.1 t/t, zero at about 8.5 t extrapolated, screening level at about 5.5 t; "Depth and g-level" (319-408): sweep 2 and the reading that a lower felt g pays off only through a lighter structure; "Max-Q and loads" (613-638); "Limits" (693-710) |
| docs/findings/RQ3-silo-screening-2d.md | "Caveats", no structural penalty (82-91): 184 kg of P* per tonne, break-even about 8.1 t; "Loads" (494-517); the 22 t sled and the vented-shaft bias |
| docs/physics.md | "Propellant offload at fixed payload" (1986), "Cross-vehicle decomposition" (3220), "Assist energy identity" (4513), "Silo model (constant_accel, vertical) and every reported quantity" (4568), "Assumptions" (5750; the offload penalty line at 5963), "SP1 research notes" (6082), "Test-to-equation map" (6163) |
| configs/vehicles/generic_f9_class_2d.yaml | stage-1 dry 22.2 t, propellant 410.9 t (287.4 LOX + 123.5 RP-1), reference area 10.52 m^2 (3.66 m body); calibrated, never edited |

**Assist package: `src/launchsim/assist/` (the drive models that exist)**

| Symbol | File and line | Note |
|---|---|---|
| `ASSIST_MODELS`, `build_assist` | `__init__.py` 27, 36 | registry keyed by the config's `model`; a new drive is registered here |
| `TrackGeometry`, `AssistForces`, `AssistModel`, `AssistBuilder`, `normal_load_N` | `base.py` 36, 69, 89, 175, 192 | the seam: `state_rate` returns sddot, drive force, normal force, interface force, dissipated power and extra-state rates; `extra_state_names` for a drum or cable state; `push_time_estimate` is "an estimate for a force-limited drive" |
| `NoAssist` | `none.py` 17 | the pad |
| `ConstantAccelAssist` | `constant_accel.py` 31 | prescribed a; F_drive = M (a + g_eff sin phi) - (1 - f_imp) T; F_int = m_v (a + g_eff sin phi) - T; assumptions list "infinite jerk at push start and release" and "shaft vented (no air column), no friction" |
| `StraightTrack`, `VERTICAL` | `track.py` 18, 13 | straight track only; curved arcs are the Phase 3 remainder |

**Config: `src/launchsim/config.py`**

| Symbol | Line | Note |
|---|---|---|
| `PlannedModel`, `PLANNED_MODELS` | 78, 79 | `linear_motor`, `cable_winch`; refused as "planned for Phase 3" (tests/test_config.py 219-220, 283) |
| `StageConfig` | 434 | `dry_mass_t`, `propellant_mass_t` |
| `TrackConfig` | 584 | `angle_deg` 90 only ("a Phase 3 feature") |
| `NoAssistConfig`, `ConstantAccelConfig`, `PlannedAssistConfig`, `AssistConfig` | 607, 613, 708, 721 | `shaft: Literal["vented"]`; `_dump_one_push_key` is the model for leaving unset keys out of a dump |
| `OFFLOAD_STAGE1_INDEX`, `OFFLOAD_DRY_MASS_KEY` | 1542, 1547 | |
| `OffloadCaseConfig` | 1619 | `stage1_dry_mass_added_t` 1637; refused with `paired_pad` (1654) |
| `ResolvedOffloadCase` | 2412 | |
| `offload_overrides`, `offload_case_start`, `offload_solved_run` | 2658, 2708, 2734 | where a penalty enters the vehicle dict |
| `resolve_experiment` | 2816 | |

**Solver, pipeline and reporting**

| Symbol | File and line | Note |
|---|---|---|
| `OffloadProblem` (`vehicle_at`, `problem_at`), `planar_problem_factory`, `solve_offload` | `offload.py` 151, 256, 472 | the factory seam of section 5.5 |
| `with_offload`, `with_stage_propellant`, `offload_split_kg`, `Stage`, `Vehicle` | `vehicle.py` 653, 600, 613, 162, 480 | |
| `check_resolved`, `offload_penalty_assumption`, `offload_problem_factory`, `solve_resolved_offload`, `offload_run_result` | `sim.py` 932, 1690, 1708, 1717, 1728 | |
| `_offload_assumptions`, `planar_offload` | `results_io.py` 1291, 1687 | penalty rows in the post-pass |
| `OFFLOAD_CAVEATS`, `offload_caveats`, `offload_section` | `summary.py` 1500, 1553, 1897 | the summary block and its caveats |
| `cross_vehicle_decomposition` | `compare.py` 1534 | carries `xv_dry_mass_delta_kg` |
| `g_eff_track`, `TrackParams`, `rhs_track` | `dynamics.py` 114, 372, 438 | the track equation the linear motor and air column feed |
| `track_params`, `fly_track` | `phases/prelude.py` 737, 774 | the push to the track exit |
| `ev_track_end`, `ev_drive_limit` | `phases/engine.py` 674, 688 | release at s = L; a target-speed release needs its own event |
| `TRACK_COLUMNS`, `track_metrics`, `track_flags` | `metrics.py` 60, 441, 525 | |
| `PUSH_SETTING_METRICS`, `planar_track_metrics` | `metrics_planar.py` 933, 963 | |

**Tests to keep green and to copy from**

- `tests/test_silo.py` (1,223 lines): the straight-track closed forms, loads, felt g.
- `tests/test_assist_energy.py`: the assist energy identity, hot starts included.
- `tests/test_offload.py` (slow tier from 725) and `tests/test_offload_pipeline.py`.
- `tests/test_config.py` (planned models refused), `tests/test_config_planar.py`
  (`PLANAR_EXPERIMENTS`: a new experiment file is classified there).
- `tests/test_golden_1d.py`, the planar digest pin and the planar output capture.

## 7. Steps

Proposed, to confirm in Plan mode (step 0). Each step runs the loop of
SESSION_PROTOCOL.md section 4: implementer; adversarial reviewers (a physics or numerics
skeptic on every code step, a CLAUDE.md compliance auditor on every step, an honesty
auditor on S0, S6 and S7); up to two fix rounds; independent gate; commit; tracker commit;
push. Standing gate on every code step: fast suite green, ruff clean, 1-D golden
byte-identical, the planar digest pin and output capture unchanged, no shipped experiment
or vehicle file changed. The full suite after S3, S4 and S5 and before the close.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| 0 | Plan mode: entry criteria; inventory re-check; open KI and B items owned by SP7; the questions of section 10 to the user; the detailed design saved under docs/phases/inputs/ | this file, TODO.md | fast suite | User approves the plan | [ ] | |
| S0 | Sources: the structural coefficients, the stage-1 mass breakdown, the linear-motor parameter rule; a dated source note under docs/phases/inputs/ | docs/phases/inputs/ | none | Every number sourced or marked assumed; honesty review | [ ] | |
| S1 | Structural sizing core (pure): hydrostatic pressure, hoop, axial and buckling thickness, domes, load-entry structure, interface hardware | `structure.py` | `tests/test_structure.py` (new): the closed forms of section 5.9 | All listed tests | [ ] | |
| S2 | Load cases and envelope from a run's records; the increment; the structure file and its config model; the sizing-only sensitivity ranking | `structure.py`, `config.py`, `configs/structures/` | zero inside the envelope; monotone; the pad gets zero; the file validates with every number sourced or assumed | All listed tests; vehicle files untouched; digests unchanged | [ ] | |
| S3 | Coupling into the offload solve and the payload search; reporting (summary rows, metrics keys, assumptions) | `offload.py`, `sim.py`, `results_io.py`, `summary.py` | the constant-2 t cross-check against the +2 t row (slow); monotonicity of m_res in x with dm(x); without the switch, outputs unchanged | All listed tests; full suite | [ ] | |
| S4 | `linear_motor`: config, model, force rise time, carriage mass, release at a target speed; physics.md in the same change | `assist/linear_motor.py`, `assist/__init__.py`, `config.py`, `phases/` (target-speed event), `docs/physics.md` | the closed forms of section 5.7; limits honoured; energy identity < 1e-6 relative; refusals | All listed tests; full suite | [ ] | |
| S5 | Modelled braking and the sealed-shaft air column (if taken in step 0) | `assist/`, `dynamics.py` or `phases/prelude.py`, `docs/physics.md` | braking and adiabatic closed forms; energy identity with the piston work | All listed tests; full suite | [ ] | |
| S6 | Experiment file(s) and the pre-registration note (expected readings, the band, the cross-checks), committed before any run | `experiments/`, docs/phases/inputs/ | `tests/test_config_planar.py` lists the new file | Resolves; committed; clean tree | [ ] | |
| S7 | Runs from the clean commit; findings (RQ1 updated or a new note linked from it; Q6); README results, findings index, physics.md research notes | results/ (summaries), docs/findings/ | full suite | No `bug_suspect`; verification within tolerance; honesty review | [ ] | |
| C | Close SP7: exit-criteria gate; full suite; demo; trackers; CLAUDE.md layout and status; public face; SP3's file fact-checked; handoff and prompt; memory; cold-read check; push | docs/, site/, TODO.md, CLAUDE.md, README.md, memory | full suite; site build | Independent gate; final commit; Pages green | [ ] | |

## 8. Exit criteria

Draft; SP7's Plan mode fixes the tolerances marked "proposed".

1. Validation first: every test of section 5.9 for the pieces taken in step 0 passes, and
   each piece's test commit precedes the first experiment commit that uses it (git log).
2. The structure file(s) validate with every coefficient sourced or `assumed: true`; the
   calibrated vehicle files and the shipped experiment files are byte-identical to SP7's
   start commit.
3. Nothing validated moved: 1-D golden, planar digest pin and output capture pass; the pad
   and silo_cold P* within 0.002 kg; SP1's headline offload with the structural model off
   reproduces 41,262.9 kg within about 3.8 kg (proposed; SP1's reproduction tolerance).
4. **The headline offload re-solved with a modelled structural mass**, from a
   pre-registered experiment run from a clean commit: the central value and its
   uncertainty band, dm at each end, the full-load-sizing bound, the penalty rows beside
   them; each solve verified (independent payload search within
   `checks.search_final_flag_rel` x P_ref, or flagged), its decomposition closing, no
   `bug_suspect`.
5. The fixed-exit-speed stroke series and the linear-motor case(s) of section 5.8 are
   solved and reported with their felt g, dm, electricity, peak power and facility length.
6. **The findings note updated** (docs/findings/RQ1-fuel-offload-2d.md with a dated
   section that keeps the earlier record, or a new note linked from it), passing the
   honesty review: the modelled number with its band and caveats beside it, plainly
   stated if the structure cancels most of the offload; README results and the findings
   index updated.
7. `docs/physics.md` has the structural model, the linear motor (and braking and the air
   column if taken), their assumptions and test map entries.
8. Full suite green; ruff clean; no new dependency, or each justified in one line and
   logged.
9. Demo recorded under docs/demos/SP7/.
10. Close-out done: the public face refreshed (landing page, deck and PDF, gallery, manual
    with the new settings), main pushed and Pages green; SP3's phase file fact-checked
    (or the phase the user chooses); handoff, prompt and memory written.

## 9. Demo script

Output goes to docs/demos/SP7/ (text captures, a short README with the commit). Names are
proposals; the session fixes them.

    uv run pytest -q -m "not slow"
    uv run pytest -q tests/test_structure.py -k "closed_form or envelope"
    uv run python -m launchsim run experiments/<SP7 offload file>.yaml
    uv run python -m launchsim replay results/<SP7 offload file>/<timestamp> --runs pad <structural headline run> --out docs/demos/SP7/<name>.html

Look at:

- the offload block of summary.md: the stage-1 offload with the modelled structure
  (central and band), dm beside each, the penalty rows, the decomposition residual, the
  flags;
- the stroke series: offload against stroke at 76.7 m/s with the structure charged, felt
  g, electricity and facility length beside it;
- the linear-motor run: drive force against speed (force limit, then power limit), the
  interface force, the exit speed;
- the findings note's headline paragraph and its caveats.

Save a replay page under a name that `.gitignore` does not ignore (`*_replay.html` is
ignored at any depth unless SP1 or SP2 added `!docs/demos/**`); check with `git status`.

## 10. Risks and open questions

**Questions SP7's Plan mode puts to the user** (recommendation first; give the ambitious
option fairly with its cost)

| # | Question | Recommendation | Why |
|---|---|---|---|
| Q1 | Structural model fidelity | B, first-order station sizing (section 5.3) | Testable closed forms and sourceable coefficients; A adds little to the penalty rows; C (FEM) needs your approval and its inputs are not public |
| Q2 | Size the structure for the offloaded stack actually flown, or for the full-load push | The flown stack, with the full-load sizing as a bound row | The flown stack is the least mass the offloaded vehicle needs; a vehicle that must also fly full loads needs the full-load structure, so both are shown |
| Q3 | How much spare margin does the existing stage 1 have over its pad envelope | None (the structure exactly meets the envelope), with a margin as a sensitivity | The real margins are not public; zero margin charges the most and does not favour the assist |
| Q4 | Drive scope | Linear motor and carriage mass in; modelled braking and the air column in but first to cut; the curved track and cable winch out (README Phase 3 remainder) | The first two set the felt g and exit speed that the structure depends on; braking and air move little of the answer; the ramp and cable belong to concept B. Ambitious option: take the curved track with its frictionless-arc test and the cable winch with its frequency test too, at the cost of a second session or a split phase |
| Q5 | Where the carriage load enters the vehicle | An aft ring at the stage base, with the thrust structure as the alternative row | It is the simplest load path to size; body supports fly and concentrate loads (README) |
| Q6 | Findings: update RQ1 or write a new note | A new note (for example RQ1-structural-2d.md) with a dated pointer section at the top of RQ1; RQ1's record kept | Keeps the pre-registered SP1 note intact and the new experiments with their own provenance |
| Q7 | Dynamic load factor at push start | Charge it from a stated force rise time and an assumed structural period, with the quasi-static value beside | A step load (the prescribed drive's infinite jerk) peaks at twice the static load on an undamped elastic structure; ignoring it would favour the assist |

**Risks**

| # | Risk | Resolution |
|---|---|---|
| R1 | The coefficients dominate the answer and the band is wider than the offload | Report it as the result: the model cannot decide, and which coefficient would decide it |
| R2 | A first-order model looks more certain than it is | Every element's assumptions in summary.md and the note; the penalty rows stay beside it; "first order, not a sized structure" in the caveats |
| R3 | The coupling breaks the solver's monotonicity | The solver's own `offload_nonmonotone` flag; the fixed point (option ii) as the fallback |
| R4 | New config fields change resolved dicts and break the digest pin | New fields on new models only, or left out of the dump when unset (section 5.10) |
| R5 | Linear-motor parameters chosen to flatter the assist | A selection rule stated before any run (section 5.7); no adjustment after |
| R6 | The existing envelope of the real vehicle is unknown | Q3; built from the pad run's own records; a margin sensitivity |
| R7 | Run time: a band of solves plus the stroke series plus the drive cases | Budget in Plan mode from SP1's measured times; run the commands in parallel as SP1 did |
| R8 | Scope creep toward FEM, bending or lateral loads | Out of scope (section 2); any expansion asked of the user first and logged |
| R9 | SP2 changes files this inventory names | The re-check of section 6 by the session before SP7 |
| R10 | The calibration miss (+14.3%) | The bridge case on the README-loads fork with its own structure file |

**Open design points for Plan mode (no user decision needed unless they change scope)**

- Option (i) or (ii) of section 5.5, after a monotonicity probe at a few x.
- The structure file's place and schema (section 5.4).
- Whether the stroke series is a sweep (`launchsim sweep`) or cases of the run command.
- The target-speed release: its event, and what happens to the unused stroke.
- Whether the app's form (SP2) gains the structural switch now or later (backlog).

## 11. Session log

(empty: phase not started)

## 12. Deviations from the plan

(none)

## 13. Prompt to start this phase

Draft, the previous session finalises it.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP7-structural-mass-push-load.md, CLAUDE.md, TODO.md,
> README.md, and the memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links. Then read docs/findings/RQ1-fuel-offload-2d.md ("Structural
> penalty rows and break-even", "Depth and g-level", "Max-Q and loads", "Limits") and
> docs/findings/RQ3-silo-screening-2d.md ("Caveats", "Loads").
>
> We are continuing launch-assist-sim. This session is phase SP7 (D-SP1-18): charge the
> structural mass that the 4 g full-stack push needs, with a first-order sizing model
> validated against closed forms, so that SP1's headline (41.26 t of stage-1 propellant,
> 10.04% of stage 1, before any structural mass) carries a modelled structural cost with
> an uncertainty band instead of only the assumed penalty rows; and build the drive
> realism that interacts with it: a force- and power-limited linear motor with carriage
> mass, and, if we keep them, modelled braking and the silo air column.
>
> Follow the session protocol. Run its start checklist: clean tree, HEAD's subject the
> previous phase's bookkeeping commit, its closing commit an ancestor, the fast suite
> green with the count recorded, the entry criteria of section 4, the inventory of
> section 6 re-checked against HEAD, the open KI and B items owned by SP7 listed (B-004,
> B-005, and B-007 if it is re-targeted). Then work in Plan mode (step 0): put the
> questions of section 10 to me (Q1 model fidelity, Q2 sizing basis, Q3 existing margin,
> Q4 drive scope, Q5 where the load enters, Q6 the findings note, Q7 the dynamic load
> factor), each with your recommendation first and the trade-off in one line, and give
> the ambitious option fairly with its cost. Structural FEM is a scope expansion: do not
> plan it without my approval. Show me the detailed design, the step table with gates and
> the exit criteria, and wait for my approval before writing code. After approval, log the
> decisions as D-SP7-nn in TODO.md, save the design under docs/phases/inputs/, and make
> the start commit ("Start SP7: status in progress").
>
> Every structural coefficient is sourced or marked assumed, in a structure file, never in
> a calibrated vehicle file. Every new physics piece passes its closed-form test before an
> experiment uses it, with docs/physics.md updated in the same change. No validated number
> may move: the 1-D golden tier, the planar digest pin, the planar output capture, the pad
> and silo_cold payload capacities, and SP1's headline with the structural model off. The
> experiment file and its expected readings are committed before any run, and the runs
> start from a clean commit. Never choose a drive or structural parameter to make the
> assist look better. Keep SP1's penalty rows beside the modelled number, and report
> plainly if the modelled structure cancels most of the offload.
>
> Run every step through the loop (implementer, adversarial reviewers, up to two fix
> rounds, an independent gate, one commit per gate, the tracker commit at once, push and a
> green Pages deployment). At the end, run the end checklist: the exit-criteria gate, the
> full suite, the demo under docs/demos/SP7/, the trackers, CLAUDE.md, README, the public
> face, the close-out questions (which phase runs next: SP3 in the planned order), the
> fact-check of the next phase's file, the handoff and prompt, the memory, the cold-read
> check, the closing commit and the push.
