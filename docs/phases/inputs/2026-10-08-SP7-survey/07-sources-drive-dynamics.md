<!-- Record of SP7 step 0: read-only survey 07-sources-drive-dynamics (sources for the drive, carriage, braking, air column and dynamics), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# SP7 step 0 survey 07: sources for the drive, carriage, braking, air column and structural-dynamics parameters (HEAD 22c62e9, 2026-10-07)

Summary. I opened and text-extracted about two dozen documents. I checked every closed form below against direct numerical integration in a scratch script.

**What primary sources give:**
- **NASA Marshall maglev goal (Jacobs 2000):** a 55 t vehicle at 2 g to 183 m/s. The carrier is assumed to weigh half the vehicle, final power is force x exit speed, and system efficiency is assumed at 50%.
- **MagLifter (Mankins 1994):** at most 3 g, 600 mph, an assumed 80% efficiency, and a 0.5-1.0 mile carrier decelerator.
- **Linear-motor efficiency (Kaye and Masada 2004):** an LSM is 98% efficient at its own terminals but 62-87% at the converter output; an LIM is 70-77%.
- **Saturn V first longitudinal mode at lift-off load:** 3.75 Hz, from the full-scale test (NASA CR-1540).
- **Structural damping:** SP-8055 caps it at 1% of critical; the Saturn V measured about 0.5%.
- **Falcon payload envelope (Falcon User's Guide, 2025):** axial +6.0 / -2.0 g for payloads over 1,800 kg; payload axial mode above 25 Hz.

**What no source gives:** EMALS numbers reach me only through secondary sources (Sandia 2015, trade press, and Wikipedia citing Doyle 1995, which is paywalled). Nothing I found gives a catapult force rise time, a Falcon 9 stack axial frequency, or a braking deceleration for a large carriage. These must be `assumed: true`.

**Four results matter for the design:**
- **(a) A power limit cannot lower the structural load.** At the headline's fixed stroke and exit speed (100 m, 76.7 m/s), any power limit below F_max x v_exit forces a higher peak force and felt g. A constant-force linear motor (ratio 1) gives exactly the constant_accel push's 4.0 g0; ratio 0.5 gives 5.8 g0. Only a longer stroke lowers the load at fixed (L, v_exit).
- **(b) A force ramp is cheap and helps a lot.**
  - A ramp of 0.5-1.0 s costs only +0.2% to +0.9% of F_max at the same exit speed. It cuts the dynamic load factor from 2 (a step) to about 1.0-1.2 for a 3-10 Hz stack.
  - The factor applies to the 3 g0 increment over the 1 g0 static preload, so a step peaks at 7 g0, not 8.
  - Damping of 0.5-3% only moves the step factor to 1.98-1.91.
- **(c) The 3.7 m bore is a piston.** Around a 3.66 m body, the annulus is 2.2% of the bore. At Mach 0.225 the Kantrowitz limit needs at least 37.8%. Without dedicated vents of roughly the bore area, a shaft sealed at the bottom pulls 0.86-1.09 MN at exit, which is the README's p_atm x A bound.
- **(d) Release is a second load step.** At the stroke end the push unloads from about 4 g0 compression. The brief's section 5.2 does not mention this.

## 1. Method, access and what "read" means

**How each fact was obtained:**
- "read, text": I extracted the source's text with `pdftotext` from the copy WebFetch saved.
- "read, summary": I read it through a WebFetch page summary.
- "snippet": I saw the number only in a search-result summary and could not open the page (HTTP 403/402 or a paywall). These numbers are low confidence; S0 should re-check them before use.
- "(computed)": I derived the number myself.
- "(inferred)": a reading I did not see stated in any source.

**Could not access:**
- Papers behind paywalls: Doyle et al. 1995 (IEEE Trans. Magn. 31(1) 528-533), Bushway 2001 (IEEE Trans. Magn. 37(1) 52-54), and Schultz et al. 2001 (IEEE Trans. Appl. Supercond. 11, 1749-1752). Schultz is the source of the README's "4% of liftoff weight".
- Sites that returned 403: Design News 1995, GlobalSecurity, NAVAIR and FlightGlobal.
- Textbooks: Biggs 1964 and Chopra.
- The MIT EMALS thesis (Johnson 2005, 22.9 MB): abstract only.
- NTRS 19690013567 and 20090034160, both over 10 MB.

**Scratch files.** Nothing in the repository was edited. These are in C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/07-sources-drive-dynamics/:
- `checks.py` with `checks_output.txt`
- `checks_ramp.py` with `checks_ramp_output.txt`
- the extracted source texts (`*.txt`)

**REPORT.md was not written.** The harness refuses report files from this agent. This message is the report.

## 2. What the code holds today (facts at HEAD 22c62e9)

- **`linear_motor` is planned and refused at load:** `PlannedModel` and `PLANNED_MODELS` (src/launchsim/config.py:78-79); `PlannedAssistConfig` (config.py:713).
- **`ConstantAccelConfig` (config.py:618) fields:**
  - `carriage_mass_t`, default 0.0 (642)
  - `brake_decel_g`, > 0 with no default (643)
  - `drive_efficiency`, default 1.0, in (0, 1] (644)
  - `exhaust_impingement_fraction` (645)
  - `shaft: Literal["vented"]` (646)
- **`ConstantAccelAssist`:**
  - Forces: F_drive = M (a + g_eff sin phi) - (1 - f_imp) T and F_int = m_v (a + g_eff sin phi) - T (src/launchsim/assist/constant_accel.py:52-53).
  - Assumption strings: "shaft vented (no air column), no friction" (222) and "infinite jerk at push start and release" (224).
- **Shipped silo settings, all assumed:**
  - a 5 g0 carriage brake and drive efficiency 0.5 (experiments/silo_offload_2d.yaml:80-81, 89-91);
  - a 22 t sled case commented "MagLifter ~4% of liftoff" (experiments/silo_screening_2d.yaml:86).
- **Vehicle masses (configs/vehicles/generic_f9_class_2d.yaml):**
  - stage 1 dry 22.2 t and propellant 410.9 t (46-47);
  - stage 2 dry 4.0 t and propellant 107.5 t (58-59);
  - fairing 1.7 t (69).
  - That is 546.3 t before payload. Adding silo_cold's P* of 27.55 t gives 573.9 t, which matches 22.49 MN / (3.996 g0) from the brief (computed).
- **README first-order rows:** peak power, silo air (p_atm x bore, 1.1 MN at 3.7 m) and braking at 5 g (about 60 m) (README.md:245-247). Prior-art rows for MagLev/MagLifter, EMALS and Holloman (358-360). EMALS scale (208). Push energy 2.249 GJ (257).
- **Brief:** the dynamic-load-factor statements (docs/phases/SP7-structural-mass-push-load.md:334-341, the ramp formula at 337-338), the interface-force expression (420) and the linear-motor closed forms (424-433).

## 3. Linear-motor launchers

### 3.1 EMALS (General Atomics / US Navy)

**Facts, strongest source first:**
- **Motor type.** GA calls the fielded system the most powerful linear induction motor in the world. Source: GA-EMS datasheet "EMALS", EMS-EMALS Rev C 0818, NAVAIR Public Release 2017-816, https://www.ga.com/images/products/defense/emals/EMALS_DS_1018E.pdf (read, text). The datasheet gives no numbers. The 1995 design was a linear synchronous motor fed by disk alternators through a cycloconverter (Sandia, below; Doyle 1995 via secondaries). Confidence high that the fielded system is an LIM.
- **Energy storage and power.** Each disk-alternator rotor stores 121 MJ (33.6 kWh) of extractable energy at 6,400 rpm. The pulse lasts about 2 s, recharge takes 45 s, and peak alternator output is 81.6 MW into a matched load.
  - Source: D. Bender, "Flywheels", Sandia report SAND2015-3976, May 2015, section 6.3.1, p. 21, https://www.sandia.gov/app/uploads/sites/163/2021/09/SAND2015-3976.pdf (read, text; it cites GlobalSecurity).
  - Confidence medium: secondary, but institutional.
- **Motor rating and braking method.** The launch motor is rated about 100,000 hp (74.6 MW, computed). The motor current reverses to brake the shuttle; there is no water brake.
  - Source: E. Tegler, "Electromagnetic Aircraft Launch System (EMALS) Launches the E-2D Advanced Hawkeye", Defense Media Network, 2011-10-10, https://www.defensemedianetwork.com/stories/big-wave-surfing/ (read, summary).
  - Confidence medium-low (trade press).
- **Stroke, mass, speed, cycle, energy.** Stroke 300 ft (91 m). A 100,000 lb (45 t) aircraft reaches 130 kn (67 m/s). The cycle is 45 s, and power conversion efficiency was "planned" at 90% (EDN, Schweber 2002). Launch energy is 122 MJ, with 121 MJ per alternator (Doyle et al. 1995). Both are quoted by Wikipedia, https://en.wikipedia.org/wiki/Electromagnetic_Aircraft_Launch_System (read, summary). Confidence medium: secondary, primaries not read.
- **Prototype and ranges.** Track 103 m, with a half-scale prototype of about 50 m. Aircraft 4.5-45 t, launch speeds 100-370 km/h (28-103 m/s), launch time 2-3 s. Source: S. Kariya, "A high-tech launch system for carriers", IEEE Spectrum, 2004-01-01, https://spectrum.ieee.org/a-hightech-launchsystem-for-carriers (read, summary). Confidence medium.
- **Control.** Closed-loop control with Hall-effect sensors holds a constant tow force. Source: S. Davis, Electronic Design, 2017-08-10, https://www.electronicdesign.com/technologies/power/article/21199416/ (read, summary). Confidence medium.
- **Maximum design thrust:** 290,000 lbf (1.29 MN, computed). Source: Design News 1995, "Linear motor outperforms steam-piston catapults" (snippet; 403). Confidence low.
- **Braking distance:**
  - the carriage stops in 20 ft (6.1 m) by reversing the windings (globalspec.com article; snippet, 403);
  - a university paper reportedly specifies a 100 m stroke, 100 m/s and 10 m of braking (scholarcommons.sc.edu; snippet, 403).
  - Confidence low.

**Inferred:**
- **Mean push.** 45 t to 67 m/s over 91 m is a mean 2.52 g0, 1.11 MN of mean net force and 101 MJ of kinetic energy (computed). This fits a 1.29 MN maximum.
- **Power ratio.** P/(F_max v_exit) is about 0.56-0.94: 74.6-81.6 MW against 1.29 MN x 67-103 m/s (86-133 MW). The numbers come from different sources, so confidence is low. They suggest the drive is not sized for full force at its top end speed.
- **Shuttle braking.** 6.1 m from about 70 m/s is about 41 g0, and 10 m from 100 m/s is about 51 g0 (computed). That is a light shuttle of unknown mass, stopped electromagnetically. It says nothing about a carriage of tens to hundreds of tonnes.
- **Force rise time:** not published anywhere I could open (section 5).

### 3.2 NASA Marshall Magnetic Launch Assist (Jacobs 2000)

Source: W. A. Jacobs, "Magnetic Launch Assist - NASA's Vision for the Future", NASA MSFC, May 2000 (10th EML Symposium), NTRS 20000103883, https://ntrs.nasa.gov/api/citations/20000103883/downloads/20000103883.pdf, pp. 1-2 (read, text). The companion preprint NTRS 20000068443 (read, summary) gives the same goal as 600 ft/s in under 10 s. Confidence high, as stated goals and assumptions.

- **Goal.** A 55,000 kg vehicle accelerated at 2 g to 183 m/s. The carrier is assumed to weigh half the vehicle, for 82,000 kg in total.
- **Sizing.** Force = m_total x a = 1.6e6 N, over 9.34 s. Final power is force x 183 m/s = 2.93e5 kW (293 MW), and kinetic energy 1.4e9 J. At an assumed 50% system efficiency the energy is about 3,000 MJ. The sizing is constant force with P_max = F_max v_exit, a ratio of 1.
- **Sub-scale demonstrators:**
  - Foster-Miller LSM: 13 m track, 6 kg cradle, 97 km/h; 6.5 m of drive coils, then 6.5 m of aluminium bars for braking.
  - LLNL Halbach array: 20 kg cradle, 43 km/h.
  - PRT LIM: 15 m track (7.5 m propulsion, 7.5 m braking), 58 kg carrier, 45 km/h.
- **The 20% claim.** The paper says an initial velocity can save over 20% of onboard fuel. That sentence gives no speed (p. 1).

### 3.3 MagLifter (Mankins 1994)

Source: J. C. Mankins, "The MagLifter: An Advanced Concept Using Electromagnetic Propulsion in Reducing the Cost of Space Launch", AIAA 94-2726, 30th Joint Propulsion Conference, June 1994, https://ewh.ieee.org/r4/se_michigan/Spring2011/AIAA-1994-2726-303%20mankins%20maglifter%20electromagnetic%20launch.pdf, pp. 5-7 and 12-13 (read, text; OCR quality fair). Confidence high, as concept statements.

- **Guideway.** 3-4 miles in total: a 2.5 mile accelerator and a 0.5-1.0 mile carrier decelerator, in a tunnel up a mountain, optionally helium-filled near the end. LSM propulsion.
- **Performance.** At most 3 g, exiting at about 600 mph at 45-55 deg and 10,000 ft. The launch sequence accelerates for about 30 s, releases at about 650 mph and exits at 600 mph.
- **Energy and power.** About 200 GJ over about 60 s for a rocket SSTO. The maglev system (guideway, carrier, LSM) is assumed about 80% efficient, which leaves about 40 GJ of heat. Power is on the order of 10 GW for a large system.
- **Carrier mass:** not stated. The README's 4% (README.md:358) comes from Schultz et al. 2001, which I did not read.
- **Decelerator, inferred:** (268 m/s)^2 / (2 x 0.5-1.0 mi) is 2.3-4.6 g0 of carrier braking (computed).

### 3.4 Holloman maglev sled

- **The record run.** On 2016-03-04 the 846th Test Squadron ran a 2,000 lb (907 kg) sled to 633 mph (283 m/s) on a 2,100 ft (640 m) track. Superconducting magnets cooled to 4 K levitated it, and rockets propelled it. Source: Air & Space Forces Magazine, "Breaking the maglev record again", 2016, https://www.airandspaceforces.com/breaking-the-maglev-record-again/ (read, summary). It agrees with the ACC/Nellis release "633 mph, nothing to Mach" (https://www.acc.af.mil/News/Article-Display/Article/721996/; snippet).
- **Relevance.** Because it is rocket-propelled, it says nothing about linear-motor force, power or efficiency.
- **Braking.** The track stops sleds by water braking, with scoops into a water trough. Source: Terrazas et al., ASME J. Fluids Eng. preprint, arXiv 2411.18939, 2024 (read, text). It gives no deceleration levels. Confidence medium.

### 3.5 LIM against LSM efficiency, 50-300 m/s

Source: R. J. Kaye and E. Masada, "Comparison of Linear Synchronous and Induction Motors", Sandia National Laboratories and Tokyo University of Science for the FTA, 2004, FTA-DC-26-7002.2004.01, SAND2004-2734P, https://rosap.ntl.bts.gov/view/dot/16110, pp. 7, 10-11 and 19-20 (read, text). Confidence high.

- **Transrapid TR07 LSM at 200 km/h, maximum thrust:**
  - 98% at the motor terminals under the vehicle;
  - 85% at the terminals of a 300 m block section;
  - 62% at the output of the variable-voltage, variable-frequency converter.
  - The best converter-output figure is 87%, at 480 km/h. A longer block section lowers efficiency.
- **Locally commutated LSM** (an inverter per coil): about 95% at the converter.
- **COL-200 LIM:** 70% at its 144 km/h average speed and 77% at about 225 km/h maximum, measured at the power-pickup rail. This is comparable to TR07, with a lower power factor.
- **Speed limit for LIMs.** The authors find an LSM the only suitable choice well above 200 km/h for vehicles that carry the LIM primary on board. That reasoning is about on-board LIM weight, not a ground-primary launcher (inferred).

**Inferred for SP7.** End to end, the best published LSM figure at the converter output is 0.62-0.95, and energy storage and its conversion (flywheel or capacitor) lower it further. Jacobs' 0.5 and MagLifter's 0.8 bracket this. SP1's 0.5 (experiments/silo_offload_2d.yaml:81) is at the low end: conservative for energy and power, and neutral for the vehicle.

## 4. How studies size F_max and P_max

**Facts:**
- Jacobs 2000 sizes for constant force at the target acceleration, with power = force x exit speed, so P_max / (F_max v_exit) = 1 (section 3.2).
- EMALS uses closed-loop control to hold a constant tow force (Davis 2017). Its stated peak powers (74.6-81.6 MW) against its maximum thrust suggest a ratio below 1 at the highest end speeds (section 3.1, low confidence).
- MagLifter states a 3 g ceiling and a power on the order of 10 GW, but no rule linking them (section 3.3).
- No source I read gives a general rule for setting P_max below F_max v_exit.

**Computed (checks.py section 2).** Assumptions: vertical track, cold start, massless carriage, constant mass, g = g0, L = 100 m, v_exit = 76.707 m/s. The drive is F = min(F_max, P_max / v) with P_max = r F_max v_exit. F_max is solved so that the drive reaches v_exit exactly at s = L.

| r = P_max / (F_max v_exit) | F_max (573.9 t) | peak felt g0 | P_max | corner speed | push time |
|---|---|---|---|---|---|
| 1.0 | 22.51 MN | 4.000 | 1.727 GW | 76.7 m/s | 2.607 s |
| 0.9 | 22.76 MN | 4.044 | 1.571 GW | 69.0 m/s | 2.589 s |
| 0.8 | 23.61 MN | 4.194 | 1.449 GW | 61.4 m/s | 2.534 s |
| 0.7 | 25.26 MN | 4.488 | 1.356 GW | 53.7 m/s | 2.445 s |
| 0.6 | 28.04 MN | 4.983 | 1.291 GW | 46.0 m/s | 2.333 s |
| 0.5 | 32.51 MN | 5.776 | 1.247 GW | 38.4 m/s | 2.215 s |

The felt-g column is the same for the 531.0 t headline stack, because F scales with M. I also checked the brief's power-limited vertical closed forms (SP7 file 429-430) against direct integration at F = 4 g0 M and r = 0.6: they agree to better than 1e-9 m and 1e-9 s.

**Reading (inferred):**
- At fixed (L, v_exit), lowering P_max to r = 0.5 saves at most 28% of peak power, but raises peak felt load from 4.0 to 5.8 g0.
- 5.8 g0 is above the 5.2 g0 MECO envelope. By the brief's own section 5.2, it would then start to size stage 2 and the interstage as well.
- So the only drive with no structural cost beyond constant_accel is the constant-force one (r = 1). For a cold start with a massless carriage, it reproduces constant_accel's 4.0 g0 exactly.

**Recommendation:** a sizing rule stated before any run, with r = 1 at the headline and r < 1 only as a labelled sensitivity. A carriage of mass m_c at fixed F_max lowers the vehicle's felt g, but needs a larger F_max for the same v_exit, so the carriage mass must also be stated (the brief's interface-force expression, SP7 file 420).

## 5. Force rise time and jerk limits

**Facts:**
- **No catapult rise time is published.** No source I could open gives a force rise time for EMALS or any other electromagnetic catapult. The trade press (Davis 2017; Kariya 2004) describes continuous closed-loop control over a 2-3 s stroke. The US Navy training sheet describes the steam catapult's water brake and holdback release without timings (Information Sheet 3.8 "Catapults", https://man.fas.org/dod-101/navy/docs/swos/eng/62n-308.htm; read, summary).
- **Crew limits have no jerk requirement.**
  - NASA-STD-3001 Vol. 2 Rev D sets sustained translational acceleration limits [V2 6064] for exposures over 0.5 s, and handles shorter transients through injury-risk and dynamic-response criteria [V2 6069] and [V2 6070].
  - I found no onset-rate (jerk) requirement in its technical brief: NASA OCHMO-TB-024 Rev D, "Occupant Protection", https://www.nasa.gov/sites/default/files/atoms/files/acceleration_technical_brief_ochmo.pdf (read, text). Confidence medium.
  - A historical "600 g/s" figure appeared in one search snippet with no traceable source; I did not use it.
- **Payloads have no jerk limit either.** The Falcon User's Guide gives quasi-static limits and sine environments only (section 7.3).

**Computed (checks_ramp.py).** The drive force ramps linearly from the 1 g0 static support (M g) to F_max over t_r, then holds constant. F_max is set to hold v_exit = 76.707 m/s at 100 m (573.9 t, g = g0).

| t_r | F_max | felt g0 after the ramp | change against the step |
|---|---|---|---|
| 0 | 22.512 MN | 4.0000 | 0 |
| 0.10 s | 22.514 MN | 4.0004 | +0.01% |
| 0.25 s | 22.525 MN | 4.0023 | +0.06% |
| 0.50 s | 22.564 MN | 4.0093 | +0.23% |
| 1.00 s | 22.724 MN | 4.0377 | +0.94% |

**Recommendation.** With no source, the rise time is a design choice marked `assumed: true` and fixed by a rule before any run.
- One rule: t_r >= 3.2 T at the low end of the frequency band (section 7). That keeps the undamped ramp envelope at or below 1.10.
- It gives t_r = 1.06 s at 3 Hz or 0.64 s at 5 Hz, and costs under 1% of F_max.
- Keep the step (t_r = 0) as the bound row; it reproduces constant_accel's own assumption (constant_accel.py:224).

## 6. Carriage braking

**Facts:**
- **EMALS:** the motor current reverses to brake the shuttle, with no water brake (Tegler 2011; read). The 20 ft distance is a snippet only.
- **Steam catapults:** spear-tipped pistons ram water-filled cylinders (US Navy training sheet; read). The "about 5 ft" stop is a snippet only; if true, it is about 170 g0 from 72 m/s (computed, low confidence).
- **NASA MSFC sub-scale tracks:** eddy-current braking on aluminium bars, over the same length as the drive section (Jacobs 2000, p. 2; read).
- **MagLifter:** a 0.5-1.0 mile carrier decelerator (Mankins 1994; read), which implies 2.3-4.6 g0 (computed).
- **Launch coasters:**
  - An Accelerator Coaster catch car reportedly needs 20 m to stop from 100 km/h, about 2 g0 (computed). That sentence is uncited on Wikipedia, https://en.wikipedia.org/wiki/Accelerator_Coaster (read, summary). Confidence low.
  - Coaster brakes are permanent-magnet eddy-current fin brakes whose force can be tuned to the car's speed (US patents found by search; not read in full).
  - Passenger comfort limits coaster braking, which does not apply to an uncrewed carriage.
- **Holloman sleds:** water braking (section 3.4); no deceleration value found.

**Computed.** Braking from 76.71 m/s at a constant deceleration:

| Deceleration | Distance | Time |
|---|---|---|
| 1 g0 | 300 m | 7.8 s |
| 2 g0 | 150 m | 3.9 s |
| 3 g0 | 100 m | 2.6 s |
| 5 g0 | 60.0 m | 1.56 s |
| 10 g0 | 30 m | 0.78 s |
| 20 g0 | 15 m | 0.39 s |

**Recommendation.**
- No source gives a braking deceleration for a carriage of tens to hundreds of tonnes. Keep 5 g0 as `assumed: true` (central), with a range of 2 g0 (MagLifter-like and coaster-like) to 20 g0 (EMALS-shuttle-like, electromagnetic).
- Braking moves only facility length and the failed-ignition geometry (brief section 5.7), so reporting the range is cheap.
- Eddy-current brake force depends on speed (inferred from the patents' adjustable-force claims). A modelled braking phase that goes beyond the constant-deceleration closed form needs a stated force-speed law, which no source here supplies.

## 7. Structural dynamics: axial frequency, damping, the existing load envelope

### 7.1 First longitudinal frequency at lift-off

**Facts:**
- **Saturn V, 100% propellant (lift-off), full-scale dynamic test.**
  - First longitudinal mode 3.75 Hz, second 4.46 Hz. The 1/10-scale replica gave 3.09 and 4.02 Hz in full-scale terms.
  - The first mode comes from the liquid propellant coupling with the structure (S-IC tank bulging). The first pitch mode is 1.11 Hz.
  - Source: P. J. Grimes, L. D. McTigue, G. F. Riley and D. I. Tilden (The Boeing Company), "Advancements in structural dynamic technology resulting from Saturn V programs, Volume II", NASA CR-1540, June 1970, section 3.5.2, p. 26, Figures 3-7 and 3-9, https://ntrs.nasa.gov/api/citations/19700022502/downloads/19700022502.pdf (read, OCR text, PDF page 42).
  - Confidence medium-high. The figure labels come from OCR and I did not view the figure image. The text's ratios to the 1/10 scale (23% and 11% higher) match the label pairs (21% and 11%). The pitch pairs match their stated 22% and 14% exactly.
- **Larsen 2008 pogo history.** Source: C. E. Larsen (NASA NESC), "NASA Experience with Pogo in Human Spaceflight Vehicles", RTO-MP-AVT-152, 2008, pp. 5-6 to 5-8 and 5-18, NTRS 20080018689 (read, text). Confidence high.
  - Saturn V AS-502 had pogo at 5 Hz from 105 to 140 s of the S-IC burn: the first longitudinal frequency rose as mass fell until it met the F-1 engines' roughly 5.5 Hz.
  - Atlas had about 12 Hz pogo just before booster cutoff, and 5-6 Hz ullage-coupled pogo for the first 20 s after lift-off.
  - Gemini-Titan II had 10.9-11.2 Hz at T+123 to T+126 s.
  - The Space Shuttle's pogo analysis assumed 0.5% structural damping as the worst case.
- **SP-8055.** Pogo has occurred at 5-60 Hz. It tracks the first structural mode, which rises as propellant is used. Source: S. Rubin (The Aerospace Corporation), "Prevention of Coupled Structure-Propulsion Instability (Pogo)", NASA SP-8055, October 1970, section 1, p. 1, https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19710016604.pdf (read, text). Confidence high.
- **Falcon 9: no public stack axial frequency found.** Search found only a student finite-element model's bending modes (4.29 and 11.56 Hz, propellant state not given; Aamer et al. 2023, arXiv 2309.13032; read, summary). That is not an axial value and not authoritative.

**Inferred:**
- Atlas's 5-6 Hz pogo just after lift-off implies a first longitudinal mode near 5-6 Hz with full tanks, since SP-8055 says pogo tracks that mode.
- Falcon 9 is much shorter than Saturn V (about 70 m against 110 m) but similarly dominated by liquid mass. Its first axial mode at lift-off is plausibly 4-8 Hz; I have no source for its wall stiffness.

**Proposed values (`assumed: true`):** central 5 Hz (T = 0.20 s), low 3 Hz, high 10 Hz. The low end is the conservative one: a lower frequency gives a larger load factor at a given rise time.

### 7.2 Structural damping

**Facts:**
- **SP-8055 cap.** A mode's damping should not exceed 1% of critical without strong experimental evidence. Source: NASA SP-8055, section 4.1.1, pp. 21-22 (read, text). Confidence high.
- **Saturn V measurements.** Equivalent viscous damping ranged from 0.4% in the S-II tanks to 3% in the spacecraft, and 70% in the engine servoactuators. Modal damping measured in the full-scale test was near 0.5%, against an estimated 2%. Source: NASA CR-1540, section 4.5.6, p. 95 and section 5.1.3, p. 122 (read, OCR text). Confidence high.
- **Shuttle pogo analysis:** 0.5% worst case (Larsen 2008, p. 5-18).

**Proposed:** central 1%, low 0.5%, high 3%. Damping barely moves the load factor (section 8). Using zero damping (a closed form) is conservative and overstates a step by at most 4.5% compared with 1-3% damping.

### 7.3 The Falcon payload envelope (bounds the existing load case)

Source: SpaceX, "Falcon User's Guide", Version 8 (March 2025), file dated 2025-05-09, https://www.spacex.com/assets/media/falcon-users-guide-2025-05-09.pdf, section 5.3, pp. 32-34, Figure 5-1 and Table 5-3 (read, text). Confidence high.

- **Recommended payload frequencies:** primary lateral above 10 Hz, primary axial above 25 Hz, secondary structure above 35 Hz.
- **Quasi-static limit load factors.** These are limit levels with no qualification factor; positive axial means compression.

| Payload mass | Axial g | Lateral g with it |
|---|---|---|
| over 1,800 kg | +6.0 | +/-0.5 |
| over 1,800 kg | +3.5 | +/-2.0 |
| over 1,800 kg | -1.5 (tension) | +/-2.0 |
| over 1,800 kg | -2.0 (tension) | +/-0.5 |
| 1,000-1,800 kg | +8.5 / -4.0 | |
| under 1,000 kg | +11.0 / -6.0 | |

- **Axial acceleration and throttling.** Thrust and drag drive axial acceleration, and either stage may throttle to stay within steady-state acceleration limits.
- **Axial sine environment** at the top of the payload adapter, payloads over 1,800 kg: 0.5 g at 5 Hz, 0.8 g at 20-35 Hz, 0.6-0.9 g at 35-100 Hz.

**Inferred:**
- These are payload-interface limits, not stage-1 tank allowables. The model's MECO peak of 5.195 g0 (RQ1) sits under the +6.0 g limit.
- The tension corners (-1.5 to -2.0 g) show that the existing envelope already includes an unloading transient, plausibly at MECO and staging. This bears on the release step (section 8.3).

## 8. Dynamic load factor (DLF) closed forms

### 8.1 Forms and sources

- **Closed forms** (undamped single-degree-of-freedom oscillator, period T):
  - a step gives DLF = 2;
  - a linear ramp to F0 over t_r, then constant, gives DLF = 1 + |sin(pi t_r / T)| / (pi t_r / T), exactly 1 at t_r / T = 1, 2, 3, ...;
  - a damped step gives DLF = 1 + exp(-zeta pi / sqrt(1 - zeta^2)).
- **Textbook sources, not read:** J. M. Biggs, "Introduction to Structural Dynamics", McGraw-Hill, 1964 (the chapter 2 load-factor charts), and A. K. Chopra, "Dynamics of Structures" (the section on a step force with finite rise time). Search results give Chopra's limiting cases: twice static for t_r < T/4, exactly 1 at integer t_r / T.
- **Read:** MIT course 1.581 (Structural Dynamics), Homework 3 solutions, Fall 2001, problem 1, https://stuff.mit.edu/afs/athena/course/1/1.581/www/hw/Hw3_Sol.pdf (read, text). It derives the undamped ramp response and gets DLF_max = 1.18 for t_r = 1.25 T; the closed form gives 1.1801.

### 8.2 Numerical verification (checks.py section 1; DOP853, rtol 1e-11)

| t_r / T | closed form (undamped) | numeric, zeta = 0 | 0.5% | 1% | 2% | 3% |
|---|---|---|---|---|---|---|
| 0 (step) | 2.0000 | 2.0000 | 1.9844 | 1.9691 | 1.9391 | 1.9100 |
| 0.25 | 1.9003 | 1.9003 | 1.8863 | 1.8725 | 1.8455 | 1.8193 |
| 0.5 | 1.6366 | 1.6366 | 1.6267 | 1.6169 | 1.5979 | 1.5795 |
| 1.0 | 1.0000 | 1.0000 | 1.0049 | 1.0095 | 1.0182 | 1.0261 |
| 1.25 | 1.1801 | 1.1801 | 1.1746 | 1.1694 | 1.1598 | 1.1513 |
| 1.5 | 1.2122 | 1.2122 | 1.2057 | 1.1995 | 1.1879 | 1.1773 |
| 2.5 | 1.1273 | 1.1273 | 1.1216 | 1.1162 | 1.1067 | 1.0985 |
| 5.0 | 1.0000 | 1.0000 | 1.0046 | 1.0084 | 1.0144 | 1.0185 |

- The damped step values match 1 + exp(-zeta pi / sqrt(1 - zeta^2)) to four decimals.
- Damping removes the exact zeros at integer t_r / T, leaving factors of 1.005-1.026 there. A test with damping on should not expect DLF = 1 at an integer ratio.
- The envelope 1 + 1/(pi t_r / T) is at most 1.10 for t_r / T >= 3.18, and at most 1.05 for t_r / T >= 6.37.

### 8.3 Three modelling points for Plan mode (inferred; no source read states them)

- **The factor multiplies the increment, not the total.** The stack rests on the carriage at 1 g0 before the push, so a step to the 4.0 g0 push peaks at 1 + 2 x 3 = 7 g0 equivalent, not 8 g0 (linear superposition). The brief's section 5.2 (SP7 file 334-341) says a step peaks at twice the static load. Applied to the whole 4 g0, that overstates the step case by 1 g0.
- **Release is a second step.**
  - At the stroke end the drive force drops from about 4 g0 compression to zero; a cold start then coasts at 0 g0 felt. If the drop is fast and undamped, the first mode swings to a tension of similar size.
  - constant_accel already lists infinite jerk at release (constant_accel.py:224), and the Falcon envelope's tension corners are only -1.5 to -2.0 g (section 7.3).
  - Ramping the force down before s = L costs exit speed, just as the ramp-up does.
  - Whether SP7 charges this case is a Plan-mode decision.
- **Compare like with like.** The pad's lift-off case uses the vehicle's 2 s thrust ramp (an SP1 setting), much longer than T, so its factor is about 1. A push charged with a dynamic factor should be compared with a quasi-static envelope only if that envelope includes its own dynamic factors. Otherwise, state the comparison as conservative.

## 9. The silo air column

### 9.1 Facts

- **Snug-tube limit (Kantrowitz).**
  - If the tube is smaller than the isentropic minimum, not all the air can pass around the pod, and the pod acts as a piston that pressurises the air ahead. The minimum bypass area occurs when the bypass flow is sonic.
  - Source: J. C. Chin, J. S. Gray, S. M. Jones and J. J. Berton (NASA Glenn), "Open-Source Conceptual Sizing Models for the Hyperloop Passenger Pod", AIAA paper, 2015, Eq. (1), pp. 6-7, NTRS 20150000699 (read, text). Confidence high.
- **Piston effect in elevator shafts.**
  - The pressure difference follows from flow through the free area around the car (shaft area minus car area), with a flow coefficient. Tests gave 0.94 for one car in a two-car shaft and 0.83 for two cars side by side, the stand-in for a single-car shaft.
  - Source: J. H. Klote and G. T. Tamura, "Elevator Piston Effect and the Smoke Problem", Fire Safety Journal 11 (1986) 227-233, p. 229; NRC Canada reprint at https://www.nist.gov/document/3kloter8700428elevatorpistonpdf (read, text; the equations were garbled in extraction). Confidence medium.
- **Silo practice.** Confidence low-medium: secondary sources.
  - Titan II was hot-launched from its silo, with a flame deflector at the base and two exhaust ducts up to the surface (themilitarystandard.com, "Titan II Missile System Silo Complex"; snippet).
  - Peacekeeper (MX) was cold-launched: a gas generator ejected it from its canister to about 150-300 ft before first-stage ignition, because the silo had no room for hot exhaust to escape (FAS and CSIS pages; snippets).
  - Long March 11 can be cold-launched from a launch tube (Wikipedia citing Gunter's Space Page; read, summary).
  - The pattern: a deliberately sealed tube works as a gas-driven piston, and a hot-launch silo is vented by ducts.
- **Adiabatic trapped column.** p = p0 (V0 / V)^gamma, and the work on the piston is W = (p0 V0 - p V) / (gamma - 1). This is a standard thermodynamics closed form (for example Anderson, "Modern Compressible Flow"; not read here). A hand-computed test value is enough; no further source is needed.

### 9.2 Computed for the SP7 geometry (checks.py section 4)

- **The 3.7 m bore is choked.** Exit Mach is 76.71 / 340.3 = 0.2254, so the Kantrowitz minimum is A_bypass / A_tube = 0.3779. A 3.66 m body would need a bore of at least 4.64 m for the annulus to carry the flow even at sonic speed. The 3.7 m bore leaves an annulus of 0.231 m^2, 2.15% of the 10.752 m^2 bore: fully choked, a piston.
- **What "vented" needs.** An incompressible orifice estimate gives a vent area of about 11.4-13.0 m^2 (1.06-1.21 x the bore, for C = 0.94-0.83) to keep the pressure difference at or below 3.6 kPa, the exit dynamic pressure. That means vent ducts of the order of the bore area at both ends of the column (inferred).
- **Sealed bottom, open mouth.** Quasi-static adiabatic expansion of the gap below the carriage over a 100 m stroke:

| Initial gap | p_end / p0 | Net force at exit | Net work against the column |
|---|---|---|---|
| 1 m | 0.0016 | 1.088 MN | 107 MJ |
| 5 m | 0.014 | 1.074 MN | 99 MJ |
| 10 m | 0.035 | 1.052 MN | 92 MJ |
| 20 m | 0.081 | 1.001 MN | 81 MJ |
| 50 m | 0.215 | 0.855 MN | 61 MJ |

  - The force bound p_atm x A_bore = 1.089 MN matches README.md:246.
  - The 99 MJ at a 5 m gap is about 4.4% of the 2.249 GJ push energy (README.md:257).
- **Acoustic scales.**
  - The compression ahead of an impulsively started piston is rho a u = 32.0 kPa. The rarefaction behind a piston at 76.7 m/s gives p/p0 = 0.724: dp = 28.0 kPa, or 0.30 MN on the bore.
  - These wave values are not reached (inferred). The push ramps over 2.6 s, against a 0.29 s acoustic transit of 100 m, so the quasi-static column is the right first model.
  - The 1,317 kg of air above needs 38.7 kN to accelerate at 3 g0.

### 9.3 Recommendation

- **Define the vented default** by its vent area: about the bore area at the bottom and along the shaft.
- **Define the sealed shaft** by its initial gap volume, a design choice marked `assumed: true`. Below about 10 m, the force barely depends on it.
- **Say where the piston acts.** Whether the piston acts on the carriage or on the vehicle decides whether it reaches the interface force (brief section 5.7). If the carriage is the sealing piston (inferred), the suction acts on the carriage. The drive must then supply up to 1.09 MN more, and the interface force is unchanged for a massless carriage. Under a force-limited drive it lowers the exit speed.

## 10. Discrepancies with the repository's record (facts, for S0's honesty review)

- **README.md:358 speed and time.** The row says Magnetic Launch Assist was a track about 1.5 miles long reaching 600 mph in 9.5 s.
  - MSFC's public statements do say 600 mph: search results give exactly that wording for an MSFC fact sheet (not read), and the 1999 MSFC release (ScienceDaily 1999-10-08; read, summary) says "up to 600 mph".
  - The MSFC paper I read (Jacobs 2000) states 183 m/s, which is 600 ft/s and not 600 mph, in 9.34 s at 2 g for a 55 t vehicle. The NTRS preprint 20000068443 also says 600 ft/s.
  - 600 mph in 9.5 s would be 2.9 g0 over 0.79 mi (computed). The row may combine two different statements.
- **README.md:231 "over 20%".** The row says the MagLev papers claimed "over 20%" savings for an assist of about 270-280 m/s (600 mph). In Jacobs 2000 that sentence gives no speed, and the paper's own goal is 183 m/s. MagLifter's 600 mph comes from a different study (Mankins 1994).
- **README.md:359 motor type.** The row describes EMALS as "a 91 m linear motor", and the 1995 design was an LSM. GA describes the fielded system as a linear induction motor (datasheet Rev C 0818). The row is not wrong, but the motor type matters for the efficiency range (section 3.5).

## 11. Recommendations for S0, S4 and S5 (not facts)

1. **Treat drive and structure parameters as design choices.** F_max, P_max, t_r, carriage mass, braking deceleration, the structural period, damping and the shaft vent or gap are all `assumed: true`. Choose each by a rule stated before any run. The sources bound these values; none sets them.
2. **Linear-motor rule.** Use r = P_max / (F_max v_exit) = 1 at the headline (Jacobs' rule; it reproduces constant_accel's 4.0 g0). Run r < 1 only as a sensitivity: it raises felt g and dm (section 4). Solve F_max for the stated (L, v_exit) and carriage mass.
3. **Rise time.** Ramp from the static 1 g0 support to F_max over t_r >= 3.2 T_low, with the step as the bound row. Charge the factor on the increment only (section 8.3). Plan mode decides whether to charge the release step.
4. **Efficiency.** Define P_max as mechanical, so eta scales only grid energy and power. Central 0.5 (SP1's value and Jacobs' assumption), range 0.4-0.85, plus the CLAUDE.md +/-10% sensitivity.
5. **Structural period and damping.** Central 5 Hz, conservative low 3 Hz (Saturn V measured 3.75 Hz on a far larger stack), high 10 Hz. Damping 1% (range 0.5-3%), or zero for the closed form.
6. **Braking.** Constant deceleration (closed form), 5 g0 central, 2-20 g0 range. Its speed dependence is not sourced.
7. **Air column.** Define the vented case by its vent area and the sealed case by its stated initial gap. Put the Kantrowitz check in the assumptions.

## 12. Parameter table

In the last column: "read" = I read the source's text or page summary this session; "snippet" = search summary only; "computed" = derived here from read inputs; "no" = not read.

| Parameter | Central | Low | High | Source or assumed | Confidence | Read myself |
|---|---|---|---|---|---|---|
| EMALS motor type (fielded) | LIM | - | - | GA datasheet EMS-EMALS Rev C 0818 | high | read (text) |
| EMALS stroke | 91 m | 91 m | 103 m | EDN 2002 via Wikipedia; Kariya 2004 (103 m) | medium | read (summary; secondary) |
| EMALS end speed at 45 t | 67 m/s | 28 m/s | 103 m/s | Wikipedia (EDN 2002); Kariya 2004 (100-370 km/h) | medium | read (summary) |
| EMALS max thrust | 1.29 MN | - | - | Design News 1995 | low | snippet |
| EMALS launch energy | 122 MJ | - | - | Doyle 1995 via Wikipedia; README:245 | medium | read (secondary) |
| EMALS peak power | 81.6 MW | 74.6 MW | - | Sandia SAND2015-3976 p. 21; Tegler 2011 (100,000 hp) | medium | read |
| EMALS P/(F_max v_exit) | 0.75 (midpoint) | 0.56 | 0.94 | (computed) from the rows above | low | computed |
| EMALS efficiency | 0.7 | 0.7 | 0.9 | Kaman 70% (FlightGlobal snippet); "planned 90%" (EDN via Wikipedia) | low | snippet / secondary |
| EMALS shuttle braking | current reversal | 6.1 m | 10 m | Tegler 2011 (method, read); 20 ft and 10 m from snippets | low (distance) | read (method) |
| MSFC goal: vehicle, acceleration, exit | 55 t, 2 g, 183 m/s | - | - | Jacobs 2000, NTRS 20000103883, pp. 1-2 | high | read (text) |
| MSFC carrier / vehicle mass | 0.5 | - | - | Jacobs 2000 p. 1 | high (as assumption) | read (text) |
| MSFC force, power, time | 1.6 MN, 293 MW, 9.34 s | - | - | Jacobs 2000 p. 2 (power = F x v_exit) | high | read (text) |
| MSFC system efficiency | 0.5 | - | - | Jacobs 2000 p. 2 (assumed there) | high (as assumption) | read (text) |
| MagLifter acceleration, exit | <= 3 g, 268 m/s | - | - | Mankins 1994, AIAA 94-2726, pp. 12-13 | high | read (text) |
| MagLifter efficiency | 0.8 | - | - | Mankins 1994 p. 7 (assumed there) | high (as assumption) | read (text) |
| MagLifter decelerator | 0.75 mi | 0.5 mi | 1.0 mi | Mankins 1994 p. 5; implies 2.3-4.6 g0 (computed) | high | read (text) |
| MagLifter levitation modules / liftoff weight | 4% | - | - | Schultz et al. 2001 (README:358) | unverified | no |
| Holloman sled | 907 kg, 283 m/s, 640 m | - | - | Air & Space Forces 2016; rocket-propelled | medium | read (summary) |
| LSM efficiency, motor terminals | 0.98 | - | - | Kaye & Masada 2004 p. 10 (TR07, 200 km/h) | high | read (text) |
| LSM efficiency, converter output | 0.62 | 0.62 | 0.95 | Kaye & Masada 2004 pp. 10-11 (87% at 480 km/h; locally commutated LSM 95%) | high | read (text) |
| LIM efficiency (COL-200) | 0.70 | 0.70 | 0.77 | Kaye & Masada 2004 p. 7 | high | read (text) |
| Drive efficiency for SP7 (eta) | 0.5 | 0.4 | 0.85 | assumed: true (bracketed by Jacobs 0.5, MagLifter 0.8, LSM 0.62-0.95) | assumed | - |
| P_max / (F_max v_exit) for SP7 | 1.0 | 0.5 | 1.0 | assumed: true (Jacobs' rule); r = 0.5 raises felt g to 5.8 g0 (computed) | assumed | computed |
| Force rise time t_r | 0.64-1.06 s (3.2 T_low) | 0 (step) | 2 s | assumed: true; no source found | assumed | - |
| Crew jerk limit | none in the NASA-STD-3001 V2 Rev D brief | - | - | OCHMO-TB-024 Rev D | medium | read (text) |
| Carriage mass / vehicle | 0 | 0 | 0.5 | assumed: true; anchors 4% (Schultz, unread) and 50% (Jacobs) | assumed | partly |
| Carriage braking deceleration | 5 g0 | 2 g0 | 20 g0 | assumed: true (MagLifter 2.3-4.6 g0 computed; coaster ~2 g0 uncited; EMALS shuttle ~41-51 g0 from snippets) | assumed | partly |
| First axial frequency at lift-off (F9 class) | 5 Hz | 3 Hz | 10 Hz | assumed: true; anchors Saturn V 3.75 Hz (CR-1540 Fig. 3-9) and Atlas 5-6 Hz (Larsen 2008, inferred) | assumed (anchors medium-high) | read (anchors) |
| Saturn V first / second longitudinal, 100% propellant | 3.75 / 4.46 Hz | - | - | NASA CR-1540 (1970) p. 26, Fig. 3-9 | medium-high | read (OCR text) |
| Pogo frequency range | 5-60 Hz | - | - | NASA SP-8055 p. 1 | high | read (text) |
| Structural damping ratio | 1% | 0.5% | 3% | SP-8055 pp. 21-22 (<= 1%); CR-1540 pp. 95, 122 (0.4-3%, measured ~0.5%); Larsen p. 5-18 (0.5%) | high | read (text) |
| Step DLF (undamped / 1% / 3%) | 2.000 / 1.969 / 1.910 | - | - | closed form, verified numerically | high | computed |
| Ramp DLF | 1 + abs(sin x)/x, x = pi t_r/T | - | - | Biggs 1964 / Chopra (not read); MIT 1.581 HW3 2001 (read); verified numerically | high | read (MIT) + computed |
| Falcon payload axial limit (>1,800 kg) | +6.0 g | -2.0 g | +6.0 g | Falcon User's Guide v8 (2025), Table 5-3, p. 33 | high | read (text) |
| Falcon payload frequency, axial / lateral | > 25 Hz / > 10 Hz | - | - | Falcon User's Guide v8, section 5.3, p. 32 | high | read (text) |
| Kantrowitz bypass fraction at exit | 0.378 | - | - | Chin et al. 2015 Eq. 1, at Mach 0.2254 (computed) | high | read (text) + computed |
| Minimum unchoked bore for a 3.66 m body | 4.64 m | - | - | (computed) | high | computed |
| Vent area for <= 3.6 kPa | 1.1-1.2 x bore | - | - | Klote & Tamura 1986 flow coefficients 0.83-0.94 (incompressible estimate) | medium | read (text) + computed |
| Sealed-shaft force at exit (3.7 m bore) | 1.07 MN (5 m gap) | 0.86 MN (50 m gap) | 1.09 MN (p_atm x A) | adiabatic closed form (computed); README:246 bound | high (as computed) | computed |
| Sealed-shaft initial gap | 5 m | 1 m | 20 m | assumed: true (design choice) | assumed | - |
