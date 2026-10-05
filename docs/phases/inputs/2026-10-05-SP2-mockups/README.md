# SP2 mock-ups (step A0, 2026-10-05)

The two static mock-ups shown to the user in the chat on 2026-10-05, in SP2 step A0, at
commit b69ff0c. The user approved them with the design
([../2026-10-05-SP2-design.md](../2026-10-05-SP2-design.md), "Status": "The two mock-ups
shown in the chat ... are part of what is approved; their numbers are illustrative";
decision D-SP2-08 for the look). They are a record and are not edited.

| File | What it shows |
|---|---|
| [scene-frame.svg](scene-frame.svg) | One frame of the 2-D launch scene, one second before release (T -1.00 s): two panels on one clock and one scale. Left, the pad: the rocket held down by its clamps with the engines at half thrust, both tanks full. Right, the 100 m silo in cross-section: the unlit rocket riding the carriage up the shaft past the drive rings, the stage-1 tank 90% full. Each panel has a scale bar, two tank gauges and a short readout; below them are the clock, the rate, a timeline with the event marks (release, MECO, staging, fairing, cutoff) and a legend that names the display-only shapes |
| [app-page.html](app-page.html) | The app page: the header with the address and the "Exploratory runs, not findings" tag; the form (preset, launch site, silo depth, push set by net acceleration or exit speed, where the stage-1 thrust ramp starts, propellant, stage-2 pre-offload, assumed structural penalty, Launch); the progress of one launch by stage with its results directory; the results panel with four numbers and the caveats beside them; the scene player (a placeholder box); the list of recorded runs |

**Every number in the two files is illustrative.** None was produced by the app, which does
not exist yet.

- The scene frame's readouts (depth 62 m, 47 m/s, 4.0 g felt, 20.7 MN of drive force, thrust
  50% on the pad, the 90% tank) were computed by hand from SP1's settings for the 3 g, 100 m
  cold-start silo.
- The app page's four result numbers (41.26 t, 10.04%, +3.4%, 26,054 kg) and its caveat
  lines (+14.3%, an assumed +8.1 t leaving 1.98 t) repeat SP1's recorded headline
  ([../../../findings/RQ1-fuel-offload-2d.md](../../../findings/RQ1-fuel-offload-2d.md)),
  with its caveats there.
- The timings (2 min 44 s; 14 s, 104 s and 31 s by stage) and the name
  `results/app/20261005T181204Z` are placeholders. No such directory exists.
- The run counts and sizes in the list of recorded runs are those of the phase file's
  section 6.

What the files are, and what was added to them:

- They were drawn for a chat widget host that supplies CSS classes (`t`, `ts`, `th`, `box`,
  `c-gray`, `leader`), CSS variables (`--s`, `--surface-1`, `--surface-2`, `--border`,
  `--border-strong`, `--border-stronger`, `--text-secondary`, `--text-muted`,
  `--bg-warning`, `--text-warning`, `--border-warning`, `--bg-success`, `--text-success`,
  `--fill-primary`, `--on-primary`, `--radius`) and an icon font. The widget code was
  taken from the session transcript.
- So that each file renders on its own, a small `<style>` block with plain fallback values
  was added to each. The SVG also got the `xmlns` attribute a standalone SVG file needs.
  The HTML fragment got a minimal document wrapper (doctype, `<meta charset>`, a title),
  and two plain glyphs stand in for the icon font. Nothing else was changed.
- The colours of those fallbacks, and the blue and orange of the drawings, are not the
  project's palette. The real pages use the project's brand tokens (the site's set, light
  and dark; the design, section 4.5 and D-SP2-33).

The mock-ups were shown before the first draft of the design was written and reviewed. The
approved design adds things they do not show, among them the fixed-scale close-up of the
vehicle in each panel (D-SP2-35) and the scene's own playback rate law (D-SP2-21; the
mock-ups show the replay page's "Auto" rate and its 1x, 5x and 30x choices).
