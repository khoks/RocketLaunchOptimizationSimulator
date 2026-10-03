# Source note: the RP-1 heating value for the SP1 energy comparison

Looked up on 2026-10-02 for SP1 step 8 (the `offload.energy` block of
experiments/silo_offload_2d.yaml). Input to the step 8 implementer; the experiment file
cites the source itself.

## Value to use

- RP-1 lower (net) heat of combustion: **18,500 Btu/lb minimum**, the requirement of
  military specification MIL-DTL-25576E, "Propellant, Rocket Grade Kerosene" (14 April
  2006), test method ASTM D240. The specification's table lists the same minimum for RP-1
  and RP-2.
- In SI: 18,500 Btu/lb x 2.326 kJ/kg per Btu/lb (the International Table Btu per pound,
  an exact factor) = 43,031 kJ/kg = **43.03 MJ/kg**.
- It is a specification minimum. Delivered lots are slightly higher (measured net heats
  of RP-1 sit around 43.2 MJ/kg in the NIST literature below). Using the minimum gives a
  slightly smaller heat for the removed RP-1, so it lowers the energy ratio a little; it
  does not favour the assist. State this beside the ratio.
- "Net" means the water product is vapour (lower heating value); the NIST paper notes
  that the net, not the gross, heat is used in rocket-propellant specifications.

## Where it was confirmed

- Web search results (2026-10-02) quoting MIL-DTL-25576E: RP-1 net heat of combustion
  18,500 Btu/lb minimum by ASTM D240 (about 43 MJ/kg). The DLA ASSIST copy of the
  specification (quicksearch.dla.mil) was not reachable directly (transient link).
- L. S. Ott, A. B. Hadler, T. J. Bruno, "Variability of the rocket propellants RP-1, RP-2,
  and TS-5: application of a composition- and enthalpy-explicit distillation curve
  method", Industrial & Engineering Chemistry Research (NIST, 2008),
  https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=832254 : cites MIL-DTL-25576E
  (April 14, 2006) as reference 1 and defines the net enthalpy of combustion used in the
  specification (H2O as vapour).

## The LOX/RP-1 split

Already sourced in configs/vehicles/generic_f9_class_2d.yaml (source strings of the
propellant masses; Espace & Exploration No. 39 via Wikipedia, Falcon 9 Full Thrust):
stage 1 287.4 t LOX + 123.5 t RP-1 = 410.9 t; stage 2 75.2 t LOX + 32.3 t RP-1 = 107.5 t.
The vehicle file is never edited, so the split is repeated, with that source, in the
experiment's `offload.energy` block.

## What the ratio leaves out (say so in the summary and the findings note)

LOX production (air separation energy), RP-1 refining and transport, power generation and
storage losses, and the energy embodied in the silo. The ratio compares the combustion
heat of the RP-1 not carried with the push's electrical input at the assumed drive
efficiency; it is not an efficiency.
