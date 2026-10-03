# 10. Validation

[Manual contents](README.md) · Previous: [9. Reading results](09-reading-results.md) · Next: [11. Troubleshooting](11-troubleshooting.md)

The project's rule is **validation first**: no physics feature is used in an experiment until
an analytic test of it passes. The expected values in those tests are closed forms written
in the tests themselves, not numbers copied from the code's own output. This chapter lists
the required tests, separates validation from calibration, and shows how to run the suite.

## The analytic tests CLAUDE.md requires

| Required test (CLAUDE.md) | Where | Status |
|---|---|---|
| Rocket equation in vacuum without gravity: dv = c ln(m0/mf), relative error < 1e-6 | `tests/test_rocket_equation.py` | passes |
| Vertical burn at constant g, no drag: v_f = v_0 + c ln(m0/mf) - g t_b, for several v_0 | `tests/test_vertical_burn.py` | passes |
| Elliptical orbit (e about 0.3) for 10 revolutions: energy and angular momentum drift < 1e-8 relative; period 2 pi sqrt(a^3/mu) | `tests/test_orbit.py` | passes |
| Vacuum coast: apex v_0^2/(2g) at constant g; energy conserved with mu/r^2 | `tests/test_coast.py`, `tests/test_orbit.py` | passes |
| Straight track, constant force: v = sqrt(2 a L), t = v/a | `tests/test_silo.py` | passes |
| Frictionless, unpowered circular-arc ramp: v and the normal load against the closed form | | not yet: comes with curved tracks, README roadmap Phase 3 (backlog B-006) |
| Release mapping: an equatorial east pad launch starts at 465.1 m/s inertial | `tests/test_release_planar.py`, `tests/test_config_planar.py` | passes |
| Loss budget closes to < 0.01 m/s over a full ascent | `tests/test_loss_identity_2d.py` (2-D), `tests/test_loss_identity.py` (1-D) | passes |
| Assist energy, including hot starts with changing mass, relative error < 1e-6 | `tests/test_assist_energy.py` | passes |
| Cable: small-oscillation frequency sqrt(k/m) | | not yet: comes with the cable winch, Phase 3 (B-006) |
| Convergence: tightening tolerances 10x changes payload and margins by < 0.1% | `tests/test_convergence.py`, `tests/test_convergence_2d.py` | passes |

The "passes" column was checked for this manual by running those files, slow tests
included, at commit `e4f36ee`.

The orbit test uses an ellipse on purpose: in polar coordinates a circular orbit is an
equilibrium and would pass even with a wrong equation of motion.

Every test the list requires for Phases 0 to 2 passes (README). The two missing ones belong
to models that do not exist yet; nothing in the shipped experiments uses a curved track or a
cable.

Other closed-form checks in the suite include the gravity turn against the Culler-Fried
solution (`test_gravity_turn.py`), linear-tangent steering (`test_ltg.py`), the
ignition-loss forms (`test_ignition_loss.py`), a toy payload search (`test_payload_search.py`),
max-Q from a constant-thrust rise (`test_max_q.py`), the planar model reducing exactly to the
1-D one (`test_planar_reductions.py`), the failed-ignition coast (`test_failed_ignition.py`),
the rocket-equation closure (`test_closure.py`), the atmosphere against the `ambiance`
reference (`test_atmosphere.py`) and the offload solver's toy cases (`test_offload.py`).
[docs/physics.md](../physics.md) ends with a test-to-equation map.

## Records and goldens (regression, not validation)

Some tests pin results rather than check physics, so that a change that moves a recorded
number is noticed:

- `tests/test_golden_1d.py`: every 1-D output, captured from the CLI.
- `tests/test_calibration.py`: the calibration record (labelled calibration).
- `tests/test_silo_screening_record.py`: the recorded payload capacities of the 2-D screening.
- `tests/test_readme_numbers.py`: the README's hand numbers (calibration-flavoured).
- The planar pins under `tests/data/`: digests of the shipped planar experiments.

## Calibration is not validation

**Validation** asks whether the code solves its equations correctly; the tests above answer
it. **Calibration** asks whether the model vehicle behaves like the real one. They are kept
apart and labelled.

The calibration compares the gate vehicle with SpaceX's published 22,800 kg to low Earth
orbit (expendable). SpaceX does not publish the reference orbit, so one was fixed before the
run and never moved: 200 km circular, 28.5 degrees, due east. Nothing was tuned toward the
published number. The result ([CAL-f9-leo-2d](../findings/CAL-f9-leo-2d.md)):

- the gate vehicle (mass set C) reaches 26,054.4 kg, +14.3%: 974.4 kg above the +/-10% band,
  a miss high;
- set A (the README masses) reaches 24,700.0 kg (+8.33%), set B 25,416.3 kg (+11.48%);
- every numerical check passes, and the cause of the miss is not established: throttling,
  reserves and residuals would lower the payload, better guidance could raise it;
- the user accepted the miss as documented on 2026-09-30, and every 2-D finding inherits it.

`experiments/calibration_f9_2d.yaml` carries `label: calibration`. Its run records whether
`configs/` and `experiments/` were committed (the pre-registration state); an uncommitted
input prints `PREREGISTRATION DIRTY ... not a valid calibration record` and the summary says
so.

Published claims are benchmarks to explain, never targets to tune toward. NASA's "over 20%"
onboard-fuel saving for a 270-280 m/s assist is one: the README explains why a fixed vehicle
cannot reach it on the rocket equation alone. A hobby-scale comparison with RocketPy
(apogee within +/-5%) is planned for README roadmap Phase 6.

## Running the tests

```text
uv run pytest -q -m "not slow"     # fast tier
uv run pytest -q                   # everything, including tests slower than 5 s
uv run pytest -q tests/test_orbit.py
uv run pytest -q -k elliptical
```

Tests slower than 5 s carry `@pytest.mark.slow`. The suite treats every warning as an error
(`filterwarnings = ["error"]` in `pyproject.toml`), so a numerical warning fails a test.

The project's working rules: run the fast tests before calling any change done, and the
full suite after any change to the physics core (CLAUDE.md).

Next: [11. Troubleshooting](11-troubleshooting.md)
