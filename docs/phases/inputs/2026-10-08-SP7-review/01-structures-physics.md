<!-- Record of SP7 step 0: independent adversarial review (structures-physics) of design draft v1 (draft-v1.md in this folder), made by a workflow agent on 2026-10-08 at HEAD 22c62e9 and rendered from its structured output. The disposition of every finding is appendix A of ../2026-10-08-SP7-design.md. Not edited. -->

# Review: structures-physics

Structures-physics lens. The free bodies in section 4.2 are right. With a common dome, cutting the RP-1 barrel gives N = (U + struct + m_LOX) n g0 + D - p_u,RP1 pi r^2. The LOX ullage pressure stays inside that free body, so it does not enter. The SP-8007 Eq. 48 relief is subtracted once and Delta_gamma is added once, so nothing is double-counted. The DLF on the increment over the resting load is right for a step from preload, and a quasi-static pad envelope is conservative. But the station model as drafted under-charges the push in several places, and nearly all of them point toward a larger offload. (1) Max-of-modes has no combined-stress check, and the push is the only case where high hoop and high axial compression meet at the same lower stations. My scratch run at S06's central coefficients adds about 0.39 t before NOF. (2) Gerard's C and n can be corner-searched as independent ranges, and the plate-limited exponent for 2195 is missing. (3) The dome junction rings, the LOX transfer tube, the feed system and submerged hardware are missing from both the model and the caveats. (4) No drive models a ramp-down, so every release is a step. The SDOF swing takes the upper stack and payload to about -4 g0, against the published -2.0 g payload limit, and reverses the common-dome pressure difference. The design reports this as a flag without saying dm is then a lower bound. (5) The rise-time rule t_r = 10 T_low/pi holds the DLF at 1.03-1.10 in every coefficient set, so the band leaves out the term S08 ranks first. (6) Section 1's magnitude (12-33 t) uses k_entry = 20-100 kg/MN, but the design's own high anchor is 200-360 kg/MN, which is 4.5-8.1 t of hardware alone. Smaller issues: FS_u is applied twice on the common dome; the relief term never names its tank; margin is applied to thickness instead of load; a single DLF is used for every station, where my 4-mass chain gives 3.3-3.5 at the upper station for a step; the plausibility check has no consequence; and corner sets found at the headline push are reused at other strokes and drives. Scratch scripts (no repository file written): C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/review/structures-physics/chain_dlf.py, modes.py, vm.py.

## SP-1 [major] (4.2.1, 4.2.5, D-SP7-12) favours_assist=True

Issue: The rise-time rule ties t_r to the lowest assumed frequency (t_r = 10 T_low/pi), which makes DLF = 1 + f_low/(10 f). Every coefficient set, including the high-mass corner, therefore has a DLF in [1 + f_low/(10 f_high), 1.10]. With S07's 3/5/10 Hz the band's DLF is 1.03 / 1.06 / 1.10 by construction. The corner search cannot carry the uncertainty S08 ranks first (the DLF), and the constant_accel structural headline credits a ramp its own trajectory does not have. The frequency range then shifts the DLF by at most 0.07.

Evidence: Draft 4.2.1 (lines 200-204), D-SP7-12 (line 102), 4.2.5 (233-242); S07 lines 189-190, 244, 412 (3/5/10 Hz; t_r = 1.06 s at 3 Hz); S08 section 3 and section 8 (coupled x: DLF 1.0 gives 12.2-32.9 t, DLF 1.3 gives 1.6-29.5 t, DLF 2.0 gives 0-20.2 t). Computation: 1 + (1/f)/(pi x 1.061 s) = 1.100, 1.060, 1.030 at 3, 5, 10 Hz.

Recommendation: Give the constant_accel and linear-motor rise time its own assumed range, independent of f (no source bounds what a 20-23 MN drive can achieve, so say so and make the range wide), and include it in the corner search and the tornado. Alternatively, pre-register that the band is conditional on the rise-time rule, write the quasi-static and step rows into the band line itself, and say in every headline sentence that DLF <= 1.10 is a drive-design assumption, not a result.

## SP-2 [major] (4.2.2, D-SP7-13, section 1) favours_assist=True

Issue: The release is a step for every drive (no ramp-down is modelled), so the release flag fires on every case. Four consequences go unsized. (a) The SDOF swing n_after - (n_rel - n_after) = -4.0 g0 puts the upper stack and payload far past the published payload tension corner of -2.0 g, contradicting section 1's implication that stage 2 and the interstage are untouched by the push. (b) In a 4-mass chain of the headline stack, the upper-stack spring swings to -2.3x its push quasi-static load, against -1.0x for the SDOF. (c) The LOX side of the common dome drops below the RP-1 ullage pressure, so the dome is loaded on its convex side (buckling), which nothing checks. (d) After the column separates, its re-impact (water hammer) is bounded by nothing in the model, and the walls have no axial-tension mode. The flag text does not say dm is then a lower bound, as the upper-stack flag does.

Evidence: Draft 4.2.2 (lines 211-215), 4.6 (F = min(F_lim, F_max, P_max/sdot) with release at s = L or v_release; no ramp-down); constant_accel.py:224 ('infinite jerk at push start and release'); S07 lines 11 and 276 (FUG 2025 payload axial +6.0/-2.0 g; tension corners -1.5 to -2.0 g); S08 section 3 (LOX bottom -0.53 MPa absolute). Scratch chain_dlf.py: release minimum of the LOX-barrel/upper spring is -2.33 (headline) and -2.39 (full load) times the push quasi-static load.

Recommendation: Either model a release ramp-down by the same rule as the rise (with its exit-speed cost), then size a tension mode and the common dome's reverse pressure and check the payload against -2.0 g. Or state in every modelled sentence that dm excludes the release transient and is a lower bound wherever the flag fires, which is every case. Compare the push release with the pad's MECO unload under the same dynamic treatment, so the asymmetry is visible.

## SP-3 [major] (4.2 (modes), D-SP7-10) favours_assist=True

Issue: Max-of-modes has no combined (biaxial membrane) stress check. The push is the only load case with high hoop tension and high axial compression at the same lower barrel stations: liftoff has the head but little compression, and MECO has the compression but only ullage hoop. So the omission removes mass from the push side only.

Evidence: Draft lines 174-188. Scratch vm.py at S06 central (E 75.8 GPa, F_tu 558 MPa, eta_w 0.7, FS 1.4, p_u 3 bar, Gerard 6.48/0.6, k_s 0.65): at the hoop-sized LOX barrel bottom, von Mises/(F_tu eta_w) is 1.067 at the push and 0.987 at liftoff. Adding a von Mises membrane mode raises the RP-1 barrel increment from 1,141 to 1,464 kg and the LOX barrel from 39 to 104 kg before NOF (+0.39 t; about 0.58 t with NOF 1.5, about 2.6 t of offload at E = 4.5). With eta_w = 1.0 the effect vanishes, so it depends on the weld treatment.

Recommendation: Add an interaction mode, von Mises or Tresca on hoop plus net axial membrane stress at ultimate (relief unfactored, eta_w on the weld lines), to both the envelope and the push cases; test it against a hand value; state how eta_w enters it.

## SP-4 [major] (4.2 (stiffened), 4.2.5, 4.3) favours_assist=True

Issue: Gerard's C and n are a fitted pair (one row of Table 2), but the schema makes 'every number a range quantity' and the 2^k corner search runs over '(C, n)'. Searched independently they give unphysical walls. At the headline, N_x/(k_s E d) = 9.2e-6; with C = 6.48 the smeared thickness is 5.6 mm at n = 3/5, 17.9 mm at n = 1/2 and 3.7 mm at n = 7/11, so corners like these would dominate both ends of the band. Separately, S06 found that Lovejoy's optimized 2195 designs scale as N^0.90-1.00 (plate-limited). Table 2 does not cover that trend and the design leaves it out. At exponent 1, anchored at the envelope load, the RP-1 compression increment at the bottom station roughly doubles (2.5 to 5.2 mm).

Evidence: Draft lines 183-185 and 233-242; schema line 257; S06 section 6 and table rows 318-319 ('n 3/5, low 1/2, high 7/11 (0.9-1.0 if plate-limited)'; 'C 6.48, 5.93-6.01, 7.14'). Computation: t_bar = (d/4) C (N_x/(k_s E d))^n with N_x = 1.652 MN/m, d = 3.66 m.

Recommendation: Make the stiffened construction one discrete choice of Table-2 rows (C and n together), searched as rows. Add a plate-limited row (exponent about 1, anchored at the envelope load) as the stated high end, or explain why F9's skin-and-stringer RP-1 tank is not plate-limited.

## SP-5 [major] (1, 4.2.3, D-SP7-14) favours_assist=True

Issue: Section 1's magnitude (0.4-2.1 t of load-entry hardware; 12-33 t of offload) comes from S08's placeholder k_entry = 20-100 kg/MN. Section 4.2.3 anchors k_entry's high end on the thrust-structure relation, 200-360 kg/MN, which is 4.5-8.1 t at F_peak = 22.4 MN (DLF 1.1). That hardware alone is close to or above SP1's 8.1 t break-even row. The 'central' anchor (hold-down hardpoint structure per unit load) has no source. The high anchor also double-counts the aft skirt, which is already sized in closed form.

Evidence: Draft lines 35-40 and 221-226; S06 section 7 and lines 229, 331 (0.20-0.36 kg/kN; no public mass for the octaweb, aft skirt or hold-down fittings); S08 section 7. F_peak = 5.19 + 1.1 x (20.81 - 5.19) = 22.4 MN; 0.20-0.36 kg/kN x 22.4 MN = 4.5-8.1 t.

Recommendation: Restate section 1 and the pre-registration's expected x* with the anchors actually adopted. Give k_entry's central value a computable basis, for example a closed-form ring in bending between a stated number of carriage pads, instead of an unsourced order of magnitude. Choose one treatment at the high end so the skirt is not counted twice.

## SP-6 [major] (4.2 (elements), 4.11) favours_assist=True

Issue: Elements that carry the new load are missing from the model, and the findings-note caveats do not name them. (a) The common-dome and aft-dome junction rings, which take the dome resultants as line loads: at ultimate, the common-dome junction goes from about 0.46 MN/m at liftoff to 1.23 MN/m in the push (2.66x), and the aft junction from 0.58 to 0.91 MN/m. (b) The LOX transfer tube and feed system: the tube bottom sits under about 34 m of LOX, so it sees about 2.0 MPa at 3.996 g0 against about 1.24 MPa, the flight maximum near MECO (1.6x), plus prevalves, manifolds and engine inlets. (c) Hardware submerged in full tanks, such as COPVs in the LOX tank if stage 1 carries them there, whose strut loads scale as buoyancy x n. (d) Engine mounts, which a cold push loads in reverse (tension). S08 section 9 had listed the feedlines, Y-rings and joints.

Evidence: Draft 4.2 element list (lines 152-156) and 4.11 caveats (lines 504-508); S06 section 1.1 (transfer tube through the RP-1 tank); S08 section 9. Computation: junction line load 1.4 x (m_LOX n g0 + delta-p A)/(2 pi r) with r = 1.83 m; tube head 1253 x 9.80665 x n x (H_LOX + 14.75 m) + 0.3 MPa. (c) rests on the reviewer's recollection that CRS-7 was a COPV-strut failure under ascent acceleration; to be verified in S0.

Recommendation: Add the junction rings as an element (line load = dome resultant / 2 pi r, sized by a closed form or a stated coefficient) and the transfer tube's hoop at its bottom. List (c), (d) and the rest as unmodelled in the caveats and in the 'not a detailed design' text. Say whether the NOF (Wu's 1.54 acreage value) covers joints and rings; if it does not, use the 'average' value or a separate term.

## SP-7 [minor] (4.2.1, D-SP7-07, 4.2.2) favours_assist=True

Issue: One SDOF DLF is applied to every station. In a multi-mass chain the upper stations overshoot more. A step gives 2.0 at the skirt and the RP-1 barrel but 3.3-3.5 at the LOX-barrel/upper-stack spring. At t_r = 0.1 s the chain gives 1.6, against an envelope of 1.43. At the rule's t_r the gap is small (1.094-1.115 against 1.10). So the step row is not a bound at the upper stations, and the upper-stack threshold (DLF > 1.40) is unreliable for short rise times.

Evidence: D-SP7-07 ('the step (factor 2) as a bound row'); draft lines 200-210. Scratch chain_dlf.py: 4 masses (ring, RP-1 + aft dry, LOX + lower tank, U + top dry), wall springs, no dome compliance; first elastic mode 7.3-7.4 Hz.

Recommendation: Call the step row 'the single-mode step value', not a bound. Either derive the upper-stack flag from a small modal chain that can be tested in closed form, or state that the uniform DLF is not conservative at the upper stations.

## SP-8 [minor] (4.2.1, D-SP7-12) favours_assist=True

Issue: For constant_accel in rise_time mode, the structure uses the constant-acceleration n (3.996 g0), but the assumed ramp needs a higher plateau to reach the same exit speed in the same stroke. For a linear ramp from rest over t_r = 1.06 s (the rule at 3 Hz), the plateau net acceleration is 1.2% higher and the felt n 0.9% higher (4.032 g0). This is not charged.

Evidence: Closed form for a ramp then constant acceleration at fixed L and v_e: a' = [L - sqrt(L^2 - v_e^2 t_r^2/12)]/(t_r^2/12) = 29.77 against 29.42 m/s^2 at L = 100 m, v_e = 76.707 m/s; this agrees with S07 line 18 (+0.2-0.9% of F_max).

Recommendation: Evaluate n for the rise_time case at the plateau of the ramped profile with the same (L, v_e), using the closed form above, or state the bias next to the headline.

## SP-9 [minor] (4.2 (compression), 4.2.3) favours_assist=False

Issue: N_d = FS_u N - p_u,min pi r^2 never says whose pressure. The relief must be the RP-1 tank's minimum pressure for the RP-1 barrel and the LOX tank's for the LOX barrel. The unpressurized aft skirt, which 4.2.3 sizes with the same stiffened rule, gets none. The band varies p_u,LOX and p_u,RP1 independently, so a mix-up changes the result. Hoop should use the maximum expected operating pressure (SpaceX: ultimate 1.4 x MEOP), and relief the minimum. The free body itself checks out: with a common dome the LOX ullage pressure is internal to the RP-1 barrel's cut.

Evidence: Draft lines 166-168 and 177-178; S06 table line 166 (1.4 x MEOP ultimate) and FSR 19 (line 162). Free body above a cut in the RP-1 barrel: N_wall + p_RP1(z) A = (U + struct + m_LOX + m_RP1,above) n g0 + D, and p_RP1(z) A - m_RP1,above n g0 = p_u,RP1 A.

Recommendation: Write each element's free body with the tank named; use no relief on the skirt; use MEOP for hoop and p_u,min for relief; add a test with p_u,LOX different from p_u,RP1.

## SP-10 [minor] (4.2 (domes)) favours_assist=False

Issue: (a) The common-dome text inserts p_net = FS_u(p_u,LOX + rho n g0 H) - p_u,RP1,min into t = FS_u p_net r k_d/(F_tu eta_w). That applies FS_u^2 to the LOX side and factors the relieving pressure, contrary to FSR 19. (b) Crown-only sizing: for a/b above sqrt(2) (S06's band reaches 2) the equatorial hoop stress is compressive, sigma_theta = (p a/t)(1 - k^2/2) = -p a/t at k = 2, a buckling mode the crown check misses. (c) The common dome's reverse-pressure (convex-side) case is not checked. (d) The crown head ignores the dome depth (about +0.43 m at sqrt(2) with dome volumes neglected). (e) With 3% ullage (4.5 m^3 of RP-1 ullage) and a 9.1 m^3 dome bulging into the RP-1 tank, the full RP-1 surface lies inside the dome, so the cylinder-equivalent geometry is inconsistent there.

Evidence: Draft lines 188-192; S06 table line 326 (a/b 1 / sqrt(2) / 2); FSR 19 (S06 line 162). Dome volume (2/3) pi r^2 (r/sqrt 2) = 9.08 m^3.

Recommendation: Factor once and leave the relieving side unfactored. Add an equator check, or bound a/b at sqrt(2). Add the reverse-pressure buckling case for the common dome (pad pressurization sequence and the release swing). Use the head at the crown.

## SP-11 [minor] (4.2.3, section 1) favours_assist=False

Issue: The aft skirt's envelope, the hold-down support only (5.593 MN), is an unsupported fixed choice. S05 infers that the hold reacts through the thrust structure (so the skirt envelope could be about 0). S08's probe used the flight thrust path (7.88 MN at about 100 s). Section 1 quotes 'the aft structure 2.6-2.9 times', which is S05's flight-path ratio; against the design's own skirt envelope the ratio is 3.7-4.0. The hold also puts the skirt in 2.04 MN of tension at the end of the hold.

Evidence: Draft lines 32-33 and 217-219; S05 section 3.2 ('the thrust structure carries up to 7.607 MN, while every station above it carries only the weight'), S05 interface table (3.721x / 4.021x against the 5.593 MN clamp); S08 section 6 (aft skirt governed at 97-101 s, 7.7-7.9 MN).

Recommendation: Make the skirt envelope a discrete assumed choice (none, hold-down, flight thrust path) in the tornado or the band, with a reason, and correct section 1's ratio.

## SP-12 [minor] (4.2 (envelope), D-SP7-03) favours_assist=True

Issue: The margin is applied to thickness, t_env = (1 + margin) max t, not to load. A 10% thickness margin is about 21% load margin in monocoque buckling (t roughly proportional to N^0.5), about 17% under Gerard (n = 0.6) and 10% in hoop, while '10% margin' reads as a margin of safety on load. The margin rows therefore overstate the existing capacity in the buckling-governed elements.

Evidence: Draft line 194; (1.1)^2 = 1.21 and (1.1)^(1/0.6) = 1.172.

Recommendation: Apply the margin to the envelope loads and pressures before sizing, or rename it 'thickness margin' and report the load equivalent of each mode.

## SP-13 [minor] (4.2.2, 4.4 (payload form)) favours_assist=True

Issue: The upper-stack flag compares n only. In the payload form U_push > U_pad (P* 27.55 t against P_ref 26.05 t), so the threshold is n U (about 5.14 g0 at full load, not 5.195). t_push takes push samples only, so the payload form's post-release flight exceedances (+0.15-0.18% at the interstage, +0.6-0.7% at the aft station) are charged nowhere.

Evidence: Draft lines 195 and 207-210; S05 section 4 break-even table (n U 5.140 for silo_cold) and section 5 (flight exceedances of the full-load runs).

Recommendation: Flag on n U against the pad's maximum n U. In the payload form, take t_push over the assisted run's whole stage-1 flight, not just the push.

## SP-14 [minor] (4.2 (monocoque), 4.2 (station loads)) favours_assist=True

Issue: (a) Delta_gamma(p, t) does not say which pressure it uses. If it takes the local p(z), including the push's hydrostatic head at n_peak, the push's own DLF-amplified load is credited as stabilizing; FSR 19 and 53-54 require the stabilizing pressure at its minimum, unfactored. This matters where the LOX barrel compression exceeds MECO's: the step row and the 50 m stroke. (b) N = m_above n g0 + D puts all drag above every station, an upper bound on the envelope (base drag acts below), while the push side leaves out the snug-shaft air momentum on the vehicle (about 77 kN). Both are negligible (0.01% and 0.4%), but both lean toward the assist.

Evidence: Draft lines 166-168 and 180-182; S06 section 5 (FSR 19, 53-54); S05 section 3.5 (drag moves the envelope by 0.01%); S08 section 4 (77 kN).

Recommendation: Use p_u,min only in Delta_gamma, and state it. Either use D on the envelope side with a nose fraction or leave it out, and state the push side's omitted air load.

## SP-15 [minor] (4.2 (envelope), 4.11) favours_assist=True

Issue: The RP-1 and LOX barrel envelopes, which carry the dominant increment, are set by the model's unthrottled, instantaneous MECO (5.195 g0). No row tests that credit, although S05 asked for a MECO-envelope sensitivity. Under Gerard, dropping the MECO case (ultimate net 7.2 MN, against 4.9 MN at liftoff) raises the RP-1 compression increment by about 26%.

Evidence: S05 section 8 and recommendation 6; draft D-SP7-11 (line 101). Computation: (19.0^0.6 - 7.2^0.6)/(19.0^0.6 - 4.9^0.6) = 2.58/3.26.

Recommendation: Add a tornado or sensitivity row with the envelope's stage-1 maximum capped at a stated lower acceleration, or with MECO excluded. Name the MECO credit in the caveats as the source of the RP-1 barrel's envelope.

## SP-16 [minor] (4.2.4) favours_assist=False

Issue: The plausibility check has no consequence and no threshold. Brief 5.3 says a large disagreement 'is reported and widens the band'; the draft says only 'it changes no coefficient'. S06 and S08 already show the model's envelope may come out heavy: the monocoque LOX barrel alone matches Heineman's whole LOX tank.

Evidence: Draft lines 228-231; brief docs/phases/SP7-structural-mass-push-load.md:365-367; S06 section 9 ('Plausibility'); S08 section 6 (9.2 t monocoque envelope, 51% of the non-engine dry mass).

Recommendation: Pre-register a threshold (for example, the envelope tank mass outside Heineman's +/-30%) and a fixed consequence (for example, a row that scales the increment by the plausibility ratio, or a widened band), before any run.

## SP-17 [minor] (4.2.5, D-SP7-15) favours_assist=False

Issue: The corner search is not 'seconds'. With about 20-24 ranged coefficients that is 1-17 million corners, and each one recomputes the envelope over about 3,000 pad samples x N stations with a root solve per monocoque station. The sets are also frozen at the headline push but reused for the 50 m stroke, the linear-motor cases and the payload form. Coefficient directions can flip with the buckling form (S08) and with n, so 'the bounds of the stated coefficient ranges' is not true outside the headline.

Evidence: Draft lines 236-242 and 461-463; S05 section 2 (3,073 pad stage-1 samples); S08 section 7 (the direction of p_u's effect flips with the form).

Recommendation: Prove the monotone directions by test (NOF, k_entry, FS_u and others), fix those coefficients, and search only the rest. Label other cases' bands 'the headline's corner sets', or re-run the sizing-only search per case.
