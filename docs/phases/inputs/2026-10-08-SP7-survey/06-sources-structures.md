<!-- Record of SP7 step 0: read-only survey 06-sources-structures (sources for the structural coefficients and the stage-1 breakdown), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# SP7 step 0, survey 06: sources for the structural coefficients and the stage-1 mass breakdown

Summary. SpaceX's own user guides (Rev 2 from 2015, and the March 2025 edition) give the construction facts the sizing model needs: aluminium-lithium tank walls, friction-stir welded, a **monocoque LOX tank on top and a skin-and-stringer RP-1 tank below**, an insulated common dome between them, a LOX transfer tube through the RP-1 tank, "aluminum lithium skin; aluminum domes", an interstage of carbon fibre over aluminium honeycomb, a 3.66 m diameter, and a structural factor of safety of 1.4 (the guide contrasts it with "the traditional 1.25" for uncrewed flight). A 2009 SpaceX release adds tank proof at 1.1 × MEOP and ultimate at 1.4 × MEOP. No public source gives Falcon 9 tank pressures, dome shape or tank lengths. The only stage-1 component masses I found are the Merlin 1D (470 kg) and the v1.1 landing legs (under 2,100 kg), and I only saw both quoted. The octaweb, interstage, tanks, aft skirt and grid fins have no published mass, so the breakdown can only be bracketed with generic mass-estimating relations. Material allowables come from NASA papers that quote the Alcan 2195-T8R78 datasheet (E 11.0 Msi, nu 0.33, rho 0.098 lb/in^3, Fty 73 ksi, Ftu 81 ksi). MSFC reports friction-stir welds at 70% of parent strength. MMPDS and the MSFC 2195 allowables handbook are not public. I read the SP-8007 knockdown formula, its internal-pressure increment curve (digitized below; it levels off near Delta gamma = 0.25) and its stiffened-cylinder factors in both editions: 0.75 in 1968 and 0.65 in 2020. The sources I could open give no single new SBKF number. NASA-STD-5001B gives ultimate 1.4, yield 1.0 or 1.25, and proof 1.05 for propellant tanks. It requires buckling to be checked at ultimate loads and relieving pressure to be taken at its minimum, unfactored, and it does not cover knockdown or load-uncertainty factors. For stiffened-shell weight, Gerard (1966) gives a closed-form law Sigma = C (N/(E d))^n, with n = 3/5 to 7/11 for ring-and-stringer cylinders. With the 0.65 knockdown and the 1.4 factor applied, it falls inside the range of NASA's optimized 2195 orthogrid designs (Lovejoy et al. 2010). NASA's conceptual-sizing deck (Wu 2024) uses the same SP-8007 approach and documents non-optimum factors (NOF) of 1.0 to 1.9. Thrust-structure relations give 0.20 to 0.36 kg per kN of thrust; a Saturn S-II thrust cone works out to 0.65 kg/kN. I found **no published estimate of the structural mass that a ground push costs a rocket**: the MagLifter-era studies either leave structure out on purpose or count a saving (a smaller landing gear). Section 9 is an illustration with assumed pressures, not a result. In it the increment sits mostly in two places: the RP-1 barrel, about 0.7 to 1.3 t before non-optimum factors, and the load-entry or thrust structure, about 3.6 t if a thrust-structure relation is scaled to 22.5 MN. The LOX barrel adds between about 0 and 1.6 t, depending on weld efficiency and on what sizes the existing wall. The load-entry coefficient is both the least sourced and the largest.

## 0. Scope, method and conventions

- Read first: docs/phases/SP7-structural-mass-push-load.md at HEAD 22c62e9 (clean tree): sections 2 and 5 (5.2 load case 315-347; 5.3 options and source list 349-367; the source places at 357-363), 6, and 10 (questions Q1-Q7 at 910-916).
- Repository facts used (HEAD 22c62e9):
  - configs/vehicles/generic_f9_class_2d.yaml:46 (stage-1 dry mass 22.2 t), :47 (410.9 t = 287.4 t LOX + 123.5 t RP-1), :50 (914.1 kN vacuum per engine, 8,227 kN total), :84 (A_ref 10.52 m^2, 3.66 m body).
  - Envelope values: liftoff 1.36 g0, MECO 5.195 g0, max-Q 37.19 kPa (SP7 file 323-326).
  - README.md:241 and :256 (break-even rows), :358 (MagLifter "~4% of liftoff weight"), :487-489 (MagLifter references).
- Labels used below:
  - [opened]: I downloaded or fetched the source and read the passage myself. Pages are PDF pages unless marked "printed".
  - [quoted]: I saw the number only as quoted by another document or a search summary and could not open the original.
  - (inferred): my own reasoning, not a statement in a source.
- Sections 1-8 are facts. My recommendations are only in section 10 and are labelled as such. Section 9 is arithmetic on the sources: an illustration, not a sizing result.
- The harness refused the requested write of REPORT.md ("subagents should return findings as text"), so this message is the only copy of the report. The scratch folder .../scratchpad/a0/06-sources-structures/ holds:
  - every opened PDF and its text extraction, plus rendered page images;
  - the scratch script derive.py and its output derive_out.txt.

## 1. Falcon 9 first-stage tank construction

### 1.1 Facts from SpaceX documents [opened]

| Item | Statement (paraphrase) | Source, page | Confidence |
|---|---|---|---|
| Wall alloy and welding | First-stage tank walls are aluminium-lithium alloy, friction-stir welded | Falcon 9 Launch Vehicle Payload User's Guide Rev 2, SpaceX, 21 Oct 2015, section 2.2, PDF p.10; Falcon User's Guide, SpaceX, version 8 (March 2025; file falcon-users-guide-2025-05-09.pdf), printed p.8 | high |
| Stiffening | Table 2-1: "LOX tank - monocoque; Fuel tank - skin and stringer" (same wording for stage 2) | Rev 2 Table 2-1, PDF p.11; 2025 Table 2-1, printed p.9 | high |
| Skin and domes | Table 2-1: "Aluminum lithium skin; aluminum domes" | same tables | high as stated; the dome alloy is not named |
| Bulkhead and tank order | An insulated common dome separates the LOX and RP-1 tanks. An insulated (2025: double-wall) transfer tube carries LOX through the centre of the RP-1 tank to the engine section, so LOX is above RP-1 | Rev 2 section 2.2, PDF p.10; 2025 printed p.8 | high |
| Interstage | Composite: aluminium honeycomb core with carbon-fibre face-sheet plies, fixed to the forward end of the first-stage tank | Rev 2 PDF p.11; 2025 printed p.8-9 | high |
| Diameter, height | 3.66 m for both stages; 70 m overall including both stages, interstage and fairing (75.2 m with the extended fairing, 2025) | Rev 2 and 2025 Table 2-1 | high |
| Load-sized walls | The Falcon Heavy centre core "consists of thicker tank walls" | 2025 printed p.8 | high as a fact; that F9 walls are therefore load-sized is (inferred) |
| Factors of safety | "increased structural factors of safety (1.4 versus the traditional 1.25 for flight without crew)" | Rev 2 section 1.4, PDF p.6. The 2025 edition keeps the phrase without the numbers | high |
| Tank qualification (2009) | Proof to 1.1 × MEOP; 1.4 × MEOP ultimate; over 150 pressure cycles; load cases for max-Q, MECO, ultimate loads and ground winds | SpaceX release via Business Wire, 29 Jul 2009, read in its aeroweb-fr.net republication | medium (secondary copy of a primary release) |
| Payload-level envelope | Payload design load factors reach +6 g axial with 0.5 g lateral for standard payloads, and 8.5 g for light payloads | Rev 2 section 4.3.1, Figs. 4-1 and 4-2, PDF p.20-21 | high. That this shows the upper stack is designed above the push's 4.0 g is (inferred) |

### 1.2 Facts from secondary sources

- **Alloy and temper.**
  - Light Metal Age (26 Apr 2019) says "low-density Airware 2195-T8 plate" is used "in the tank barrels and domes of the booster", attributed to Constellium [opened, via fetch summary].
  - This conflicts with SpaceX's "aluminum domes" (Table 2-1) on the domes. SpaceX's tables do not name the alloy.
  - Wikipedia's Falcon 9 Full Thrust page says "Aluminum lithium alloy skin; aluminum domes" and "2195-T8", citing the 2015 user guide and 2016 SpaceX documents [opened].
  - No source I found says 2198.
  - Confidence: medium that the barrels are 2195-T8; low on the dome alloy.
- **Lengths.**
  - Wikipedia cites Espace & Exploration No. 39 (May 2017), pp. 36-37, for a 42.6 m first stage and a 4.5 m interstage on Full Thrust [quoted]. The sentence I read does not say whether 42.6 m includes the interstage.
  - For v1.1, spaceflight101 gives 41.2 m without the interstage and a 6.5 m interstage [quoted, search summary only].
  - Confidence: medium-low.
- **Densified propellants.** LOX at 66.5 K and RP-1 at 266.5 K, which Wikipedia cites to an Elon Musk tweet of 17 Dec 2015 [quoted]. Confidence: medium.
- **Tank pressures: no public SpaceX value found.**
  - A search summary relayed a NASASpaceflight forum post: "rumors ... 35-40 psi", and "50 psia" as a design estimate. The forum refused access, so this is [quoted], low confidence and not citable.
  - A summary of space-access.org says only "a few tens of psi".
- **Dome shape and tank lengths:** not published anywhere I found.

### 1.3 Analogue pressures (basis for the assumed range) [opened unless marked]

| Vehicle | Value | Source |
|---|---|---|
| Saturn V S-IC (stiffened LOX/RP-1 stage) | LOX ullage 18-20 psia in flight (prepressurization max 18 psig); fuel tank minimum 24.2 psia in flight | Saturn V Flight Manual SA-503, MSFC-MAN-503 (NASA TM-X-72151), Nov 1968, NTRS 19750063889, section IV, printed p.4-11 and 4-12 |
| SLS-like orthogrid design study | Proof 66 psi, maximum 50 psi, ullage 30 psi (study assumptions) | Lovejoy, Hilburger, Chunchu, AIAA 2010-2778, NTRS 20100016271, PDF p.4 |
| Shuttle SLWT LH2 barrel; Ares V core LH2 barrel | Proof 38.7 psi; proof 43.4 psi | Wu, NASA LaRC deck (2024), NTRS 20240002646, PDF p.27-29 |
| Shuttle ET LOX tank | About 20-22 psig | Wikipedia "Space Shuttle external tank" [quoted; primary not checked] |

### 1.4 Propellant densities and derived column heights

| Quantity | Value | Source or derivation | Confidence |
|---|---|---|---|
| LOX density, 66.5 K, 0.1-0.5 MPa | 1,253.0-1,253.6 kg/m^3. Also 1,264.6 at 64 K, 1,246.5 at 68 K, 1,237.4 at 70 K, and 1,141.2 at 90.19 K (normal boiling point; densification gains +9.8%) | NIST Chemistry WebBook, oxygen isotherms [opened] | high (density at a given temperature) |
| RP-1 density | Measured 813.2 kg/m^3 at 2.9 C and 799.0 at 23.3 C (original sample; the ultra-low-sulfur sample is about 0.28% denser). Linear extrapolation gives 819.9 kg/m^3 at -6.6 C (slope -0.696 kg/m^3/K) and 804.8 at 15 C | Magee et al., NIST IR 6646, Feb 2007, Table 8, PDF p.41 (printed 35) [opened]. The extrapolation, 9.5 K below the lowest measurement, is mine | medium |
| Equivalent column heights (cylinders of 10.52 m^2; no domes, transfer tube or ullage) | LOX 229.4 m^3, so 21.8 m; RP-1 150.6 m^3, so 14.3 m | Derived (derive.py section 1) from generic_f9_class_2d.yaml:47 | medium-low |
| Head at the bottom of each full column | LOX: 3.64 bar at 1.36 g0, 10.70 bar at 3.996 g0. RP-1: 1.57 and 4.60 bar | Derived (derive.py section 2). At MECO's 5.195 g0 the tanks are nearly empty | medium-low |

## 2. Stage-1 dry-mass breakdown (22.2 t, Full Thrust)

No public breakdown exists in any source I could reach. What is public:

| Item | Value | Source | Confidence |
|---|---|---|---|
| Merlin 1D dry mass | 470 kg each; 9 × 470 = 4,230 kg | Wikipedia "SpaceX Merlin", citing Tom Mueller's Quora answer of 8 Jun 2015 [quoted] | low-medium; the engine version is not stated |
| Landing legs (v1.1) | Under 2,100 kg; carbon fibre and aluminium honeycomb | Light Metal Age, 26 Apr 2019 [opened, via fetch summary]. The original SpaceX 2013 page was not opened (web.archive.org blocked) | low-medium |
| Grid fins | No public mass | none found | - |
| Octaweb / thrust structure | No public mass. NASA's SpaceX blog (18 Apr 2014) says only that the octaweb "reduces the length and weight" | search summary | - |
| Interstage, tanks, aft skirt, hold-down fittings | No public mass | none found | - |
| Are legs and fins inside the 22.2 t? | Not stated; the source gives only "empty mass" | Espace & Exploration via Wikipedia [quoted] | unknown |
| A design-tool reconstruction | 27.2 t first-stage structural mass for a reusable Block 5 with legs and fins, "based on unofficial estimations". Landing gear modelled as +15% of first-stage dry mass, "reverse-engineering" Falcon 9 | Dresia et al. (DLR), arXiv:2009.01664 (2020), section II.A (PDF p.4) and Table 5 (PDF p.18) [opened] | low |

Generic mass-estimating relations, used only as cross-checks (calibration, not validation; derive.py section 7):

| Element | Relation | F9 value | Source |
|---|---|---|---|
| Tanks and insulation | M = 10.41 V^0.75 (lbm, ft^3), ±30%. The Shuttle SLWT LH2 tank came out 35% below it | LOX tank 4.03 t; RP-1 tank 2.94 t | Heineman, JSC-26098 (1994), as reproduced in Wu 2024, PDF p.24-25 [opened in Wu; Heineman itself not opened] |
| Thrust structure | 2.55e-4 kg/N (0.255 kg/kN) | 2.10 t at 8,227 kN | Akin, UMD ENAE 791 "Mass Estimating Relations" [quoted: search summary only; the UMD server refused connections] |
| Thrust structure | Linear aluminium relations, read off the chart: about 0.20-0.36 kg/kN. One non-linear relation includes a load-factor term | 1.6-3.0 t | Castellini, PhD thesis, Politecnico di Milano (2012), section 4.5.5, Fig. 48 and the M_TF equation, PDF p.83-84 (printed 65-66) [opened] |
| Interstage (lower stage) | M = k_SM k1 S (3.2808 D)^k2, with k1 7.7165, k2 0.4856, k_SM 1 (Al) or 0.7 (composite) | 0.93 t (composite) to 1.34 t (Al) for 3.66 m × 4.5 m | Castellini 2012, Table 15, PDF p.83 [opened] |

The relation-based items add up to about 14-15 t of the 22.2 t: tanks 7.0 t, engines 4.2 t, thrust structure 2.1 t, interstage 0.9-1.3 t. The remaining 7-8 t would be feed and pressurization systems, thrust vector control, avionics, wiring, aft skirt and engine section, separation hardware, and possibly recovery hardware (inferred). This gap is reported as found, not tuned away.

## 3. Material allowables

| Property | Value | Source | Confidence |
|---|---|---|---|
| 2195-T8R78 plate, room temperature | E 11.0 Msi (75.8 GPa); Fty 73.0 ksi (503 MPa); Ftu 81.0 ksi (558 MPa); rho 0.098 lb/in^3 (2,713 kg/m^3); nu 0.33; maximum plate thickness 1.8 in | Lovejoy et al. 2010, Table 1, PDF p.3, citing the Alcan 2195-T8R78 datasheet and MMPDS-04 [opened; the datasheet itself not opened]. The study uses room-temperature values throughout | medium-high |
| 2195-T8M4 (SBKF test articles) | E 11.0 Msi, nu 0.33, rho 0.098 lb/in^3; slight longitudinal/transverse stiffness difference noted | Hilburger & Lindell, NTRS 20190000441, PDF p.12 [opened]. Their ref. 8 is the MSFC "Design Allowables Handbook for Aluminum-Lithium 2195 Plates, Extrusions, Forgings, & Welds" (not public, (inferred)) | high |
| 2195 yield used by NASA for SLWT and Ares V sizing | 72 ksi (496 MPa) | Wu 2024, PDF p.27-28 [opened] | medium-high |
| 2195 friction-stir weld | Joint efficiency about 70% of parent | Bhat et al., "Friction Stir Welding Development at NASA-Marshall Space Flight Center", NTRS 20020015869 (2001), PDF p.5 (OCR text) [opened] | medium |
| 2195 fusion (VPPA) repair-weld allowable requirements | 30 ksi at room temperature; 38 ksi at LH2 temperature | Russell, AMPET 2000, NTRS 20010067248, chart slides [opened] | medium |
| Cryogenic strength gain | Strength rises at low temperature | MDPI Metals 13(4):740 (2023) [quoted: search summary; page returned 403] | low; not proposed for use |
| Typical 2195 values | Ftu 590 MPa, Fty 560 MPa | makeitfrom.com [quoted; not primary] | low |
| MMPDS allowables | Not public | - | - |
| Composite interstage properties | Not sought. The brief's first look (SP7 file 328-334) has the push below MECO's 5.2 g0 at the interstage | - | - |

## 4. Shell buckling: SP-8007 and the SBKF work

### 4.1 Unstiffened isotropic cylinders under axial compression [opened]

- **Classical stress.** sigma_cr = gamma E t / (r sqrt(3(1 - nu^2))), which is 0.605 gamma E t / r for nu = 0.3 (2020 edition, Eq. 7-8, PDF p.41, printed 23). For 2195's nu = 0.33 the constant becomes 0.612 (derived).
- **Knockdown.** gamma = 1 - 0.901 (1 - e^(-phi)), with phi = (1/16) sqrt(r/t) for r/t < 1500 (2020 Eq. 9-10, PDF p.41-42; 1968 edition Eq. 5, PDF p.15-16).
  - Both editions call it a lower bound to 1930s-1960s test data: about 200 compression tests, r/t 80-4150, L/r 0.5-5.
  - The 2020 edition adds a caution for L/r > 5 and says the curve likely bounds aerospace-quality cylinders conservatively.
- **Values** (derive.py section 3):

  | r/t | 200 | 300 | 400 | 500 | 1000 |
  |---|---|---|---|---|---|
  | gamma | 0.471 | 0.404 | 0.357 | 0.322 | 0.224 |

### 4.2 Internal pressure [opened]

- **Load with pressure.** P_press = 2 pi E t^2 (gamma / sqrt(3(1 - nu^2)) + Delta gamma) + p pi r^2 (2020 Eq. 48-49, PDF p.50-51; same form in 1968 section 4.2.5.4). The 2020 edition says the Delta gamma curve is to be used only with these equations.
- **Delta gamma curve.** Fig. 6 (1968, PDF p.25, printed 15) and Fig. 4-5 (2020, PDF p.51, printed 33) show the same curve. I read it from the rendered pages, about ±10%; it levels off near 0.25:

  | (p/E)(r/t)^2 | 0.015 | 0.02 | 0.04 | 0.06 | 0.08 | 0.1 | 0.2 | 0.4 | 0.6 | 1 | 2 | 4 | 10 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | Delta gamma | 0.023 | 0.028 | 0.046 | 0.060 | 0.075 | 0.09 | 0.13 | 0.17 | 0.20 | 0.22 | 0.245 | 0.25 | 0.25 |

- **For an F9-like wall** (derived): p = 3 bar and r/t = 400 give 0.63, so Delta gamma is about 0.20. That is nearly as large as 0.605 gamma = 0.216.
- **Analysis-based alternative** for pressurized stiffened cylinders: Delta gamma = 0.14, which the authors call "smaller in magnitude" than SP-8007 would give (Lovejoy et al. 2010, PDF p.5).

### 4.3 Stiffened (orthotropic) cylinders [opened]

- **1968 edition:** cylinders with "closely spaced, moderately large stiffeners" get a factor of 0.75 (PDF p.28).
- **2020 edition:** the same case gets **0.65**, because tests fell as low as 65% of the classical load. The 0.65 comes from TN D-5561 and the Isogrid Design Handbook (PDF p.53-54, printed 35-36; history at PDF p.34-35, printed 16-17).
- **Unstiffened orthotropic walls:** same formula, with phi = (1/29.8) sqrt(r / (D11 D22/(A11 A22))^(1/4)) (2020 Eq. 60-61; 1968 Eq. 45). Hilburger (NTRS 20120008172, PDF p.3-4) says this gives 0.68-0.52 for typical orthogrid and isogrid walls with 50 < R/t_eff < 150.
- **Isogrid Design Handbook** (NASA CR-124075, 1973, NTRS 19730011184, section 4.2, PDF p.62):
  - gamma = 0.65 "for moderate or heavy stiffening", so c0 = 0.612 gamma = 0.397.
  - Skin-buckling constant c1 = 10.2; rib-crippling constant c2 = 0.616.
  - The minimum weight is given as a chart, not a closed form.
- **Test-data ranges** behind the stiffened factors (Hilburger 2012, Table 1, PDF p.5): from 0.68-1.08 (45-degree waffle with pressure) to 0.91-0.98 (Z-stringer); lowest values 0.68-0.70.
- **SBKF (NESC assessment 07-010-E).** New analysis-based factors exist and were used on the SLS core stage (NESC web page, 23 Jan 2018; Hilburger extended abstract, NTRS 20180006178), but **no single published value** appears in what I could open. SP-8007-2020 section 4.3 (PDF p.91 onward) describes the hierarchy of factors without giving a design value.
- **What the factor is worth in mass** (Lovejoy et al. 2010, PDF p.6-8):
  - Raising the knockdown from 0.65 to 0.85 cut 2195 orthogrid area weight by 18-24%, and 2050/2219 by 4-13%.
  - Pressure relief and stabilization cut 36-41% when there is no pressure-loss load case.

## 5. Factors of safety and load factors

| Factor | Value | Source | Confidence |
|---|---|---|---|
| Ultimate design factor, metallic structure | 1.4 (prototype and protoflight) | NASA-STD-5001B with Change 3 (2022-10-24), Table 1, PDF p.18 [opened] | high |
| Yield design factor | Prototype 1.0 (plus a check against harmful yielding); protoflight 1.25 | same | high |
| Qualification test factor | Prototype 1.4; protoflight 1.2 | same | high |
| Proof factor, propellant tanks and SRM cases | 1.05 | same, footnote | high |
| Relieving pressure (FSR 19) | Use the minimum expected pressure, unfactored, with the other loads factored | section 4.2, PDF p.16 | high |
| Buckling (FSR 53-54) | Checked at ultimate loads; a load that eases buckling is used unfactored; knockdown factors from SP-8007 | section 4.5, PDF p.25 | high |
| Scope exclusions | Does not cover design-load determination, fitting factors, knockdown factors or load-uncertainty factors | section 1.2.1, PDF p.6 | high |
| SpaceX structure | 1.4, against "the traditional 1.25" for uncrewed flight | FUG Rev 2, PDF p.6 | high |
| SpaceX tank pressure | Proof 1.1 × MEOP; ultimate 1.4 × MEOP | 2009 release | medium |
| SpaceX payload factors (uncrewed practice) | Yield 1.10; ultimate (flight) 1.25; ultimate (ground operations) 1.40 | FUG 2025, Table 6-1, printed p.43 [opened] | high |
| NASA preferred practice | Ultimate typically 1.4; yield typically 1.25 | NASA PD-AP-1318 (Apr 1996) [opened] | high |
| Model uncertainty factor | Applied to early coupled-loads results, reduced to 1.0 as the model is verified; no value given | NASA PD-AP-1317 (Apr 1996) [opened] | high (but no number) |
| A NASA design-study set | Limit 1.1; ultimate 1.4; global buckling 1.4 (1.1 or 1.2 in a pressure-loss case); local buckling 1.25 with local knockdown 0.9 | Lovejoy et al. 2010, PDF p.5 [opened] | high |
| Expendable-vehicle standards (SMC-S-005, MIL-HDBK-340A) | Yield 1.1; ultimate 1.25 | search summaries only [quoted] | low as a citation; SpaceX's own Table 6-1 covers it |

## 6. Weight of stiffened cylinders under axial compression

**Gerard & Lakshmikantham (1966).** Allied Research Associates TR 292-2, NASA contract NASw-1174, NTRS 19660015694 [opened].
- They define solidity Sigma = 4 t_bar / d: structural volume over enclosed volume, where t_bar is the smeared wall thickness and d the diameter (Eq. 18, PDF p.27).
- Minimum-weight designs follow Sigma = C (N/(E d))^n (Eq. 32), with the coefficients of Table 2 (PDF p.31, printed 27):

  | Type | n | C |
  |---|---|---|
  | isotropic, perfect | 1/2 | 3.63 |
  | isotropic, imperfect | 2/5 | 1.40 |
  | honeycomb sandwich | 1/2 | 1.02 |
  | longitudinally stiffened, common Z / common Y (zero ring area) | 3/5 | 4.91 / 4.44 |
  | longitudinally stiffened, improved Z / improved Y (zero ring area) | 7/11 | 5.22 / 4.45 |
  | ring stiffened, isotropic skin | 1/2 | 3.63 k_a^(3/4) |
  | ring stiffened, common Z / common Y (k_a = 1) | 3/5 | 6.48 / 5.93 |
  | ring stiffened, improved Z / improved Y (k_a = 1) | 7/11 | 7.14 / 6.01 |

- These are perfect-theory minimum weights, limited to the region where linear orthotropic theory matched tests. A knockdown has to be applied to the load (inferred). The authors treat the ring-stiffened k_a = 1 rows as the reliable ones.
- The perfect-isotropic row reproduces the classical thickness exactly: 4 sqrt(1/1.21) = 3.636.

**Check against optimized designs** (derive.py section 5).
- Lovejoy et al. 2010 optimized unpressurized orthogrid cylinders (R = 200 in, L/R 0.5, knockdown 0.65, factor 1.4) for Nx = 1,800-2,000 lb/in (Figs. 2-3, PDF p.7-8, read off the plots):

  | Design | Area weight (lb/ft^2) |
  |---|---|
  | 2195, genetic-algorithm optimizer | 2.61-2.87 |
  | 2195, PANDA2 optimizer | 2.70-3.00 |
  | 2050 | 1.90-2.00 |
  | 2219 | 2.05-2.15 |

- Gerard with the same knockdown and factor:
  - Ring + common Z gives 2.13-2.27 lb/ft^2, inside that range.
  - Ring + improved Y gives 1.19-1.27, lighter than any optimized design.
  - An SP-8007 monocoque needs 4.8-5.1 lb/ft^2.
- How area weight grows with Nx in the optimized designs: exponent 0.45-0.49 for 2050 and 2219, but 0.90-1.00 for 2195. Lovejoy attributes this to the 1.8 in plate limit, which caps the stiffener height.

**NASA conceptual sizing practice.** Wu, "Loads and Sizing for Launch Vehicle Conceptual and Preliminary Design", NASA LaRC, 3 Jun 2024, NTRS 20240002646 [opened].
- Sizing a monocoque with SP-8007, gamma = 1 and factor 1.4 reproduces flown hardware to within:
  - S-IC intertank: +16% (15.3 against 13.2 klbm);
  - S-IC/S-II interstage: -28%;
  - S-II thrust structure (SP-8019 cone): -12%.
  - Pages: PDF p.10-13 and 30. I reproduced t = 0.465 in (derive.py section 6).
- Non-optimum factors (PDF p.27-29):
  - SLWT LH2 barrel: average 1.80, acreage 1.54;
  - Ares V barrel: 1.54 (coarse model), 1.24 (intermediate), 1.03 (unit cell).
- Bulkhead gores (Wu, Wallace, Cerro, AIAA 2013-0814, NTRS 20130002605): coarse 1.28-2.76 (average 1.90); refined 1.00-1.50 [opened: abstract only].

**Not opened:** Bruhn; Shanley; Block, NASA CR-1766 (downloaded, title page only); Rohrschneider 2002 (404).

## 7. Thrust structure, load entry and assist-side hardware

- **Relations per unit thrust:**
  - 0.255 kg/kN [quoted, Akin];
  - 0.20-0.36 kg/kN for the linear aluminium relations in Castellini Fig. 48 [opened, read off a chart];
  - 0.65 kg/kN for the Saturn S-II thrust cone: 7.3 klbm for 5 × 230 klbf (Wu 2024, PDF p.13) [opened].
- **Castellini's adopted relation** (his "Ref. 5", from a compilation he cites as [100]; by the bibliography's order probably Rohrschneider 2002, (inferred)). It multiplies a thrust-and-engine-mass term by (1.5 × SSM × n_ax,max × g0) × k_SM, so it scales linearly with the design axial load factor (PDF p.83). The printed formula does not make the role of g0 clear.
- **Falcon 9 octaweb, aft skirt and hold-down fittings:** no public mass or load capacity.
- **MagLifter levitation modules,** "~4% of liftoff weight" (README.md:358). Source: Schultz, Radovinsky, Thome, "Superconducting magnets for Maglifter launch assist sleds", IEEE Trans. Appl. Supercond. 11(1):1749-1752 (2001) [quoted; ResearchGate returned 403]. This is sled-side hardware, not vehicle structure.
- **Mankins, "The MagLifter", AIAA 94-2726 (June 1994)** [opened]. The carrier vehicles carry "cradles" that support the vehicle structurally during acceleration and then release it. No vehicle-side mass is estimated.

## 8. Published structural penalties for a ground-assist load case

None found. What the studies I could open say:

- **Olds & Bellini, "Argus ... with Maglifter Launch Assist"**, AIAA 98-1557, NTRS 19980202962, PDF p.8 [opened]. Because the sled carries the takeoff loads, Argus's landing gear is about 25% of a conventional horizontal-takeoff vehicle's, and that saving "cascades" through the design. No structural penalty is charged for the 800 ft/s run, which is horizontal with a gentle pullout.
- **Kloesel et al., "First Stage of a Highly Reliable Reusable Launch System"**, AIAA SPACE 2009, NTRS 20090034160 [opened]. The simulations "do not take into account" the structural changes, and the trade-offs are "left for future study" (PDF p.7). It also notes a design limit of "less than 50 g's" (PDF p.12).
- **MSFC magnetic launch assist summaries** (Jacobs 2000, NTRS 20000103883 and 20000068443; Perez 2000, NTRS 20010071139) [opened: abstracts only]. They claim reduced vehicle weight and estimate no penalty.
- **StarTram:** not searched in depth; it is a different, high-g evacuated-tube concept.
- **This project:** the only numbers are its own break-even rows (README.md:241 and :256; RQ1's penalty rows).

## 9. Arithmetic on the sources (illustration, not a result)

All of this is in derive.py. Inputs not taken from a source are marked ASSUMED there: ullage 3.0 bar gauge, and the stack above stage 1 = 111.5 + 26.054 + 1.7 t, with interstage and dome masses ignored.

- **Station loads** (derive.py section 9):

  | Wall | Liftoff | Push | MECO | Push vs envelope |
  |---|---|---|---|---|
  | LOX tank (carries the stack above stage 1) | 1.86 MN | 5.46 MN | 7.09 MN | **push stays inside the envelope** (matches SP7 file 328-334) |
  | RP-1 tank (also carries the LOX) | 5.69 MN | **16.72 MN** | 7.09 MN | 2.36 × the envelope |

  The aft structure carries the whole stack, about 22.4 MN under the push (the 22.49 MN interface force), against 7.6-8.2 MN of engine thrust.
- **LOX barrel** (monocoque; SP-8007 with Delta gamma; factor 1.4; relief unfactored).
  - Buckling needs 5.9 mm at MECO and 4.7 mm under the push.
  - The push's hoop requirement (10.7 bar of head at the bottom) exceeds 5.9 mm only near the bottom. Increment: about 11 kg with parent Ftu, about 0.47 t with a 0.7 weld efficiency.
  - If the barrel were instead exactly hoop-sized for the liftoff head (zero margin, Q3), the increment would be 1.1-1.6 t.
  - So the LOX term is decided by weld efficiency and by what sizes the existing wall.
- **RP-1 barrel** (stiffened; Gerard; knockdown 0.65 or 0.85; factor 1.4; relief unfactored; before any non-optimum factor of 1.0-1.9):

  | Wall pattern | Envelope mass | Push mass | Increment at 0.65 | Increment at 0.85 |
  |---|---|---|---|---|
  | Ring + common Z | 1.35 t | 2.61 t | 1.26 t | 1.07 t |
  | Ring + improved Y | 0.79 t | 1.59 t | 0.80 t | 0.67 t |

- **Load entry.** Scaling the 0.255 kg/kN thrust-structure relation from 8.23 MN to 22.49 MN adds 3.6 t (2.9-5.1 t over 0.20-0.36 kg/kN). This term has the weakest sourcing: I found no relation for an aft ring or skirt. It is also the largest.
- **Plausibility.** The 5.9 mm monocoque LOX barrel weighs about 4.0 t, the same as Heineman's 4.0 t for the whole LOX tank including domes. A first-order model may therefore come out heavy against the 22.2 t (inferred).

## 10. Recommendations (mine, for Plan mode; not facts)

1. **Wall material.**
   - Central set: 2195 room-temperature parent values (E 75.8 GPa, nu 0.33, rho 2,713 kg/m^3, Fty 503 MPa, Ftu 558 MPa).
   - Do not credit the cryogenic strength gain: no primary source was opened, and room temperature is conservative (as in Lovejoy).
   - Carry a friction-stir weld efficiency of 0.7 as one end of the band. On its own it moves the LOX term from about 0 to about 0.5 t. Real weld lands are thickened, so 1.0 on the acreage is the other end.
2. **Factors.**
   - Ultimate 1.4 on both the push and the envelope cases, and yield 1.1.
   - Check buckling at ultimate load, with relieving pressure at its minimum and unfactored (FSR 19, 53, 54).
   - Keep the dynamic load factor (Q7) separate and explicit; 5001B does not cover load-uncertainty factors.
3. **Tank sizing models.**
   - LOX tank: SP-8007 Eq. 9-10, the digitized Delta gamma table and Eq. 48 for compression; Barlow with the hydrostatic head for hoop. Add a sensitivity case with Delta gamma = 0.
   - RP-1 tank: Gerard ring + common Z (n = 3/5, C = 6.48) with knockdown 0.65 as central. Run 0.75 (1968) and 0.85 (Lovejoy; the SBKF direction) as favourable cases, and ring + improved Y as a light case. Apply pressure relief p pi r^2.
   - Label the Gerard-versus-Lovejoy agreement as calibration, not validation.
4. **Tank pressures.** Mark them `assumed: true`: 3.0 bar gauge in both tanks, band 2.0-4.0 bar, justified by the analogues in section 1.3. Pressure both raises the hoop need and relieves compression, so the sign of its effect on the added mass is not obvious. S2's sizing-only sensitivity ranking should include it.
5. **Load entry (Q5).**
   - No source sizes an aft ring or skirt for a ground push.
   - For the thrust-structure path: scale 0.255 kg/kN (band 0.20-0.36; 0.65 for a cone) with the peak load carried.
   - For an aft ring: size ring and skirt in closed form like the barrels, plus an `assumed: true` fitting factor.
   - Say in the findings note that this term is the least sourced and may be the largest.
6. **Non-optimum factor.** 1.5 central (Wu's acreage value), band 1.0-1.9, applied the same way to the increments and to the plausibility check.
7. **Breakdown file.**
   - Record engines 4.23 t [quoted] and legs under 2.1 t [quoted, v1.1].
   - Mark everything else `assumed: true`, with the relation-based estimates of section 2 as the reason.
   - Keep "are legs and fins inside the 22.2 t?" as an open, assumed item.
8. **Do not cite** the forum pressures, the makeitfrom values or the MDPI cryogenic numbers; I saw them only in summaries.

## 11. Coefficient table

"Low" and "high" are the numeric ends of each range, not the direction of the added mass. Last column: O = I read the number in the source myself; Q = I only saw it quoted.

| Coefficient | Central | Low | High | Source or assumed | Confidence | O/Q |
|---|---|---|---|---|---|---|
| Stage-1 tank construction | Monocoque LOX tank above, skin-and-stringer RP-1 tank below, common dome, transfer tube | - | - | FUG Rev 2 Table 2-1 and section 2.2; FUG 2025 | high | O |
| Tank wall alloy | Al-Li 2195-T8 (barrels); domes "aluminum" | - | - | FUG Table 2-1; Light Metal Age 2019 | medium | O |
| Radius r | 1.83 m | - | - | FUG Table 2-1 | high | O |
| Wall density | 2,713 kg/m^3 | 2,700 | 2,720 | Lovejoy 2010; Hilburger 2019 (range assumed) | high | O |
| Young's modulus E | 75.8 GPa | 72 | 78 | same (range assumed for anisotropy) | medium-high | O |
| Poisson's ratio | 0.33 | 0.30 | 0.33 | same; SP-8007 uses 0.3 | high | O |
| Ftu, parent, room temperature | 558 MPa | 520 (assumed) | 590 (makeitfrom, Q) | Lovejoy (Alcan datasheet) | medium | O (central) |
| Fty, parent, room temperature | 503 MPa | 496 | 560 (makeitfrom, Q) | Lovejoy; Wu 2024 (72 ksi) | medium | O (central, low) |
| Friction-stir weld efficiency | 0.70 | 0.60 | 1.0 | Bhat 2001; ends assumed | medium | O |
| Ultimate factor | 1.4 | 1.25 | 1.5 | FUG Rev 2; 5001B Table 1; FUG 2025 Table 6-1; 1.5 assumed as an early-design allowance | high (1.4) | O |
| Yield factor | 1.1 | 1.0 | 1.25 | FUG 2025 Table 6-1; 5001B Table 1 | high | O |
| Tank proof factor | 1.1 × MEOP | 1.05 | 1.1 | 2009 SpaceX release; 5001B | medium | O |
| Unstiffened knockdown gamma | 1 - 0.901(1 - e^-phi), phi = sqrt(r/t)/16 | same | 0.70 constant (assumed; SP-8007-2020 calls the formula a lower bound) | SP-8007 1968 Eq. 5; 2020 Eq. 9-10 | high (formula) | O |
| Pressure increment Delta gamma | Digitized Fig. 6 / Fig. 4-5 (levels off at 0.25) | 0 (no credit) | Fig. 6 values | SP-8007; Lovejoy uses 0.14 for stiffened walls | medium-high (reading ±10%) | O |
| Stiffened knockdown | 0.65 | 0.65 | 0.85 (0.75 in 1968) | SP-8007-2020; Isogrid Design Handbook 4.2; Lovejoy 2010 | high (0.65) | O |
| Stiffened efficiency exponent n | 3/5 | 1/2 | 7/11 (0.9-1.0 if plate-limited) | Gerard 1966 Table 2; Lovejoy trends | medium | O |
| Stiffened efficiency C (Sigma = C (N/(E d))^n, Sigma = 4 t_bar/d) | 6.48 (ring + common Z) | 5.93-6.01 (ring + Y) | 7.14 (ring + improved Z) | Gerard 1966 Table 2 | medium | O |
| Non-optimum factor | 1.5 | 1.0 | 1.9 | Wu 2024; Wu et al. 2013 | medium | O (2013: abstract) |
| LOX ullage pressure | 3.0 bar gauge | 2.0 | 4.0 | Assumed; no public F9 value; analogues in section 1.3 | low | - |
| RP-1 ullage pressure | 3.0 bar gauge | 2.0 | 4.0 | Assumed, as above | low | - |
| LOX density | 1,253 kg/m^3 (66.5 K) | 1,237 (70 K) | 1,265 (64 K) | NIST WebBook; 66.5 K from Musk via Wikipedia (Q) | high (density), medium (temperature) | O (density) |
| RP-1 density | 820 kg/m^3 (266.5 K) | 815 | 825 | NIST IR 6646 Table 8, extrapolated; 266.5 K via Wikipedia (Q) | medium | O (density) |
| LOX / RP-1 column height | 21.8 m / 14.3 m | - | - | Derived from the vehicle file's masses | medium-low | derived |
| Dome shape | Ellipsoid, a/b = sqrt(2) | 1 (hemisphere) | 2 | Assumed. sqrt(2) is the textbook ratio where the equator's hoop stress stops being tensile (inferred) | low | - |
| Merlin 1D mass | 470 kg | 450 | 520 | Mueller via Wikipedia; range assumed | low-medium | Q |
| Landing legs (v1.1) | Under 2,100 kg | - | - | Light Metal Age 2019 | low-medium | Q |
| Grid fin, octaweb, interstage and aft-skirt masses | None public | - | - | - | - | - |
| Tank mass relation (cross-check) | 10.41 V^0.75 (lbm, ft^3), ±30% | -35% (SLWT) | +30% | Heineman via Wu 2024 | medium | O (via Wu) |
| Thrust-structure coefficient | 0.255 kg/kN | 0.20 | 0.36 (0.65 for a cone) | Akin (Q); Castellini Fig. 48 (O, chart reading); Wu S-II (O) | low | Q (central) |
| Interstage relation (cross-check) | 0.93 t (composite) | - | 1.34 t (Al) | Castellini Table 15 | low-medium | O |
| Vehicle-side penalty of a ground push | None published | - | - | Argus 1998; Kloesel 2009; MSFC abstracts | high (absence in what I read) | O |
| MagLifter levitation modules | About 4% of liftoff weight (sled side) | - | - | Schultz et al. 2001 via README.md:358 | low | Q |

## 12. Sources (URLs)

**SpaceX and Falcon 9**
- Falcon 9 Payload User's Guide Rev 2 (2015): https://wayback.archive.org/web/20160103224230/http://www.spacex.com/sites/spacex/files/falcon_9_users_guide_rev_2.0.pdf
- Falcon User's Guide v8 (March 2025): https://www.spacex.com/assets/media/falcon-users-guide-2025-05-09.pdf (downloaded with a browser user-agent)
- 2009 SpaceX release, as republished: https://www.aeroweb-fr.net/depeches/2009/07/spacex-completes-qualification-of-falcon-9-first-stage-tank-and-interstage
- Light Metal Age, 26 Apr 2019: https://www.lightmetalage.com/news/industry-news/aerospace/how-light-metals-help-spacex-land-falcon-9-rockets-with-astonishing-accuracy/
- Wikipedia: https://en.wikipedia.org/wiki/Falcon_9_Full_Thrust ; https://en.wikipedia.org/wiki/SpaceX_Merlin ; https://en.wikipedia.org/wiki/Falcon_9_v1.0

**Propellant properties**
- NIST WebBook, oxygen: https://webbook.nist.gov/cgi/fluid.cgi?ID=C7782447
- NIST IR 6646: https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir6646.pdf

**Standards and design criteria**
- NASA-STD-5001B with Change 3: https://standards.nasa.gov/sites/default/files/standards/NASA/B-w/CHANGE-3/3/2022-10-24-NASA-STD-5001B-w-Change-3-Approved.pdf
- SP-8007 (1968): https://ntrs.nasa.gov/api/citations/19690013955/downloads/19690013955.pdf
- SP-8007-2020 REV 2: https://ntrs.nasa.gov/api/citations/20205011530/downloads/20205011530%20Rev%202FINALa%201-2023.pdf
- Isogrid Design Handbook: https://ntrs.nasa.gov/api/citations/19730011184/downloads/19730011184.pdf
- PD-AP-1317: https://klabs.org/DEI/References/design_guidelines/analysis_series/1317.pdf
- PD-AP-1318: https://extapps.ksc.nasa.gov/Reliability/Documents/Preferred_Practices/1318.pdf

**Buckling and stiffened-shell weight**
- Hilburger 2012: https://ntrs.nasa.gov/api/citations/20120008172/downloads/20120008172.pdf
- Hilburger 2018: https://ntrs.nasa.gov/api/citations/20180006178/downloads/20180006178.pdf
- Hilburger & Lindell: https://ntrs.nasa.gov/api/citations/20190000441/downloads/20190000441.pdf
- Lovejoy et al. 2010: https://ntrs.nasa.gov/api/citations/20100016271/downloads/20100016271.pdf
- Gerard & Lakshmikantham 1966: https://ntrs.nasa.gov/api/citations/19660015694/downloads/19660015694.pdf

**Mass estimation**
- Wu 2024: https://ntrs.nasa.gov/api/citations/20240002646/downloads/05-LV_Loads_Sizing.pdf
- Wu et al. 2013: https://ntrs.nasa.gov/citations/20130002605
- Castellini 2012: https://www.politesi.polimi.it/retrieve/a81cb059-f560-616b-e053-1605fe0a889a/201203_PhD_Castellini.pdf
- Dresia et al. 2020: https://arxiv.org/pdf/2009.01664

**Welding and materials**
- Bhat 2001: https://ntrs.nasa.gov/api/citations/20020015869/downloads/20020015869.pdf
- Russell 2000: https://ntrs.nasa.gov/api/citations/20010067248/downloads/20010067248.pdf

**Saturn V**
- SA-503 flight manual: https://ntrs.nasa.gov/api/citations/19750063889/downloads/19750063889.pdf

**Launch assist**
- Mankins 1994: https://ewh.ieee.org/r4/se_michigan/Spring2011/AIAA-1994-2726-303%20mankins%20maglifter%20electromagnetic%20launch.pdf
- Olds & Bellini 1998: https://ntrs.nasa.gov/api/citations/19980202962/downloads/19980202962.pdf
- Kloesel 2009: https://ntrs.nasa.gov/api/citations/20090034160/downloads/20090034160.pdf

**Could not reach:** Akin's UMD lectures (connection refused), Rohrschneider 2002 (404), web.archive.org (blocked), ResearchGate, MDPI and the NASASpaceflight forum (all 403).
